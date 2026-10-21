"""Symbol definitions for lib/APE-SBC.SchLib.

Pin numbers and names come from each part's datasheet pin table; the source
is noted on every IC. Generic two-terminal symbols are horizontal with pin
ends at x = +/-200 mil.
"""
import csv
import re
from pathlib import Path

from schgen import Pin, Symbol, box, two_pin

# ------------------------------------------------------------ generic parts

RES = two_pin("RES", "Resistor", [
    "rectangle|1|1|0|-100|-35|100|35"], "R", body=100)
CAP = two_pin("CAP", "Capacitor, non-polarized", [
    "line|1|2|-30|-80|-30|80", "line|1|2|30|-80|30|80"], "C", body=30)
CAP_POL = two_pin("CAP_POL", "Capacitor, polarized (pin 1 = +)", [
    "line|1|2|-30|-80|-30|80", "arc|1|2|110|0|80|150|210", "label|1|-100|40|+"], "C", body=30)
IND = two_pin("IND", "Inductor", [
    "arc|1|1|-75|0|25|0|180", "arc|1|1|-25|0|25|0|180",
    "arc|1|1|25|0|25|0|180", "arc|1|1|75|0|25|0|180"], "L", body=100)
FB = two_pin("FERRITE", "Ferrite bead", [
    "rectangle|1|1|1|-60|-25|60|25"], "FB", body=60)
DIODE = two_pin("DIODE", "Diode (pin 1 = anode)", [
    "polygon|1|1|0|-40|-40|-40|40|40|0", "line|1|2|40|-40|40|40"], "D", ("A", "K"), body=40)
ZENER = two_pin("ZENER", "Zener diode (pin 1 = anode)", [
    "polygon|1|1|0|-40|-40|-40|40|40|0", "polyline|1|2|25|-50|40|-40|40|40|55|50"],
    "D", ("A", "K"), body=40)
TVS_BI = two_pin("TVS_BI", "Bidirectional TVS / ESD diode", [
    "polygon|1|1|0|-60|-40|-60|40|0|0", "polygon|1|1|0|60|-40|60|40|0|0",
    "polyline|1|2|-15|-50|0|-40|0|40|15|50"], "D", body=60)
LED = two_pin("LED", "LED (pin 1 = anode)", [
    "polygon|1|1|0|-40|-40|-40|40|40|0", "line|1|2|40|-40|40|40",
    "line|1|1|0|50|30|90", "line|1|1|30|50|60|90"], "LED", ("A", "K"), body=40)
XTAL2 = two_pin("XTAL2", "Crystal, 2-terminal", [
    "line|1|2|-50|-60|-50|60", "line|1|2|50|-60|50|60",
    "rectangle|1|1|0|-25|-50|25|50"], "Y", body=50)
TESTPOINT = Symbol("TESTPOINT", "Test point", [Pin("1", "TP", "pas", "L", 1, 60, -40, 0, 2)],
                   graphics=["ellipse|1|1|0|0|0|40|40"], designator_prefix="TP",
                   footprint="TP_PAD_1.0", show_names=False, show_numbers=False)
SW_PUSH = two_pin("SW_PUSH", "Push button, normally open", [
    "line|1|1|-100|0|-60|0", "line|1|1|60|0|100|0",
    "line|1|1|-60|0|60|50", "line|1|1|0|50|0|100", "line|1|1|-40|100|40|100"],
    "SW", body=100)

GENERIC = [RES, CAP, CAP_POL, IND, FB, DIODE, ZENER, TVS_BI, LED, XTAL2, TESTPOINT, SW_PUSH]

