"""Sheet 12 - camera: 15-pin 1.0 mm FPC in Raspberry Pi camera pinout (CSI0 2-lane).

References:
  * TE customer drawing C-1734248 rev E1 (1-1734248-5 = 15 positions, circuit 1 marked)
  * Raspberry Pi 15-pin camera connector pinout, as used on TI SK-AM62B-P1 PROC142B p.40 (J19)
  * data/pinmux_allocation.csv camera rows (I2C2 dedicated bus, CAM_IO0 10k pull-down,
    CAM_IO1 0R DNP)
  * docs/research/bom/hdmi-audio-camera-wireless-expansion.md section 3 (no TCA9543A)
"""
from schgen import Sheet
from symbols import CAP, FB, RES
from symlib.av import FPC15_CSI


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/12_Camera.SchDoc", "Camera FPC", style=7)  # C size

    sh.add("J1200", FPC15_CSI, 6000, 13500, {
        "1": "GND", "2": "CSI_D0_N", "3": "CSI_D0_P",
        "4": "GND", "5": "CSI_D1_N", "6": "CSI_D1_P",
        "7": "GND", "8": "CSI_CLK_N", "9": "CSI_CLK_P",
        "10": "GND",
        "11": "CAM_IO0",           # RPi CAM_GPIO0: camera power enable / shutdown
        "12": "CAM_FPC_IO1",       # RPi CAM_GPIO1: LED (v1) / unused (v2)
        "13": "CAM_I2C_SCL", "14": "CAM_I2C_SDA",
        "15": "VCC_3V3_CAM",
    }, comment="1-1734248-5", MPN="1-1734248-5", Manufacturer="TE Connectivity")

    sh.column(10500, 13400, [
        ("FB1200", FB, "VCC_3V3_SYS", "VCC_3V3_CAM", "BLM18KG601SN1D 600R@100MHz 1.3A 0603 (camera 3.3 V)",
         {"MPN": "BLM18KG601SN1D", "Manufacturer": "Murata"}),
        ("C1200", CAP, "VCC_3V3_CAM", "GND", "10uF 10V X5R 0603 (bulk at J1200, SK C43)"),
        ("C1201", CAP, "VCC_3V3_CAM", "GND", "1uF 16V X5R 0402"),
        ("C1202", CAP, "VCC_3V3_CAM", "GND", "100nF 16V X7R 0402 (at pin 15, SK C45)"),
        ("C1203", CAP, "VCC_3V3_SYS", "GND", "100nF 16V X7R 0402 (bead input)"),
    ], pitch=300)
    sh.column(10500, 11600, [
        ("R1200", RES, "VCC_3V3_SYS", "CAM_I2C_SCL", "2.2k 0402 (I2C2 pull-up)"),
        ("R1201", RES, "VCC_3V3_SYS", "CAM_I2C_SDA", "2.2k 0402 (I2C2 pull-up)"),
        ("R1202", RES, "CAM_IO0", "GND", "10k 0402 (camera off in reset)"),
        ("R1203", RES, "CAM_IO1", "CAM_FPC_IO1", "0R 0402 DNP (fit for camera LED control)", {"DNP": "1"}),
    ], pitch=300)

    notes = [
        "RPi 15-pin camera pinout (SK J19): 1/4/7/10 GND, 2/3 D0 N/P, 5/6 D1 N/P, 8/9 CLK N/P, 11 CAM_IO0, 12 CAM_IO1, 13 SCL, 14 SDA, 15 3.3 V.",
        "Each TE circuit has two SMT tails (two pad rows): both pads of circuit n get pad number n. Contact side matches RPi cables (same part as SK).",
        "CSI0: 100R differential, length-matched within and between pairs, no stubs or series parts (D-PHY RX on 1.8 V analog). Ground pins 1/4/7/10 to GND plane.",
        "Camera I2C = SoC I2C2 (dedicated bus, no TCA9543A). CAM_IO0 has a 10k pull-down so the camera stays off until software enables it.",
    ]
    for i, t in enumerate(notes):
        sh.note(1000, 7500 - i * 220, t)
    return sh
