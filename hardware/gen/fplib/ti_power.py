"""TI power ICs: PMIC, USB-PD sink, buck, buck-boost, load switches, surge clamp
(sheets 01, 02, 07).

All land patterns are TI's package addendum "EXAMPLE BOARD LAYOUT" (pad copper)
and, where the paste is not 1:1, "EXAMPLE STENCIL DESIGN". Coordinates were
taken from the drawing dimensions and cross-checked against the vector
geometry of the PDF pages (PyMuPDF, scale from the drawing's SCALE note).
Frame: origin = package centre (TI "PKG" / "SYMM" centre lines), +y up, so
TI's top-view y values are negated. Every footprint was checked against the
datasheet's pinout figure: pin 1 top left, counter-clockwise.

TI draws lead corners "(R0.05) TYP"; ``_r05`` sets each lead's roundrect
corner radius to 0.05 mm (footprints.with_radius).
Exposed pads are plain rectangles.
"""
from footprints import Footprint, dual, quad, smd, window_grid, with_radius

R_LEAD = 0.05


def _lead(name, x, y, w, h):
    """Roundrect lead with TI's R0.05 corners."""
    return with_radius([smd(name, x, y, w, h)], R_LEAD)[0]


def _ep(name, x, y, w, h):
    return smd(name, x, y, w, h, "rect")


def _r05(pads):
    return with_radius(pads, R_LEAD)


# ---------------------------------------------------------------- TPS65219 RSM
# TI TPS65219 PMIC, RSM0032B VQFN-32 4 x 4 mm, 0.4 mm pitch, exposed pad = 33.
# Datasheet SLVSGA0D (May 2022, rev. April 2026), repo datasheets/tps65219.pdf,
#   https://www.ti.com/lit/ds/symlink/tps65219.pdf
# Pinout: Figure 5-2 "RSM Package, 32-pin QFN (Top View)", p.4.
# Land: "RSM0032B EXAMPLE BOARD LAYOUT" (4219108/B 08/2019), p.158:
#   32X (0.55) x (0.2) leads, 28X (0.4) pitch, (3.85) between lead centres both
#   ways -> lead centres at +/-1.925; exposed pad (2.8) square.
# Paste: "RSM0032B EXAMPLE STENCIL DESIGN", p.159: EP 33 as 4X (1.23) square
#   windows centred (0.715) off both centre lines (77 % coverage); leads 1:1.
VQFN32_RSM_4X4 = Footprint(
    "VQFN32_RSM_4X4", "TI RSM0032B VQFN-32 4x4 mm, 0.4 mm pitch, 2.8 mm exposed pad (TPS65219)",
    _r05(quad(8, 8, 0.4, 3.85, 3.85, 0.55, 0.2)) + [_ep("33", 0, 0, 2.8, 2.8)],
    body=(4.0, 4.0),
    paste=window_grid(0, 0, 1.23, 1.23, 1.43, 1.43, 2, 2))

