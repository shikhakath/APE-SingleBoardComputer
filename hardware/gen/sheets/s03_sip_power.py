"""Sheet 03 - OSD6254 SiP supplies: part A (72 power balls), beads, decoupling, VMON.

References:
  * Octavo OSD62x-PM datasheet Rev 2.0 Table 4-3 (recommended external caps;
    the SiP already contains CAP_VDDSx, RCALIB and part of the core/DDR decoupling)
  * TI SK-AM62B-P1 PROC142B p.15-17 (supply mapping, beads)
  * docs/research/am625-tps65219-constraints.md A.2 (rail grouping rules)

Rail decisions:
  * VDD_CORE, VDD_CANUART (no Partial-IO) and, through 26 Ohm beads,
    VDDA_CORE_USB / VDDA_CORE_CSIRX0 share Buck1 at 0.85 V.
  * VDDR_CORE is fed from VDD_CORE through a 0 Ohm link (same source, ramps
    together, as required at 0.85 V); the link lets it be measured or split.
  * Each 1.8 V analog supply gets its own 120 Ohm bead from VDDA_1V8 (LDO3).
    VDDA_MCU and VDDA_PLL0/1/2 take 1 uF + 0.1 uF (Octavo Table 4-3 size columns, SK p.17):
    with 4.7 uF there, LDO3 would carry 32 uF, over its 30 uF slow-ramp limit
    (TPS65219 DS Table 8-3, LDO3_SLOW_PU_RAMP = 1 in SLVUCL1A).
  * VDDS_OSC0 (also the MCU_PORz and MCU_ERRORn IO domain) has its own bead from VDDA_1V8,
    shared with the 25 MHz oscillator and the MCU_PORz gate on sheet 06 (Octavo 62_CLOCK_2:
    same rail; 62_POWER_4 group 2).
  * VDDA_TEMP shares the VDDA_MCU bead and VDDA_3P3_USB has its own bead from VCC_3V3_SYS
    (Octavo 62_POWER_4 groups 3 and 5).
  * Every VDDSHV bank is a named net, fed through a 0 Ohm link (R303-R310) from VCC_3V3_SYS
    or VDD_1V8. Pull-ups and IO supplies on the other sheets go to the net of the bank that
    powers the SoC ball, as the Octavo checklist words it (for example 62_CONFIG_4: MCU_RESETz
    to VDDSHV_MCU). The link pads double as the rail probe points of 62_ALL_2.
  * VDDSHV_CANUART stays on the switched 3.3 V rail: no Partial-IO, so AM625 DS Table 6-5
    note 3 asks only for a valid IO source that ramps with the other 3.3 V supplies. An
    always-on feed (as on the SK) would also need an always-on VDD_CANUART, because rails
    may only stay up across a power cycle in that Partial-IO configuration (DS 6.12.2.2).
  * VPP (eFuse) goes to VPP_EFUSE_1V8 - normally off (LDO on sheet 02 is DNP).
  * OLDI0 is unused but VDDA_1P8_OLDI0 must still be powered (pinmux notes).
"""
from schgen import Sheet
from symbols import CAP, FB, OSD6254, RES, TESTPOINT

C100N = "100nF 16V X7R 0402"
C1U = "1uF 10V X5R 0402"
C4U7 = "4.7uF 10V X5R 0402"
C10U = "10uF 10V X5R 0603"
R0_P = {"MPN": "0402WGF0000TCE", "Manufacturer": "UNI-ROYAL", "LCSC": "C17168"}
BEAD_A = "BLM15PX121SN1D 120R@100MHz 2A"
BEAD_C = "BLM18SG260TN1D 26R@100MHz 6A"

