"""Sheet 15 - debug: FT4232HL quad USB-UART on its own USB-C, isolation buffers,
Tag-Connect TC2070 JTAG.

References:
  * FTDI DS_FT4232H v2.6: Figure 6.1 (USB bus-powered configuration), section 6.3
    (crystal), Table 3.2-3.4 (power, REF 12k 1%, EEPROM interface), section 4 (RESET#)
  * TI SK-AM62B-P1 PROC142B p.33 (FT4232 UART-to-USB bridge, 4x SN74AVC4T245,
    TPD2E001 + TPD1E10B06 USB ESD, 0 Ohm shield link) and p.31-32 (JTAG pulls,
    cTI-20 connector, JTAG_EMU_RSTn 4.7k pull-up)
  * TI SPRU655I (Emulation and Trace Headers) Table 13 / Table 17 / Figure 26:
    TDIS to GND, VTRef through 100 Ohm, RTCK = 22 Ohm loopback of TCK, nTRST 4.7k
    pull-down, EMU 4.7-10k pull-ups, reset is open drain with 4.7k pull-up
  * AM625 DS SPRSP58C Table 5-74: TRSTn pulled down; EMU0/1, TCK, TDI, TMS pulled up
  * docs/research/bom/processor-clocks-debug-misc.md (Debug section)

UART channel map (data/pinmux_allocation.csv; all SoC pads at 3.3 V on VCC_3V3_SYS):
  A = MAIN_UART0 (Linux console, VDDSHV0)     B = MAIN_UART1 (TIFS, VDDSHV0)
  C = MCU_UART0 (MCU+ SDK, VDDSHV_CANUART)    D = WKUP_UART0 (DM R5, VDDSHV_CANUART)
Net naming: FTx_TXD / FTx_RXD are the FT4232 pins (FTDI view). FTx_TXD reaches the SoC
RXD net DBG_*_RXD; the SoC TXD net DBG_*_TXD reaches FTx_RXD.
"""
from schgen import Sheet
from symbols import CAP, FB, RES, TESTPOINT, TPD4E05U06, TVS_BI
from symlib.debug_io import (AP2112K, EE93LC46B, FT4232HL, SN74AVC4T245, TC2070, TPD2E001,
                             X322512MSB4SI)
from symlib.power_input import TYPE_C_31_M_12   # same connector part as USB-C #1 (sheet 01)

C100N = "100nF 16V X7R 0402"
C1U = "1uF 10V X5R 0402"
C4U7 = "4.7uF 10V X5R 0402"
BEAD = "BLM18PG121SN1D 120R@100MHz"
BEAD_P = {"MPN": "BLM18PG121SN1D", "Manufacturer": "Murata"}

