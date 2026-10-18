"""Sheet 02 - PMIC (TPS6521904RSMR), 3.3 V IO load switch, eFuse VPP LDO, PHY 1.0 V LDO.

References:
  * TI SK-AM62B-P1 PROC142B schematic p.12-13 (same PMIC OPN and rail map)
  * datasheets/tps65219.pdf Table 5-1 (pins), section 8.2.3 (external parts)
  * docs/research/am625-tps65219-constraints.md section B.3 (capacitance limits)

Rail map (TPS6521904 NVM, VSYS = 3.3 V):
  Buck1 0.85 V -> VDD_CORE_0V85 (SiP VDD_CORE + VDDR_CORE, same source)
  Buck2 1.8 V  -> VDD_1V8
  Buck3 1.2 V  -> VDDS_DDR_1V2 (SiP DDR IO + internal DDR4 VDD/VDDQ)
  LDO1 3.3/1.8 V (VSEL_SD) -> VDD_SDIO_LDO1 (to the SD dual load switch)
  LDO2 unused in this NVM (SK-AM62B leaves it on a test point)
  LDO3 1.8 V   -> VDDA_1V8 (analog, beads on sheet 03)
  LDO4 2.5 V   -> DDR4_VPP_2V5 (SiP DDR_VPP + PHY 2.5 V)
  GPO2         -> EN_3V3_SYS (TPS22965 -> VCC_3V3_SYS)
Open items: confirm the rail map and LDO1 bypass/LDO mode against TI SLVUCL1.
"""
from schgen import Sheet
from symbols import CAP, IND, RES, SW_PUSH, TESTPOINT, TLV755P, TPS22965, TPS65219, TVS_BI