# ball name -> net
RAILS = {
    "VDD_CORE": "VDD_CORE_0V85",
    "VDD_CANUART": "VDD_CORE_0V85",
    "VDDR_CORE": "VDDR_CORE_0V85",
    "VDDA_CORE_USB": "VDDA_CORE_USB_0V85",
    "VDDA_CORE_CSIRX0": "VDDA_CORE_CSI_0V85",
    "VDDS_DDR": "VDDS_DDR_1V2",
    "DDR_VPP": "DDR4_VPP_2V5_SIP",
    "VDDS_OSC0": "VDDS_OSC0_1V8",
    "VDDA_MCU": "VDDA_1V8_MCU",
    "VDDA_PLL0": "VDDA_1V8_PLL0",
    "VDDA_PLL1": "VDDA_1V8_PLL1",
    "VDDA_PLL2": "VDDA_1V8_PLL2",
    "VDDA_1P8_CSIRX0": "VDDA_1V8_CSI",
    "VDDA_1P8_OLDI0": "VDDA_1V8_OLDI",
    "VDDA_1P8_USB": "VDDA_1V8_USB",
    "VDDA_TEMP": "VDDA_1V8_MCU",
    "VDDA_3P3_USB": "VDDA_3P3_USB",
    "VMON_1P8_SOC": "VDD_1V8",
    "VMON_3P3_SOC": "VCC_3V3_SYS",
    "VMON_VSYS": "VMON_VSYS",
    "VPP": "VPP_EFUSE_1V8",
    "VDDSHV0": "VDDSHV0",
    "VDDSHV1": "VDDSHV1",
    "VDDSHV2": "VDDSHV2",
    "VDDSHV3": "VDDSHV3",
    "VDDSHV4": "VDDSHV4",
    "VDDSHV5": "VDDSHV5_SD",
    "VDDSHV6": "VDDSHV6",
    "VDDSHV_MCU": "VDDSHV_MCU",
    "VDDSHV_CANUART": "VDDSHV_CANUART",
}


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/03_SiP_Power.SchDoc", "SiP power", style=7)

    nets = {}
    for p in OSD6254.pins:
        if p.part == 1:
            if p.name not in RAILS:
                raise KeyError(f"no rail for SiP power ball {p.number} {p.name}")
            nets[p.number] = RAILS[p.name]
    sh.add("U1", OSD6254, 7000, 15500, nets, part=1, comment="OSD6254-1G-IPM",
           MPN="OSD6254-1G-IPM", Manufacturer="Octavo Systems")

    # ---- feed links and beads -------------------------------------------
    sh.column(3000, 15400, [
        ("R300", RES, "VDD_CORE_0V85", "VDDR_CORE_0V85", "0R 0603 (VDDR_CORE from VDD_CORE)"),
        ("FB300", FB, "VDD_CORE_0V85", "VDDA_CORE_USB_0V85", BEAD_C),
        ("FB301", FB, "VDD_CORE_0V85", "VDDA_CORE_CSI_0V85", BEAD_C),
        ("FB302", FB, "DDR4_VPP_2V5", "DDR4_VPP_2V5_SIP", BEAD_A),
        ("FB303", FB, "VDDA_1V8", "VDDA_1V8_MCU", BEAD_A),
        ("FB304", FB, "VDDA_1V8", "VDDA_1V8_PLL0", BEAD_A),
        ("FB305", FB, "VDDA_1V8", "VDDA_1V8_PLL1", BEAD_A),
        ("FB306", FB, "VDDA_1V8", "VDDA_1V8_PLL2", BEAD_A),
        ("FB307", FB, "VDDA_1V8", "VDDA_1V8_CSI", BEAD_A),
        ("FB308", FB, "VDDA_1V8", "VDDA_1V8_OLDI", BEAD_A),
        ("FB309", FB, "VDDA_1V8", "VDDA_1V8_USB", BEAD_A),
        ("FB310", FB, "VDDA_1V8", "VDDS_OSC0_1V8", BEAD_A + " (VDDS_OSC0, 25 MHz osc, PORz gate)"),
    ])

    # ---- IO-domain rails: one named net per VDDSHV bank (see the module docstring) ----
    sh.note(6200, 9900, "IO-domain rails: pull-ups go to the net of the bank that powers the ball.")
    sh.column(8500, 9500, [
        ("R303", RES, "VCC_3V3_SYS", "VDDSHV0", "0R 0402 (UART0/1, I2C0/1, resets, SDCD)", R0_P),
        ("R304", RES, "VDD_1V8", "VDDSHV1", "0R 0402 (OSPI balls: BT UART, eMMC GPIO)", R0_P),
        ("R305", RES, "VCC_3V3_SYS", "VDDSHV2", "0R 0402 (RGMII, MDIO, PHY VDDIO)", R0_P),
        ("R306", RES, "VCC_3V3_SYS", "VDDSHV3", "0R 0402 (DPI, GPMC, BOOTMODE)", R0_P),
        ("R307", RES, "VDD_1V8", "VDDSHV4", "0R 0402 (MMC0, eMMC VCCQ)", R0_P),
        ("R308", RES, "VDD_1V8", "VDDSHV6", "0R 0402 (MMC2, M.2 SDIO)", R0_P),
        ("R309", RES, "VCC_3V3_SYS", "VDDSHV_MCU", "0R 0402 (MCU_RESETz, JTAG, MCU/WKUP_I2C0)", R0_P),
        ("R310", RES, "VCC_3V3_SYS", "VDDSHV_CANUART", "0R 0402 (MCU/WKUP_UART0, PMIC_LPM_EN0)", R0_P),
        ("FB311", FB, "VCC_3V3_SYS", "VDDA_3P3_USB", BEAD_A + " (62_POWER_4 group 5)"),
    ])

    # ---- VMON_VSYS: 62_CONFIG_6 / AM625 DS Fig 8-5 divider on the 5 V system supply. 0.45 V +-3%,
    #      1% resistors, 2.5 uA leakage: trips between 3.97 V and 4.47 V (DS method). The figure's
    #      4.81k is not an E96 value; 4.87k keeps the maximum trip under the 4.5 V (5 V - 10%) target.
    sh.column(3000, 9800, [
        ("R301", RES, "VCC_5V0", "VMON_VSYS", "40.2k 1% 0402 (R2)",
         {"MPN": "0402WGF4022TCE", "Manufacturer": "UNI-ROYAL", "LCSC": "C25893"}),
        ("R302", RES, "VMON_VSYS", "GND", "4.87k 1% 0402 (R1)",
         {"MPN": "0402WGF4871TCE", "Manufacturer": "UNI-ROYAL", "LCSC": "C25902"}),
        ("C300", CAP, "VMON_VSYS", "GND", "22pF 50V C0G 0402 (C1)"),
    ])

    # ---- rail test points (Octavo checklist 62_ALL_2) -------------------------
    for i, rail in enumerate(("VSYS_PD", "VCC_5V0", "VCC_3V3_MAIN", "VCC_3V3_SYS", "VDD_CORE_0V85",
                              "VDDR_CORE_0V85", "VDDS_DDR_1V2", "DDR4_VPP_2V5_SIP", "VDD_1V8",
                              "VDDA_1V8", "VDDS_OSC0_1V8", "VDDSHV5_SD", "VDD_1V0_PHY")):
        sh.add(f"TP{300 + i}", TESTPOINT, 3000, 7800 - i * 400, {"1": rail}, comment=rail)

    # ---- decoupling, Octavo Table 4-3 (+ IO rails per TI/SK practice) ----
    core = [("VDD_CORE_0V85", C10U)] + [("VDD_CORE_0V85", C100N)] * 6
    core += [("VDDA_CORE_USB_0V85", C4U7), ("VDDA_CORE_USB_0V85", C100N),
             ("VDDA_CORE_CSI_0V85", C4U7), ("VDDA_CORE_CSI_0V85", C100N),
             ("VDD_CORE_0V85", C4U7 + " (VDD_CANUART ball)"), ("VDD_CORE_0V85", C100N + " (VDD_CANUART ball)")]
    core += [("VDDR_CORE_0V85", C100N)] * 4
    core += [("VDDS_DDR_1V2", C100N)] * 3 + [("DDR4_VPP_2V5_SIP", C100N)]
    analog = []
    for net in ("VDDA_1V8_MCU", "VDDA_1V8_PLL0", "VDDA_1V8_PLL1", "VDDA_1V8_PLL2"):
        analog += [(net, C1U), (net, C100N)]
    for net in ("VDDA_1V8_CSI", "VDDA_1V8_USB"):
        analog += [(net, C4U7), (net, C100N)]
    analog += [("VDDA_1V8_OLDI", C1U), ("VDDA_1V8_OLDI", C100N),
               ("VDDA_1V8_MCU", C100N + " (VDDA_TEMP ball)"),
               ("VDDS_OSC0_1V8", C1U + " (VDDS_OSC0)"), ("VDDS_OSC0_1V8", C100N + " (VDDS_OSC0)"),
               ("VDDA_3P3_USB", C100N + " (VDDA_3P3_USB)")]
    io = []
    for rail, note in (("VDDSHV0", "VDDSHV0"), ("VDDSHV1", "VDDSHV1"), ("VDDSHV2", "VDDSHV2"),
                       ("VDDSHV3", "VDDSHV3"), ("VDDSHV4", "VDDSHV4"), ("VDDSHV5_SD", "VDDSHV5"),
                       ("VDDSHV6", "VDDSHV6"), ("VDDSHV_MCU", "VDDSHV_MCU"),
                       ("VDDSHV_CANUART", "VDDSHV_CANUART")):
        io += [(rail, f"{C1U} ({note})"), (rail, f"{C100N} ({note})")]
    vpp = [("VPP_EFUSE_1V8", C1U + " (VPP, DNP)", {"DNP": "1"}),
           ("VPP_EFUSE_1V8", C1U + " (VPP, DNP)", {"DNP": "1"}),
           ("VPP_EFUSE_1V8", C100N + " (VPP, DNP)", {"DNP": "1"})]

    n = 301
    columns = [core, analog, io, vpp]
    xs = [12500, 15000, 17500, 20000]
    for x, items in zip(xs, columns):
        entries = []
        for item in items:
            net, comment = item[0], item[1]
            params = item[2] if len(item) > 2 else {}
            entries.append((f"C{n}", CAP, net, "GND", comment, params))
            n += 1
        sh.column(x, 15400, entries, pitch=400)
    assert n == 361, n
    sh.column(20000, 14200, [("C361", CAP, "VDDA_3P3_USB", "GND", C1U + " (VDDA_3P3_USB, FB311 output)")])

    sh.note(12000, 16200, "Decoupling per OSD62x-PM DS Rev 2.0 Table 4-3. Caps may sit on either side; none needed under the BGA.")
    sh.note(12000, 16000, "VDD_CORE and VDDA_CORE_USB must stay within 1% - keep the beads and their traces low-resistance.")
    return sh
