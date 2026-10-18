"""Sheet 08 - Gigabit Ethernet: DP83867ISRGZR PHY on RGMII1/MDIO0, 25 MHz crystal, HR911130A MagJack.

References:
  * TI DP83867E/IS/CS datasheet SNLS504G: Table 5-1 (pins), 7.5.1 (4-level straps,
    Tables 7-6..7-10), 7.5.2 / Fig 7-12 (LED + strap), 9.2.1.3 (crystal),
    9.3 Fig 9-7 (supplies and decoupling), RGMIICTL 0x32 defaults (TX and RX clock
    shift both enabled by default -> TX skew must be strapped to 0 ns)
  * TI SK-AM62B-P1 PROC142B p.24-26 (CPSW PHY-1: 22R TX series at SoC, strap set
    "PHY addr 0, ANEG on, 10/100/1000, TX skew 0 ns, RX skew 2 ns", MDIO 2.2k,
    RBIAS, shield 0R/2 kV cap option)
  * docs/research/am625-tps65219-constraints.md A.6 (AM62x MAC always adds the TX
    delay; PHY must add the RX delay; ROM Ethernet boot needs the PHY strapped to
    RGMII-ID and out of reset)
  * docs/research/bom/storage-usb-ethernet.md section 5 (IS vs IR, HR911130A)

Supplies: VDDIO = VCC_3V3_SYS, VDDA2P5 = VDDA_2V5_PHY (BLM15PX121SN1D from
DDR4_VPP_2V5, PMIC LDO4), VDD1P0 = VDD_1V0_PHY (TLV757 on sheet 02). TI calls this
the "two-supply configuration" (Fig 9-7; VDDIO counted separately): VDDA1P8 pins
13/48 are left unconnected as the figure's note A requires, and there is no
sequencing requirement.
"""
from schgen import Sheet
from symbols import CAP, FB, RES
from symlib.ethernet import DP83867_RGZ, HR911130A, XTAL4_3225

C100N = "100nF 16V X7R 0402"
C10N = "10nF 25V X7R 0402"
C1U = "1uF 25V X5R 0402"
C10U = "10uF 10V X5R 0603"
R22 = "22R 0402"
DNP = {"DNP": "1"}

TX = [("ETH_TXC", "PHY_GTX_CLK"), ("ETH_TX_CTL", "PHY_TX_CTRL"), ("ETH_TD0", "PHY_TX_D0"),
      ("ETH_TD1", "PHY_TX_D1"), ("ETH_TD2", "PHY_TX_D2"), ("ETH_TD3", "PHY_TX_D3")]
