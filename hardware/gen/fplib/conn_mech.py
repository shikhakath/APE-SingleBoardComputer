"""Connectors, switches and mechanical parts.

RJ45 MagJack (sheet 08), dual stacked USB-A (09), M.2 Key-E socket and the
SMT standoff for the card (13), 40-pin header (14), Tag-Connect TC2070 (15),
boot DIP switch and reset tact switch (06), mounting holes and test pads.

Connectors keep the drawing's top view with the mating face toward -y where
that face is known (RJ45, USB-A, M.2 card side). Downloaded copies of the
documents cited below were read in the session scratchpad (not in the repo);
LCSC / JLCPCB URLs are the files those sites serve for the quoted part
numbers. THT pad sizes are not given by any of these drawings unless stated:
they are the drawing's hole + 0.3..0.7 mm (annular ring >= 0.15 mm, JLCPCB).
"""
import math

from footprints import MIL_PER_MM, Footprint, npth, smd, tht


def _r(x, y):
    """Turn a point of a drawing 180 deg about the origin (no mirroring)."""
    return -x, -y


# ------------------------------------------------------------ RJ45 (sheet 08)
# HanRun HR911130A RJ45 MagJack, shield type A (LCSC C54408). Drawing rev A,
# page 2/2 "(Component Side View) (Mounting Pattern)":
#   https://datasheet.lcsc.com/datasheet/pdf/d9b1e130e54a44fe9872ced55aa393e4.pdf?productCode=C54408
# Image-only PDF, rendered at 400 dpi and read. "Component side view" = top
# view: it is the bottom view on the same page (pins 9 7 5 3 1 / 10 8 6 4 2,
# pin 1 right, opening at the bottom) flipped about the horizontal axis.
# Drawing frame (datum = line through the two 3.25 mm posts, centre line
# between them, +y toward the LED row = the RJ45 opening):
#   posts  ø3.25 x2 (plastic, NPTH)  x = +-11.43 / 2 = +-5.715, y = 0
#   LED    ø1.02 x4                  14, 13, 12, 11 at x = -6.625, -4.085,
#                                    +4.085, +6.625 (13.25 / 2 = 6.625 outer,
#                                    2.54 per pair), y = +4.90
#   shield ø1.63 x2 (plated tabs)    x = +-15.49 / 2 = +-7.745, y = -3.05
#   pins   ø0.89 x10                 row 9 7 5 3 1 at y = -8.89, row
#                                    10 8 6 4 2 at y = -8.89 + 2.54 = -6.35;
#                                    pin 5 is 0.64 right of the centre line,
#                                    2.54 per row, rows offset 1.27 ->
#                                    x(n) = 5.715 - (n - 1) * 1.27 (pin 1 at
#                                    +5.715 under the right post, 10 at -5.715)
#   body   16.10 wide (dashed outline), front edge +10.92, depth A = 21.30
#          -> rear edge 10.92 - 21.30 = -10.38
# The opening is at +y in the drawing frame, so every point is turned 180 deg
# (_r) to put it at -y: pin 1 ends up at the left, rows at the rear (+y).
# Pin 1 check: the front view puts P1 at the left and the green LED (11/12)
# at the left seen from the front; with the opening at -y the viewer's left
# is -x, which is where pin 1 and LEDs 11/12 land. Pads: ø0.89 -> 1.5,
# ø1.02 -> 1.6, ø1.63 -> 2.3 (drawing gives holes only).
_HR_PINS = [tht(n, *_r(5.715 - (n - 1) * 1.27, -8.89 if n % 2 else -6.35), 1.5, hole=0.89)
            for n in range(1, 11)]
_HR_LED = [tht(n, *_r(x, 4.90), 1.6, hole=1.02)
           for n, x in ((14, -6.625), (13, -4.085), (12, 4.085), (11, 6.625))]
RJ45_HANRUN_HR911130A = Footprint(
    "RJ45_HANRUN_HR911130A",
    "HanRun HR911130A RJ45 MagJack 1000BASE-T with LEDs, shielded, THT (HanRun mounting pattern)",
    _HR_PINS + _HR_LED + [
        tht("15", *_r(7.745, -3.05), 2.3, hole=1.63),      # shield tab on the pin-1 side
        tht("16", *_r(-7.745, -3.05), 2.3, hole=1.63),
        npth(*_r(5.715, 0), 3.25),
        npth(*_r(-5.715, 0), 3.25),
    ],
    body=(-8.05, -10.92, 8.05, 10.38),
    assumed="The drawing does not number the two shield tabs: 15 = the tab on the pin-1 side, "
            "16 = the other (both SHIELD).")

