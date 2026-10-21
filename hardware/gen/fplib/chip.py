"""Two-terminal chip parts: resistors, MLCCs, ferrite beads, LEDs, PTC fuse.

Generic RES / CAP / FERRITE / LED symbols reach these through
footprints.resolve() (PART_RULES and the size code in the comment). Every
footprint is two pads along x, pad "1" on the left, built with
``chip(pad_l, pad_w, gap)``: pad_l = land length along the part (x), pad_w =
land width across it (y), gap = distance between the inner land edges.
Outer land extent = gap + 2 * pad_l. All lands are reflow lands.

Downloaded copies of the documents cited below were read in the session
scratchpad (not in the repo); LCSC URLs are the files LCSC serves for the
quoted LCSC part numbers.
"""
from footprints import Footprint, chip


def _fp(name, desc, pad_l, pad_w, gap, body, marker="none"):
    return Footprint(name, desc, chip(pad_l, pad_w, gap), body=body, marker=marker,
                     marker_pad="2" if marker == "cathode" else "1")


# ------------------------------------------------------------ resistors
# UNI-ROYAL thick-film chip resistors: 0402WGFxxxxTCE (C25744 0402WGF1002TCE,
# C11702, C25092, C25105, ...) and 0603WAFxxxxT5E (C21189 0603WAF0000T5E).
# UNI-ROYAL "Thick Film Chip Resistors" data sheet, Jun.21,2025 V.9,
# section 11.3 "Soldering pad size recommended", p.8/9 (body: section 5, p.4/9),
#   https://datasheet.lcsc.com/datasheet/pdf/f42da6c80a0747bae77c2f98f4e46d1d.pdf (LCSC C21189)
# The older Feb.12,2019 V.3 issue (section 8 "Recommend the size of welding
# plate", p.5/9) has the same table:
#   https://datasheet.lcsc.com/datasheet/pdf/0a975aaa49b7c97f38a963127be4a823.pdf (LCSC C25744 / C17168)
# Drawing: A = gap between lands, B = land length, C = land width,
# D = outer extent  ->  chip(pad_l=B, pad_w=C, gap=A).

# 0402: A 0.50+-0.05, B 0.45+-0.05, C 0.5+-0.05, D 1.4+-0.05 (A + 2B = D).
# Body 1.00 x 0.50 mm.
R0402 = _fp("R0402", "Chip resistor 0402 (1005), UNI-ROYAL recommended land",
            pad_l=0.45, pad_w=0.50, gap=0.50, body=(1.0, 0.5))

# 0603: A 0.9+-0.05, B 0.65+-0.05, C 0.8+-0.05, D 2.1+-0.05. The table is not
# self-consistent (A + 2B = 2.2 > D); A = 0.90 and D = 2.10 give B = 0.60,
# the only set inside every tolerance. Body 1.60 x 0.80 mm.
R0603 = _fp("R0603", "Chip resistor 0603 (1608), UNI-ROYAL recommended land",
            pad_l=0.60, pad_w=0.80, gap=0.90, body=(1.6, 0.8))


# ------------------------------------------------------------ MLCCs
# Samsung Electro-Mechanics MLCC Product Manual, section 5-4 "Land Dimension",
# table "Reflow Footprint" (PDF p.33/38 of the CL05B104KO5NNNC spec sheet,
# issued APR.09.2024; product.samsungsem.com/mlcc/CL05B104KO5NNN.do ->
# "Specsheet" download, POST /part/download.do). Rows are by metric chip size
# and chip length tolerance; the figure gives a = gap between lands, b = land
# length, c = land width  ->  chip(pad_l=b, pad_w=c, gap=a), each the middle
# of the published range. Chip tolerances from the product pages
# (product.samsungsem.com/mlcc/<P/N>.do, checked 2026-10-17).