# ---------------------------------------------------------------- TPS25730D REF
# TI TPS25730D USB-PD sink, REF0038A WQFN-38 6 x 4 mm, two thermal pads.
# Datasheet SLVSGP9 (October 2023), https://www.ti.com/lit/ds/symlink/tps25730.pdf
# Pinout: Figure 5-1 "Top View of the TPS25730D 38-pin QFN Package", p.4: the
#   large left thermal pad is GND, the smaller right one DRAIN. The land drawing
#   numbers them 39 (left, 2.72 wide) and 40 (right, 1.53 wide), so 39 =
#   GND_PAD and 40 = DRAIN_PAD as in the symbol.
# Land: "REF0038A EXAMPLE BOARD LAYOUT" (4226763/C 11/2021), p.65:
#   pins 1-6 (left) and 7-19 / 26-38 (bottom / top): (0.55) x (0.2), 30X (0.4)
#   pitch; left column at -(2.925), rows at +/-(3.85)/2 = 1.925, rows centred on
#   PKG (pin 13 / pin 32 at x = 0); pins 1-6 at y = 1.0 ... -1.0.
#   EP 39: (2.72) x (2.65) centred (0.965) left of PKG; EP 40: (1.53) x (2.65)
#   centred (1.56) right of PKG.
#   Pins 20-22, 23-25, 32-33 and 34-35 are each one package terminal (outline
#   p.64) and TI lands them solder-mask defined: a copper block (metal under
#   mask, 0.05 larger) with a mask opening shaped like the terminal. Those
#   openings were read from the PDF vectors:
#     23-25: E, x 2.65..3.2, y 0.1..1.2, fingers 0.2 wide at y 0.2 / 0.65 / 1.1
#            (4X (0.45) pitch), spine x 2.65..2.85 (4X (0.2)); 20-22 mirrored.
#     34-35 / 32-33: U, fingers 0.2 x 0.55 at the normal pin sites, joined by a
#            0.6 x 0.2 bar at the inner end (y 1.65..1.85); notch 0.35 deep.
#   Here the copper is the opening shape (NSMD equivalent: the board's +0.05 mm
#   mask expansion then exposes exactly TI's metal). The joining bar / spine
#   carries the name of one pin of the group (32, 34, 21, 24).
# Paste: "REF0038A EXAMPLE STENCIL DESIGN", p.66: EP 39 4X (1.19) x (1.17)
#   windows at x -0.965 +/- 0.695 (= (1.66) / (0.27) from PKG), y +/-(0.69)
#   (0.685 from the vectors), 78 %; EP 40 2X (1.4) x (1.17) at x (1.56),
#   y +/-0.685, 80 %. U / E terminals and leads 1:1.
_REF = ([_lead(n, -2.925, 1.0 - 0.4 * i, 0.55, 0.2) for i, n in enumerate(range(1, 7))]
        + [_lead(n, -2.4 + 0.4 * i, -1.925, 0.2, 0.55) for i, n in enumerate(range(7, 20))]
        + [_lead(n, 2.925, y, 0.55, 0.2)
           for n, y in ((20, -1.1), (21, -0.65), (22, -0.2), (23, 0.2), (24, 0.65), (25, 1.1))]
        + [_lead("21", 2.75, -0.65, 0.2, 1.1), _lead("24", 2.75, 0.65, 0.2, 1.1)]
        + [_lead(n, 2.4 - 0.4 * i, 1.925, 0.2, 0.55) for i, n in enumerate(range(26, 39))]
        + [_lead("32", -0.2, 1.75, 0.6, 0.2), _lead("34", -1.0, 1.75, 0.6, 0.2)]
        + [_ep("39", -0.965, 0, 2.72, 2.65), _ep("40", 1.56, 0, 1.53, 2.65)])
WQFN38_REF_4X6 = Footprint(
    "WQFN38_REF_4X6", "TI REF0038A WQFN-38 6x4 mm, 0.4 mm pitch, GND + DRAIN thermal pads (TPS25730D)",
    _REF, body=(6.0, 4.0),
    paste=window_grid(-0.965, 0, 1.19, 1.17, 1.39, 1.37, 2, 2) + window_grid(1.56, 0, 1.40, 1.17, 0, 1.37, 1, 2),
    # the joining bar / spine of each multi-pin terminal is named 21, 24, 32 or 34
    joined=(("20", "21", "22"), ("23", "24", "25"), ("32", "33"), ("34", "35")))

