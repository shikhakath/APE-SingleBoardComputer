"""Sheet 06 - clocks, reset logic, buttons and BOOTMODE straps.

References:
  * AM625 datasheet SPRSP58C: 6.8.2 (FS RESET input), 6.8.6 (LVCMOS IOL 5 mA /
    IOH 9 mA at 3.3 V), 6.12.4.1.2 + Table 6-24 (25 MHz LVCMOS clock on
    MCU_OSC0_XI: point-to-point, series termination at the source, tR/F <= 4 ns),
    6.12.4.1.3 + Fig 6-21 / Table 6-26 (32 kHz crystal, Cf1 = Cf2 = 12-24 pF,
    optional Rbias and Rd), Table 5-74 (MCU_ERRORn pull-down, MCU_RESETz /
    RESET_REQz pull-up, every GPMC0_AD / BOOTMODE ball pulled)
  * AM62x TRM SPRUIV7C 5.3 Tables 5-2..5-5, 5-23, 5-29 (BOOTMODE fields)
  * TI SK-AM62B-P1 PROC142B p.34 (LFOSC, bootmode D-notes), p.44 (MCU_PORz AND3
    + 22 pF + 4.7 k pull-down, PORz_OUT/RESETSTATz pull-downs, 25 MHz
    ECS-2520MV with 10 k OE pull-up, 10 nF + 1 uF, 22R), p.45 (Schmitt
    debounce: 10 k pull-up + 100 nF + TPD1E10B06 per button, 22 pF at the SoC)
  * docs/research/pinmux-allocation.md section 4 (default 0x0643)
  * Shared-symbol pinouts re-checked against freshly downloaded datasheets:
    SN74LVC1G11 DCK ti.com/lit/ds/symlink/sn74lvc1g11.pdf Table 4-1 (A1 GND2 B3 Y4
    VCC5 C6); SN74LVC2G17 DBV ti.com/lit/ds/symlink/sn74lvc2g17.pdf Pin Functions
    p.3 (1A1 GND2 2A3 2Y4 VCC5 1Y6); TPD1E10B06 ti.com/lit/ds/symlink/tpd1e10b06.pdf
    Table 4-1 (2 pins, bidirectional).

PMIC_PGOOD level: the SN74LVC1G11 runs from VDD_1V8 but its inputs accept 0-5.5 V
at any VCC (SCES487I 5.3: VI 0..5.5 V; VIH = 0.65 x VCC = 1.17 V at 1.8 V; Ioff
partial power-down), so PMIC_PGOOD pulled to 3.3 V on sheet 02 is fine.
"""
from schgen import Sheet
from symbols import CAP, RES, SN74LVC1G11, SN74LVC2G17, TESTPOINT, TVS_BI, XTAL2
from symlib.clock_reset import DIPSW4, ECS2520MV, TS1187A

R10K = "10k 1% 0402"
C100N = "100nF 16V X7R 0402"
C22P = "22pF 50V C0G 0402"
DNP = {"DNP": "1"}

# ---------------------------------------------------------------- BOOTMODE
BOOT_DEFAULT = 0x0643          # 25 MHz | primary MMCSD port 1 (SD), FS | backup USB DFU
BOOT_NET = {b: f"BOOTMODE{b:02d}" for b in range(8)}
BOOT_NET.update({b: f"DPI_D{b + 8}" for b in range(8, 16)})   # BOOTMODE08..15 = DPI_D16..23
DIP_BITS = (3, 4, 5, 6)        # GPMC0_AD3..6: primary boot device, DIP positions 1..4
BOOT_MEANING = {
    0: "PLL ref 011 = 25 MHz", 1: "PLL ref", 2: "PLL ref",
    7: "MMCSD FS/raw: 0 = FAT", 8: "rsvd for MMCSD", 9: "MMCSD port: 1 = MMC1 (SD)",
    10: "backup 001 = USB", 11: "backup", 12: "backup", 13: "backup USB mode: 0 = DFU",
    14: "reserved", 15: "reserved",
}


def bit(b: int) -> int:
    return (BOOT_DEFAULT >> b) & 1


def _check_straps():
    value = 0
    for b in range(16):
        value |= bit(b) << b      # fixed straps, and DIP bits with every switch OFF
    assert value == BOOT_DEFAULT, hex(value)
    assert bit(9) == 1, "B9 is fixed at 1: USB primary would read it as 0.75 V core"


