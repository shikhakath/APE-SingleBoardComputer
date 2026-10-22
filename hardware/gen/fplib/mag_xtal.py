"""Magnetics, polymer bulk capacitor, crystals and oscillators.

Power inductors (generic IND symbol, via PART_RULES), the USB common-mode
choke, the USB-A polymer bulk capacitor (CAP_POL, via PART_RULES), the
32.768 kHz tuning-fork crystal (XTAL2, via PART_RULES) and the 3225 / 2520
4-pad crystals and oscillators (fixed-package symbols).

Two-terminal parts: pad "1" on the left. 4-pad crystals / oscillators: the
manufacturers draw them in the top view with #1 bottom left and the numbers
counter-clockwise (1 BL, 2 BR, 3 TR, 4 TL, #1-#2 along the long side). Each
is turned 90 deg clockwise, (x, y) -> (y, -x), so pad 1 is top left and the
order stays counter-clockwise: 1 TL, 2 BL, 3 BR, 4 TR, long side vertical.
A turn never mirrors, so the GND / VDD diagonal of the oscillators stays
where the data sheet puts it.

Downloaded copies of the documents cited below were read in the session
scratchpad (not in the repo). LCSC / JLCPCB URLs are the files those sites
serve for the quoted part numbers.
"""
from footprints import Footprint, chip, smd


def _quad4(cx, cy, w, h):
    """4 pads at (+-cx, +-cy), ``w`` along x, ``h`` along y; 1 TL, 2 BL,
    3 BR, 4 TR (counter-clockwise from the top left)."""
    return [smd("1", -cx, cy, w, h), smd("2", -cx, -cy, w, h),
            smd("3", cx, -cy, w, h), smd("4", cx, cy, w, h)]


# ------------------------------------------------------------ power inductors
# Murata DFE252012F-R47M=P2 (0.47 uH metal-alloy, LCSC C703140), PMIC bucks.
# Body: Murata Reference Specification J(E)TE243A-0017D-01, p.1/10 "Physical
# Dimensions": 2.5+-0.2 x 2.0+-0.2 x 1.2 max, electrodes 0.6+-0.2 at the ends
# (product page "Specifications Sheet",
#   https://pim.murata.com/asset/pim4/inductor/J(E)TE243A-0017_PDF_INDUCTOR).
# That sheet has no land pattern. Land: Murata DFE252012F series data sheet
# (ex-TOKO, PDF of 2016-06-05), p.1 "Recommended patterns":
#   https://www.murata.com/-/media/webrenewal/products/inductor/chip/tokoproducts/wirewoundmetalalloychiptype/m_dfe252012f.ashx
# outer 2.8, gap 1.2, land height 2.0 -> land length (2.8 - 1.2) / 2 = 0.8,
# centres at +-(0.6 + 0.4) = +-1.0. The older Murata sheet J(E)TE243A-0017B-01
# (LCSC C703140 file) p.5/9 "Recommended PCB pattern" gives the same 2.8 / 1.2
# / 2.0. Its p.7/9 "Precautions" 2a (low-insulation core): no through holes and
# no copper under the coil except the pattern to the electrodes, so keep vias,
# tracks and pour out of the gap between the pads on the top layer.
IND_MURATA_DFE252012F = Footprint(
    "IND_MURATA_DFE252012F", "Murata DFE252012F metal-alloy power inductor 2.5x2.0 mm, Murata recommended land",
    chip(0.8, 2.0, 1.2), body=(2.5, 2.0), marker="none")

