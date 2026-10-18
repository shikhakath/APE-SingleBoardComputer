"""Sheet 11 - audio: TLV320AIC3104 codec, 12.288 MHz MCLK oscillator, TRRS headset jack, I2C1 pull-ups.

References:
  * TI TLV320AIC3104 datasheet SLAS510G: Table 7-1 (pins), Figure 11-1/11-4 (typical
    connections and supply decoupling), Figure 10-19 (headset detection with AC-coupled
    headphones), section 12 (supply sequencing), 10.5.1 (I2C address 0x18)
  * TI SK-AM62B-P1 PROC142B p.42 (AIC3106 hookup: 47 uF HP caps, 2.2k MICBIAS,
    0.47 uF mic cap, MCLK 10k pull-down D-note, reset pull-down) and p.44 (47R I2C series)
  * SJK 3N12288G33YC spec (pad 1 OE high/open = run), Hroparts PJ-320DB drawing
  * docs/research/bom/hdmi-audio-camera-wireless-expansion.md section 2

MCLK: the oscillator Y1100 is the only driver of AUD_MCLK. It clocks the codec and
the SoC ball G26 (AUDIO_EXT_REFCLK1), which software must configure as an INPUT
(McASP1 AHCLKX/AHCLKR source); the SoC output on that pad must stay disabled
while Y1100 is fitted. Option: Y1100 DNP and the SoC drives AUD_MCLK instead.
"""
from schgen import Sheet
from symbols import CAP, FB, RES
from symlib.av import AIC3104, JACK_TRRS, OSC_3225

