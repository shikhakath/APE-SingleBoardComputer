"""Sheet 16 - board-ID EEPROM, temperature sensor, I2C0 pull-ups, LEDs, mounting holes.

References:
  * TI SK-AM62B-P1 PROC142B p.23 (AT24C512C board ID at 0x51 on I2C0: A0 10k
    pull-up, A1/A2 low, WP 10k pull-down, 0.1 uF; TMP100 with 0.01 uF),
    p.44 D-note (I2C0/I2C1 are emulated open drain: 47R series at the SoC)
  * AT24C512C (Atmel 8720C) Section 4: A0-A2/WP to a known level, pull-ups <= 10k
  * TMP102 SBOS397I Table 6-4 (ADD0 = GND -> 0x48), 7.3 (0.01 uF bypass),
    Pin Functions (ALERT is open drain and needs a pull-up)
  * AM625 SPRSP58C 6.8.6: 3.3 V LVCMOS IOH 9 mA @ VOH 2.4 V, IOL 5 mA @ 0.4 V,
    so the GPIOs source the ~1.5-2 mA LED currents directly
  * LED datasheets (LCSC C2297 KT-0805G: VF 2.6-3.1 V @ 5 mA; C2286 KT-0603R:
    VF 1.8-2.4 V @ 20 mA)

I2C0 devices: TPS25730 0x20/0x21 (01), TPS65219 0x30 (02), TMP102 0x48, AT24C512C 0x51.
"""
from schgen import Sheet
from symbols import CAP, LED, MOUNTING_HOLE, RES, TESTPOINT
from symlib.misc import AT24C512C, TMP102

R10K = "10k 1% 0402"
DNP = {"DNP": "1"}
LED_G = {"MPN": "KT-0805G", "Manufacturer": "Hubei KENTO"}
LED_R = {"MPN": "KT-0603R", "Manufacturer": "Hubei KENTO"}


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/16_Misc.SchDoc", "Board ID, sensors, LEDs, mounting", style=7)

    # ---- board-ID EEPROM, I2C0 address 0x51 (1010 A2 A1 A0 = 1010 001) -------
    sh.add("U1600", AT24C512C, 2000, 15800, {
        "8": "VCC_3V3_SYS", "1": "EEPROM_A0", "2": "GND", "3": "GND", "7": "EEPROM_WP",
        "4": "GND", "5": "I2C0_SDA", "6": "I2C0_SCL",
    }, comment="AT24C512C-SSHD-T", MPN="AT24C512C-SSHD-T", Manufacturer="Microchip")
    sh.column(6200, 15700, [
        ("C1600", CAP, "VCC_3V3_SYS", "GND", "100nF 16V X7R 0402 (U1600 VCC)"),
        ("R1600", RES, "VCC_3V3_SYS", "EEPROM_A0", R10K + " (A0 = 1 -> 0x51)"),
        ("R1601", RES, "EEPROM_A0", "GND", R10K + " DNP (fit instead of R1600 for 0x50)", DNP),
        ("R1602", RES, "EEPROM_WP", "GND", R10K + " (WP low = writable, as SK)"),
        ("R1603", RES, "VCC_3V3_SYS", "EEPROM_WP", R10K + " DNP (write-protect after programming)", DNP),
    ])
    sh.note(1000, 16500, "Board ID EEPROM at 0x51 (TI SK board-detect address; Octavo BRK uses 0x50 - R1600/R1601 option).")

    # ---- TMP102 at 0x48, close to the SiP --------------------------------------
    sh.add("U1601", TMP102, 2000, 12300, {
        "5": "VCC_3V3_SYS", "4": "GND", "2": "GND",
        "6": "I2C0_SDA", "1": "I2C0_SCL", "3": "TMP102_ALERT_N",
    }, comment="TMP102AIDRLR", MPN="TMP102AIDRLR", Manufacturer="Texas Instruments")
    sh.column(6200, 12200, [
        ("C1601", CAP, "VCC_3V3_SYS", "GND", "10nF 50V X7R 0402 (U1601 V+, DS 7.3)"),
        ("R1604", RES, "VCC_3V3_SYS", "TMP102_ALERT_N", R10K + " (ALERT open drain)"),
    ])
    sh.add("TP1600", TESTPOINT, 9200, 11800, {"1": "TMP102_ALERT_N"}, comment="TMP102 ALERT")
    sh.note(1000, 12900, "TMP102: place next to the SiP, away from the PMIC inductors. ALERT to a test point only (no SoC pin allocated).")

    # ---- I2C0 pull-ups (one set for the whole bus) -----------------------------
    sh.column(12500, 15700, [
        ("R1605", RES, "VCC_3V3_SYS", "I2C0_SCL", "2.2k 1% 0402 (I2C0 SCL pull-up)"),
        ("R1606", RES, "VCC_3V3_SYS", "I2C0_SDA", "2.2k 1% 0402 (I2C0 SDA pull-up)"),
    ])
    sh.add("TP1601", TESTPOINT, 15800, 15600, {"1": "I2C0_SCL"}, comment="I2C0_SCL")
    sh.add("TP1602", TESTPOINT, 15800, 15200, {"1": "I2C0_SDA"}, comment="I2C0_SDA")
    sh.note(11000, 16500, "I2C0 pull-ups: the only ones on this bus (PMIC 0x30, PD 0x20/21, TMP102 0x48, EEPROM 0x51).")
    sh.note(11000, 16300, "SK 47R series at the SoC ball is NOT placed: the contract names both ends I2C0_SCL/SDA (open item).")

    # ---- LEDs: active-high GPIOs source the current through the resistor ------
    sh.column(12500, 12600, [
        ("R1607", RES, "VCC_3V3_SYS", "LED_PWR_A", "330R 1% 0402 (power LED)"),
        ("R1608", RES, "USER_LED1", "LED_USR1_A", "330R 1% 0402 (heartbeat, ~1.5 mA)"),
        ("R1609", RES, "USER_LED2", "LED_USR2_A", "1k 1% 0402 (user 2, ~1.3 mA)"),
        ("R1610", RES, "VCC_5V0", "LED_5V_A", "1k 1% 0402 (5 V present, ~3 mA)"),
    ])
    sh.column(16300, 12600, [
        ("LED1600", LED, "LED_PWR_A", "GND", "KT-0805G green (3V3)", LED_G),
        ("LED1601", LED, "LED_USR1_A", "GND", "KT-0805G green (USER_LED1 heartbeat)", LED_G),
        ("LED1602", LED, "LED_USR2_A", "GND", "KT-0603R red (USER_LED2)", LED_R),
        ("LED1603", LED, "LED_5V_A", "GND", "KT-0603R red (VCC_5V0)", LED_R),
    ])
    sh.note(11000, 13300, "USER_LED1/2 = MCU_GPIO0_0/1 (3.3 V, VDDSHV_MCU), active high; pads are off in reset so LEDs are dark.")
    sh.note(11000, 13100, "Debug-USB power LED (BOM 'Misc', green 330R) belongs on sheet 15 with its rail.")

    # ---- mounting holes ---------------------------------------------------------
    for i in range(4):
        sh.add(f"H{1600 + i}", MOUNTING_HOLE, 2500 + i * 1500, 6500, {"1": "GND"},
               comment="Plated mounting hole, M2.5 (RPi pattern - confirm)")
    sh.note(1000, 7200, "Mounting holes plated, tied to GND. Fiducials (3, copper only) need no symbol.")
    return sh