# ------------------------------------------------------------ PMIC
# TPS65219, datasheets/tps65219.pdf Table 5-1, p.4-6. RHB (5x5) and RSM (4x4,
# 0.4 mm) share one pin numbering; the BOM uses TPS6521904RSMR (RHB out of stock).
TPS65219 = box("TPS65219", "TPS65219 PMIC, 3 bucks + 4 LDOs, VQFN-32 RHB/RSM (NVM per OPN)", [
    (13, "VSYS", "pwr", "L"),
    (4, "PVIN_B1_1", "pwr", "L"),
    (5, "PVIN_B1_2", "pwr", "L"),
    (30, "PVIN_B2", "pwr", "L"),
    (26, "PVIN_B3", "pwr", "L"),
    (6, "PVIN_LDO1", "pwr", "L"),
    (20, "PVIN_LDO2", "pwr", "L"),
    (22, "PVIN_LDO34", "pwr", "L"),
    ("", "", "pas", "L"),
    (25, "EN/PB/VSENSE", "in", "L"),
    (28, "MODE/RESET", "in", "L"),
    (31, "MODE/STBY", "in", "L"),
    (12, "VSEL_SD/VSEL_DDR", "in", "L"),
    ("", "", "pas", "L"),
    (9, "SDA", "io", "L"),
    (10, "SCL", "in", "L"),
    ("", "", "pas", "L"),
    (14, "VDD1P8", "pas", "L"),
    (15, "AGND", "pwr", "L"),
    (33, "PGND", "pwr", "L"),
    (2, "LX_B1_1", "pas", "R"),
    (3, "LX_B1_2", "pas", "R"),
    (1, "FB_B1", "in", "R"),
    (29, "LX_B2", "pas", "R"),
    (32, "FB_B2", "in", "R"),
    (27, "LX_B3", "pas", "R"),
    (24, "FB_B3", "in", "R"),
    ("", "", "pas", "R"),
    (7, "VLDO1", "pas", "R"),
    (19, "VLDO2", "pas", "R"),
    (21, "VLDO3", "pas", "R"),
    (23, "VLDO4", "pas", "R"),
    ("", "", "pas", "R"),
    (8, "GPO1", "oc", "R"),
    (17, "GPO2", "oc", "R"),
    (16, "GPIO", "io", "R"),
    (11, "nINT", "oc", "R"),
    (18, "nRSTOUT", "oc", "R"),
], footprint="VQFN32_RSM_4X4")


# TPS22965 DSG (WSON-8 2x2), ti.com/lit/ds/symlink/tps22965.pdf, Pin Functions p.3.
# Thermal pad mapped as pin 9 (tie to GND).
TPS22965 = box("TPS22965_DSG", "TPS22965 5.7 V 4 A load switch with controlled rise time, WSON-8", [
    (1, "VIN", "pwr", "L"),
    (2, "VIN", "pwr", "L"),
    (4, "VBIAS", "pwr", "L"),
    (3, "ON", "in", "L"),
    (5, "GND", "pwr", "L"),
    (9, "EP", "pas", "L"),
    (7, "VOUT", "pas", "R"),
    (8, "VOUT", "pas", "R"),
    (6, "CT", "pas", "R"),
], footprint="WSON8_DSG_2X2")

# TLV755P DBV (SOT-23-5), ti.com/lit/ds/symlink/tlv755p.pdf, Table 4-1.
TLV755P = box("TLV755P_DBV", "TLV755P 500 mA LDO, SOT-23-5 (fixed output per OPN)", [
    (1, "IN", "pwr", "L"),
    (3, "EN", "in", "L"),
    (2, "GND", "pwr", "L"),
    (5, "OUT", "pas", "R"),
    (4, "NC", "pas", "R"),
], footprint="SOT23-5")