# ------------------------------------------------------------ USB-A (sheet 09)
# Bossie BX-TYPE-A-MWC44 dual stacked USB 2.0 Type-A, THT right angle (LCSC
# C18077688). Drawing rev A, sheet 1/1, "RECOMMANDED PCBA LAYOUT Top VIEW
# (TOLERANCE +-0.05)":
#   https://datasheet.lcsc.com/datasheet/pdf/5bd3848faf114811a5412815f6d91e72.pdf?productCode=C18077688
#   contacts ø0.90 x8, 2 rows x 4: x = +-2.00 / 2, +-7.00 / 2; rows 2.71 apart
#   shell pegs ø2.30 x4: x = +-13.14 / 2 = +-6.57, two rows 5.68 apart
#   the row nearer one peg row is 5.68 - 5.33 = 0.35 from it.
# Side view: depth 17.00, the far peg row is 9.97 from the mating face, the
# contact rows sit 5.33 and 2.62 behind the front pegs, i.e. the contacts and
# the 0.35-offset peg row are at the REAR. Frame used here: front pegs at
# y = 0, +y toward the rear, mating face at y = -9.97 (-y), rear edge at
# 5.68 + (17.00 - 9.97 - 5.68) = 7.03; body width 15.20 (front view).
# Numbering (the drawing has none; symbol symlib/usb.py, docs B8):
#   1-4 = LOWER port = FRONT row (y = 2.62), 5-8 = UPPER port = REAR row
#   (y = 5.33): both rows use the same x, so the lower port's contacts, which
#   run back at the low tongue, must turn down in front of the upper port's
#   tails coming down the rear wall (side view: the front-row tail leaves a
#   separate lower housing block).
#   VBUS..GND at x = -3.5, -1.0, +1.0, +3.5 (VBUS on the left seen from the
#   front, tongue on top as in the front view). Cross-checks: the LCSC
#   EasyEDA footprint USB-A-TH_BX-TYPE-A-MWC44 (VCC at the same -x for both
#   rows, its own 1-4 in the rear row) and TI SK-AM62A J7 (Wurth 629104151021,
#   reference/2_PROC142A IPC-D-356: VBUS pad at the left seen from the board
#   edge).
#   9-12 = shell pegs: 9 front left, 10 front right, 11 rear left, 12 rear right.
# Pads: ø0.90 -> 1.5, ø2.30 -> 3.0.
USBA_2X_BX_TYPE_A_MWC44 = Footprint(
    "USBA_2X_BX-TYPE-A-MWC44",
    "Bossie BX-TYPE-A-MWC44 dual stacked USB 2.0 Type-A receptacle, THT right angle",
    [tht(n, x, y, 1.5, hole=0.90)
     for row, y in (((1, 2, 3, 4), 2.62), ((5, 6, 7, 8), 5.33))
     for n, x in zip(row, (-3.5, -1.0, 1.0, 3.5))]
    + [tht(9, -6.57, 0, 3.0, hole=2.30), tht(10, 6.57, 0, 3.0, hole=2.30),
       tht(11, -6.57, 5.68, 3.0, hole=2.30), tht(12, 6.57, 5.68, 3.0, hole=2.30)],
    body=(-7.60, -9.97, 7.60, 7.03),
    assumed="The drawing does not number the pads: 1-4 = lower port in the front contact row and 5-8 = "
            "upper port in the rear row (from the stacked contact geometry), VBUS-D-D+-GND left to right "
            "seen from the front, 9-12 = shell pegs FL, FR, RL, RR.")