def build(sch_dir: str) -> Sheet:
    _check_straps()
    sh = Sheet(f"{sch_dir}/06_Clock_Reset_Boot.SchDoc", "Clocks, reset and boot", style=7)

    # ---- 25 MHz LVCMOS oscillator on MCU_OSC0_XI (VDDS_OSC0 = VDD_1V8) -----
    sh.add("U600", ECS2520MV, 1800, 16300, {
        "4": "VDD_1V8", "1": "OSC25M_OE", "2": "GND", "3": "OSC25M_SRC",
    }, comment="ECS-2520MV-250-CN-TR", MPN="ECS-2520MV-250-CN-TR", Manufacturer="ECS Inc")
    sh.column(5600, 16200, [
        ("R600", RES, "OSC25M_SRC", "OSC_25M", "22R 1% 0402 (series term. at the oscillator)"),
        ("R601", RES, "VDD_1V8", "OSC25M_OE", R10K + " (OE pull-up, SK R370)"),
        ("C600", CAP, "VDD_1V8", "GND", "10nF 50V X7R 0402 (osc VDD)"),
        ("C601", CAP, "VDD_1V8", "GND", "1uF 10V X5R 0402 (osc VDD)"),
    ])
    sh.note(800, 16700, "25 MHz: MCU_OSC0_XO is tied to GND on sheet 05. Osc + R600 within a few mm of ball G1, point-to-point, GND guard.")
    sh.note(800, 14500, "OSC: ECS spec is tR/F <= 7 ns @15 pF; AM62x needs <= 4 ns at XI (light load) - confirm with ECS or scope; LMK6CE02500 is TI's alt.")

    # ---- 32.768 kHz crystal, WKUP_LFOSC0 (DS Fig 6-21) ----------------------
    sh.add("Y600", XTAL2, 9600, 16100, {"1": "LFOSC_XI", "2": "LFOSC_XO_X"},
           comment="32.768kHz 9pF 20ppm Q13FC13500003", MPN="Q13FC13500003",
           Manufacturer="Seiko Epson")
    sh.column(9600, 15600, [
        ("R602", RES, "LFOSC_XO_X", "LFOSC_XO", "0R 0402 (Rd, DS Fig 6-21)"),
        ("C602", CAP, "LFOSC_XI", "GND", "18pF 50V C0G 0402 (Cf1)"),
        ("C603", CAP, "LFOSC_XO_X", "GND", "18pF 50V C0G 0402 (Cf2)"),
        ("R603", RES, "LFOSC_XI", "LFOSC_XO", "DNP (Rbias option, DS Fig 6-21)", DNP),
    ])
    sh.note(8000, 16700, "32 kHz: CL 9 pF with 2x18 pF. ESR 70k max -> Cshunt (C0 + PCB) <= 2-3 pF: short, guarded traces. LFXOSC_TRIM i_mult per CL.")

    # ---- MCU_PORz: AND3 in the 1.8 V VDDS_OSC0 domain (SK U72) --------------
    sh.add("U601", SN74LVC1G11, 1800, 12600, {
        "1": "PMIC_PGOOD", "3": "JTAG_SRST_N", "6": "PORZ_MAN_N", "2": "GND",
        "5": "VDD_1V8", "4": "MCU_PORZ",
    }, comment="SN74LVC1G11DCKR", MPN="SN74LVC1G11DCKR", Manufacturer="Texas Instruments")
    sh.column(5600, 12600, [
        ("C604", CAP, "VDD_1V8", "GND", C100N + " (U601 VCC)"),
        ("R604", RES, "VCC_3V3_SYS", "JTAG_SRST_N", R10K + " (gate enabled with no debugger)"),
        ("R605", RES, "VDD_1V8", "PORZ_MAN_N", R10K + " (spare input high)"),
        ("C605", CAP, "MCU_PORZ", "GND", C22P + " (glitch filter at ball D6)"),
        ("R606", RES, "MCU_PORZ", "GND", "4.7k 1% 0402 (SK R201; holds PORz low when U601 is unpowered)"),
    ])
    sh.add("TP600", TESTPOINT, 9300, 12500, {"1": "PORZ_MAN_N"}, comment="Cold reset: short to GND")
    sh.add("TP601", TESTPOINT, 9300, 12100, {"1": "MCU_PORZ"}, comment="MCU_PORz")
    sh.note(800, 13300, "MCU_PORz = AND(PMIC nRSTOUT, JTAG nSRST, manual). Fast push-pull edge per SK D-note; 9.5 ms delay comes from the PMIC.")
    sh.note(800, 13100, "Inputs are 5.5 V tolerant at VCC = 1.8 V, so PMIC_PGOOD (3.3 V pull-up on 02) and JTAG_SRST_N (3.3 V) are fine.")
    sh.note(800, 10600, "Input edge limit 20 ns/V at 1.8 V: PMIC_PGOOD rises through a 10k pull-up (~70 ns/V). Consider 2.2k on sheet 02 (SK: 100-200 ns).")

    # ---- warm reset and user buttons through a Schmitt buffer (SK U82) ------
    sh.add("U602", SN74LVC2G17, 4200, 8800, {
        "1": "WARMRST_BTN_N", "3": "USERBTN_SW_N", "2": "GND",
        "5": "VCC_3V3_SYS", "6": "RESET_REQZ", "4": "USER_BTN_N",
    }, comment="SN74LVC2G17DBVR", MPN="SN74LVC2G17DBVR", Manufacturer="Texas Instruments")
    sh.add("SW600", TS1187A, 2000, 6700, {
        "1": "WARMRST_BTN_N", "2": "WARMRST_BTN_N", "3": "GND", "4": "GND",
    }, comment="TS-1187A-B-A-B (RESET)", MPN="TS-1187A-B-A-B", Manufacturer="XKB Connection")
    sh.add("SW601", TS1187A, 2000, 5100, {
        "1": "USERBTN_SW_N", "2": "USERBTN_SW_N", "3": "GND", "4": "GND",
    }, comment="TS-1187A-B-A-B (USER)", MPN="TS-1187A-B-A-B", Manufacturer="XKB Connection")
    sh.column(5600, 6600, [
        ("R607", RES, "VCC_3V3_SYS", "WARMRST_BTN_N", R10K),
        ("C606", CAP, "WARMRST_BTN_N", "GND", C100N + " (debounce)"),
        ("D600", TVS_BI, "WARMRST_BTN_N", "GND", "TPD1E10B06DPYR",
         {"MPN": "TPD1E10B06DPYR", "Manufacturer": "Texas Instruments"}),
        ("R608", RES, "VCC_3V3_SYS", "USERBTN_SW_N", R10K),
        ("C607", CAP, "USERBTN_SW_N", "GND", C100N + " (debounce)"),
        ("D601", TVS_BI, "USERBTN_SW_N", "GND", "TPD1E10B06DPYR",
         {"MPN": "TPD1E10B06DPYR", "Manufacturer": "Texas Instruments"}),
    ])
    sh.column(9300, 8700, [
        ("C608", CAP, "VCC_3V3_SYS", "GND", C100N + " (U602 VCC)"),
        ("R609", RES, "VCC_3V3_SYS", "RESET_REQZ", R10K + " (Octavo 62_RESET_6)"),
        ("C609", CAP, "RESET_REQZ", "GND", C22P + " (glitch filter at ball D17)"),
    ])
    sh.note(800, 9500, "Buttons: 10k + 100nF RC into the Schmitt buffer (tau 1 ms). ESD diode at each button. Power button is on sheet 02.")

    # ---- reset status / error pins ------------------------------------------
    sh.column(5600, 3600, [
        ("R610", RES, "VCC_3V3_SYS", "MCU_RESETZ", R10K + " (VDDSHV_MCU)"),
        ("R611", RES, "RESETSTATZ", "GND", R10K + " (holds peripherals in reset)"),
        ("R612", RES, "PORZ_OUT", "GND", R10K + " (holds peripherals in reset)"),
        ("R613", RES, "MCU_ERRORN", "GND", R10K + " (DS Table 5-74: pull-down)"),
    ])
    for i, (tp, net, comment) in enumerate([
        ("TP602", "MCU_RESETZ", "MCU_RESETz"),
        ("TP603", "RESETSTATZ", "RESETSTATz"),
        ("TP604", "PORZ_OUT", "PORz_OUT"),
        ("TP605", "MCU_ERRORN", "MCU_ERRORn (1.8 V)"),
        ("TP606", "MCU_RESETSTATZ", "MCU_RESETSTATz (test only, erratum i2407)"),
    ]):
        sh.add(tp, TESTPOINT, 9300, 3600 - i * 400, {"1": net}, comment=comment)
    sh.note(800, 4200, "MCU_RESETSTATz: test point only - unreliable while MCU_RESETz is low (erratum i2407). Never use it as a reset source.")

    # ---- BOOTMODE straps ------------------------------------------------------
    # Fixed bits: a pull-up and a pull-down pad per bit, only the default fitted.
    n = 620
    pu, pd = [], []
    y_rows = 12600
    for b in [b for b in range(16) if b not in DIP_BITS]:
        net = BOOT_NET[b]
        one = bit(b) == 1
        tag = f"B{b} = {bit(b)}: {BOOT_MEANING[b]}"
        pu.append((f"R{n}", RES, "VCC_3V3_SYS", net, R10K + (" " if one else " DNP ") + f"({tag})",
                   {} if one else DNP))
        pd.append((f"R{n + 1}", RES, net, "GND", R10K + (" DNP " if one else " ") + f"({tag})",
                   DNP if one else {}))
        n += 2
    sh.column(12300, y_rows, pu)
    sh.column(14800, y_rows, pd)
    sh.note(11000, 13500, "BOOTMODE straps, default 0x0643 = 25 MHz, primary MMCSD port 1 (SD, FAT), backup USB DFU.")
    sh.note(11000, 13300, "Pull-ups to VCC_3V3_SYS (= VDDSHV3). Both pads on every fixed bit, one fitted. Latched at PORz_OUT rising.")
    sh.note(11000, 13100, "B8-B15 are DPI_D16..23 (HDMI data): fixed 10k only. The TFP410 must not drive them while the SoC is in reset.")

    # DIP bits B3..B6: 47k default pull + 1k through the switch to the other rail.
    # All switches OFF (as delivered) = default 1000 (MMCSD). B6 defaults to 1, so
    # its 47k pulls up and its switch pulls down: position 4 ON = 0.
    sw_nets = {}
    k_ser, k_def = [], []
    for pos, b in enumerate(DIP_BITS, start=1):
        node = f"BOOT_SW{b}"
        to_rail = "GND" if bit(b) else "VCC_3V3_SYS"
        sw_nets[str(pos)] = to_rail
        sw_nets[str(9 - pos)] = node
        on_val = 1 - bit(b)
        k_ser.append((f"R{n}", RES, node, BOOT_NET[b],
                      f"1k 1% 0402 (DIP pos {pos} ON -> B{b} = {on_val})"))
        k_def.append((f"R{n + 1}", RES, "VCC_3V3_SYS" if bit(b) else BOOT_NET[b],
                      BOOT_NET[b] if bit(b) else "GND",
                      f"47k 1% 0402 (B{b} OFF = {bit(b)})"))
        n += 2
    sh.add("SW602", DIPSW4, 17300, 12700, sw_nets, comment="2.54-4P TPGT (BOOT B3..B6)",
           MPN="2.54-4P TPGT", Manufacturer="SHOU HAN")
    sh.column(20300, 12600, k_ser)
    sh.column(20300, 10800, k_def)

    table = [
        "DIP SW602 (pos 1..4 = B3..B6; pos 4 is inverted: ON = 0). OFF = as delivered.",
        "  SD card (MMCSD port 1, FAT) [default]: all OFF                -> B6..B3 = 1000",
        "  eMMC boot partition:                   pos1 ON                -> 1001",
        "  UART0 (XMODEM, 115200 8N1):            pos1+2+3+4 ON          -> 0111",
        "  Ethernet RGMII (BOOTP/TFTP):           pos3+4 ON              -> 0100 (B9=1: ROM drives 25 MHz on CLKOUT0 = header pin 12)",
        "  No-boot / dev boot (JTAG):             pos1+2+3 ON            -> 1111",
        "  DO NOT select USB primary (1010 = pos2 ON): B9 is fixed 1, which USB",
        "  primary reads as 'core = 0.75 V'; this board runs 0.85 V. Use the USB DFU backup instead.",
        "  eMMC UDA via MMCSD is not available (needs B9 = 0); use the eMMC boot partition mode.",
        "  Backup (fixed): B12..B10 = 001 USB0 DFU, B13 = 0. Fixed: B2..B0 = 011, B7 = 0, B8 = 0, B15..B14 = 00.",
    ]
    for i, line in enumerate(table):
        sh.note(11000, 7400 - i * 200, line)
    return sh
