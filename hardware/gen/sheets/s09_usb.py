"""Sheet 09 - USB: USB0 device path (USB-C #1), USB1 host -> CH335F 4-port hub,
two USB-A host ports with TPS2051B 0.5 A switches.

References:
  * AM625 datasheet SPRSP58C: 8.2.3 / Figure 8-4 (VBUS divider + 6.8 V clamp),
    6.1 abs max (USBx_VBUS -0.3..3.6 V), 6.5 ROC (USBx_VBUS <= 3.465 V),
    Table 5-72/5-73 + 5-74 (RCALIB is inside the OSD62x SiP)
  * TI SK-AM62B-P1 PROC142B p.37 (USB0: DLW21 CMC + 0R bypass, ESD122) and p.38
    (USB1: TPS2051BD, EN from USB1_DRVVBUS with DNI pull-down, 10k OC pull-up,
    150 uF + 0.1 uF, TPD4S012, CMC + 0R bypass, shield 0R + DNI 2 kV cap,
    Fig 8-4 divider + BZX84C6V8 on both ports)
  * WCH CH334/CH335 datasheet V2.91: Table 1-3 (pins), 3.1 / Table 3-1 (OC modes:
    CH335F = dual-independent or GANG), 3.2.2 / Fig 3-2-2 (RESET#/CDP: ~25k internal
    pull-up, VILRST 0.75 V, MCU drive through a series Schottky so CDP stays off),
    3.3.2 (LED2/PGANG pull-down 3-5.1k selects independent OC detection),
    6.1 (12 MHz crystal, NO external load caps), 6.4 (V5 and VDD33 both on 3.3 V),
    6.5 (CH335F independent-OC reference circuit)
  * TPS2041B/51B datasheet SLVS514P (TPS2051B EN is active high, OC open drain)
  * Octavo OSD62x-PM checklist: no series parts on DP/DM except a CMC with 0R bypass

Decisions:
  * Port power: the CH335F PWRENx# outputs are active LOW, the BOM's TPS2051B EN is
    active HIGH. Both switches are therefore enabled by USB1_DRVVBUS (SK topology).
    The SoC holds DRVVBUS low through its internal pull-down while in reset and the
    pad is unpowered while VCC_3V3_SYS is off, so the ports are dead whenever the hub
    is. The hub runs in dual-independent OC mode (PGANG pulled down) so it reports an
    over-current per port; its PWREN1..4# outputs are not used.
  * USB0 is device-only: USB0_DRVVBUS only gets a DNP pull-down (SK D-note: DNI keeps
    USB deep-sleep wake possible; fit it if wake is not used).
  * USB1_VBUS_DIV: same Fig 8-4 network fed from VCC_5V0 (the hub's port supply).
    For a host-only port the VBUS pin is optional (SK D-note) but the divider keeps
    the pin at a defined 1.67 V and costs four parts.
"""
from schgen import Sheet
from symbols import CAP, CAP_POL, DIODE, RES
from symlib.usb import (BX_TYPE_A_MWC44, BZX84_SOT23, CH335F, ESD122_DMX, SDCW2012_CMC,
                        TPS2051B_DBV, USBLC6_2SC6, XTAL_YSX321SL)

