"""Sheet 02 - PMIC (TPS6521904RSMR), 3.3 V IO load switch, eFuse VPP LDO, PHY 1.0 V LDO.

References:
  * TI SK-AM62B-P1 PROC142B schematic p.12-13 (same PMIC OPN and rail map)
  * datasheets/tps65219.pdf Table 5-1 (pins), section 8.2.3 (external parts)
  * docs/research/am625-tps65219-constraints.md section B.3 (capacitance limits)

Rail map (TPS6521904 NVM, VSYS = 3.3 V), checked against TI SLVUCL1A (TPS6521904 TRM,
Tables 2-2..2-9 and section 2.6):
  slot 0 (10 ms)  GPO2 -> EN_3V3_SYS (TPS22965 -> VCC_3V3_SYS)
  slot 2 (3 ms)   Buck2 1.8 V  -> VDD_1V8
                  LDO1 3.3 V bypass, 1.8 V LDO when VSEL_SD is low -> VDD_SDIO_LDO1 (SD dual switch)
                  LDO3 1.8 V LDO, slow ramp (total C <= 30 uF) -> VDDA_1V8 (beads on sheet 03)
                  LDO4 2.5 V LDO, slow ramp (total C <= 30 uF) -> DDR4_VPP_2V5 (SiP DDR_VPP + PHY 2.5 V)
  slot 3 (1.5 ms) Buck3 1.2 V  -> VDDS_DDR_1V2 (SiP DDR IO + internal DDR4 VDD/VDDQ)
  slot 4 (1.5 ms) Buck1 0.85 V -> VDD_CORE_0V85 (SiP VDD_CORE + VDDR_CORE, same source)
  slot 5          LDO2 1.8 V bypass from VDD_1V8 (enabled, output only on TP204)
  slot 8          nRSTOUT (PMIC_PGOOD) high, ~13 ms after the last rail is enabled
  Power-down: Buck3, LDO2, nRSTOUT first; 10 ms later all other rails and GPO2.
  Bucks quasi-fixed frequency, high bandwidth (COUT 30-220 uF, datasheet Table 8-1).
  GPO1 and GPIO disabled (output low): left on test points.
  EN/PB/VSENSE = push button with first-supply detection: powers up when VCC_3V3_MAIN appears.
  VSEL_SD polarity: low = 1.8 V, high = LDO1_VSET (3.3 V); pulled up so SD starts at 3.3 V.
  MODE/STBY = MODE and STBY, low = STBY + auto-PFM, high = ACTIVE + forced PWM.
  MODE/RESET = WARM reset, low = reset. Both pins have only a ~25 nA internal pull-down
  (datasheet 9.1.8) and must be set externally (datasheet Table 8-4).
"""
from schgen import Sheet
from symbols import CAP, IND, RES, TESTPOINT, TLV755P, TPS22965, TPS65219, TVS_BI
from symlib.clock_reset import TS1187A

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
        "25": "PMIC_PB_N", "28": "PMIC_MODE_RESET", "31": "PMIC_STBY",
        "12": "SD_VSEL",
        "9": "I2C0_SDA_BUS", "10": "I2C0_SCL_BUS",
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

    # ---- buck inductors (0.47 uH, DCR <= 50 mOhm; datasheet 8.2.3.1 asks Isat >= 7.4 A B1 /
    #      5.4 A B2-B3). DFE252012F-R47M: Isat 6.7 A, Itemp 4.9 A, DCR 23 mOhm max - below the
    #      7.4 A wish for Buck1 (peak limit 6.9 A max), above the SK's DFE201612E (4.5 A). ----
    sh.column(11000, 13900, [
        ("L200", IND, "PMIC_LX_B1", "VDD_CORE_0V85", "0.47uH DFE252012F-R47M (Buck1, Isat 6.7A)", {"MPN": "DFE252012F-R47M=P2", "Manufacturer": "Murata"}),
        ("L201", IND, "PMIC_LX_B2", "VDD_1V8", "0.47uH DFE252012F-R47M (Buck2)", {"MPN": "DFE252012F-R47M=P2", "Manufacturer": "Murata"}),
        ("L202", IND, "PMIC_LX_B3", "VDDS_DDR_1V2", "0.47uH DFE252012F-R47M (Buck3)", {"MPN": "DFE252012F-R47M=P2", "Manufacturer": "Murata"}),
    ], pitch=500)

    # ---- buck and LDO output capacitors (FB senses at these local caps) ----
    sh.column(14000, 13900, [
        ("C210", CAP, "VDD_CORE_0V85", "GND", C0805_22U + " (Buck1 out)"),
        ("C211", CAP, "VDD_CORE_0V85", "GND", C0805_22U + " (Buck1 out)"),
        ("C212", CAP, "VDD_1V8", "GND", C0805_22U + " (Buck2 out)"),
        ("C213", CAP, "VDD_1V8", "GND", C0805_22U + " (Buck2 out)"),
        ("C214", CAP, "VDDS_DDR_1V2", "GND", C0805_22U + " (Buck3 out)"),
        ("C215", CAP, "VDDS_DDR_1V2", "GND", C0805_22U + " (Buck3 out)"),
    ])
    sh.column(17000, 13900, [
        ("C216", CAP, "VDD_SDIO_LDO1", "GND", C0402_2U2 + " (LDO1 out)"),
        ("C217", CAP, "VDD_LDO2", "GND", C0402_2U2 + " (LDO2 out, unused)"),
        ("C218", CAP, "VDDA_1V8", "GND", C0402_2U2 + " (LDO3 out)"),
        ("C219", CAP, "DDR4_VPP_2V5", "GND", C0402_2U2 + " (LDO4 out)"),
    ])
    sh.note(13500, 14600, "FB_B1/B2/B3 route as traces to the local output caps (no remote sense)")
    sh.note(13500, 14400, "Total C incl. point of load and SiP-internal caps: LDO1/2 (bypass) <= 50uF, LDO3/4 (slow ramp) <= 30uF")

    # ---- control pull-ups, interrupt slew limiter, push button ----
    sh.column(2500, 9500, [
        ("R200", RES, "VCC_3V3_MAIN", "PMIC_PB_N", "10k 0402"),
        ("R201", RES, "VCC_3V3_MAIN", "PMIC_PGOOD", "2.2k 0402 (fast edge into the MCU_PORz gate, sheet 06)"),
        ("R202", RES, "VCC_3V3_SYS", "PMIC_INT_N", "10k 0402"),
        ("R203", RES, "PMIC_INT_N", "PMIC_NINT", "62R 0402 (slew limiter, SK rev B)"),
        ("C220", CAP, "PMIC_NINT", "GND", "47pF 50V C0G 0402"),
        ("R204", RES, "VCC_3V3_SYS", "SD_VSEL", "10k 0402 (SD starts at 3.3 V)"),
        ("R205", RES, "VCC_3V3_MAIN", "EN_3V3_SYS", "10k 0402 (GPO2 is open drain)"),
        ("D200", TVS_BI, "PMIC_PB_N", "GND", "TPD1E10B06 ESD"),
        ("R207", RES, "PMIC_LPM_EN0", "PMIC_STBY", "0R 0402 DNP (SoC low-power control; SK removed this link)",
         {"DNP": "1"}),
        ("R208", RES, "VCC_3V3_SYS", "PMIC_STBY", "10k 0402 (MODE/STBY high = ACTIVE + forced PWM, SK R621)"),
        ("R209", RES, "VCC_3V3_MAIN", "PMIC_MODE_RESET", "10k 0402 (MODE/RESET high = no reset)"),
        ("R210", RES, "VCC_3V3_SYS", "PMIC_LPM_EN0", "10k 0402 (Octavo 62_CONFIG_9 pull-up)"),
    ])
    sh.add("SW200", TS1187A, 6000, 6300, {"1": "PMIC_PB_N", "2": "PMIC_PB_N", "3": "GND", "4": "GND"},
           comment="TS-1187A-B-A-B (POWER)", MPN="TS-1187A-B-A-B", Manufacturer="XKB Connection")
    sh.add("TP200", TESTPOINT, 6000, 8500, {"1": "PMIC_MODE_RESET"}, comment="MODE/RESET")
    sh.add("TP201", TESTPOINT, 6000, 8100, {"1": "PMIC_STBY"}, comment="MODE/STBY")
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
    }, comment="TLV75518PDBVR (DNP)", MPN="TLV75518PDBVR", Manufacturer="Texas Instruments", DNP="1")
    # TLV757P (1 A) has the TLV755P DBV pinout: 1 IN, 2 GND, 3 EN, 4 NC, 5 OUT
    # (ti.com/lit/ds/symlink/tlv757p.pdf Table 4-1), so it shares the TLV755P_DBV symbol.
    sh.add("U203", TLV755P, 9500, 4300, {
        "1": "VDD_1V8", "3": "VDD_1V8", "2": "GND", "5": "VDD_1V0_PHY", "4": "NC",
    }, comment="TLV75710PDBVR", MPN="TLV75710PDBVR", Manufacturer="Texas Instruments")
    sh.column(13500, 5500, [
        ("C225", CAP, "VCC_3V3_SYS", "GND", "1uF 10V X5R 0402 (VPP LDO in, DNP)", {"DNP": "1"}),
        ("C226", CAP, "VPP_EFUSE_1V8", "GND", "2.2uF 10V X5R 0402 (VPP LDO out, DNP)", {"DNP": "1"}),
        ("R206", RES, "VPP_EFUSE_EN", "GND", "100k 0402 (keeps VPP off)"),
        ("C227", CAP, "VDD_1V8", "GND", "1uF 10V X5R 0402 (PHY LDO in)"),
        ("C228", CAP, "VDD_1V0_PHY", "GND", "1uF 10V X5R 0402 (PHY LDO out)"),
    ])
    sh.note(9000, 3200, "VPP_EFUSE_1V8 is the AM62x eFuse pin - never tie it to a permanent 1.8 V rail.")
    sh.note(9000, 3000, "VPP_EFUSE_EN: drive from a SoC GPIO only when programming eFuses.")
    return sh
