"""Symbols for sheet 06 (clocks, reset, boot).

Every pin table below was read from the downloaded datasheet (scratch copy),
not from memory. The 32.768 kHz crystal (Epson FC-135, 2 pads #1/#2, LCSC
C99010 datasheet p.1), the button ESD diode TPD1E10B06 (DPY, 2 pins, TI
SLLSEB1G Table 4-1) and the passives use the generic symbols in symbols.py.
"""
from schgen import box

# ECS-2520MV MultiVolt HCMOS oscillator, 2.5 x 2.0 mm, 4 pads.
# https://ecsxtal.com/store/pdf/ECS-2520MV.pdf  p.1 "PAD CONNECTIONS":
#   1 Tri-state, 2 Gnd, 3 Output, 4 Vdd.  Tri-state: pin 1 >= 0.7*Vdd or NC
#   = output active, <= 0.3*Vdd = high impedance.
ECS2520MV = box("ECS-2520MV", "25 MHz HCMOS oscillator 1.6-3.6 V, 2.5x2.0 mm SMD-4", [
    (4, "VDD", "pwr", "L"),
    (1, "OE/TRI", "in", "L"),
    (2, "GND", "pwr", "L"),
    (3, "OUT", "out", "R"),
], footprint="OSC_2520_4P")

# SHOU HAN 2.54-4P TPGT, 4-position SPST slide DIP switch, SMD gull wing.
# https://www.lcsc.com/datasheet/C6331176.pdf  (drawing DSP-DSICXXLS-AP, p.1:
# schematic + P.C.B layout). The drawing numbers the positions 1..4 only; the
# pads follow the standard DIP numbering (1-4 along the "ON"/numbered edge,
# 5-8 back along the opposite edge), so position k connects pads k and 9-k.
# The Altium footprint must use the same pad numbers.
DIPSW4 = box("DIPSW4_SMD", "DIP switch 4-position SPST, 2.54 mm SMD (pos k = pins k / 9-k)", [
    (1, "SW1A", "pas", "L"),
    (2, "SW2A", "pas", "L"),
    (3, "SW3A", "pas", "L"),
    (4, "SW4A", "pas", "L"),
    (8, "SW1B", "pas", "R"),
    (7, "SW2B", "pas", "R"),
    (6, "SW3B", "pas", "R"),
    (5, "SW4B", "pas", "R"),
], prefix="SW", footprint="SW_DIP4_SMD_2.54")

# XKB TS-1187A-B-A-B tactile switch, 5.1 x 5.1 mm, 4 SMD terminals.
# https://www.lcsc.com/datasheet/C318884.pdf  (drawing TS-1187A-X-X-X, p.1):
# terminals A-B are one contact (tied internally), C-D the other; the switch
# closes A/B to C/D. Pad numbers 1-4 = A, B, C, D (footprint must match).
TS1187A = box("TS-1187A", "Tactile switch SPST-NO 5.1x5.1 mm, 4 terminals (A=B, C=D)", [
    (1, "A", "pas", "L"),
    (2, "B", "pas", "L"),
    (3, "C", "pas", "R"),
    (4, "D", "pas", "R"),
], prefix="SW", footprint="SW_TACT_5.1X5.1_SMD4")

SYMBOLS = [ECS2520MV, DIPSW4, TS1187A]
