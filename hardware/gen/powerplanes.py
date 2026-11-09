"""APE-SBC power and ground copper, computed offline and applied to PCB.PcbDoc.

No autorouter: everything here is scripted and deterministic. For a given placement.csv:

1. fan-out: a via and a short stub for each power and GND pad. SiP balls use one via between
   four balls (Octavo "configuration 1"), on a checkerboard of sites so that planes keep copper
   between neighbouring vias. Large pads take vias in the pad (JLC fills and caps them for free).
2. regions: each rail gets connected copper on the plane layers, by shortest paths on a 0.25 mm
   grid, with its neighbours kept one cell away. Spare copper then goes to the nearest rail,
   faster for the rails that carry more current.
3. polygons: each region's outline becomes one Altium polygon. GND gets L2 and L7 whole.

    python powerplanes.py plan [1|2]     regions on fanout.py's fan-out, report, out/plane_*.png
    python powerplanes.py spec [N]       the same, and writes the spec for Altium without running it
    python powerplanes.py apply [N]      writes the objects to the PcbDoc (take the Altium lock)

Frame: mm, origin at the board's lower-left corner. docs/pcb-placement.md has the reasoning.
"""
from __future__ import annotations

import heapq
import json
import math
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

import footprints as FP
import pcbsetup as S
import placement as P

OUT = P.OUT
GRID = 0.25
NX = int(P.BOARD_W / GRID) + 1
NY = int(P.BOARD_H / GRID) + 1
EDGE = 0.55                     # plane copper to the outline
CLR = 0.12                      # new copper to other nets on the outer layers (rule 0.10 mm)
SIP_VIA = (0.15, 0.25)          # hole, diameter: VIA_BGA, JLC minimum
VIAS = ((0.30, 0.50), (0.20, 0.40), (0.20, 0.35))    # Via_PWR preferred, then down to the smallest it allows
SIP_ANTI = 0.275                # JLC inner layer: hole to copper 0.20 mm
HOP_VIA = (0.30, 0.50)          # hole, diameter: Via_PWR preferred, for a rail changing plane
HOP_COST = 40.0                 # a new via is worth 10 mm of plane path
OFF_PLANE_COST = 1.2            # a step on the rail's other plane
THIN_W = 0.15                   # W_PWR minimum; also inside W_SiP's range
THIN_W_HI = 0.20                # W_PWR_HI minimum, outside the SiP's room
MIN_PATCH = 40                  # cells: about 2.5 mm2
MAX_L8_LINK = 25.0              # mm: a longer thin link goes on an inner layer, away from the parts on the back
THIN_ROW_COST = 8.0             # on L3 and L6, what a step through the SiP's signal rows costs
ANTI_CLR = 0.20                 # polygon to via pad, Clr_InnerPour_Hole
PLANES_2 = ("L4_PWR", "L5_PWR")
RS = 1.72e-5 / 0.0152 * (1 + 0.0039 * 40)   # ohm per square, 0.0152 mm copper, 60 C

# Rail current in A: docs/research/bom/power.md, SK budget. Others get SMALL.
SMALL = 0.05
CURRENT = {"VCC_3V3_MAIN": 5.3, "VCC_3V3_SYS": 2.9, "VDD_CORE_0V85": 2.7, "VSYS_PD": 2.3, "VBUS_USBC": 3.0,
           "VCC_5V0": 1.6, "VDD_1V8": 1.2, "VDDS_DDR_1V2": 0.9, "VBUS_USBA1": 0.5, "VBUS_USBA2": 0.5,
           "VDDR_CORE_0V85": 0.5, "VDD_1V0_PHY": 0.22, "VDDA_1V8": 0.2, "VDD_SD_3V3": 0.2, "VDD_1V8_M2": 0.3,
           "VDDSHV0": 0.2, "VDDSHV1": 0.2, "VDDSHV2": 0.2, "VDDSHV3": 0.2, "VDDSHV4": 0.2, "VDDSHV5_SD": 0.05,
           "VDDSHV6": 0.2, "VDDSHV_MCU": 0.1, "VDDSHV_CANUART": 0.05, "VCC_3V3_TFP_DVDD": 0.1,
           "VCC_3V3_TFP_TVDD": 0.1, "VCC_3V3_TFP_PVDD": 0.05, "VDDA_2V5_PHY": 0.2, "VCC_3V3_DBG": 0.2,
           "VDD_1V8_DBG": 0.05, "VBUS_DBG": 0.2, "VCC_3V3_CAM": 0.2, "VDDA_3V3_AUD": 0.05}
# Rails that also get spare copper on the other plane, in parallel through their vias
DUAL = {"VDD_CORE_0V85"}
# Source of the IR-drop estimates: the pad the rail's current comes from
SOURCE = {"VDD_CORE_0V85": "L200.2", "VDDS_DDR_1V2": "L202.2"}
# Rails routed first and then widened by this many cells: the most current, the tightest budget
TRUNKS = {"VDD_CORE_0V85": 14, "VDDS_DDR_1V2": 3}
# Small rails that have to cross the board: routed early, or they end up as long thin links on a signal layer
LONG_RAILS = {"VDD_SDIO_LDO1", "DDR4_VPP_2V5", "VDDR_CORE_0V85"}
# Entries into the SiP's power block, held for these rails before anything else routes (x1, y1, x2, y2 in
# mm from the SiP's centre). The balls there are no-connects, so nothing else needs the space.
CORRIDORS = {"VDD_CORE_0V85": [("L4_PWR", (-6.5, 0.0, -1.4, 1.6)), ("L4_PWR", (-0.6, -3.5, 2.2, -0.8))],
             "VDDS_DDR_1V2": [("L5_PWR", (-4.4, -4.5, -2.5, -2.0))]}
# IO banks in the cell of GND balls at the SiP's east side: the hardest rails to get out
WALLED = {"VDDSHV0", "VDDSHV1", "VDDSHV2", "VDDSHV3", "VDDSHV5_SD", "VDDSHV6"}
# Switch nodes stay on the surface: short loops, no via
SURFACE_ONLY = {"LM_SW", "BB_L1", "BB_L2", "PMIC_LX_B1", "PMIC_LX_B2", "PMIC_LX_B3"}


L4_RAILS = {"VDD_CORE_0V85", "VDDR_CORE_0V85", "VDD_1V8", "VCC_5V0", "VDD_1V0_PHY", "VDDA_2V5_PHY",
            "VDD_1V8_DBG", "VDD_1V8_M2", "VDD_2V5", "VDD_LDO2"}


def plane_of(net):
    """L4: the core and DDR rails, which take the free west side of the SiP, with the rails that share
    no pins with the 3.3 V family. L5: 3.3 V, the IO banks and the small analogue rails at the SiP."""
    return "L4_PWR" if net in L4_RAILS else "L5_PWR"


NB8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]


# ------------------------------------------------------------------ pads
class Pad:
    __slots__ = ("ref", "name", "net", "side", "x", "y", "hw", "hh", "hole", "round", "tht")

    def __repr__(self):
        return f"{self.ref}.{self.name}"


def load_pads(parts, place):
    fps = {f.name: f for f in FP.all_footprints()}
    pads = []
    for d, pt in parts.items():
        if d not in place:
            continue
        x, y, rot, side = place[d]
        fp = fps[pt.fp]
        for lp, fpad in zip(pt.pads, fp.pads):
            p = Pad()
            p.ref, p.name, p.net = d, lp[4], lp[2]
            p.side = side
            p.x, p.y = P.xform(lp[0], lp[1], x, y, rot, side)
            w, h = fpad.w, fpad.h
            if (round(rot + fpad.rot) % 180) == 90:
                w, h = h, w
            elif round(rot + fpad.rot) % 90:
                w = h = max(w, h)
            p.hw, p.hh = w / 2, h / 2
            p.hole = fpad.hole
            p.tht = bool(fpad.hole)
            p.round = fpad.shape == "round"
            pads.append(p)
    return pads