C0402_100N = "100nF 16V X7R 0402"
C0402_2U2 = "2.2uF 10V X5R 0402"
C0603_4U7 = "4.7uF 10V X5R 0603"
C0603_10U = "10uF 10V X5R 0603"
C0805_22U = "22uF 6.3V X5R 0805"


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/02_PMIC.SchDoc", "PMIC and power switches", style=7)  # C size

    # ---- PMIC -------------------------------------------------------
    sh.add("U200", TPS65219, 6000, 14000, {
        "13": "VCC_3V3_MAIN", "4": "VCC_3V3_MAIN", "5": "VCC_3V3_MAIN",
        "30": "VCC_3V3_MAIN", "26": "VCC_3V3_MAIN", "6": "VCC_3V3_MAIN",
        "20": "VDD_1V8", "22": "VCC_3V3_MAIN",
        "25": "PMIC_PB_N", "28": "TP_PMIC_MODE_RESET", "31": "TP_PMIC_STBY",
        "12": "PMIC_VSEL_SD",
        "9": "I2C0_SDA", "10": "I2C0_SCL",
        "14": "PMIC_VDD1P8", "15": "GND", "33": "GND",
        "2": "PMIC_LX_B1", "3": "PMIC_LX_B1", "1": "VDD_CORE_0V85",
        "29": "PMIC_LX_B2", "32": "VDD_1V8",
        "27": "PMIC_LX_B3", "24": "VDDS_DDR_1V2",
        "7": "VDD_SDIO_LDO1", "19": "VDD_LDO2", "21": "VDDA_1V8", "23": "DDR4_VPP_2V5",
        "8": "TP_PMIC_GPO1", "17": "EN_3V3_SYS", "16": "TP_PMIC_GPIO",
        "11": "PMIC_INT_N", "18": "PMIC_PGOOD",
    }, comment="TPS6521904RSMR", MPN="TPS6521904RSMR", Manufacturer="Texas Instruments")

    # ---- input decoupling (datasheet 8.2.3: 4.7 uF per PVIN_Bx, 2.2 uF VSYS/LDO) ---
    sh.column(2500, 13900, [
        ("C200", CAP, "VCC_3V3_MAIN", "GND", C0603_4U7 + " (PVIN_B1)"),
        ("C201", CAP, "VCC_3V3_MAIN", "GND", C0402_100N + " (PVIN_B1)"),
        ("C202", CAP, "VCC_3V3_MAIN", "GND", C0603_4U7 + " (PVIN_B2)"),
        ("C203", CAP, "VCC_3V3_MAIN", "GND", C0603_4U7 + " (PVIN_B3)"),
        ("C204", CAP, "VCC_3V3_MAIN", "GND", C0402_2U2 + " (VSYS)"),
        ("C205", CAP, "VCC_3V3_MAIN", "GND", C0402_2U2 + " (PVIN_LDO1)"),
        ("C206", CAP, "VDD_1V8", "GND", C0402_2U2 + " (PVIN_LDO2)"),
        ("C207", CAP, "VCC_3V3_MAIN", "GND", C0603_4U7 + " (PVIN_LDO34)"),
        ("C208", CAP, "PMIC_VDD1P8", "GND", C0402_2U2 + " (VDD1P8, no load)"),
        ("C209", CAP, "VCC_3V3_MAIN", "GND", C0805_22U + " (bulk)"),
    ])

    # ---- buck inductors (0.47 uH, DCR <= 50 mOhm, Isat >= 7.4 A B1 / 5.4 A B2-B3) ----
    sh.column(10000, 13900, [
        ("L200", IND, "PMIC_LX_B1", "VDD_CORE_0V85", "0.47uH DFE252012F-R47M (Buck1, Isat 7.4A)", {"MPN": "DFE252012F-R47M=P2"}),
        ("L201", IND, "PMIC_LX_B2", "VDD_1V8", "0.47uH DFE252012F-R47M (Buck2)", {"MPN": "DFE252012F-R47M=P2"}),
        ("L202", IND, "PMIC_LX_B3", "VDDS_DDR_1V2", "0.47uH DFE252012F-R47M (Buck3)", {"MPN": "DFE252012F-R47M=P2"}),
    ], pitch=500)

    # ---- buck and LDO output capacitors (FB senses at these local caps) ----
    sh.column(12500, 13900, [
        ("C210", CAP, "VDD_CORE_0V85", "GND", C0805_22U + " (Buck1 out)"),
        ("C211", CAP, "VDD_CORE_0V85", "GND", C0805_22U + " (Buck1 out)"),
        ("C212", CAP, "VDD_1V8", "GND", C0805_22U + " (Buck2 out)"),
        ("C213", CAP, "VDD_1V8", "GND", C0805_22U + " (Buck2 out)"),
        ("C214", CAP, "VDDS_DDR_1V2", "GND", C0805_22U + " (Buck3 out)"),
        ("C215", CAP, "VDDS_DDR_1V2", "GND", C0805_22U + " (Buck3 out)"),
    ])
    sh.column(15000, 13900, [
        ("C216", CAP, "VDD_SDIO_LDO1", "GND", C0402_2U2 + " (LDO1 out)"),
        ("C217", CAP, "VDD_LDO2", "GND", C0402_2U2 + " (LDO2 out, unused)"),
        ("C218", CAP, "VDDA_1V8", "GND", C0402_2U2 + " (LDO3 out)"),
        ("C219", CAP, "DDR4_VPP_2V5", "GND", C0402_2U2 + " (LDO4 out)"),
    ])
    sh.note(12000, 14600, "FB_B1/B2/B3 route as traces to the local output caps (no remote sense)")
    sh.note(12000, 14400, "Total C on each LDO rail incl. SiP-internal caps: LDO1/2 <= 20uF, LDO3/4 <= 30uF (slow ramp)")

    # ---- control pull-ups, interrupt slew limiter, push button ----
    sh.column(2500, 9500, [
        ("R200", RES, "VCC_3V3_MAIN", "PMIC_PB_N", "10k"),
        ("R201", RES, "VCC_3V3_MAIN", "PMIC_PGOOD", "10k"),
        ("R202", RES, "VCC_3V3_SYS", "PMIC_INT_N", "10k"),
        ("R203", RES, "PMIC_INT_N", "EXTINT_N", "62R (slew limiter, SK rev B)"),
        ("C220", CAP, "EXTINT_N", "GND", "47pF 50V C0G 0402"),
        ("R204", RES, "VCC_3V3_SYS", "PMIC_VSEL_SD", "10k (SD starts at 3.3 V)"),
        ("R205", RES, "VCC_3V3_MAIN", "EN_3V3_SYS", "10k (GPO2 is open drain)"),
        ("SW200", SW_PUSH, "PMIC_PB_N", "GND", "Power button"),
        ("D200", TVS_BI, "PMIC_PB_N", "GND", "TPD1E10B06 ESD"),
    ])
    sh.add("TP200", TESTPOINT, 6000, 8500, {"1": "TP_PMIC_MODE_RESET"}, comment="MODE/RESET (internal pull)")
    sh.add("TP201", TESTPOINT, 6000, 8100, {"1": "TP_PMIC_STBY"}, comment="MODE/STBY")
    sh.add("TP202", TESTPOINT, 6000, 7700, {"1": "TP_PMIC_GPO1"}, comment="GPO1")
    sh.add("TP203", TESTPOINT, 6000, 7300, {"1": "TP_PMIC_GPIO"}, comment="GPIO")
    sh.add("TP204", TESTPOINT, 6000, 6900, {"1": "VDD_LDO2"}, comment="LDO2")

    # ---- 3.3 V IO load switch: GPO2 sequences VCC_3V3_SYS (slot 1) ----
    sh.add("U201", TPS22965, 9500, 8500, {
        "1": "VCC_3V3_MAIN", "2": "VCC_3V3_MAIN", "4": "VCC_3V3_MAIN", "3": "EN_3V3_SYS",
        "5": "GND", "9": "GND", "7": "VCC_3V3_SYS", "8": "VCC_3V3_SYS", "6": "LSW_CT",
    }, comment="TPS22965DSGR", MPN="TPS22965DSGR", Manufacturer="Texas Instruments")
    sh.column(13500, 8400, [
        ("C221", CAP, "LSW_CT", "GND", "220pF 50V C0G 0402 (CT: IO supply slew)"),
        ("C222", CAP, "VCC_3V3_MAIN", "GND", C0402_2U2 + " (VIN)"),
        ("C223", CAP, "VCC_3V3_SYS", "GND", C0603_10U + " (VOUT)"),
        ("C224", CAP, "VCC_3V3_SYS", "GND", C0402_100N + " (VOUT)"),
    ])

    # ---- VPP eFuse LDO (DNP by default) and Ethernet PHY 1.0 V ----
    sh.add("U202", TLV755P, 9500, 5600, {
        "1": "VCC_3V3_SYS", "3": "VPP_EFUSE_EN", "2": "GND", "5": "VPP_EFUSE_1V8", "4": "NC",
    }, comment="TLV75518PDBVR (DNP)", MPN="TLV75518PDBVR", DNP="1")
    sh.add("U203", TLV755P, 9500, 4300, {
        "1": "VDD_1V8", "3": "VDD_1V8", "2": "GND", "5": "VDD_1V0_PHY", "4": "NC",
    }, comment="TLV75710PDBVR", MPN="TLV75710PDBVR")
    sh.column(13500, 5500, [
        ("C225", CAP, "VCC_3V3_SYS", "GND", "1uF 10V X5R 0402 (VPP LDO in, DNP)", {"DNP": "1"}),
        ("C226", CAP, "VPP_EFUSE_1V8", "GND", "2.2uF 10V X5R 0402 (VPP LDO out, DNP)", {"DNP": "1"}),
        ("R206", RES, "VPP_EFUSE_EN", "GND", "100k (keeps VPP off)"),
        ("C227", CAP, "VDD_1V8", "GND", "1uF 10V X5R 0402 (PHY LDO in)"),
        ("C228", CAP, "VDD_1V0_PHY", "GND", "1uF 10V X5R 0402 (PHY LDO out)"),
    ])
    sh.note(9000, 3200, "VPP_EFUSE_1V8 is the AM62x eFuse pin - never tie it to a permanent 1.8 V rail.")
    sh.note(9000, 3000, "VPP_EFUSE_EN: drive from a SoC GPIO only when programming eFuses.")
    return sh