# 0402 (1005). Parts: CL05B104KO5NNNC L 1.00+-0.05, CL05A225MQ5NSNC +-0.07,
# CL05A105KA5NQNC +-0.10, CL05A475MP5NRNC +-0.15 (plus FH 0402CG C0G caps).
# Used the +-0.10 row: a 0.38~0.46, b 0.50~0.58, c 0.56~0.64. a and b are
# also inside the +-0.05 and +-0.15 rows; c = 0.60 is 0.01 mm outside both
# (+-0.05: c <= 0.59, +-0.15: c >= 0.61). Body 1.00 x 0.50 mm.
C0402 = _fp("C0402", "MLCC 0402 (1005), Samsung reflow land",
            pad_l=0.54, pad_w=0.60, gap=0.42, body=(1.0, 0.5))

# 0603 (1608). CL10A106KP8NNNC L 1.60+-0.10 (also YAGEO CC0603 caps):
# +-0.10 row a 0.63~0.73, b 0.71~0.81, c 0.80~0.90. Body 1.60 x 0.80 mm.
C0603 = _fp("C0603", "MLCC 0603 (1608), Samsung reflow land",
            pad_l=0.76, pad_w=0.85, gap=0.68, body=(1.6, 0.8))

# 0805 (2012). CL21A106KAYNNNE, CL21A476MQYNNNE L 2.00+-0.20; CL21A226MAQNNNE
# +-0.15. +-0.20 row a 0.83~0.93, b 0.91~1.01, c 1.35~1.45 (the values are
# also inside the +-0.15 row). Body 2.00 x 1.25 mm.
C0805 = _fp("C0805", "MLCC 0805 (2012), Samsung reflow land",
            pad_l=0.96, pad_w=1.40, gap=0.88, body=(2.0, 1.25))

# 1206 (3216). CL31A106KBHNNNE, CL31A226KAHNNNE, CL31A476MPHNNNE L 3.20+-0.20:
# +-0.20 row a 1.64~1.76, b 1.19~1.31, c 1.74~1.86. Body 3.20 x 1.60 mm.
C1206 = _fp("C1206", "MLCC 1206 (3216), Samsung reflow land",
            pad_l=1.25, pad_w=1.80, gap=1.70, body=(3.2, 1.6))


# ------------------------------------------------------------ ferrite beads
# Murata lands for BLM15P / BLM18P/S/K are solder-resist defined: the table's
# c is the solder-resist opening and d is the copper width under the resist,
# chosen by rated current and copper thickness. The batch tool has no per-pad
# mask, so the pad here is the opening (b - a)/2 x c with the board mask rule;
# route copper at least d wide into each land under the mask. This board has
# 35 um (1 oz) outer copper (docs/research/bom/jlcpcb-stackup-and-cost.md).

# BLM15PX121SN1D (120 ohm, 2000 mA). Murata Reference Spec. JENF243A-0018AJ-01,
# section 10-1 "Land pattern designing", "< For BLM15P, BLM15AX, BLM15KD type >",
# P8/11:  https://datasheet.lcsc.com/datasheet/pdf/f85b01b3a1a015a5ec4a9f03876e0063.pdf (LCSC C88970)
# a = 0.4 (gap), b = 1.2 to 1.4 (outer extent), c = 0.5 (land width);
# d (2.2 A max row) = 1.2 / 0.7 / 0.5 mm for 18 / 35 / 70 um copper -> 0.7 mm here.
# b taken at 1.4 (same 1.4 mm outer extent as R0402): chip(pad_l=(1.4 - 0.4)/2,
# pad_w=c, gap=a). Body 1.0 x 0.5 mm.
FB0402 = _fp("FB0402", "Ferrite bead 0402 (1005), Murata BLM15P reflow land",
             pad_l=0.50, pad_w=0.50, gap=0.40, body=(1.0, 0.5))

