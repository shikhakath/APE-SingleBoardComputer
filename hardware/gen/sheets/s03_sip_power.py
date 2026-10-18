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
  * VDDS_OSC0 (also the MCU_PORz input domain) is on VDD_1V8 as on the SK.
  * VPP (eFuse) goes to VPP_EFUSE_1V8 - normally off (LDO on sheet 02 is DNP).
  * OLDI0 is unused but VDDA_1P8_OLDI0 must still be powered (pinmux notes).
"""
from schgen import Sheet
from symbols import CAP, FB, OSD6254, RES

C100N = "100nF 16V X7R 0402"
C1U = "1uF 10V X5R 0402"
C4U7 = "4.7uF 10V X5R 0402"
C10U = "10uF 10V X5R 0603"
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
    "VDDS_OSC0": "VDD_1V8",
    "VDDA_MCU": "VDDA_1V8_MCU",
    "VDDA_PLL0": "VDDA_1V8_PLL0",
    "VDDA_PLL1": "VDDA_1V8_PLL1",
    "VDDA_PLL2": "VDDA_1V8_PLL2",
    "VDDA_1P8_CSIRX0": "VDDA_1V8_CSI",
    "VDDA_1P8_OLDI0": "VDDA_1V8_OLDI",
    "VDDA_1P8_USB": "VDDA_1V8_USB",
    "VDDA_TEMP": "VDDA_1V8",
    "VDDA_3P3_USB": "VCC_3V3_SYS",
    "VMON_1P8_SOC": "VDD_1V8",
    "VMON_3P3_SOC": "VCC_3V3_SYS",
    "VMON_VSYS": "VMON_VSYS",
    "VPP": "VPP_EFUSE_1V8",
    "VDDSHV0": "VCC_3V3_SYS",
    "VDDSHV1": "VDD_1V8",
    "VDDSHV2": "VCC_3V3_SYS",
    "VDDSHV3": "VCC_3V3_SYS",
    "VDDSHV4": "VDD_1V8",
    "VDDSHV5": "VDDSHV5_SD",
    "VDDSHV6": "VDD_1V8",
    "VDDSHV_MCU": "VCC_3V3_SYS",
    "VDDSHV_CANUART": "VCC_3V3_SYS",
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
    sh.column(1500, 15400, [
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
    ])

    # ---- VMON_VSYS: 5 V divider, 0.45 V threshold -> trips at ~4.54 V ----
    sh.column(1500, 10600, [
        ("R301", RES, "VCC_5V0", "VMON_VSYS", "10k 1% 0402"),
        ("R302", RES, "VMON_VSYS", "GND", "1.1k 1% 0402"),
        ("C300", CAP, "VMON_VSYS", "GND", "22pF 50V C0G 0402"),
    ])

    # ---- decoupling, Octavo Table 4-3 (+ IO rails per TI/SK practice) ----
    core = [("VDD_CORE_0V85", C10U)] + [("VDD_CORE_0V85", C100N)] * 6
    core += [("VDDA_CORE_USB_0V85", C4U7), ("VDDA_CORE_USB_0V85", C100N),
             ("VDDA_CORE_CSI_0V85", C4U7), ("VDDA_CORE_CSI_0V85", C100N),
             ("VDD_CORE_0V85", C4U7 + " (VDD_CANUART ball)"), ("VDD_CORE_0V85", C100N + " (VDD_CANUART ball)")]
    core += [("VDDR_CORE_0V85", C100N)] * 4
    core += [("VDDS_DDR_1V2", C100N)] * 3 + [("DDR4_VPP_2V5_SIP", C100N)]
    analog = []
    for net in ("VDDA_1V8_MCU", "VDDA_1V8_PLL0", "VDDA_1V8_PLL1", "VDDA_1V8_PLL2",
                "VDDA_1V8_CSI", "VDDA_1V8_USB"):
        analog += [(net, C4U7), (net, C100N)]
    analog += [("VDDA_1V8_OLDI", C1U), ("VDDA_1V8_OLDI", C100N),
               ("VDDA_1V8", C100N + " (VDDA_TEMP ball)"),
               ("VDD_1V8", C1U + " (VDDS_OSC0)"), ("VDD_1V8", C100N + " (VDDS_OSC0)"),
               ("VCC_3V3_SYS", C100N + " (VDDA_3P3_USB)")]
    io = []
    for rail, note in (("VCC_3V3_SYS", "VDDSHV0"), ("VDD_1V8", "VDDSHV1"), ("VCC_3V3_SYS", "VDDSHV2"),
                       ("VCC_3V3_SYS", "VDDSHV3"), ("VDD_1V8", "VDDSHV4"), ("VDDSHV5_SD", "VDDSHV5"),
                       ("VDD_1V8", "VDDSHV6"), ("VCC_3V3_SYS", "VDDSHV_MCU"),
                       ("VCC_3V3_SYS", "VDDSHV_CANUART")):
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

    sh.note(12000, 16200, "Decoupling per OSD62x-PM DS Rev 2.0 Table 4-3. Caps may sit on either side; none needed under the BGA.")
    sh.note(12000, 16000, "VDD_CORE and VDDA_CORE_USB must stay within 1% - keep the beads and their traces low-resistance.")
    return sh
