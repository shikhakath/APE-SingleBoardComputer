"""APE-SBC component placement, computed offline and applied to PCB.PcbDoc.

The hand floorplan is ``FIXED`` below (connectors, ICs, power stages, mounting
hardware). Everything else (passives, small parts, test pads) is placed by simulated
annealing around those parts. Results live in ``placement.csv``, keyed by designator,
so a netlist change only re-places what is new. Run from hardware/gen:

    python build.py check            refresh out/netlist.csv and friends
    python placement.py solve        anneal everything not in FIXED (about 3 minutes)
    python placement.py add          place only the parts missing from the csv
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
import random
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
BOARD_W, BOARD_H = 100.0, 70.0   # pcbsetup reads these
CORNER_R = 3.0                   # Raspberry Pi drawing: all corners R3
EDGE_CLR = 0.5                   # courtyard to outline, parts not on an edge
GRID = 0.5                       # annealed parts: with the margin below, 0402s fall on a 2.5-3 x 2 mm lattice
MARGIN = 0.3                     # around every annealed courtyard, room for its fan-out vias
# The Raspberry Pi rectangle (85 x 56) is the board's upper-left part: the board grows
# 15 mm to the right and 14 mm down, so the holes and the 40-pin header keep their
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

U1_XY = (44.0, 43.0)             # SiP centre: CSI balls over J1200, HDR balls under J1400
M2_XY = (62.0, 38.0)             # back side, card toward +x, SDIO pins level with the SDIO balls
# Socket centre line to the standoff hole: 30.06 mm on TI SK-AM62A (reference/2_PROC142A
# IPC-D-356: J2 rows at x -45.6 / +251.6 mil, SH3 at 1286.6 mil). Same contact-row spacing
# as the LOTES socket (7.55 mm). The rows' centre is 1.5 mm above the holes' line, the
# footprint origin 1.355 mm.
M2_STANDOFF_DX = 30.06 - (1.5 - 1.355)
EMMC_XY = (33.5, 42.0)           # J700, back side; the module runs toward -x

# designator: (x, y, rotation, side)
FIXED = {
    # ---- mechanics, Raspberry Pi pattern
    **{d: (x, y, 0, "T") for d, (x, y) in HOLES.items()},
    "J1400": (HEADER[0], HEADER[1], 0, "T"),
    "U1400": (41.0, 60.6, 0, "T"),
    # I2C slew parts on the back, by balls A7, B7, A8, B8: sheet 14 wants the 62 R and 47 pF
    # within 5 mm of the balls. Pad 1 (the ball side) faces the balls.
    "R1425": (37.6, 49.6, 0, "B"),
    "C1401": (37.6, 50.95, 0, "B"),
    "R1424": (39.85, 49.6, 0, "B"),
    "C1400": (39.85, 50.95, 0, "B"),
    "R1426": (42.1, 49.6, 180, "B"),
    "C1402": (42.1, 50.95, 180, "B"),
    "R1427": (44.35, 49.6, 180, "B"),
    "C1403": (44.35, 50.95, 180, "B"),

    # ---- SiP. Zero orientation: rows A-D (HDR, JTAG, SD, SDIO) up, columns 25-28
    # (DPI) right, rows U-V (USB, CSI, RGMII) down, columns 1-2 (MMC0, clocks) left.
    "U1": (U1_XY[0], U1_XY[1], 0, "T"),

    # ---- HDMI, straight run to the right edge. DPI enters the TFP410's top (D12-23) and left
    # (D0-11) sides, level with the DPI balls; TMDS leaves its right side toward J1000.
    "U1000": (63.7, 37.5, 90, "T"),
    "U1001": (83.4, 24.0, 0, "T"),
    # Low enough that the M.2 card on the back (y > 27) clears the shell-leg tails
    "J1000": (BOARD_W - 4.70, 18.7, 90, "T"),

    # ---- Ethernet, straight down from the RGMII balls: PHY's RGMII side up (same left-to-right
    # order as the balls), MDI side down (same order as the RJ45 pins). The RJ45 sits in the
    # strip below the HAT, beside H1601.
    "U800": (52.5, 28.7, 90, "T"),
    "Y800": (59.2, 25.5, 0, "T"),
    "U203": (52.0, 21.5, 0, "B"),
    # RGMII series resistors in line on the top side, two rows between U1 and the PHY:
    # transmit at the SiP, receive at the PHY. Rows U and V escape on L1 straight into them.
    "R801": (48.4, 36.75, 270, "T"),
    "R806": (49.65, 36.75, 90, "T"),
    "R800": (50.9, 36.75, 270, "T"),
    "R802": (52.15, 36.75, 270, "T"),
    "R803": (53.4, 36.75, 270, "T"),
    "R804": (54.65, 36.75, 270, "T"),
    "R805": (55.9, 36.75, 270, "T"),
    "R807": (48.4, 34.45, 90, "T"),
    "R811": (49.65, 34.45, 90, "T"),
    "R810": (50.9, 34.45, 90, "T"),
    "R809": (52.15, 34.45, 90, "T"),
    "R808": (53.4, 34.45, 90, "T"),
    "J800": (74.4, 10.65 - OVERHANG, 0, "T"),

    # ---- USB, straight down from the USB balls: hub, CMC, then the stacked USB-A in the strip
    # below the HAT. Bulk caps at the VBUS pins on its left.
    "U900": (38.0, 20.0, 90, "T"),
    "Y900": (43.0, 22.4, 0, "B"),
    "L901": (38.0, 15.6, 0, "T"),
    "L902": (38.0, 15.6, 0, "B"),
    "D904": (43.0, 17.2, 90, "B"),
    "D905": (33.0, 17.2, 90, "B"),
    "J900": (40.5, 8.5 - OVERHANG - 0.2, 0, "T"),
    "C907": (28.0, 6.2, 90, "T"),
    "C911": (27.55, 16.95, 90, "T"),
    "U901": (33.1, 17.6, 90, "T"),
    "U902": (33.1, 22.7, 90, "T"),

    # ---- camera: on the Pi's camera-connector line (x = 45, the HAT slot), flex straight up
    "J1200": (45.0, 26.0, 90, "T"),

    # ---- SD on the top edge, level with the SD balls; audio beyond it, far from the switchers
    "J702": (73.75, BOARD_H - 7.25, 180, "T"),
    "J1100": (88.0, BOARD_H - 6.05, 180, "T"),
    "U1100": (86.0, 50.0, 90, "T"),
    "Y1100": (81.0, 47.5, 0, "T"),

    # ---- Wi-Fi on the back, socket beside U1 at the height of the SDIO balls, card over low parts
    "J1300": (M2_XY[0], M2_XY[1], 90, "B"),
    "H1300": (M2_XY[0] + M2_STANDOFF_DX, M2_XY[1], 0, "B"),

    # ---- eMMC module on the back against U1's left edge (MMC0 balls), two plugs 13 mm apart
    "J700": (EMMC_XY[0], EMMC_XY[1], 270, "B"),
    "J701": (EMMC_XY[0] - 13.0, EMMC_XY[1], 270, "B"),

    # ---- boot DIP above the BOOTMODE balls
    "SW602": (57.0, 55.35, 90, "T"),

    # ---- USB-C power input on the left edge: CC toward J100, VBUS and VSYS out of the top side
    "J100": (3.185, 27.0, 270, "T"),
    "U100": (13.5, 27.0, 90, "T"),
    "C107": (18.6, 31.0, 0, "T"),
    "C108": (18.6, 28.4, 0, "T"),

    # ---- LM61460 3.3 V: SW down into L100, VIN caps on both sides of the part
    "U101": (14.0, 18.4, 270, "T"),
    "L100": (14.0, 11.0, 270, "T"),
    "C109": (10.3, 18.4, 270, "T"),
    "C111": (17.6, 19.1, 270, "T"),
    "C117": (20.3, 7.7, 0, "T"),
    "C118": (20.3, 10.25, 0, "T"),
    "C119": (20.3, 12.8, 0, "T"),
    "C120": (20.3, 15.35, 0, "T"),

    # ---- TPS63070 5 V: inductor beside the L1/L2 pins, output caps under VOUT, input caps over VIN
    "U102": (12.7, 38.0, 0, "T"),
    "L101": (17.45, 38.0, 270, "T"),
    "C125": (12.4, 34.4, 0, "T"),
    "C126": (17.45, 33.6, 180, "T"),
    "C127": (22.6, 34.0, 0, "T"),
    "C121": (12.7, 41.4, 0, "T"),
    "C122": (16.4, 42.2, 0, "T"),

    # ---- PMIC at U1's lower-left corner: LX_B2/B3 down into L201/L202, LX_B1 right into L200
    "U200": (29.0, 33.0, 180, "T"),
    "L200": (33.7, 31.2, 270, "T"),
    "L201": (30.6, 27.2, 270, "T"),
    "L202": (27.2, 27.2, 270, "T"),
    "U201": (23.5, 28.5, 0, "T"),

    # ---- SiP clocks: 25 MHz oscillator and series R within 2 mm of ball G1, 32 kHz crystal at
    # H1/H2. Top side; the MMC0 balls below them escape to the back, into J700.
    "U600": (34.1, 46.7, 0, "T"),
    "R600": (34.6, 44.25, 0, "T"),
    "Y600": (33.5, 42.3, 180, "T"),
    "U1601": (35.8, 50.5, 0, "T"),
    "U601": (29.7, 47.5, 0, "T"),
    "U1600": (23.0, 44.5, 0, "T"),

    # ---- debug: USB-C on the left edge, FT4232 next to it, level shifters toward U1
    "J1500": (3.185, 53.0, 270, "T"),
    "U1500": (16.5, 54.3, 0, "T"),
    "U1504": (29.5, 58.0, 0, "T"),
    "U1505": (29.5, 52.0, 0, "T"),
    "J1501": (29.0, 55.8, 0, "B"),

    # ---- buttons and LEDs on the bottom edge, in the strip a HAT does not cover
    "SW200": (4.85, 3.4, 0, "T"),
    "SW600": (12.6, 3.4, 0, "T"),
    "SW601": (20.4, 3.4, 0, "T"),
    "LED1600": (51.0, 1.7, 0, "T"),
    "LED1601": (55.2, 1.7, 0, "T"),
    "LED1602": (59.0, 1.7, 0, "T"),
    "LED1603": (62.3, 1.7, 0, "T"),

    "C831": (86.2, 15.0, 90, "T"),
}


# Rectangles (x1, y1, x2, y2, side, why) where annealed parts may not go. Side
# "T", "B" or "TB". Hand-placed parts are not checked against them.
# Parts that hang off a high-speed or crystal net, placed for the shortest stub after the anneal (the annealer
# scores them as wire, and left some 10-20 mm from the route; one load cap was 32 mm from its crystal). R900 and
# R901 straddle the choke L900. C320 and TP1000 gave up their spots. docs/pcb-placement.md lists what is left.
STUB_PARTS = {
    "C320": (22.5, 40.5, 270, "T"), "C602": (28, 39, 180, "T"), "C603": (30.5, 42, 270, "T"),
    "C800": (58, 28.5, 0, "T"), "C801": (58.5, 25, 0, "B"), "C1519": (9, 59.5, 180, "B"),
    "C1520": (10, 58, 180, "B"), "C1600": (19, 28.5, 180, "B"), "R602": (29.5, 37.5, 0, "T"),
    "R629": (77.5, 45.5, 90, "T"), "R630": (67.5, 43, 270, "B"), "R631": (65.5, 50.5, 270, "B"),
    "R632": (69.5, 43, 0, "B"), "R633": (60, 50, 0, "B"), "R635": (74.5, 49, 270, "B"),
    "R637": (76.5, 47, 180, "B"), "R639": (68, 45, 180, "B"), "R641": (70, 51.5, 270, "B"),
    "R643": (70, 45.5, 90, "B"), "R701": (32, 31.5, 180, "B"), "R702": (29, 30.5, 180, "B"),
    "R703": (32, 33, 180, "B"), "R704": (31.5, 30, 180, "B"), "R705": (24, 48.5, 270, "T"),
    "R706": (31.5, 28.5, 180, "B"), "R707": (22.5, 34.5, 180, "B"), "R708": (35, 30, 270, "B"),
    "R709": (37, 29.5, 0, "B"), "R712": (26.5, 34, 90, "B"), "R723": (65, 52, 0, "T"),
    "R724": (68.5, 52.5, 0, "T"), "R725": (78.5, 54.5, 270, "B"), "R726": (63.5, 53.5, 270, "B"),
    "R727": (72, 57, 180, "B"), "R728": (71, 52.5, 180, "T"), "R732": (71, 53.5, 180, "B"),
    "R900": (18.3, 29.8, 180, "B"), "R901": (17.6, 33.2, 180, "B"), "R915": (38.5, 14, 180, "B"),
    "R1305": (54.5, 55, 0, "B"), "R1306": (61.5, 53, 0, "B"), "R1308": (55, 35.5, 180, "B"),
    "R1310": (57, 52, 270, "B"), "TP300": (16.3, 29, 0, "B"), "TP1000": (60.5, 25, 180, "B"),
}
FIXED.update(STUB_PARTS)


def keepouts() -> list[tuple]:
    ux, uy = U1_XY
    ex, ey = EMMC_XY
    mx, my = M2_XY
    return [
        # SiP fan-out: 1 mm around the 14 x 9 mm body, on both sides (the U1_SiP room)
        (ux - 8.0, uy - 5.5, ux + 8.0, uy + 5.5, "TB", "U1 fan-out"),
        # eMMC module, 18 x 13 mm, 1 mm stack: nothing fits under it
        (ex - 15.5, ey - 6.5, ex + 2.5, ey + 6.5, "B", "eMMC module"),
        # bus corridors on the top side: L1 stays free where a whole bus leaves U1
        (ux + 8.0, 35.2, 57.0, 53.0, "T", "DPI, SD, AUD escape"),
        (ux - 7.5, uy + 5.5, ux + 8.0, uy + 11.0, "T", "HDR, JTAG escape"),
        (36.0, 22.7, 40.9, uy - 5.5, "T", "USB escape"),
        (46.0, 32.65, 56.5, uy - 5.5, "T", "RGMII escape"),
        (70.4, 20.0, 78.8, 44.2, "T", "TMDS"),
        (48.0, 20.8, 78.0, 24.1, "T", "MDI"),
        (57.0, 44.2, 71.0, 50.0, "T", "D12-D23, SD, AUD"),
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




# Parts that stay on one side when annealed (default: passives both, the rest top)
TOP_ONLY_FOOTPRINTS = {"C1206", "CP_SMD_D6.3X5.8", "IND_MURATA_DFE252012F", "IND_SUNLORD_MWSA0402S",
                       "IND_SUNLORD_MWSA0603S", "DIO_SMA", "SOT23-5", "SOT23-6",
                       "SOIC8_3.9X4.9_P1.27", "TSSOP8_4.4X3.0_P0.65", "TSSOP16_4.4X5.0_P0.65",
                       "XTAL_3225_4P", "OSC_3225_4P", "OSC_2520_4P", "XTAL_EPSON_FC-135", "LED0603", "LED0805"}
BOTTOM_ONLY_FOOTPRINTS = {"TP_PAD_1.0"}
# Power-stage parts stay beside their switcher on the top side: short loops
TOP_ONLY_SHEETS = {"USB-C power input and main converters", "PMIC and power switches"}

VIA_COST = 3.5                   # mm of extra wire a net pays for changing sides

# Net weights, by name pattern (first match wins)
NET_WEIGHTS = [
    (re.compile(r"^(LM_SW|BB_L1|BB_L2|PMIC_LX_B\d)$"), 8.0),                # switch nodes: short loops
    (re.compile(r"^(OSC_25M|OSC25M_SRC|LFOSC_.*|PHY_X.|HUB_X.|FT_OSC.|AUD_MCLK_OSC|LM_CBOOT|LM_RBOOT)$"), 6.0),
    (re.compile(r"^J_HDR"), 6.0),                                           # series R at the header pin
    (re.compile(r"^(ETH_MDI|HDMI_TX|CSI_|USB|HUB_P|USBA|USBC|DBG_USB)"), 2.5),
    (re.compile(r"^(ETH_|PHY_|EMMC_|SD_|M2_SDIO|WL_SDIO|DPI_|TFP_IDCK)"), 2.0),
]


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


# A comment that says where a part sits: the net to that part scores 6 x wire length
SITS_AT = [(re.compile(r"at SoC|near SoC|at the SoC ball|slew limiter"), "U1"), (re.compile(r"at PHY"), "U800"),
           (re.compile(r"at the oscillator"), "U600"), (re.compile(r"at J1100"), "J1100"),
           (re.compile(r"at Y1100"), "Y1100"), (re.compile(r"at J1200"), "J1200")]


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


def net_weight(net):
    for rx, w in NET_WEIGHTS:
        if rx.search(net):
            return w
    return 1.0


def ball_positions():
    """{ball name of symbol pin: [ball numbers]} for the SiP's power balls."""
    from symbols import OSD6254
    out = {}
    for p in OSD6254.pins:
        out.setdefault(p.name, []).append(p.number)
    return out


