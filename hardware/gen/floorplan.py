"""APE-SBC functional floorplan, for review before any detailed placement.

Nothing here touches the PcbDoc. It holds, for a given board size:
- where the connectors and big ICs go, by hand (Plan.big);
- one region per schematic function, per side (Plan.top, Plan.back);
- the buses and power flow to draw.

From those it works out the numbers that decide the size: ratsnest length and crossings, routing demand, bus
lengths and meanders from the real pin positions, and how close the passives can get to the pins they serve.
The small parts are only dropped into their regions for those numbers (estimated_place). It is an estimate, and
the positions it finds are not used for the board.

    python floorplan.py compare           the current placement against this floorplan at several sizes
    python floorplan.py report 110 80     region fill and passive distances at one size
    python floorplan.py render 110 80     docs/pcb-floorplan.png

Frame: mm, origin at the board's lower-left corner, as in placement.py. The Pi rectangle (85 x 56) stays at
the upper-left, so the holes and the 40-pin header keep their positions and a HAT still fits.
"""
from __future__ import annotations

import collections
import math
import re
import statistics
import sys
from pathlib import Path

import numpy as np

import pcbsetup as S
import placement as P


SIZES = ((100, 70), (105, 75), (110, 80), (120, 85), (130, 95))
GAP = P.CLEAR_GAP
OUT = Path(__file__).resolve().parents[2] / "docs" / "pcb-floorplan.png"