# BLM18KG601SN1D (600 ohm, 1300 mA), BLM18PG121SN1D (120 ohm, 2000 mA),
# BLM18SG260TN1D (26 ohm, 6000 mA): all in Murata Reference Spec.
# JENF243A-0003Z-01 "Chip Ferrite Bead BLM18_N Series", section 10-1
# "Land pattern designing", "< For BLM18P/BLM18S/BLM18K type >", P.9/12:
#   https://datasheet.lcsc.com/datasheet/pdf/12e7821a4cf54a50a621ce7fb859e87d.pdf (LCSC C87063)
# (murata.com's PDF link only redirects to a script-rendered product page.)
# a = 0.7 (gap), b = 1.8 to 2.0 reflow (outer extent), c = 0.7 (land width),
# the same for the P, S and K types; only d differs by current, at 35 um:
# 0.7 mm for KG601 (0.5-1.5 A row) and PG121 (1.7-2.5 A row), 3.3 mm for the
# high-current SG260 (5-6 A row). b taken at the reflow maximum 2.0:
# chip(pad_l=(2.0 - 0.7)/2, pad_w=c, gap=a). Body 1.6 x 0.8 mm.
FB0603 = _fp("FB0603", "Ferrite bead 0603 (1608), Murata BLM18P/S/K reflow land",
             pad_l=0.65, pad_w=0.70, gap=0.70, body=(1.6, 0.8))


# ------------------------------------------------------------ LEDs
# Hubei KENTO "Specification for approval", Revision A.0, 2018-12-06, section 2
# "Package Profile & Soldering PAD Suggested", p.2. The drawing shows the part
# vertical with pad (2) at the top: the symbol beside it has its bar at (2) and
# "+" at (1), the top-view green corner mark and the bottom-view triangle are
# at the (2) end. So (1) = anode = pin 1, (2) = cathode = pin 2 (generic LED
# symbol); rotated here to pad 1 left, cathode bar beside pad 2.
# Drawing land dimensions: length along the part (pad_l), width across (pad_w),
# gap between lands.

# KT-0603R (red, LCSC C2286), body 1.6 x 0.8 x 0.6 mm:
#   https://datasheet.lcsc.com/datasheet/pdf/011ec3e8cb1e825f6961d29bc4db4c7a.pdf
# Lands 0.70 long, 0.70 gap. The land width is not dimensioned; the lands are
# drawn square (same size as the 0.70 dimension) -> 0.70.
LED0603 = _fp("LED0603", "LED 0603 (1608), KENTO KT-0603R land, pad 1 anode, pad 2 cathode",
              pad_l=0.70, pad_w=0.70, gap=0.70, body=(1.6, 0.8), marker="cathode")

# KT-0805G (green, LCSC C2297), body 2.0 x 1.25 x 0.85 mm:
#   https://datasheet.lcsc.com/datasheet/pdf/de342fde3322df0797012cd7a04e2194.pdf
# Lands 1.00 long x 1.40 wide, 0.90 gap.
LED0805 = _fp("LED0805", "LED 0805 (2012), KENTO KT-0805G land, pad 1 anode, pad 2 cathode",
              pad_l=1.00, pad_w=1.40, gap=0.90, body=(2.0, 1.25), marker="cathode")


# ------------------------------------------------------------ PTC fuse
# BHFUSE BSMD1206-110-6V (LCSC C2803344), BSMD1206 Series data sheet,
# "Revision 2025", "Physical Dimensions & Recommended Pad Layout (mm)", p.7/10
# (BSMD1206-110 row A 3.00~3.60, B 1.50~1.90 on p.8/10; nominal "3.2*1.6 mm" p.1):
#   https://datasheet.lcsc.com/datasheet/pdf/536516336d784fb8e1d4d3f7dabf668c.pdf
# Pads 1.00+-0.1 long x 1.80+-0.1 wide, 1.80+-0.1 between the inner edges
# -> chip(pad_l=1.00, pad_w=1.80, gap=1.80). Not polarized.
FUSE_BHFUSE_BSMD1206 = _fp("FUSE_BHFUSE_BSMD1206", "PTC resettable fuse 1206, BHFUSE BSMD1206 recommended pad layout",
                           pad_l=1.00, pad_w=1.80, gap=1.80, body=(3.2, 1.6))


FOOTPRINTS = [R0402, R0603, C0402, C0603, C0805, C1206, FB0402, FB0603, LED0603, LED0805,
              FUSE_BHFUSE_BSMD1206]