class Copper:
    """Outer-layer obstacles: pads, vias and stubs in a 1 mm hash."""

    def __init__(self):
        self.h = defaultdict(list)

    def _cells(self, x1, y1, x2, y2):
        for i in range(int(x1 // 1), int(x2 // 1) + 1):
            for j in range(int(y1 // 1), int(y2 // 1) + 1):
                yield i, j

    def add(self, kind, layers, net, rect, seg=None, ref=None):
        item = (kind, layers, net, rect, seg, ref)
        for c in self._cells(*rect):
            self.h[c].append(item)

    def near(self, x1, y1, x2, y2):
        seen = set()
        for c in self._cells(x1, y1, x2, y2):
            for it in self.h.get(c, ()):
                if id(it) not in seen:
                    seen.add(id(it))
                    yield it


def point_gap(x, y, rc, seg):
    """Distance from a point to an obstacle: to the centre line less half the width for a stub, else to
    the rectangle."""
    if seg:
        ax, ay, bx, by, w = seg
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - ax - t * dx, y - ay - t * dy) - w / 2
    gx = max(rc[0] - x, 0, x - rc[2])
    gy = max(rc[1] - y, 0, y - rc[3])
    return math.hypot(gx, gy)


def seg_rect_gap(ax, ay, bx, by, r):
    """Distance from segment a-b to rectangle r = (x1, y1, x2, y2); 0 inside."""
    # sample: stubs are short, so 11 points are enough at this scale
    n = max(2, int(math.hypot(bx - ax, by - ay) / 0.05) + 1)
    best = 1e9
    for k in range(n + 1):
        t = k / n
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        dx = max(r[0] - px, 0, px - r[2])
        dy = max(r[1] - py, 0, py - r[3])
        best = min(best, math.hypot(dx, dy))
    return best


def seg_seg_gap(a, b):
    ax, ay, bx, by = a
    cx, cy, dx, dy = b
    n = max(2, int(math.hypot(bx - ax, by - ay) / 0.05) + 1)
    m = max(2, int(math.hypot(dx - cx, dy - cy) / 0.05) + 1)
    best = 1e9
    for k in range(n + 1):
        t = k / n
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        for l in range(m + 1):
            u = l / m
            qx, qy = cx + (dx - cx) * u, cy + (dy - cy) * u
            best = min(best, math.hypot(px - qx, py - qy))
    return best


# ------------------------------------------------------------------ fan-out
class Plan:
    def __init__(self):
        self.vias = []       # (x, y, hole, dia, net, how)
        self.stubs = []      # (layer "T"/"B", x1, y1, x2, y2, width, net)
        self.failed = []     # pads with no connection
        self.by_net = defaultdict(list)


def fanout_sip(parts, place, plan, cu, power, usable=None, signals=(), banned=None, exempt=()):
    """One via per power and GND ball, on the even sites of the 0.5 mm site lattice wherever possible.

    usable: {ball: its sites, best first}, for the balls that have a choice to make. signals: the inner signal balls, which
    get a site here, in the same matching, but no copper: the result's "signal_sites" says where they go. banned(x, y): sites
    to stay off unless a ball has nothing else. A GND ball with no site of its own shares a GND via beside it."""
    u = parts["U1"]
    balls = {}
    for q in u.pads:
        x, y = P.xform(q[0], q[1], *place["U1"])
        balls[q[4]] = (round(x, 3), round(y, 3), q[2])

    def sites(x, y):
        out = []
        for dx in (-0.25, 0.25):
            for dy in (-0.25, 0.25):
                sx, sy = round(x + dx, 3), round(y + dy, 3)
                even = (round(sx / 0.5) + round(sy / 0.5)) % 2 == 0
                out.append(((not even, abs(sx - place["U1"][0]) + abs(sy - place["U1"][1])), sx, sy))
        return [(s[1], s[2]) for s in sorted(out)]

    want = sorted((b for b, v in balls.items() if v[2] == "GND" or v[2] in power), key=P._natural)
    usable = usable or {}
    banned = banned or (lambda x, y: False)
    signals = set(signals)
    taken = {}
    frozen = set()
    shared = {}
    # A rail with just two neighbouring balls shares one via: those rails are low current, and in the
    # GND-walled cell at the SiP's east side two vias each would box each other in
    by_rail = defaultdict(list)
    for b in want:
        if balls[b][2] != "GND":
            by_rail[balls[b][2]].append(b)
    for net, bs in sorted(by_rail.items()):
        if len(bs) == 2:
            a, c = balls[bs[0]], balls[bs[1]]
            if abs(a[0] - c[0]) + abs(a[1] - c[1]) <= 0.51:
                both = [q for q in sites(a[0], a[1]) if q in sites(c[0], c[1]) and q not in taken]
                if both:
                    taken[both[0]] = bs[0]
                    frozen.add(both[0])
                    shared[bs[1]] = both[0]

    field = (min(v[0] for v in balls.values()), min(v[1] for v in balls.values()),
             max(v[0] for v in balls.values()), max(v[1] for v in balls.values()))

    def in_field(s):
        return field[0] < s[0] < field[2] and field[1] < s[1] < field[3]

    def options(b, last_resort):
        x, y, net = balls[b]
        out = usable[b] if b in usable else sites(x, y)
        if last_resort or b in exempt:
            return out
        return [s for s in out if not banned(s[0], s[1]) and in_field(s)]

    def assign(b, seen, last_resort=False):
        for s in options(b, last_resort):
            if s in seen or s in frozen:
                continue
            seen.add(s)
            if s not in taken or assign(taken[s], seen, last_resort):
                taken[s] = b
                return True
        return False

    # even sites first; the recursion moves earlier balls only among their own sites. Power and signals before GND,
    # because GND can share a via.
    holding = set(taken.values())
    todo = [b for b in want if b not in shared and b not in holding]
    first = [b for b in todo if balls[b][2] != "GND"] + sorted(signals, key=P._natural)
    left = [b for b in first if not assign(b, set())]
    xs = sorted({v[0] for v in balls.values()})
    ys = sorted({v[1] for v in balls.values()})

    def beside(b):
        x, y, net = balls[b]
        return [s for s in sites(x, y) if s in taken and balls[taken[s]][2] == "GND"]

    # One via per GND ball, as the Octavo layout guide has it: they are the SiP's way to the planes and its thermal path. A
    # ball shares only when it has no site of its own, in the field and out of the channels.
    gnd = [b for b in todo if balls[b][2] == "GND"]
    gnd_left = [b for b in gnd if not assign(b, set())]
    fail = []
    for b in left:
        if not assign(b, set(), True):
            fail.append(b)
    for b in gnd_left:
        if beside(b):
            shared[b] = beside(b)[0]
        elif not assign(b, set(), True):
            fail.append(b)
    signal_sites = {b: s for s, b in taken.items() if b in signals}
    for s, b in sorted(taken.items()):
        if b in signals:
            continue
        x, y, net = balls[b]
        plan.vias.append((s[0], s[1], SIP_VIA[0], SIP_VIA[1], net, "sip"))
        plan.stubs.append(("T", x, y, s[0], s[1], 0.10, net))
        plan.by_net[net].append((s[0], s[1], SIP_VIA[1]))
        r = SIP_VIA[1] / 2
        cu.add("via", "TB", net, (s[0] - r, s[1] - r, s[0] + r, s[1] + r))
    for b, s in sorted(shared.items()):
        x, y, net = balls[b]
        plan.stubs.append(("T", x, y, s[0], s[1], 0.10, net))
    # signal balls in from the two outer rows need a site too: check there is one
    inner = [b for b, v in balls.items() if v[2] and v[2] != "GND" and v[2] not in power and not signals
             and min(xs.index(v[0]), len(xs) - 1 - xs.index(v[0]), ys.index(v[1]), len(ys) - 1 - ys.index(v[1])) >= 2]
    free = {}

    def assign2(b, seen):
        x, y, net = balls[b]
        for s in sites(x, y):
            if s in taken or s in seen:
                continue
            seen.add(s)
            if s not in free or assign2(free[s], seen):
                free[s] = b
                return True
        return False

    stuck = [b for b in sorted(inner, key=P._natural) if not assign2(b, set())]
    even = sum(1 for s in taken if (round(s[0] / 0.5) + round(s[1] / 0.5)) % 2 == 0)
    return {"balls": len(want), "vias": len(taken) - len(signal_sites), "shared": len(shared), "on_even_sites": even,
            "no_site": fail, "signal_balls_inner": len(inner), "signal_balls_no_site": stuck, "signal_sites": signal_sites}


def fanout_pads(pads, parts, place, plan, cu, power):
    """Vias and stubs for every other SMD power and GND pad."""
    body = defaultdict(list)                 # same-side no-go: bounding box of each part's pads
    for p in pads:
        body[p.ref].append(p)
    boxes = {}
    for d, ps in body.items():
        boxes[d] = (place[d][3], min(q.x - q.hw for q in ps), min(q.y - q.hh for q in ps),
                    max(q.x + q.hw for q in ps), max(q.y + q.hh for q in ps))
    u1 = P.crt_rect(parts["U1"], *place["U1"])
    box_list = [(d, *b) for d, b in boxes.items() if d != "U1"]
    # bus corridors: a via there takes room on all four signal layers, so it costs 0.7 mm of extra stub
    corridors = [k for k in P.keepouts() if k[5] not in ("U1 fan-out", "eMMC module", "M.2 standoff")]

    def via_ok(x, y, hole, dia, net, own):
        r = dia / 2
        if not P.outline_ok(x, y) or x < 0.6 or y < 0.6 or x > P.BOARD_W - 0.6 or y > P.BOARD_H - 0.6:
            return False
        if u1[0] - 0.1 < x < u1[2] + 0.1 and u1[1] - 0.1 < y < u1[3] + 0.1:
            return False
        m = r + CLR + 0.3
        for kind, layers, onet, rc, seg, ref in cu.near(x - m, y - m, x + m, y + m):
            gap = point_gap(x, y, rc, seg) - r
            if onet != net and gap < CLR:
                return False
            if kind in ("via", "hole") and gap < 0.2:   # hole to hole, roughly
                return False
        for d, side, x1, y1, x2, y2 in box_list:
            if d != own[0] and x1 - 0.02 < x < x2 + 0.02 and y1 - 0.02 < y < y2 + 0.02 and side == own[1]:
                return False
        return True

    def stub_ok(side, x1, y1, x2, y2, w, net):
        m = w / 2 + CLR + 0.3
        rect = (min(x1, x2) - m, min(y1, y2) - m, max(x1, x2) + m, max(y1, y2) + m)
        for kind, layers, onet, rc, seg, ref in cu.near(*rect):
            if onet == net or side not in layers:
                continue
            if seg:
                if seg_seg_gap((x1, y1, x2, y2), seg[:4]) - seg[4] / 2 - w / 2 < CLR:
                    return False
            elif seg_rect_gap(x1, y1, x2, y2, rc) - w / 2 < CLR:
                return False
        return True

    def put_via(x, y, hole, dia, net, how):
        plan.vias.append((round(x, 3), round(y, 3), hole, dia, net, how))
        plan.by_net[net].append((x, y, dia))
        r = dia / 2
        cu.add("via", "TB", net, (x - r, y - r, x + r, y + r))

    def put_stub(side, x1, y1, x2, y2, w, net):
        plan.stubs.append((side, round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3), w, net))
        m = w / 2
        cu.add("stub", side, net, (min(x1, x2) - m, min(y1, y2) - m, max(x1, x2) + m, max(y1, y2) + m),
               seg=(x1, y1, x2, y2, w))

    todo = [p for p in pads if p.ref != "U1" and not p.tht and (p.net == "GND" or p.net in power)
            and p.net not in SURFACE_ONLY]
    # big pads first: they place vias in the pad, which small pads next to them can then reuse
    # then IC and connector pins, which have nowhere else to go, then the two-pin parts
    def rank(p):
        area = 4 * p.hw * p.hh
        if area >= 1.0:
            return (0, -area)
        return (1 if len(body[p.ref]) > 4 else 2, 0.0)

    todo.sort(key=lambda p: (rank(p), P._natural(p.ref), str(p.name)))
    done = 0
    for p in todo:
        area = 4 * p.hw * p.hh
        if area >= 1.0:
            hole, dia = VIAS[0]
            pitch = 1.5 if area > 20 else 1.0
            nx = max(1, int((2 * p.hw - dia) / pitch) + 1)
            ny = max(1, int((2 * p.hh - dia) / pitch) + 1)
            placed = 0
            for i in range(nx):
                for j in range(ny):
                    x = p.x + (i - (nx - 1) / 2) * pitch
                    y = p.y + (j - (ny - 1) / 2) * pitch
                    # the far side must be clear of other nets; the own pad is same-net copper
                    if via_ok(x, y, hole, dia, p.net, (p.ref, p.side)) or _inside_ok(cu, x, y, dia, p):
                        put_via(x, y, hole, dia, p.net, "pad")
                        placed += 1
            if placed:
                done += 1
                continue
        w = max(0.15, min(0.40, 1.6 * min(p.hw, p.hh)))
        # 1. a same-net via already close by
        best = None
        for vx, vy, vd in plan.by_net[p.net]:
            d = math.hypot(vx - p.x, vy - p.y)
            if d <= 1.3 + max(p.hw, p.hh) and stub_ok(p.side, p.x, p.y, vx, vy, w, p.net):
                if best is None or d < best[0]:
                    best = (d, vx, vy)
        if best:
            put_stub(p.side, p.x, p.y, best[1], best[2], w, p.net)
            done += 1
            continue
        # 2. the nearest legal spot, preferring away from the part's own centre
        bx1, by1, bx2, by2 = boxes[p.ref][1:]
        cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
        found = None
        for hole, dia in VIAS:
            cands = []
            reach = 3.0
            n = int(reach / 0.05)
            for i in range(-n, n + 1):
                for j in range(-n, n + 1):
                    x, y = p.x + i * 0.05, p.y + j * 0.05
                    d = math.hypot(i * 0.05, j * 0.05)
                    if d > reach:
                        continue
                    out = (x - p.x) * (p.x - cx) + (y - p.y) * (p.y - cy)
                    busy = any(c[0] < x < c[2] and c[1] < y < c[3] for c in corridors)
                    cands.append((d - 0.3 * (1 if out > 0 else 0) + (0.7 if busy else 0.0), i, j, x, y))
            cands.sort()
            for _, i, j, x, y in cands:
                if via_ok(x, y, hole, dia, p.net, (p.ref, p.side)) and stub_ok(p.side, p.x, p.y, x, y, w, p.net):
                    found = (x, y, hole, dia)
                    break
            if found:
                break
        if found:
            put_via(found[0], found[1], found[2], found[3], p.net, "stub")
            put_stub(p.side, p.x, p.y, found[0], found[1], w, p.net)
            done += 1
            continue
        # 3. out of the pin field first, then to the via: a stub with one bend
        w2 = min(w, 0.15)
        ax, ay = 0.0, 0.0
        if abs(p.x - cx) / max(bx2 - bx1, 0.01) >= abs(p.y - cy) / max(by2 - by1, 0.01):
            ax = 1.0 if p.x >= cx else -1.0
        else:
            ay = 1.0 if p.y >= cy else -1.0
        for e in (0.3, 0.45, 0.6, 0.8, 1.0, 1.3, 1.6):
            ex, ey = p.x + ax * (e + (p.hw if ax else p.hh)), p.y + ay * (e + (p.hw if ax else p.hh))
            if not stub_ok(p.side, p.x, p.y, ex, ey, w2, p.net):
                break
            for hole, dia in VIAS:
                n = int(1.6 / 0.05)
                cands = sorted((math.hypot(i * 0.05, j * 0.05), i, j) for i in range(-n, n + 1) for j in range(-n, n + 1))
                for d, i, j in cands:
                    x, y = ex + i * 0.05, ey + j * 0.05
                    if d <= 1.6 and via_ok(x, y, hole, dia, p.net, (p.ref, p.side)) and stub_ok(p.side, ex, ey, x, y, w2, p.net):
                        found = (x, y, hole, dia, ex, ey)
                        break
                if found:
                    break
            if found:
                break
        if found:
            put_via(found[0], found[1], found[2], found[3], p.net, "stub")
            put_stub(p.side, p.x, p.y, found[4], found[5], w2, p.net)
            put_stub(p.side, found[4], found[5], found[0], found[1], w2, p.net)
            done += 1
            continue
        # 4. a filled via in the pad itself (JLC caps it for free): the far side must be clear
        hole, dia = VIAS[-1]
        spot = None
        for t in (0.0, 0.1, -0.1, 0.2, -0.2):
            x, y = (p.x, p.y + t) if p.hh > p.hw else (p.x + t, p.y)
            if _vip_ok(cu, x, y, dia, p):
                spot = (x, y)
                break
        if spot:
            put_via(spot[0], spot[1], hole, dia, p.net, "pin")
            done += 1
        else:
            plan.failed.append(p)
    return done


def _vip_ok(cu, x, y, dia, pad):
    """A via in a narrow pin: it may overhang the pin, but must clear the neighbours and the far side."""
    r = dia / 2
    m = r + CLR + 0.3
    for kind, layers, onet, rc, seg, ref in cu.near(x - m, y - m, x + m, y + m):
        gap = point_gap(x, y, rc, seg) - r
        if kind in ("via", "hole") and gap < 0.2:
            return False
        if onet != pad.net and gap < 0.10:
            return False
    return True


def _inside_ok(cu, x, y, dia, pad):
    """A via inside its own pad: only the far side and other vias can object."""
    r = dia / 2
    if abs(x - pad.x) + r > pad.hw or abs(y - pad.y) + r > pad.hh:
        return False
    far = "B" if pad.side == "T" else "T"
    m = r + CLR + 0.3
    for kind, layers, onet, rc, seg, ref in cu.near(x - m, y - m, x + m, y + m):
        gap = point_gap(x, y, rc, seg) - r
        if kind in ("via", "hole") and gap < 0.2:
            return False
        if onet != pad.net and far in layers and gap < CLR:
            return False
    return True


def surface_path(cu, side, net, a, b, w):
    """Shortest clear path from a to b on a 0.1 mm grid, on one outer layer. None if there is none."""
    step = 0.1
    m = w / 2 + CLR
    x0, x1 = a[0] - 4 - max(0.0, a[0] - b[0]), a[0] + 4 + max(0.0, b[0] - a[0])
    y0, y1 = a[1] - 4 - max(0.0, a[1] - b[1]), a[1] + 4 + max(0.0, b[1] - a[1])
    x0 = a[0] - round((a[0] - x0) / step) * step
    y0 = a[1] - round((a[1] - y0) / step) * step
    items = [it for it in cu.near(x0, y0, x1, y1) if it[2] != net and side in it[1]]
    nx_, ny_ = int((x1 - x0) / step) + 1, int((y1 - y0) / step) + 1
    blocked = bytearray(nx_ * ny_)
    for it in items:
        rc = it[3]
        i1, i2 = math.ceil((rc[0] - m - x0) / step), math.floor((rc[2] + m - x0) / step)
        j1, j2 = math.ceil((rc[1] - m - y0) / step), math.floor((rc[3] + m - y0) / step)
        for j in range(max(j1, 0), min(j2 + 1, ny_)):
            lo, hi = max(i1, 0), min(i2 + 1, nx_)
            if hi > lo:
                blocked[j * nx_ + lo:j * nx_ + hi] = b"\x01" * (hi - lo)
    def cell(p):
        return round((p[1] - y0) / step) * nx_ + round((p[0] - x0) / step)
    s0, t0 = cell(a), cell(b)
    # the pads themselves stand in blocked space only if a neighbour is too close: open them
    for c in (s0, t0):
        blocked[c] = 0
    prev = {s0: -1}
    q = deque([s0])
    while q:
        c = q.popleft()
        if c == t0:
            path = []
            while c != -1:
                path.append((x0 + (c % nx_) * step, y0 + (c // nx_) * step))
                c = prev[c]
            path.reverse()
            path[0], path[-1] = a, b
            out = [path[0]]
            for i in range(1, len(path) - 1):
                u, v, t = out[-1], path[i], path[i + 1]
                if abs((v[0] - u[0]) * (t[1] - v[1]) - (v[1] - u[1]) * (t[0] - v[0])) > 1e-6:
                    out.append(v)
            out.append(path[-1])
            return out
        i, j = c % nx_, c // nx_
        for dx, dy in NB8:
            a2, b2 = i + dx, j + dy
            if 0 <= a2 < nx_ and 0 <= b2 < ny_:
                n = b2 * nx_ + a2
                if n not in prev and not blocked[n]:
                    prev[n] = c
                    q.append(n)
    return None


def surface_links(pads, plan, cu):
    """Switch nodes: wide tracks on the surface between the pads; a via only for a pad on the far side."""
    by = defaultdict(list)
    for p in pads:
        if p.net in SURFACE_ONLY:
            by[p.net].append(p)
    fails = []
    for net, ps in sorted(by.items()):
        ps.sort(key=lambda q: (P._natural(q.ref), str(q.name)))
        sides = Counter(q.side for q in ps)
        main = sides.most_common(1)[0][0]
        mains = [q for q in ps if q.side == main]
        linked = [(mains[0].x, mains[0].y)]
        for p in mains[1:] + [q for q in ps if q.side != main]:
            target = min(linked, key=lambda o: abs(o[0] - p.x) + abs(o[1] - p.y))
            if abs(target[0] - p.x) + abs(target[1] - p.y) < 0.01:
                continue
            if p.side != main:
                # a via beside the far-side pad, then the track goes to the via
                via = None
                for r in (0.5, 0.7, 0.9, 1.2, 1.5, 2.0):
                    for ang in range(0, 360, 30):
                        x = p.x + r * math.cos(math.radians(ang))
                        y = p.y + r * math.sin(math.radians(ang))
                        d = VIAS[0][1] / 2 + CLR
                        if all(it[2] == net or not (it[3][0] - d < x < it[3][2] + d and it[3][1] - d < y < it[3][3] + d)
                               for it in cu.near(x - 1, y - 1, x + 1, y + 1)):
                            via = (x, y)
                            break
                    if via:
                        break
                if not via:
                    fails.append((net, str(p), "no via spot"))
                    continue
                plan.vias.append((round(via[0], 3), round(via[1], 3), VIAS[0][0], VIAS[0][1], net, "stub"))
                r = VIAS[0][1] / 2
                cu.add("via", "TB", net, (via[0] - r, via[1] - r, via[0] + r, via[1] + r))
                plan.stubs.append((p.side, round(p.x, 3), round(p.y, 3), round(via[0], 3), round(via[1], 3), 0.3, net))
                end = via
            else:
                end = (p.x, p.y)
            target = min(linked, key=lambda o: abs(o[0] - end[0]) + abs(o[1] - end[1]))
            path = None
            for w in (1.0, 0.8, 0.6, 0.4, 0.3, 0.2):
                path = surface_path(cu, main, net, end, target, w)
                if path:
                    for a_, b_ in zip(path, path[1:]):
                        plan.stubs.append((main, round(a_[0], 3), round(a_[1], 3), round(b_[0], 3), round(b_[1], 3), w, net))
                        m = w / 2
                        cu.add("stub", main, net, (min(a_[0], b_[0]) - m, min(a_[1], b_[1]) - m,
                                                   max(a_[0], b_[0]) + m, max(a_[1], b_[1]) + m),
                               seg=(a_[0], a_[1], b_[0], b_[1], w))
                    linked.append(end)
                    break
            if not path:
                fails.append((net, str(p), "no clear path"))
    return fails


# ------------------------------------------------------------------ regions
class Grid:
    def __init__(self, planes):
        self.planes = planes
        self.owner = {pl: [0] * (NX * NY) for pl in planes}
        self.ap = [0] * (NX * NY)
        self.rail_id = {}
        self.rails = []
        self.term = defaultdict(list)     # rail id -> [cell]
        self.held = defaultdict(set)      # (plane, rail id) -> cells
        self.tree = defaultdict(set)      # (plane, rail id) -> cells joined to the rail's first terminal
        self.hops = []                    # (x, y, net): vias added where a rail changes plane
        for j in range(NY):
            for i in range(NX):
                x, y = i * GRID, j * GRID
                if x < EDGE or y < EDGE or x > P.BOARD_W - EDGE or y > P.BOARD_H - EDGE or not _in_outline(x, y):
                    for pl in planes:
                        self.owner[pl][j * NX + i] = -1

    def rid(self, net):
        if net not in self.rail_id:
            self.rails.append(net)
            self.rail_id[net] = len(self.rails)
        return self.rail_id[net]

    def cell(self, x, y):
        return round(y / GRID) * NX + round(x / GRID)

    def add_hop(self, c, k):
        """A new via for rail k, where its path changes plane."""
        x, y = (c % NX) * GRID, (c // NX) * GRID
        self.mark_anti(x, y, HOP_VIA[1] / 2 + ANTI_CLR, k)
        self.hops.append((x, y, self.rails[k - 1]))

    def mark_anti(self, x, y, r, k, terminal=True):
        n = int(r / GRID) + 1
        ci, cj = round(x / GRID), round(y / GRID)
        for j in range(cj - n, cj + n + 1):
            for i in range(ci - n, ci + n + 1):
                if 0 <= i < NX and 0 <= j < NY and math.hypot(i * GRID - x, j * GRID - y) <= r:
                    c = j * NX + i
                    a = self.ap[c]
                    self.ap[c] = k if a in (0, k) else -1
        if terminal and k > 0:
            self.term[k].append(cj * NX + ci)
            self.ap[cj * NX + ci] = k


def _in_outline(x, y):
    r = P.CORNER_R + EDGE
    W, H = P.BOARD_W, P.BOARD_H
    for cx, cy, sx, sy in ((r, r, -1, -1), (W - r, r, 1, -1), (r, H - r, -1, 1), (W - r, H - r, 1, 1)):
        if (x - cx) * sx > 0 and (y - cy) * sy > 0 and math.hypot(x - cx, y - cy) > r - EDGE:
            return False
    return True


def neighbours(c):
    i, j = c % NX, c // NX
    for dx, dy in NB8:
        a, b = i + dx, j + dy
        if 0 <= a < NX and 0 <= b < NY:
            yield b * NX + a


def adj_other(g, pl, c, k):
    own = g.owner[pl]
    for n in neighbours(c):
        o = own[n]
        if o > 0 and o != k:
            return True
    return False


def lay_path(g, layers, k, path, connected=None):
    """Put a path of (layer index, cell) on the planes. Where it changes layer it needs a new via."""
    for li, c in path:
        pl = layers[li]
        g.owner[pl][c] = k
        g.held[(pl, k)].add(c)
        g.tree[(pl, k)].add(c)
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            g.add_hop(a[1], k)
            if connected is not None:
                connected.add(a[1])


def _route(g, layers, pref, k, connected, rest, gap, hop_ok):
    """Cheapest path over both plane layers, for a rail neither layer can do alone. It may change layer at a new via, which
    costs HOP_COST cells; off its own plane each step costs a little more. Returns (terminal, [(layer index, cell)])."""
    h, prev, dist = [], {}, {}
    for li, pl in enumerate(layers):
        for c in set(connected) | g.tree[(pl, k)]:
            prev[(li, c)] = None
            dist[(li, c)] = 0.0
            h.append((0.0, li, c))
    heapq.heapify(h)
    ap = g.ap
    while h:
        d, li, c = heapq.heappop(h)
        if d > dist[(li, c)]:
            continue
        if c in rest:
            path = []
            st = (li, c)
            while st is not None:
                path.append(st)
                st = prev[st]
            return c, path
        pl = layers[li]
        own = g.owner[pl]
        cost = 1.0 if li == pref else OFF_PLANE_COST
        i, j = c % NX, c // NX
        for dx, dy in NB8:
            if not (0 <= i + dx < NX and 0 <= j + dy < NY):
                continue
            n = c + dx + dy * NX
            o = own[n]
            if (o != 0 and o != k) or (ap[n] != 0 and ap[n] != k):
                continue
            if dx and dy and own[c + dx] not in (0, k) and own[c + dy * NX] not in (0, k):
                continue
            nd = d + cost * (1.414 if dx and dy else 1.0)
            if nd >= dist.get((li, n), 1e18):
                continue
            if gap and adj_other(g, pl, n, k):
                continue
            dist[(li, n)] = nd
            prev[(li, n)] = (li, c)
            heapq.heappush(h, (nd, li, n))
        for lj in range(len(layers)):
            if lj != li and d + HOP_COST < dist.get((lj, c), 1e18) and hop_ok(c, k):
                dist[(lj, c)] = d + HOP_COST
                prev[(lj, c)] = (li, c)
                heapq.heappush(h, (d + HOP_COST, lj, c))
    return None


def route_rail(g, k, layers, gap=True, hop_ok=None, pref=0):
    """Connect the terminals of rail k: from the connected part, shortest path to the nearest other
    terminal. A terminal neither layer can reach alone gets a path with a new via. One nothing can reach starts a group of
    its own, so the others still join up. Returns True if the rail ended up in one group."""
    terms = sorted(set(g.term[k]))
    if not terms:
        return True
    connected = {terms[0]}
    rest = set(terms[1:])
    for pl in layers:
        g.owner[pl][terms[0]] = k
        g.held[(pl, k)].add(terms[0])
        g.tree[(pl, k)].add(terms[0])
    whole = True
    while rest:
        hit = None
        for pl in layers:
            hit = _bfs(g, pl, k, connected, rest, gap)
            if hit is not None:
                t, path = hit
                for c in path:
                    g.owner[pl][c] = k
                    g.held[(pl, k)].add(c)
                    g.tree[(pl, k)].add(c)
                connected.add(t)
                rest.discard(t)
                break
        if hit is None and hop_ok is not None and len(layers) > 1:
            found = _route(g, layers, pref, k, connected, rest, gap, hop_ok)
            if found:
                lay_path(g, layers, k, found[1], connected)
                connected.add(found[0])
                rest.discard(found[0])
                continue
        if hit is None:
            # nothing left is reachable from this group: the rest make their own
            whole = False
            seed = min(rest)
            rest.discard(seed)
            connected = {seed}
            for pl in layers:
                g.tree[(pl, k)] = set()
                if g.owner[pl][seed] in (0, k):
                    g.owner[pl][seed] = k
                    g.held[(pl, k)].add(seed)
                    g.tree[(pl, k)].add(seed)
    return whole


def dilate(g, pl, k, cells, radius):
    """Widen a trunk where the copper is free."""
    own = g.owner[pl]
    front = list(cells)
    for _ in range(radius):
        nxt = []
        for c in front:
            for n in neighbours(c):
                if own[n] == 0 and g.ap[n] in (0, k) and not adj_other(g, pl, n, k):
                    own[n] = k
                    g.held[(pl, k)].add(n)
                    nxt.append(n)
        front = nxt


def _bfs(g, pl, k, connected, rest, gap):
    own = g.owner[pl]
    ap = g.ap
    prev = {}
    q = deque()
    for c in connected:
        prev[c] = -1
        q.append(c)
    # everything already joined to the rail on this layer is a source too
    for c in g.tree[(pl, k)]:
        if c not in prev:
            prev[c] = -1
            q.append(c)
    while q:
        c = q.popleft()
        if c in rest:
            path = []
            n = c
            while n != -1:
                path.append(n)
                n = prev[n]
            return c, path
        for n in neighbours(c):
            if n in prev:
                continue
            o = own[n]
            if o != 0 and o != k:
                continue
            a = ap[n]
            if a != 0 and a != k:
                continue
            if gap and adj_other(g, pl, n, k):
                continue
            # a diagonal step between two other rails' cells holds no copper
            dx, dy = n % NX - c % NX, n // NX - c // NX
            if dx and dy and own[c + dx] not in (0, k) and own[c + dy * NX] not in (0, k):
                continue
            prev[n] = c
            q.append(n)
    return None


def fill(g, weights):
    """Spare copper to the nearest rail, at a speed set by the rail's current; one empty cell between
    rails."""
    for pl in g.planes:
        own = g.owner[pl]
        h = []
        seq = 0
        for c, o in enumerate(own):
            if o > 0:
                h.append((0.0, seq, c, o))
                seq += 1
        for net in DUAL:
            k = g.rail_id.get(net)
            if k:
                for c in g.term[k]:
                    if own[c] == 0:
                        h.append((0.0, seq, c, k))
                        seq += 1
        heapq.heapify(h)
        while h:
            d, _, c, k = heapq.heappop(h)
            if own[c] not in (0, k):
                continue
            if own[c] == k and d > 0:
                continue
            a = g.ap[c]
            if a != 0 and a != k:
                continue
            if adj_other(g, pl, c, k):
                continue
            own[c] = k
            step = 1.0 / weights.get(k, 0.3)
            i, j = c % NX, c // NX
            for dx, dy in NB8:
                a2, b2 = i + dx, j + dy
                if 0 <= a2 < NX and 0 <= b2 < NY:
                    n = b2 * NX + a2
                    if own[n] == 0:
                        heapq.heappush(h, (d + step * (1.414 if dx and dy else 1.0), seq, n, k))
                        seq += 1


def region(g, pl, k):
    """The cells rail k's polygons cover on a layer. A diagonal step between two cells needs a free cell beside it, or there
    is no copper there. A via's anti-pad cells count as free: the pour clears them by itself."""
    own = g.owner[pl]
    cells = {c for c, o in enumerate(own) if o == k}
    for c in list(cells):
        i, j = c % NX, c // NX
        for dx, dy in ((1, 1), (1, -1)):
            if not (0 <= i + dx < NX and 0 <= j + dy < NY):
                continue
            n = (j + dy) * NX + i + dx
            if n in cells:
                a = j * NX + i + dx
                b = (j + dy) * NX + i
                if a not in cells and b not in cells:
                    for m in (a, b):
                        if own[m] == 0:
                            cells.add(m)
                            break
    grown = set(cells)
    for c in cells:
        for n in neighbours(c):
            if own[n] == 0 and g.ap[n] != 0 and not any(own[m] > 0 and own[m] != k for m in neighbours(n)):
                grown.add(n)
    return grown


def components(g, pl, k):
    """Rail k's copper on a layer, in the 4-connected pieces that really touch."""
    cells = region(g, pl, k)
    seen = set()
    out = []
    for c0 in sorted(cells):
        if c0 in seen:
            continue
        comp = {c0}
        seen.add(c0)
        st = [c0]
        while st:
            c = st.pop()
            for n in (c - 1, c + 1, c - NX, c + NX):
                if n in cells and n not in seen and abs(n % NX - c % NX) <= 1:
                    seen.add(n)
                    comp.add(n)
                    st.append(n)
        out.append(comp)
    return out


def connectivity(g, k):
    """Groups of rail k's terminals joined through plane copper on any layer plus their own vias."""
    terms = sorted(set(g.term[k]))
    if not terms:
        return []
    parent = {t: t for t in terms}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    tset = set(terms)
    for pl in g.planes:
        for comp in components(g, pl, k):
            inside = [c for c in comp if c in tset]
            for t in inside[1:]:
                parent[find(t)] = find(inside[0])
    groups = defaultdict(list)
    for t in terms:
        groups[find(t)].append(t)
    return list(groups.values())


# ------------------------------------------------------------------ IR drop
def ir_drop(g, net, source_cells, load_cells, amps):
    """Conjugate gradient on the rail's copper, both plane layers joined at its vias. Square cells, so
    each edge conducts 1 / RS. Returns (volts at each load, the node map)."""
    k = g.rail_id[net]
    nodes = {}
    for li, pl in enumerate(g.planes):
        own = g.owner[pl]
        for c, o in enumerate(own):
            if o == k:
                nodes[(li, c)] = len(nodes)
    if not nodes:
        return None
    import numpy as np
    n = len(nodes)
    edges = []
    for (li, c), a in nodes.items():
        i, j = c % NX, c // NX
        for dx, dy, cond in ((1, 0, 1.0), (0, 1, 1.0), (1, 1, 0.3), (1, -1, 0.3)):
            if 0 <= i + dx < NX and 0 <= j + dy < NY:
                b = nodes.get((li, c + dx + dy * NX))
                if b is not None:
                    edges.append((a, b, cond / RS))
    if len(g.planes) > 1:
        for t in set(g.term[k]):
            a, b = nodes.get((0, t)), nodes.get((1, t))
            if a is not None and b is not None:
                edges.append((a, b, 1.0 / 2.0e-3))        # via barrel
    e = np.array(edges)
    ai, bi, gi = e[:, 0].astype(int), e[:, 1].astype(int), e[:, 2]
    fixed = np.zeros(n, bool)
    for s in source_cells:
        for li in range(len(g.planes)):
            v = nodes.get((li, s))
            if v is not None:
                fixed[v] = True
    rhs = np.zeros(n)
    loads = []
    for s in load_cells:
        for li in range(len(g.planes)):
            v = nodes.get((li, s))
            if v is not None:
                loads.append(v)
                break
    if not loads or not fixed.any():
        return None
    # copper not joined to the source would make the system singular
    adj = defaultdict(list)
    for a, b, _ in edges:
        adj[a].append(b)
        adj[b].append(a)
    reach = set(np.nonzero(fixed)[0].tolist())
    st = list(reach)
    while st:
        a = st.pop()
        for b in adj[a]:
            if b not in reach:
                reach.add(b)
                st.append(b)
    loads = [v for v in loads if v in reach]
    if not loads:
        return None
    mask = np.zeros(n, bool)
    mask[list(reach)] = True
    fixed = fixed | ~mask
    for v in loads:
        rhs[v] -= amps / len(loads)

    def mul(x):
        y = np.zeros(n)
        d = gi * (x[ai] - x[bi])
        np.add.at(y, ai, d)
        np.add.at(y, bi, -d)
        y[fixed] = 0
        return y

    x = np.zeros(n)
    b = rhs.copy()
    b[fixed] = 0
    r = b - mul(x)
    diag = np.zeros(n)
    np.add.at(diag, ai, gi)
    np.add.at(diag, bi, gi)
    diag[diag == 0] = 1
    z = r / diag
    p = z.copy()
    rz = r @ z
    for it in range(6000):
        ap = mul(p)
        alpha = rz / (p @ ap)
        x += alpha * p
        r -= alpha * ap
        if np.abs(r).max() < 1e-7:
            break
        z = r / diag
        rz2 = r @ z
        p = z + rz2 / rz * p
        rz = rz2
    return x, nodes, loads


# ------------------------------------------------------------------ build
def build_fanout(parts=None, nets=None, place=None):
    if parts is None:
        parts, nets = P.load_parts()
        place = P.read_csv()
    classes = S.net_classes(_nets())
    power = set(classes["PWR"]) | set(classes["PWR_HI"])
    pads = load_pads(parts, place)
    cu = Copper()
    for p in pads:
        layers = "TB" if p.tht else p.side
        cu.add("hole" if p.tht else "pad", layers, p.net, (p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh), ref=p.ref)
    plan = Plan()
    sip = fanout_sip(parts, place, plan, cu, power)
    link_fail = surface_links(pads, plan, cu)
    done = fanout_pads(pads, parts, place, plan, cu, power)
    return dict(plan=plan, pads=pads, sip=sip, done=done, link_fail=link_fail, power=power, parts=parts,
                nets=nets, place=place)


def best_plan(planes, fan=None, rounds=3, log=print):
    """Route, see which rails fell apart, and route again with those first. Keeps the best round."""
    fan = fan or build_fanout()
    best, hint = None, []
    for i in range(rounds):
        res = build_plan(planes, fan, hint)
        g = res["g"]
        split = [net for net, k in g.rail_id.items() if len(connectivity_planes(res, k)) > 1]
        thin_mm = sum(len(t[2]) * GRID for t in res["thin"])
        score = (sum(len(v) for v in res["unconnected"].values()), thin_mm, len(res["thin"]))
        log(f"round {i}: {score[0]} terminals unconnected, {score[2]} thin links, {thin_mm:.0f} mm; {len(split)} rails split")
        if best is None or score < best[0]:
            best = (score, res)
        if not split:
            break
        hint = split + [n for n in hint if n not in split]
    return best[1]


def connectivity_planes(res, k):
    return connectivity(res["g"], k)


def build_plan(planes, fan=None, hint=()):
    fan = fan or build_fanout()
    plan, pads, power, parts, place = fan["plan"], fan["pads"], fan["power"], fan["parts"], fan["place"]
    # ---- regions
    g = Grid(planes)
    for v in plan.vias:
        r = SIP_ANTI if v[3] <= 0.26 else v[3] / 2 + ANTI_CLR
        if v[4] in power:
            g.mark_anti(v[0], v[1], r, g.rid(v[4]))
        else:
            # GND and the signal fan-out: the planes clear them
            g.mark_anti(v[0], v[1], r, -1, terminal=False)
    for p in pads:
        if not p.tht:
            continue
        r = max(p.hw, p.hh) + ANTI_CLR
        if p.net in power and p.net not in SURFACE_ONLY:
            g.mark_anti(p.x, p.y, r, g.rid(p.net))
        else:
            g.mark_anti(p.x, p.y, r, -1, terminal=False)
    weights = {}
    for net, k in g.rail_id.items():
        weights[k] = max(0.25, min(3.0, CURRENT.get(net, SMALL) * 1.5))
    sip_rails = {q[2] for q in parts["U1"].pads if q[2] in power}

    def order_key(net):
        i = CURRENT.get(net, SMALL)
        if net in TRUNKS:
            return (0, -i, net)
        if net in LONG_RAILS:
            return (0.25, -i, net)
        if net in hint:
            return (0.5, list(hint).index(net), net)
        if net in WALLED:
            return (1, i, net)
        if net in sip_rails:
            return (2, i, net)
        return (3, -i, net)

    ux, uy = place["U1"][:2]
    for net, boxes in CORRIDORS.items():
        k = g.rail_id[net]
        for pl, (x1, y1, x2, y2) in boxes:
            if pl not in planes:
                continue
            first = None
            for j in range(round((uy + y1) / GRID), round((uy + y2) / GRID) + 1):
                for i in range(round((ux + x1) / GRID), round((ux + x2) / GRID) + 1):
                    c = j * NX + i
                    if g.owner[pl][c] == 0 and g.ap[c] in (0, k):
                        g.owner[pl][c] = k
                        g.held[(pl, k)].add(c)
                        if first is None or (abs(i * GRID - ux - (x1 + x2) / 2) + abs(j * GRID - uy - (y1 + y2) / 2)) < first[0]:
                            first = (abs(i * GRID - ux - (x1 + x2) / 2) + abs(j * GRID - uy - (y1 + y2) / 2), c)
            if first:
                # a direct trunk from the regulator: without it the corridor would join the rail through
                # the balls, and carry no current
                src = SOURCE.get(net)
                if src:
                    ref, pin = src.split(".")
                    sp = next(q for q in pads if q.ref == ref and q.name == pin)
                    via = min((v for v in plan.vias if v[4] == net), key=lambda v: abs(v[0] - sp.x) + abs(v[1] - sp.y))
                    start = g.cell(via[0], via[1])
                    g.owner[pl][start] = k
                    g.held[(pl, k)].add(start)
                    hit = _bfs(g, pl, k, {start}, {first[1]}, True)
                    if hit:
                        for c in hit[1]:
                            g.owner[pl][c] = k
                            g.held[(pl, k)].add(c)
                        dilate(g, pl, k, list(hit[1]), TRUNKS.get(net, 2))
                        for c in g.held[(pl, k)]:
                            g.tree[(pl, k)].add(c)
    unconnected = {}
    near_surface = surface_copper(pads, plan)

    def hop_ok(c, k):
        """A via here: outside the SiP's room, clear of copper on both sides and of every other rail's copper and vias."""
        x, y = (c % NX) * GRID, (c // NX) * GRID
        if abs(x - ux) < S.ROOM_W_MM / 2 + 0.6 and abs(y - uy) < S.ROOM_H_MM / 2 + 0.6:
            return False
        if near_surface.get(c, set()) - {g.rails[k - 1]}:
            return False
        i, j = c % NX, c // NX
        for b in range(j - 2, j + 3):
            for a in range(i - 2, i + 3):
                if not (0 <= a < NX and 0 <= b < NY):
                    return False
                m = b * NX + a
                if g.ap[m] not in (0, k):
                    return False
                for pl in planes:
                    if g.owner[pl][m] not in (0, k):
                        return False
        return True

    # first pass with a one-cell gap, on the rail's plane and then the other
    for net in sorted(g.rail_id, key=order_key):
        k = g.rail_id[net]
        pref = plane_of(net)
        layers = [pref] + [q for q in planes if q != pref] if pref in planes else list(planes)
        if not route_rail(g, k, layers, True, hop_ok, 0):
            unconnected[net] = True
        if net in TRUNKS:
            for pl in planes:
                dilate(g, pl, k, list(g.held[(pl, k)]), TRUNKS[net])
    # a second pass for what is left: copper may touch the neighbour's cell edge
    for net in unconnected:
        join_groups(g, g.rail_id[net], list(planes), hop_ok)
    fill(g, weights)
    thin, still = thin_links(g, power, back_copper(pads, plan), off_grid_vias(plan), place["U1"])
    hi = set(S.net_classes(_nets())["PWR_HI"])
    return dict(fan, g=g, hi=hi, weights=weights, unconnected=still, first_fail=list(unconnected), thin=thin)


def join_groups(g, k, layers, hop_ok=None):
    """Second try for a rail in several groups: copper may run next to its neighbours' cells."""
    for _ in range(40):
        groups = connectivity(g, k)
        if len(groups) < 2:
            return
        groups.sort(key=len, reverse=True)
        done = False
        for grp in groups[1:]:
            others = set(t for h in groups if h is not grp for t in h)
            for pl in layers:
                g.tree[(pl, k)] = set()
                hit = _bfs(g, pl, k, set(grp), others, False)
                if hit is not None:
                    for c in hit[1]:
                        g.owner[pl][c] = k
                        g.held[(pl, k)].add(c)
                    done = True
                    break
            if not done and hop_ok is not None and len(layers) > 1:
                found = _route(g, layers, 0, k, set(grp), others, False, hop_ok)
                if found:
                    lay_path(g, layers, k, found[1])
                    done = True
            if done:
                break
        if not done:
            return


def surface_copper(pads, plan):
    """{cell: nets} where a new via would be too close to copper on L1 or L8."""
    near = defaultdict(set)
    m = HOP_VIA[1] / 2 + 0.12

    def mark(x1, y1, x2, y2, net):
        for j in range(math.ceil((y1 - m) / GRID), math.floor((y2 + m) / GRID) + 1):
            for i in range(math.ceil((x1 - m) / GRID), math.floor((x2 + m) / GRID) + 1):
                if 0 <= i < NX and 0 <= j < NY:
                    near[j * NX + i].add(net)

    for p in pads:
        mark(p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh, p.net)
    for t in plan.stubs:
        steps = max(1, int(math.hypot(t[3] - t[1], t[4] - t[2]) / 0.1))
        for s_ in range(steps + 1):
            x = t[1] + (t[3] - t[1]) * s_ / steps
            y = t[2] + (t[4] - t[2]) * s_ / steps
            mark(x - t[5] / 2, y - t[5] / 2, x + t[5] / 2, y + t[5] / 2, t[6])
    return near


def back_copper(pads, plan):
    """{cell: nets} for the cells a thin track on L8 can't use: too close to copper on the back."""
    near = defaultdict(set)
    m = 0.10 + THIN_W_HI / 2

    def mark(x1, y1, x2, y2, net):
        for j in range(math.ceil((y1 - m) / GRID), math.floor((y2 + m) / GRID) + 1):
            for i in range(math.ceil((x1 - m) / GRID), math.floor((x2 + m) / GRID) + 1):
                if 0 <= i < NX and 0 <= j < NY:
                    near[j * NX + i].add(net)

    for p in pads:
        if p.side == "B" or p.tht:
            mark(p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh, p.net)
    for t in plan.stubs:
        if t[0] == "B":
            steps = max(1, int(math.hypot(t[3] - t[1], t[4] - t[2]) / 0.1))
            for s in range(steps + 1):
                x = t[1] + (t[3] - t[1]) * s / steps
                y = t[2] + (t[4] - t[2]) * s / steps
                mark(x - t[5] / 2, y - t[5] / 2, x + t[5] / 2, y + t[5] / 2, t[6])
    return near


def off_grid_vias(plan):
    """{cell: nets} near vias that aren't on the grid. A track can pass such a via between two cells, closer than either."""
    near = defaultdict(set)
    for v in plan.vias:
        if abs(v[0] / GRID - round(v[0] / GRID)) < 0.01 and abs(v[1] / GRID - round(v[1] / GRID)) < 0.01:
            continue
        r = v[3] / 2 + 0.10 + THIN_W_HI / 2 + GRID * 0.6
        n = int(r / GRID) + 1
        ci, cj = round(v[0] / GRID), round(v[1] / GRID)
        for j in range(cj - n, cj + n + 1):
            for i in range(ci - n, ci + n + 1):
                if 0 <= i < NX and 0 <= j < NY and math.hypot(i * GRID - v[0], j * GRID - v[1]) <= r:
                    near[j * NX + i].add(v[4])
    return near


def thin_links(g, power, back, off_grid, u1):
    """A rail's groups that stay apart after the pours, joined with a thin track: on L8 where it can, because under the SiP
    the back holds only caps, and then on L6 and L3, which the signals need. On those two a track pays to run through the
    SiP's signal rows, so it crosses them instead of running along them."""
    tracks = []
    left = {}
    used = {8: {}, 3: {}, 6: {}}
    ux, uy = u1[:2]

    def signal_rows(c):
        x, y = (c % NX) * GRID - ux, (c // NX) * GRID - uy
        return abs(x) < 7.5 and abs(y) < 5.0 and (abs(y) >= 2.0 or x >= 4.0)

    for net, k in sorted(g.rail_id.items(), key=lambda kv: kv[1]):
        groups = connectivity(g, k)
        if len(groups) < 2:
            continue
        groups.sort(key=len, reverse=True)
        main = set()
        for pl in g.planes:
            main |= g.held[(pl, k)]
        joined = set(groups[0])
        for grp in groups[1:]:
            done = False
            for layer in (8, 6, 3):
                path = _thin_path(g, used[layer], k, net, grp, joined, back if layer == 8 else None,
                                  None if layer == 8 else signal_rows, off_grid)
                if path and not (layer == 8 and len(path) * GRID > MAX_L8_LINK):
                    for c in path:
                        used[layer][c] = k
                    tracks.append((layer, net, path))
                    joined |= set(grp)
                    done = True
                    break
            if not done:
                left.setdefault(net, []).extend(grp)
    return tracks, left


def _thin_path(g, used, k, net, sources, goals, back, costly, off_grid):
    """Cheapest path for a thin track. back: {cell: nets} to stay off. costly(cell): true where a cell costs more."""
    prev = {c: -1 for c in sources}
    dist = {c: 0.0 for c in sources}
    h = [(0.0, c) for c in sources]
    heapq.heapify(h)
    ap = g.ap
    while h:
        d, c = heapq.heappop(h)
        if d > dist[c]:
            continue
        if c in goals:
            path = []
            n = c
            while n != -1:
                path.append(n)
                n = prev[n]
            return path
        i, j = c % NX, c // NX
        for dx, dy in NB8:
            if not (0 <= i + dx < NX and 0 <= j + dy < NY):
                continue
            n = c + dx + dy * NX
            a = ap[n]
            if a != 0 and a != k:
                continue
            if used.get(n, k) != k or g.owner[g.planes[0]][n] == -1:
                continue
            if any(used.get(m, k) != k for m in neighbours(n)):
                continue
            if back is not None and back.get(n, set()) - {net}:
                continue
            if off_grid.get(n, set()) - {net}:
                continue
            nd = d + (1.414 if dx and dy else 1.0) * (THIN_ROW_COST if costly and costly(n) else 1.0)
            if nd < dist.get(n, 1e18):
                dist[n] = nd
                prev[n] = c
                heapq.heappush(h, (nd, n))
    return None


def _nets():
    import build
    return build.pcb_nets()


def report(res, name):
    g, plan = res["g"], res["plan"]
    vias = plan.vias
    print(f"--- {name}")
    print("vias", len(vias), Counter(v[5] for v in vias), "sizes", Counter((v[2], v[3]) for v in vias))
    print("  GND vias", sum(1 for v in vias if v[4] == "GND"), "stubs", len(plan.stubs))
    print("SiP", res["sip"])
    print("pads with no via or stub:", len(plan.failed), [str(p) + ":" + p.net for p in plan.failed][:60])
    print("switch-node links failed:", res["link_fail"])
    print("first pass, rails needing the tight pass:", res["first_fail"])
    bad = {}
    for net, k in g.rail_id.items():
        groups = connectivity(g, k)
        if len(groups) > 1:
            bad[net] = sorted(len(x) for x in groups)
    print("rails split on the planes after fill:", len(bad), "of", len(g.rail_id), bad)
    print("new vias where a rail changes plane:", len(g.hops), Counter(h[2] for h in g.hops).most_common(12))
    print("thin links:", len(res["thin"]), [(t[0], t[1], round(len(t[2]) * GRID, 1)) for t in res["thin"]])
    print("rails still not connected:", {k: len(v) for k, v in res["unconnected"].items()})
    for pl in g.planes:
        own = g.owner[pl]
        c = Counter(o for o in own if o > 0)
        top = [(g.rails[k - 1], round(v * GRID * GRID)) for k, v in c.most_common(8)]
        print(pl, "rails", len(c), "free cells", sum(1 for o in own if o == 0), "top mm2", top)
    # IR drop
    place, nets, parts = res["place"], res["nets"], res["parts"]
    pad_at = {(p.ref, p.name): p for p in res["pads"]}
    out = {}
    for net, src in SOURCE.items():
        if net not in g.rail_id:
            continue
        ref, pin = src.split(".")
        sp = pad_at[(ref, pin)]
        src_cells = [g.cell(v[0], v[1]) for v in plan.vias if v[4] == net and abs(v[0] - sp.x) < 3 and abs(v[1] - sp.y) < 3]
        loads = []
        balls = [n.split(".")[1] for n in nets[net] if n.startswith("U1.")]
        for b in balls:
            bp = pad_at[("U1", b)]
            near = min((v for v in plan.vias if v[4] == net and v[5] == "sip"),
                       key=lambda v: abs(v[0] - bp.x) + abs(v[1] - bp.y))
            loads.append(g.cell(near[0], near[1]))
        r = ir_drop(g, net, src_cells, loads, CURRENT.get(net, 0.5))
        if r is None:
            print(net, "no solution")
            continue
        x, nodes, lv = r
        print(f"{net}: {CURRENT.get(net)} A, source {src}, worst ball {abs(x[lv]).max()*1e3:.1f} mV, mean ball {abs(x[lv]).mean()*1e3:.1f} mV "
              f"= {abs(x[lv]).mean()*1e3/ (0.85 if 'CORE' in net else 1.2) / 10:.2f} % of the rail")
        out[net] = (x, nodes, lv)
        if net == "VDD_CORE_0V85":
            for tap in ("FB300", "FB301"):
                p = [q for q in res["pads"] if q.ref == tap and q.net == net]
                if p:
                    v = min((w for w in plan.vias if w[4] == net), key=lambda w: abs(w[0] - p[0].x) + abs(w[1] - p[0].y))
                    c = g.cell(v[0], v[1])
                    for li in range(len(g.planes)):
                        n = nodes.get((li, c))
                        if n is not None:
                            print(f"  {tap} input: {abs(x[n])*1e3:.1f} mV; difference to mean ball {abs(abs(x[lv]).mean()-abs(x[n]))*1e3:.1f} mV (limit 8.5 mV, 1 %)")
                            break
    return bad


def render(res, tag):
    from PIL import Image, ImageDraw
    g = res["g"]
    S_ = 4
    rng = __import__("random").Random(3)
    colors = {k: (rng.randint(60, 240), rng.randint(60, 240), rng.randint(60, 240)) for k in range(1, len(g.rails) + 2)}
    files = []
    for pl in g.planes:
        im = Image.new("RGB", (NX * S_, NY * S_), (15, 15, 20))
        px = im.load()
        own = g.owner[pl]
        for j in range(NY):
            for i in range(NX):
                o = own[j * NX + i]
                col = colors.get(o) if o > 0 else ((40, 40, 45) if o == 0 else (0, 0, 0))
                if g.ap[j * NX + i] == -1 and o <= 0:
                    col = (90, 90, 90)
                for a in range(S_):
                    for b in range(S_):
                        px[i * S_ + a, (NY - 1 - j) * S_ + b] = col
        d = ImageDraw.Draw(im)
        c = Counter(o for o in own if o > 0)
        for k, v in c.items():
            if v > 40:
                cells = [q for q, o in enumerate(own) if o == k]
                mid = cells[len(cells) // 2]
                d.text(((mid % NX) * S_, (NY - 1 - mid // NX) * S_), g.rails[k - 1][:12], fill=(255, 255, 255))
        path = OUT / f"plane_{tag}_{pl}.png"
        im.save(path)
        files.append(path)
    return files


# ------------------------------------------------------------------ polygons
def outlines(g, pl, k):
    """Rectilinear outlines (mm) of rail k's 4-connected copper on a layer, holes ignored: the polygon
    inside a hole is poured first and this one pours around it."""
    tset = set(g.term[k])
    polys = []
    for comp in components(g, pl, k):
        # copper that joins nothing: a small patch around one via does no good, and takes room from the next rail
        joins = len(comp & tset)
        if joins == 0 or (joins == 1 and len(comp) < MIN_PATCH):
            continue
        polys.append((len(comp), trace(comp)))
    return polys


def trace(comp):
    """Outer boundary of a 4-connected set of cells, as corner points in mm."""
    edges = {}
    for c in comp:
        i, j = c % NX, c // NX
        # cell corners in half-cell units, counter-clockwise with the cell on the left
        x1, x2, y1, y2 = 2 * i - 1, 2 * i + 1, 2 * j - 1, 2 * j + 1
        if c - NX not in comp:
            edges.setdefault((x1, y1), []).append((x2, y1))
        if c + 1 not in comp or (c + 1) % NX == 0:
            edges.setdefault((x2, y1), []).append((x2, y2))
        if c + NX not in comp:
            edges.setdefault((x2, y2), []).append((x1, y2))
        if c - 1 not in comp or c % NX == 0:
            edges.setdefault((x1, y2), []).append((x1, y1))
    loops = []
    while edges:
        start = min(edges)
        loop = [start]
        cur = start
        prev_dir = (1, 0)
        while True:
            nexts = edges[cur]
            if len(nexts) == 1:
                nx_ = nexts.pop()
                del edges[cur]
            else:
                # at a corner touch, turn left to stay on this loop
                def turn(n):
                    d = (n[0] - cur[0], n[1] - cur[1])
                    return -(prev_dir[0] * d[1] - prev_dir[1] * d[0])
                nexts.sort(key=turn)
                nx_ = nexts.pop(0)
            prev_dir = (nx_[0] - cur[0], nx_[1] - cur[1])
            if nx_ == start:
                break
            loop.append(nx_)
            cur = nx_
        loops.append(loop)

    def area(l):
        return sum(l[i][0] * l[(i + 1) % len(l)][1] - l[(i + 1) % len(l)][0] * l[i][1] for i in range(len(l))) / 2

    best = max(loops, key=lambda l: abs(area(l)))
    corners = []
    n = len(best)
    for i in range(n):
        a, b, c = best[i - 1], best[i], best[(i + 1) % n]
        if (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0]):
            corners.append(b)
    return [(x * GRID / 2, y * GRID / 2) for x, y in smooth(corners)]


def smooth(pts):
    """Staircases on the cell grid become 45 degree edges. A run is cut from outer corner to outer corner, so the copper only
    ever grows into the free cells beside it, and a one-cell strip can't lose its neck. Altium keeps the clearance when it
    pours. Points in half cells, counter-clockwise with the copper on the left."""
    n = len(pts)
    if n < 8:
        return pts

    def step(i):
        a, b = pts[i % n], pts[(i + 1) % n]
        return b[0] - a[0], b[1] - a[1]

    def convex(i):
        (ax, ay), (bx, by) = step(i - 1), step(i)
        return ax * by - ay * bx > 0

    def unit(d):
        return abs(d[0]) + abs(d[1]) == 2

    # start somewhere that isn't inside a staircase
    start = next((i for i in range(n) if not (unit(step(i)) and unit(step(i - 1)))), None)
    if start is None:
        return pts
    out = []
    i = 0
    while i < n:
        k = (start + i) % n
        out.append(pts[k])
        if convex(k):
            # how far does a stair with the same two directions go?
            a, b = step(k), step(k + 1)
            j = 0
            if unit(a) and unit(b) and a[0] * b[0] + a[1] * b[1] == 0:
                while i + j + 1 < n and step(k + j) == (a if j % 2 == 0 else b) and unit(step(k + j)):
                    j += 1
            # back up to the last outer corner in the run
            while j >= 2 and not convex(k + j):
                j -= 1
            if j >= 4:
                i += j
                continue
        i += 1
    return out


def polygons(res):
    g = res["g"]
    rows = []
    for pl in g.planes:
        for net, k in g.rail_id.items():
            for size, pts in outlines(g, pl, k):
                if len(pts) >= 4:
                    rows.append((size, pl, net, pts))
    rows.sort(key=lambda r: r[0])       # small first: larger polygons pour around them
    return rows


def thin_width(net, a, b, res):
    """W_PWR_HI wants 0.20 mm; inside the SiP's room W_SiP allows 0.15 mm at most, and comes first."""
    if net not in res["hi"]:
        return THIN_W
    ux, uy = res["place"]["U1"][:2]
    inside = any(abs(q[0] - ux) <= S.ROOM_W_MM / 2 + 0.2 and abs(q[1] - uy) <= S.ROOM_H_MM / 2 + 0.2 for q in (a, b))
    return THIN_W if inside else THIN_W_HI


def thin_tracks(res):
    """Thin links on L3 and L6 as (layer, x1, y1, x2, y2, width)."""
    return [(layer, a[0], a[1], b[0], b[1], THIN_W) for layer, net, path in res["thin"] if layer != 8
            for a, b in thin_segments(path)]


def thin_segments(path):
    """Grid cells to straight segments in mm."""
    pts = [((c % NX) * GRID, (c // NX) * GRID) for c in path]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        u, v, w = out[-1], pts[i], pts[i + 1]
        if abs((v[0] - u[0]) * (w[1] - v[1]) - (v[1] - u[1]) * (w[0] - v[0])) > 1e-9:
            out.append(v)
    out.append(pts[-1])
    return list(zip(out, out[1:]))


def spec_text(res, pcb):
    """ape_place_power.txt: coordinates in Altium coords relative to the board origin. Vias and tracks
    are grouped by net, because the script looks a net up only when the name changes."""
    def co(v):
        return int(round(v / 0.0254 * 10000))

    plan = res["plan"]
    g = res["g"]
    lines = [str(pcb)]
    owned = sorted(set(res["power"]) | {"GND"})
    lines += [f"NET|{n}" for n in owned]
    # the signal fan-out goes back with the rest; signal copper outside the SiP's area stays
    signal_nets = ({t[6] for t in plan.stubs} | {v[4] for v in plan.vias}) - set(res["power"]) - {"GND"}
    lines += [f"SIGNET|{n}" for n in sorted(signal_nets)]
    b = P.crt_rect(res["parts"]["U1"], *res["place"]["U1"])
    m = 2.0
    lines.append(f"AREA|{co(b[0] - m)}|{co(b[1] - m)}|{co(b[2] + m)}|{co(b[3] + m)}")
    rows = []
    for v in plan.vias:
        rows.append((v[4], 0, f"VIA|{co(v[0])}|{co(v[1])}|{co(v[2])}|{co(v[3])}|{v[4]}"))
    for t in plan.stubs:
        layer = 1 if t[0] == "T" else 32
        rows.append((t[6], 1, f"TRK|{layer}|{co(t[1])}|{co(t[2])}|{co(t[3])}|{co(t[4])}|{co(t[5])}|{t[6]}"))
    for x, y, net in g.hops:
        rows.append((net, 0, f"VIA|{co(x)}|{co(y)}|{co(HOP_VIA[0])}|{co(HOP_VIA[1])}|{net}"))
    for layer, net, path in res["thin"]:
        for a, b in thin_segments(path):
            old = 32 if layer == 8 else layer
            w = thin_width(net, a, b, res)
            rows.append((net, 1, f"TRK|{old}|{co(a[0])}|{co(a[1])}|{co(b[0])}|{co(b[1])}|{co(w)}|{net}"))
    rows.sort(key=lambda r: (r[0], r[1]))
    lines += [r[2] for r in rows]
    order = 1
    for size, pl, net, pts in polygons(res):
        lines.append(f"POLY|{S.V5_LAYER[pl]}|{net}|{order}|" + ";".join(f"{co(x)},{co(y)}" for x, y in pts))
        order += 1
    e = EDGE
    W, H = P.BOARD_W, P.BOARD_H
    r = P.CORNER_R
    box = [(e, e + r), (e + r, e), (W - e - r, e), (W - e, e + r), (W - e, H - e - r), (W - e - r, H - e),
           (e + r, H - e), (e, H - e - r)]
    for pl in ("L2_GND", "L7_GND"):
        lines.append(f"POLY|{S.V5_LAYER[pl]}|GND|{order}|" + ";".join(f"{co(x)},{co(y)}" for x, y in box))
        order += 1
    return "\n".join(lines) + "\n"


def main(argv):
    import fanout
    cmd = argv[0] if argv else "plan"
    if cmd == "plan":
        n = argv[1] if len(argv) > 1 else "2"
        planes = PLANES_2 if n == "2" else (PLANES_2[0],)
        res = best_plan(planes, fanout.build())
        report(res, f"{n} power plane(s)")
        print("SiP signal vias that can get out, with the thin links down:", fanout.escape_check(res, thin=thin_tracks(res)))
        for net, cells in res["unconnected"].items():
            print("not connected:", net, [((c % NX) * GRID, (c // NX) * GRID) for c in cells])
        print([str(p) for p in render(res, n)])
    elif cmd in ("spec", "apply"):
        # apply N: only N rounds of the search, when an earlier "plan" showed the best round
        import build
        res = best_plan(PLANES_2, fanout.build(), rounds=int(argv[1]) if len(argv) > 1 else 3)
        report(res, "2 power planes")
        print("SiP signal vias that can get out, with the thin links down:", fanout.escape_check(res, thin=thin_tracks(res)))
        text = spec_text(res, build.PCB_PATH)
        (P.BRIDGE / "ape_place_power.txt").write_text(text)
        kinds = Counter(line.split("|")[0] for line in text.splitlines())
        corners = sum(line.count(";") + 1 for line in text.splitlines() if line.startswith("POLY"))
        print("spec:", dict(kinds), "polygon corners:", corners)
        fanout.render(res)
        if cmd == "apply":
            print(P.run_place("PlacePower", timeout=1800))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