class Plan:
    """One floorplan at one size."""

    def __init__(self, W, H):
        self.W, self.H = W, H
        self.pi_y = H - 56.0
        ux, uy = 42.0, H - 27.0
        self.u1 = (ux, uy)
        W_, H_ = W, H
        # the HDMI chain runs straight east from the DPI side of the SiP
        tfp = (ux + 24.0, uy - 5.5)
        tmds = tfp[1] + 0.7                     # middle of the TMDS band on the TFP410
        j1000 = (W_ - 4.7, tmds - 1.75 - 2.0)   # 2 mm low so its shell slots clear the M.2 card
        u1001 = (W_ - 16.6, tmds - 0.3)
        # the south edge, west to east in the order of the balls: USB1, CSI, RGMII
        j1200 = (ux + 6.0, 4.6)
        j900 = (j1200[0] - 11.5 - 8.5 - 1.0, 5.3)
        j800 = (j1200[0] + 11.5 + 9.2 + 1.0, 7.65)
        u800 = (ux + 9.0, uy - 19.4)
        m2 = (70.5, H_ - 16.0)
        emmc = (ux - 18.0, uy - 1.0)            # J700, back; centred on the MMC0 balls
        self.m2, self.emmc = m2, emmc
        self.big = {
            "U1": (ux, uy, 0, "T"),
            "J1400": (32.5, self.pi_y + 52.5, 0, "T"),
            "H1600": (3.5, self.pi_y + 3.5, 0, "T"), "H1601": (61.5, self.pi_y + 3.5, 0, "T"),
            "H1602": (3.5, self.pi_y + 52.5, 0, "T"), "H1603": (61.5, self.pi_y + 52.5, 0, "T"),
            "U1000": (tfp[0], tfp[1], 90, "T"), "U1001": (u1001[0], u1001[1], 0, "T"), "J1000": (j1000[0], j1000[1], 90, "T"),
            "J800": (j800[0], j800[1], 0, "T"), "U800": (u800[0], u800[1], 90, "T"),
            "J900": (j900[0], j900[1], 0, "T"), "U900": (j900[0] + 1.0, 24.0, 90, "T"),
            "C907": (j900[0] - 14.3, 4.2, 0, "T"), "C911": (j900[0] - 14.3, 11.7, 0, "T"),
            "J1200": (j1200[0], j1200[1], 180, "T"),
            # USB-C power and data on the west edge, level with the USB0 balls; converters south of it
            "J100": (3.185, uy - 4.0, 270, "T"), "U100": (13.5, uy - 13.0, 90, "T"),
            "U101": (14.0, uy - 25.0, 270, "T"), "L100": (14.0, uy - 32.5, 270, "T"),
            "U102": (5.0, uy - 18.0, 0, "T"), "L101": (5.0, uy - 12.4, 270, "T"),
            # the PMIC at the SiP's south-west corner, inductors towards the balls
            "U200": (ux - 12.0, uy - 12.5, 180, "T"),
            # debug in the north-west corner, narrow bus to the SiP
            "J1500": (3.185, H_ - 14.0, 270, "T"), "U1500": (16.2, H_ - 14.0, 0, "T"),
            "U1504": (28.2, H_ - 11.5, 0, "T"), "U1505": (28.2, H_ - 18.0, 0, "T"),
            "J1501": (19.0, H_ - 14.0, 0, "B"),
            # north-east: SD on the top edge, audio to its right, the M.2 card under both
            "J702": (74.5, H_ - 7.25, 180, "T"),
            "J1100": (W_ - 5.5, H_ - 6.05, 180, "T"), "U1100": (W_ - 20.0, H_ - 15.0, 90, "T"),
            # the 32 kHz crystal beside its balls: series and feedback resistors on the ball side, load caps beside it
            "Y600": (ux - 12.5, uy + 0.8, 0, "T"), "R602": (ux - 9.3, uy + 2.0, 90, "T"), "R603": (ux - 9.3, uy - 0.4, 90, "T"),
            "C602": (ux - 12.5, uy + 2.9, 0, "T"), "C603": (ux - 12.5, uy - 1.3, 0, "T"),
            "J1300": (m2[0], m2[1], 90, "B"), "H1300": (m2[0] + P.M2_STANDOFF_DX, m2[1], 0, "B"),
            "J700": (emmc[0], emmc[1], 270, "B"), "J701": (emmc[0] - 13.0, emmc[1], 270, "B"),
            # the boot DIP on the south edge beside J800; the buttons on the west edge, south of the Pi hole and clear
            # of any HAT, because their nets start on the SiP's west side
            "SW602": (j800[0] + 15.3, 6.1, 90, "T"), "SW200": (3.5, 20.0, 90, "T"),
            "SW601": (3.5, 12.0, 90, "T"), "SW600": (3.5, 4.1, 90, "T"),
        }
        self.top, self.back = self.blocks()

    def blocks(self):
        """(label, x1, y1, x2, y2, function). One region per function per side; two rectangles of one function touch."""
        W, H, (ux, uy) = self.W, self.H, self.u1
        ex, ey = self.emmc
        mx, my = self.m2
        tfp = self.big["U1000"]
        j800 = self.big["J800"]
        top = [
            ("Debug", 0.5, H - 21, ux - 5.3, H - 7.1, "dbg"),
            ("", 0.5, uy + 1.3, 8.4, H - 21, "dbg"),
            ("Expansion: header series parts", ux - 5, H - 17, 51, H - 7.1, "exp"),
            ("Board ID, sensor, I2C", 51.5, H - 21, 65.3, H - 7.1, "misc"),
            ("Clocks, reset", 17.3, uy - 6.6, ux - 8.5, uy + 5.7, "clk"),
            ("Power: PD, 3.3 V and 5 V converters", 0.5, 24.2, 18, uy - 8.8, "pwr"),
            ("", 6.8, 15.8, 18, 24.2, "pwr"),
            ("USB-C port: ESD, CC", 8.6, uy - 8.8, 17, uy + 5.5, "pwr"),
            ("PMIC, inductors, load switches", 18.5, uy - 22.5, 36, uy - 6.8, "pmic"),
            ("USB hub, ESD, VBUS switches", 18.3, 14.5, 36.2, uy - 22.8, "usb"),
            ("", 7.1, 0.5, 18.2, 15.6, "usb"),
            ("Ethernet PHY, crystal, series row", ux + 4.5, 21, 58, uy - 8, "eth"),
            ("HDMI: TFP410", tfp[0] - 7.5, tfp[1] - 13.7, tfp[0] + 8.5, tfp[1] + 7.2, "hdmi"),
            ("HDMI ESD", W - 22, tfp[1] - 6, W - 12.5, tfp[1] + 7, "hdmi"),
            ("microSD: ESD, switch", 65.5, uy + 2, 84, H - 0.5, "sd"),
            ("Audio codec", 84.5, uy + 2.5, W - 11, H - 0.5, "aud"),
            ("Boot DIP, LEDs", j800[0] + 9.8, 0.5, W - 9.5, 15, "boot"),
        ]
        back = [
            ("SiP decoupling", ux - 12, uy - 14.3, ux + 14, uy + 5.7, "sip"),
            ("", ux - 12, uy + 5.7, ux + 3, uy + 8.5, "sip"),
            ("", ux + 9.2, uy + 5.7, ux + 14, uy + 9.7, "sip"),
            ("SDIO series", ux + 3, uy + 5.9, ux + 9, uy + 9.7, "sdio"),
            ("eMMC module", ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5, "module"),
            ("eMMC pull-ups", ex + 2.8, ey - 10.5, ux - 12.2, ey + 9.5, "emmc"),
            ("", ex - 15.5, ey - 10.5, ex + 2.5, ey - 6.7, "emmc"),
            ("", ex - 15.5, ey + 6.7, ex + 2.5, ey + 9.5, "emmc"),
            ("Expansion: slew and series", ux - 5, H - 17, 57, H - 7.1, "exp"),
            ("Debug parts, Tag-Connect", 0.5, ey + 9.7, ux - 5.3, H - 7.1, "dbg"),
            ("", 0.5, uy + 1.3, 8.3, ey + 9.7, "dbg"),
            ("M.2 card: only 0402s under it", mx - 1.5, my - 11, mx + P.M2_STANDOFF_DX + 1.75, my + 11, "m2"),
            ("M.2 parts", ux + 15.3, my - 1.2, 64.5, H - 7.1, "m2"),
            ("Strap resistors on DPI, BOOTMODE", ux + 14.3, uy - 14.3, 64, uy + 5.3, "strap"),
            ("Power: filters, bulk", 0.5, 24.2, 18, ey - 10.7, "pwr"),
            ("", 7.7, 15.8, 18, 24.2, "pwr"),
            ("Button parts", 0.5, 0.5, 7.4, 24, "btn"),
            ("PMIC decoupling", 18.5, uy - 22.5, 36, uy - 14.5, "pmic"),
            ("", 18.5, uy - 14.5, ux - 12.2, ey - 10.7, "pmic"),
            ("USB: chokes, pull-downs", 18.3, 14.5, 36.2, uy - 22.8, "usb"),
            ("PHY decoupling, straps", ux + 4.5, 21, 56, uy - 14.5, "eth"),
            ("TFP410 decoupling", 64.3, tfp[1] - 13.7, tfp[0] + 8.5, tfp[1] + 5, "hdmi"),
            ("Test pads, grouped by rail", j800[0] + 9.8, 0.5, W - 0.5, 19, "test"),
            ("Camera: filter, pull-ups", self.big["J1200"][0] - 11.3, 0.5, self.big["J1200"][0] + 11.3, 7.0, "cam"),
        ]
        return top, back


