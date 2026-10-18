"""Sheet 07 - Storage: removable eMMC module (MMC0) and microSD (MMC1).

References:
  * docs/research/bom/storage-usb-ethernet.md sections 1-2 (GB042 module ecosystem,
    34-pin pinout, VCC/VCCQ from the host, pin-12 RST_n caveat, TF-01A, ESD)
  * TI SK-AM62B-P1 PROC142B p.20 (eMMC) and p.21 (SD load switch, pulls, SDCD)
  * docs/research/am625-tps65219-constraints.md A.6 (MMC0 HS200 1.8 V, MMC1 UHS-I,
    ROM needs MMC1_SDCD = 0 and a powered card for SD boot)
  * TPS22996 datasheet SLVSH99A section 8.3 / 9.2 (ON-pin series resistor, caps)

Decisions:
  * eMMC module VCC (3.3 V) and VCCQ (1.8 V) come straight from VCC_3V3_SYS and
    VDD_1V8 (no load switch). Both are PMIC-sequenced, so the module is power-cycled
    on every PMIC off/on and cold reset; it keeps the BOM to in-stock basics and
    avoids back-powering the module through the 1.8 V pull-ups. Warm-reset recovery
    relies on the ROM's CMD0 re-init plus RST_n where the module wires it (see notes).
  * SD card VDD and the SoC VDDSHV5 IO rail switch together in a TPS22996 (SK rev B).
    The enable SD_PWR_EN is pulled to RESETSTATZ instead of to GND: the card is
    unpowered while the SoC is in reset (contract intent), but powered as soon as
    the SoC leaves reset, which the ROM needs for SD boot (the default boot mode)
    because it never drives GPIO1_1. Software can still power-cycle the card by
    driving SD_PWR_EN low. This is the SK's AND(RESETSTATz, GPIO) without the gate.
"""
from schgen import Sheet
from symbols import CAP, RES, TPD4E05U06
from symlib.storage import GB042_30P, GB042_34P, TF_01A, TPS22996

