"""Sheet 10 - HDMI output: TFP410 DPI->DVI transmitter, TPD12S016 companion, HDMI-A receptacle.

References:
  * TI TFP410 datasheet SLDS145D: Table 4-1 (pins), Table 6-1 (interface modes),
    5.6 (latch timing), 7.2.2.3 / Figure 7-3 (supply decoupling), 7.3 (beads)
  * TI TPD12S016 datasheet SLLSE96F: pin table p.4, Table 1 (CT_HPD / LS_OE modes),
    8.2.2 / Figure 18 (two-GPIO control), 7.3.14 (port-A VILC)
  * TI SK-AM62B-P1 PROC142B p.43 (TPD12S016 bulk caps, HDMI connector, shell bead)
  * docs/research/bom/hdmi-audio-camera-wireless-expansion.md section 1

TFP410 in strap mode (ISEL = 0, no I2C). DVI only: no HDMI audio, CEC or infoframes.
"""
from schgen import Sheet
from symbols import CAP, FB, RES, TESTPOINT
from symlib.av import HDMI_A, TFP410, TPD12S016

C100N = "100nF 16V X7R 0402"
C10U = "10uF 10V X5R 0603"
BEAD = "BLM18KG601SN1D 600R@100MHz 1.3A 0603"
BEAD_P = {"MPN": "BLM18KG601SN1D", "Manufacturer": "Murata"}
TI = "Texas Instruments"

