"""Large quad ICs: TFP410 (HTQFP-64), TLV320AIC3104 (VQFN-32), DP83867 (VQFN-48),
FT4232HL (LQFP-64) and CH335F (QFN-28 4x4).

All five are quads numbered counter-clockwise in the top view. The TFP410 package
outline and the WCH drawing put pin 1 at the left end of the bottom row; the TI
land patterns and the FTDI drawing already show it at the top of the left side.
Every footprint here is in IPC-7351 zero orientation: pin 1 at the top of the left side, ``quad()``
numbering (left side top to bottom, bottom row left to right, right side bottom
to top, top row right to left). Exposed pads take the symbol's pin number.

Lands without a manufacturer pattern (FT4232HL, CH335F) are derived with
IPC-7351B, density level B (nominal), from the package tolerances:
    Zmax = Lmin + 2*JT + sqrt(CL^2 + F^2 + P^2)
    Gmin = Smax' - 2*JH - sqrt(CS'^2 + F^2 + P^2)
    Xmax = Wmin + 2*JS + sqrt(CW^2 + F^2 + P^2)
with L = lead span (toe to toe), T = foot / terminal length, W = lead width,
C* = max - min, S = L - 2T taken as the RMS-corrected inner span (CS' =
sqrt(CL^2 + 2*CT^2), Smax' = Smax - (CS - CS')/2), F = 0.05 (board fabrication),
P = 0.025 (placement), results rounded outward to the 0.05 mm round-off factor
(Z up, G down, X up). Pad length = (Z - G)/2, pad-centre span = (Z + G)/2.
"""
import math

from footprints import Footprint, quad, smd, window_grid

_F, _P = 0.05, 0.025


def _ipc7351b(lmin, lmax, tmin, tmax, wmin, wmax, jt, jh, js, step=0.05):
    """IPC-7351B (Z, G, X) for a two-sided lead row; see the module docstring."""
    cl, ct, cw = lmax - lmin, tmax - tmin, wmax - wmin
    smin, smax = lmin - 2 * tmax, lmax - 2 * tmin
    cs = smax - smin
    cs_rms = math.sqrt(cl ** 2 + 2 * ct ** 2)
    smax_rms = smax - (cs - cs_rms) / 2
    fp2 = _F ** 2 + _P ** 2
    z = lmin + 2 * jt + math.sqrt(cl ** 2 + fp2)
    g = smax_rms - 2 * jh - math.sqrt(cs_rms ** 2 + fp2)
    x = wmin + 2 * js + math.sqrt(cw ** 2 + fp2)
    up = lambda v: math.ceil(round(v / step, 6)) * step
    down = lambda v: math.floor(round(v / step, 6)) * step
    return round(up(z), 4), round(down(g), 4), round(up(x), 4)


def _span_len(z, g):
    """(pad-centre span, pad length) from Z and G."""
    return round((z + g) / 2, 4), round((z - g) / 2, 4)


# ------------------------------------------------------------------ TFP410
# TI TFP410PAP(R), HTQFP-64 PowerPAD, package PAP (S-PQFP-G64), 10 x 10 mm body,
# 0.5 mm pitch. https://www.ti.com/lit/ds/symlink/tfp410.pdf (SLDS145D, Feb 2024):
#   PDF p.41 "MECHANICAL DATA PAP (S-PQFP-G64)" 4147702/C 08/03: body 9.80-10.20 SQ,
#     lead span 11.80-12.20 SQ, b 0.17-0.27, L 0.45-0.75, e 0.50.
#   PDF p.42 "THERMAL PAD MECHANICAL DATA" 4206326-3/P 05/14: exposed thermal pad
#     4.30-5.00 square (tie-strap stubs 0.23 at the corners may not be present).
#   PDF p.43 "LAND PATTERN DATA" 4208775-4/G 03/16, Example Board Layout: lands
#     64 x 1.5 x 0.3 at 0.5 pitch; 11.4 = pad-centre span (the extension lines sit
#     on the pad centre lines), so pad centres at +-5.70, lands 4.95..6.45 from the
#     centre. The drawing already shows pin 1 at the top of the left column.
#     (This old-style page is not to scale for the span: its vectors measure 11.2
#     at the 8.0 / 5.0 / 0.5 scale. TI's current PAP0064G layout, ads1278.pdf
#     SBAS367 p.50, same lead frame, gives 64X (1.5) x (0.3) and (11.4) between pad
#     centres, so 11.4 stands.)
#     Thermal land: 8.0 x 8.0 copper covered by solder mask except a 5.0 x 5.0
#     solder-mask-defined opening, 36 x d0.2 vias on a 6 x 6 grid at 1.3 pitch.
#   Stencil (same page, "Stencil Openings ... 0.125 mm"): leads 1.5 x 0.3 (= land);
#     centre pad 5.00 x 5.00 at 0.127 mm (table: 0.1 mm 5.59, 0.152 mm 4.56,
#     0.178 mm 4.23).
# Pad 65 is the 5.0 x 5.0 solder-mask-defined opening: the tool has no per-pad
# mask, and an 8.0 mm pad with the board's +0.05 mask rule would expose copper
# 0.95 mm from the leads. Layout: put an 8.0 x 8.0 GND polygon under pad 65 (it
# is covered by mask) and the 36 vias (6 x 6, 1.3 mm pitch, d0.2, plugged/capped).
# Paste: the board rule (0 expansion) gives 5.00 x 5.00 = TI's single opening for a
# 0.127 mm stencil, so no Top Paste windows; JLCPCB's 0.10-0.12 mm stencil sits
# between the 5.00 and 5.59 rows, 5.00 is the conservative end.
HTQFP64_PAP = Footprint(
    "HTQFP64_PAP_10X10",
    "TI HTQFP-64 PowerPAD (PAP), 10x10 mm, 0.5 mm pitch, 5.0 mm exposed pad (TFP410)",
    quad(16, 16, 0.5, 11.4, 11.4, 1.5, 0.3)
    + [smd("65", 0, 0, 5.0, 5.0, "rect")],
    body=(10.0, 10.0))