# ---- which region each part belongs to

SHEET_FUNCTION = {"Debug USB-UART and JTAG": "dbg", "USB: device port, hub, USB-A host ports": "usb", "Gigabit Ethernet PHY": "eth",
                  "HDMI output (TFP410)": "hdmi", "USB-C power input and main converters": "pwr",
                  "Storage: eMMC module and microSD": "sd", "40-pin expansion header": "exp", "Clocks, reset and boot": "clk",
                  "SiP power": "sip", "M.2 Key-E Wi-Fi / Bluetooth": "m2", "Board ID, sensors, LEDs, mounting": "misc",
                  "Audio codec": "aud", "PMIC and power switches": "pmic", "Camera FPC": "cam"}
TO_USBC = {"D900", "L900", "R900", "R901", "R902", "R903", "R904", "R905", "D901"}
TO_BOOT = {"R1607", "R1608", "R1609", "R1610"}
TO_BUTTON = {"U602", "C606", "C607", "D600", "D601", "R607", "R608", "D200", "R200"}
TO_EMMC = {f"C{n}" for n in range(700, 706)} | {f"R{n}" for n in range(700, 714)} | {"U703"}
TO_SDIO = {"R1300", "R1301", "R1302", "R1303", "R1304"}


def function_of(parts):
    """Function per part: the schematic sheet, except where a part serves something placed elsewhere."""
    out = {}
    for d, pt in parts.items():
        k = SHEET_FUNCTION.get(pt.sheet, "misc")
        n = int(re.sub(r"\D", "", d) or 0)
        if d in TO_USBC:
            k = "pwr"
        elif d in TO_BOOT or d.startswith("LED"):
            k = "boot"
        elif d in TO_BUTTON:
            k = "btn"
        elif d in TO_EMMC:
            k = "emmc"
        elif d in TO_SDIO:
            k = "sdio"
        elif d[0] == "R" and 620 <= n <= 651:
            k = "strap"
        elif pt.sheet == "SiP power" and d.startswith("TP"):
            k = "test"
        out[d] = k
    return out


# ---- geometry helpers

def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def pin(parts, nets, plan, ref, net):
    for nd in nets[net]:
        r, n = nd.split(".", 1)
        if r == ref:
            q = next(q for q in parts[r].pads if q[4] == n)
            return P.xform(q[0], q[1], *plan.big[r])
    raise KeyError((ref, net))


def pads_on(parts, ref, net, place):
    return [P.xform(q[0], q[1], *place[ref]) for q in parts[ref].pads if q[2] == net]


def buses(parts, nets, plan):
    """Ball to load pin, Manhattan, per interface; meander needed to match and to reach a minimum."""
    out = {}
    tol = {"RGMII_TX": 1.52, "RGMII_RX": 1.52, "MMC0": 1.16, "MMC1": 1.16, "MMC2": 1.16, "DPI": 14.5}
    minimum = {"MMC0": 10.66, "MMC1": 20.66}
    for bus, (load, pairs) in S.BUSES.items():
        lens = {}
        for a, b in pairs:
            lens[a] = man(pin(parts, nets, plan, "U1", a), pin(parts, nets, plan, load, b))
        v = sorted(lens.values())
        target = max(v[-1] - tol[bus], minimum.get(bus, 0.0))
        meander = sum(max(0.0, target - x) for x in v)
        out[bus] = (v[0], v[-1], meander)
    pairs = {"USB0": ("U1", "USB0_DP", "J100", "USBC1_DP"), "USB1": ("U1", "USB1_DP", "U900", "USB1_DP"),
             "CSI_CLK": ("U1", "CSI_CLK_P", "J1200", "CSI_CLK_P"), "CSI_D0": ("U1", "CSI_D0_P", "J1200", "CSI_D0_P"),
             "TMDS_TX2": ("U1000", "HDMI_TX2_P", "J1000", "HDMI_TX2_P"), "TMDS_TXC": ("U1000", "HDMI_TXC_P", "J1000", "HDMI_TXC_P"),
             "MDI0": ("U800", "ETH_MDI0_P", "J800", "ETH_MDI0_P"), "MDI3": ("U800", "ETH_MDI3_P", "J800", "ETH_MDI3_P")}
    for name, (r1, n1, r2, n2) in pairs.items():
        d = man(pin(parts, nets, plan, r1, n1), pin(parts, nets, plan, r2, n2))
        out[name] = (d, d, 0.0)
    return out