C100N = "100nF 16V X7R 0402"
C1U = "1uF 16V X5R 0402"
C10U = "10uF 10V X5R 0603"
AVDD = "VDDA_3V3_AUD"
TI = "Texas Instruments"


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/11_Audio.SchDoc", "Audio codec", style=7)  # C size

    # ---- codec ----------------------------------------------------------------
    sh.add("U1100", AIC3104, 3000, 15000, {
        "1": "AUD_MCLK", "2": "AUD_BCLK", "3": "AUD_FSYNC",
        "4": "AUD_DOUT",        # codec DIN  <- SoC McASP1 AXR0
        "5": "AUD_DIN",         # codec DOUT -> SoC McASP1 AXR2
        "8": "AUD_I2C_SCL", "9": "AUD_I2C_SDA", "31": "AUD_RST_N",
        "7": "VCC_3V3_SYS", "32": "VDD_1V8", "25": AVDD, "18": AVDD, "24": AVDD,
        "6": "GND", "17": "GND", "26": "GND", "21": "GND", "33": "GND",
        # unused analog inputs/outputs (powered down after reset, left open as on the SK)
        "10": "NC", "11": "NC", "12": "NC", "13": "NC",
        "14": "AUD_MIC",        # MIC2L/LINE2L/MICDET: headset detect, DC on the mic line (Fig 10-19)
        "16": "AUD_MIC_IN",     # MIC2R: mic preamp input, AC coupled
        "15": "AUD_MICBIAS",
        "19": "AUD_HPLOUT", "23": "AUD_HPROUT",
        "20": "NC", "22": "NC",  # HPLCOM/HPRCOM unused with AC-coupled HP outputs
        "27": "NC", "28": "NC", "29": "NC", "30": "NC",
    }, comment="TLV320AIC3104IRHBR", MPN="TLV320AIC3104IRHBR", Manufacturer=TI)

    # ---- supplies and decoupling (Figure 11-1) -----------------------------------
    sh.column(8600, 14900, [
        ("FB1100", FB, "VCC_3V3_SYS", AVDD, "BLM18KG601SN1D 600R@100MHz 1.3A 0603 (codec analog 3.3 V)",
         {"MPN": "BLM18KG601SN1D", "Manufacturer": "Murata"}),
        ("C1100", CAP, AVDD, "GND", C10U + " (bulk after bead)"),
        ("C1101", CAP, AVDD, "GND", C100N + " (AVDD pin 25)"),
        ("C1102", CAP, AVDD, "GND", C1U + " (AVDD pin 25)"),
        ("C1103", CAP, AVDD, "GND", C100N + " (DRVDD pin 18)"),
        ("C1104", CAP, AVDD, "GND", C100N + " (DRVDD pin 24)"),
        ("C1105", CAP, AVDD, "GND", C1U + " (DRVDD)"),
        ("C1106", CAP, AVDD, "GND", C10U + " (DRVDD)"),
        ("C1107", CAP, "VCC_3V3_SYS", "GND", C100N + " (IOVDD pin 7)"),
        ("C1108", CAP, "VCC_3V3_SYS", "GND", C1U + " (IOVDD pin 7)"),
        ("C1109", CAP, "VDD_1V8", "GND", C100N + " (DVDD pin 32)"),
        ("C1110", CAP, "VDD_1V8", "GND", C1U + " (DVDD pin 32)"),
    ], pitch=300)

    # ---- headphone and microphone (Figure 10-19, SK values) -----------------------
    sh.column(12600, 14900, [
        ("C1111", CAP, "AUD_HPLOUT", "AUD_HP_L", "47uF 6.3V X5R 0805 (HP L coupling)"),
        ("C1112", CAP, "AUD_HPROUT", "AUD_HP_R", "47uF 6.3V X5R 0805 (HP R coupling)"),
        ("R1105", RES, "AUD_MICBIAS", "AUD_MIC", "2.2k 0402 (MICBIAS feed)"),
        ("C1113", CAP, "AUD_MIC", "AUD_MIC_IN", "0.47uF 16V X7R 0402 (mic AC coupling)"),
    ], pitch=300)
    sh.add("J1100", JACK_TRRS, 17300, 14900, {
        "2": "AUD_HP_L",     # tip    = left  (CTIA)
        "3": "AUD_HP_R",     # ring 1 = right
        "4": "GND",          # ring 2 = ground
        "1": "AUD_MIC",      # sleeve = mic
        "5": "GND",          # mechanical "dummy" tab
    }, comment="PJ-320DB-5A", MPN="PJ-320DB-5A", Manufacturer="Korean Hroparts Elec")

    # ---- I2C1 pull-ups, codec I2C series, reset and I2S pulls ----------------------
    sh.column(12600, 13300, [
        ("R1100", RES, "VCC_3V3_SYS", "I2C1_SCL", "2.2k 0402 (I2C1 pull-up)"),
        ("R1101", RES, "VCC_3V3_SYS", "I2C1_SDA", "2.2k 0402 (I2C1 pull-up)"),
        ("R1102", RES, "I2C1_SCL", "AUD_I2C_SCL", "47R 0402 (series, SK R759 practice)"),
        ("R1103", RES, "I2C1_SDA", "AUD_I2C_SDA", "47R 0402 (series, SK R760 practice)"),
        ("R1108", RES, "AUD_RST_N", "GND", "10k 0402 (codec held in reset)"),
        ("R1109", RES, "AUD_BCLK", "GND", "100k 0402 (pad off in SoC reset)"),
        ("R1110", RES, "AUD_FSYNC", "GND", "100k 0402 (pad off in SoC reset)"),
        ("R1111", RES, "AUD_DOUT", "GND", "100k 0402 (pad off in SoC reset)"),
        ("R1112", RES, "AUD_DIN", "GND", "100k 0402 (codec DOUT Hi-Z in reset)"),
    ], pitch=300)

    # ---- 12.288 MHz MCLK oscillator ---------------------------------------------
    sh.add("Y1100", OSC_3225, 3000, 10500, {
        "4": "VCC_3V3_SYS", "1": "AUD_OSC_OE", "2": "GND", "3": "AUD_MCLK_OSC",
    }, comment="3N12288G33YC 12.288MHz", MPN="3N12288G33YC", Manufacturer="SJK")
    sh.column(7600, 10400, [
        ("R1104", RES, "AUD_MCLK_OSC", "AUD_MCLK", "22R 0402 (source series, at Y1100)"),
        ("R1106", RES, "VCC_3V3_SYS", "AUD_OSC_OE", "10k 0402 (OE high = run, SK R425)"),
        ("R1107", RES, "AUD_MCLK", "GND", "10k 0402 (MCLK pull-down, SK D-note)"),
        ("C1114", CAP, "VCC_3V3_SYS", "GND", C100N + " (Y1100 VDD)"),
        ("C1115", CAP, "VCC_3V3_SYS", "GND", C1U + " (Y1100 VDD)"),
    ], pitch=300)

    # ---- notes ---------------------------------------------------------------------
    notes = [
        "MCLK direction: Y1100 is the only AUD_MCLK driver (codec MCLK + SoC G26 AUDIO_EXT_REFCLK1 as INPUT -> McASP1 AHCLK). Never enable the G26 output with Y1100 fitted.",
        "Clocking: 12.288 MHz = 256 x 48 kHz. SoC McASP1 is BCLK/FSYNC master from AHCLK (pinmux), or codec master (SK DT); both lock to Y1100. Codec I2C address 0x18 (fixed).",
        "I2C1 pull-ups (2.2k) sit on I2C1_SCL/SDA with the TPD12S016 DDC A-port (sheet 10). The 47R SK series resistors are in the codec branch only: the TPD12S016",
        "A-port needs a LOW below 0.065*VCCA = 0.21 V to pass it to the HDMI side, and 47R x 1.8 mA in front of it would use most of that margin.",
        "Headphone: AC coupled (TRRS sleeve/ring2 shared with mic, no capless HPCOM). 47 uF -> 211 Hz corner at 16R / 106 Hz at 32R; 100-220 uF per TI Fig 11-1/11-4 if bass matters.",
        "Mic: MICBIAS 2.2k to the sleeve, AC coupled to MIC2R; MIC2L/MICDET on the mic line for headset detect (TI Fig 10-19, AC-coupled HP variant).",
        "Jack PJ-320DB-5A (CTIA): pin 2 tip = L, 3 ring1 = R, 4 ring2 = GND, 1 sleeve = MIC, 5 dummy tab = GND. No detect switch. Verify contact roles on a sample.",
        "Supplies: AVDD/DRVDD = VDDA_3V3_AUD (bead from VCC_3V3_SYS), IOVDD = VCC_3V3_SYS, DVDD = VDD_1V8. VDD_1V8 ramps before 3.3 V (TI asks AVDD >= DVDD);",
        "same as SK (AIC3106 from VCC_1V8/VCC_3V3_SYS); RESET is held low by R1108 until all rails are up. Codec thermal pad (33) to GND under the part.",
    ]
    for i, t in enumerate(notes):
        sh.note(1000, 6500 - i * 220, t)
    return sh
