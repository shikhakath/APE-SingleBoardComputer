"""Symbols for sheet 16 (board ID EEPROM, temperature sensor).

Pin tables read from the downloaded datasheets. LEDs, resistors and
mounting holes use the generic/shared symbols in symbols.py.
"""
from schgen import box

# Microchip (Atmel) AT24C512C-SSHD-T, 512 Kbit I2C EEPROM, 8-lead JEDEC SOIC.
# https://www.lcsc.com/datasheet/C12371.pdf  (Atmel doc 8720C, Section 1,
# Figure 1 "Pin Configurations", p.2): 1 A0, 2 A1, 3 A2, 4 GND, 5 SDA, 6 SCL,
# 7 WP, 8 VCC. Device address 1010 A2 A1 A0 (Section 7). A0-A2 and WP have
# weak internal pull-downs; the datasheet recommends tying them to a known level.
# Ordering code -SSHD-T = 2.5-5.5 V version, package 8S1 (0.150" JEDEC SOIC),
# Section 12 p.14 - fine on VCC_3V3_SYS.
AT24C512C = box("AT24C512C_SOIC8", "512 Kbit I2C EEPROM, SOIC-8 (SSHD: 2.5-5.5 V)", [
    (8, "VCC", "pwr", "L"),
    (1, "A0", "in", "L"),
    (2, "A1", "in", "L"),
    (3, "A2", "in", "L"),
    (7, "WP", "in", "L"),
    (4, "GND", "pwr", "L"),
    (5, "SDA", "io", "R"),
    (6, "SCL", "in", "R"),
], footprint="SOIC8_150MIL")

# TI TMP102AIDRLR, I2C temperature sensor, SOT-563 (DRL).
# https://www.ti.com/lit/ds/symlink/tmp102.pdf  (SBOS397I) Section 4 Pin
# Functions, p.3: 1 SCL, 2 GND, 3 ALERT (open drain), 4 ADD0, 5 V+, 6 SDA.
# Address (Table 6-4): ADD0 = GND -> 1001000 (0x48).
TMP102 = box("TMP102_DRL", "TMP102 digital temperature sensor, I2C, SOT-563", [
    (5, "V+", "pwr", "L"),
    (4, "ADD0", "in", "L"),
    (2, "GND", "pwr", "L"),
    (6, "SDA", "io", "R"),
    (1, "SCL", "in", "R"),
    (3, "ALERT", "oc", "R"),
], footprint="SOT563_DRL")

SYMBOLS = [AT24C512C, TMP102]