# 0R links feeding the IO-bank rails. Their pads are the only probe points on those rails,
# so they sit by the bank's balls and caps, and stay out from under the M.2 card.
BANK_LINKS = {f"R{n}" for n in range(303, 311)}

# Decoupling parts whose pin is known from the schematic comments (sheet 02)
ANCHOR_PIN = {"C200": ("U200", "4"), "C201": ("U200", "5"), "C202": ("U200", "30"), "C203": ("U200", "26"),
              "C204": ("U200", "13"), "C205": ("U200", "6"), "C206": ("U200", "20"), "C207": ("U200", "22"),
              "C209": ("U200", "13"), "C210": ("L200", "2"), "C211": ("L200", "2"), "C212": ("L201", "2"),
              "C213": ("L201", "2"), "C214": ("L202", "2"), "C215": ("L202", "2")}

COMMENT_BALL = re.compile(r"\((VDD\w*|VPP)[ ,)]")


def bom_comments():
    comments = {}
    with open(OUT / "schematic_bom.csv", newline="", encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            comments.setdefault(r["designator"], r["comment"])
    return comments


def anchors(parts, nets, place):
    """Decoupling caps on a big rail: the IC pin each one serves, one cap per pin
    in turn. Returns {des: [(x, y, net)]} in board mm."""
    comments = bom_comments()
    balls = ball_positions()
    out = {}
    turn = {}
    pads_of = {d: {p[4]: p for p in pt.pads if p[4]} for d, pt in parts.items()}

    def pin_xy(d, name):
        x, y, rot, side = place[d]
        p = pads_of[d][name]
        return xform(p[0], p[1], x, y, rot, side)

    for d, pt in sorted(parts.items(), key=lambda kv: _natural(kv[0])):
        named = [p for p in pt.pads if p[4]]
        if d in place:
            continue
        if pt.sheet == "SiP power" and (d.startswith("C") or d in BANK_LINKS):
            net = next((p[2] for p in named if p[2] and p[2] != "GND"
                        and (d not in BANK_LINKS or p[2].startswith("VDDSHV"))), None)
            ball_list = [nd.split(".", 1)[1] for nd in nets.get(net, []) if nd.startswith("U1.")]
            if ball_list:
                m = COMMENT_BALL.search(comments.get(d, ""))
                wanted = [b for b in balls.get(m.group(1), []) if b in ball_list] if m else []
                if wanted:
                    ball_list = wanted
                ball_list = sorted(ball_list, key=_natural)
                i = turn.get(("SIP", net), 0)
                turn[("SIP", net)] = i + 1
                out[d] = (pin_xy("U1", ball_list[i % len(ball_list)]), net)
                continue
        signal = {p[2] for p in named if p[2] and p[2] not in ("GND", "NC")}
        if len(signal) != 1:
            continue                                         # not a plain decoupling or clamp part
        net = next(iter(signal))
        # candidates: IC and connector pins on that net in the same sheet, hand-placed parts only
        cand = []
        for nd in nets[net]:
            od, pin = nd.split(".", 1)
            if od in place and parts[od].sheet == pt.sheet and od != d and len(pads_of[od]) > 2:
                cand.append((od, pin))
        if not cand:
            cand = [(nd.split(".", 1)) for nd in nets[net]
                    if nd.split(".", 1)[0] in place and nd.split(".", 1)[0] != d]
        if not cand:
            continue
        cand = sorted(cand, key=lambda c: (_natural(c[0]), _natural(c[1])))
        key = (net, pt.sheet)
        i = turn.get(key, 0)
        turn[key] = i + 1
        od, pin = ANCHOR_PIN.get(d) or cand[i % len(cand)]
        out[d] = (pin_xy(od, pin), net)
    return out


def allowed_sides(pt: Part):
    if pt.des in ("R820", "R821"):               # RGMII_RX straps: RGMII stays on L1 and L3 (README section 11)
        return ("T",)
    if pt.fp in BOTTOM_ONLY_FOOTPRINTS:
        return ("B",)
    if pt.fp in TOP_ONLY_FOOTPRINTS:
        return ("T",)
    if pt.sheet in TOP_ONLY_SHEETS and pt.fp not in ("R0402", "C0402", "SOD323", "X1SON2_DPY"):
        return ("T",)
    return ("T", "B")


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


def fixed_obstacles(parts, place, grid):
    """Courtyards of placed parts on their side, holes of THT parts on the other."""
    n = 0
    for d, (x, y, rot, side) in place.items():
        pt = parts[d]
        grid.add(("P", d), side, crt_rect(pt, x, y, rot, side))
        other = "B" if side == "T" else "T"
        for hole in pt.holes:
            a = xform(hole[0], hole[1], x, y, rot, side)
            b = xform(hole[2], hole[3], x, y, rot, side)
            n += 1
            grid.add(("H", n), other, (min(a[0], b[0]) - 0.25, min(a[1], b[1]) - 0.25,
                                       max(a[0], b[0]) + 0.25, max(a[1], b[1]) + 0.25))


def solve(parts, nets, seed_place, movable, steps=1_500_000, seed=1, t_start=4.0, t_end=0.02,
          log=True, margin=MARGIN):
    grow = margin
    rng = random.Random(seed)
    place = dict(seed_place)
    fixed = {d: place[d] for d in place if d not in movable}
    anc = anchors(parts, nets, fixed)

    grid = Grid()
    fixed_obstacles(parts, fixed, grid)
    for i, k in enumerate(keepouts() + thermal_keepouts(parts, fixed)):
        for s in k[4]:
            grid.add(("K", i, s), s, (k[0], k[1], k[2], k[3]))

    # nets that the annealer scores by HPWL: not rails, not GND
    d_nets = {d: {} for d in parts}
    for net, nodes in nets.items():
        if net in ("NC",) or is_rail(net, nodes) or net.startswith("NC"):
            continue
        for nd in nodes:
            od, pin = nd.split(".", 1)
            if od in d_nets and not (od in anc and anc[od][1] == net):
                d_nets[od].setdefault(net, []).append(pin)
    net_pins = {}
    for d, m in d_nets.items():
        for net, pins in m.items():
            net_pins.setdefault(net, []).append((d, pins))
    pad_of = {d: {p[4]: p for p in pt.pads if p[4]} for d, pt in parts.items()}
    weights = {n: net_weight(n) for n in net_pins}
    comments = bom_comments()
    for d in parts:
        for rx, target in SITS_AT:
            if rx.search(comments.get(d, "")):
                for net in d_nets[d]:
                    if any(od == target for od, _ in net_pins[net]):
                        weights[net] = max(weights[net], 6.0)
    # A slew limiter belongs at the ball: its far side (often a header net) must not pull it away
    for d in parts:
        if "slew limiter" in comments.get(d, ""):
            for net in d_nets[d]:
                if not any(od == "U1" for od, _ in net_pins[net]):
                    weights[net] = 1.0
    # A through-hole pin or a SiP ball (via in every pad) reaches both sides for free
    neutral = {d for d, pt in parts.items() if pt.holes and len(pt.holes) >= len([q for q in pt.pads if q[4]])}
    neutral.add("U1")

    pad_xy = {}

    def set_pads(d, x, y, rot, side):
        pad_xy[d] = {name: xform(p[0], p[1], x, y, rot, side) for name, p in pad_of[d].items()}

    for d, v in place.items():
        set_pads(d, *v)

    def net_cost(net):
        xs, ys = [], []
        sides = set()
        for d, pins in net_pins[net]:
            v = place.get(d)
            if v is None:
                continue
            if d not in neutral:
                sides.add(v[3])
            xy = pad_xy[d]
            for pin in pins:
                px, py = xy[pin]
                xs.append(px)
                ys.append(py)
        n = len(xs)
        if n < 2:
            return 0.0
        cx, cy = sum(xs) / n, sum(ys) / n
        star = sum(abs(q - cx) for q in xs) + sum(abs(q - cy) for q in ys)
        return weights[net] * (star + (VIA_COST if len(sides) > 1 else 0.0))

    def part_cost(d):
        v = place[d]
        c = 0.0
        a = anc.get(d)
        if a:
            (ax, ay), net = a
            for name, p in pad_of[d].items():
                if p[2] == net:
                    px, py = pad_xy[d][name]
                    c += (3.0 if parts[d].sheet == "SiP power" else 1.5) * (abs(px - ax) + abs(py - ay))
                    break
        return c

    def nets_of(d):
        return list(d_nets[d].keys())

    # start: any legal position near the part's nets
    card = (M2_XY[0] - 2.0, M2_XY[1] - 11.5, M2_XY[0] + M2_STANDOFF_DX + 2.0, M2_XY[1] + 11.5)

    def bounds_ok(r, pt):
        if not (r[0] >= EDGE_CLR and r[1] >= EDGE_CLR and r[2] <= BOARD_W - EDGE_CLR and r[3] <= BOARD_H - EDGE_CLR):
            return False
        if (pt.fp == "TP_PAD_1.0" or pt.des in BANK_LINKS) and r[0] < card[2] and card[0] < r[2] and r[1] < card[3] and card[1] < r[3]:
            return False
        return True

    unplaced = []

    def target_of(d):
        pts = []
        for net in d_nets[d]:
            for od, pins in net_pins[net]:
                if od != d and od in place:
                    pts += [pad_xy[od][p] for p in pins]
        a = anc.get(d)
        if a:
            pts.append(a[0])
        if pts:
            return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        return rng.uniform(5, BOARD_W - 5), rng.uniform(5, BOARD_H - 5)

    def links(d):
        n = 1 if d in anc else 0
        for net in d_nets[d]:
            if any(od in place for od, _ in net_pins[net]):
                n += 1
        return n

    t0 = time.time()
    waiting = set(movable)
    while waiting:
        d = max(waiting, key=lambda q: (links(q) > 0, (parts[q].crt[2] - parts[q].crt[0]) * (parts[q].crt[3] - parts[q].crt[1]) > 6,
                                        links(q), parts[q].sheet == "SiP power", q))
        waiting.discard(d)
        pt = parts[d]
        sides = allowed_sides(pt)
        tx, ty = target_of(d)
        done = False
        for radius in [1, 2, 3, 4, 6, 8, 11, 15, 20, 30, 45, 70, 100]:
            for _ in range(200):
                x = round((tx + rng.uniform(-radius, radius)) / GRID) * GRID
                y = round((ty + rng.uniform(-radius, radius)) / GRID) * GRID
                rot = rng.choice((0, 90, 180, 270))
                side = rng.choice(sides)
                r = crt_rect(pt, x, y, rot, side, grow)
                if bounds_ok(r, pt) and grid.hits(side, r) is None:
                    place[d] = (x, y, rot, side)
                    set_pads(d, x, y, rot, side)
                    grid.add(("P", d), side, r)
                    done = True
                    break
            if done:
                break
        if not done:                                         # scan the board, nearest first
            best = None
            for side in sides:
                for rot in (0, 90):
                    gx = EDGE_CLR
                    while gx < BOARD_W:
                        gy = EDGE_CLR
                        while gy < BOARD_H:
                            r = crt_rect(pt, gx, gy, rot, side, grow)
                            if bounds_ok(r, pt) and grid.hits(side, r) is None:
                                dist = abs(gx - tx) + abs(gy - ty)
                                if best is None or dist < best[0]:
                                    best = (dist, gx, gy, rot, side, r)
                            gy += 0.5
                        gx += 0.5
            if best:
                _, x, y, rot, side, r = best
                place[d] = (x, y, rot, side)
                set_pads(d, x, y, rot, side)
                grid.add(("P", d), side, r)
                done = True
        if not done:
            unplaced.append(d)
    if unplaced:
        print("could not start:", " ".join(unplaced))
    movable = [d for d in movable if d in place]

    net_c = {n: net_cost(n) for n in net_pins}
    part_c = {d: part_cost(d) for d in movable}
    total = sum(net_c.values()) + sum(part_c.values())
    if log:
        print(f"start cost {total:.0f}, {len(movable)} movable, {time.time() - t0:.1f} s")

    same_fp = {}
    for d in movable:
        same_fp.setdefault(parts[d].fp, []).append(d)

    t = t_start
    alpha = (t_end / t_start) ** (1 / max(1, steps))
    accepted = 0
    t0 = time.time()
    for step in range(steps):
        t *= alpha
        d = movable[rng.randrange(len(movable))]
        pt = parts[d]
        ox, oy, orot, oside = place[d]
        kind = rng.random()
        partner = None
        if kind < 0.12 and len(same_fp[pt.fp]) > 1:
            partner = same_fp[pt.fp][rng.randrange(len(same_fp[pt.fp]))]
            if partner == d:
                continue
            nx, ny, nrot, nside = place[partner]
            px, py, prot, pside = ox, oy, orot, oside
            if nside not in allowed_sides(pt) or pside not in allowed_sides(parts[partner]):
                continue
        else:
            radius = max(0.5, 18.0 * t / t_start)
            if kind < 0.3:
                nx, ny = ox, oy
            elif kind < 0.5:
                tx, ty = target_of(d)
                nx = round((tx + rng.uniform(-3, 3)) / GRID) * GRID
                ny = round((ty + rng.uniform(-3, 3)) / GRID) * GRID
            else:
                nx = round((ox + rng.uniform(-radius, radius)) / GRID) * GRID
                ny = round((oy + rng.uniform(-radius, radius)) / GRID) * GRID
            nrot = rng.choice((0, 90, 180, 270)) if kind < 0.75 else orot
            sides = allowed_sides(pt)
            nside = rng.choice(sides) if len(sides) > 1 and rng.random() < 0.15 else oside
            if (nx, ny, nrot, nside) == (ox, oy, orot, oside):
                continue
        nr = crt_rect(pt, nx, ny, nrot, nside, grow)
        if not bounds_ok(nr, pt):
            continue
        key = ("P", d)
        if partner:
            ppt = parts[partner]
            pr = crt_rect(ppt, px, py, prot, pside, grow)
            if not bounds_ok(pr, ppt):
                continue
            pkey = ("P", partner)
            if grid.hits(nside, nr, ignore=(key, pkey)) is not None or grid.hits(pside, pr, ignore=(key, pkey)) is not None:
                continue
            if nr[0] < pr[2] and pr[0] < nr[2] and nr[1] < pr[3] and pr[1] < nr[3] and nside == pside:
                continue
            affected = set(nets_of(d)) | set(nets_of(partner))
            old = sum(net_c[n] for n in affected) + part_c[d] + part_c[partner]
            place[d] = (nx, ny, nrot, nside)
            place[partner] = (px, py, prot, pside)
            set_pads(d, nx, ny, nrot, nside)
            set_pads(partner, px, py, prot, pside)
            new_n = {n: net_cost(n) for n in affected}
            new_pc, new_pp = part_cost(d), part_cost(partner)
            delta = sum(new_n.values()) + new_pc + new_pp - old
            if delta <= 0 or rng.random() < math.exp(-delta / t):
                grid.remove(key)
                grid.remove(pkey)
                grid.add(key, nside, nr)
                grid.add(pkey, pside, pr)
                net_c.update(new_n)
                part_c[d], part_c[partner] = new_pc, new_pp
                total += delta
                accepted += 1
            else:
                place[d] = (ox, oy, orot, oside)
                place[partner] = (nx, ny, nrot, nside)
                set_pads(d, ox, oy, orot, oside)
                set_pads(partner, nx, ny, nrot, nside)
            continue
        if grid.hits(nside, nr, ignore=(key,)) is not None:
            continue
        affected = nets_of(d)
        old = sum(net_c[n] for n in affected) + part_c[d]
        place[d] = (nx, ny, nrot, nside)
        set_pads(d, nx, ny, nrot, nside)
        new_n = {n: net_cost(n) for n in affected}
        new_pc = part_cost(d)
        delta = sum(new_n.values()) + new_pc - old
        if delta <= 0 or rng.random() < math.exp(-delta / t):
            grid.remove(key)
            grid.add(key, nside, nr)
            net_c.update(new_n)
            part_c[d] = new_pc
            total += delta
            accepted += 1
        else:
            place[d] = (ox, oy, orot, oside)
            set_pads(d, ox, oy, orot, oside)
        if log and step % 300000 == 0 and step:
            print(f"  {step} T={t:.3f} cost={total:.0f} acc={accepted} {time.time() - t0:.0f} s", flush=True)
    if log:
        print(f"final cost {total:.0f}, accepted {accepted}, {time.time() - t0:.0f} s")

    # Repair: a part still far from its connections gets the best free spot near them. The
    # annealer rarely finds it at low temperature because the moves in between are blocked.
    def own_cost(d):
        return part_c[d] + sum(net_c[n] for n in nets_of(d))

    moved = 0
    for pass_no in range(2):
        for d in movable:
            pt = parts[d]
            ox, oy, orot, oside = place[d]
            key = ("P", d)
            tx, ty = target_of(d)
            tx, ty = round(tx / GRID) * GRID, round(ty / GRID) * GRID
            grid.remove(key)
            base = own_cost(d)
            best = (base - 0.5, None)
            tried = 0
            for ring in range(0, 41):
                r_mm = ring * GRID
                cells = [(tx + i * GRID, ty + j * GRID) for i in range(-ring, ring + 1) for j in range(-ring, ring + 1)
                         if max(abs(i), abs(j)) == ring]
                for nx, ny in cells:
                    for nside in allowed_sides(pt):
                        for nrot in (0, 90, 180, 270):
                            nr = crt_rect(pt, nx, ny, nrot, nside, grow)
                            if not bounds_ok(nr, pt) or grid.hits(nside, nr) is not None:
                                continue
                            tried += 1
                            place[d] = (nx, ny, nrot, nside)
                            set_pads(d, nx, ny, nrot, nside)
                            c = part_cost(d) + sum(net_cost(n) for n in nets_of(d))
                            if c < best[0]:
                                best = (c, (nx, ny, nrot, nside, nr))
                if tried > 160:
                    break
            if best[1]:
                nx, ny, nrot, nside, nr = best[1]
                place[d] = (nx, ny, nrot, nside)
                set_pads(d, nx, ny, nrot, nside)
                grid.add(key, nside, nr)
                for n in nets_of(d):
                    net_c[n] = net_cost(n)
                part_c[d] = part_cost(d)
                moved += 1
            else:
                place[d] = (ox, oy, orot, oside)
                set_pads(d, ox, oy, orot, oside)
                grid.add(key, oside, crt_rect(pt, ox, oy, orot, oside, grow))
    if log:
        print(f"repair moved {moved}, cost {sum(net_c.values()) + sum(part_c.values()):.0f}, {time.time() - t0:.0f} s")
    return place


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
    half-perimeter wire over its bounding box. Capacity: L1, L3 and L6 at a 0.30 mm track
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
    cap = 3 * (1 / 0.30) * 0.5                   # mm of track per mm2: 5.0
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
    if cmd == "solve":
        steps = int(argv[1]) if len(argv) > 1 else 1_500_000
        seed = int(argv[2]) if len(argv) > 2 else 1
        place = {d: v for d, v in FIXED.items() if d in parts}
        # the SiP's own caps and beads first, so they get the ring around it
        comments = bom_comments()
        at_soc = SITS_AT[0][0]
        ball_nets = {n for n, nodes in nets.items() if n not in ("GND", "NC") and any(q.startswith("U1.") for q in nodes)}

        def at_balls(p):
            """A cap from a SiP signal to ground (slew and filter caps sheet 14 wants within 5 mm)."""
            named = {q[2] for q in p.pads if q[4]}
            return "GND" in named and len(named) == 2 and bool(named & ball_nets) and not is_rail(
                next(iter(named - {"GND"})), nets.get(next(iter(named - {"GND"})), []))

        first = sorted(d for d, p in parts.items() if d not in FIXED and p.fp != "TP_PAD_1.0"
                       and (p.sheet == "SiP power" or at_soc.search(comments.get(d, "")) or at_balls(p)))
        # slew parts first of all (sheet 14 wants the 47 pF and 62 R within 5 mm of the balls)
        slew = re.compile(r"slew limiter|^47pF")
        clock_series = ("R700", "R729", "R1000", "R1321", "R1520")     # at the SoC, per their comments
        zero = [d for d in first if slew.search(comments.get(d, "")) or d in clock_series]
        place = solve(parts, nets, place, zero, steps=60000, seed=seed, margin=0.25)
        # then the SiP's own caps, beads and links, then the other parts that sit at a ball
        own = [d for d in first if d not in place and parts[d].sheet == "SiP power"]
        place = solve(parts, nets, place, own, steps=steps // 6, seed=seed, margin=0.25)
        first = [d for d in first if d not in place]
        place = solve(parts, nets, place, first, steps=steps // 6, seed=seed, margin=0.25)
        movable = sorted(d for d in parts if d not in place)
        place = solve(parts, nets, place, movable, steps=steps, seed=seed)
        write_csv(place)
    elif cmd == "add":
        place = {d: v for d, v in read_csv().items() if d in parts}
        place.update({d: v for d, v in FIXED.items() if d in parts})
        movable = sorted(d for d in parts if d not in place)
        print("new parts:", " ".join(movable) or "none")
        if movable:
            place = solve(parts, nets, place, movable, steps=int(argv[1]) if len(argv) > 1 else 40000 * len(movable),
                          t_start=1.0)
            write_csv(place)
    elif cmd == "check":
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
