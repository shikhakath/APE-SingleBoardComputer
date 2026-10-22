"""Sheet 14 - 40-pin Raspberry-Pi-style expansion header.

References:
  * docs/research/pinmux-allocation.md section 3 (header map) and section 2.5
    (MCU_I2C0 on pins 3/5, WKUP_I2C0 on 27/28, both fail-safe open-drain buffers)
  * data/pinmux_allocation.csv: every header ball is 3.3 V (VDDSHV0, VDDSHV3,
    VDDSHV_MCU, VDDSHV_CANUART), all fed from VCC_3V3_SYS on sheet 03
  * TI SK-AM62B-P1 PROC142B p.35 (J3) and the rev B design-update notes:
    62 Ohm + 47 pF RC slew limiter on the MCU_I2C0 / WKUP_I2C0 open-drain pads
    (SK p.34 WKUP_I2C0: 47 pF at the SoC pad, 62 Ohm in series, pull-up on the bus side)
  * AM625 DS SPRSP58C Table 5-74: MCU_I2C0 / WKUP_I2C0 balls need external pull resistors
  * Raspberry Pi HAT design guide (github.com/raspberrypi/hats designguide.md):
    ID_SD/ID_SC 3.9 k pull-ups, 24Cxx 16-bit-address EEPROM at 0x50, WP pulled up
    with 1 k to 3V3 and brought to a test point
  * docs/research/bom/hdmi-audio-camera-wireless-expansion.md (header, 33 Ohm, HAT EEPROM)

Signal path: SoC net HDRn_* -> 33 Ohm (or the 62 Ohm slew limiter on the I2C pins)
-> header-side net J_HDRn -> header pin n.
"""
from schgen import Sheet
from symbols import CAP, RES, TESTPOINT
from symlib.debug_io import BL24C32A, HDR_2X20, PTC_BSMD1206

R33 = "33R 1% 0402"
R33_P = {"MPN": "0402WGF330JTCE", "Manufacturer": "UNI-ROYAL"}
R62 = "62R 1% 0402 (slew limiter)"
R62_P = {"MPN": "0402WGF620JTCE", "Manufacturer": "UNI-ROYAL"}
C47P = "47pF 50V C0G 0402 (I2C slew limiter)"
C47P_P = {"MPN": "0402CG470J500NT", "Manufacturer": "FH"}

# SoC net per header pin (data/pinmux_allocation.csv; the number is the header pin)
SOC = {
    3: "HDR3_I2C1_SDA", 5: "HDR5_I2C1_SCL", 7: "HDR7_GPIO4_GPCLK", 8: "HDR8_UART_TXD",
    10: "HDR10_UART_RXD", 11: "HDR11_GPIO17", 12: "HDR12_GPIO18_PCM_CLK", 13: "HDR13_GPIO27",
    15: "HDR15_GPIO22", 16: "HDR16_GPIO23", 18: "HDR18_GPIO24", 19: "HDR19_SPI0_MOSI",
    21: "HDR21_SPI0_MISO", 22: "HDR22_GPIO25", 23: "HDR23_SPI0_SCLK", 24: "HDR24_SPI0_CE0_N",
    26: "HDR26_SPI0_CE1_N", 27: "HDR27_ID_SD", 28: "HDR28_ID_SC", 29: "HDR29_GPIO5",
    31: "HDR31_GPIO6", 32: "HDR32_GPIO12_PWM0", 33: "HDR33_GPIO13_PWM1",
    35: "HDR35_GPIO19_PCM_FS", 36: "HDR36_GPIO16", 37: "HDR37_GPIO26",
    38: "HDR38_GPIO20_PCM_DIN", 40: "HDR40_GPIO21_PCM_DOUT",
}
I2C_PINS = (3, 5, 27, 28)
GND_PINS = (6, 9, 14, 20, 25, 30, 34, 39)      # Raspberry Pi: pin 39 is GND (SK: HAT detect)