# Sunlord MWSA-S molded power inductors, catalogue "Molded Power Inductors -
# MWSA-S Series", revised 2025/5/29 (JLCPCB/LCSC C408334 MWSA0402S-1R5MT and
# C408447 MWSA0603S-4R7MT serve the same file):
#   https://jlcpcb.com/partdetail/Sunlord-MWSA0402S1R5MT/C408334 (datasheet link)
# p.2 "Shape and Dimensions" (drawing for MWSA0412S ~ MWSA1265S) and table:
# B = length along the terminals (x), A = width (y), D x E = terminal,
# "Recommend Land Pattern": I = land length (x), J = gap, H = land height (y).
# MWSA0402S: A 4.2+-0.25, B 4.4+-0.35, C 1.8+-0.2, D 0.8, E 2.0; I 1.5, J 2.2,
# H 2.5 -> outer 1.5 + 2.2 + 1.5 = 5.2, centres +-(1.1 + 0.75) = +-1.85.
IND_SUNLORD_MWSA0402S = Footprint(
    "IND_SUNLORD_MWSA0402S", "Sunlord MWSA0402S molded power inductor 4.4x4.2 mm, Sunlord recommended land",
    chip(1.5, 2.5, 2.2), body=(4.4, 4.2), marker="none")

# MWSA0603S (same page): A 6.6+-0.2, B 7.0+-0.3, C 2.8+-0.2, D 1.6, E 3.0;
# I 2.35, J 3.7, H 3.5 -> outer 2.35 + 3.7 + 2.35 = 8.4, centres
# +-(1.85 + 1.175) = +-3.025.
IND_SUNLORD_MWSA0603S = Footprint(
    "IND_SUNLORD_MWSA0603S", "Sunlord MWSA0603S molded power inductor 7.0x6.6 mm, Sunlord recommended land",
    chip(2.35, 3.5, 3.7), body=(7.0, 6.6), marker="none")


# ------------------------------------------------------------ polymer capacitor
# Honor Elec (HONORCAP) RYHV10V150UF6*5, 150 uF 10 V conductive-polymer
# aluminium, D6.3 x L5.8 (size code 6*5), LCSC C48970647:
#   https://datasheet.lcsc.com/datasheet/pdf/f34224d04c6728b1a6079bfa1652a6b6.pdf?productCode=C48970647
# p.8 "2> Product size drawing" (and the p.1 table): base plate A = B =
# 6.6+-0.2, terminal tip-to-tip C = 7.2+-0.2 (p.1 gives 2 x 2.4 + 2.2 = 7.0),
# inner terminal gap P = 2.2 (+-0.2 on p.1), terminal width W = 0.5~0.8;
# the base plate's chamfered corners and the "+" are on the anode side.
# The data sheet has NO recommended land (checked all 20 pages), so the land
# is derived per IPC-7351B, CAPAE family, nominal (level B): toe JT 0.70,
# heel JH -0.05, side JS 0.50, F 0.10, P 0.05, round-off 0.05 mm.
#   L = 7.0..7.4 (7.2+-0.2), S = 2.0..2.4, W = 0.5..0.8
#   Zmax = 7.0 + 2(0.70) + sqrt(0.4^2 + 0.1^2 + 0.05^2) = 8.815 -> 8.85
#   Gmin = 2.4 - 2(-0.05) - sqrt(0.4^2 + 0.1^2 + 0.05^2) = 2.085 -> 2.05
#   Xmax = 0.5 + 2(0.50) + sqrt(0.3^2 + 0.1^2 + 0.05^2) = 1.820 -> 1.85
#   land length (8.85 - 2.05) / 2 = 3.40, width 1.85, centres +-2.725.
# (Panasonic's 6.3 mm V-chip land, 1.8-1.9 gap / 3.5 length / 1.6 width, is
# close.) Pad 1 = + (CAP_POL pin 1) on the left; body = the 6.6 x 6.6 base.
CP_SMD_D6_3X5_8 = Footprint(
    "CP_SMD_D6.3X5.8", "Polymer aluminium capacitor D6.3 x L5.8 SMD (6.6 mm base), IPC-7351B nominal land, pad 1 = +",
    chip(3.40, 1.85, 2.05), body=(6.6, 6.6), marker="plus", marker_pad="1")