# ------------------------------------------------------------------ TLV320AIC3104
# TI TLV320AIC3104IRHBR, VQFN-32, package RHB0032E, 5 x 5 mm, 0.5 mm pitch.
# https://www.ti.com/lit/ds/symlink/tlv320aic3104.pdf (SLAS510G, Feb 2021):
#   PDF p.100 "PACKAGE OUTLINE" RHB0032E 4223442/B 08/2019: body 4.9-5.1, exposed
#     thermal pad 3.45 +-0.1, pins 1-8 left, 9-16 bottom, 17-24 right, 25-32 top.
#   PDF p.101 "EXAMPLE BOARD LAYOUT": 32X (0.6) x (0.25) lands, 28X (0.5) pitch,
#     (4.8) pad-centre span both ways, thermal land (3.45) square = pin 33; optional
#     d0.2 vias at the centre and +-1.475 on both axes (layout item, not in here).
#   PDF p.102 "EXAMPLE STENCIL DESIGN" (0.125 mm stencil): pad 33 split into
#     4X (1.49) squares centred at (+-0.845, +-0.845) -> pitch 1.69, 0.20 webs;
#     75 % coverage (4 x 1.49^2 / 3.45^2 = 74.6 %). Lead apertures = land.
VQFN32_RHB = Footprint(
    "VQFN32_RHB_5X5",
    "TI VQFN-32 (RHB0032E), 5x5 mm, 0.5 mm pitch, 3.45 mm thermal pad (TLV320AIC3104)",
    quad(8, 8, 0.5, 4.8, 4.8, 0.6, 0.25)
    + [smd("33", 0, 0, 3.45, 3.45, "rect")],
    body=(5.0, 5.0),
    paste=window_grid(0, 0, 1.49, 1.49, 1.69, 1.69, 2, 2))

# ------------------------------------------------------------------ DP83867
# TI DP83867IS/E/CS (and IR/CR) RGZ, VQFN-48, package RGZ0048B, 7 x 7 mm, 0.5 mm pitch.
# https://www.ti.com/lit/ds/symlink/dp83867e.pdf (SNLS504G, rev. June 2026):
#   PDF p.126 "PACKAGE OUTLINE" RGZ0048B 4218795/B 02/2017: body 6.85-7.15,
#     exposed thermal pad 4.1 +-0.1, pins 1-12 left, 13-24 bottom, 25-36 right,
#     37-48 top.
#   PDF p.127 "EXAMPLE BOARD LAYOUT": 48X (0.6) x (0.24) lands, 44X (0.5) pitch,
#     (6.8) pad-centre span, thermal land (4.1) square = pin 49; optional d0.2 vias
#     on a 1.115 / 0.685 grid (layout item, not in here).
#   PDF p.128 "EXAMPLE STENCIL DESIGN" (0.125 mm stencil): pad 49 split into
#     9X (1.17) squares on a (1.37) pitch, 3 x 3 centred -> 0.20 webs; 73 %
#     coverage (9 x 1.17^2 / 4.1^2 = 73.3 %). Lead apertures = land.
# Same drawings in dp83867ir.pdf (SNLS484J) PDF p.135-137.
VQFN48_RGZ = Footprint(
    "VQFN48_RGZ_7X7",
    "TI VQFN-48 (RGZ0048B), 7x7 mm, 0.5 mm pitch, 4.1 mm thermal pad (DP83867)",
    quad(12, 12, 0.5, 6.8, 6.8, 0.6, 0.24)
    + [smd("49", 0, 0, 4.1, 4.1, "rect")],
    body=(7.0, 7.0),
    paste=window_grid(0, 0, 1.17, 1.17, 1.37, 1.37, 3, 3))

