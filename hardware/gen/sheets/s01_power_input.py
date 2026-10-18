"""Sheet 01 - USB-C #1 power input: receptacle, VBUS/CC protection, TPS25730D
USB-PD sink, LM61460 3.3 V always-on buck, TPS63070 5 V buck-boost.

References (datasheets downloaded 2026-10-17; see symlib/power_input.py):
  * TPS25730 SLVSGP9 (ti.com/lit/ds/symlink/tps25730.pdf): 6.4 Recommended
    Capacitance (p.9-10), 8.3.6 / Table 8-1 ADCIN decoding (p.31), Table 8-3
    configuration + I2C address (p.35), Tables 8-4/8-5/8-6 (p.36-37), 8.5
    Schottky (p.39), Figure 9-3 example schematic (p.42), 9.4.1.3 layout (p.48).
  * LM61460 SNVSBD5D: 8.3.4 Equation 2 (RT), 9.2 Table 9-2 / 9-3 (p.29-31),
    9.2.2.5-9.2.2.11 (p.32-33).
  * TPS63070 SLVSC58B: 7.3 ROC (p.4), 8.4.2/8.4.3 EN and PG (p.11), Figure 10 and
    Tables 2-6 (p.16-19).
  * docs/research/bom/power.md sections 1-2, docs/bom/APE-SBC_BOM_estimate.csv (group Power).

Power path:
  USB-C VBUS (VBUS_USBC, 5 V implicit or 9 V PD) -> TPS25730D PPHV switch
  (OVP/RCP, 16 mOhm) -> VSYS_PD -> LM61460 -> VCC_3V3_MAIN (always on)
                                -> TPS63070 -> VCC_5V0 (EN from VCC_3V3_MAIN)

TPS25730D straps (Table 8-1 decode windows, DIV = Rdown / (Rup + Rdown)):
  ADCIN1 = GND                       -> decoded 0 -> min voltage 5 V (Table 8-4)
  ADCIN2 = 100k to LDO_3V3 / 4.99k   -> DIV 4.99/104.99 = 0.0475 (window
           to GND (1 %)                 0.0229-0.0722; worst case 1 % = 0.0466-0.0484)
                                     -> decoded 1 -> max voltage 9 V (Table 8-5)
  Table 8-3: ADCIN1 = 0 / ADCIN2 = 1 -> I2C target address 0x20, dead-battery
           mode AlwaysEnableSink (path closes on plain 5 V sources too).
  ADCIN3 = 100k / 4.99k (same divider) -> decoded 1
  ADCIN4 = LDO_1V5 ("tie to LDO_1V5")  -> decoded 5
           Table 8-6 row (1, 5): operating current 1.5 A, maximum current 3 A.
  RESERVED 26/27/36: "tie to ground or LDO_3V3" - 10k to GND each (as Figure 9-3).
  If a TPS25730ADREFR is fitted instead (EnableSinkAfterContract), change ADCIN3
  to GND (decoded 0) and ADCIN4 stays at LDO_1V5 -> 0.5 A operating / 3 A max
  (power.md section 1).
"""
from schgen import Sheet
from symbols import CAP, DIODE, IND, RES, TESTPOINT, TVS_BI
from symlib.power_input import LM61460, TPS25730D, TPS63070, TVS2200, TYPE_C_31_M_12

C330P = "330pF 50V C0G 0402"
C4P7 = "4.7pF 50V C0G 0402"
C100N_16 = "100nF 16V X7R 0402"
C100N_50 = "100nF 50V X7R 0603"
C1U_25 = "1uF 25V X5R 0402"
C10U_10 = "10uF 10V X5R 0603"
C10U_25 = "10uF 25V X5R 0805"
C10U_50 = "10uF 50V X5R 1206"
C22U_25 = "22uF 25V X5R 1206"
C47U_10 = "47uF 10V X5R 1206"

