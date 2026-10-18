"""Sheet 13 - Wireless: M.2 2230 Key-E socket for the TI M2-CC3351 (Wi-Fi 6 on SDIO,
BLE on UART), SMT standoff.

References:
  * PCI Express M.2 Specification Rev 5.0 v1.0 (in TI SWAC007): Table 3-1 (signal
    voltages), 3.1.12 (SUSCLK, W_DISABLE# with 100-200k card pull-up to 3.3 V),
    3.1.15 (VIO_CFG), 3.1.1 (VIO 1.8 V must be supplied by 1.8 V-sideband
    platforms), Table 3-12 (Key E pinout, card view), Table 4-26 (Key E 3.3 V: 2 A peak)
  * TI SWAU133 (M2-CC3351 EVM guide) Table 2-1/2-2 and the MCU127A card schematic
    (SWAC007): HOST_nRESET is W_DISABLE1# (pin 56, R8 fitted; SDIO_RESET# pin 23 is
    the R9 option) -> 10k pull-up to the card's 1.8 V -> SN74LVC1G17 (5.5 V tolerant);
    IRQ_WL on SDIO_WAKE# (pin 21) and IRQ_BLE on UART_WAKE# (pin 20) are open-drain
    SN74LVC2G06 outputs that need a 10k host pull-up; SUSCLK, W_DISABLE2#, PCM, LED,
    COEX, I2C, USB, PCIe and VIO 1.8 V are NC on the card; card UART/SDIO are 1.8 V.
  * TI SWRU612 (CC33xx HW integration) 2.5: SDIO lines need host pull-ups
  * TI SK-AM62B-P1 PROC142B p.19: 47k SDIO pull-ups, 10k pull-down on SDIO_CLK,
    optional 0R series on CMD/D0-D3 at the SoC, R6 WLAN_IRQ pull-up (rev B),
    33R on the UART line into the card, 10k pull-down on W_DISABLE1#, 0R SUSCLK
    link, 10u + 0.1u at each 3.3 V pin pair

Signal levels (all checked at the card): SDIO, UART, WLAN_EN, BT_EN are 1.8 V on both
sides - no level shifter. W_DISABLE1#/2# accept 1.8 V or 3.3 V (card buffer is
5.5 V tolerant). SUSCLK is 3.3 V from WKUP_CLKOUT0 - the M.2 default level, and NC on
the CC3351 card (it has an internal slow clock). UART_WAKE#/SDIO_WAKE#/ALERT# are open
drain, pulled up to VDD_1V8 here.
"""
from schgen import Sheet
from symbols import CAP, RES, TESTPOINT
from symlib.wireless import M2_KEY_E, STANDOFF_M2

C100N = "100nF 16V X7R 0402"
C10U = "10uF 10V X5R 0603"
C22U = "22uF 25V X5R 0805"
DNP = {"DNP": "1"}
P_C100N = {"MPN": "CL05B104KO5NNNC", "Manufacturer": "Samsung", "LCSC": "C1525"}
P_C22U = {"MPN": "CL21A226MAQNNNE", "Manufacturer": "Samsung", "LCSC": "C45783"}
P_R0 = {"MPN": "0402WGF0000TCE", "Manufacturer": "UNI-ROYAL", "LCSC": "C17168"}
P_R47K = {"MPN": "0402WGF4702TCE", "Manufacturer": "UNI-ROYAL", "LCSC": "C25792"}
P_R10K = {"MPN": "0402WGF1002TCE", "Manufacturer": "UNI-ROYAL", "LCSC": "C25744"}