C100N = "100nF 16V X7R 0402"
C1U = "1uF 25V X5R 0402"
C2U2 = "2.2uF 10V X5R 0402"
C4U7 = "4.7uF 10V X5R 0603"
C10U = "10uF 10V X5R 0603"
DNP = {"DNP": "1"}


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/07_Storage.SchDoc", "Storage: eMMC module and microSD", style=7)

    # ================================================================ eMMC module
    sh.add("J700", GB042_34P, 3600, 16000, {
        "6": "EMMC_D0", "29": "EMMC_D1", "27": "EMMC_D2", "10": "EMMC_D3",
        "4": "EMMC_D4", "2": "EMMC_D5", "33": "EMMC_D6", "31": "EMMC_D7",
        "25": "EMMC_CMD", "8": "EMMC_MOD_CLK", "12": "EMMC_MOD_RST_N", "15": "EMMC_MOD_DS",
        "20": "VDD_1V8", "21": "VDD_1V8", "22": "VCC_3V3_SYS", "23": "VCC_3V3_SYS",
        **{p: "GND" for p in ("1", "3", "5", "7", "9", "11", "13", "14", "16", "17", "18", "19",
                              "24", "26", "28", "30", "32", "34", "35", "36", "37", "38")},
    }, comment="GB042-34P-H10-E3000", MPN="GB042-34P-H10-E3000", Manufacturer="LS Mtron",
        Supplier="broker, consigned to JLC (STOCK RISK)")
    sh.add("J701", GB042_30P, 3600, 13000,
           {str(n): "GND" for n in range(1, 35)},
           comment="GB042-30P-H10-E3000 (DNP, retention only)", MPN="GB042-30P-H10-E3000",
           Manufacturer="LS Mtron", DNP="1")

    # MMC0 data/CMD pull-ups at the connector end (no stubs), CLK has none.
    sh.column(7600, 15900, [
        ("R701", RES, "VDD_1V8", "EMMC_CMD", "47k 0402"),
        ("R702", RES, "VDD_1V8", "EMMC_D0", "47k 0402"),
        ("R703", RES, "VDD_1V8", "EMMC_D1", "47k 0402"),
        ("R704", RES, "VDD_1V8", "EMMC_D2", "47k 0402"),
        ("R705", RES, "VDD_1V8", "EMMC_D3", "47k 0402"),
        ("R706", RES, "VDD_1V8", "EMMC_D4", "47k 0402"),
        ("R707", RES, "VDD_1V8", "EMMC_D5", "47k 0402"),
        ("R708", RES, "VDD_1V8", "EMMC_D6", "47k 0402"),
        ("R709", RES, "VDD_1V8", "EMMC_D7", "47k 0402"),
    ])
    # CLK series resistor at the SoC end; CLK and data-strobe pull-downs at the
    # connector (SK p.20 R398/R393: defined low while the clock is stopped and
    # for the unused HS400 strobe); module reset pull-up and GPIO link.
    sh.column(11000, 15900, [
        ("R700", RES, "EMMC_CLK", "EMMC_MOD_CLK", "22R 0402 (at SoC; 0R option)"),
        ("R712", RES, "EMMC_MOD_CLK", "GND", "10k 0402 (CLK pull-down, at pin 8)"),
        ("R713", RES, "EMMC_MOD_DS", "GND", "10k 0402 (strobe pull-down)"),
        ("R710", RES, "VDD_1V8", "EMMC_MOD_RST_N", "10k 0402"),
        ("R711", RES, "EMMC_RST_N", "EMMC_MOD_RST_N", "1k 0402 (RST_n link, see note)"),
    ])
    # Connector decoupling: VCC 3.3 V pins 22/23, VCCQ 1.8 V pins 20/21.
    sh.column(11000, 13700, [
        ("C700", CAP, "VCC_3V3_SYS", "GND", C10U + " (VCC)"),
        ("C701", CAP, "VCC_3V3_SYS", "GND", C100N + " (VCC)"),
        ("C702", CAP, "VDD_1V8", "GND", C4U7 + " (VCCQ)"),
        ("C703", CAP, "VDD_1V8", "GND", C100N + " (VCCQ pin 20)"),
        ("C704", CAP, "VDD_1V8", "GND", C100N + " (VCCQ pin 21)"),
    ])
    nx, ny = 14200, 16200
    for i, t in enumerate([
        "eMMC module (GB042 Odroid/Radxa/PINE64 standard). Do not hot-plug.",
        "VCC/VCCQ fed directly from VCC_3V3_SYS / VDD_1V8 (no load switch): module",
        "  power-cycles with the PMIC; pull-ups share VDD_1V8 so nothing back-powers it.",
        "MMC0 HS200: keep host traces <= 40 mm, matched <= 8 ps; connector next to SiP.",
        "  Module routing is unknown - drop to HS/DDR52 in DT if a module is marginal.",
        "R700 22R at the SoC ball (0R option); pulls at the connector pins, no stubs.",
        "Pin 12: RST_n on Hardkernel/PINE64 modules, 1.8 V supply on Radxa modules.",
        "  R711 1k limits the GPIO to 1.8 mA if it is a supply; RST_n only acts when",
        "  EXT_CSD[162] RST_n_ENABLE = 1. Remove R711 if a module misbehaves.",
        "Pin 13 (CDN) is GND on all modules; pin 15 strobe unused (no HS400), 10k down (SK).",
        "J701 30-pin retention plug: footprint only (DNP); all contacts to GND.",
        "Hold-down pads 35-38 / 31-34 per ROCK64 footprint - verify on a GB042 sample.",
    ]):
        sh.note(nx, ny - i * 200, t)

    # ================================================================ microSD power
    sh.add("U700", TPS22996, 3600, 8700, {
        "2": "VCC_3V3_SYS", "3": "VDD_SDIO_LDO1", "8": "VCC_3V3_SYS",
        "1": "SD_LSW_ON1", "4": "SD_LSW_ON2", "5": "GND",
        "7": "VDD_SD_3V3", "6": "VDDSHV5_SD",
    }, comment="TPS22996DRLR", MPN="TPS22996DRLR", Manufacturer="Texas Instruments")
    sh.column(7600, 8600, [
        ("R720", RES, "RESETSTATZ", "SD_PWR_EN", "4.7k 0402 (SD power follows RESETSTATz)"),
        ("R721", RES, "SD_PWR_EN", "SD_LSW_ON1", "10k 0402 (RT1 rise time)"),
        ("R722", RES, "SD_PWR_EN", "SD_LSW_ON2", "10k 0402 (RT2 rise time)"),
    ])
    sh.column(7600, 7300, [
        ("C710", CAP, "VCC_3V3_SYS", "GND", C1U + " (VIN1)"),
        ("C711", CAP, "VDD_SDIO_LDO1", "GND", C1U + " (VIN2)"),
        ("C712", CAP, "VCC_3V3_SYS", "GND", C100N + " (VBIAS)"),
        ("C713", CAP, "VDD_SD_3V3", "GND", C2U2 + " (card VDD)"),
        ("C714", CAP, "VDD_SD_3V3", "GND", C100N + " (card VDD)"),
        ("C715", CAP, "VDDSHV5_SD", "GND", C100N + " (VOUT2)"),
    ])

    # ================================================================ microSD socket
    sh.add("J702", TF_01A, 3600, 4600, {
        "7": "SD_D0", "8": "SD_D1", "1": "SD_D2", "2": "SD_D3", "3": "SD_CMD",
        "5": "SD_SOCK_CLK", "9": "SD_SOCK_CD_N",
        "4": "VDD_SD_3V3", "6": "GND", "10": "GND", "11": "GND", "12": "GND", "13": "GND",
    }, comment="TF-01A", MPN="TF-01A", Manufacturer="Korean Hroparts Elec", LCSC="C91145")
    # MMC1 pull-ups to the SWITCHED IO rail; CLK pull-up DNP (SK).
    sh.column(11000, 8600, [
        ("R723", RES, "VDDSHV5_SD", "SD_CMD", "47k 0402"),
        ("R724", RES, "VDDSHV5_SD", "SD_D0", "47k 0402"),
        ("R725", RES, "VDDSHV5_SD", "SD_D1", "47k 0402"),
        ("R726", RES, "VDDSHV5_SD", "SD_D2", "47k 0402"),
        ("R727", RES, "VDDSHV5_SD", "SD_D3", "47k 0402"),
        ("R728", RES, "VDDSHV5_SD", "SD_SOCK_CLK", "47k 0402 (DNP)", DNP),
        ("R729", RES, "SD_CLK", "SD_SOCK_CLK", "0R 0402 (at SoC; 22R option)"),
        ("R730", RES, "SD_SOCK_CD_N", "SD_CD_N", "100R 0402 (SDCD series)"),
        ("R731", RES, "VCC_3V3_SYS", "SD_SOCK_CD_N", "47k 0402 (SDCD pull-up)"),
    ])
    # ESD at the socket: 8 channels = CLK, CMD, DAT0-3, CD, card VDD.
    sh.add("U701", TPD4E05U06, 14600, 8600, {
        "1": "SD_SOCK_CLK", "2": "SD_CMD", "4": "SD_D0", "5": "SD_D1",
        "3": "GND", "8": "GND", "6": "NC", "7": "NC", "9": "NC", "10": "NC",
    }, comment="TPD4E05U06DQAR", MPN="TPD4E05U06DQAR", Manufacturer="Texas Instruments")
    sh.add("U702", TPD4E05U06, 14600, 6900, {
        "1": "SD_D2", "2": "SD_D3", "4": "SD_SOCK_CD_N", "5": "VDD_SD_3V3",
        "3": "GND", "8": "GND", "6": "NC", "7": "NC", "9": "NC", "10": "NC",
    }, comment="TPD4E05U06DQAR", MPN="TPD4E05U06DQAR", Manufacturer="Texas Instruments")

    nx, ny = 9800, 4600
    for i, t in enumerate([
        "microSD (MMC1, UHS-I). TPS22996 ch1: VCC_3V3_SYS -> card VDD (VDD_SD_3V3);",
        "  ch2: PMIC LDO1 (3.3/1.8 V, SD_VSEL on sheet 02) -> VDDSHV5_SD (SoC VDDSHV5 + pulls).",
        "SD_PWR_EN: R720 to RESETSTATZ = card + VDDSHV5 off during SoC reset, on when the",
        "  SoC leaves reset (ROM SD boot needs a powered card). GPIO drives low to cycle",
        "  power (UHS-I 1.8 V -> 3.3 V recovery); keep it low >= 5 ms (QOD 230R x 2.4 uF).",
        "R721/R722 set ON current 70-100 uA -> rise time ~0.5-1.5 ms (SLVSH99A Table 8-2).",
        "  ON VIH is only 1.2 V: if RESETSTATZ floats early in power-up (R815 on sheet 08 lifts it",
        "  to ~1.5 V) the switch may start; it turns off as soon as the SoC drives RESETSTATz low.",
        "Card VDD kept at 2.2 uF + 0.1 uF (SK) so QOD discharges it within a warm reset.",
        "SD_CD_N: 100R series + 47k to VCC_3V3_SYS (VDDSHV0 pad); card present = LOW.",
        "  Verify on a TF-01A sample that the Cd spring closes to the shell on insertion.",
        "ESD U701/U702 at the socket; NC pins 6/7/9/10 left open (flow-through pads).",
    ]):
        sh.note(nx, ny - i * 200, t)
    return sh
