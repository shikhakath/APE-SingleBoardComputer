"""Symbols for sheet 07 (storage): eMMC-module connectors, microSD socket, SD dual load switch.

Pin numbers and names come from the sources noted above each symbol, never
from memory. The shared ESD array (TPD4E05U06) lives in symbols.py.
"""
from schgen import box

# ---------------------------------------------------------------- eMMC module
# LS Mtron GB042-34P-H10(-E3000), 34-pin 0.4 mm board-to-board PLUG (host side;
# the module carries the GB042-34S-H10 socket). The LS Mtron drawing itself could
# not be obtained (LS no longer hosts it; broker/aggregator copies are behind a
# Cloudflare check or 404). Pin numbering is therefore taken from three published
# sources that agree pin for pin:
#   * Radxa eMMC module product brief RAD-DOC-0126 rev 1.1, section 5 "Pinout"
#     https://dl.radxa.com/accessories/emmc-module/rad-doc-0126_radxa_emmc_module_product_brief__revision_1.1_g69c4d5d.pdf
#   * Radxa ROCK 3A v1.31 schematic p.17 "eMMC Flash", J5 (GB042-34P + 30P merged as pins 35-64)
#     https://dl.radxa.com/rock3/docs/hw/3a/radxa_rock_3a_v1310_schematic.pdf
#   * PINE64 ROCK64 v2.0 schematic p.14 "EMMC SOCKET", J7101 footprint CFPC031035
#     http://files.pine64.org/doc/rock64/ROCK64_Schematic_v2.0_20171019.pdf
# Pins 35-38 are the four metal hold-down pads of the ROCK64 footprint (tied to
# GND there); the GB042 series lists a "locking structure for the hold down".
# Confirm the hold-down pad count against a sample before the footprint is drawn.
# Pin 12: eMMC RST_n on Hardkernel/PINE64 modules, labelled "VCC 1V8" in the Radxa
# brief. Pin 13: GND on the module (Odroid uses it as module detect CDN).
# Pin 15: eMMC data strobe (HS400 only).
GB042_34P = box("GB042-34P-H10", "eMMC-module connector, LS Mtron GB042 34-pin 0.4 mm B2B plug (Odroid/Radxa/PINE64 pinout)", [
    (6, "D0", "io", "L"), (29, "D1", "io", "L"), (27, "D2", "io", "L"), (10, "D3", "io", "L"),
    (4, "D4", "io", "L"), (2, "D5", "io", "L"), (33, "D6", "io", "L"), (31, "D7", "io", "L"),
    (25, "CMD", "io", "L"), (8, "CLK", "in", "L"), (12, "RST_N", "in", "L"), (15, "DS", "out", "L"),
    ("", "", "pas", "L"),
    (20, "VCCQ", "pwr", "L"), (21, "VCCQ", "pwr", "L"), (22, "VCC", "pwr", "L"), (23, "VCC", "pwr", "L"),
    (1, "GND", "pwr", "R"), (3, "GND", "pwr", "R"), (5, "GND", "pwr", "R"), (7, "GND", "pwr", "R"),
    (9, "GND", "pwr", "R"), (11, "GND", "pwr", "R"), (13, "CDN/GND", "pas", "R"), (14, "GND", "pwr", "R"),
    (16, "GND", "pwr", "R"), (17, "GND", "pwr", "R"), (18, "GND", "pwr", "R"), (19, "GND", "pwr", "R"),
    (24, "GND", "pwr", "R"), (26, "GND", "pwr", "R"), (28, "GND", "pwr", "R"), (30, "GND", "pwr", "R"),
    (32, "GND", "pwr", "R"), (34, "GND", "pwr", "R"),
    (35, "HD1", "pas", "R"), (36, "HD2", "pas", "R"), (37, "HD3", "pas", "R"), (38, "HD4", "pas", "R"),
], prefix="J", footprint="B2B_LSM_GB042-34P-H10")

# LS Mtron GB042-30P-H10(-E3000), 30-pin plug, mechanical retention only for Radxa
# dual-connector modules (no signals: Radxa brief RAD-DOC-0126 rev 1.1 section 4;
# ROCK 3A v1.31 p.17 ties all 30 contacts, J5 pins 35-64, to GND). Same source
# caveat as above: pins 31-34 are the hold-down pads by analogy with the 34-pin
# part; verify on a sample.
GB042_30P = box("GB042-30P-H10", "eMMC-module retention connector, LS Mtron GB042 30-pin 0.4 mm B2B plug (mechanical, all GND)",
                [(n, "GND", "pas", "L") for n in range(1, 16)] + [(31, "HD1", "pas", "L"), (32, "HD2", "pas", "L")]
                + [(n, "GND", "pas", "R") for n in range(16, 31)] + [(33, "HD3", "pas", "R"), (34, "HD4", "pas", "R")],
                prefix="J", footprint="B2B_LSM_GB042-30P-H10")

# ---------------------------------------------------------------- microSD
# Korean Hroparts Elec TF-01A push-push microSD socket (LCSC C91145), drawing
# "TF-01A" rev A 2014-09-29, PCB layout (pattern side):
#   https://datasheet.lcsc.com/datasheet/pdf/7650eac21a54674b08ad4ba21e17fceb.pdf?productCode=C91145
# Nine 0.70 mm contact pads numbered 1-8 plus "Cd"; contact functions are the
# microSD standard for pads 1-8 (1 DAT2, 2 CD/DAT3, 3 CMD, 4 VDD, 5 CLK, 6 VSS,
# 7 DAT0, 8 DAT1). "Cd" (mapped as pin 9) is the card-detect spring, which closes
# to the grounded shell when a card is inserted. The four shell tabs (2x 2.00 mm,
# 2x 1.40 mm) are unnumbered on the drawing and mapped as pins 10-13. The two
# 1.00 mm holes are non-plated locating holes (no pin).
TF_01A = box("TF-01A", "microSD push-push socket with card-detect switch (Hroparts TF-01A)", [
    (7, "DAT0", "io", "L"), (8, "DAT1", "io", "L"), (1, "DAT2", "io", "L"), (2, "CD/DAT3", "io", "L"),
    (3, "CMD", "io", "L"), (5, "CLK", "in", "L"), (9, "CD", "pas", "L"),
    (4, "VDD", "pwr", "R"), (6, "VSS", "pwr", "R"),
    (10, "SHELL", "pas", "R"), (11, "SHELL", "pas", "R"), (12, "SHELL", "pas", "R"), (13, "SHELL", "pas", "R"),
], prefix="J", footprint="MICROSD_HRO_TF-01A")

# TPS22996 DRL (SOT-583-8), ti.com/lit/ds/symlink/tps22996.pdf (SLVSH99A),
# Figure 5-1 and Pin Functions table p.3. No exposed pad.
TPS22996 = box("TPS22996_DRL", "TPS22996 dual 4 A load switch with QOD and ON-current set rise time, SOT-583-8", [
    (2, "VIN1", "pwr", "L"), (3, "VIN2", "pwr", "L"), (8, "VBIAS", "pwr", "L"),
    (1, "ON1", "in", "L"), (4, "ON2", "in", "L"), (5, "GND", "pwr", "L"),
    (7, "VOUT1", "pas", "R"), (6, "VOUT2", "pas", "R"),
], footprint="SOT583-8_DRL")

SYMBOLS = [GB042_34P, GB042_30P, TF_01A, TPS22996]