def hdr(pin: int) -> str:
    return f"J_HDR{pin}"


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/14_Expansion.SchDoc", "40-pin expansion header", style=7)  # C size

    # ---- header ---------------------------------------------------------
    nets = {}
    for pin in range(1, 41):
        if pin in (1, 17):
            nets[str(pin)] = "VCC_3V3_SYS"
        elif pin in (2, 4):
            nets[str(pin)] = "VCC_5V0_HDR"
        elif pin in GND_PINS:
            nets[str(pin)] = "GND"
        else:
            nets[str(pin)] = hdr(pin)
    sh.add("J1400", HDR_2X20, 12500, 15200, nets, comment="2541WV-2x20P",
           MPN="2541WV-2x20P", Manufacturer="HanElectricity")

    # ---- 33 Ohm series resistors, SoC side -> header side (24 signal pins) ----
    series = [p for p in sorted(SOC) if p not in I2C_PINS]
    odd = [p for p in series if p % 2]
    even = [p for p in series if not p % 2]
    n = 1400
    for x, pins in ((3200, odd), (7400, even)):
        entries = []
        for p in pins:
            entries.append((f"R{n}", RES, SOC[p], hdr(p), R33, R33_P))
            n += 1
        sh.column(x, 15100, entries)
    sh.note(1500, 16000, "33R series resistors: place at the header. They limit back-drive current from a HAT "
                         "into unpowered, non-fail-safe SoC pads and damp edges.")

    # ---- open-drain I2C: pins 3/5 (MCU_I2C0) and 27/28 (WKUP_I2C0, HAT ID) ----
    # SoC pad -- 47 pF to GND -- 62R -- bus (header side) -- pull-up to VCC_3V3_SYS.
    # No 33R here: the 62R already sits between the pad and the header.
    sh.column(3200, 9000, [
        (f"R{n}", RES, SOC[3], hdr(3), R62, R62_P),
        (f"R{n + 1}", RES, SOC[5], hdr(5), R62, R62_P),
        (f"R{n + 2}", RES, SOC[27], hdr(27), R62, R62_P),
        (f"R{n + 3}", RES, SOC[28], hdr(28), R62, R62_P),
    ])
    sh.column(7400, 9000, [
        ("C1400", CAP, SOC[3], "GND", C47P, C47P_P),
        ("C1401", CAP, SOC[5], "GND", C47P, C47P_P),
        ("C1402", CAP, SOC[27], "GND", C47P, C47P_P),
        ("C1403", CAP, SOC[28], "GND", C47P, C47P_P),
    ])
    sh.column(10400, 9000, [
        (f"R{n + 4}", RES, "VCC_3V3_SYS", hdr(3), "1.8k 1% 0402 (RPi I2C1 value)"),
        (f"R{n + 5}", RES, "VCC_3V3_SYS", hdr(5), "1.8k 1% 0402 (RPi I2C1 value)"),
        (f"R{n + 6}", RES, "VCC_3V3_SYS", hdr(27), "3.9k 1% 0402 (HAT ID bus)"),
        (f"R{n + 7}", RES, "VCC_3V3_SYS", hdr(28), "3.9k 1% 0402 (HAT ID bus)"),
    ])
    sh.note(1500, 9800, "MCU_I2C0 (pins 3/5) and WKUP_I2C0 (pins 27/28) are VDDSHV_MCU = VCC_3V3_SYS, "
                         "fail-safe open-drain: pull up to VCC_3V3_SYS only.")
    sh.note(1500, 9600, "Place the 47pF + 62R within 5 mm of the SoC balls (slew-rate spec when pulled to 3.3 V); "
                         "pull-ups at the header.")

    # ---- HAT-ID EEPROM (normally on the HAT) -----------------------------
    sh.add("U1400", BL24C32A, 14000, 8900, {
        "1": "GND", "2": "GND", "3": "GND", "4": "GND", "7": "HAT_ID_WP",
        "8": "VCC_3V3_SYS", "5": hdr(27), "6": hdr(28),
    }, comment="BL24C32A-SFRC (DNP)", MPN="BL24C32A-SFRC", Manufacturer="Shanghai Belling", DNP="1")
    sh.column(18000, 8800, [
        ("C1404", CAP, "VCC_3V3_SYS", "GND", "100nF 16V X7R 0402 (EEPROM, DNP)", {"DNP": "1"}),
        ("R1432", RES, "VCC_3V3_SYS", "HAT_ID_WP", "1k 1% 0402 (WP pull-up, DNP)", {"DNP": "1"}),
        ("R1433", RES, "VCC_3V3_SYS", "HDR10_UART_RXD", "47k 1% 0402 (UART5 RX idle high, Octavo 62_UART_2)"),
    ])
    sh.add("TP1400", TESTPOINT, 17000, 7700, {"1": "HAT_ID_WP"}, comment="HAT_ID_WP: short to GND to write")
    sh.note(13300, 9800, "HAT-ID EEPROM, I2C 0x50 (A2..A0 = 0). DNP by default: on a Raspberry Pi the ID EEPROM "
                          "lives on the HAT,")
    sh.note(13300, 9600, "and a second 0x50 device here would collide with it. Fit U1400/C1404/R1432 only for "
                          "boards that never carry an ID-EEPROM HAT.")

    # ---- header power -----------------------------------------------------
    sh.add("F1400", PTC_BSMD1206, 17300, 15000, {"1": "VCC_5V0", "2": "VCC_5V0_HDR"},
           comment="BSMD1206-110-6V (1.1A hold)", MPN="BSMD1206-110-6V", Manufacturer="BHFUSE")
    sh.column(20000, 14200, [
        ("C1405", CAP, "VCC_5V0_HDR", "GND", "10uF 10V X5R 0603 (header 5V)"),
        ("C1406", CAP, "VCC_3V3_SYS", "GND", "10uF 10V X5R 0603 (header 3V3)"),
        ("C1407", CAP, "VCC_3V3_SYS", "GND", "100nF 16V X7R 0402 (header 3V3)"),
    ])
    sh.note(15300, 16000, "Pins 2/4: VCC_5V0 through a 1.1 A PTC (RPi-style, always on with VCC_5V0).")
    sh.note(15300, 15800, "Pins 1/17: VCC_3V3_SYS, on only while the SoC IO rails are on. Never back-feed 3V3.")
    sh.note(15300, 15600, "Pin 39 is GND as on the Raspberry Pi (the SK used it for HAT detect).")
    return sh