C100N = "100nF 16V X7R 0402"
C1U = "1uF 10V X5R 0402"
C10U = "10uF 10V X5R 0603"
C10U_IN = "10uF 25V X5R 0805"
R0 = "0R 0402"
DNP = {"DNP": "1"}
P_C100N = {"MPN": "CL05B104KO5NNNC", "Manufacturer": "Samsung", "LCSC": "C1525"}
P_C10U_IN = {"MPN": "CL21A106KAYNNNE", "Manufacturer": "Samsung", "LCSC": "C15850"}
P_150U = {"MPN": "RYHV10V150UF6*5", "Manufacturer": "Honor Elec", "LCSC": "C48970647"}
P_CMC = {"MPN": "SDCW2012-2-900TF", "Manufacturer": "Sunlord", "LCSC": "C54888"}
P_ZENER = {"MPN": "LBZX84C6V8LT1G", "Manufacturer": "LRC", "LCSC": "C12746"}
P_BYPASS = {"DNP": "1", "MPN": "0402WGF0000TCE", "Manufacturer": "UNI-ROYAL", "LCSC": "C17168"}


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/09_USB.SchDoc", "USB: device port, hub, USB-A host ports", style=7)

    # ================================================================ USB0 (device, USB-C #1)
    sh.note(1000, 16600, "USB0 - device / DFU port on USB-C #1 (connector on sheet 01)")
    sh.add("L900", SDCW2012_CMC, 2500, 16000, {
        "1": "USBC1_DP", "2": "USB0_DP", "4": "USBC1_DM", "3": "USB0_DM",
    }, comment="SDCW2012-2-900TF 90R@100MHz", **P_CMC)
    sh.column(3300, 15300, [
        ("R900", RES, "USBC1_DP", "USB0_DP", "0R 0402 DNP (CMC bypass)", P_BYPASS),
        ("R901", RES, "USBC1_DM", "USB0_DM", "0R 0402 DNP (CMC bypass)", P_BYPASS),
    ])
    sh.add("D900", ESD122_DMX, 2500, 14300, {"2": "USBC1_DP", "3": "USBC1_DM", "1": "GND"},
           comment="ESD122DMXR", MPN="ESD122DMXR", Manufacturer="Texas Instruments", LCSC="C544474")
    sh.note(1000, 13700, "Order from the USB-C pads: ESD122 -> CMC (R900/R901 0R footprints stacked on L900) -> SoC.")
    sh.note(1000, 13500, "90 Ohm diff, no other series parts on USB0_DP/DM (AM62x / Octavo checklist).")

    # ---- USB0_VBUS: AM62x DS Fig 8-4 divider + 6.8 V clamp ----
    sh.column(3300, 12900, [
        ("R902", RES, "VBUS_USBC", "USB0_VBUS_CLAMP", "3.48k 1% 0402"),
        ("R903", RES, "USB0_VBUS_CLAMP", "USB0_VBUS_DIV", "16.5k 1% 0402"),
        ("R904", RES, "USB0_VBUS_DIV", "GND", "10k 1% 0402"),
        ("R905", RES, "USB0_DRVVBUS", "GND", "10k 0402 DNP (device-only port)", DNP),
    ])
    sh.add("D901", BZX84_SOT23, 2500, 11100, {"3": "USB0_VBUS_CLAMP", "1": "GND", "2": "NC"},
           comment="LBZX84C6V8LT1G 6.8V", **P_ZENER)
    sh.note(1000, 10300, "VBUS_USBC is 5-9 V (PD max 9 V). Pin = VBUS x 10/29.98 unclamped:")
    sh.note(1000, 10100, "  5 V -> 1.67 V, 9 V -> 3.00 V, 9.45 V (+5%) -> 3.15 V; all < 3.465 V ROC / 3.6 V abs max.")
    sh.note(1000, 9900, "  Above ~7.9 V the zener node clamps at 6.4-7.2 V -> pin 2.4-2.7 V. At 9 V R902 sees 1.4 mW.")
    sh.note(1000, 9700, "USB0_DRVVBUS: device-only port, pin left on its internal pull-down; R905 is the SK option.")

    # ================================================================ hub
    sh.note(6300, 16600, "USB1 host -> CH335F 4-port MTT hub (self-powered, ports 1-2 used)")
    sh.add("U900", CH335F, 7600, 15700, {
        "21": "USB1_DP", "20": "USB1_DM",
        "11": "HUB_XI", "12": "HUB_XO",
        "17": "HUB_RESET_N", "1": "NC", "3": "HUB_PGANG", "22": "NC", "25": "NC",
        "26": "VCC_3V3_SYS", "28": "VCC_3V3_SYS", "27": "GND", "29": "GND",
        "7": "HUB_P1_DP", "6": "HUB_P1_DM", "4": "NC", "24": "USBA1_OC_N",
        "9": "HUB_P2_DP", "8": "HUB_P2_DM", "2": "NC", "23": "USBA2_OC_N",
        "14": "NC", "13": "NC", "10": "NC", "19": "VCC_3V3_SYS",
        "16": "NC", "15": "NC", "5": "NC", "18": "VCC_3V3_SYS",
    }, comment="CH335F", MPN="CH335F", Manufacturer="WCH (Jiangsu Qin Heng)", LCSC="C5137013")
    sh.note(6300, 13700, "PSELF floats high (internal pull-up) = self-powered. LED3/LED4 float (no EEPROM, no LEDs).")
    sh.note(6300, 13500, "PWREN1..4# unused (port power follows USB1_DRVVBUS). Ports 3/4: DP/DM open, OVCUR3/4# tied high.")

    sh.add("Y900", XTAL_YSX321SL, 7300, 12900, {"1": "HUB_XI", "3": "HUB_XO", "2": "GND", "4": "GND"},
           comment="X322512MSB4SI 12MHz 20pF 10ppm", MPN="X322512MSB4SI", Manufacturer="YXC",
           LCSC="C9002")
    sh.note(6300, 12100, "No load caps on Y900: XI/XO have ~16 pF built in (WCH DS 6.1).")

    sh.column(7300, 11400, [
        ("C900", CAP, "VCC_3V3_SYS", "GND", C1U + " (V5 pin 26)"),
        ("C901", CAP, "VCC_3V3_SYS", "GND", C100N + " (V5 pin 26)", P_C100N),
        ("C902", CAP, "VCC_3V3_SYS", "GND", C10U + " (VDD33 pin 28)"),
        ("C903", CAP, "VCC_3V3_SYS", "GND", C1U + " (VDD33 pin 28)"),
        ("C904", CAP, "VCC_3V3_SYS", "GND", C100N + " (VDD33 pin 28)", P_C100N),
        ("R907", RES, "HUB_PGANG", "GND", "3.9k 0402 (PGANG low = independent OC)"),
        ("R908", RES, "VCC_3V3_SYS", "USBA1_OC_N", "10k 0402 (TPS2051B OC pull-up)"),
        ("R909", RES, "VCC_3V3_SYS", "USBA2_OC_N", "10k 0402 (TPS2051B OC pull-up)"),
    ])
    sh.note(6300, 8000, "V5 and VDD33 both on VCC_3V3_SYS (internal LDO bypassed, WCH DS 6.4).")

    # ---- hub reset: GPIO pulls low through a Schottky; release = internal pull-up ----
    sh.add("D902", DIODE, 10600, 11400, {"1": "HUB_RESET_N", "2": "USB_HUB_RST_N"},
           comment="BAT54WS-7-F (anode at hub)", MPN="BAT54WS-7-F", Manufacturer="Diodes Inc",
           LCSC="C124205")
    sh.column(10600, 10900, [
        ("R906", RES, "USB_HUB_RST_N", "GND", "1.5k 0402 (holds hub in reset while SoC pads are off)"),
    ])
    sh.note(9400, 10300, "Reset low = 0.25 V + 115 uA x 1.5k = 0.42 V < VILRST 0.75 V. GPIO high: diode blocks,")
    sh.note(9400, 10100, "RESET# rises on its own ~25k pull-up, so CDP is never strapped on (WCH Fig 3-2-2).")

    # ---- USB1_VBUS: Fig 8-4 network from the 5 V port supply ----
    sh.column(10600, 9300, [
        ("R910", RES, "VCC_5V0", "USB1_VBUS_CLAMP", "3.48k 1% 0402"),
        ("R911", RES, "USB1_VBUS_CLAMP", "USB1_VBUS_DIV", "16.5k 1% 0402"),
        ("R912", RES, "USB1_VBUS_DIV", "GND", "10k 1% 0402"),
        ("R913", RES, "USB1_DRVVBUS", "GND", "100k 0402 (keeps USB-A power off while the SoC IO is unpowered; DNP only for USB1 deep-sleep wake)"),
    ])
    sh.add("D903", BZX84_SOT23, 9900, 7500, {"3": "USB1_VBUS_CLAMP", "1": "GND", "2": "NC"},
           comment="LBZX84C6V8LT1G 6.8V", **P_ZENER)
    sh.note(9400, 6700, "USB1_VBUS_DIV = 1.67 V from VCC_5V0. In host mode the pin is optional (SK D-note);")
    sh.note(9400, 6500, "DT: set ti,vbus-divider on both USB wrappers.")

    # ================================================================ USB-A port power
    sh.note(12300, 16600, "USB-A ports: 0.5 A each, enabled together by USB1_DRVVBUS, OC flags to the hub")
    for i, (u, y, ccol) in enumerate((("U901", 16000, 901), ("U902", 13600, 909))):
        port = i + 1
        sh.add(u, TPS2051B_DBV, 13500, y, {
            "5": "VCC_5V0", "4": "USB1_DRVVBUS", "2": "GND",
            "1": f"VBUS_USBA{port}", "3": f"USBA{port}_OC_N",
        }, comment="TPS2051BDBVR", MPN="TPS2051BDBVR", Manufacturer="Texas Instruments", LCSC="C24593")
        n = 905 + 4 * i
        sh.column(17200, y, [
            (f"C{n}", CAP, "VCC_5V0", "GND", C10U_IN + " (switch IN)", P_C10U_IN),
            (f"C{n + 1}", CAP, "VCC_5V0", "GND", C100N + " (switch IN)", P_C100N),
            (f"C{n + 2}", CAP_POL, f"VBUS_USBA{port}", "GND", "150uF 10V polymer (USB 2.0 >= 120 uF)", P_150U),
            (f"C{n + 3}", CAP, f"VBUS_USBA{port}", "GND", C100N + " (at connector)", P_C100N),
        ])

    # ================================================================ USB-A data paths
    for i, y in enumerate((10600, 7600)):
        port = i + 1
        cmc, rb, esd = f"L{901 + i}", 914 + 2 * i, f"D{904 + i}"
        sh.add(cmc, SDCW2012_CMC, 13300, y, {
            "1": f"HUB_P{port}_DP", "2": f"USBA{port}_DP",
            "4": f"HUB_P{port}_DM", "3": f"USBA{port}_DM",
        }, comment="SDCW2012-2-900TF 90R@100MHz", **P_CMC)
        sh.column(14100, y - 700, [
            (f"R{rb}", RES, f"HUB_P{port}_DP", f"USBA{port}_DP", "0R 0402 DNP (CMC bypass)", P_BYPASS),
            (f"R{rb + 1}", RES, f"HUB_P{port}_DM", f"USBA{port}_DM", "0R 0402 DNP (CMC bypass)", P_BYPASS),
        ])
        sh.add(esd, USBLC6_2SC6, 16200, y, {
            "1": f"USBA{port}_DP", "6": f"USBA{port}_DP", "3": f"USBA{port}_DM", "4": f"USBA{port}_DM",
            "2": "GND", "5": f"VBUS_USBA{port}",
        }, comment="USBLC6-2SC6", MPN="USBLC6-2SC6", Manufacturer="STMicroelectronics", LCSC="C7519")

    sh.add("J900", BX_TYPE_A_MWC44, 19300, 10700, {
        "1": "VBUS_USBA1", "2": "USBA1_DM", "3": "USBA1_DP", "4": "GND",
        "5": "VBUS_USBA2", "6": "USBA2_DM", "7": "USBA2_DP", "8": "GND",
        "9": "USBA_SHIELD", "10": "USBA_SHIELD", "11": "USBA_SHIELD", "12": "USBA_SHIELD",
    }, comment="BX-TYPE-A-MWC44", MPN="BX-TYPE-A-MWC44", Manufacturer="Bossie", LCSC="C18077688")
    sh.column(19900, 8900, [
        ("R918", RES, "USBA_SHIELD", "GND", "0R 0603 (shield to GND, SK R418)"),
        ("C913", CAP, "USBA_SHIELD", "GND", "4.7nF 2kV X7R 1206 DNP (SK C372 option)", DNP),
    ])
    sh.note(12300, 5900, "J900 pad numbers are defined by the symbol (the Bossie drawing has none):")
    sh.note(12300, 5700, "  1-4 lower port VBUS/D-/D+/GND = port 1, 5-8 upper port = port 2, 9-12 shell pegs.")
    sh.note(12300, 5500, "USBLC6 at the connector pins, then CMC (R914-R917 0R footprints stacked on L901/L902).")
    sh.note(12300, 5300, "Hub port k -> USB-A port k. 90 Ohm diff; keep DP/DM pairs away from the 5 V switch nodes.")
    return sh
