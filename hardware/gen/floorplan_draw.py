"""Draws the floorplan in floorplan.py as one PNG: top side, back side, power flow, and the numbers that matter.

    python floorplan.py render 110 80     docs/pcb-floorplan.png

The back side is drawn as seen through the board from the top, so a point on one panel is the same point on the
other.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

import floorplan as F
import placement as P

SCALE = 11.0          # px per mm on the two main panels
SMALL = 7.0           # px per mm on the power panel
MARGIN = 54
FONT_DIR = "C:/Windows/Fonts/"

INK = (32, 36, 44)
MUTED = (96, 104, 116)
EDGE = (20, 24, 30)
BUS = (22, 60, 130)
DC = (120, 76, 20)
POWER = (190, 34, 30)
GHOST = (120, 128, 140)
PANEL_BG = (255, 255, 255)

# fill, outline, per function
COLOURS = {
    "pwr": ((252, 226, 216), (200, 96, 70)), "pmic": ((255, 214, 170), (205, 120, 40)),
    "usb": ((208, 228, 250), (70, 120, 190)), "eth": ((200, 238, 228), (50, 150, 125)),
    "hdmi": ((228, 216, 248), (125, 90, 190)), "sd": ((214, 240, 200), (95, 160, 70)),
    "emmc": ((214, 240, 200), (95, 160, 70)), "module": ((188, 226, 170), (80, 145, 60)),
    "m2": ((240, 238, 190), (160, 150, 50)), "sdio": ((240, 238, 190), (160, 150, 50)),
    "exp": ((222, 228, 236), (110, 125, 145)), "dbg": ((206, 212, 224), (90, 100, 125)),
    "clk": ((255, 240, 170), (190, 155, 30)), "strap": ((248, 228, 190), (170, 130, 60)),
    "sip": ((250, 214, 232), (190, 80, 140)), "aud": ((200, 240, 244), (50, 150, 165)),
    "boot": ((236, 224, 208), (140, 110, 75)), "test": ((236, 224, 208), (140, 110, 75)), "btn": ((236, 224, 208), (140, 110, 75)),
    "misc": ((234, 234, 234), (130, 130, 130)), "cam": ((222, 246, 214), (110, 170, 90)),
}
LEGEND = [("sip", "SiP decoupling"), ("clk", "Clocks, reset"), ("strap", "Boot and DPI straps"), ("pmic", "PMIC"),
          ("pwr", "USB-C, converters"), ("usb", "USB hub, USB-A"), ("eth", "Ethernet"), ("cam", "Camera"),
          ("hdmi", "HDMI"), ("sd", "eMMC, microSD"), ("m2", "M.2, SDIO"), ("aud", "Audio"),
          ("exp", "40-pin header"), ("dbg", "Debug"), ("misc", "Board ID, sensor"), ("boot", "Buttons, LEDs, test pads")]

CONNECTORS = {"J100": "J100 USB-C", "J1500": "J1500 debug", "J900": "J900 USB-A x2", "J1200": "J1200 camera FPC, vertical",
              "J800": "J800 RJ45", "J1000": "J1000 HDMI", "J702": "J702 microSD", "J1100": "J1100 audio",
              "J1400": "J1400 40-pin header", "J700": "J700", "J701": "J701", "J1300": "J1300 M.2",
              "J1501": "J1501 Tag-Connect"}
ICS = {"U1": "U1 SiP", "U200": "U200 PMIC", "U800": "U800 PHY", "U900": "U900 hub", "U1000": "U1000 TFP410", "U1001": "U1001 ESD",
       "U1100": "U1100 codec", "U1500": "U1500 FT4232", "U1504": "U1504 shift", "U1505": "U1505 shift", "U100": "U100 PD",
       "U101": "U101 3V3", "L100": "L100", "U102": "U102 5V", "L101": "L101", "SW602": "SW602 boot DIP", "SW200": "SW200",
       "SW601": "SW601", "SW600": "SW600", "C907": "C907 bulk", "C911": "C911 bulk", "Y600": "Y600"}
TINY = {"R602", "R603", "C602", "C603"}


def font(size, bold=False):
    return ImageFont.truetype(FONT_DIR + ("arialbd.ttf" if bold else "arial.ttf"), int(size))


class Panel:
    def __init__(self, draw, ox, oy, scale, plan):
        self.d, self.ox, self.oy, self.s, self.plan = draw, ox, oy, scale, plan

    def xy(self, x, y):
        return self.ox + x * self.s, self.oy + (self.plan.H - y) * self.s

    def rect(self, x1, y1, x2, y2, fill=None, outline=None, width=1):
        a, b = self.xy(x1, y2), self.xy(x2, y1)
        self.d.rectangle([a, b], fill=fill, outline=outline, width=width)

    def dashed_rect(self, x1, y1, x2, y2, colour, dash=7, width=1):
        for a, b in (((x1, y1), (x2, y1)), ((x2, y1), (x2, y2)), ((x2, y2), (x1, y2)), ((x1, y2), (x1, y1))):
            self.dashed(self.xy(*a), self.xy(*b), colour, dash, width)

    def dashed(self, a, b, colour, dash=7, width=1):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L == 0:
            return
        n = int(L / dash)
        for i in range(0, n, 2):
            t1, t2 = i / max(n, 1), min((i + 1) / max(n, 1), 1.0)
            self.d.line([(a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1),
                         (a[0] + (b[0] - a[0]) * t2, a[1] + (b[1] - a[1]) * t2)], fill=colour, width=width)

    def text(self, x, y, s, f, fill=INK, anchor="la"):
        self.d.text(self.xy(x, y), s, font=f, fill=fill, anchor=anchor)

    def wrapped(self, x, y, w_mm, s, f, fill=INK):
        """Wrap into a width in mm, starting at the top-left point."""
        words, line, lines = s.split(), "", []
        w = w_mm * self.s
        for word in words:
            t = (line + " " + word).strip()
            if self.d.textlength(t, font=f) <= w or not line:
                line = t
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        px, py = self.xy(x, y)
        h = f.size + 2
        for i, t in enumerate(lines):
            self.d.text((px, py + i * h), t, font=f, fill=fill)

    def arrow(self, pts, colour=BUS, width=4, dashed=False, both=False):
        q = [self.xy(*p) for p in pts]
        for a, b in zip(q, q[1:]):
            if dashed:
                self.dashed(a, b, colour, 9, width)
            else:
                self.d.line([a, b], fill=colour, width=width)
        self.head(q[-2], q[-1], colour, width)
        if both:
            self.head(q[1], q[0], colour, width)
        for p in q[1:-1]:
            r = width / 2
            self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=colour)

    def head(self, a, b, colour, width):
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        size = 7 + width * 1.6
        self.d.polygon([b, (b[0] - ux * size - uy * size * 0.55, b[1] - uy * size + ux * size * 0.55),
                        (b[0] - ux * size + uy * size * 0.55, b[1] - uy * size - ux * size * 0.55)], fill=colour)

    def tag(self, x, y, s, f, colour=BUS):
        """A label on a white chip, centred on the point."""
        px, py = self.xy(x, y)
        lines = s.split("\n")
        w = max(self.d.textlength(t, font=f) for t in lines)
        h = (f.size + 2) * len(lines)
        self.d.rectangle([px - w / 2 - 4, py - h / 2 - 2, px + w / 2 + 4, py + h / 2 + 2], fill=(255, 255, 255), outline=colour)
        for i, t in enumerate(lines):
            self.d.text((px - w / 2, py - h / 2 + i * (f.size + 2)), t, font=f, fill=colour)


def board(p, label_edges=True):
    plan = p.plan
    p.rect(0, 0, plan.W, plan.H, fill=PANEL_BG, outline=None)


def outline_and_frame(p, parts):
    plan = p.plan
    p.rect(0, 0, plan.W, plan.H, outline=EDGE, width=3)
    # the Pi frame: holes and header keep their positions, so a HAT fits
    p.dashed_rect(0, plan.pi_y, 85, plan.H, GHOST, 8, 1)
    p.text(86.0, plan.pi_y + 1.6, "Pi frame 85 x 56:", font(12), MUTED)
    p.text(86.0, plan.pi_y + 0.2, "holes, header unchanged", font(12), MUTED)
    # millimetre ticks
    f = font(12)
    for x in range(0, int(plan.W) + 1, 10):
        a = p.xy(x, 0)
        p.d.line([a, (a[0], a[1] + 6)], fill=MUTED)
        p.d.text((a[0], a[1] + 8), str(x), font=f, fill=MUTED, anchor="ma")
    for y in range(0, int(plan.H) + 1, 10):
        a = p.xy(0, y)
        p.d.line([a, (a[0] - 6, a[1])], fill=MUTED)
        p.d.text((a[0] - 9, a[1]), str(y), font=f, fill=MUTED, anchor="rm")


def holes(p, parts, big):
    for d in ("H1600", "H1601", "H1602", "H1603", "H1300"):
        v = big[d]
        cx, cy = p.xy(v[0], v[1])
        r = 2.75 / 2 * p.s if d != "H1300" else 1.6 * p.s
        p.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255), outline=EDGE, width=2)
        r2 = r * 0.45
        p.d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(80, 84, 92))


def label_inside(p, r, text, f, fill):
    """Text fitted inside a rectangle in mm, turned to run along a tall part when that fits better."""
    px1, py2 = p.xy(r[0], r[1])
    px2, py1 = p.xy(r[2], r[3])
    w, h = px2 - px1, py2 - py1
    tw = p.d.textlength(text, font=f)
    if tw + 6 <= w or h <= 1.7 * w:
        words = text.split()
        lines = [text]
        if tw + 6 > w and len(words) > 1:
            lines, line = [], ""
            for word in words:
                t = (line + " " + word).strip()
                if p.d.textlength(t, font=f) <= w - 4 or not line:
                    line = t
                else:
                    lines.append(line)
                    line = word
            lines.append(line)
        total = (f.size + 2) * len(lines)
        for i, t in enumerate(lines):
            p.d.text(((px1 + px2) / 2, (py1 + py2) / 2 - total / 2 + i * (f.size + 2)), t, font=f, fill=fill, anchor="ma")
    else:
        img = Image.new("RGBA", (int(tw) + 4, f.size + 6), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((2, 1), text, font=f, fill=fill + (255,))
        img = img.rotate(90, expand=True)
        p.base.paste(img, (int((px1 + px2) / 2 - img.width / 2), int((py1 + py2) / 2 - img.height / 2)), img)


def side_panel(p, parts, side, label_at):
    plan, big = p.plan, p.plan.big
    board(p)
    blocks = plan.top if side == "T" else plan.back
    fb = font(14)
    for lab, x1, y1, x2, y2, key in blocks:
        fill, line = COLOURS[key]
        p.rect(x1, y1, x2, y2, fill=fill, outline=line, width=1)
    # hide the seams between two rectangles of one function: redraw the fills without an outline, inset
    for lab, x1, y1, x2, y2, key in blocks:
        fill, line = COLOURS[key]
        p.rect(x1 + 0.1, y1 + 0.1, x2 - 0.1, y2 - 0.1, fill=fill)
    # what the other side costs this one
    if side == "B":
        ux, uy = plan.u1
        r = P.crt_rect(parts["U1"], *big["U1"])
        p.rect(r[0], r[1], r[2], r[3], fill=COLOURS["sip"][0])
        for d, v in big.items():
            if v[3] != "T" or not parts[d].holes or d.startswith("H1"):
                continue
            boxes = []
            for h in parts[d].holes:
                q, w = P.xform(h[0], h[1], *v), P.xform(h[2], h[3], *v)
                boxes.append((min(q[0], w[0]) - 0.8, min(q[1], w[1]) - 0.8, max(q[0], w[0]) + 0.8, max(q[1], w[1]) + 0.8))
            if len(boxes) > 2:
                boxes = [(min(q[0] for q in boxes), min(q[1] for q in boxes), max(q[2] for q in boxes), max(q[3] for q in boxes))]
            for q in boxes:
                q = (max(q[0], 0.0), max(q[1], 0.0), min(q[2], plan.W), min(q[3], plan.H))
                p.rect(q[0], q[1], q[2], q[3], fill=(226, 228, 232), outline=GHOST, width=1)
            if len(boxes) == 1:
                label_inside(p, boxes[0], f"{d} tails", font(13), MUTED)
        for d in ("U1", "U1000", "U1100", "U800", "U900", "U200"):
            r = P.crt_rect(parts[d], *big[d])
            p.dashed_rect(r[0], r[1], r[2], r[3], GHOST, 6, 1)
        r = P.crt_rect(parts["U1"], *big["U1"])
        p.tag((r[0] + r[2]) / 2 + 1.5, (r[1] + r[3]) / 2, "Under U1: via field,\n21 cap sites clear of it", font(14), COLOURS["sip"][1])
    else:
        ex, ey = plan.emmc
        mx, my = plan.m2
        p.dashed_rect(ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5, GHOST, 6, 1)
        p.dashed_rect(mx - 1.5, my - 11, mx + P.M2_STANDOFF_DX + 1.75, my + 11, GHOST, 6, 1)
    for d, v in big.items():
        if v[3] != side or d.startswith("H1") or d in TINY:
            continue
        r = P.crt_rect(parts[d], *v)
        r = (max(r[0], 0.0), max(r[1], 0.0), min(r[2], plan.W), min(r[3], plan.H))
        if d in CONNECTORS:
            p.rect(r[0], r[1], r[2], r[3], fill=(52, 60, 74), outline=EDGE, width=2)
            label_inside(p, r, CONNECTORS[d], font(14, True), (255, 255, 255))
        else:
            dark = d == "U1"
            p.rect(r[0], r[1], r[2], r[3], fill=(120, 30, 70) if dark else (150, 158, 170), outline=EDGE, width=1)
            label_inside(p, r, ICS.get(d, d), font(15 if dark else 13, True), (255, 255, 255))
    for d in TINY:
        if big[d][3] == side:
            r = P.crt_rect(parts[d], *big[d])
            p.rect(r[0], r[1], r[2], r[3], fill=(190, 150, 40), outline=EDGE)
    holes(p, parts, big)
    outline_and_frame(p, parts)
    for lab, x1, y1, x2, y2, key in blocks:
        if not lab:
            continue
        if lab in label_at:
            x, y, w = label_at[lab]
        else:
            x, y, w = x1 + 0.5, y2 - 0.4, x2 - x1 - 0.8
        p.wrapped(x, y, w, lab, fb, INK)


def open_text(p):
    """Space left open on purpose."""
    f = font(13)
    ux, uy = p.plan.u1
    p.text(ux - 5.2, 21.0, "Routing", f, MUTED)
    p.text(ux - 5.2, 19.6, "channel,", f, MUTED)
    p.text(ux - 5.2, 18.2, "both sides", f, MUTED)
    p.text(86.0, 37.0, "Empty on both sides", f, MUTED)


def top_arrows(p, parts, nets, b):
    plan = p.plan
    ux, uy = plan.u1
    big = plan.big
    r = lambda d: P.crt_rect(parts[d], *big[d])
    u = r("U1")
    f = font(14, True)
    rng = lambda k, n=0: f"{b[k][0]:.0f}-{b[k][1]:.0f} mm" if abs(b[k][1] - b[k][0]) >= 0.5 else f"{b[k][0]:.0f} mm"
    # south, west to east
    y0 = u[1] - 0.1
    p.arrow([(ux - 1.2, y0), (ux - 1.2, y0 - 1.6), (r("J100")[2] + 0.2, y0 - 1.6)], width=4)
    p.tag(13.5, y0 - 1.6 + 1.5, f"USB0 {rng('USB0')}", f)
    p.arrow([(ux - 2.2, y0), (ux - 2.2, y0 - 3.2), (ux - 4.4, y0 - 3.2), (ux - 4.4, 24), (r("U900")[2] + 0.2, 24)], width=4)
    p.tag(ux - 4.4, 33, f"USB1\n{rng('USB1')}", f)
    p.arrow([(big["U900"][0], r("U900")[1] - 0.1), (big["U900"][0], r("J900")[3] + 0.2)], width=4)
    csi = F.pin(parts, nets, plan, "J1200", "CSI_CLK_P")
    p.arrow([(ux + 0.7, y0), (ux + 0.7, r("J1200")[3] + 4.0), (csi[0], r("J1200")[3] + 4.0), (csi[0], r("J1200")[3] + 0.2)], width=5)
    p.tag(ux + 0.7, 24, f"CSI 3 pairs\n{b['CSI_D0'][0]:.0f}-{b['CSI_CLK'][0]:.0f} mm", f)
    rg = r("U800")
    p.arrow([(ux + 4.0, y0), (ux + 4.0, y0 - 2.6), (big["U800"][0], y0 - 2.6), (big["U800"][0], rg[3] + 0.2)], width=7)
    p.tag(big["U800"][0] + 0.2, 41.5, f"RGMII 12 lines\n{b['RGMII_TX'][0]:.0f}-{b['RGMII_RX'][1] if b['RGMII_RX'][1] > b['RGMII_TX'][1] else b['RGMII_TX'][1]:.0f} mm", f)
    j8 = r("J800")
    p.arrow([(rg[2] + 0.1, 32), (70, 32), (70, j8[3] + 0.2)], width=5)
    p.tag(70, 26, f"MDI 4 pairs\n{b['MDI0'][0]:.0f}-{b['MDI3'][0]:.0f} mm", f)
    # east
    tf = r("U1000")
    p.arrow([(u[2] + 0.1, uy - 2), (tf[0] - 0.2, uy - 2)], width=9)
    p.tag((u[2] + tf[0]) / 2, uy + 0.5, f"DPI 28\n{rng('DPI')}", f)
    es = r("U1001")
    jh = r("J1000")
    yy = big["U1001"][1]
    p.arrow([(tf[2] + 0.1, yy), (es[0] - 0.2, yy)], width=5)
    p.arrow([(es[2] + 0.1, yy), (jh[0] - 0.2, yy)], width=5)
    p.tag((tf[2] + es[0]) / 2, yy + 2.2, f"TMDS 4 pairs, straight: {b['TMDS_TX2'][0]:.0f} mm", f)
    open_text(p)
    # north-east
    jd = r("J702")
    au = r("U1100")
    p.arrow([(u[2] + 0.1, uy + 2.6), (86.0, uy + 2.6), (86.0, big["U1100"][1]), (au[0] - 0.2, big["U1100"][1])], width=4)
    p.tag(79.4, uy + 3.9 - 2.4, "McASP 6", f)
    p.arrow([(u[2] + 0.1, uy + 4.2), (72, uy + 4.2), (72, jd[1] - 0.2)], width=4)
    p.tag(61.0, uy + 4.2 + 1.3, f"SD 6 lines, {rng('MMC1')}", f)
    # north
    p.arrow([(ux - 3.2, u[3] + 0.1), (ux - 3.2, 72.9)], width=6)
    p.tag(ux + 3.2, 61.0, "Header 28, low speed", f)
    dbg = r("U1505")
    p.arrow([(ux - 6.0, u[3] + 0.1), (ux - 6.0, dbg[3] - 2.4), (dbg[2] + 0.2, dbg[3] - 2.4)], width=3)
    p.tag(ux - 9.6, u[3] + 3.9 - 3.4, "Debug 13", f)
    # DC to the south-east corner
    sw = r("SW602")
    p.arrow([(u[2] + 0.1, u[1] + 0.8), (57.4, u[1] + 0.8), (57.4, 38.3 - 4.5), (84.5, 38.3 - 4.5), (84.5, sw[3] + 0.2)], colour=DC, width=3, dashed=True)
    p.tag(90.5, 29, "4 boot lines, 2 LEDs:\nslow, narrow bus", font(13, True), DC)
    btn = r("SW200")
    p.arrow([(r("U200")[0] - 0.1, big["U200"][1] - 1.8), (18.2, big["U200"][1] - 1.8), (18.2, 31.6), (8.2, 31.6), (8.2, big["SW200"][1]), (btn[2] + 0.2, big["SW200"][1])],
            colour=DC, width=3, dashed=True)
    p.tag(22.0, 34.0, "Buttons: slow", font(13, True), DC)


def back_arrows(p, parts, nets, b):
    plan = p.plan
    ux, uy = plan.u1
    big = plan.big
    r = lambda d: P.crt_rect(parts[d], *big[d])
    u = r("U1")
    f = font(14, True)
    j = r("J700")
    p.arrow([(u[0] - 0.1, uy - 1.0), (j[2] + 0.2, uy - 1.0)], width=7)
    p.tag((u[0] + j[2]) / 2, uy - 3.6, f"eMMC 11\n{b['MMC0'][0]:.0f}-{b['MMC0'][1]:.0f} mm", f)
    open_text(p)
    jm = r("J1300")
    p.arrow([(ux + 6.0, u[3] + 0.1), (ux + 6.0, u[3] + 4.5), (jm[0] - 0.2, u[3] + 4.5)], width=4)
    p.tag(61.0, u[3] + 2.6, f"SDIO 6, {b['MMC2'][0]:.0f}-{b['MMC2'][1]:.0f} mm", f)


def power_panel(p, parts, base):
    plan = p.plan
    big = plan.big
    ux, uy = plan.u1
    r = lambda d: P.crt_rect(parts[d], *big[d])
    p.rect(0, 0, plan.W, plan.H, fill=(252, 252, 252))
    grey, navy = (150, 158, 170), (52, 60, 74)
    five, core = (205, 90, 20), (150, 20, 90)
    f = font(13, True)
    # arrows under the boxes
    a, c = r("J100"), r("U100")
    p.arrow([(a[2], c[3] + 1.2), (big["U100"][0], c[3] + 1.2), (big["U100"][0], c[3])], colour=POWER, width=4)
    p.arrow([(big["U100"][0], c[1]), (big["U101"][0], r("U101")[3])], colour=POWER, width=4)
    p.arrow([(big["U100"][0], c[1] + 2), (9.2, c[1] + 2), (9.2, big["L101"][1]), (r("L101")[2] + 0.1, big["L101"][1])], colour=POWER, width=3)
    pm, u = r("U200"), r("U1")
    l100, l101, u102 = r("L100"), r("L101"), r("U102")
    y33 = big["L100"][1]
    p.arrow([(l100[2], y33), (pm[0] + 2.5, y33), (pm[0] + 2.5, pm[1])], colour=POWER, width=5)
    p.arrow([(pm[0] + 2.5, y33), (88.0, y33)], colour=POWER, width=3)
    p.arrow([(big["U102"][0], u102[1]), (big["U102"][0], 11.5), (r("J900")[0], 11.5)], colour=five, width=3)
    p.arrow([(big["U102"][0], 27.5), (big["U1001"][0], 27.5), (big["U1001"][0], r("U1001")[1])], colour=five, width=3)
    p.arrow([(pm[2], pm[3] - 1.5), (u[0] + 2.0, pm[3] - 1.5), (u[0] + 2.0, u[1])], colour=core, width=8)
    p.arrow([(pm[2], pm[1] + 1.5), (u[0] + 6.0, pm[1] + 1.5), (u[0] + 6.0, u[1])], colour=core, width=4)
    for d, c2 in (("J100", navy), ("J900", navy), ("J1000", navy), ("U100", grey), ("U101", grey), ("L100", grey), ("U102", grey), ("L101", grey),
                  ("U200", (205, 120, 40)), ("U1", (120, 30, 70)), ("U1001", grey)):
        q = r(d)
        q = (max(q[0], 0), max(q[1], 0), min(q[2], plan.W), min(q[3], plan.H))
        p.rect(q[0], q[1], q[2], q[3], fill=c2, outline=EDGE)
        label_inside(p, q, ICS.get(d, CONNECTORS.get(d, d)).split(" ")[0], font(11, True), (255, 255, 255))
    p.rect(0, 0, plan.W, plan.H, outline=EDGE, width=2)
    p.tag(20.0, c[3] + 4.0, "VBUS_USBC", f, POWER)
    p.tag(28.0, 32.5, "VSYS_PD to the two converters", f, POWER)
    p.tag(58.0, y33 - 2.6, "3.3 V main to the PMIC; through U201 to every block, on L5", f, POWER)
    p.tag(62.0, 30.0, "5 V, on L4: USB-A switches, HDMI", f, five)
    p.tag(ux + 28.0, pm[3] + 2.6, "VDD_CORE 0.85 V: trunks on L4", f, core)
    p.tag(ux + 28.0, pm[1] + 1.5, "VDDS_DDR 1.2 V on L5, VDD_1V8 on L4", f, core)


def wrap(d, text, f, width):
    out, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if d.textlength(t, font=f) <= width or not line:
            line = t
        else:
            out.append(line)
            line = word
    out.append(line)
    return "\n".join(out)


def table(d, x, y, w, rows, widths, fh=15):
    """Plain table: bold first row, a rule under it."""
    f, fb = font(fh), font(fh, True)
    yy = y
    for i, row in enumerate(rows):
        cx = x
        ft = fb if i == 0 else f
        lines = []
        for t, cw in zip(row, widths):
            words, line, cell = str(t).split(), "", []
            for word in words:
                s = (line + " " + word).strip()
                if d.textlength(s, font=ft) <= cw - 8 or not line:
                    line = s
                else:
                    cell.append(line)
                    line = word
            cell.append(line)
            lines.append(cell)
        h = max(len(c) for c in lines) * (fh + 3) + 6
        for cell, cw in zip(lines, widths):
            for j, t in enumerate(cell):
                d.text((cx, yy + 3 + j * (fh + 3)), t, font=ft, fill=INK)
            cx += cw
        yy += h
        d.line([(x, yy - 1), (x + w, yy - 1)], fill=(120, 124, 132) if i == 0 else (214, 216, 220), width=2 if i == 0 else 1)
    return yy


TOP_LABELS = {
    "Debug": (32.0, 72.6, 4.5),
    "Expansion: header series parts": (39.9, 72.6, 10.8),
    "Clocks, reset": (17.9, 58.4, 10.0),
    "USB-C port: ESD, CC": (8.9, 58.3, 8.0),
    "Power: PD, 3.3 V and 5 V converters": (7.5, 35.9, 10.6),
    "PMIC, inductors, load switches": (25.8, 37.5, 10.0),
    "USB hub, ESD, VBUS switches": (18.8, 30.0, 6.0),
    "Ethernet PHY, crystal, series row": (46.9, 29.0, 11.0),
    "HDMI: TFP410": (58.9, 39.8, 15.5),
    "microSD: ESD, switch": (73.0, 62.8, 10.8),
    "Audio codec": (84.9, 79.3, 13.5),
    "HDMI ESD": (88.3, 43.9, 9.0),
    "Boot DIP, LEDs": (86.0, 14.7, 13.0),
    "Board ID, sensor, I2C": (51.9, 72.6, 12.8),
}
BACK_LABELS = {
    "SiP decoupling": (30.4, 46.2, 15.0),
    "eMMC pull-ups": (8.9, 61.3, 17.0),
    "Expansion: slew and series": (37.5, 72.6, 19.0),
    "Debug parts, Tag-Connect": (9.0, 72.6, 22.0),
    "M.2 card: only 0402s under it": (77.0, 58.5, 22.0),
    "M.2 parts": (57.6, 72.6, 6.5),
    "Strap resistors on DPI, BOOTMODE": (56.6, 46.0, 7.2),
    "Power: filters, bulk": (0.9, 41.0, 16.5),
    "PMIC decoupling": (18.9, 38.0, 16.5),
    "USB: chokes, pull-downs": (18.8, 30.0, 17.0),
    "PHY decoupling, straps": (46.9, 28.0, 9.0),
    "TFP410 decoupling": (64.6, 39.0, 9.5),
    "Test pads, grouped by rail": (80.5, 18.7, 25.0),
    "Button parts": (0.8, 23.6, 6.4),
    "Camera: filter, pull-ups": (37.4, 5.0, 21.0),
    "SDIO series": (45.2, 62.6, 5.5),
    "eMMC module": (13.5, 56.0, 7.5),
}


def render(W, H):
    parts, nets = P.load_parts()
    plan = F.Plan(W, H)
    now = P.read_csv()

    class Current:
        pass

    cur = Current()
    cur.big = {d: now[d] for d in now}
    b_now = F.buses(parts, nets, cur)
    b = F.buses(parts, nets, plan)
    est = F.estimated_place(parts, nets, plan)
    est.pop("__no_room__")
    st_now, st = F.passive_stats(parts, nets, now), F.passive_stats(parts, nets, est)
    nm_now, nm = F.named(parts, nets, now), F.named(parts, nets, est)
    t_now, c_now, _ = F.crossings(parts, nets, now)
    t, c, _ = F.crossings(parts, nets, est)
    bx_now, _ = F.bus_crossings(parts, nets, cur)
    bx, _ = F.bus_crossings(parts, nets, plan)
    mean_now = sum(b_now[k][2] for k in ("RGMII_TX", "RGMII_RX", "MMC0", "MMC1", "MMC2"))
    mean = sum(b[k][2] for k in ("RGMII_TX", "RGMII_RX", "MMC0", "MMC1", "MMC2"))
    d_now = F.demand(parts, nets, now, P.BOARD_W, P.BOARD_H)
    dem = F.demand(parts, nets, est, W, H)

    pw, ph = W * SCALE, H * SCALE
    cw = int(2 * pw + 3 * MARGIN + 40)
    p2h = H * SMALL
    ch = int(MARGIN + 44 + ph + 62 + 44 + 44 + max(p2h, 560) + 30)
    img = Image.new("RGB", (cw, ch), (246, 247, 249))
    draw = ImageDraw.Draw(img)
    ttl, h2 = font(30, True), font(20, True)
    draw.text((MARGIN, 14), f"APE-SBC functional floorplan, {W:g} x {H:g} mm, 8 layers: for review, nothing placed yet", font=ttl, fill=INK)
    y0 = MARGIN + 44

    x1, x2 = MARGIN + 20, MARGIN + 20 + pw + MARGIN + 20
    draw.text((x1, y0 - 26), "TOP side: regions, connectors on edges, main buses", font=h2, fill=INK)
    draw.text((x2, y0 - 26), "BACK side, seen through the board from the top: regions and the two back-side buses", font=h2, fill=INK)
    top = Panel(draw, x1, y0, SCALE, plan)
    top.base = img
    side_panel(top, parts, "T", TOP_LABELS)
    top_arrows(top, parts, nets, b)
    back = Panel(draw, x2, y0, SCALE, plan)
    back.base = img
    side_panel(back, parts, "B", BACK_LABELS)
    back_arrows(back, parts, nets, b)

    y1 = y0 + ph + 44
    # the legend
    f = font(14)
    x = x1
    for key, name in LEGEND:
        w = draw.textlength(name, font=f) + 34
        if x + w > cw - MARGIN:
            break
        draw.rectangle([x, y1 - 12, x + 18, y1 + 4], fill=COLOURS[key][0], outline=COLOURS[key][1])
        draw.text((x + 23, y1 - 12), name, font=f, fill=INK)
        x += w + 8
    # what the marks mean
    yk = y1 + 22
    x = x1
    for colour, dashed, name in ((BUS, False, "Main bus: lines, Manhattan length from ball to pin"), (DC, True, "Slow lines"), (POWER, False, "Power flow")):
        if dashed:
            for i in range(0, 34, 12):
                draw.line([(x + i, yk), (x + i + 7, yk)], fill=colour, width=3)
        else:
            draw.line([(x, yk), (x + 34, yk)], fill=colour, width=4)
        draw.text((x + 40, yk - 8), name, font=f, fill=INK)
        x += 40 + draw.textlength(name, font=f) + 20
    draw.rectangle([x, yk - 8, x + 18, yk + 8], fill=(150, 158, 170), outline=EDGE)
    draw.text((x + 23, yk - 8), "IC", font=f, fill=INK)
    x += 50
    draw.rectangle([x, yk - 8, x + 18, yk + 8], fill=(52, 60, 74), outline=EDGE)
    draw.text((x + 23, yk - 8), "Connector or module plug", font=f, fill=INK)
    x += 215
    draw.rectangle([x, yk - 8, x + 18, yk + 8], fill=(226, 228, 232), outline=GHOST)
    draw.text((x + 23, yk - 8), "Through-hole tails on the back", font=f, fill=INK)
    x += 250
    for i in range(0, 34, 12):
        draw.line([(x + i, yk), (x + i + 7, yk)], fill=GHOST, width=1)
    draw.text((x + 40, yk - 8), "Part or card on the other side", font=f, fill=INK)
    y2 = y1 + 62
    draw.text((x1, y2 - 6), "POWER FLOW", font=h2, fill=INK)
    pwr = Panel(draw, x1, y2 + 24, SMALL, plan)
    pwr.base = img
    power_panel(pwr, parts, img)

    # the numbers, beside the power flow
    tx = x1 + W * SMALL + 50
    draw.text((tx, y2 - 6), "THE REVIEW POINTS: now, and expected from this plan", font=h2, fill=INK)
    r = lambda v: f"{v:.0f}"
    fm = lambda k, bb: f"{bb[k][0]:.0f}-{bb[k][1]:.0f}"
    rows = [
        ("Review point", "Now (100 x 70)", f"Plan ({W:g} x {H:g}), estimate", "Move"),
        ("1 Passives within 3 / 5 mm of their pin", f"{st_now['all_3']:.0f} / {st_now['all_5']:.0f} %", f"{st['all_3']:.0f} / {st['all_5']:.0f} %",
         "One region per function; part sits by the pin it serves"),
        ("2 Decoupling within 3 / 5 mm; SiP caps median, worst", f"{st_now['dec_3']:.0f} / {st_now['dec_5']:.0f} %; {st_now['sip_median']:.1f}, {st_now['sip_worst']:.1f} mm",
         f"{st['dec_3']:.0f} / {st['dec_5']:.0f} %; {st['sip_median']:.1f}, {st['sip_worst']:.1f} mm", "21 caps under the SiP, the rest in a clear ring"),
        ("2 C602 to Y600; R602 to Y600, to H2", f"{nm_now['C602 to Y600']:.1f}; {nm_now['R602 to Y600']:.1f}, {nm_now['R602 to ball H2']:.1f} mm",
         f"{nm['C602 to Y600']:.1f}; {nm['R602 to Y600']:.1f}, {nm['R602 to ball H2']:.1f} mm", "Crystal group by hand at its balls"),
        ("2 C339 to N7; R1300-04 to balls", f"{nm_now['C339 to ball N7']:.1f}; {nm_now['R1300-R1304 to balls'][0]:.1f}-{nm_now['R1300-R1304 to balls'][1]:.1f} mm",
         f"{nm['C339 to ball N7']:.1f}; {nm['R1300-R1304 to balls'][0]:.1f}-{nm['R1300-R1304 to balls'][1]:.1f} mm", "Site under the SiP; series row north of the balls"),
        ("3 eMMC length; meander", f"{fm('MMC0', b_now)} mm; {b_now['MMC0'][2]:.0f} mm", f"{fm('MMC0', b)} mm; {b['MMC0'][2]:.0f} mm", "Module moved out west, back side clear round the SiP"),
        ("4 Debug block", "Beside U1", "North-west corner", "FT4232 by J1500; 13 slow lines to the SiP"),
        ("5 SW602", "Mid-board", "South edge", "4 slow lines; straps stay on their balls' side"),
        ("6 J1200 camera", f"Mid-board; {b_now['CSI_D0'][0]:.0f}-{b_now['CSI_CLK'][0]:.0f} mm", f"South edge; {b['CSI_D0'][0]:.0f}-{b['CSI_CLK'][0]:.0f} mm", "Straight run from the CSI balls; longer"),
        ("7 HDMI", f"Diagonal; {b_now['TMDS_TX2'][0]:.0f} mm", f"Straight; {b['TMDS_TX2'][0]:.0f} mm", "M.2 moved to the north-east, under SD and audio"),
        ("8 USB0 to J100", f"{b_now['USB0'][0]:.0f} mm", f"{b['USB0'][0]:.0f} mm", "J100 level with the SiP on the west edge"),
        ("Signal ratsnest; crossings", f"{t_now:.0f} mm; {c_now}", f"{t:.0f} mm; {c}", "First cut, not tuned. Longer: edge connectors by design"),
        ("Routing demand: peak; area over 100 %", f"{d_now['peak']:.2f}; {d_now['over_mm2']:.0f} mm2", f"{dem['peak']:.2f}; {dem['over_mm2']:.0f} mm2", "The peak is the SiP's own escape: not improved"),
        ("Main bus lines crossing each other", f"{bx_now}", f"{bx}", "Worse on paper: SD and SDIO cross once as whole bundles (6 x 6), by layer, as J702 is on top and J1300 on the back"),
        ("All meanders needed", f"{mean_now:.0f} mm", f"{mean:.0f} mm", "RGMII, eMMC, SD, SDIO"),
        ("Longer than now", f"RGMII {fm('RGMII_TX', b_now)}, USB1 {b_now['USB1'][0]:.0f}, SDIO {fm('MMC2', b_now)}", f"RGMII {b['RGMII_TX'][0]:.0f}-{b['RGMII_TX'][1]:.0f}, USB1 {b['USB1'][0]:.0f}, SDIO {fm('MMC2', b)}", "All in mm; room for series parts, and inside their limits"),
    ]
    tw = cw - tx - MARGIN
    widths = [tw * 0.31, tw * 0.17, tw * 0.17, tw * 0.35]
    ye = table(draw, tx, y2 + 24, tw, rows, widths, 15)
    note = ("Now is the current placement. The plan column is a first cut, not tuned: big parts by hand, small parts dropped into their regions at the free spot "
            "nearest what they serve, 10 mil apart. Vias and routing room are not modelled. Ratsnest and demand count signals only: power nets go on the planes.")
    draw.multiline_text((tx, ye + 8), wrap(draw, note, font(14), tw), font=font(14), fill=MUTED, spacing=3)
    F.OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(F.OUT, optimize=True)
    print(f"wrote {F.OUT} ({img.width} x {img.height})")
    print({k: round(v, 1) for k, v in st.items()})
    print(nm)
    print(f"ratsnest {t:.0f}, crossings {c}, demand {dem}")
    print({k: tuple(round(x, 1) for x in v) for k, v in b.items()})
