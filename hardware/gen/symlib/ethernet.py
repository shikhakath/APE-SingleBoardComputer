"""Symbols for sheet 08 (Ethernet): DP83867IS PHY, 4-pad 25 MHz crystal, HR911130A MagJack."""
from schgen import box

# DP83867IS (also E/CS) RGZ VQFN-48 7x7, ti.com/lit/ds/symlink/dp83867e.pdf
# (SNLS504G), Figure 5-1 "RGZ Package 48-Pin VQFN Top View" and Table 5-1
# "Pin Functions", p.4-7. Die attach pad = GND, mapped as pin 49.
# Pin types: the 4-level strap pins (RX_D0/D2, RX_CTRL, GPIO_0/1, LED_0/1/2) are
# outputs after reset, so they are "io" here.
DP83867_RGZ = box("DP83867_RGZ", "DP83867IS/E/CS 10/100/1000 Ethernet PHY, RGMII/SGMII, VQFN-48 RGZ", [
    (29, "GTX_CLK", "in", "L"),
    (37, "TX_CTRL", "in", "L"),
    (28, "TX_D0/SGMII_SIN", "in", "L"),
    (27, "TX_D1/SGMII_SIP", "in", "L"),
    (26, "TX_D2", "in", "L"),
    (25, "TX_D3", "in", "L"),
    ("", "", "pas", "L"),
    (32, "RX_CLK", "out", "L"),
    (38, "RX_CTRL", "io", "L"),
    (33, "RX_D0/SGMII_COP", "io", "L"),
    (34, "RX_D1/SGMII_CON", "out", "L"),
    (35, "RX_D2/SGMII_SOP", "io", "L"),
    (36, "RX_D3/SGMII_SON", "out", "L"),
    ("", "", "pas", "L"),
    (16, "MDC", "in", "L"),
    (17, "MDIO", "io", "L"),
    (44, "INT/PWDN_N", "io", "L"),
    (43, "RESET_N", "in", "L"),
    ("", "", "pas", "L"),
    (15, "XI", "in", "L"),
    (14, "XO", "out", "L"),
    (18, "CLK_OUT", "out", "L"),
    (12, "RBIAS", "pas", "L"),
    ("", "", "pas", "L"),
    (20, "JTAG_CLK", "in", "L"),
    (22, "JTAG_TMS", "in", "L"),
    (23, "JTAG_TDI", "in", "L"),
    (21, "JTAG_TDO", "out", "L"),
    (1, "TD_P_A", "pas", "R"),
    (2, "TD_M_A", "pas", "R"),
    (4, "TD_P_B", "pas", "R"),
    (5, "TD_M_B", "pas", "R"),
    (7, "TD_P_C", "pas", "R"),
    (8, "TD_M_C", "pas", "R"),
    (10, "TD_P_D", "pas", "R"),
    (11, "TD_M_D", "pas", "R"),
    ("", "", "pas", "R"),
    (47, "LED_0", "io", "R"),
    (46, "LED_1", "io", "R"),
    (45, "LED_2", "io", "R"),
    (39, "GPIO_0", "io", "R"),
    (40, "GPIO_1", "io", "R"),
    ("", "", "pas", "R"),
    (19, "VDDIO", "pwr", "R"),
    (30, "VDDIO", "pwr", "R"),
    (41, "VDDIO", "pwr", "R"),
    (3, "VDDA2P5", "pwr", "R"),
    (9, "VDDA2P5", "pwr", "R"),
    (6, "VDD1P0", "pwr", "R"),
    (24, "VDD1P0", "pwr", "R"),
    (31, "VDD1P0", "pwr", "R"),
    (42, "VDD1P0", "pwr", "R"),
    (13, "VDDA1P8", "pwr", "R"),
    (48, "VDDA1P8", "pwr", "R"),
    (49, "GND (EP)", "pwr", "R"),
], footprint="VQFN48_RGZ_7X7")

# YXC X322525MOB4SI, 25 MHz, CL 12 pF, +/-10 ppm, 3.2x2.5 mm 4-pad crystal (LCSC C9006).
# YSX321SL series datasheet p.1 "Top View Crystal Connection": #1 and #3 are the
# crystal terminals, #2 and #4 are GND (lid):
#   https://datasheet.lcsc.com/datasheet/pdf/a84bd8d530dd46e4b0f6d0ee59d8a89c.pdf?productCode=C9006
XTAL4_3225 = box("XTAL4_3225", "Crystal, 3.2x2.5 mm, 4 pads (1/3 crystal, 2/4 case GND)", [
    (1, "X1", "pas", "L"), (2, "GND", "pas", "L"),
    (3, "X2", "pas", "R"), (4, "GND", "pas", "R"),
], prefix="Y", footprint="XTAL_3225_4P")

# HanRun HR911130A RJ45 with 1000BASE-T magnetics and LEDs (LCSC C54408),
# datasheet p.1 "Schematics" (pins P1-P10, LEDs 11-14) and p.2 "Mounting Pattern":
#   https://datasheet.lcsc.com/datasheet/pdf/d9b1e130e54a44fe9872ced55aa393e4.pdf?productCode=C54408
# P1 = common chip-side centre tap of all four 1CT:1CT transformers; P10 = cold end
# of the 1000 pF/2 kV Bob-Smith capacitor (4 x 75 Ohm on the line side).
# Green LED: anode 11, cathode 12. Yellow LED: anode 14, cathode 13.
# The two 1.63 mm plated shield tabs are unnumbered on the drawing: pins 15, 16.
# The two 3.25 mm holes are plastic posts (no pin).
HR911130A = box("HR911130A", "RJ45 MagJack, 1000BASE-T 1CT:1CT magnetics, green/yellow LEDs, shielded (HanRun HR911130A)", [
    (2, "MDI0+", "pas", "L"), (3, "MDI0-", "pas", "L"),
    (4, "MDI1+", "pas", "L"), (7, "MDI1-", "pas", "L"),
    (5, "MDI2+", "pas", "L"), (6, "MDI2-", "pas", "L"),
    (8, "MDI3+", "pas", "L"), (9, "MDI3-", "pas", "L"),
    ("", "", "pas", "L"),
    (1, "CT", "pas", "L"),
    (11, "LED_G_A", "pas", "R"), (12, "LED_G_K", "pas", "R"),
    (14, "LED_Y_A", "pas", "R"), (13, "LED_Y_K", "pas", "R"),
    ("", "", "pas", "R"),
    (10, "BS_CAP", "pas", "R"),
    (15, "SHIELD", "pas", "R"), (16, "SHIELD", "pas", "R"),
], prefix="J", footprint="RJ45_HANRUN_HR911130A")

SYMBOLS = [DP83867_RGZ, XTAL4_3225, HR911130A]