def under_sip_sites(parts, with_rot=False):
    """0402 sites under the SiP on the back, relative to its centre. A site must clear every power and GND via, must
    keep both pads reachable, and must leave a via site for every signal ball that needs one: fanout.sip_signals gives
    each inner ball its own site, so this checks the whole matching, not one ball at a time."""
    import powerplanes as PP
    now = {"U1": P.read_csv()["U1"]}
    classes = S.net_classes(PP._nets())
    power = set(classes["PWR"]) | set(classes["PWR_HI"])
    plan = PP.Plan()
    PP.fanout_sip(parts, now, plan, PP.Copper(), power)
    ux, uy = now["U1"][:2]
    balls = {q[4]: (P.xform(q[0], q[1], *now["U1"]), q[2]) for q in parts["U1"].pads}
    xs = sorted({round(b[0][0], 2) for b in balls.values()})
    ys = sorted({round(b[0][1], 2) for b in balls.values()})
    fixed = {(round(v[0], 3), round(v[1], 3)) for v in plan.vias}
    inner = []
    for xy, net in balls.values():
        if not net or net == "GND" or net in power:
            continue
        ix, iy = xs.index(round(xy[0], 2)), ys.index(round(xy[1], 2))
        if min(ix, len(xs) - 1 - ix, iy, len(ys) - 1 - iy) >= 2:
            opts = [(round(xy[0] + a, 3), round(xy[1] + b, 3)) for a in (-.25, .25) for b in (-.25, .25)]
            inner.append([o for o in opts if o not in fixed])
    body = P.crt_rect(parts["U1"], *now["U1"])
    sites = []

    def touches(c, pw, ph, v):
        return abs(v[0] - c[0]) <= pw + 0.245 and abs(v[1] - c[1]) <= ph + 0.245

    def matching(blocked):
        holder = {}

        def assign(i, seen):
            for o in inner[i]:
                if o in seen or o in blocked:
                    continue
                seen.add(o)
                if o not in holder or assign(holder[o], seen):
                    holder[o] = i
                    return True
            return False

        return all(assign(i, set()) for i in range(len(inner)))

    every = {o for opts in inner for o in opts}
    blocked = set()
    for pw, ph, cw, ch in ((0.76, 0.3, 1.0, 0.55), (0.3, 0.76, 0.55, 1.0)):
        y = body[1] + ch
        while y < body[3] - ch:
            x = body[0] + cw
            while x < body[2] - cw:
                c = (x, y)
                ok = not any(touches(c, pw, ph, v) for v in fixed)
                ok = ok and all(abs(q[0] - x) >= q[2] + cw + GAP or abs(q[1] - y) >= q[3] + ch + GAP for q in sites)
                if ok:
                    new = {o for o in every if touches(c, pw, ph, o)}
                    if matching(blocked | new):
                        blocked |= new
                        sites.append((x, y, cw, ch, pw, ph))
                x += 0.25
            y += 0.25
    if with_rot:
        return [(round(q[0] - ux, 3), round(q[1] - uy, 3), 0 if q[2] == 1.0 else 90) for q in sites]
    return [(q[0] - ux, q[1] - uy) for q in sites]


class Sheet:
    """Which 0.25 mm cells of each side are taken."""

    def __init__(self, W, H):
        self.nx, self.ny = int(W * 4) + 1, int(H * 4) + 1
        self.occ = {"T": np.zeros((self.nx, self.ny), bool), "B": np.zeros((self.nx, self.ny), bool)}

    def cells(self, r, pad=GAP / 2):
        return (max(0, int(round((r[0] - pad) * 4))), min(self.nx, int(round((r[2] + pad) * 4))),
                max(0, int(round((r[1] - pad) * 4))), min(self.ny, int(round((r[3] + pad) * 4))))

    def free(self, side, r):
        a, b, c, d = self.cells(r)
        return not self.occ[side][a:b, c:d].any()

    def take(self, side, r, pad=GAP / 2):
        a, b, c, d = self.cells(r, pad)
        self.occ[side][a:b, c:d] = True