SDIO = ["CMD", "D0", "D1", "D2", "D3"]


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/13_Wireless.SchDoc", "M.2 Key-E Wi-Fi / Bluetooth", style=7)

    nets = {}
    for p in M2_KEY_E.pins:
        if p.name in ("GND", "TAB"):
            nets[p.number] = "GND"
        elif p.name == "3.3V":
            nets[p.number] = "VCC_3V3_SYS"
        else:
            nets[p.number] = "NC"
    nets.update({
        "9": "WL_SDIO_CLK", "11": "M2_SDIO_CMD", "13": "M2_SDIO_D0", "15": "M2_SDIO_D1",
        "17": "M2_SDIO_D2", "19": "M2_SDIO_D3", "21": "WLAN_IRQ", "23": "M2_SDIO_RESET_N",
        "18": "M2_VIO_CFG", "20": "M2_UART_WAKE_N",
        "22": "BT_UART_RXD", "32": "M2_UART_RXD", "34": "BT_UART_CTS_N", "36": "BT_UART_RTS_N",
        "50": "M2_SUSCLK", "54": "BT_EN", "56": "WLAN_EN", "62": "M2_ALERT_N", "64": "VDD_1V8_M2",
    })
    sh.add("J1300", M2_KEY_E, 9000, 15500, nets, comment="APCI0085-P002A",
           MPN="APCI0085-P002A", Manufacturer="LOTES", LCSC="C841649")
    sh.note(8300, 16300, "M.2 2230 Key-E socket for TI M2-CC3351 (SDIO Wi-Fi 6 + UART BLE). Pin names = card view (M.2 Rev 5.0 Table 3-12).")
    sh.note(8300, 16100, "Pin 22 UART_TXD is the card output -> SoC RXD; pin 32 UART_RXD is the card input <- SoC TXD (TI SWAU133, SK p.19).")

    # ---- SDIO: optional series links at the SoC, 47k pull-ups at the socket ----
    sh.column(5300, 15400, [
        (f"R{1300 + i}", RES, f"WL_SDIO_{s}", f"M2_SDIO_{s}", "0R 0402 (series option, place at SoC)", P_R0)
        for i, s in enumerate(SDIO)
    ] + [
        ("R1313", RES, "WLAN_EN", "M2_SDIO_RESET_N", "0R 0402 (also drive SDIO_RESET#, card R9 option)", P_R0),
        ("R1314", RES, "M2_ALERT_N", "WLAN_IRQ", "0R 0402 DNP (card R10 option: IRQ on ALERT#)",
         {"DNP": "1", **P_R0}),
    ])
    sh.column(2200, 15400, [
        (f"R{1305 + i}", RES, "VDD_1V8", f"M2_SDIO_{s}", "47k 0402 (SDIO pull-up)", P_R47K)
        for i, s in enumerate(SDIO)
    ] + [
        ("R1310", RES, "WL_SDIO_CLK", "GND", "10k 0402 (SK R12, clock low while pad is off)", P_R10K),
        ("R1311", RES, "VDD_1V8", "WLAN_IRQ", "10k 0402 (card IRQ is open drain, SK R6)", P_R10K),
        ("R1312", RES, "WLAN_EN", "GND", "2.2k 0402 (beats the card's 10k pull-up: 0.33 V)"),
    ])
    sh.note(1000, 11600, "WLAN_EN -> W_DISABLE1# = card HOST_nRESET. The card pulls it to its 1.8 V with 10k into an LVC1G17;")
    sh.note(1000, 11400, "2.2k keeps the node at 0.33 V (< VT- min) while the SoC pads are off, so the card stays in reset.")
    sh.note(1000, 11200, "SDIO 1.8 V (VDDSHV6): 50 Ohm single-ended, CLK-to-data mismatch per AM62x MMC2 limits (8 ps HS/SDR104).")

    # ---- UART, wake, slow clock, sideband ----
    sh.column(14500, 15400, [
        ("R1316", RES, "BT_UART_TXD", "M2_UART_RXD", "33R 0402 (SK R24)"),
        ("R1315", RES, "BT_EN", "GND", "10k 0402 (W_DISABLE2#: BT off by default)", P_R10K),
        ("R1317", RES, "VDD_1V8", "M2_UART_WAKE_N", "10k 0402 (card IRQ_BLE open drain)", P_R10K),
        ("R1318", RES, "M2_SUSCLK_32K", "M2_SUSCLK", "0R 0402 (SK R7)", P_R0),
        ("R1319", RES, "VDD_1V8", "M2_VIO_CFG", "100k 0402 (VIO_CFG weak pull-up, M.2 3.1.15)"),
        ("R1320", RES, "VDD_1V8", "VDD_1V8_M2", "0R 0402 (VIO 1.8 V supply, M.2 3.1.1)", P_R0),
        ("C1305", CAP, "VDD_1V8_M2", "GND", C100N + " (pin 64)", P_C100N),
    ])
    sh.add("TP1300", TESTPOINT, 19800, 11300, {"1": "M2_UART_WAKE_N"}, comment="BT wake (no SoC GPIO)")
    sh.add("TP1301", TESTPOINT, 19800, 10900, {"1": "M2_VIO_CFG"}, comment="VIO_CFG (low = 3.3 V-only card)")

    # ---- 3.3 V: Key E allows 2 A peak; SK budget 800 mA ----
    sh.column(18300, 15400, [
        ("C1300", CAP, "VCC_3V3_SYS", "GND", C22U + " (bulk)", P_C22U),
        ("C1301", CAP, "VCC_3V3_SYS", "GND", C10U + " (pins 2/4)"),
        ("C1302", CAP, "VCC_3V3_SYS", "GND", C100N + " (pins 2/4)", P_C100N),
        ("C1303", CAP, "VCC_3V3_SYS", "GND", C10U + " (pins 72/74)"),
        ("C1304", CAP, "VCC_3V3_SYS", "GND", C100N + " (pins 72/74)", P_C100N),
    ])
    sh.add("H1300", STANDOFF_M2, 19800, 12300, {"1": "GND"}, comment="9774015243R M2 SMT standoff 1.5 mm",
           MPN="9774015243R", Manufacturer="Wurth Elektronik", LCSC="C22431324")
    sh.note(13700, 9900, "H1300 sits 30 mm from the socket (2230 card). M2 x 4 screw fitted by hand, not on the BOM tree.")

    sh.note(13700, 9500, "Levels at the card: SDIO/UART/WLAN_EN/BT_EN 1.8 V both sides, no level shifter.")
    sh.note(13700, 9300, "W_DISABLE1#/2# accept 1.8 or 3.3 V. SUSCLK is 3.3 V (M.2 default); NC on M2-CC3351.")
    sh.note(13700, 9100, "VIO_CFG low = 3.3 V-only sideband card: such cards must not be used (UART is 1.8 V).")
    sh.note(13700, 8900, "Unused per M.2 3.1.13 / card table: USB, PCIe, PCM, LED, COEX, I2C, vendor, UIM pins open.")
    sh.note(13700, 8700, "3.3 V pins: keep < 15 mOhm mismatch between the 4 power pins (M.2 4.6.2).")
    return sh
