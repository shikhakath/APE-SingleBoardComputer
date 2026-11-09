"""APE-SBC placement helpers: the board, part geometry, checks, renders, and applying a placement to PCB.PcbDoc.

The positions themselves are written by hand in blocks/, one file per schematic function, and blocks.py turns them
into placement.csv. docs/pcb-floorplan.md says why each block is where it is. Run from hardware/gen:

    python build.py check            refresh out/netlist.csv and friends
    python blocks.py build           check the block files and write placement.csv
    python placement.py check        offline courtyard, outline and through-hole checks
    python placement.py render       out/place_top.png, out/place_bot.png
    python placement.py budget       area, routing-demand and distance numbers

These drive Altium; take the lock first (mkdir C:/Users/Public/altium_mcp.lock):

    python placement.py board        outline with R3 corners, notes on Mechanical 13
    python placement.py apply        move every part, rebuild the ratsnest, save
    python placement.py refresh      rebuild the ratsnest and save
    python placement_check.py        Altium's check_placement over the whole board

Frame: mm, origin at the board's lower-left corner, +y up, rotation CCW, top view.
A bottom-side part is mirrored in x and then rotated (top view); export() converts
that to Altium's rotation. docs/pcb-placement.md has the reasoning.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

GEN = Path(__file__).resolve().parent
sys.path.insert(0, str(GEN))
import footprints as FP  # noqa: E402

OUT = GEN / "out"
CSV_PATH = GEN / "placement.csv"
MM_TO_MIL = 1 / 0.0254

# ------------------------------------------------------------------ board
BOARD_W, BOARD_H = 110.0, 80.0   # pcbsetup reads these
CORNER_R = 3.0                   # Raspberry Pi drawing: all corners R3
EDGE_CLR = 0.5                   # courtyard to outline, parts not on an edge
# The Raspberry Pi rectangle (85 x 56) is the board's upper-left part: the board grows
# 25 mm to the right and 24 mm down, so the holes and the 40-pin header keep their
# positions and a HAT still fits. PI_Y is the Pi frame's bottom edge on this board.
PI_Y = BOARD_H - 56.0
# Raspberry Pi 4 mechanical drawing and HAT mechanical spec (official PDFs): holes 3.5
# from the left and bottom, 58 and 49 apart; header centred 29 from the hole column,
# on the upper hole row. A HAT covers x < 65, y > PI_Y: tall parts stay outside that.
HOLES = {"H1600": (3.5, PI_Y + 3.5), "H1601": (61.5, PI_Y + 3.5),
         "H1602": (3.5, PI_Y + 52.5), "H1603": (61.5, PI_Y + 52.5)}
HEADER = (32.5, PI_Y + 52.5)

# RJ45 and USB-A stick out past the board edge by this much (the Pi's are about 3 mm,
# read from the same drawing). Their holes and pads stay well inside the board.
OVERHANG = 3.0

U1_XY = (52.0, 45.0)             # SiP centre, near the middle of the board: docs/pcb-placement.md
M2_XY = (70.5, 64.0)             # back side, north-east, card toward +x under the SD socket and audio
# Socket centre line to the standoff hole: 30.06 mm on TI SK-AM62A (reference/2_PROC142A
# IPC-D-356: J2 rows at x -45.6 / +251.6 mil, SH3 at 1286.6 mil). Same contact-row spacing
# as the LOTES socket (7.55 mm). The rows' centre is 1.5 mm above the holes' line, the
# footprint origin 1.355 mm.
M2_STANDOFF_DX = 30.06 - (1.5 - 1.355)
EMMC_XY = (34.0, 42.0)           # J700, back side; the module runs toward -x

# Mechanics fixed by the Raspberry Pi pattern, flagged in placement.csv. Every position is in blocks/ (see blocks.py).
FIXED = {**{d: (x, y, 0, "T") for d, (x, y) in HOLES.items()}, "J1400": (HEADER[0], HEADER[1], 0, "T")}


def keepouts() -> list[tuple]:
    """Rectangles (x1, y1, x2, y2, side, why) kept clear of small parts, shown on the renders."""
    ux, uy = U1_XY
    ex, ey = EMMC_XY
    mx, my = M2_XY
    return [
        # eMMC module, 18 x 13 mm, 1 mm stack: nothing fits under it
        (ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5, "B", "eMMC module"),
        # standoff screw for the M.2 card, through the board
        (mx + M2_STANDOFF_DX - 3.0, my - 3.0, mx + M2_STANDOFF_DX + 3.0, my + 3.0, "TB", "M.2 standoff"),
    ]


def thermal_keepouts(parts, place) -> list[tuple]:
    """Exposed pads take thermal vias; keep the far side clear under them. The TFP410's
    land is 8 x 8 mm (README section 10)."""
    fps = {f.name: f for f in FP.all_footprints()}
    out = []
    for d, (x, y, rot, side) in place.items():
        if d not in parts or parts[d].fp in ("OSD62X-PM_BGA500",):
            continue
        fp = fps[parts[d].fp]
        ox, oy = fp.origin()
        other = "B" if side == "T" else "T"
        for pad in fp.pads:
            if pad.hole or pad.w * pad.h < 2.0 or fp.name.startswith(("IND_", "CP_", "C1206", "DIO_", "SW_", "USB", "HDMI",
                                                                      "RJ45", "M2_", "MICROSD", "JACK", "STANDOFF", "FUSE")):
                continue
            hw, hh = pad.w / 2 + 0.3, pad.h / 2 + 0.3
            if d == "U1000":
                hw = hh = 4.2
            a = xform(pad.x - ox - hw, pad.y - oy - hh, x, y, rot, side)
            b = xform(pad.x - ox + hw, pad.y - oy + hh, x, y, rot, side)
            out.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), other, f"{d} thermal"))
    return out








@dataclass
class Part:
    des: str
    fp: str
    sheet: str
    pads: list = field(default_factory=list)      # (x, y, net, is_tht) local, origin at body centre
    crt: tuple = ()                               # courtyard, local
    holes: list = field(default_factory=list)     # (x, y, r) through-holes: block the other side


def _natural(d):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", d)]




def load_parts() -> tuple[dict, dict]:
    fps = {f.name: f for f in FP.all_footprints()}
    d2fp, sheet = {}, {}
    with open(OUT / "footprint_usage.csv", newline="") as f:
        for r in csv.DictReader(f):
            for d in r["designators"].split():
                d2fp[d] = r["footprint"]
    with open(OUT / "schematic_bom.csv", newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            sheet.setdefault(r["designator"], r["sheet"])
    pin_net = {}
    nets = {}
    with open(OUT / "netlist.csv", newline="") as f:
        for r in csv.DictReader(f):
            nodes = r["nodes"].split()
            nets[r["net"]] = nodes
            for nd in nodes:
                d, p = nd.split(".", 1)
                pin_net[(d, p)] = r["net"]
    parts = {}
    for d, name in d2fp.items():
        fp = fps[name]
        ox, oy = fp.origin()
        x1, y1, x2, y2 = fp.courtyard_rect()
        pt = Part(d, name, sheet.get(d, ""), crt=(x1 - ox, y1 - oy, x2 - ox, y2 - oy))
        for pad in fp.pads:
            net = pin_net.get((d, pad.name)) if pad.name else None
            pt.pads.append((pad.x - ox, pad.y - oy, net, bool(pad.hole), pad.name))
            if pad.hole:
                bx1, by1, bx2, by2 = pad.bbox()
                pt.holes.append((bx1 - ox, by1 - oy, bx2 - ox, by2 - oy))
        parts[d] = pt
    return parts, nets


def xform(lx, ly, x, y, rot, side):
    if side == "B":
        lx = -lx
    if rot == 0:
        return x + lx, y + ly
    if rot == 90:
        return x - ly, y + lx
    if rot == 180:
        return x - lx, y - ly
    if rot == 270:
        return x + ly, y - lx
    a = math.radians(rot)
    return x + lx * math.cos(a) - ly * math.sin(a), y + lx * math.sin(a) + ly * math.cos(a)


def crt_rect(pt: Part, x, y, rot, side, grow=0.0):
    a = xform(pt.crt[0], pt.crt[1], x, y, rot, side)
    b = xform(pt.crt[2], pt.crt[3], x, y, rot, side)
    return (min(a[0], b[0]) - grow, min(a[1], b[1]) - grow, max(a[0], b[0]) + grow, max(a[1], b[1]) + grow)


# Rails with many pads that are still local to one block: scored as wires, not as planes
LOCAL_NETS = {"VBUS_USBC", "VCC_3V3_DBG", "VSYS_PD", "VDD_1V0_PHY", "VDDSHV5_SD"}


def is_rail(net, nodes):
    return net == "GND" or (len(nodes) > 12 and net not in LOCAL_NETS)
















def read_csv():
    out = {}
    if CSV_PATH.exists():
        with open(CSV_PATH, newline="") as f:
            for r in csv.DictReader(f):
                out[r["designator"]] = (float(r["x_mm"]), float(r["y_mm"]), int(float(r["rotation"])), r["side"])
    return out


def write_csv(place):
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["designator", "x_mm", "y_mm", "rotation", "side", "fixed"])
        for d in sorted(place, key=_natural):
            x, y, rot, side = place[d]
            w.writerow([d, f"{x:.3f}", f"{y:.3f}", rot, side, int(d in FIXED)])


# ---------------------------------------------------------------- annealer
class Grid:
    """Per-side hash of placed courtyards."""

    def __init__(self, cell=4.0):
        self.cell = cell
        self.g = {"T": {}, "B": {}}
        self.r = {}

    def _cells(self, r):
        c = self.cell
        for i in range(int(r[0] // c), int(r[2] // c) + 1):
            for j in range(int(r[1] // c), int(r[3] // c) + 1):
                yield i, j

    def add(self, key, side, r):
        self.r[key] = (side, r)
        g = self.g[side]
        for ij in self._cells(r):
            g.setdefault(ij, set()).add(key)

    def remove(self, key):
        side, r = self.r.pop(key)
        g = self.g[side]
        for ij in self._cells(r):
            g[ij].discard(key)

    def hits(self, side, r, ignore=()):
        g = self.g[side]
        seen = set()
        for ij in self._cells(r):
            for k in g.get(ij, ()):
                if k in seen or k in ignore:
                    continue
                seen.add(k)
                o = self.r[k][1]
                if r[0] < o[2] - 1e-6 and o[0] < r[2] - 1e-6 and r[1] < o[3] - 1e-6 and o[1] < r[3] - 1e-6:
                    return k
        return None






# ----------------------------------------------------------------- checks
def outline_ok(x, y):
    """True if (x, y) is inside the rounded-rectangle outline."""
    r = CORNER_R
    if not (0 <= x <= BOARD_W and 0 <= y <= BOARD_H):
        return False
    cx = min(max(x, r), BOARD_W - r)
    cy = min(max(y, r), BOARD_H - r)
    return math.hypot(x - cx, y - cy) <= r + 1e-9


def check(parts, place, quiet=False):
    probs = []
    missing = [d for d in parts if d not in place]
    if missing:
        probs.append("not placed: " + " ".join(sorted(missing, key=_natural)))
    extra = [d for d in place if d not in parts]
    if extra:
        probs.append("placed but not in the netlist: " + " ".join(extra))
    grid = Grid()
    overlaps = []
    for d, (x, y, rot, side) in sorted(place.items(), key=lambda kv: _natural(kv[0])):
        if d not in parts:
            continue
        r = crt_rect(parts[d], x, y, rot, side)
        hit = True
        ignore = set()
        while hit:
            hit = grid.hits(side, r, ignore=ignore)
            if hit:
                overlaps.append((d, hit[1]))
                ignore.add(hit)
        grid.add(("P", d), side, r)
    probs += [f"courtyard overlap: {a} {b}" for a, b in overlaps]
    # copper and holes against the outline and THT holes against the other side
    holes = {"T": [], "B": []}
    for d, (x, y, rot, side) in place.items():
        if d not in parts:
            continue
        pt = parts[d]
        for hole in pt.holes:
            a = xform(hole[0], hole[1], x, y, rot, side)
            b = xform(hole[2], hole[3], x, y, rot, side)
            holes["B" if side == "T" else "T"].append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), d))
    mx, my = M2_XY
    ex, ey = EMMC_XY
    plugged = (("M.2 card", (mx - 1.5, my - 11.0, mx + M2_STANDOFF_DX + 1.75, my + 11.0), ("J1300", "H1300")),
               ("eMMC module", (ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5), ("J700", "J701")))
    for hx1, hy1, hx2, hy2, od in holes["B"]:
        for what, box, own in plugged:
            if od not in own and hx1 < box[2] and box[0] < hx2 and hy1 < box[3] and box[1] < hy2:
                probs.append(f"through-hole pad of {od} under the {what} on the back")
    for d, (x, y, rot, side) in place.items():
        if d not in parts:
            continue
        pt = parts[d]
        r = crt_rect(pt, x, y, rot, side)
        for hx1, hy1, hx2, hy2, od in holes[side]:
            if od != d and r[0] < hx2 and hx1 < r[2] and r[1] < hy2 and hy1 < r[3]:
                probs.append(f"{d} ({side}) courtyard over a through-hole pad of {od}")
        for p in pt.pads:
            px, py = xform(p[0], p[1], x, y, rot, side)
            if not outline_ok(px, py):
                probs.append(f"{d} pad {p[4]} at ({px:.2f}, {py:.2f}) is outside the outline")
    return probs




# The ComponentClearance rule is 10 mil = 0.254 mm. Altium measures to the courtyard's drawn line, which is
# 0.05 mm wide, so a model gap of 0.30 mm reads as 9.84 mil and fails.
CLEAR_GAP = 0.32


def close_pairs(parts, place, gap=CLEAR_GAP):
    """Same-side pairs whose courtyards are closer than gap (mm), with the gap."""
    rects = {d: (place[d][3], crt_rect(parts[d], *place[d])) for d in place if d in parts}
    out = []
    names = sorted(rects, key=_natural)
    for i, a in enumerate(names):
        sa, ra = rects[a]
        for b in names[i + 1:]:
            sb, rb = rects[b]
            if sa != sb:
                continue
            dx = max(ra[0] - rb[2], rb[0] - ra[2], 0.0)
            dy = max(ra[1] - rb[3], rb[1] - ra[3], 0.0)
            if dx == 0 and dy == 0:
                g = max(ra[0] - rb[2], rb[0] - ra[2], ra[1] - rb[3], rb[1] - ra[3])
            else:
                g = math.hypot(dx, dy)
            if g < gap - 1e-6:
                out.append((round(g, 3), a, b))
    return out




def area_budget(parts):
    """Courtyard totals for docs/pcb-placement.md."""
    total = sum((p.crt[2] - p.crt[0]) * (p.crt[3] - p.crt[1]) for p in parts.values())
    # a through-hole part also blocks the other side where its tails come through
    tht = 0.0
    for name in ("J1400", "J800", "J900", "H1600", "H1601", "H1602", "H1603"):
        p = parts[name]
        tht += (p.crt[2] - p.crt[0]) * (p.crt[3] - p.crt[1])
    return total, tht


# ----------------------------------------------------------------- render
SHEET_COLOR = {
    "USB-C power input and main converters": (214, 90, 60), "PMIC and power switches": (230, 140, 50),
    "SiP power": (60, 130, 200), "SiP GND/NC": (60, 130, 200), "SiP IO": (60, 130, 200),
    "Clocks, reset and boot": (140, 90, 200), "Storage: eMMC module and microSD": (50, 160, 120),
    "Gigabit Ethernet PHY": (200, 170, 50), "USB: device port, hub, USB-A host ports": (90, 180, 210),
    "HDMI output (TFP410)": (210, 90, 160), "Audio codec": (120, 190, 80), "Camera FPC": (170, 170, 170),
    "M.2 Key-E Wi-Fi / Bluetooth": (90, 110, 230), "40-pin expansion header": (150, 120, 90),
    "Debug USB-UART and JTAG": (110, 200, 170), "Board ID, sensors, LEDs, mounting": (190, 190, 120),
}


def render(parts, nets, place, path_top, path_bot, ppm=11, ratsnest=True):
    from PIL import Image, ImageDraw
    m = 8
    W = int((BOARD_W + 2 * m) * ppm)
    H = int((BOARD_H + 2 * m) * ppm)
    X = lambda x: (x + m) * ppm
    Y = lambda y: (BOARD_H - y + m) * ppm
    # one image per side, viewed from the top so the two line up
    for side, path in (("T", path_top), ("B", path_bot)):
        img = Image.new("RGB", (W, H), (250, 250, 250))
        dr = ImageDraw.Draw(img)
        dr.rounded_rectangle((X(0), Y(BOARD_H), X(BOARD_W), Y(0)), radius=CORNER_R * ppm, outline=(0, 0, 0), width=2,
                             fill=(255, 255, 255))
        for k in keepouts():
            if side in k[4]:
                dr.rectangle((X(k[0]), Y(k[3]), X(k[2]), Y(k[1])), fill=(245, 236, 236), outline=(230, 190, 190))
        # M.2 card outline on the back, and eMMC module
        if side == "B":
            mx, my = M2_XY
            dr.rectangle((X(mx - 1.5), Y(my + 11), X(mx + M2_STANDOFF_DX + 1.75), Y(my - 11)), outline=(120, 120, 240))
        for d, (x, y, rot, s) in place.items():
            if d not in parts:
                continue
            pt = parts[d]
            r = crt_rect(pt, x, y, rot, s)
            col = SHEET_COLOR.get(pt.sheet, (160, 160, 160))
            if s == side:
                light = tuple(int(c * 0.35 + 255 * 0.65) for c in col)
                dr.rectangle((X(r[0]), Y(r[3]), X(r[2]), Y(r[1])), fill=light, outline=col)
            for p in pt.pads:
                px, py = xform(p[0], p[1], x, y, rot, s)
                if s == side or p[3]:
                    rad = 0.28 if pt.fp != "OSD62X-PM_BGA500" else 0.11
                    pc = (60, 60, 60) if s == side else (170, 170, 170)
                    dr.ellipse((X(px - rad), Y(py + rad), X(px + rad), Y(py - rad)), fill=pc)
            if s == side and (r[2] - r[0]) * (r[3] - r[1]) > 14:
                dr.text((X(r[0]) + 2, Y(r[3]) + 1), d, fill=(0, 0, 0))
        if ratsnest:
            for net, nodes in nets.items():
                if is_rail(net, nodes) or net.startswith("NC"):
                    continue
                pts = []
                for nd in nodes:
                    od, pin = nd.split(".", 1)
                    if od in place and od in parts:
                        pad = next((p for p in parts[od].pads if p[4] == pin), None)
                        if pad:
                            pts.append((*xform(pad[0], pad[1], *place[od]), place[od][3]))
                if len(pts) < 2:
                    continue
                # Prim's MST
                done = [pts[0]]
                rest = pts[1:]
                while rest:
                    a, b = min(((a, b) for a in done for b in rest), key=lambda ab: math.dist(ab[0][:2], ab[1][:2]))
                    if a[2] == side or b[2] == side:
                        dr.line((X(a[0]), Y(a[1]), X(b[0]), Y(b[1])), fill=(120, 120, 200), width=1)
                    done.append(b)
                    rest.remove(b)
        img.save(path)


def congestion(parts, nets, place, cell=2.0):
    """Routing demand against capacity, RUDY style. Every signal net spreads its
    half-perimeter wire over its bounding box. Capacity: L1, L3, L6 and L8 at a 0.30 mm track
    pitch (0.15 / 0.15), 50 % usable. Returns totals and the worst cells."""
    nx, ny = int(BOARD_W / cell), int(BOARD_H / cell)
    grid = [[0.0] * ny for _ in range(nx)]
    total_hpwl = 0.0
    total_mst = 0.0
    for net, nodes in nets.items():
        if is_rail(net, nodes) or net.startswith("NC"):
            continue
        pts = []
        for nd in nodes:
            od, pin = nd.split(".", 1)
            if od in place and od in parts:
                pad = next((q for q in parts[od].pads if q[4] == pin), None)
                if pad:
                    pts.append(xform(pad[0], pad[1], *place[od]))
        if len(pts) < 2:
            continue
        x1, x2 = min(q[0] for q in pts), max(q[0] for q in pts)
        y1, y2 = min(q[1] for q in pts), max(q[1] for q in pts)
        hp = (x2 - x1) + (y2 - y1)
        total_hpwl += hp
        done, rest = [pts[0]], pts[1:]
        while rest:
            d, b = min(((abs(a[0] - q[0]) + abs(a[1] - q[1]), q) for a in done for q in rest), key=lambda t: t[0])
            total_mst += d
            done.append(b)
            rest.remove(b)
        w, h = max(x2 - x1, cell), max(y2 - y1, cell)
        dens = (w + h) / (w * h)                 # mm of wire per mm2 inside the box
        for i in range(int(x1 / cell), min(nx, int((x1 + w) / cell) + 1)):
            for j in range(int(y1 / cell), min(ny, int((y1 + h) / cell) + 1)):
                grid[i][j] += dens
    cap = 4 * (1 / 0.30) * 0.5                   # mm of track per mm2: 6.67
    cells = sorted(((grid[i][j] / cap, (i + 0.5) * cell, (j + 0.5) * cell) for i in range(nx) for j in range(ny)),
                   reverse=True)
    area = BOARD_W * BOARD_H
    over = sum(1 for c in cells if c[0] > 1.0) * cell * cell
    return {"signal_mst_mm": total_mst, "signal_hpwl_mm": total_hpwl, "capacity_mm": area * cap,
            "demand_vs_capacity": total_mst * 1.3 / (area * cap), "peak": cells[0], "over_100pct_mm2": over,
            "top5": cells[:5]}


def report(parts, nets, place):
    """Distances the brief names, in mm, pad to pad or part to part."""
    def pad(d, name):
        q = next(q for q in parts[d].pads if q[4] == name)
        return xform(q[0], q[1], *place[d])

    def pads_on(d, net):
        return [xform(q[0], q[1], *place[d]) for q in parts[d].pads if q[2] == net]

    def closest(a, b):
        return min(math.dist(p, q) for p in a for q in b)

    def edge_gap(a, b):
        ra, rb = crt_rect(parts[a], *place[a]), crt_rect(parts[b], *place[b])
        dx = max(ra[0] - rb[2], rb[0] - ra[2], 0)
        dy = max(ra[1] - rb[3], rb[1] - ra[3], 0)
        return math.hypot(dx, dy)

    print("25 MHz: U600 output to R600", round(closest(pads_on("U600", "OSC25M_SRC"), pads_on("R600", "OSC25M_SRC")), 2),
          "| R600 to ball G1", round(closest(pads_on("R600", "OSC_25M"), [pad("U1", "G1")]), 2))
    print("32 kHz: Y600 to balls H1/H2", round(closest(pads_on("Y600", "LFOSC_XI"), [pad("U1", "H1")]), 2))
    noisy = ["L100", "L101", "L200", "L201", "L202", "U101", "U102", "U200"]
    for q in ("U1100", "Y600", "U600", "Y1100"):
        d = min(noisy, key=lambda n: edge_gap(q, n))
        print(f"{q}: nearest switcher part {d}, gap {edge_gap(q, d):.1f}")
    for sw, ind, net in (("U101", "L100", "LM_SW"), ("U102", "L101", "BB_L1"), ("U102", "L101", "BB_L2"),
                         ("U200", "L200", "PMIC_LX_B1"), ("U200", "L201", "PMIC_LX_B2"), ("U200", "L202", "PMIC_LX_B3")):
        print(f"{net}: {closest(pads_on(sw, net), pads_on(ind, net)):.2f}")
    # decoupling caps of the SiP: distance from the cap's rail pad to the nearest ball of that rail
    dist = []
    for d, pt in parts.items():
        if pt.sheet != "SiP power" or not d.startswith("C"):
            continue
        for q in pt.pads:
            if q[2] and q[2] != "GND":
                balls = [nd.split(".", 1)[1] for nd in nets[q[2]] if nd.startswith("U1.")]
                if balls:
                    dist.append(min(math.dist(xform(q[0], q[1], *place[d]), pad("U1", b)) for b in balls))
    dist.sort()
    print(f"SiP caps: {len(dist)}, ball distance median {dist[len(dist) // 2]:.1f}, worst {dist[-1]:.1f}")
    sides = {"T": 0, "B": 0}
    area = {"T": 0.0, "B": 0.0}
    for d, v in place.items():
        if d in parts:
            sides[v[3]] += 1
            r = crt_rect(parts[d], *v)
            area[v[3]] += (r[2] - r[0]) * (r[3] - r[1])
    print("parts per side", sides, "courtyard mm2 per side", {k: round(v) for k, v in area.items()})


def export(parts, place, batch=120):
    rows = []
    for d, (x, y, rot, side) in sorted(place.items(), key=lambda kv: _natural(kv[0])):
        if d not in parts:
            continue
        # Measured on AD26 through place_components: a bottom part is mirrored in y and then
        # rotated, the same as this file's "mirror x, rotate" with 180 degrees added.
        rows.append({"designator": d, "x": round(x * MM_TO_MIL, 3), "y": round(y * MM_TO_MIL, 3),
                     "rotation": rot if side == "T" else (rot + 180) % 360,
                     "layer": "top" if side == "T" else "bottom"})
    batches = [rows[i:i + batch] for i in range(0, len(rows), batch)]
    (OUT / "place_batches.json").write_text(json.dumps(batches))
    return len(rows), len(batches)



# ------------------------------------------------------------ apply in Altium
BRIDGE = Path("C:/Users/Public/altium_mcp")
PCB_PATH = GEN.parent / "PCB.PcbDoc"
MIL = 10000
BOARD_X0, BOARD_Y0 = 1000 * MIL, 1000 * MIL      # as pcbsetup.BOARD_X0


def coord(v_mm):
    return round(v_mm / 0.0254 * MIL)


def run_place(proc, timeout=180):
    """Run ApePlace>proc in the running Altium; (ok, result)."""
    import subprocess
    import build
    log, res = BRIDGE / "ape_log.txt", BRIDGE / "ape_result.json"
    for f in (log, res):
        if f.exists():
            f.unlink()
    prj = GEN / "altium" / "ApePlace.PrjScr"
    subprocess.Popen(f'"{build.altium_exe()}" -RScriptingSystem:RunScript(ProjectName="{prj}"'
                     f'^|ProcName="ApePlace>{proc}")', shell=True)
    start = time.time()
    while time.time() - start < timeout:
        # every ApePlace procedure logs as it starts: no log means Altium's script engine is stuck, not busy
        if time.time() - start > 30 and not log.exists() and not res.exists():
            return False, {"error": "the script did not start within 30 s: Altium's script engine is stuck. "
                                    "Run: python build.py unwedge"}
        if res.exists():
            time.sleep(0.3)
            data = json.loads(res.read_text(encoding="cp1252", errors="replace"))
            return bool(data.get("success")), data
        time.sleep(0.5)
    last = log.read_text(encoding="cp1252", errors="replace").splitlines()[-1:] if log.exists() else []
    return False, {"error": f"no result after {timeout} s", "last_log_line": last, "dialogs": build.altium_dialogs()}


def board_spec() -> str:
    """Outline with R3 corners, and the outlines of what plugs in later."""
    X = lambda v: BOARD_X0 + coord(v)
    Y = lambda v: BOARD_Y0 + coord(v)
    lines = [str(PCB_PATH),
             f"OUTLINE|{BOARD_X0}|{BOARD_Y0}|{coord(BOARD_W)}|{coord(BOARD_H)}|{coord(CORNER_R)}"]
    w = coord(0.1)

    def box(x1, y1, x2, y2, label):
        pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
        for a, b in zip(pts, pts[1:]):
            lines.append(f"NOTE_TRACK|{X(a[0])}|{Y(a[1])}|{X(b[0])}|{Y(b[1])}|{w}")
        lines.append(f"NOTE_TEXT|{X(x1 + 0.5)}|{Y(y1 + 0.5)}|{coord(1.0)}|{coord(0.1)}|{label}")

    mx, my = M2_XY
    box(mx - 1.5, my - 11, mx + M2_STANDOFF_DX + 1.75, my + 11, "BACK: M.2 2230 card, 1.5 mm under it")
    ex, ey = EMMC_XY
    box(ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5, "BACK: eMMC module, nothing under it")
    return "\n".join(lines) + "\n"


def apply_board():
    (BRIDGE / "ape_place_board.txt").write_text(board_spec(), encoding="cp1252", errors="replace")
    return run_place("PlaceBoard")


def apply_parts(parts, place, batch=150):
    """Move every part with the MCP's place_components, one undo step per batch."""
    import mcp_client
    n, _ = export(parts, place, batch=batch)
    batches = json.loads((OUT / "place_batches.json").read_text())
    missing = []
    placed = 0
    t0 = time.time()
    for i, rows in enumerate(batches):
        raw = mcp_client.call("place_components", {"placements": rows}, timeout=280)
        data = json.loads(raw)
        placed += data.get("placed_count") or data.get("placed") or data.get("count") or len(rows)
        missing += data.get("missing_designators", []) or []
        print(f"  batch {i + 1}/{len(batches)}: placed {placed}, {time.time() - t0:.0f} s", flush=True)
    return placed, missing


def main(argv):
    parts, nets = load_parts()
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        place = read_csv()
        probs = check(parts, place)
        print("\n".join(probs) if probs else "no problems")
        print(f"{len(place)} placed of {len(parts)}, {sum(1 for v in place.values() if v[3] == 'B')} on the bottom")
    elif cmd == "render":
        place = read_csv()
        render(parts, nets, place, OUT / "place_top.png", OUT / "place_bot.png")
    elif cmd == "export":
        place = read_csv()
        print(export(parts, place))
    elif cmd == "board":
        print(apply_board())
    elif cmd == "apply":
        place = read_csv()
        probs = check(parts, place)
        if probs:
            print("\n".join(probs))
            return 1
        placed, missing = apply_parts(parts, place)
        print(f"placed {placed}; not on the board: {' '.join(missing) or 'none'}")
        print(run_place("PlaceRefresh"))          # rebuilds the ratsnest and saves
    elif cmd == "refresh":
        print(run_place("PlaceRefresh"))
    elif cmd == "budget":
        total, tht = area_budget(parts)
        print(f"courtyards {total:.0f} mm2, of which THT that also blocks the far side {tht:.0f} mm2")
        print(congestion(parts, nets, read_csv()))
        report(parts, nets, read_csv())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