def estimated_place(parts, nets, plan, under=None):
    """Big parts where the plan puts them; each small part at the free spot of its own function's regions nearest
    what it serves, keeping the 10 mil spacing. Vias and routing room are not modelled, so this is the best case."""
    fn = function_of(parts)
    rects = collections.defaultdict(list)
    for side, blocks in (("T", plan.top), ("B", plan.back)):
        for lab, x1, y1, x2, y2, key in blocks:
            rects[key].append((side, x1, y1, x2, y2))
    place = dict(plan.big)
    sheet = Sheet(plan.W, plan.H)
    for d, v in plan.big.items():
        sheet.take(v[3], P.crt_rect(parts[d], *v))
        other = "B" if v[3] == "T" else "T"
        for h in parts[d].holes:
            a, b = P.xform(h[0], h[1], *v), P.xform(h[2], h[3], *v)
            sheet.take(other, (min(a[0], b[0]) - 0.6, min(a[1], b[1]) - 0.6, max(a[0], b[0]) + 0.6, max(a[1], b[1]) + 0.6), 0.0)
    sheet.take("B", P.crt_rect(parts["U1"], *plan.big["U1"]), 0.0)      # the SiP's via field
    ex, ey = plan.emmc
    sheet.take("B", (ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5))          # under the eMMC module
    offsets = {}

    def offs(d, rot, side):
        k = (d, rot, side)
        if k not in offsets:
            offsets[k] = P.crt_rect(parts[d], 0.0, 0.0, rot, side)
        return offsets[k]

    def ic(d):
        return d in place and (len(parts[d].pads) > 2 or d[0] == "Y")

    uses = collections.Counter()

    def rail_target(d, net):
        """The pin on this rail with the fewest caps so far, on an IC of this function if there is one."""
        pins = []
        for nd in nets[net]:
            r, n = nd.split(".", 1)
            if r in parts and ic(r):
                q = next((q for q in parts[r].pads if q[4] == n), None)
                if q:
                    same = fn.get(r) == fn[d] or (fn[d] == "sip" and r == "U1")
                    pins.append((not same, uses[nd], nd, P.xform(q[0], q[1], *place[r]), place[r][3]))
        if not pins:
            return None
        pins.sort(key=lambda t: t[:3])
        if not pins[0][0]:
            pins = [p for p in pins if not p[0]]
        uses[pins[0][2]] += 1
        return pins[0][3], pins[0][4]

    def signal_target(d):
        xs, ys, sides = [], [], []
        ic_pins = []
        for q in parts[d].pads:
            net = q[2]
            if not net or net == "GND" or net.startswith("NC") or P.is_rail(net, nets.get(net, [])):
                continue
            for nd in nets.get(net, []):
                r, n = nd.split(".", 1)
                if r != d and r in place and r in parts:
                    q2 = next((c for c in parts[r].pads if c[4] == n), None)
                    if q2:
                        x, y = P.xform(q2[0], q2[1], *place[r])
                        xs.append(x)
                        ys.append(y)
                        sides.append(place[r][3])
                        if r == "U1" or len(parts[r].pads) > 2 or r[0] == "Y":
                            ic_pins.append((r != "U1", x, y, place[r][3]))
        if not xs:
            return None
        if ic_pins and len(parts[d].pads) == 2:
            # a two-pin part sits by the pin it serves, the SiP's first; not half way along its net
            r = rects[fn[d]][0]
            cx, cy = (r[1] + r[3]) / 2, (r[2] + r[4]) / 2
            ic_pins.sort(key=lambda t: (t[0], abs(t[1] - cx) + abs(t[2] - cy)))
            return (ic_pins[0][1], ic_pins[0][2]), ic_pins[0][3]
        return (sum(xs) / len(xs), sum(ys) / len(ys)), collections.Counter(sides).most_common(1)[0][0]

    no_room = []

    def drop(d, target, tside):
        best = None
        for side, x1, y1, x2, y2 in rects[fn[d]]:
            for rot in (0, 90):
                o = offs(d, rot, side)
                xs = np.arange(x1 - o[0], x2 - o[2] + 1e-6, 0.25)
                ys = np.arange(y1 - o[1], y2 - o[3] + 1e-6, 0.25)
                if len(xs) == 0 or len(ys) == 0:
                    continue
                gx, gy = np.meshgrid(xs, ys, indexing="ij")
                cost = np.abs(gx - target[0]) + np.abs(gy - target[1]) + (0.0 if side == tside else 1.0)
                for i in np.argsort(cost, axis=None):
                    a, b = np.unravel_index(i, cost.shape)
                    x, y = float(gx[a, b]), float(gy[a, b])
                    if best is not None and cost[a, b] >= best[0]:
                        break
                    if sheet.free(side, (x + o[0], y + o[1], x + o[2], y + o[3])):
                        best = (float(cost[a, b]), x, y, rot, side, o)
                        break
        if best is None:
            no_room.append(d)
            r = rects[fn[d]][0]
            place[d] = ((r[1] + r[3]) / 2, (r[2] + r[4]) / 2, 0, r[0])
            return
        _, x, y, rot, side, o = best
        place[d] = (x, y, rot, side)
        sheet.take(side, (x + o[0], y + o[1], x + o[2], y + o[3]))

    small = [d for d in parts if d not in place]
    is_cap = {d: d[0] == "C" and any(q[2] == "GND" for q in parts[d].pads) for d in small}
    rail_of = {}
    for d in small:
        for q in parts[d].pads:
            # a cap to GND serves whatever it hangs on, a filtered analog rail included
            if q[2] and q[2] != "GND" and (is_cap[d] or P.is_rail(q[2], nets.get(q[2], []))):
                rail_of[d] = q[2]
                break
    # the crystal and ICs first, so their passives have something to sit beside
    first = [d for d in small if len(parts[d].pads) > 2 or d[0] == "Y"]
    first.sort(key=lambda d: fn[d])
    for d in first:
        t = signal_target(d)
        if t is None:
            r = rects[fn[d]][0]
            t = (((r[1] + r[3]) / 2, (r[2] + r[4]) / 2), r[0])
        drop(d, t[0], t[1])
    # SiP decoupling: the sites under the body first, to the caps whose balls are nearest
    caps = [d for d in small if is_cap[d] and fn[d] == "sip" and d in rail_of]
    sites = list(under if under is not None else under_sip_sites(parts))
    ux, uy = plan.big["U1"][:2]
    pairs = []
    per_rail = collections.Counter(rail_of[d] for d in caps)
    for d in caps:
        balls = pads_on(parts, "U1", rail_of[d], place)
        if balls:
            for s in sites:
                pairs.append((min(math.hypot(ux + s[0] - b[0], uy + s[1] - b[1]) for b in balls), d, s))
    done = set()
    served = set()
    for d, s in ((("C361", (-4.75, 0.5)),) if "C361" in caps else ()):
        s = min(sites, key=lambda q: math.hypot(q[0] - s[0], q[1] - s[1]))
        place[d] = (ux + s[0], uy + s[1], 0, "B")
        done.add(d)
        served.add(rail_of[d])
        sites.remove(s)
    for only_new_rails in (True, False):
        order = sorted(pairs, key=lambda t: (per_rail[rail_of[t[1]]], t[0])) if only_new_rails else sorted(pairs, key=lambda t: t[0])
        for dist, d, s in order:
            if d in done or s not in sites or (only_new_rails and rail_of[d] in served):
                continue
            place[d] = (ux + s[0], uy + s[1], 0, "B")
            done.add(d)
            served.add(rail_of[d])
            sites.remove(s)
    for d in sorted((d for d in small if is_cap[d] and d in rail_of and d not in done), key=lambda d: fn[d] != "sip"):
        t = rail_target(d, rail_of[d])
        if t is None:
            r = rects[fn[d]][0]
            t = (((r[1] + r[3]) / 2, (r[2] + r[4]) / 2), r[0])
        drop(d, t[0], t[1])
    # everything else, those with the most placed neighbours first
    rest = [d for d in small if d not in place]
    while rest:
        scored = [(signal_target(d), d) for d in rest]
        ready = [(t, d) for t, d in scored if t is not None]
        if ready:
            for t, d in ready:
                drop(d, t[0], t[1])
                rest.remove(d)
        else:
            for d in rest:
                t = rail_target(d, rail_of[d]) if d in rail_of else None
                if t is None:
                    r = rects[fn[d]][0]
                    t = (((r[1] + r[3]) / 2, (r[2] + r[4]) / 2), r[0])
                drop(d, t[0], t[1])
            rest = []
    place["__no_room__"] = no_room
    return place