# ------------------------------------------------------------ crystals
# Epson FC-135 32.768 kHz tuning-fork crystal, Q13FC13500003 (LCSC C99010),
# Epson data sheet "FC-135R / FC-135 / FC-255" (Chinese edition, LCSC C99010
# datasheet, https://www.lcsc.com/datasheet/C99010.pdf), p.1: body 3.2+-0.1 x
# 1.5+-0.1 x 0.8; #1 left, #2 right (top view, not polarised); "recommended
# land" (FC-135R / FC-135): lands 1.0 x 1.8, 2.5 between land centres (gap
# 2.5 - 1.0 = 1.5). The hatched area between the lands is "no other tracks
# or lands" (route nothing between the pads on the top layer).
XTAL_EPSON_FC_135 = Footprint(
    "XTAL_EPSON_FC-135", "Epson FC-135 32.768 kHz crystal 3.2x1.5 mm, Epson recommended land",
    chip(1.0, 1.8, 1.5), body=(3.2, 1.5), marker="none")

# YXC YSX321SL 3.2 x 2.5 mm 4-pad crystal: X322512MSB4SI (LCSC C9002) and
# X322525MOB4SI (LCSC C9006) - both LCSC files are the same series sheet:
#   https://www.lcsc.com/datasheet/lcsc_datasheet_2403291504_YXC-Crystal-Oscillators-X322512MSB4SI_C9002.pdf
#   https://datasheet.lcsc.com/datasheet/pdf/a84bd8d530dd46e4b0f6d0ee59d8a89c.pdf?productCode=C9006
# p.1 "Dimensions and Recommended Land Pattern": body 3.20+-0.1 x 2.50+-0.1 x
# 0.7; "Top View Crystal Connection": #1 BL, #2 BR (GND), #3 TR, #4 TL (GND),
# crystal #1-#3; "Top View Suggested Layout": lands 1.4 x 1.2, gaps 0.8 (x) and
# 0.5 (y) -> centres +-(0.4 + 0.7) = +-1.1 (x), +-(0.25 + 0.6) = +-0.85 (y);
# the layout's chamfered land is at #1 (bottom left), matching the figure.
# Turned 90 deg clockwise (module docstring): lands 1.2 (x) x 1.4 (y) at
# (+-0.85, +-1.1), body 2.5 x 3.2; 1 TL, 2 BL, 3 BR, 4 TR (crystal 1-3 diagonal).
XTAL_3225_4P = Footprint(
    "XTAL_3225_4P", "Crystal 3.2x2.5 mm 4-pad (YXC YSX321SL), 1/3 crystal, 2/4 GND, YXC suggested land",
    _quad4(0.85, 1.1, 1.2, 1.4), body=(2.5, 3.2), marker="pin1")


# ------------------------------------------------------------ oscillators
# SJK 3N12288G33YC 12.288 MHz LVCMOS oscillator, series 3N, 3.2 x 2.5 mm
# (LCSC C252334): https://www.lcsc.com/datasheet/C252334.pdf (spec A1,
# 2017-5-10), p.3 "2. DIMENSIONS": body 3.2+-0.1 x 2.5+-0.1 x 1.0; Top View
# 1 BL, 2 BR, 3 TR, 4 TL ("3. MARKING": pin-1 dot bottom left); PAD FUNCTION
# 1 enable, 2 GND, 3 OUT, 4 VDD; "Top View Suggested Layout": 1.4 / 0.8 / 1.4
# (x) by 1.2 / 0.5 / 1.2 (y) - the same land as the YXC crystal above.
# Turned 90 deg clockwise: 1 OE TL, 2 GND BL, 3 OUT BR, 4 VDD TR.
OSC_3225_4P = Footprint(
    "OSC_3225_4P", "Oscillator 3.2x2.5 mm 4-pad (1 OE, 2 GND, 3 OUT, 4 VDD), SJK suggested land",
    _quad4(0.85, 1.1, 1.2, 1.4), body=(2.5, 3.2), marker="pin1")