P_C10U_10 = {"MPN": "CL10A106KP8NNNC", "Manufacturer": "Samsung"}
P_C10U_25 = {"MPN": "CL21A106KAYNNNE", "Manufacturer": "Samsung"}
P_C10U_50 = {"MPN": "CL31A106KBHNNNE", "Manufacturer": "Samsung"}
P_C22U_25 = {"MPN": "CL31A226KAHNNNE", "Manufacturer": "Samsung"}
P_C47U_10 = {"MPN": "CL31A476MPHNNNE", "Manufacturer": "Samsung"}
P_C100N_50 = {"MPN": "CC0603KRX7R9BB104", "Manufacturer": "YAGEO"}


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/01_Power_Input.SchDoc", "USB-C power input and main converters", style=7)

    # ================================================================ USB-C #1
    sh.add("J100", TYPE_C_31_M_12, 1500, 16200, {
        "A1B12": "GND", "B1A12": "GND",
        "S1": "GND", "S2": "GND", "S3": "GND", "S4": "GND",
        "A4B9": "VBUS_USBC", "B4A9": "VBUS_USBC",
        "A5": "USBC1_CC1", "B5": "USBC1_CC2",
        "A6": "USBC1_DP", "B6": "USBC1_DP",      # both rows tied: plug works either way up
        "A7": "USBC1_DM", "B7": "USBC1_DM",
        "A8": "NC", "B8": "NC",                  # SBU unused for a USB 2.0 sink/device port
    }, comment="TYPE-C-31-M-12", MPN="TYPE-C-31-M-12", Manufacturer="Korean Hroparts Elec")
    sh.note(500, 12600, "J100 shell pegs S1-S4 go straight to GND (single-ground board; ESD returns via the plane). No RC.")
    sh.note(500, 12400, "USBC1_DP/DM: 90 Ohm diff pair to sheet 09 (CMC + ESD122 there). Tie DP1/DP2 and DN1/DN2 at the pads, stubs < 3 mm.")

    # ---- VBUS clamp, surge Schottky, VBUS caps (CVBUS 1-10 uF, DS 6.4) ----
    sh.add("D100", TVS2200, 1700, 13800, {
        "4": "VBUS_USBC", "5": "VBUS_USBC", "6": "VBUS_USBC",
        "1": "GND", "2": "GND", "3": "GND", "7": "GND",
    }, comment="TVS2200DRVR", MPN="TVS2200DRVR", Manufacturer="Texas Instruments")
    sh.column(4900, 16100, [
        ("D103", DIODE, "GND", "VBUS_USBC", "SS34 40V 3A Schottky (TPS25730 DS 8.5)",
         {"MPN": "SS34", "Manufacturer": "MDD"}),
        ("C100", CAP, "VBUS_USBC", "GND", C10U_25 + " (CVBUS)", P_C10U_25),
        ("C101", CAP, "VBUS_USBC", "GND", C100N_50 + " (VBUS HF)", P_C100N_50),
        ("D101", TVS_BI, "USBC1_CC1", "GND", "PESD24VL1BA CC1 ESD (11pF)",
         {"MPN": "PESD24VL1BA,115", "Manufacturer": "Nexperia"}),
        ("D102", TVS_BI, "USBC1_CC2", "GND", "PESD24VL1BA CC2 ESD (11pF)",
         {"MPN": "PESD24VL1BA,115", "Manufacturer": "Nexperia"}),
        ("C102", CAP, "USBC1_CC1", "GND", C330P + " (CCCy)"),
        ("C103", CAP, "USBC1_CC2", "GND", C330P + " (CCCy)"),
    ])
    sh.note(500, 12200, "D100/D103 at the receptacle VBUS pins. CC: 330pF + 11pF ESD = ~341pF per pin (DS 6.4: 200-480pF).")
    sh.note(500, 12000, "C102/C103 on the same layer as U100, next to CC1/CC2; no via between pin and cap (DS 9.4.1.3).")

    # ================================================================ TPS25730D
    sh.add("U100", TPS25730D, 7500, 16200, {
        "23": "VBUS_USBC", "24": "VBUS_USBC", "25": "VBUS_USBC",
        "32": "VBUS_USBC", "33": "VBUS_USBC",       # DS 6.3 note 2: all VBUS/VBUS_IN shorted
        "38": "VCC_3V3_MAIN", "1": "PD_LDO_3V3", "4": "PD_LDO_1V5",
        "2": "GND", "3": "PD_ADCIN2", "5": "PD_ADCIN3", "7": "PD_LDO_1V5",
        "26": "PD_RSVD26", "27": "PD_RSVD27", "36": "PD_RSVD36",
        "11": "GND", "12": "GND", "14": "GND", "16": "GND", "17": "GND",
        "31": "GND", "34": "GND", "35": "GND", "39": "GND",
        "20": "VSYS_PD", "21": "VSYS_PD", "22": "VSYS_PD",
        "15": "PD_DRAIN", "30": "PD_DRAIN", "40": "PD_DRAIN",
        "28": "USBC1_CC1", "29": "USBC1_CC2",
        "9": "I2C0_SCL", "8": "I2C0_SDA",
        "18": "PD_FAULT_IN_N", "19": "TP_PD_SINK_EN_N", "6": "PD_INT_N",
        "37": "TP_PD_PLUG_EVT", "13": "TP_PD_PLUG_FLIP", "10": "TP_PD_DBG_ACC",
    }, comment="TPS25730DREFR", MPN="TPS25730DREFR", Manufacturer="Texas Instruments")
    sh.note(500, 11800, "U100: VIN_3V3 from VCC_3V3_MAIN; until the host clears the dead-battery flag it runs from its VBUS LDO (DS 8.3.2).")
    sh.note(500, 11600, "PD_DRAIN (pins 15/30/40): thermal copper only - connect to nothing else (DS 9.4.1.3).")
    sh.note(500, 11400, "I2C0 target address 0x20 (ADCIN1=0, ADCIN2=1, Table 8-3). Pull-ups on sheet 16. Addr collides with TCA64xx defaults.")
    sh.note(11000, 12600, "PD_INT_N = CAP_MIS (open drain, toggles while the PD contract has a capability mismatch); no IRQ pin exists.")
    sh.note(11000, 12400, "VSYS_PD total C (CPPHV) must stay <= 100uF nominal: now 2x22 + 4x10 + 3x0.1 = 84.3uF. No electrolytics.")

    # LDO, strap, reserved and status passives (DS 6.4 and Figure 9-3)
    sh.column(11800, 16100, [
        ("C104", CAP, "VCC_3V3_MAIN", "GND", C10U_10 + " (CVIN_3V3)", P_C10U_10),
        ("C105", CAP, "PD_LDO_3V3", "GND", C10U_10 + " (CLDO_3V3 5-25uF)", P_C10U_10),
        ("C106", CAP, "PD_LDO_1V5", "GND", C10U_10 + " (CLDO_1V5 4.5-12uF)", P_C10U_10),
        ("R100", RES, "PD_LDO_3V3", "PD_ADCIN2", "100k 1% 0402 (ADCIN2 up)"),
        ("R101", RES, "PD_ADCIN2", "GND", "4.99k 1% 0402 (ADCIN2 dn: max 9V)"),
        ("R102", RES, "PD_LDO_3V3", "PD_ADCIN3", "100k 1% 0402 (ADCIN3 up)"),
        ("R103", RES, "PD_ADCIN3", "GND", "4.99k 1% 0402 (ADCIN3 dn: 1.5A op)"),
        ("R104", RES, "PD_RSVD26", "GND", "10k 1% 0402 (RESERVED)"),
        ("R105", RES, "PD_RSVD27", "GND", "10k 1% 0402 (RESERVED)"),
    ])
    sh.column(14700, 16100, [
        ("R106", RES, "PD_RSVD36", "GND", "10k 1% 0402 (RESERVED)"),
        ("R107", RES, "PD_LDO_3V3", "PD_FAULT_IN_N", "10k 1% 0402 (FAULT_IN high = no fault)"),
        ("R108", RES, "VCC_3V3_SYS", "PD_INT_N", "10k 1% 0402 (SoC-side pull-up)"),
        ("R109", RES, "PD_LDO_3V3", "TP_PD_SINK_EN_N", "100k 1% 0402"),
        ("R110", RES, "PD_LDO_3V3", "TP_PD_PLUG_EVT", "100k 1% 0402"),
        ("R111", RES, "PD_LDO_3V3", "TP_PD_PLUG_FLIP", "100k 1% 0402"),
        ("R112", RES, "PD_LDO_3V3", "TP_PD_DBG_ACC", "100k 1% 0402"),
        ("C107", CAP, "VSYS_PD", "GND", C22U_25 + " (CPPHV bulk)", P_C22U_25),
        ("C108", CAP, "VSYS_PD", "GND", C22U_25 + " (CPPHV bulk)", P_C22U_25),
    ])
    sh.add("TP100", TESTPOINT, 19000, 16100, {"1": "TP_PD_SINK_EN_N"}, comment="SINK_EN# (low = sink path on)")
    sh.add("TP101", TESTPOINT, 19000, 15700, {"1": "TP_PD_PLUG_EVT"}, comment="PLUG_EVENT")
    sh.add("TP102", TESTPOINT, 19000, 15300, {"1": "TP_PD_PLUG_FLIP"}, comment="PLUG_FLIP")
    sh.add("TP103", TESTPOINT, 19000, 14900, {"1": "TP_PD_DBG_ACC"}, comment="DBG_ACC")
    sh.note(11000, 12200, "LDO_3V3 load: 2 dividers (2x31uA) + 4x100k pull-ups (<=4x33uA) << 1mA allowed.")
    sh.note(11000, 12000, "C106: 10uF 0603 instead of 4.7uF 0402 so >=4.5uF remains after tolerance + DC bias.")

    # ================================================================ LM61460 3.3 V
    sh.add("U101", LM61460, 3500, 10900, {
        "8": "VSYS_PD", "12": "VSYS_PD",
        "7": "LM_EN", "6": "LM_RT",
        "1": "VCC_3V3_MAIN", "2": "LM_VCC",
        "3": "GND", "9": "GND", "11": "GND",
        "10": "LM_SW", "14": "LM_CBOOT", "13": "LM_RBOOT",
        "4": "LM_FB", "5": "TP_3V3_PG",
    }, comment="LM61460AANRJRR", MPN="LM61460AANRJRR", Manufacturer="Texas Instruments")
    sh.column(6900, 10800, [
        ("C109", CAP, "VSYS_PD", "GND", C10U_50 + " (VIN1/PGND1)", P_C10U_50),
        ("C110", CAP, "VSYS_PD", "GND", C100N_50 + " (VIN1/PGND1 HF)", P_C100N_50),
        ("C111", CAP, "VSYS_PD", "GND", C10U_50 + " (VIN2/PGND2)", P_C10U_50),
        ("C112", CAP, "VSYS_PD", "GND", C100N_50 + " (VIN2/PGND2 HF)", P_C100N_50),
        ("R113", RES, "VSYS_PD", "LM_EN", "100k 1% 0402 (RENT)"),
        ("R114", RES, "LM_EN", "GND", "43.2k 1% 0402 (RENB: UVLO on 4.19V, off 3.0V)"),
        ("R115", RES, "LM_RT", "GND", "33.2k 1% 0402 (RT: 400kHz)"),
        ("C113", CAP, "LM_VCC", "GND", C1U_25 + " (VCC)"),
        ("C114", CAP, "VCC_3V3_MAIN", "GND", C100N_16 + " (at BIAS pin)"),
        ("C115", CAP, "LM_SW", "LM_CBOOT", C100N_16 + " (CBOOT)"),
        ("R116", RES, "LM_RBOOT", "LM_CBOOT", "0R 0402 (RBOOT; 100R option for EMI)"),
    ])
    sh.column(10300, 10800, [
        ("L100", IND, "LM_SW", "VCC_3V3_MAIN", "4.7uH MWSA0603S-4R7MT (Isat 9A, 33mOhm)",
         {"MPN": "MWSA0603S-4R7MT", "Manufacturer": "Sunlord"}),
        ("R117", RES, "VCC_3V3_MAIN", "LM_FB", "100k 1% 0402 (RFBT)"),
        ("R118", RES, "LM_FB", "GND", "43.2k 1% 0402 (RFBB: 3.315V)"),
        ("R119", RES, "VCC_3V3_MAIN", "LM_FF", "1k 1% 0402 (RFF)"),
        ("C116", CAP, "LM_FF", "LM_FB", C4P7 + " (CFF)"),
        ("R120", RES, "VCC_3V3_MAIN", "TP_3V3_PG", "100k 1% 0402 (PGOOD pull-up)"),
        ("C117", CAP, "VCC_3V3_MAIN", "GND", C47U_10 + " (COUT)", P_C47U_10),
        ("C118", CAP, "VCC_3V3_MAIN", "GND", C47U_10 + " (COUT)", P_C47U_10),
        ("C119", CAP, "VCC_3V3_MAIN", "GND", C47U_10 + " (COUT)", P_C47U_10),
        ("C120", CAP, "VCC_3V3_MAIN", "GND", C47U_10 + " (COUT)", P_C47U_10),
    ], pitch=400)
    sh.add("TP104", TESTPOINT, 4500, 8900, {"1": "TP_3V3_PG"}, comment="3V3_MAIN PGOOD")
    sh.note(500, 6400, "LM61460 at 400 kHz (RT = (1/400 - 3.3e-5) x 1.346e4 = 33.2k, DS Eq.2): DS Table 9-2 row for 3.3V/4.7uH/3x47uF,")
    sh.note(500, 6200, "  below the AM band, lowest switching loss for ~2W dissipation at 9V/5A; on-time 0.9us at 9V, off-time ok at 4.4V in.")
    sh.note(500, 6000, "  4x47uF 10V X5R ~= TI's 3x47uF 16V X7R after DC bias, so CFF 4.7pF + RFF 1k per Table 9-2/9-3.")
    sh.note(500, 5800, "  Vout = 1.0V x (1 + 100k/43.2k) = 3.315V (DS Eq.3). EN UVLO: Von = 1.263V x (1 + 100k/43.2k) = 4.19V, Voff = 0.72 x Von.")
    sh.note(500, 5600, "  BIAS tied to the 3.3V output (Vout < 12V, DS 9.2.2.9). Split input caps: one 10uF + 100nF per VIN/PGND pair.")

    # ================================================================ TPS63070 5 V
    sh.add("U102", TPS63070, 14000, 10900, {
        "12": "VSYS_PD", "13": "VSYS_PD",
        "14": "EN_5V0", "1": "BB_PS_SYNC", "15": "GND", "3": "BB_VAUX",
        "4": "GND", "10": "GND",
        "11": "BB_L1", "9": "BB_L2",
        "7": "VCC_5V0", "8": "VCC_5V0",
        "5": "BB_FB", "6": "GND", "2": "TP_5V0_PG",
    }, comment="TPS63070RNMR", MPN="TPS63070RNMR", Manufacturer="Texas Instruments")
    sh.column(17000, 10800, [
        ("C121", CAP, "VSYS_PD", "GND", C10U_25 + " (CIN)", P_C10U_25),
        ("C122", CAP, "VSYS_PD", "GND", C10U_25 + " (CIN)", P_C10U_25),
        ("C123", CAP, "VSYS_PD", "GND", C100N_50 + " (VIN HF, at pins)", P_C100N_50),
        ("R121", RES, "VCC_3V3_MAIN", "EN_5V0", "100k 1% 0402 (EN: on with 3V3_MAIN)"),
        ("R122", RES, "VCC_3V3_MAIN", "BB_PS_SYNC", "100k 1% 0402 (PS high: power save)"),
        ("C124", CAP, "BB_VAUX", "GND", C100N_16 + " (VAUX)"),
        ("L101", IND, "BB_L1", "BB_L2", "1.5uH MWSA0402S-1R5MT (Isat 5.5A)",
         {"MPN": "MWSA0402S-1R5MT", "Manufacturer": "Sunlord"}),
    ])
    sh.column(19700, 10800, [
        ("R123", RES, "VCC_5V0", "BB_FB", "680k 1% 0402 (R1)"),
        ("R124", RES, "BB_FB", "GND", "130k 1% 0402 (R2: 4.985V)"),
        ("R125", RES, "VCC_5V0", "TP_5V0_PG", "100k 1% 0402 (PG pull-up)"),
        ("C125", CAP, "VCC_5V0", "GND", C22U_25 + " (COUT)", P_C22U_25),
        ("C126", CAP, "VCC_5V0", "GND", C22U_25 + " (COUT)", P_C22U_25),
        ("C127", CAP, "VCC_5V0", "GND", C22U_25 + " (COUT)", P_C22U_25),
        ("C128", CAP, "VCC_5V0", "GND", C10U_10 + " (VOUT bypass at pins)", P_C10U_10),
    ])
    sh.add("TP105", TESTPOINT, 15000, 8900, {"1": "TP_5V0_PG"}, comment="5V0 PG")
    sh.note(13000, 6400, "TPS63070: Vout = 0.8V x (1 + R1/R2) = 0.8 x (1 + 680k/130k) = 4.985V (DS Eq.6, Table 4; SK uses 680k).")
    sh.note(13000, 6200, "  VSEL and FB2 to GND (unused, DS Fig.10). EN pulled to VCC_3V3_MAIN (as SK) so 5V follows 3V3_MAIN.")
    sh.note(13000, 6000, "  PS/SYNC high = PFM power save at light load; fit R122 to GND instead for forced PWM.")
    sh.note(13000, 5800, "  Total VCC_5V0 capacitance incl. sheet 09 USB-A bulk must stay within 15-470uF effective (DS 7.3).")
    sh.note(13000, 5600, "  VIN max 16V: never strap the PD maximum above 9V while U102 is a TPS63070 (power.md risk 4).")
    return sh