# ------------------------------------------------------------ M.2 (sheet 13)
# LOTES APCI0085-P002A, 67-pin M.2 Key E socket, H3.2 (LCSC C841649).
# Drawing AP-APCI0085-P rev 1, sheet 3/4 "RECOMMENDED PCB LAYOUT (TOP VIEW)",
# default tolerance +-0.05:
#   https://datasheet.lcsc.com/datasheet/pdf/dd04174b85f5751d9f98e98486e9a8c9.pdf?productCode=C841649
# Vector PDF; the figures below were also measured from the PDF geometry
# (10.597 pt/mm) and agree to 0.01 mm. Frame: x = 0 on the centre line
# (datum N), y = 0 on the locating-hole centres.
#   contacts 0.30 x 1.55, 0.5 pitch per row: x(n) = -9.25 + (n - 1) * 0.25
#     (pin 1 at -9.25, 75 at +9.25, pin 23 at -9.25 + 5.50, pin 33 at -1.25;
#      pin 2 at -9.00, 74 at +9.00, pin 22 at -4.00, pin 32 at -1.50)
#   odd row: outer edge 6.05, inner edge 4.50 above the holes -> y = +5.275
#   even row: outer edge 3.05 below the holes -> y = -3.05 + 1.55 / 2 = -2.275
#   SMT tabs 1.20 x 2.75 at x = +-20.70 / 2 = +-10.35, centred on the 4.50
#     line (PDF: 3.13..5.88)
#   locating holes ø1.10 at x = -10.00 and ø1.60 at x = +10.00 (20.00 apart),
#     non-plated (plastic pegs)
#   body (dashed): 22.00 max wide, y -2.54..+5.25 (PDF).
# Card side = the even row (-y): the card's bottom-side (even) contacts sit at
# the front of the socket. Confirmed on TI SK-AM62A J2 (TE 2199119-4, IPC-D-356
# netlist): the 2230 card standoff hole lies beyond the even row.
# Numbering from the drawing (sheet 1/4 and 3/4 callouts PIN 1/2/22/23/32/33/
# 74/75); the tabs are unnumbered: 76 = left, 77 = right (symbol, docs B9).
# The EasyEDA cross-check file for C841649 in the scratchpad is a 403 error
# page, so there was nothing to compare against.
_M2_ODD = list(range(1, 24, 2)) + list(range(33, 76, 2))
_M2_EVEN = list(range(2, 23, 2)) + list(range(32, 75, 2))
M2_KEYE_APCI0085 = Footprint(
    "M2_KEYE_APCI0085", "LOTES APCI0085-P002A M.2 Key-E socket, 67 contacts 0.5 mm, H3.2, SMT",
    [smd(n, -9.25 + (n - 1) * 0.25, 5.275, 0.30, 1.55, "rect") for n in _M2_ODD]
    + [smd(n, -9.25 + (n - 1) * 0.25, -2.275, 0.30, 1.55, "rect") for n in _M2_EVEN]
    + [smd(76, -10.35, 4.50, 1.20, 2.75, "rect"), smd(77, 10.35, 4.50, 1.20, 2.75, "rect"),
       npth(-10.00, 0, 1.10), npth(10.00, 0, 1.60)],
    body=(-11.0, -2.54, 11.0, 5.25), marker_at=(-9.25, 6.65),
    assumed="The drawing does not number the two SMT hold-down tabs: 76 = left (pin-1 end), 77 = right.")
if len(M2_KEYE_APCI0085.pad_names()) != 69:
    raise ValueError("M.2 Key-E footprint must have 67 contacts + 2 tabs")