# ------------------------------------------------------------------ FT4232HL
# FTDI FT4232HL, LQFP-64, 10 x 10 mm body, 0.5 mm pitch, no exposed pad.
# FTDI DS_FT4232H Version 2.6 (FT_000060), section 8.2 "FT4232HL, LQFP-64 Package
# Dimensions", Figure 8.2 p.37 (JEDEC MS-026 BCD); copy from
# https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_FTDI-FT4232HL-Reel_C56742.pdf
# Top view: pin 1 top of the left side, 16 bottom left, 17-32 bottom, 33-48 right,
# 49-64 top (quad() order as drawn).
# FTDI gives no land pattern: DERIVED per IPC-7351B nominal (level B), gull wing
# <= 0.625 mm pitch (JT 0.35, JH 0.35, JS -0.02), from
#   L = D/E 11.75-12.25, T = L 0.45-0.75, W = b 0.17-0.27:
#   Smin 10.25, Smax 11.35, CS' = sqrt(0.5^2 + 2*0.3^2) = 0.656, Smax' = 11.128
#   Z = 11.75 + 0.70 + 0.503 = 12.953 -> 13.00
#   G = 11.128 - 0.70 - 0.658 = 9.770 -> 9.75
#   X = 0.17 - 0.04 + 0.115 = 0.245 -> 0.25
#   -> lands 1.625 x 0.25 at an 11.375 pad-centre span.
# (TI's land for the same-size PAP lead frame above is 1.5 x 0.3 at 11.4.)
_LQ_Z, _LQ_G, _LQ_X = _ipc7351b(11.75, 12.25, 0.45, 0.75, 0.17, 0.27, 0.35, 0.35, -0.02)
_LQ_SPAN, _LQ_LEN = _span_len(_LQ_Z, _LQ_G)
LQFP64 = Footprint(
    "LQFP64_10X10_P0.5",
    "LQFP-64, 10x10 mm, 0.5 mm pitch, IPC-7351B nominal lands (FT4232HL)",
    quad(16, 16, 0.5, _LQ_SPAN, _LQ_SPAN, _LQ_LEN, _LQ_X),
    body=(10.0, 10.0))

# ------------------------------------------------------------------ CH335F
# WCH CH335F, QFN-28 4 x 4 mm, 0.4 mm pitch ("QFN28_4x4x0.75-0.4").
# WCH CH334/CH335 datasheet V2.91 (Chinese), LCSC C5137013:
# https://datasheet.lcsc.com/datasheet/pdf/77721fceaa29165ba79c58173b46c67f.pdf?productCode=C5137013
#   p.23 section 5.6 "QFN28_4x4x0.75-0.4" (image drawing): body 4.0 +-0.1, lead
#     width 0.2 +-0.05, terminal length 0.35 +-0.1, pitch 0.4, exposed pad
#     2.7 +-0.2 (pin-1 corner chamfered). Top view: #1 left end of the bottom row,
#     #8 bottom of the right side, #28 bottom of the left side = counter-clockwise,
#     same as Figure 1-1 p.2 (CH335F); turned 90 deg clockwise here so pin 1 is at
#     the top of the left side. Exposed pad = datasheet "pin 0" = symbol pin 29.
# WCH gives no land pattern: DERIVED per IPC-7351B nominal (level B), QFN
# (JT 0.30, JH 0.00, JS -0.04), from L = body 3.9-4.1, T 0.25-0.45, W 0.15-0.25:
#   Smin 3.0, Smax 3.6, CS' = sqrt(0.2^2 + 2*0.2^2) = 0.346, Smax' = 3.473
#   Z = 3.9 + 0.60 + 0.208 = 4.708 -> 4.75
#   G = 3.473 - 0 - 0.351 = 3.122 -> 3.10
#   X = 0.15 - 0.08 + 0.115 = 0.185 -> 0.20
#   -> lands 0.825 x 0.20 at a 3.925 pad-centre span (0.20 mm between lands).
# Thermal land = nominal exposed pad 2.7 x 2.7 (0.20 mm to the lead lands).
# Paste: WCH gives no stencil. 100 % paste on a 2.7 mm pad next to 0.4 mm-pitch
# leads risks float and bridging, so pad 29 is printed through 4X 1.17 square
# windows on a 1.37 pitch (0.20 webs, 0.08 inset), 75 % coverage, as TI does for
# the same-size RSM0032B (4X 1.23 on a 2.8 pad, 77 %) and RHB0032E (75 %). Leads 1:1.
# The EasyEDA/LCSC footprint for C5137013 could not be used as a cross-check
# (the API returned HTTP 403).
_QF_Z, _QF_G, _QF_X = _ipc7351b(3.9, 4.1, 0.25, 0.45, 0.15, 0.25, 0.30, 0.0, -0.04)
_QF_SPAN, _QF_LEN = _span_len(_QF_Z, _QF_G)
QFN28_4X4 = Footprint(
    "QFN28_4X4_P0.4",
    "QFN-28 4x4 mm, 0.4 mm pitch, 2.7 mm exposed pad, IPC-7351B nominal lands (WCH CH335F)",
    quad(7, 7, 0.4, _QF_SPAN, _QF_SPAN, _QF_LEN, _QF_X)
    + [smd("29", 0, 0, 2.7, 2.7, "rect")],
    body=(4.0, 4.0),
    paste=window_grid(0, 0, 1.17, 1.17, 1.37, 1.37, 2, 2))

FOOTPRINTS = [HTQFP64_PAP, VQFN32_RHB, VQFN48_RGZ, LQFP64, QFN28_4X4]