UARTS = [  # channel, SoC RXD net (driven by FTDI TXD), SoC TXD net (to FTDI RXD)
    ("A", "DBG_MAIN_UART0_RXD", "DBG_MAIN_UART0_TXD"),
    ("B", "DBG_MAIN_UART1_RXD", "DBG_MAIN_UART1_TXD"),
    ("C", "DBG_MCU_UART0_RXD", "DBG_MCU_UART0_TXD"),
    ("D", "DBG_WKUP_UART0_RXD", "DBG_WKUP_UART0_TXD"),
]
FT_BUS = {"A": (16, 17, [18, 19, 21, 22, 23, 24]), "B": (26, 27, [28, 29, 30, 32, 33, 34]),
          "C": (38, 39, [40, 41, 43, 44, 45, 46]), "D": (48, 52, [53, 54, 55, 57, 58, 59])}


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/15_Debug.SchDoc", "Debug USB-UART and JTAG", style=8)  # D size

    # ---- debug USB-C (USB 2.0 device) -------------------------------------
    sh.add("J1500", TYPE_C_31_M_12, 2000, 20500, {
        "A4B9": "VBUS_DBG", "B4A9": "VBUS_DBG", "A5": "DBG_USB_CC1", "B5": "DBG_USB_CC2",
        "A8": "NC", "B8": "NC", "A1B12": "GND", "B1A12": "GND",
        "A6": "DBG_USB_DP", "B6": "DBG_USB_DP", "A7": "DBG_USB_DM", "B7": "DBG_USB_DM",
        "S1": "DBG_USB_SHIELD", "S2": "DBG_USB_SHIELD", "S3": "DBG_USB_SHIELD",
        "S4": "DBG_USB_SHIELD",
    }, comment="TYPE-C-31-M-12", MPN="TYPE-C-31-M-12", Manufacturer="Korean Hroparts (HRO)")
    sh.column(5900, 20400, [
        ("R1500", RES, "DBG_USB_CC1", "GND", "5.1k 1% 0402 (Rd, UFP)"),
        ("R1501", RES, "DBG_USB_CC2", "GND", "5.1k 1% 0402 (Rd, UFP)"),
        ("R1502", RES, "DBG_USB_SHIELD", "GND", "0R 0402 (shield link)"),
        ("D1500", TVS_BI, "VBUS_DBG", "GND", "TPD1E10B06DPYR",
         {"MPN": "TPD1E10B06DPYR", "Manufacturer": "Texas Instruments"}),
        ("C1500", CAP, "VBUS_DBG", "GND", "4.7uF 10V X5R 0603 (VBUS; total <= 10uF)"),
        ("C1501", CAP, "VBUS_DBG", "GND", C100N),
        ("C1502", CAP, "VBUS_DBG", "GND", C100N + " (TPD2E001 VCC)"),
    ])
    sh.add("U1501", TPD2E001, 8200, 20400, {
        "3": "DBG_USB_DP", "5": "DBG_USB_DM", "2": "NC", "1": "VBUS_DBG", "4": "GND",
    }, comment="TPD2E001DRLR", MPN="TPD2E001DRLR", Manufacturer="Texas Instruments")
    sh.note(1500, 21500, "Debug USB-C: USB 2.0 device only. D+/D- of both plug orientations tied at the connector; "
                         "90R differential, ESD (U1501) next to the connector, no stubs.")

    # ---- 3.3 V LDO from debug VBUS (FT4232 + buffer A side) ----------------
    sh.add("U1502", AP2112K, 8200, 18800, {
        "1": "VBUS_DBG", "3": "VBUS_DBG", "2": "GND", "5": "VCC_3V3_DBG", "4": "NC",
    }, comment="AP2112K-3.3TRG1", MPN="AP2112K-3.3TRG1", Manufacturer="Diodes Incorporated")
    sh.column(11500, 18700, [
        ("C1503", CAP, "VBUS_DBG", "GND", C1U + " (LDO in)"),
        ("C1504", CAP, "VCC_3V3_DBG", "GND", "2.2uF 10V X5R 0402 (LDO out)"),
        ("C1505", CAP, "VCC_3V3_DBG", "GND", C100N + " (LDO out)"),
    ])
    sh.column(9500, 17000, [
        ("FB1500", FB, "VCC_3V3_DBG", "VCC_3V3_FTPHY", BEAD + " (VPHY)", BEAD_P),
        ("FB1501", FB, "VCC_3V3_DBG", "VCC_3V3_FTPLL", BEAD + " (VPLL)", BEAD_P),
    ])
    sh.note(1500, 17300, "VCC_3V3_DBG / VBUS_DBG exist only while a debug cable is plugged in;")
    sh.note(1500, 17100, "they never touch SoC pins except through U1504/U1505.")

    # ---- FT4232HL -----------------------------------------------------------
    ft = {
        "50": "VCC_3V3_DBG", "49": "VDD_1V8_DBG",
        "12": "VDD_1V8_DBG", "37": "VDD_1V8_DBG", "64": "VDD_1V8_DBG",
        "20": "VCC_3V3_DBG", "31": "VCC_3V3_DBG", "42": "VCC_3V3_DBG", "56": "VCC_3V3_DBG",
        "4": "VCC_3V3_FTPHY", "9": "VCC_3V3_FTPLL",
        "8": "DBG_USB_DP", "7": "DBG_USB_DM", "6": "FT_REF", "14": "FT_RESET_N", "13": "GND",
        "2": "FT_OSCI", "3": "FT_OSCO",
        "63": "FT_EECS", "62": "FT_EECLK", "61": "FT_EEDATA",
        "60": "FT_PWREN_N", "36": "NC",
        "10": "GND", "1": "GND", "5": "GND", "11": "GND", "15": "GND", "25": "GND",
        "35": "GND", "47": "GND", "51": "GND",
    }
    for ch, (txd, rxd, unused) in FT_BUS.items():
        ft[str(txd)] = f"FT{ch}_TXD"
        ft[str(rxd)] = f"FT{ch}_RXD"
        for p in unused:
            ft[str(p)] = "NC"
    sh.add("U1500", FT4232HL, 16000, 20500, ft, comment="FT4232HL-REEL",
           MPN="FT4232HL-REEL", Manufacturer="FTDI")
    sh.column(13300, 20400, [
        # FTDI: VREGOUT needs >= 3.3 uF; a 4.7 uF 0402 X5R keeps ~3 uF at 1.8 V bias, so 10 uF 0603.
        ("C1506", CAP, "VDD_1V8_DBG", "GND", "10uF 10V X5R 0603 (VREGOUT, >= 3.3uF effective)"),
        ("C1507", CAP, "VDD_1V8_DBG", "GND", C100N + " (VCORE 12)"),
        ("C1508", CAP, "VDD_1V8_DBG", "GND", C100N + " (VCORE 37)"),
        ("C1509", CAP, "VDD_1V8_DBG", "GND", C100N + " (VCORE 64)"),
        ("C1510", CAP, "VCC_3V3_DBG", "GND", C100N + " (VREGIN)"),
        ("C1511", CAP, "VCC_3V3_DBG", "GND", C100N + " (VCCIO 20)"),
        ("C1512", CAP, "VCC_3V3_DBG", "GND", C100N + " (VCCIO 31)"),
        ("C1513", CAP, "VCC_3V3_DBG", "GND", C100N + " (VCCIO 42)"),
        ("C1514", CAP, "VCC_3V3_DBG", "GND", C100N + " (VCCIO 56)"),
        ("C1515", CAP, "VCC_3V3_FTPHY", "GND", C4U7 + " (VPHY)"),
        ("C1516", CAP, "VCC_3V3_FTPHY", "GND", C100N + " (VPHY)"),
        ("C1517", CAP, "VCC_3V3_FTPLL", "GND", C4U7 + " (VPLL)"),
        ("C1518", CAP, "VCC_3V3_FTPLL", "GND", C100N + " (VPLL)"),
    ])
    sh.column(9500, 16000, [
        ("R1503", RES, "FT_REF", "GND", "12k 1% 0402 (REF)"),
        ("R1504", RES, "VCC_3V3_DBG", "FT_RESET_N", "1k 1% 0402 (RESET# pull-up)"),
        ("R1505", RES, "VCC_3V3_DBG", "DBG_BUF_OE_N", "10k 1% 0402 (OE# pull-up)"),
        # PWREN# is a driven output (high until configured / in suspend): the always-on
        # option must open R1530 first, or R1506 would short PWREN# high to GND.
        ("R1530", RES, "FT_PWREN_N", "DBG_BUF_OE_N", "0R 0402 (PWREN# to OE#; remove for always-on)"),
        ("R1506", RES, "DBG_BUF_OE_N", "GND", "0R 0402 DNP (OE# always on; only with R1530 removed)",
         {"DNP": "1"}),
        ("C1519", CAP, "FT_OSCI", "GND", "33pF 50V C0G 0402 (CL 20pF crystal)"),
        ("C1520", CAP, "FT_OSCO", "GND", "33pF 50V C0G 0402 (CL 20pF crystal)"),
    ])
    sh.add("Y1500", X322512MSB4SI, 11800, 14400, {
        "1": "FT_OSCI", "2": "GND", "3": "FT_OSCO", "4": "GND",
    }, comment="12MHz X322512MSB4SI", MPN="X322512MSB4SI", Manufacturer="YXC")
    sh.note(13000, 21500, "FT4232HL per FTDI DS_FT4232H Fig 6.1 (bus powered): 1.8 V core from its own "
                          "VREGOUT, VPHY/VPLL through 120R beads.")
    sh.note(13000, 21300, "Unused xDBUS2-7 (RTS/CTS/DTR/DSR/DCD/RI) and SUSPEND# stay open as in Fig 6.1 "
                          "(internal 75k pull-ups). TEST to GND.")

    # ---- FT4232 configuration EEPROM (FTDI Fig 6.1: 10k pull-ups, 2.2k DO->EEDATA) ----
    sh.add("U1503", EE93LC46B, 11800, 11500, {
        "5": "FT_EECS", "4": "FT_EECLK", "3": "FT_EEDATA", "2": "GND",
        "6": "VCC_3V3_DBG", "1": "FT_EEDO",
    }, comment="93LC46BT-I/OT", MPN="93LC46BT-I/OT", Manufacturer="Microchip")
    sh.column(15000, 11400, [
        ("R1507", RES, "FT_EEDO", "FT_EEDATA", "2.2k 1% 0402"),
        ("R1508", RES, "VCC_3V3_DBG", "FT_EECS", "10k 1% 0402"),
        ("R1509", RES, "VCC_3V3_DBG", "FT_EECLK", "10k 1% 0402"),
        ("R1510", RES, "VCC_3V3_DBG", "FT_EEDO", "10k 1% 0402"),
        ("C1521", CAP, "VCC_3V3_DBG", "GND", C100N + " (EEPROM)"),
    ])
    sh.note(9000, 9200, "EEPROM: program with FT_PROG, all four channels as VCP (RS232 UART). "
                         "A blank EEPROM also works (default = 4x VCP).")

    # ---- isolation buffers -------------------------------------------------
    # A port = FT4232 side (VCCA = VCC_3V3_DBG, also supplies DIR/OE), B port = SoC side
    # (VCCB = VCC_3V3_SYS). Half 1 (DIR high, A->B): FTDI TXD -> SoC RXD.
    # Half 2 (DIR low, B->A): SoC TXD -> FTDI RXD.
    for i, desig in enumerate(("U1504", "U1505")):
        (c1, rx1, tx1), (c2, rx2, tx2) = UARTS[2 * i], UARTS[2 * i + 1]
        sh.add(desig, SN74AVC4T245, 21000, 20500 - 2000 * i, {
            "1": "VCC_3V3_DBG", "2": "VCC_3V3_DBG", "3": "GND",
            "15": "DBG_BUF_OE_N", "14": "DBG_BUF_OE_N",
            "4": f"FT{c1}_TXD", "5": f"FT{c2}_TXD", "6": f"FT{c1}_RXD", "7": f"FT{c2}_RXD",
            "8": "GND", "9": "GND", "16": "VCC_3V3_SYS",
            "13": rx1, "12": rx2, "11": tx1, "10": tx2,
        }, comment="SN74AVC4T245PWR", MPN="SN74AVC4T245PWR", Manufacturer="Texas Instruments")
    pulls = []
    n = 1511
    for _, rx, tx in UARTS:
        pulls.append((f"R{n}", RES, "VCC_3V3_SYS", rx, "10k 1% 0402 (SoC RXD pull-up)"))
        pulls.append((f"R{n + 1}", RES, "VCC_3V3_SYS", tx, "10k 1% 0402 (SoC TXD pull-up)"))
        n += 2
    sh.column(25600, 20400, pulls + [
        ("C1522", CAP, "VCC_3V3_DBG", "GND", C100N + " (U1504 VCCA)"),
        ("C1523", CAP, "VCC_3V3_SYS", "GND", C100N + " (U1504 VCCB)"),
        ("C1524", CAP, "VCC_3V3_DBG", "GND", C100N + " (U1505 VCCA)"),
        ("C1525", CAP, "VCC_3V3_SYS", "GND", C100N + " (U1505 VCCB)"),
    ])
    sh.note(20000, 15600, "Isolation: SN74AVC4T245 VCC isolation puts both ports in Hi-Z when either VCCA "
                          "(debug cable) or VCCB (SoC IO) is at 0 V; Ioff < 5 uA,")
    sh.note(20000, 15400, "so a powered debug cable never drives an unpowered SoC pad and vice versa. "
                          "OE# = FT4232 PWREN#: high (Hi-Z) until the host configures the FT4232,")
    sh.note(20000, 15200, "and pulled up to VCCA by R1505 during cable plug-in. B outputs swing to VCCB = "
                          "VCC_3V3_SYS, the same rail as the SoC pads. Always-on: remove R1530, fit R1506.")

    # ---- JTAG: Tag-Connect TC2070 (TI 14-pin) ------------------------------
    sh.add("J1501", TC2070, 22500, 11500, {
        "1": "JTAG_TMS", "3": "JTAG_TDI", "5": "JTAG_VTREF", "7": "JTAG_TDO_TC",
        "9": "JTAG_RTCK_TC", "11": "JTAG_TCK", "13": "EMU0",
        "2": "JTAG_TRSTN", "4": "GND", "6": "JTAG_SRST_N", "8": "GND", "10": "GND", "12": "GND",
        "14": "EMU1",
    }, comment="TC2070-NL-FP (footprint only, no part)", DNP="1",
       MPN="TC2070-NL-FP", Manufacturer="Tag-Connect")
    sh.column(18000, 12000, [
        ("R1520", RES, "JTAG_TDO", "JTAG_TDO_TC", "22R 1% 0402 (TDO, near SoC)"),
        ("R1521", RES, "JTAG_TCK", "JTAG_RTCK_TC", "22R 1% 0402 (RTCK loopback)"),
        ("R1522", RES, "VCC_3V3_SYS", "JTAG_VTREF", "100R 1% 0402 (VTref current limit)"),
        ("R1523", RES, "VCC_3V3_SYS", "JTAG_TCK", "10k 1% 0402"),
        ("R1524", RES, "VCC_3V3_SYS", "JTAG_TMS", "10k 1% 0402"),
        ("R1525", RES, "VCC_3V3_SYS", "JTAG_TDI", "10k 1% 0402"),
        ("R1526", RES, "VCC_3V3_SYS", "EMU0", "10k 1% 0402"),
        ("R1527", RES, "VCC_3V3_SYS", "EMU1", "10k 1% 0402"),
        ("R1528", RES, "JTAG_TRSTN", "GND", "4.7k 1% 0402 (TRSTn pull-down)"),
        ("R1529", RES, "VCC_3V3_SYS", "JTAG_SRST_N", "4.7k 0402 DNP (sheet 06 R604 already pulls SRST up)", {"DNP": "1"}),
    ])
    sh.add("U1510", TPD4E05U06, 27000, 11500, {
        "1": "JTAG_TCK", "2": "JTAG_TMS", "4": "JTAG_TDI", "5": "JTAG_TDO_TC",
        "3": "GND", "8": "GND", "6": "NC", "7": "NC", "9": "NC", "10": "NC",
    }, comment="TPD4E05U06DQAR", MPN="TPD4E05U06DQAR", Manufacturer="Texas Instruments")
    sh.add("U1511", TPD4E05U06, 27000, 10300, {
        "1": "JTAG_TRSTN", "2": "EMU0", "4": "EMU1", "5": "JTAG_SRST_N",
        "3": "GND", "8": "GND", "6": "NC", "7": "NC", "9": "NC", "10": "NC",
    }, comment="TPD4E05U06DQAR", MPN="TPD4E05U06DQAR", Manufacturer="Texas Instruments")
    sh.add("TP1500", TESTPOINT, 23500, 9800, {"1": "JTAG_SRST_N"}, comment="JTAG_SRST_N")
    sh.note(17500, 13200, "JTAG: TC2070 pads 1-14 = TI 14-pin header (TMS, nTRST, TDI, TDIS, VTref, KEY, TDO, "
                          "GND, RTCK, GND, TCK, GND, EMU0, EMU1).")
    sh.note(17500, 13000, "Pad 6 (KEY in TI-14) carries JTAG_SRST_N (non-standard; needs a cTI-20 pin 15 "
                          "-> pad 6 adapter). It goes to the MCU_PORz AND gate on sheet 06.")
    sh.note(17500, 12800, "Keep ESD (U1510/U1511) at J1501; pull-ups/down near the SoC. "
                          "TC2070 is a footprint: mark DNL, the cable is a tool.")
    return sh