# ECS-2520MV MultiVolt HCMOS oscillator 2.5 x 2.0 mm:
#   https://ecsxtal.com/store/pdf/ECS-2520MV.pdf (Rev. 2026), p.1.
# Figure 1 "Top, Side, and Bottom views": body 2.5+-0.1 x 2.0+-0.1 x 0.8; the
# pad view is the BOTTOM view: #1 TL (C0.3 chamfer), #2 TR, #3 BR, #4 BL, i.e.
# clockwise from below = counter-clockwise from above (1 BL, 2 BR, 3 TR, 4 TL
# in the top view, #1-#2 along the 2.5 side). PAD CONNECTIONS 1 tri-state,
# 2 GND, 3 output, 4 VDD. Figure 2 "Suggested Land": lands 0.9 (x) x 0.8 (y),
# gaps 0.95 (x) and 0.65 (y) -> centres +-(0.475 + 0.45) = +-0.925 (x),
# +-(0.325 + 0.4) = +-0.725 (y). Cross-check: TI SK-AM62B (PROC142A) U53,
# ECS-2520MV on the bottom side, 35 x 31 mil lands at 72.8 x 57.1 mil pitch,
# 1 2 / 4 3 seen through the board = the same counter-clockwise top view.
# Turned 90 deg clockwise: lands 0.8 (x) x 0.9 (y) at (+-0.725, +-0.925),
# body 2.0 x 2.5; 1 OE TL, 2 GND BL, 3 OUT BR, 4 VDD TR.
OSC_2520_4P = Footprint(
    "OSC_2520_4P", "Oscillator 2.5x2.0 mm 4-pad (1 OE, 2 GND, 3 OUT, 4 VDD), ECS suggested land",
    _quad4(0.725, 0.925, 0.8, 0.9), body=(2.0, 2.5), marker="pin1")


# ------------------------------------------------------------ common-mode choke
# Sunlord SDCW2012-2-900TF wire-wound 2-line CMC 2.0 x 1.2 mm (LCSC/JLCPCB
# C54888), catalogue "Wire Wound Chip Common Mode Choke Coil - SDCW Series",
# revised 2025/5/23, p.1 "Shape and Dimensions" (SDCW2012 Type): body 2.0+-0.2
# x 1.2+-0.2 x 1.2+-0.2; terminal view (1) TL, (2) TR, (4) BL, (3) BR, so each
# winding runs end to end: A (1)-(2) on one long side, B (4)-(3) on the other
# (p.3 "Equivalent Circuit", dots on 1 and 4 = the same end). "Recommended
# Land Pattern": outer 2.6, gap 0.8 (x); outer 1.2, gap 0.4 (y) -> lands
# (2.6 - 0.8) / 2 = 0.9 x (1.2 - 0.4) / 2 = 0.4, centres +-(0.4 + 0.45) =
# +-0.85 (x), +-(0.2 + 0.2) = +-0.4 (y).
# The numbered view is drawn as printed (pin 1 already top left; pads match the
# symbol: 1, 4 left, 2, 3 right). The catalogue does not say whether that view
# is the top or the bottom; its mirror image only swaps the two ends of both
# windings together (1 and 4 stay on one end), which is electrically the same
# choke, and the part has no polarity mark (marker none).
CMC_SUNLORD_SDCW2012 = Footprint(
    "CMC_SUNLORD_SDCW2012", "Sunlord SDCW2012 common-mode choke 2.0x1.2 mm, 4 pads (A 1-2, B 4-3), Sunlord recommended land",
    [smd("1", -0.85, 0.4, 0.9, 0.4), smd("2", 0.85, 0.4, 0.9, 0.4),
     smd("3", 0.85, -0.4, 0.9, 0.4), smd("4", -0.85, -0.4, 0.9, 0.4)],
    body=(2.0, 1.2), marker="none",
    assumed="catalogue terminal view not marked top/bottom; drawn order kept "
            "(a mirror only reverses both windings together)")


FOOTPRINTS = [
    IND_MURATA_DFE252012F, IND_SUNLORD_MWSA0402S, IND_SUNLORD_MWSA0603S,
    CP_SMD_D6_3X5_8, XTAL_EPSON_FC_135, XTAL_3225_4P, OSC_3225_4P, OSC_2520_4P,
    CMC_SUNLORD_SDCW2012,
]