DVDD = "VCC_3V3_TFP_DVDD"
PVDD = "VCC_3V3_TFP_PVDD"
TVDD = "VCC_3V3_TFP_TVDD"


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/10_HDMI.SchDoc", "HDMI output (TFP410)", style=7)  # C size

    # ---- TFP410 part A: 24-bit pixel bus, clock, syncs, straps ------------
    a = {str(p.number): f"DPI_D{int(p.name[4:])}" for p in TFP410.pins
         if p.part == 1 and p.name.startswith("DATA")}
    a.update({
        "57": "TFP_IDCK", "56": "GND",                  # single-ended clock: IDCK- to GND
        "2": "DPI_DE", "4": "DPI_HSYNC", "5": "DPI_VSYNC",
        "13": "TFP_ISEL", "15": "TFP_BSEL", "14": "TFP_DSEL", "9": "TFP_EDGE", "35": "TFP_DKEN",
        "6": "GND", "7": "GND", "8": "GND",             # DK3 unused, CTL2/CTL1 low
        "3": DVDD,                                      # VREF = DVDD: 3.3 V high-swing input
        "10": "HDMI_PD_N", "11": "TP_HDMI_MSEN",
        "34": "GND",                                    # RESERVED: tie to GND
        "49": "NC",                                     # NC: no connection required
    })
    sh.add("U1000", TFP410, 2500, 16300, a, part=1, comment="TFP410PAPR",
           MPN="TFP410PAPR", Manufacturer=TI)

    # ---- TFP410 part B: supplies, DVI outputs, swing set ------------------
    sh.add("U1000", TFP410, 2200, 12600, {
        "1": DVDD, "12": DVDD, "33": DVDD, "18": PVDD, "23": TVDD, "29": TVDD,
        "16": "GND", "48": "GND", "64": "GND", "17": "GND",
        "20": "GND", "26": "GND", "32": "GND", "65": "GND",
        "25": "HDMI_TX0_P", "24": "HDMI_TX0_N", "28": "HDMI_TX1_P", "27": "HDMI_TX1_N",
        "31": "HDMI_TX2_P", "30": "HDMI_TX2_N", "22": "HDMI_TXC_P", "21": "HDMI_TXC_N",
        "19": "TFP_TFADJ",
    }, part=2, comment="TFP410PAPR", MPN="TFP410PAPR", Manufacturer=TI)

    # ---- straps (Table 6-1, ISEL = 0) and control pulls --------------------
    sh.column(6800, 16200, [
        ("R1000", RES, "DPI_PCLK", "TFP_IDCK", "22R 0402 (IDCK series, place at SoC ball T26)"),
        ("R1001", RES, "TFP_ISEL", "GND", "10k 0402 (ISEL=0: I2C off, strap mode)"),
        ("R1002", RES, "VCC_3V3_SYS", "TFP_BSEL", "10k 0402 (BSEL=1: 24-bit single edge)"),
        ("R1003", RES, "TFP_DSEL", "GND", "10k 0402 (DSEL=0: don't care at VREF=DVDD)"),
        ("R1004", RES, "TFP_EDGE", "GND", "10k 0402 (EDGE=0: latch on IDCK falling edge)"),
        ("R1005", RES, "TFP_DKEN", "GND", "10k 0402 (DKEN=0: de-skew off)"),
        ("R1006", RES, "HDMI_PD_N", "GND", "10k 0402 (TFP410 powered down in reset)"),
        ("R1007", RES, "VCC_3V3_SYS", "TP_HDMI_MSEN", "5.1k 0402 (MSEN open-drain pull-up, DS: 5k)"),
    ], pitch=300)
    sh.add("TP1000", TESTPOINT, 7400, 13500, {"1": "TP_HDMI_MSEN"}, comment="MSEN (receiver sense)")

    # ---- supply beads (Figure 7-3: one bead per supply) ---------------------
    sh.column(5700, 12500, [
        ("FB1000", FB, "VCC_3V3_SYS", DVDD, BEAD + " (DVDD)", BEAD_P),
        ("FB1001", FB, "VCC_3V3_SYS", PVDD, BEAD + " (PVDD)", BEAD_P),
        ("FB1002", FB, "VCC_3V3_SYS", TVDD, BEAD + " (TVDD)", BEAD_P),
        ("R1008", RES, TVDD, "TFP_TFADJ", "510R 1% 0402 (RTFADJ: 500 mV DVI swing)"),
    ], pitch=300)

    # ---- decoupling (Figure 7-3: 10 uF + 4 x 0.1 uF per supply) -------------
    n = 1000
    for x, rail, tag in ((9000, DVDD, "DVDD pins 1/12/33"), (11300, PVDD, "PVDD pin 18"),
                         (13600, TVDD, "TVDD pins 23/29")):
        entries = [(f"C{n}", CAP, rail, "GND", f"{C10U} ({tag})")]
        entries += [(f"C{n + i}", CAP, rail, "GND", f"{C100N} ({tag})") for i in range(1, 5)]
        n += 5
        sh.column(x, 12500, entries, pitch=300)

    # ---- TPD12S016: 5 V switch, DDC/HPD/CEC level shift, ESD -----------------
    sh.add("U1001", TPD12S016, 10000, 16300, {
        "24": "VCC_3V3_SYS", "11": "VCC_5V0",
        "12": "HDMI_CT_CP_HPD", "5": "HDMI_LS_OE",
        "2": "I2C1_SCL", "3": "I2C1_SDA", "4": "HDMI_HPD", "1": "TP_HDMI_CEC_A",
        "6": "GND", "14": "GND", "19": "GND",
        "13": "VCC_5V0_HDMI",
        "8": "HDMI_DDC_SCL", "9": "HDMI_DDC_SDA", "10": "HDMI_CONN_HPD", "7": "HDMI_CONN_CEC",
        "23": "HDMI_TX2_P", "22": "HDMI_TX2_N", "21": "HDMI_TX1_P", "20": "HDMI_TX1_N",
        "18": "HDMI_TX0_P", "17": "HDMI_TX0_N", "16": "HDMI_TXC_P", "15": "HDMI_TXC_N",
    }, comment="TPD12S016PWR", MPN="TPD12S016PWR", Manufacturer=TI)
    sh.add("TP1001", TESTPOINT, 14000, 14500, {"1": "TP_HDMI_CEC_A"}, comment="CEC_A (unused, 10k internal pull-up)")

    sh.column(15800, 12500, [
        ("C1015", CAP, "VCC_3V3_SYS", "GND", C100N + " (TPD VCCA)"),
        ("C1016", CAP, "VCC_3V3_SYS", "GND", C10U + " (TPD VCCA bulk, SK)"),
        ("C1017", CAP, "VCC_5V0", "GND", C100N + " (TPD VCC5V)"),
        ("C1018", CAP, "VCC_5V0", "GND", C10U + " (TPD VCC5V bulk, SK)"),
        ("C1019", CAP, "VCC_5V0_HDMI", "GND", C100N + " (5V_OUT)"),
        ("C1020", CAP, "VCC_5V0_HDMI", "GND", C10U + " (5V_OUT bulk, SK)"),
    ], pitch=300)
    sh.column(19000, 12500, [
        ("R1009", RES, "HDMI_CT_CP_HPD", "GND", "10k 0402 (5 V switch + HPD off in reset)"),
        ("R1010", RES, "HDMI_LS_OE", "GND", "10k 0402 (DDC level shifter off in reset)"),
        ("R1011", RES, "HDMI_HPD", "GND", "100k 0402 (defines HPD while CT_HPD = 0)"),
    ], pitch=300)

    # ---- HDMI type-A receptacle --------------------------------------------
    sh.add("J1000", HDMI_A, 15500, 16300, {
        "1": "HDMI_TX2_P", "2": "GND", "3": "HDMI_TX2_N",
        "4": "HDMI_TX1_P", "5": "GND", "6": "HDMI_TX1_N",
        "7": "HDMI_TX0_P", "8": "GND", "9": "HDMI_TX0_N",
        "10": "HDMI_TXC_P", "11": "GND", "12": "HDMI_TXC_N",
        "13": "HDMI_CONN_CEC", "14": "NC",          # Utility/HEAC+: not used by a DVI source (SK: NC)
        "15": "HDMI_DDC_SCL", "16": "HDMI_DDC_SDA", "17": "GND",
        "18": "VCC_5V0_HDMI", "19": "HDMI_CONN_HPD",
        "20": "HDMI_SHELL", "21": "HDMI_SHELL", "22": "HDMI_SHELL", "23": "HDMI_SHELL",
    }, comment="HDMI-A-19F-S-D", MPN="HDMI-A-19F-S-D", Manufacturer="XFCN")
    sh.column(17500, 13700, [
        ("FB1003", FB, "HDMI_SHELL", "GND", "BLM18PG121SN1D 120R@100MHz 0603 (shell to GND, SK FL17)",
         {"MPN": "BLM18PG121SN1D", "Manufacturer": "Murata"}),
    ])

    # ---- notes --------------------------------------------------------------
    notes = [
        "TFP410 strap mode (ISEL=0): BSEL=1 24-bit single-edge | DSEL=0 (X at VREF=DVDD) | EDGE=0 latch on IDCK falling edge | DKEN=0 | VREF=DVDD (3.3 V swing)",
        "EDGE=0 matches the ti-tfp410 driver default (no pclk-sample in DT = sample on negedge): tidss then drives data on the rising edge (IPC=0).",
        "IDCK- tied to GND (single-ended clock). DK3 unused, CTL2/CTL1 tied low. RESERVED to GND. NC pin 49 open. PD# = HDMI_PD_N (10k pull-down).",
        "DT: tidss VP2 (DPI, RGB888) -> ti,tfp410 (powerdown-gpios = HDMI_PD_N) -> hdmi-connector type a (ddc-i2c-bus = main_i2c1, hpd-gpios = HDMI_HPD).",
        "TPD12S016: CT_HPD and LS_OE are separate SoC GPIOs with 10k pull-downs. Set CT_HPD first (5 V + HPD), LS_OE before EDID reads.",
        "DDC A-side = I2C1 (pull-ups 2.2k on sheet 11; TPD A-side adds 10k internal). Port A only passes a LOW below VILC = 0.065*VCCA (0.21 V): no series R here.",
        "Layout: TMDS 100R diff, length-matched, flow-through over the TPD12S016 pads next to J1000. TFP410 PowerPAD (pin 65) to GND with via array (0.8 W).",
        "Layout: DPI bus length-matched to DPI_PCLK, R1000 at the SoC ball. Each TFP410 supply on its own bead and pour; 100 nF caps at the pins.",
        "Shell: HDMI_SHELL to GND through FB1003 (SK practice). DPI_D16..23 also carry the BOOTMODE[15:8] 10k straps (sheet 06); TFP410 input leakage <= 25 uA.",
    ]
    for i, t in enumerate(notes):
        sh.note(1000, 9600 - i * 220, t)
    return sh