# ---------------------------------------------------------------- LM61460 RJR
# TI LM61460 buck, RJR0014A VQFN-HR-14 4 x 3.5 mm (HotRod, no exposed pad).
# Datasheet SNVSBD5D (May 2019, rev. July 2022), https://www.ti.com/lit/ds/symlink/lm61460.pdf
#   (the downloaded copy carries addendum drawing 4223976/H 06/2026).
# Pinout: Figure 6-1 "14-Pin VQFN-HR RJR Package (Top View)", p.3. Package
#   outline p.55: body 4.0 (x) x 3.5 (y), pin 1 index top left.
# Land: "RJR0014A EXAMPLE BOARD LAYOUT", p.56 (all NSMD), from PKG / SYMM:
#   2-4: (0.7) long at x -(1.85); 2 / 4 (0.25) high at y +/-(0.525); 3 (0.3) high.
#   1 / 5: L = (0.7) x (0.4) foot at the left edge (x -2.2..-1.5, y 0.95..1.35)
#          + (0.35) x (1) leg up to the top edge (x -1.85..-1.5, y 0.95..1.95).
#   11 / 9: L = (0.8) x (0.4) foot (x 1.4..2.2) + (0.4) x (1) leg (x 1.4..1.8).
#   14 / 6 and 13 / 7: (0.25) x (0.7) at x -1.125 / -0.625 ((0.625), (0.5)),
#          y 1.25..1.95; 12 / 8: (0.4) x (1) at x (0.45), y 0.95..1.95.
#   10 (SW): (2.4) x (0.4) centred (1) right of PKG.
#   Each L is two same-named pads; TI's inner R0.12 fillet is not modelled.
# Paste: "RJR0014A EXAMPLE STENCIL DESIGN", p.57: pads 1, 5, 9, 11 printed at
#   90 % (leg 2X (0.3) / (0.35) wide, foot 4X (0.35) high, outer edges kept);
#   SW split into 2X (1.1) x (0.4) windows centred (0.35) and (1.65) right of
#   PKG; all other pads 1:1.
_RJR = [
    _lead("1", -1.85, 1.15, 0.7, 0.4), _lead("1", -1.675, 1.45, 0.35, 1.0),
    _lead("2", -1.85, 0.525, 0.7, 0.25), _lead("3", -1.85, 0, 0.7, 0.3), _lead("4", -1.85, -0.525, 0.7, 0.25),
    _lead("5", -1.85, -1.15, 0.7, 0.4), _lead("5", -1.675, -1.45, 0.35, 1.0),
    _lead("6", -1.125, -1.6, 0.25, 0.7), _lead("7", -0.625, -1.6, 0.25, 0.7), _lead("8", 0.45, -1.45, 0.4, 1.0),
    _lead("9", 1.8, -1.15, 0.8, 0.4), _lead("9", 1.6, -1.45, 0.4, 1.0),
    _lead("10", 1.0, 0, 2.4, 0.4),
    _lead("11", 1.8, 1.15, 0.8, 0.4), _lead("11", 1.6, 1.45, 0.4, 1.0),
    _lead("12", 0.45, 1.45, 0.4, 1.0), _lead("13", -0.625, 1.6, 0.25, 0.7), _lead("14", -1.125, 1.6, 0.25, 0.7),
]
VQFN_HR14_RJR = Footprint(
    "VQFN-HR14_RJR_3.5X4", "TI RJR0014A VQFN-HR-14 4x3.5 mm HotRod, no exposed pad (LM61460)",
    _RJR, body=(4.0, 3.5),
    paste=[(-1.65, 1.45, 0.3, 1.0), (-1.85, 1.125, 0.7, 0.35),         # 1
           (-1.65, -1.45, 0.3, 1.0), (-1.85, -1.125, 0.7, 0.35),       # 5
           (1.575, -1.45, 0.35, 1.0), (1.8, -1.125, 0.8, 0.35),        # 9
           (1.575, 1.45, 0.35, 1.0), (1.8, 1.125, 0.8, 0.35),          # 11
           (0.35, 0, 1.1, 0.4), (1.65, 0, 1.1, 0.4)])                  # 10 (SW)