RX = [("PHY_RX_CLK", "ETH_RXC"), ("PHY_RX_CTRL", "ETH_RX_CTL"), ("PHY_RX_D0", "ETH_RD0"),
      ("PHY_RX_D1", "ETH_RD1"), ("PHY_RX_D2", "ETH_RD2"), ("PHY_RX_D3", "ETH_RD3")]


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/08_Ethernet.SchDoc", "Gigabit Ethernet PHY", style=8)

    # ================================================================ PHY
    sh.add("U800", DP83867_RGZ, 9000, 19500, {
        "29": "PHY_GTX_CLK", "37": "PHY_TX_CTRL", "28": "PHY_TX_D0", "27": "PHY_TX_D1",
        "26": "PHY_TX_D2", "25": "PHY_TX_D3",
        "32": "PHY_RX_CLK", "38": "PHY_RX_CTRL", "33": "PHY_RX_D0", "34": "PHY_RX_D1",
        "35": "PHY_RX_D2", "36": "PHY_RX_D3",
        "16": "ETH_MDC", "17": "ETH_MDIO", "44": "ETH_PHY_INT_N", "43": "ETH_PHY_RST_N",
        "15": "PHY_XI", "14": "PHY_XO", "18": "NC", "12": "PHY_RBIAS",
        "20": "NC", "22": "NC", "23": "NC", "21": "NC",
        "1": "ETH_MDI0_P", "2": "ETH_MDI0_N", "4": "ETH_MDI1_P", "5": "ETH_MDI1_N",
        "7": "ETH_MDI2_P", "8": "ETH_MDI2_N", "10": "ETH_MDI3_P", "11": "ETH_MDI3_N",
        "47": "PHY_LED0", "46": "PHY_LED1", "45": "PHY_LED2", "39": "PHY_GPIO0", "40": "PHY_GPIO1",
        "19": "VCC_3V3_SYS", "30": "VCC_3V3_SYS", "41": "VCC_3V3_SYS",
        "3": "VDDA_2V5_PHY", "9": "VDDA_2V5_PHY",
        "6": "VDD_1V0_PHY", "24": "VDD_1V0_PHY", "31": "VDD_1V0_PHY", "42": "VDD_1V0_PHY",
        "13": "NC", "48": "NC", "49": "GND",
    }, comment="DP83867ISRGZR", MPN="DP83867ISRGZR", Manufacturer="Texas Instruments", LCSC="C543036")

    # ---- RGMII series resistors: TX at the SoC balls, RX at the PHY pins (SK) ----
    sh.column(3000, 19400, [(f"R{800 + i}", RES, a, b, R22 + " (at SoC)") for i, (a, b) in enumerate(TX)])
    sh.column(3000, 16800, [(f"R{806 + i}", RES, a, b, R22 + " (at PHY)") for i, (a, b) in enumerate(RX)])

    # ---- management, interrupt, reset, bias ----
    sh.column(3000, 14200, [
        ("R813", RES, "VCC_3V3_SYS", "ETH_MDIO", "2.2k 0402 (MDIO pull-up)"),
        ("R814", RES, "VCC_3V3_SYS", "ETH_PHY_INT_N", "2.2k 0402 (INT open drain)"),
        ("R815", RES, "RESETSTATZ", "ETH_PHY_RST_N", "1.5k 0402 (reset follows RESETSTATz)"),
        ("R816", RES, "VCC_3V3_SYS", "ETH_PHY_RST_N", "10k 0402 (DNP, plain pull-up instead of R815)", DNP),
        ("R812", RES, "PHY_RBIAS", "GND", "11k 1% 0402 (RBIAS)"),
        ("C802", CAP, "PHY_RBIAS", "GND", "22pF 50V C0G 0402 (DNP, SK compliance option)", DNP),
    ])

    # ---- 25 MHz crystal, CL 12 pF: C = 2 x (CL - Cstray 4.5 pF) = 15 pF ----
    sh.add("Y800", XTAL4_3225, 3000, 11800, {"1": "PHY_XI", "3": "PHY_XO", "2": "GND", "4": "GND"},
           comment="X322525MOB4SI 25MHz 12pF 10ppm", MPN="X322525MOB4SI", Manufacturer="YXC", LCSC="C9006")
    sh.column(3000, 10900, [
        ("C800", CAP, "PHY_XI", "GND", "15pF 50V C0G 0402"),
        ("C801", CAP, "PHY_XO", "GND", "15pF 50V C0G 0402"),
    ])

    # ---- supplies: 2.5 V bead + decoupling per Fig 9-7 (1uF + 0.1uF per pin, 10uF + 10nF bulk) ----
    sh.column(8600, 15200, [
        ("FB800", FB, "DDR4_VPP_2V5", "VDDA_2V5_PHY", "BLM15PX121SN1D 120R@100MHz 2A",
         {"MPN": "BLM15PX121SN1D", "Manufacturer": "Murata"}),
        ("C811", CAP, "VDDA_2V5_PHY", "GND", C10U + " (VDDA2P5 bulk)"),
        ("C812", CAP, "VDDA_2V5_PHY", "GND", C10N + " (VDDA2P5 bulk)"),
        ("C813", CAP, "VDDA_2V5_PHY", "GND", C1U + " (pin 3)"),
        ("C814", CAP, "VDDA_2V5_PHY", "GND", C100N + " (pin 3)"),
        ("C815", CAP, "VDDA_2V5_PHY", "GND", C1U + " (pin 9)"),
        ("C816", CAP, "VDDA_2V5_PHY", "GND", C100N + " (pin 9)"),
    ])
    sh.column(12200, 15200, [
        ("C803", CAP, "VCC_3V3_SYS", "GND", C10U + " (VDDIO bulk)"),
        ("C804", CAP, "VCC_3V3_SYS", "GND", C10N + " (VDDIO bulk)"),
        ("C805", CAP, "VCC_3V3_SYS", "GND", C1U + " (pin 19)"),
        ("C806", CAP, "VCC_3V3_SYS", "GND", C100N + " (pin 19)"),
        ("C807", CAP, "VCC_3V3_SYS", "GND", C1U + " (pin 30)"),
        ("C808", CAP, "VCC_3V3_SYS", "GND", C100N + " (pin 30)"),
        ("C809", CAP, "VCC_3V3_SYS", "GND", C1U + " (pin 41)"),
        ("C810", CAP, "VCC_3V3_SYS", "GND", C100N + " (pin 41)"),
    ])
    sh.column(15800, 15200, [
        ("C817", CAP, "VDD_1V0_PHY", "GND", C10U + " (VDD1P0 bulk)"),
        ("C818", CAP, "VDD_1V0_PHY", "GND", C10N + " (VDD1P0 bulk)"),
        ("C819", CAP, "VDD_1V0_PHY", "GND", C1U + " (pin 6)"),
        ("C820", CAP, "VDD_1V0_PHY", "GND", C100N + " (pin 6)"),
        ("C821", CAP, "VDD_1V0_PHY", "GND", C1U + " (pin 24)"),
        ("C822", CAP, "VDD_1V0_PHY", "GND", C100N + " (pin 24)"),
        ("C823", CAP, "VDD_1V0_PHY", "GND", C1U + " (pin 31)"),
        ("C824", CAP, "VDD_1V0_PHY", "GND", C100N + " (pin 31)"),
        ("C825", CAP, "VDD_1V0_PHY", "GND", C1U + " (pin 42)"),
        ("C826", CAP, "VDD_1V0_PHY", "GND", C100N + " (pin 42)"),
    ])

    # ---- 4-level straps (Rhi to VDDIO, Rlo to GND; 1% 0402). Fitted: RX_CTRL mode 3,
    #      LED_1 mode 2. Everything else mode 1 (internal 9k pull-down), footprints DNP. ----
    def pair(n, net, rhi, rlo, fit, what):
        p = {} if fit else DNP
        tag = what if fit else what + ", DNP"
        return [(f"R{n}", RES, "VCC_3V3_SYS", net, f"{rhi} 1% 0402 (Rhi {tag})", p),
                (f"R{n + 1}", RES, net, "GND", f"{rlo} 1% 0402 (Rlo {tag})", p)]
    sh.column(19600, 19400,
              pair(820, "PHY_RX_CTRL", "5.76k", "2.49k", True, "RX_CTRL mode 3")
              + pair(822, "PHY_LED1", "10k", "2.49k", True, "LED_1 mode 2")
              + pair(824, "PHY_RX_D0", "10k", "2.49k", False, "RX_D0")
              + pair(826, "PHY_RX_D1", "10k", "2.49k", False, "RX_D1 dummy"))
    sh.column(23600, 19400,
              pair(828, "PHY_RX_D2", "10k", "2.49k", False, "RX_D2")
              + pair(830, "PHY_RX_D3", "10k", "2.49k", False, "RX_D3 dummy")
              + pair(832, "PHY_GPIO0", "5.76k", "2.49k", False, "GPIO_0")
              + pair(834, "PHY_GPIO1", "10k", "2.49k", False, "GPIO_1")
              + pair(836, "PHY_LED2", "10k", "2.49k", False, "LED_2"))

    # ================================================================ RJ45
    sh.add("J800", HR911130A, 28000, 19500, {
        "2": "ETH_MDI0_P", "3": "ETH_MDI0_N", "4": "ETH_MDI1_P", "7": "ETH_MDI1_N",
        "5": "ETH_MDI2_P", "6": "ETH_MDI2_N", "8": "ETH_MDI3_P", "9": "ETH_MDI3_N",
        "1": "ETH_MDI_CT",
        "11": "ETH_LED_GRN", "12": "GND", "14": "ETH_LED_YEL", "13": "GND",
        "10": "ETH_SHIELD", "15": "ETH_SHIELD", "16": "ETH_SHIELD",
    }, comment="HR911130A", MPN="HR911130A", Manufacturer="HanRun", LCSC="C54408")
    sh.column(28800, 16800, [
        ("R840", RES, "PHY_LED0", "ETH_LED_GRN", "470R 0402 (green = LED_0 link)"),
        ("R841", RES, "PHY_LED1", "ETH_LED_YEL", "470R 0402 (yellow = LED_1 1000M)"),
        ("C830", CAP, "ETH_MDI_CT", "GND", C100N + " (centre tap)"),
        ("R842", RES, "ETH_SHIELD", "GND", "0R 0603 (shield/Bob-Smith to GND)"),
        ("C831", CAP, "ETH_SHIELD", "GND", "1nF 2kV X7R 1206 (DNP, AC-coupled shield option)", DNP),
    ])

    # ================================================================ notes
    notes = [
        "DP83867IS strap set (SNLS504G Tables 7-6..7-10), VDDIO = 3.3 V:",
        "  RX_D0 (33)  mode 1 open/open     PHY_ADD[1:0] = 00",
        "  RX_D2 (35)  mode 1 open/open     PHY_ADD[3:2] = 00  -> PHY address 0",
        "  RX_CTRL(38) mode 3 5.76k/2.49k   Autoneg Disable = 0 (auto-neg ON; mode 3/4 mandatory)",
        "  GPIO_0 (39) mode 1 open/open     RX skew RX[0] = 0",
        "  GPIO_1 (40) mode 1 open/open     RX skew RX[2:1] = 00  -> RX clock skew 2.0 ns (RGMII-RXID)",
        "  LED_2 (45)  mode 1 open/open     TX skew TX[1:0] = 00",
        "  LED_1 (46)  mode 2 10k/2.49k     ANEG_SEL = 0 (10/100/1000), TX[2] = 1 -> TX skew 0 ns",
        "  LED_0 (47)  mode 1 open/open     Mirror = 0, SGMII Enable = 0 (RGMII)",
        "  RX_D1/RX_D3: SGMII-pair dummies, must copy RX_D0/RX_D2 straps (both DNP = mode 1).",
        "RGMIICTL resets with TX and RX shift enabled; TX skew strapped to 0 ns because the AM62x MAC",
        "  always delays TXC. Linux: phy-mode rgmii-rxid, ti,rx-internal-delay = 2.0 ns.",
        "LEDs: modes 1/2 make LED_0/1 active-high drivers, LEDs to GND via 470R (Fig 7-12).",
        "  LED_0 link (reprogram LEDCR1 for link+activity), LED_1 1000M link, LED_2 unused.",
        "ETH_PHY_RST_N: R815 to RESETSTATZ holds the PHY in reset while the SoC is in reset and",
        "  releases it when the SoC leaves reset, so ROM RGMII boot finds a strapped, running PHY.",
        "  GPIO0_88 can still reset the PHY (drives 2.2 mA into R815). RESET_N has ~9k internal",
        "  pull-up: worst-case low level 0.63 V during reset - check at bring-up.",
        "  While the RESETSTATz pad is still Hi-Z (early power-up) that pull-up lifts the",
        "  RESETSTATZ net to ~1.5 V against R611 10k (sheet 06); it settles once the SoC drives it.",
        "  R816 (DNP) = plain 10k pull-up alternative: fit it and remove R815 to decouple the PHY.",
        "ETH_PHY_INT_N: open drain, 2.2k pull-up (datasheet); plain GPIO, so no 62R/47pF RC.",
        "Series R: 22R TX at the SoC balls, 22R RX at the PHY pins; may become 0R after SI sim.",
        "  Strap resistors sit on the PHY side of the RX series resistors. Groups matched <= 50 ps.",
        "VDDA1P8 (13, 48): no connection (two-supply mode). RBIAS 11k 1% (C802 DNP per SK).",
        "Crystal CL 12 pF: 15 pF caps assume 4.5 pF stray; 18 pF if the PCB is tighter.",
        "MDI: 100R differential pairs, no termination or CT bias (voltage-mode PHY).",
        "Shield: tabs + Bob-Smith P10 -> ETH_SHIELD -> R842 0R to GND (board has one GND).",
        "  For a chassis-earth product fit C831 1nF/2kV instead of R842.",
        "VDDA_2V5_PHY total C 12.2 uF behind FB800; LDO4 rail budget <= 30 uF (sheet 02).",
    ]
    for i, t in enumerate(notes):
        sh.note(19200, 12600 - i * 200, t)
    return sh