# ------------------------------------------------------------ header (sheet 14)
# HanElectricity 2541WV-2x20P, 2x20 pin header 2.54 mm, THT (LCSC C25503140).
# Drawing 2541WV-2xXXP rev A (2015-05-03), single sheet, "P.C.B Layout":
#   https://www.lcsc.com/datasheet/lcsc_datasheet_2407041454_HanElectricity-2541WV-2x20P_C25503140.pdf
# ø1.0 holes, 2.54 pitch, rows 2.54 apart; table row 20: A = 50.80 (body
# length), B = 48.26 (= 19 x 2.54, first to last pin); body width 5.0. No pad
# size given: 1.7 mm (ring 0.35), pin 1 square.
# Numbering (the drawing has none; docs B10): Raspberry Pi / IDC, odd pins in
# one row, even in the other, 1-2 at the left end. Laid out as on a Pi seen
# from the top with the header along the top board edge: odd row at -y
# (inner), even row at +y (edge side).
HDR_2X20_P2_54_THT = Footprint(
    "HDR_2X20_P2.54_THT", "Pin header 2x20 2.54 mm THT, Raspberry Pi 40-pin numbering (HanElectricity 2541WV-2x20P)",
    [tht(n, -24.13 + ((n - 1) // 2) * 2.54, -1.27 if n % 2 else 1.27, 1.7, hole=1.0,
         shape="rect" if n == 1 else "round") for n in range(1, 41)],
    body=(50.80, 5.0),
    assumed="The drawing does not number the pins: Raspberry Pi numbering, odd pins in the row at -y, even "
            "at +y, pin 1 at the left end.")

# ------------------------------------------------------------ switches (sheet 06)
# SHOU HAN 2.54-4P TPGT, 4-position slide DIP switch, SMD gull wing (LCSC
# C6331176). Drawing DSP-DSICXXLS-AP (DSIC series), p.1 "P.C.B LAYOUT":
#   https://www.lcsc.com/datasheet/C6331176.pdf
# pads 1.1 (along the row) x (11 - 6.6) / 2 = 2.2; inner edges 6.6 apart,
# outer edges 11 apart -> row centres +-(6.6 + 2.2) / 2 = +-4.4; pitch 2.54
# (gap 1.44). Body: A = 10.16 (4 poles) x 6.15. Kept in the drawing's view:
# "ON" printed at the top edge, positions 1-4 left to right at the bottom.
# Numbering (the drawing numbers only the positions; symbol, docs B11): DIP
# style, pads 1-4 left to right along the bottom (numbered) edge, 5-8 right to
# left along the top, so position k = pads k (bottom) and 9 - k (above it).
SW_DIP4_SMD_2_54 = Footprint(
    "SW_DIP4_SMD_2.54", "DIP switch 4-position SPST, 2.54 mm SMD gull wing (SHOU HAN 2.54-4P TPGT)",
    [smd(k, -3.81 + (k - 1) * 2.54, -4.4, 1.1, 2.2) for k in range(1, 5)]
    + [smd(9 - k, -3.81 + (k - 1) * 2.54, 4.4, 1.1, 2.2) for k in range(1, 5)],
    body=(10.16, 6.15),
    assumed="The drawing numbers only the switch positions: pads 1-4 along the numbered edge, 5-8 back "
            "along the ON edge, position k = pads k and 9-k.")

# XKB TS-1187A-B-A-B tactile switch 5.1 x 5.1 mm, 4 SMD terminals (LCSC
# C318884). Drawing TS-1187A-X-X-X rev A0, sheet 1/1, "P.C.B LAYOUT TOP
# VIEW" (image-only PDF, rendered and read):
#   https://www.lcsc.com/datasheet/C318884.pdf
# pads: outer x 7.0, inner x 5.0 -> 1.0 long, centres +-3.0; outer y 4.5,
# inner y 3.0 -> 0.75 high, centres +-(3.0 + 4.5) / 4 = +-1.875 (terminal
# pitch 3.7 in the part view). Body 5.1 x 5.1. Terminals in the top view:
# A top left, B top right, C bottom left, D bottom right; the schematic on
# the same sheet ties A-B and C-D, the switch closes A/B to C/D. Pads 1-4 =
# A, B, C, D (symbol), so 1/2 are one contact and 3/4 the other. No marker:
# a 180 deg turn swaps the pairs but keeps 1-2 and 3-4 shorted.
SW_TACT_5_1X5_1_SMD4 = Footprint(
    "SW_TACT_5.1X5.1_SMD4", "Tactile switch 5.1x5.1 mm SPST-NO, 4 SMD terminals A=B / C=D (XKB TS-1187A)",
    [smd(1, -3.0, 1.875, 1.0, 0.75), smd(2, 3.0, 1.875, 1.0, 0.75),
     smd(3, -3.0, -1.875, 1.0, 0.75), smd(4, 3.0, -1.875, 1.0, 0.75)],
    body=(5.1, 5.1), marker="none",
    assumed="The drawing letters the terminals A-D: pads 1-4 = A, B, C, D (A-B and C-D tied inside).")

# ------------------------------------------------------------ debug (sheet 15)
# Tag-Connect TC2070-IDC-NL footprint (no part is fitted; the cable is a
# tool). Drawing TC2070-IDC-NL rev B, sheet 1 of 3 "PCB TOP LAYER":
#   https://www.tag-connect.com/wp-content/uploads/bsk-pdf-manager/TC2070-IDC-NL_Datasheet_12.pdf
#   contact pads ø0.787 (0.031") x14, 1.27 (0.050") pitch, rows 2 x 0.635
#     (0.025") = 1.27 apart; 1-7 in the bottom row left to right, 8-14 in the
#     top row right to left (14 above 1)
#   alignment holes ø0.990 (0.039") NON-PLATED x3: one 1.27 left of the pad-1
#     column on the pad-row centre line, two at 10.16 (0.400") from it,
#     +-1.016 (0.040") off the centre line (1.27 right of the pad-7 column).
# Frame: left hole at (0, 0). The pads are SMD with NO SOLDER PASTE (note 3):
# footprints.py cannot drop paste per pad, so the board needs a paste rule
# that removes paste from this footprint's pads (e.g. paste expansion -1 mm,
# InComponent of TC2070-NL). Layout notes 1-2 and sheet 3: no tracks or vias
# in the KEEP OUT area = the rectangle between the pad centres, x 1.27..8.89,
# y -0.635..+0.635 (a via <= 0.3 mm finished hole is allowed in a pad centre
# or between four pads); no other track within 0.020" (0.51 mm) of a pad.
# Body = the plug footprint on sheet 2 (2:1): 16.5 x 6.0, centred on the hole
# pattern (x = 10.16 / 2); parts up to 1.0 mm tall may sit under the plug, so
# a courtyard overlap with such parts can be waived.
TC2070_NL = Footprint(
    "TC2070-NL", "Tag-Connect TC2070-NL plug-of-nails footprint, 14 pads, no paste, 3 NPTH (not a part, DNL)",
    [smd(k, 1.27 * k, -0.635, 0.787, 0.787, "round") for k in range(1, 8)]
    + [smd(15 - k, 1.27 * k, 0.635, 0.787, 0.787, "round") for k in range(1, 8)]
    + [npth(0, 0, 0.99), npth(10.16, 1.016, 0.99), npth(10.16, -1.016, 0.99)],
    body=(5.08 - 8.25, -3.0, 5.08 + 8.25, 3.0))

# ------------------------------------------------------------ mechanical
# Wurth WA-SMSI 9774015243R, SMT steel spacer, M2 internal thread, L = 1.5 mm
# (JLC C22431324). Data sheet rev 001.003 (2025-12-31), p.1/6 "Recommended
# Land Pattern" and "Stencil Suggestion":
#   https://www.we-online.com/components/products/datasheet/9774015243R.pdf
# suggested solder pad ø5.3 (annular) around a ø3.0 NON-PLATED through hole
# (the ø2.8 x 1.4 spigot drops into it); body ø4.35. Modelled as one
# Multi-Layer pad with a non-plated hole, so it also has a ø5.3 ring on the
# bottom layer (harmless: the pin goes to GND). Altium makes no paste for a
# Multi-Layer pad, so the stencil suggestion (ring ø3.1..ø5.2 cut by four
# 0.6 mm webs on the axes) is added as Top Paste arcs: three concentric arcs
# 0.35 wide per quadrant, ends set back so the round caps stop at the webs.
# Check in Altium that the pad itself adds no paste.
def _ring_paste(r_in, r_out, web, n=3):
    w = (r_out - r_in) / n
    out = []
    for i in range(n):
        r = r_in + w * (i + 0.5)
        phi = math.degrees(math.asin((web / 2 + w / 2) / r))
        for q in range(4):
            out.append(f"ARC|0|0|{r * MIL_PER_MM:.3f}|{q * 90 + phi:.2f}|{q * 90 + 90 - phi:.2f}|"
                       f"{w * MIL_PER_MM:.3f}|Top Paste")
    return out


STANDOFF_WE_9774015243R = Footprint(
    "STANDOFF_WE_9774015243R", "Wurth WA-SMSI 9774015243R SMT spacer M2 L1.5, 5.3 mm ring pad, 3.0 mm NPTH",
    [tht("1", 0, 0, 5.3, hole=3.0, plated=False)],
    body=(4.35, 4.35), marker="none", extra=_ring_paste(3.1 / 2, 5.2 / 2, 0.6))

# M2.5 plated mounting hole, Raspberry Pi HAT pattern. Raspberry Pi "HAT
# board mechanical specification" (c) 2014/2018:
#   https://github.com/raspberrypi/hats/blob/master/hat-board-mechanical.pdf
# "4x M2.5 MOUNTING HOLES DRILLED TO 2.75mm +/- 0.05mm", "MOUNTING HOLE LAND
# SHOULD BE MIN. 6.2mm" -> hole 2.75 (between ISO 273 medium 2.7 and coarse
# 3.1), pad 6.2. The HAT spec wants a HAT's own holes non-plated or isolated;
# this is the host board, where the symbol ties the pad to GND.
MH_M2_5_PLATED = Footprint(
    "MH_M2.5_PLATED", "Mounting hole M2.5, plated, 2.75 mm hole, 6.2 mm pad (Raspberry Pi HAT pattern)",
    [tht("1", 0, 0, 6.2, hole=2.75)],
    body=(6.2, 6.2), marker="none")

# Bare SMD test pad, 1.0 mm round (no data sheet: generic probe target).
TP_PAD_1_0 = Footprint(
    "TP_PAD_1.0", "Test pad, 1.0 mm round SMD",
    [smd("1", 0, 0, 1.0, 1.0, "round")],
    body=(1.0, 1.0), marker="none")

FOOTPRINTS = [RJ45_HANRUN_HR911130A, USBA_2X_BX_TYPE_A_MWC44, M2_KEYE_APCI0085, HDR_2X20_P2_54_THT,
              SW_DIP4_SMD_2_54, SW_TACT_5_1X5_1_SMD4, TC2070_NL, STANDOFF_WE_9774015243R,
              MH_M2_5_PLATED, TP_PAD_1_0]