# ---------------------------------------------------------------- TPS63070 RNM
# TI TPS63070 buck-boost, RNM0015A VQFN-HR-15 2.5 x 3 mm (HotRod, no exposed pad).
# Datasheet SLVSC58B (June 2016, rev. March 2019), https://www.ti.com/lit/ds/symlink/tps63070.pdf
# Pinout: Section 6 "QFN PACKAGE Top View", p.3. The land drawing is that view
#   turned 90 deg clockwise (not mirrored): pins 1-4 down the left, 5-8 along the
#   bottom, 12-15 along the top (15 left), bars 11 / 10 / 9 from top to bottom.
#   Package outline p.39: body 2.5 (x) x 3.0 (y), pin 1 index top left.
# Land: "RNM0015A EXAMPLE BOARD LAYOUT" (4222000/B 03/2020), p.40, from PKG / SYMM:
#   1-4 (NSMD): (0.6) x (0.25) at x -(1.15), 5X (0.5) pitch, y 0.75 ... -0.75.
#   15 / 14 and 5 / 6 (NSMD): (0.25) x (0.6) at x -(0.725) / -0.225, y +/-(2.8)/2.
#   9-11 (SMD; copper = the dimensioned mask opening): (0.25) high at y -0.5 /
#     0 / +0.5 ((0.5)); 9 / 11 (1.35) long from x 0.1 (centre (0.775));
#     10 (1.7) long from x -0.25 (centre (0.6)).
#   12-13 and 7-8: one package terminal each (outline p.39), SMD U-shaped land
#     (2X (0.75) x 4X (0.6), centre 2X (0.525)): fingers 0.25 wide at x 0.275 /
#     0.775 ((0.775)), joined by a 0.75 x 0.25 bar at the inner end (y 1.1..1.35);
#     notch 0.25 wide, 0.35 deep from the outer edge. The bar carries pin 12 / 7.
#   SMD copper (metal under mask) is 0.05 larger all round; here the copper is
#   the opening (NSMD equivalent with the board's +0.05 mm mask expansion).
# Paste: "RNM0015A EXAMPLE STENCIL DESIGN", p.41, "FOR EXPOSED PADS 9-11" (85 %):
#   9 / 11 split into 4X (0.575) x 0.25 windows at x (0.388) and (1.163);
#   10 into 2X (0.72) x 0.25 windows at x (0.14) and (1.06). Others 1:1.
_RNM = ([_lead(n, -1.15, 0.75 - 0.5 * i, 0.6, 0.25) for i, n in enumerate(range(1, 5))]
        + [_lead("5", -0.725, -1.4, 0.25, 0.6), _lead("6", -0.225, -1.4, 0.25, 0.6),
           _lead("7", 0.275, -1.4, 0.25, 0.6), _lead("8", 0.775, -1.4, 0.25, 0.6),
           _lead("7", 0.525, -1.225, 0.75, 0.25),
           _lead("9", 0.775, -0.5, 1.35, 0.25), _lead("10", 0.6, 0, 1.7, 0.25),
           _lead("11", 0.775, 0.5, 1.35, 0.25),
           _lead("12", 0.775, 1.4, 0.25, 0.6), _lead("13", 0.275, 1.4, 0.25, 0.6),
           _lead("12", 0.525, 1.225, 0.75, 0.25),
           _lead("14", -0.225, 1.4, 0.25, 0.6), _lead("15", -0.725, 1.4, 0.25, 0.6)])
VQFN_HR15_RNM = Footprint(
    "VQFN-HR15_RNM_2.5X3", "TI RNM0015A VQFN-HR-15 2.5x3 mm HotRod, no exposed pad (TPS63070)",
    _RNM, body=(2.5, 3.0),
    paste=[(0.3875, -0.5, 0.575, 0.25), (1.1625, -0.5, 0.575, 0.25),   # 9
           (0.14, 0, 0.72, 0.25), (1.06, 0, 0.72, 0.25),               # 10
           (0.3875, 0.5, 0.575, 0.25), (1.1625, 0.5, 0.575, 0.25)],    # 11
    # the joining bar of the 7-8 / 12-13 terminals is named 7 / 12
    joined=(("7", "8"), ("12", "13")))