# ------------------------------------------------------------ shared logic / ESD
# Used by several sheets, so they live here rather than in a symlib module.
# SN74LVC1G08 DBV (SOT-23-5), ti.com/lit/ds/symlink/sn74lvc1g08.pdf Pin Functions.
SN74LVC1G08 = box("SN74LVC1G08_DBV", "Single 2-input AND gate, SOT-23-5", [
    (1, "A", "in", "L"), (2, "B", "in", "L"), (3, "GND", "pwr", "L"),
    (5, "VCC", "pwr", "R"), (4, "Y", "out", "R"),
], footprint="SOT23-5")
# SN74LVC1G11 DCK (SC70-6), ti.com/lit/ds/symlink/sn74lvc1g11.pdf Table 4-1.
SN74LVC1G11 = box("SN74LVC1G11_DCK", "Single 3-input AND gate, SC70-6", [
    (1, "A", "in", "L"), (3, "B", "in", "L"), (6, "C", "in", "L"), (2, "GND", "pwr", "L"),
    (5, "VCC", "pwr", "R"), (4, "Y", "out", "R"),
], footprint="SC70-6")
# SN74LVC2G17 DBV (SOT-23-6), ti.com/lit/ds/symlink/sn74lvc2g17.pdf Pin Functions.
SN74LVC2G17 = box("SN74LVC2G17_DBV", "Dual Schmitt-trigger buffer, SOT-23-6", [
    (1, "1A", "in", "L"), (3, "2A", "in", "L"), (2, "GND", "pwr", "L"),
    (5, "VCC", "pwr", "R"), (6, "1Y", "out", "R"), (4, "2Y", "out", "R"),
], footprint="SOT23-6")
# TPD4E05U06 DQA (USON-10), ti.com/lit/ds/symlink/tpd4e05u06.pdf Table 4-2.
# Four independent channels on pins 1/2/4/5; NC pins 6/7/9/10 are the
# straight-through routing pads (leave unconnected).
TPD4E05U06 = box("TPD4E05U06_DQA", "4-channel 0.5 pF ESD array, USON-10", [
    (1, "D1+", "pas", "L"), (2, "D1-", "pas", "L"), (4, "D2+", "pas", "L"), (5, "D2-", "pas", "L"),
    (3, "GND", "pwr", "R"), (8, "GND", "pwr", "R"),
    (6, "NC", "pas", "R"), (7, "NC", "pas", "R"), (9, "NC", "pas", "R"), (10, "NC", "pas", "R"),
], footprint="USON10_DQA")
MOUNTING_HOLE = Symbol("MOUNTING_HOLE", "Plated mounting hole (pin to GND)",
                       [Pin("1", "MH", "pas", "L", 1, 60, -40, 0, 2)],
                       graphics=["ellipse|1|1|0|0|0|40|40", "ellipse|1|1|0|0|0|20|20"],
                       designator_prefix="H", footprint="MH_M2.5_PLATED",
                       show_names=False, show_numbers=False)

SHARED = [SN74LVC1G08, SN74LVC1G11, SN74LVC2G17, TPD4E05U06, MOUNTING_HOLE]

# ------------------------------------------------------------ SiP
# OSD6254-1G-IPM, 500-ball 0.5 mm BGA. Ball map: data/osd6254_ballmap.csv,
# extracted from the Octavo OSD62x-PM datasheet Rev 2.0 (Tables 5-6/5-7 and
# the ball grid, cross-checked; 500 balls, 0 mismatches).
SIP_PARTS = [
    ("A", ["POWER"]),
    ("B", ["GND"]),
    ("C", ["NC/RSVD"]),
    ("D", ["MMC0", "MMC1", "MMC2"]),
    ("E", ["RGMII", "OSPI0"]),
    ("F", ["VOUT0/GPMC"]),
    ("G", ["CSI0", "USB", "OLDI0"]),
    ("H", ["MCU/WKUP", "SYSTEM/RESET/JTAG"]),
    ("I", ["I2C/UART/SPI/McASP"]),
]
_RESET_INPUTS = {"MCU_PORZ", "MCU_RESETZ", "RESET_REQZ", "TRSTN", "TCK", "TMS", "TDI"}


def _natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def _sip_symbol():
    path = Path(__file__).with_name("data") / "osd6254_ballmap.csv"
    with open(path, newline="", encoding="utf-8") as f:
        balls = list(csv.DictReader(f))
    pins = []
    for part_no, (_, groups) in enumerate(SIP_PARTS, start=1):
        members = [b for b in balls if b["group"] in groups]
        members.sort(key=lambda b: (groups.index(b["group"]), _natural(b["name"]), _natural(b["ball"])))
        half = (len(members) + 1) // 2
        for i, b in enumerate(members):
            kind = {"power": "pwr", "ground": "pwr", "nc": "pas", "reserved": "pas"}.get(b["type"], "io")
            if b["name"] in _RESET_INPUTS:
                kind = "in"
            pins.append((b["ball"], b["name"], kind, "L" if i < half else "R", part_no))
    covered = {p[0] for p in pins}
    if len(covered) != len(balls):
        raise ValueError("SiP symbol does not map every ball")
    return box("OSD6254-1G-IPM", "Octavo OSD6254 SiP: TI AM6254 + 1 GB DDR4, 9x14 mm 500-ball 0.5 mm BGA",
               pins, part_count=len(SIP_PARTS), footprint="OSD62X-PM_BGA500")


OSD6254 = _sip_symbol()

ALL = GENERIC + SHARED + [TPS65219, TPS22965, TLV755P, OSD6254]