# ---- the numbers

_POWER = None


def is_power(net, nodes):
    """Every net that goes on the power pours, however few pins it has."""
    global _POWER
    if _POWER is None:
        import powerplanes as PP
        classes = S.net_classes(PP._nets())
        _POWER = set(classes["PWR"]) | set(classes["PWR_HI"])
    return net in _POWER or P.is_rail(net, nodes)


def crossings(parts, nets, place):
    """Signal ratsnest: spanning-tree length and how many of its lines cross."""
    segs = []
    total = 0.0
    for net, nodes in nets.items():
        if net.startswith("NC") or is_power(net, nodes):
            continue
        pts = []
        for nd in nodes:
            r, n = nd.split(".", 1)
            if r in place and r in parts:
                q = next((q for q in parts[r].pads if q[4] == n), None)
                if q:
                    pts.append(P.xform(q[0], q[1], *place[r]))
        if len(pts) < 2:
            continue
        seen, rest = [pts[0]], pts[1:]
        while rest:
            d, a, c = min(((man(a, c), a, c) for a in seen for c in rest), key=lambda t: t[0])
            total += d
            seen.append(c)
            rest.remove(c)
            segs.append((a, c))

    def ccw(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    n = 0
    for i, (a, b) in enumerate(segs):
        ax1, ax2 = min(a[0], b[0]), max(a[0], b[0])
        ay1, ay2 = min(a[1], b[1]), max(a[1], b[1])
        for c, d in segs[i + 1:]:
            if max(c[0], d[0]) < ax1 or min(c[0], d[0]) > ax2 or max(c[1], d[1]) < ay1 or min(c[1], d[1]) > ay2:
                continue
            if ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
                n += 1
    return total, n, len(segs)


def bus_crossings(parts, nets, plan):
    """Crossings between different main buses, ball to load pin in straight lines: each one needs a layer change."""
    lines = {}
    for bus, (load, pairs) in S.BUSES.items():
        lines[bus] = [(pin(parts, nets, plan, "U1", a), pin(parts, nets, plan, load, b)) for a, b in pairs]
    pairs = {"USB0": ("U1", "J100", (("USB0_DP", "USBC1_DP"), ("USB0_DM", "USBC1_DM"))),
             "USB1": ("U1", "U900", (("USB1_DP", "USB1_DP"), ("USB1_DM", "USB1_DM"))),
             "CSI": ("U1", "J1200", tuple((f"CSI_{n}", f"CSI_{n}") for n in ("CLK_P", "CLK_N", "D0_P", "D0_N", "D1_P", "D1_N"))),
             "TMDS": ("U1000", "J1000", tuple((f"HDMI_{n}", f"HDMI_{n}") for n in ("TX0_P", "TX0_N", "TX1_P", "TX1_N", "TX2_P", "TX2_N", "TXC_P", "TXC_N"))),
             "MDI": ("U800", "J800", tuple((f"ETH_MDI{i}_{e}", f"ETH_MDI{i}_{e}") for i in range(4) for e in "PN"))}
    for bus, (r1, r2, nn) in pairs.items():
        lines[bus] = [(pin(parts, nets, plan, r1, a), pin(parts, nets, plan, r2, b)) for a, b in nn]

    def ccw(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    total = 0
    per = collections.Counter()
    names = sorted(lines)
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            for a, b in lines[x]:
                for c, d in lines[y]:
                    if ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
                        total += 1
                        per[(x, y)] += 1
    return total, per


def demand(parts, nets, place, W, H, cell=2.0):
    """RUDY as in placement.congestion, on a board of any size, four signal layers."""
    nx, ny = int(W / cell), int(H / cell)
    grid = [[0.0] * ny for _ in range(nx)]
    hp = 0.0
    for net, nodes in nets.items():
        if is_power(net, nodes) or net.startswith("NC"):
            continue
        pts = []
        for nd in nodes:
            r, n = nd.split(".", 1)
            if r in place and r in parts:
                q = next((q for q in parts[r].pads if q[4] == n), None)
                if q:
                    pts.append(P.xform(q[0], q[1], *place[r]))
        if len(pts) < 2:
            continue
        x1, x2 = min(p[0] for p in pts), max(p[0] for p in pts)
        y1, y2 = min(p[1] for p in pts), max(p[1] for p in pts)
        w, h = max(x2 - x1, cell), max(y2 - y1, cell)
        hp += (x2 - x1) + (y2 - y1)
        dens = ((x2 - x1) + (y2 - y1)) * 1.3 / (w * h)
        for i in range(max(0, int(x1 / cell)), min(nx - 1, int(x2 / cell)) + 1):
            for j in range(max(0, int(y1 / cell)), min(ny - 1, int(y2 / cell)) + 1):
                grid[i][j] += dens
    cap = 4 * (1 / 0.30) * 0.5
    cells = [v / cap for col in grid for v in col]
    return {"peak": max(cells), "over_mm2": sum(1 for v in cells if v > 1.0) * cell * cell,
            "over_70_mm2": sum(1 for v in cells if v > 0.7) * cell * cell,
            "whole": hp * 1.3 / (W * H * cap)}


def density(parts, plan, area=6199.0, tht=1204.0):
    """Effective share of both sides, as in docs/pcb-placement.md."""
    eff = area + tht + 161 + 193 + 71
    return eff / (2 * plan.W * plan.H)


def served_distance(parts, nets, place, d):
    """Straight-line distance from a passive's pad to the nearest pin it serves: an IC or connector pin on the
    same net (a crystal or an inductor counts). GND is not served. None when no such pin exists, as for a divider's
    midpoint."""
    best = None
    for q in parts[d].pads:
        net = q[2]
        if not net or net == "GND" or net not in nets:
            continue
        a = P.xform(q[0], q[1], *place[d])
        for nd in nets[net]:
            r, n = nd.split(".", 1)
            if r == d or r not in parts or r not in place:
                continue
            if len(parts[r].pads) <= 2 and r[0] not in "YL":
                continue
            q2 = next((c for c in parts[r].pads if c[4] == n), None)
            if q2:
                b = P.xform(q2[0], q2[1], *place[r])
                dist = math.hypot(a[0] - b[0], a[1] - b[1])
                if best is None or dist < best:
                    best = dist
    return best


def passive_stats(parts, nets, place):
    """Share of passives within 3 and 5 mm of the pin they serve, overall and for decoupling; SiP decoupling alone."""
    every, decoup, sip = [], [], []
    for d, pt in parts.items():
        if d not in place or not re.match(r"(R|C|L|FB)\d", d) or len(pt.pads) != 2:
            continue
        v = served_distance(parts, nets, place, d)
        if v is None:
            continue
        every.append(v)
        names = {q[2] for q in pt.pads}
        if d[0] == "C" and "GND" in names:
            decoup.append(v)
            if pt.sheet == "SiP power":
                sip.append(v)

    def share(v, lim):
        return 100.0 * sum(1 for x in v if x <= lim) / max(1, len(v))

    return {"all_3": share(every, 3), "all_5": share(every, 5), "dec_3": share(decoup, 3), "dec_5": share(decoup, 5),
            "n_all": len(every), "n_dec": len(decoup), "sip_median": statistics.median(sip), "sip_worst": max(sip),
            "all_median": statistics.median(every), "dec_median": statistics.median(decoup)}


def named(parts, nets, place):
    """The parts called out in the review, distances in mm."""
    def between(a, net, b):
        pa, pb = pads_on(parts, a, net, place), pads_on(parts, b, net, place)
        return min(math.hypot(x[0] - y[0], x[1] - y[1]) for x in pa for y in pb)

    out = {"C602 to Y600": between("C602", "LFOSC_XI", "Y600"), "R602 to Y600": between("R602", "LFOSC_XO_X", "Y600"),
           "R602 to ball H2": between("R602", "LFOSC_XO", "U1"), "C339 to ball N7": between("C339", "VDDA_3P3_USB", "U1")}
    series = [between(f"R130{i}", n, "U1") for i, n in enumerate(("WL_SDIO_CMD", "WL_SDIO_D0", "WL_SDIO_D1", "WL_SDIO_D2", "WL_SDIO_D3"))]
    out["R1300-R1304 to balls"] = (min(series), max(series))
    return out


def checks(parts, plan):
    """Same-side overlaps between big parts and between regions, through-holes under the module or card, parts off the edge."""
    probs = []
    rects = {d: (v[3], P.crt_rect(parts[d], *v)) for d, v in plan.big.items()}
    names = sorted(rects)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if rects[a][0] != rects[b][0]:
                continue
            ra, rb = rects[a][1], rects[b][1]
            g = max(ra[0] - rb[2], rb[0] - ra[2], ra[1] - rb[3], rb[1] - ra[3])
            if g < GAP:
                probs.append((round(g, 2), a, b))
    for side, blocks in (("T", plan.top), ("B", plan.back)):
        for i, a in enumerate(blocks):
            for b in blocks[i + 1:]:
                if min(a[3], b[3]) - max(a[1], b[1]) > 0.01 and min(a[4], b[4]) - max(a[2], b[2]) > 0.01:
                    probs.append(("regions", side, a[0][:18] or a[5], b[0][:18] or b[5]))
    mx, my = plan.m2
    ex, ey = plan.emmc
    boxes = {"card": (mx - 1.5, my - 11, mx + P.M2_STANDOFF_DX + 1.75, my + 11), "module": (ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5)}
    for d, v in plan.big.items():
        if v[3] != "T":
            continue
        for hole in parts[d].holes:
            a = P.xform(hole[0], hole[1], *v)
            b = P.xform(hole[2], hole[3], *v)
            for name, bx in boxes.items():
                if min(a[0], b[0]) < bx[2] and bx[0] < max(a[0], b[0]) and min(a[1], b[1]) < bx[3] and bx[1] < max(a[1], b[1]):
                    probs.append((name, d, "hole"))
    for d, v in plan.big.items():
        r = P.crt_rect(parts[d], *v)
        if d in ("J100", "J1500", "J800", "J900", "J1000", "J1100", "J702"):
            continue                     # these overhang the edge on purpose
        if r[0] < 0 or r[1] < 0 or r[2] > plan.W or r[3] > plan.H:
            probs.append(("edge", d, tuple(round(q, 1) for q in r)))
    return probs


def fill(parts, plan):
    """Area the small parts of each function need, with spacing, against the free area of its regions."""
    fn = function_of(parts)
    need = collections.Counter()
    count = collections.Counter()
    for d, pt in parts.items():
        if d in plan.big:
            continue
        r = P.crt_rect(pt, 0, 0, 0, "T")
        need[fn[d]] += (r[2] - r[0] + GAP) * (r[3] - r[1] + GAP)
        count[fn[d]] += 1
    free = collections.Counter()
    for side, blocks in (("T", plan.top), ("B", plan.back)):
        for lab, x1, y1, x2, y2, key in blocks:
            a = (x2 - x1) * (y2 - y1)
            for d, v in plan.big.items():
                if v[3] != side:
                    continue
                r = P.crt_rect(parts[d], *v)
                ix, iy = min(r[2], x2) - max(r[0], x1), min(r[3], y2) - max(r[1], y1)
                if ix > 0 and iy > 0:
                    a -= ix * iy
            free[key] += max(a, 0.0)
    return {k: (count[k], need[k], free[k]) for k in sorted(need)}


def compare():
    parts, nets = P.load_parts()
    now = P.read_csv()

    class Current:
        pass

    cur = Current()
    cur.big = {d: now[d] for d in now}
    t, c, n = crossings(parts, nets, now)
    d = demand(parts, nets, now, P.BOARD_W, P.BOARD_H)
    print(f"current 100x70: ratsnest {t:.0f} mm, {c} crossings of {n} lines; peak {d['peak']:.2f}, over 100% {d['over_mm2']:.0f} mm2, "
          f"over 70% {d['over_70_mm2']:.0f} mm2, whole {d['whole']*100:.0f}%")
    print("   ", {k: tuple(round(x, 1) for x in v) for k, v in buses(parts, nets, cur).items()})
    print("    bus crossings", bus_crossings(parts, nets, cur))
    under = under_sip_sites(parts)
    for W, H in SIZES:
        pl = Plan(W, H)
        print(f"--- {W}x{H}: effective {density(parts, pl)*100:.0f}%; problems {checks(parts, pl)}")
        est = estimated_place(parts, nets, pl, under)
        lost = est.pop("__no_room__")
        d = demand(parts, nets, est, W, H)
        t, c, n = crossings(parts, nets, est)
        print(f"    ratsnest {t:.0f} mm, {c} crossings; peak {d['peak']:.2f}, over 100% {d['over_mm2']:.0f} mm2, over 70% {d['over_70_mm2']:.0f} mm2, "
              f"whole {d['whole']*100:.0f}%; parts with no room in their region {len(lost)}")
        print("   ", {k: tuple(round(x, 1) for x in v) for k, v in buses(parts, nets, pl).items()})
        print("    bus crossings", bus_crossings(parts, nets, pl))


def report(W, H):
    parts, nets = P.load_parts()
    now = P.read_csv()
    pl = Plan(W, H)
    print("problems", checks(parts, pl))
    print("function  parts  need mm2  free mm2  fill")
    for k, (n, need, free) in fill(parts, pl).items():
        print(f"  {k:7s} {n:5d} {need:9.0f} {free:9.0f} {100 * need / max(free, 1):4.0f}%")
    est = estimated_place(parts, nets, pl)
    lost = est.pop("__no_room__")
    print("parts with no room", lost)
    print("now ", {k: round(v, 1) for k, v in passive_stats(parts, nets, now).items()})
    print("plan", {k: round(v, 1) for k, v in passive_stats(parts, nets, est).items()})
    print("now ", {k: (tuple(round(x, 1) for x in v) if isinstance(v, tuple) else round(v, 1)) for k, v in named(parts, nets, now).items()})
    print("plan", {k: (tuple(round(x, 1) for x in v) if isinstance(v, tuple) else round(v, 1)) for k, v in named(parts, nets, est).items()})


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "compare":
        compare()
    elif what == "report":
        report(float(sys.argv[2]), float(sys.argv[3]))
    elif what == "render":
        import floorplan_draw
        floorplan_draw.render(float(sys.argv[2]), float(sys.argv[3]))