# ---------------------------------------------------------------- TPS22965 DSG
# TI TPS22965 load switch, DSG0008A WSON-8 2 x 2 mm, 0.5 mm pitch, thermal pad = 9.
# Datasheet SLVSBJ0F (August 2012, rev. August 2016), https://www.ti.com/lit/ds/symlink/tps22965.pdf
# Pinout: "DSG PACKAGE 8-Pin WSON Top View", p.4 (1-4 VIN VIN ON VBIAS down the
#   left, 5-8 GND CT VOUT VOUT up the right).
# Land: "DSG0008A EXAMPLE BOARD LAYOUT" (4218900/E 08/2022), p.30: 8X (0.5) x
#   (0.25), 6X (0.5) pitch, (1.9) between column centres; pad 9 (0.9) x (1.6).
# Paste: "DSG0008A EXAMPLE STENCIL DESIGN", p.31: pad 9 as two (0.9) x (0.7)
#   windows centred (0.45) above / below SYMM (87 %); leads 1:1.
WSON8_DSG_2X2 = Footprint(
    "WSON8_DSG_2X2", "TI DSG0008A WSON-8 2x2 mm, 0.5 mm pitch, 0.9x1.6 mm thermal pad (TPS22965)",
    _r05(dual(8, 0.5, 1.9, 0.5, 0.25)) + [_ep("9", 0, 0, 0.9, 1.6)],
    body=(2.0, 2.0),
    paste=window_grid(0, 0, 0.9, 0.7, 0, 0.9, 1, 2))

# ---------------------------------------------------------------- TVS2200 DRV
# TI TVS2200 surge clamp, DRV0006A WSON-6 2 x 2 mm, 0.65 mm pitch, thermal pad = 7.
# Datasheet SLVSED5C (December 2017, rev. August 2023), https://www.ti.com/lit/ds/symlink/tvs2200.pdf
# Pinout: Figure 6-1 "DRV Package, 6-Pin SON (Bottom View)", p.3; seen from the
#   top, pins 1-3 (GND) run down the left with 1 at the top and 4-6 (IN) up the
#   right, as the land drawing (a top view) numbers them.
# Land: "DRV0006A EXAMPLE BOARD LAYOUT" (4222173/C 11/2025), p.19: 6X (0.45) x
#   (0.3), 4X (0.65) pitch, (1.95) between column centres; pad 7 (1) x (1.6).
# Paste: "DRV0006A EXAMPLE STENCIL DESIGN", p.20: pad 7 as two (1) x (0.7)
#   windows centred (0.45) above / below SYMM (88 %); leads 1:1.
WSON6_DRV_2X2 = Footprint(
    "WSON6_DRV_2X2", "TI DRV0006A WSON-6 2x2 mm, 0.65 mm pitch, 1.0x1.6 mm thermal pad (TVS2200)",
    _r05(dual(6, 0.65, 1.95, 0.45, 0.3)) + [_ep("7", 0, 0, 1.0, 1.6)],
    body=(2.0, 2.0),
    paste=window_grid(0, 0, 1.0, 0.7, 0, 0.9, 1, 2))

# ---------------------------------------------------------------- TPS22996 DRL
# TI TPS22996 dual load switch, DRL0008A SOT-583-8 (SOT-5X3), 0.5 mm pitch, no pad.
# Datasheet SLVSH99A (December 2023, rev. August 2025), https://www.ti.com/lit/ds/symlink/tps22996.pdf
# Pinout: Figure 5-1 "DRL Package, 8-Pin SOT (Top View)", p.3 (1-4 ON1 VIN1 VIN2
#   ON2 down the left, 5-8 GND VOUT2 VOUT1 VBIAS up the right).
# Package outline p.26: body 1.2 x 2.1 (1.1-1.3 x 2.0-2.2), 1.6 across the leads.
# Land: "DRL0008A EXAMPLE BOARD LAYOUT" (4224486/G 11/2024), p.27: 8X (0.67) x
#   (0.3), 6X (0.5) pitch, (1.48) between column centres. Stencil p.28: 1:1.
SOT583_8 = Footprint(
    "SOT583-8", "TI DRL0008A SOT-583-8 (SOT-5X3) 1.2x2.1 mm, 0.5 mm pitch (TPS22996)",
    _r05(dual(8, 0.5, 1.48, 0.67, 0.3)),
    body=(1.2, 2.1))

FOOTPRINTS = [VQFN32_RSM_4X4, WQFN38_REF_4X6, VQFN_HR14_RJR, VQFN_HR15_RNM,
              WSON8_DSG_2X2, WSON6_DRV_2X2, SOT583_8]
