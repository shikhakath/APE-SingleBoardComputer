# APE-SBC: BOM and cost estimate

| | |
|---|---|
| Date priced | 2026-10-17 (prices and stock change daily; re-check before ordering) |
| Price basis | Unit price at the break for **10 boards** (qty = 10 × per-board count) |
| Sources | JLCPCB/LCSC parts library first, then Digi-Key, Mouser, vendor stores |
| Stock rule | Every placed line must show stock ≥ 10 boards' worth at a real distributor (most show ≥ 50). The one exception is flagged below. |
| Machine-readable | [`APE-SBC_BOM_estimate.csv`](APE-SBC_BOM_estimate.csv): all 156 lines, including 16 qty-0 alternates and rejected options |
| Section notes | [`docs/research/bom/`](../research/bom/): part comparisons and rationale for each section |

## Summary

| Subsystem | $ / board | Key parts |
|---|---:|---|
| Processor | 44.06 | OSD6254-1G-IPM SiP (Digi-Key; the only stock found anywhere) |
| Power | 15.23 | TPS25730 USB-PD sink, LM61460 3.3 V buck, TPS63070 5 V buck-boost, TPS6521904**RSM** PMIC, TPS22965, TPS22996, TPS2051B ×2 |
| Debug | 14.40 | FT4232HL quad USB-UART (as on the TI reference), isolation buffers, USB-C, Tag-Connect TC2070 footprint |
| Ethernet | 7.27 | DP83867**IS**RGZR GbE PHY, HanRun HR911130A RJ45 with magnetics |
| HDMI | 5.88 | **TI TFP410** (DVI over the HDMI connector), TPD12S016, HDMI-A connector |
| Clock + reset + boot | 2.80 | 25 MHz oscillator, 32.768 kHz crystal, reset logic, boot DIP switch, 3 buttons |
| USB | 2.36 | WCH CH335F USB 2.0 hub, dual stacked USB-A, chokes, ESD |
| Audio | 2.25 | TLV320AIC3104 codec, 12.288 MHz oscillator, 3.5 mm TRRS jack |
| Wireless (on board) | 1.27 | M.2 Key-E socket (LOTES), standoff, screw |
| Storage (on board) | 1.11 | eMMC-module connector, microSD socket, ESD |
| Misc | 1.06 | Board-ID EEPROM, TMP102, LEDs |
| Camera | 1.01 | 15-pin Raspberry Pi camera FPC |
| Passives (SiP + generic) | 0.91 | SiP decoupling per Octavo Table 4-3, pulls, filters |
| Expansion | 0.34 | 2×20 header, HAT-ID EEPROM, series resistors |
| **Board parts subtotal** | **99.95** | |
| eMMC module, 32 GB (plug-in) | 24.95 | PINE64 module (Hardkernel/Radxa-compatible connector) |
| Wi-Fi 6 + BLE module (plug-in) | 55.00 | TI M2-CC3351 (TI.com, 74 in stock) |
| **Parts total** | **179.90** | |
| PCB + JLCPCB assembly (qty 10) | 52.72 | 6-layer JLC06161H-3313, ENIG, impedance control, Standard PCBA, X-ray, SiP consignment |
| **Total per board, qty 10** | **232.62** | **Under the $300 target** |
| Total per board, qty 5 | ≈ 267.5 | PCB + assembly rises to $87.60 per board at qty 5 |

**Not included:** shipping, import duties or VAT, spare parts, the Tag-Connect TC2070 cable ($49, a tool), and the HDMI/USB-C cables and power supply.

### Ways to adjust cost

| Option | Δ per board |
|---|---:|
| Ship boards without the Wi-Fi module (the socket stays) | −55.00 |
| 16 GB eMMC module instead of 32 GB | −9.00 |
| ES8316 codec instead of TLV320AIC3104 | −0.70 |
| RTL8211F PHY instead of DP83867 (not recommended: no TI SDK reference) | −3.40 |
| ADV7513 bridge for real HDMI with audio, instead of the DVI-only TFP410 | +21.90 |
| Keep your exact layer order using the JLC06161H-3313**E** stackup | +6.73 (+$67.32 per order) |

## Changes forced by the in-stock rule

| Area | Original plan | Now | Why |
|---|---|---|---|
| HDMI bridge | SiI9022A | **TFP410PAPR** | SiI9022A, IT66121 and IT6263 are broker-only, and LT8618 has no stock. TFP410 is in stock (TI.com 11,487) and has a mainline Linux driver. It outputs **DVI**: video works on any HDMI monitor, but there is no HDMI audio or CEC, so audio comes from the codec. |
| PMIC package | TPS6521904**RHB** (5×5 mm) | TPS6521904**RSM** (4×4 mm, 0.4 mm pitch) | RHB is out at Digi-Key, Mouser and TI (JLC has 19). The RSM part has the same NVM, and Digi-Key has 2,524. |
| Ethernet PHY | DP83867IRRGZ | DP83867**IS**RGZR | The IR part is backordered to 2027. IS is a pin-compatible superset with the same driver; it needs dummy straps on RX_D1/RX_D3. |
| PHY 1.0 V LDO | TLV75510 | TLV757**10**PDBVR | Same SOT-23 pinout, in stock |
| 5 V converter | TPS630702 | TPS63070 | Stock and price |
| USB-PD | TPS65988 (dual-port, flash-configured) | **TPS25730** | Resistor-strapped sink with an integrated, protected 5 A switch. Set to 5–9 V, so it also runs from plain 5 V chargers. |
| UART bridge | FT4232HL at Mouser/Digi-Key (~$6) | FT4232HL at LCSC ($12.60) | Mouser and Digi-Key have 0 (50-week lead). LCSC has 3,109. |
| Connectors | GCT microSD, Amphenol HDMI, CUI jack, TE M.2, LINK-PP RJ45 | Hroparts, XFCN, PJ-320DB, LOTES, HanRun equivalents | The SK parts have 0–10 in stock |

## Stock risk: one line needs your decision

**eMMC module connector (LS Mtron GB042-34P-H10).** This is the board-side connector for the drop-in Hardkernel/PINE64/Radxa eMMC modules. Only Hong Kong brokers list it (about $0.50–0.60, 2,740 claimed). LCSC, Digi-Key and Mouser have none, and JLC has only placeholder entries. Options:

1. **Buy from a broker now** (cheap), test-fit with a module, and consign to JLC.
2. **Solder an eMMC chip on the board.** That is in stock at distributors, but costs about $45 for 32 GB, which is more than the module.

The modules themselves are in stock: PINE64 32 GB at $24.95, 16 GB at $15.95.

## SiP purchasing

Digi-Key holds the only stock (182, $44.06 at qty 10). Mouser shows 182 incoming on 2026-10-27. The factory lead time is 18 weeks. **Buy 10–12 SiPs now** (≈ $441–529) and consign them to JLC, or ask Octavo for a direct quote: its list price is $22.50, probably a volume price.

## JLCPCB stackup (free standard option)

JLC06161H-3313, 1.54 mm finished. The recommended layer order is **TOP / GND / SIG / GND / PWR / BOT**. In the order I first proposed, L3 sits 0.124 mm from the power plane, so its signals would reference power. Through vias of 0.15/0.25 mm with Octavo's one-via-between-balls escape fit within JLCPCB's limits. Filled and capped vias are standard on 6-layer boards at no cost. Full detail is in [`docs/research/bom/jlcpcb-stackup-and-cost.md`](../research/bom/jlcpcb-stackup-and-cost.md).

| Impedance | L1/L6 microstrip, W/S (mil) | L3 stripline, W/S (mil) |
|---|---|---|
| 50 Ω single-ended | 5.94 | 5.59 |
| 90 Ω diff (USB) | 5.34 / 6 | 5.03 / 6 |
| 100 Ω diff (Ethernet MDI, TMDS, CSI-2) | 4.69 / 8 | 4.33 / 8 |

## Schematic reconciliation (schematic v0.1, 2026-10-17)

The generated schematic (16 sheets, `hardware/gen`) has **687 designators: 629 fitted and 58 DNP**. Its parts match this BOM, apart from these additions made while drawing the sheets:

| Addition | Where | Why | ≈ $/board |
|---|---|---|---:|
| SS34 Schottky (D103) | 01 power input | TPS25730 datasheet §8.5: VBUS-to-GND clamp | 0.03 |
| BAT54WS (D902) | 09 USB | CH335F reset: keeps the hub out of CDP mode | 0.03 |
| BLM18KG601SN1D ×5 | 10 HDMI, 11 audio, 12 camera | Separate TFP410 DVDD/PVDD/TVDD filtering (datasheet Fig 7-3), codec analog, camera supply | 0.10 |
| Second zener + 3 resistors | 09 USB | USB1_VBUS divider (the AM62x host port also needs its VBUS pin handled) | 0.03 |
| More passives than estimated | all | 257 capacitors and 244 resistors fitted, against ~181 and ~196 estimated | ≈ 0.6 |
| DNP footprints | various | GB042-30P mechanical connector, VPP LDO, options | 0 |

**Net effect: about +$0.8 per board.** The estimate becomes ≈ $233.4 per board at qty 10. The five reset AND gates priced under Clock+Reset+Boot can go: the sheets hold peripheral resets with resistors instead. That saves $0.22.

### After the 2026-10-21 review (729 placed parts)

The review added the following:
- 3 × TPD1E10B06DPYR audio-jack ESD diodes;
- one BLM18KG601SN1D bead (FB310, VDDS_OSC0);
- 12 more fitted 0402 resistors: I2C0 series, PMIC mode pull-ups, pull-ups and links on the UART, SDIO and SD clock;
- 5 DNP de-skew straps;
- 13 bare test pads.

Cost: well under +$0.5 per board (estimate; not re-priced). Two capacitor values changed: C100 becomes 4.7 µF 25 V 0805 (CL21A475KAQNNNE) and C1506 becomes 10 µF 0603.

The CSV still has these known differences from the schematic. The schematic is right in each case:
- Beads are BLM18KG601SN1D 0603, not "600R 0805".
- The HDMI 10 µF caps are 0603, not 0402.
- No 1206 0R links (R1–R4) are used.
- Only 2 KT-0805G green LEDs are used, not 4.
- No SN74LVC1G08 gates are used.
- The 2.2 µF 0402 caps are rated 10 V, not 6.3 V.

## Line items (140 placed lines)

Plug-in modules and PCB/assembly fees are included as lines. Prices are USD per unit at the 10-board break.

| # | Group | Function | Qty | MPN | Manufacturer | Supplier | Unit $ | Ext $ | Stock |
|---|---|---|---:|---|---|---|---:|---:|---|
| 1 | Processor | Processor SiP: AM6254 (quad A53 @1.4 GHz) + 1 GB DDR4 + pas… | 1 | OSD6254-1G-IPM | Octavo Systems | Digi-Key (1676-OSD6254-1G…) | 44.0620 | 44.06 | Digi-Key 182 (Active, 18-… |
| 2 | Power | PMIC (3x buck, 4x LDO), NVM for AM62x DDR4 0.85 V core, 3.3… | 1 | TPS6521904RSMR | Texas Instruments | Digi-Key (296-TPS6521904R…) | 3.4490 | 3.45 | 2524 |
| 3 | Power | USB-PD sink controller w/ integrated 5 A power path (OVP/RC… | 1 | TPS25730DREFR | Texas Instruments | JLCPCB/LCSC (C22438973) | 2.5680 | 2.57 | 283 |
| 4 | Power | Always-on 3.3 V buck (VCC_3V3_MAIN) | 1 | LM61460AANRJRR | Texas Instruments | JLCPCB/LCSC (C2864505) | 1.5934 | 1.59 | 956 |
| 5 | Power | 5 V buck-boost (VCC_5V0: USB-A, HDMI 5 V, header 5 V) | 1 | TPS63070RNMR | Texas Instruments | JLCPCB/LCSC (C109322) | 1.1265 | 1.13 | 33251 |
| 6 | Power | LM61460 output caps (3.3 V) | 4 | CL31A476MPHNNNE | Samsung | JLCPCB/LCSC (C96123) | 0.1803 | 0.72 | 410152 |
| 7 | Power | Bulk 22 uF 25 V: PPHV/VMAIN (2) + TPS63070 output (3) | 5 | CL31A226KAHNNNE | Samsung | JLCPCB/LCSC (C12891) | 0.1238 | 0.62 | 491470 |
| 8 | Power | LM61460 input caps | 2 | CL31A106KBHNNNE | Samsung | JLCPCB/LCSC (C13585) | 0.2554 | 0.51 | 2288816 |
| 9 | Power | VBUS surge/ESD clamp | 1 | TVS2200DRVR | Texas Instruments | JLCPCB/LCSC (C523793) | 0.4621 | 0.46 | 1365 |
| 10 | Power | PMIC buck inductors (Buck1/2/3) | 3 | DFE252012F-R47M=P2 | Murata | JLCPCB/LCSC (C703140) | 0.1478 | 0.44 | 1654 |
| 11 | Power | USB-A VBUS current-limited switches (0.5 A each) | 2 | TPS2051BDBVR | Texas Instruments | JLCPCB/LCSC (C24593) | 0.1942 | 0.39 | 64563 |
| 12 | Power | CC1/CC2 ESD (short-to-VBUS tolerant) | 2 | PESD24VL1BA,115 | Nexperia | JLCPCB/LCSC (C69324) | 0.1749 | 0.35 | 19256 |
| 13 | Power | SD card VDD + VDDSHV5 IO supply dual switch | 1 | TPS22996DRLR | Texas Instruments | JLCPCB/LCSC (C34640248) | 0.3070 | 0.31 | 18518 |
| 14 | Power | PMIC buck output bulk (1 per buck) | 3 | CL21A476MQYNNNE | Samsung | JLCPCB/LCSC (C16780) | 0.1016 | 0.30 | 1545354 |
| 15 | Power | USB-A port VBUS bulk (>=120 uF per port) | 2 | RYHV10V150UF6*5 | Honor Elec | JLCPCB/LCSC (C48970647) | 0.1409 | 0.28 | 370 |
| 16 | Power | 3.3 V IO rail load switch (VCC_3V3_SYS), ON = PMIC GPO2 | 1 | TPS22965DSGR | Texas Instruments | JLCPCB/LCSC (C122837) | 0.2479 | 0.25 | 15234 |
| 17 | Power | Ethernet PHY 1.0 V core LDO (DP83867 VDD1P0) | 1 | TLV75710PDBVR | Texas Instruments | JLCPCB/LCSC (C2865385) | 0.2304 | 0.23 | 2113 |
| 18 | Power | Analog 1.8 V / VPP / PHY 2.5 V ferrite beads | 8 | BLM15PX121SN1D | Murata | JLCPCB/LCSC (C88970) | 0.0283 | 0.23 | 348880 |
| 19 | Power | USB-C PD power input + USB0 data (USB2) | 1 | TYPE-C-31-M-12 | Korean Hroparts Elec | JLCPCB/LCSC (C165948) | 0.1865 | 0.19 | 365172 |
| 20 | Power | Core analog ferrite beads (VDDA_CORE_USB / _CSIRX) | 2 | BLM18SG260TN1D | Murata | JLCPCB/LCSC (C87063) | 0.0848 | 0.17 | 42914 |
| 21 | Power | 5 V buck-boost inductor | 1 | MWSA0402S-1R5MT | Sunlord | JLCPCB/LCSC (C408334) | 0.1638 | 0.16 | 623 |
| 22 | Power | Small MLCC 10 uF 10 V 0603 (PMIC buck POL x3, TPS25730 VIN_… | 6 | CL10A106KP8NNNC | Samsung | JLCPCB/LCSC (C19702) | 0.0271 | 0.16 | 11164607 |
| 23 | Power | VBUS input cap (1) + TPS63070 input (2) | 3 | CL21A106KAYNNNE | Samsung | JLCPCB/LCSC (C15850) | 0.0438 | 0.13 | 6500138 |
| 24 | Power | 3.3 V buck inductor | 1 | MWSA0603S-4R7MT | Sunlord | JLCPCB/LCSC (C408447) | 0.1096 | 0.11 | 47178 |
| 25 | Power | Small MLCC 4.7 uF 10 V 0402 (PMIC PVIN_B1/B2/B3, PVIN_LDO34… | 5 | CL05A475MP5NRNC | Samsung | JLCPCB/LCSC (C23733) | 0.0206 | 0.10 | 2106975 |
| 26 | Power | Small MLCC 100 nF 16 V 0402 (HF decoupling, BOOT, VAUX, VBI… | 14 | CL05B104KO5NNNC | Samsung | JLCPCB/LCSC (C1525) | 0.0051 | 0.07 | 24757160 |
| 27 | Power | Resistors 0402 1 % (TPS25730 ADCIN straps + provision x4, L… | 40 | 0402WGF1002TCE (and similar v… | UNI-ROYAL | JLCPCB/LCSC (C25744) | 0.0015 | 0.06 | 20292353 |
| 28 | Power | Small MLCC 1 uF 25 V 0402 (LDO in/out, TPS22996 in/out, TPS… | 8 | CL05A105KA5NQNC | Samsung | JLCPCB/LCSC (C52923) | 0.0068 | 0.05 | 9087231 |
| 29 | Power | 40-pin header 5 V protection | 1 | BSMD1206-110-6V | BHFUSE | JLCPCB/LCSC (C2803344) | 0.0516 | 0.05 | 24034 |
| 30 | Power | Small MLCC 100 nF 50 V 0603 (LM61460 VIN HF x2, VBUS/VMAIN… | 4 | CC0603KRX7R9BB104 | YAGEO | JLCPCB/LCSC (C14663) | 0.0108 | 0.04 | 31897660 |
| 31 | Power | Small MLCC 2.2 uF 6.3 V 0402 (PMIC VSYS, VDD1P8, PVIN_LDO1/… | 7 | CL05A225MQ5NSNC | Samsung | JLCPCB/LCSC (C12530) | 0.0054 | 0.04 | 4363079 |
| 32 | Power | PMIC buck-output 0 Ohm test links (Buck1 x2 parallel, Buck2… | 4 | 1206W4F0000T5E | UNI-ROYAL | JLCPCB/LCSC (C17888) | 0.0085 | 0.03 | 2202661 |
| 33 | Power | Small MLCC C0G pF caps (VMON 22 pF, TPS22965 CT 220 pF, CC… | 5 | 0402CG220J500NT (and similar… | FH (Fenghua) | JLCPCB/LCSC (C1555) | 0.0026 | 0.01 | 1917153 |
| 34 | Power | PMIC LDO-output 0 Ohm test links (LDO1, LDO3, LDO4) | 3 | 0603WAF0000T5E | UNI-ROYAL | JLCPCB/LCSC (C21189) | 0.0022 | 0.01 | 23656090 |
| 35 | Clock+Reset+Boot | SoC MCU_OSC0 25 MHz LVCMOS clock (VDDS_OSC0 1.8 V; XO to VS… | 1 | ECS-2520MV-250-CN-TR | ECS Inc | LCSC/JLCPCB (C405464) | 1.3387 | 1.34 | 3477 |
| 36 | Clock+Reset+Boot | BOOTMODE[6:3] boot-device select DIP switch | 1 | 2.54-4P TPGT | SHOU HAN | LCSC/JLCPCB (C6331176) | 0.4229 | 0.42 | 45433 |
| 37 | Clock+Reset+Boot | Reset AND gates: SoC_PORz/JTAG-nRST + peripheral resets AND… | 5 | SN74LVC1G08DBVR | Texas Instruments | LCSC/JLCPCB (C7666) | 0.0449 | 0.22 | 69792 |
| 38 | Clock+Reset+Boot | Button debounce Schmitt buffers: RESET_REQz and USER button | 1 | SN74LVC2G17DBVR | Texas Instruments | LCSC/JLCPCB (C10429) | 0.2170 | 0.22 | 61719 |
| 39 | Clock+Reset+Boot | WKUP_LFOSC0 32.768 kHz crystal (CL 6-12 pF) | 1 | Q13FC13500003 | Seiko Epson | LCSC/JLCPCB (C99010) | 0.2035 | 0.20 | 45939 |
| 40 | Clock+Reset+Boot | MCU_PORz driver AND3 (PMIC nRSTOUT, JTAG nSRST, spare) in 1… | 1 | SN74LVC1G11DCKR | Texas Instruments | LCSC/JLCPCB (C529281) | 0.1546 | 0.15 | 6665 |
| 41 | Clock+Reset+Boot | Button ESD (one per button, SK D12/D13/D15) | 3 | TPD1E10B06DPYR | Texas Instruments | LCSC/JLCPCB (C48260) | 0.0446 | 0.13 | 288846 |
| 42 | Clock+Reset+Boot | Push buttons: POWER (PMIC PB), RESET (RESET_REQz), USER (MC… | 3 | TS-1187A-B-A-B | XKB Connection | LCSC/JLCPCB (C318884) | 0.0206 | 0.06 | 294963 |
| 43 | Clock+Reset+Boot | BOOTMODE fixed straps (BOOTMODE[15:7] and [2:0]: 25 MHz=011… | 12 | 0402WGF1002TCE | UNI-ROYAL | LCSC/JLCPCB (C25744) | 0.0015 | 0.02 | 20292880 |
| 44 | Clock+Reset+Boot | BOOTMODE[6:3] DIP pull-ups (switch ON = 1) | 4 | 0402WGF1001TCE | UNI-ROYAL | LCSC/JLCPCB (C11702) | 0.0035 | 0.01 | 13763230 |
| 45 | Clock+Reset+Boot | BOOTMODE[6:3] pull-downs behind DIP switch | 4 | 0402WGF4702TCE | UNI-ROYAL | LCSC/JLCPCB (C25792) | 0.0026 | 0.01 | 4979344 |
| 46 | Clock+Reset+Boot | 32.768 kHz load capacitors | 2 | 0402CG180J500NT | FH (Fenghua) | LCSC/JLCPCB (C1549) | 0.0027 | 0.01 | 790731 |
| 47 | Storage | eMMC module board-side signal connector (34-pin plug) | 1 | GB042-34P-H10-E3000 | LS Mtron (LS/LG Cable) | IC Components Ltd… (GB042-34P-H10-E…) | 0.6000 | 0.60 | 2740 (broker claim; Jotri… |
| 48 | Storage | microSD socket push-push with card-detect | 1 | TF-01A | Korean Hroparts Elec | JLCPCB/LCSC (C91145) | 0.1927 | 0.19 | 184825 |
| 49 | Storage | microSD ESD array (CLK/CMD/DAT0-3/CD; 8 ch over 2 parts) | 2 | TPD4E05U06DQAR | Texas Instruments | JLCPCB/LCSC (C138714) | 0.0830 | 0.17 | 215912 |
| 50 | Storage | Storage passives (SD: 6x47k pull-ups incl CD, 100R CD serie… | 18 | various 0402/0603 (C25792 C25… | UNI-ROYAL / Samsung | JLCPCB/LCSC (various basic) | 0.0083 | 0.15 | >1M each |
| 51 | USB | USB 2.0 hub controller (USB1 -> 2 downstream used of 4) | 1 | CH335F | WCH (Jiangsu Qin Heng) | JLCPCB/LCSC (C5137013) | 0.9192 | 0.92 | 6199 |
| 52 | USB | USB-A port ESD (D+/D-/VBUS per port) | 2 | USBLC6-2SC6 | STMicroelectronics | JLCPCB/LCSC (C7519) | 0.1774 | 0.35 | 34334 |
| 53 | USB | USB0 D+/D- ESD | 1 | ESD122DMXR | Texas Instruments | JLCPCB/LCSC (C544474) | 0.3476 | 0.35 | 34664 |
| 54 | USB | USB-A receptacle dual stacked (2 host ports) | 1 | BX-TYPE-A-MWC44 | Bossie | JLCPCB/LCSC (C18077688) | 0.2918 | 0.29 | 468 |
| 55 | USB | USB passives (hub: 2x1uF, 3x0.1uF, 10uF, 2x10k PSELF/RESET;… | 13 | various 0402/0603/0805 | UNI-ROYAL / Samsung | JLCPCB/LCSC (various basic) | 0.0115 | 0.15 | >1M each |
| 56 | USB | USB-A D+/D- common-mode choke (fit; 0R bypass footprint DNP) | 2 | SDCW2012-2-900TF | Sunlord | JLCPCB/LCSC (C54888) | 0.0593 | 0.12 | 65898 |
| 57 | USB | Hub crystal 12 MHz (no external load caps; CH335 has ~16pF… | 1 | X322512MSB4SI | YXC | JLCPCB/LCSC (C9002) | 0.0952 | 0.10 | 234110 |
| 58 | USB | USB0 (USB-C device port) D+/D- common-mode choke | 1 | SDCW2012-2-900TF | Sunlord | JLCPCB/LCSC (C54888) | 0.0593 | 0.06 | 65898 |
| 59 | USB | USB0_VBUS clamp zener 6.8V (AM62x DS Fig 8-4 divider) | 1 | LBZX84C6V8LT1G | LRC | JLCPCB/LCSC (C12746) | 0.0190 | 0.02 | 18902 |
| 60 | Ethernet | Gigabit Ethernet PHY (RGMII1) | 1 | DP83867ISRGZR | Texas Instruments | JLCPCB/LCSC (C543036) | 4.5303 | 4.53 | 777 (LCSC 773) |
| 61 | Ethernet | RJ45 with integrated 1000BASE-T magnetics + 2 LEDs | 1 | HR911130A | HanRun | JLCPCB/LCSC (C54408) | 2.3541 | 2.35 | 20781 (LCSC 1707) |
| 62 | Ethernet | Ethernet passives (decoupling per DP83867 Fig 9-7: ~9x1uF,… | 34 | various (C52923 C1525 C19702… | Samsung / UNI-ROYAL /… | JLCPCB/LCSC (various basic) | 0.0074 | 0.25 | >790k each |
| 63 | Ethernet | PHY crystal 25 MHz | 1 | X322525MOB4SI | YXC | JLCPCB/LCSC (C9006) | 0.0949 | 0.09 | 244430 |
| 64 | Ethernet | PHY strap resistors (4-level straps RX_D0, RX_D2, RX_CTRL m… | 12 | 0402 1% various (e.g. C25744… | UNI-ROYAL | JLCPCB/LCSC (various basic) | 0.0021 | 0.03 | >1M each |
| 65 | Ethernet | RGMII series resistors 22R (6 TX at SoC + 6 RX at PHY) | 12 | 0402WGF220JTCE | UNI-ROYAL | JLCPCB/LCSC (C25092) | 0.0015 | 0.02 | 3973188 |
| 66 | Ethernet | PHY RBIAS 11k 1% | 1 | 0402WGF1102TCE | UNI-ROYAL | JLCPCB/LCSC (C25749) | 0.0021 | 0.00 | 255608 |
| 67 | HDMI | DPI (24-bit RGB) to HDMI-connector TMDS transmitter (DVI 1.… | 1 | TFP410PAPR | Texas Instruments | JLCPCB/LCSC (C7498519) | 4.6021 | 4.60 | JLC 110 / LCSC 109; TI.co… |
| 68 | HDMI | HDMI companion: 5V load switch, DDC/CEC/HPD level shift, 12… | 1 | TPD12S016PWR | Texas Instruments | JLCPCB/LCSC (C201665) | 0.9453 | 0.95 | JLC 3,447; TI.com 20,549 |
| 69 | HDMI | HDMI type-A receptacle | 1 | HDMI-A-19F-S-D | XFCN | JLCPCB/LCSC (C5151728) | 0.1852 | 0.19 | JLC 3,436 / LCSC 3,060 |
| 70 | HDMI | HDMI section passives (rough) | 1 | various | various | JLCPCB basic (C1525/C52923/C1…) | 0.1500 | 0.15 | JLC basic, >1M each |
| 71 | Audio | Stereo audio codec (HP out + mic in), I2S + I2C | 1 | TLV320AIC3104IRHBR | Texas Instruments | JLCPCB/LCSC (C181753) | 1.2326 | 1.23 | JLC 769; TI.com 14,577 |
| 72 | Audio | Audio MCLK 12.288 MHz oscillator | 1 | 3N12288G33YC | SJK (Shenzhen Crystal… | JLCPCB/LCSC (C252334) | 0.5371 | 0.54 | JLC 448 |
| 73 | Audio | Audio passives (rough) | 1 | various | various | JLCPCB basic (C1525/C52923/C1…) | 0.3400 | 0.34 | JLC basic, >1M each |
| 74 | Audio | 3.5 mm 4-pole TRRS jack (headphone + mic) | 1 | PJ-320DB-5A | Korean Hroparts Elec | JLCPCB/LCSC (C707225) | 0.1452 | 0.15 | JLC 412 |
| 75 | Camera | 15-pin 1.0 mm CSI FPC (RPi camera pinout) | 1 | 1-1734248-5 | TE Connectivity | JLCPCB/LCSC (C2922285) | 0.9453 | 0.95 | JLC 3,324 |
| 76 | Camera | Camera passives (rough) | 1 | various | various | JLCPCB basic (C1525/C52923/C1…) | 0.0600 | 0.06 | JLC basic, >1M each |
| 77 | Wireless | M.2 module standoff (SMT M2 threaded, 1.5 mm) | 1 | 9774015243R | Wurth Elektronik | JLCPCB/LCSC (C22431324) | 0.6106 | 0.61 | JLC 1,763 |
| 78 | Wireless | M.2 Key-E 2230 socket, 67P, H3.2 | 1 | APCI0085-P002A | LOTES | JLCPCB/LCSC (C841649) | 0.3641 | 0.36 | JLC 6,396 / LCSC 6,336 |
| 79 | Wireless | Wireless passives (rough) | 1 | various | various | JLCPCB basic (C25792/C25744/C…) | 0.2900 | 0.29 | JLC basic, >1M each |
| 80 | Wireless | M.2 module retaining screw M2 x 4 pan head | 1 | PM2X4 (nickel) | Shuntian | JLCPCB/LCSC (C357393) | 0.0018 | 0.00 | JLC 11,579 |
| 81 | Expansion | 40-pin 2x20 2.54 mm header (RPi pinout) | 1 | 2541WV-2x20P | HanElectricity | JLCPCB/LCSC (C25503140) | 0.1377 | 0.14 | JLC 3,873 |
| 82 | Expansion | HAT-ID EEPROM 24C32 on dedicated ID_SD/ID_SC bus | 1 | BL24C32A-SFRC | Shanghai Belling | JLCPCB/LCSC (C177775) | 0.1076 | 0.11 | JLC 11,669 |
| 83 | Expansion | Expansion passives (rough) | 1 | various | various | JLCPCB basic (C25879/C1525/C1…) | 0.0600 | 0.06 | JLC basic, >1M each |
| 84 | Expansion | Header IO series resistors 33R (back-power/ESD damping) | 28 | 0402WGF330JTCE | UNI-ROYAL | JLCPCB/LCSC (C25105) | 0.0012 | 0.03 | JLC 1,682,522 |
| 85 | Debug | Quad USB-UART bridge: MAIN_UART0 (Linux), MAIN_UART1 (TIFS)… | 1 | FT4232HL-Reel | FTDI | LCSC/JLCPCB (C56742) | 12.6031 | 12.60 | 3109 |
| 86 | Debug | UART power-domain isolation buffers (FT4232 side on debug-V… | 2 | SN74AVC4T245PWR | Texas Instruments | LCSC/JLCPCB (C81461) | 0.2444 | 0.49 | 18217 |
| 87 | Debug | FT4232 config EEPROM (93LC46B, 16-bit org) | 1 | 93LC46BT-I/OT | Microchip | LCSC/JLCPCB (C2649426) | 0.4392 | 0.44 | 1081 |
| 88 | Debug | Debug USB connector (USB 2.0 only, UFP) | 1 | TYPE-C-31-M-12 | Korean Hroparts (HRO) | LCSC/JLCPCB (C165948) | 0.1865 | 0.19 | 365192 |
| 89 | Debug | 3.3 V LDO for FT4232 + buffer A-side, powered from debug US… | 1 | AP2112K-3.3TRG1 | Diodes Inc | LCSC/JLCPCB (C51118) | 0.1717 | 0.17 | 7645 |
| 90 | Debug | JTAG ESD on Tag-Connect lines (TCK/TMS/TDI/TDO/TRSTn/EMU0/E… | 2 | TPD4E05U06DQAR | Texas Instruments | LCSC/JLCPCB (C138714) | 0.0830 | 0.17 | 215912 |
| 91 | Debug | Debug USB D+/D- ESD | 1 | TPD2E001DRLR | Texas Instruments | LCSC/JLCPCB (C150526) | 0.1610 | 0.16 | 6370 |
| 92 | Debug | FT4232 12 MHz crystal | 1 | X322512MSB4SI | YXC | LCSC/JLCPCB (C9002) | 0.0952 | 0.10 | 234140 |
| 93 | Debug | Debug VBUS ESD | 1 | TPD1E10B06DPYR | Texas Instruments | LCSC/JLCPCB (C48260) | 0.0446 | 0.04 | 288846 |
| 94 | Debug | FT4232 VPHY/VPLL ferrite beads | 2 | BLM18PG121SN1D | Murata | LCSC/JLCPCB (C14709) | 0.0152 | 0.03 | 2705359 |
| 95 | Debug | 12 MHz crystal load caps | 2 | 0402CG330J500NT | FH (Fenghua) | LCSC/JLCPCB (C1562) | 0.0032 | 0.01 | 1278855 |
| 96 | Debug | USB-C CC Rd pull-downs (device/UFP) | 2 | 0402WGF5101TCE | UNI-ROYAL | LCSC/JLCPCB (C25905) | 0.0023 | 0.00 | 5094583 |
| 97 | Debug | FT4232 REF resistor | 1 | 0402WGF1202TCE | UNI-ROYAL | LCSC/JLCPCB (C25752) | 0.0018 | 0.00 | 952381 |
| 98 | Debug | JTAG connector: Tag-Connect TC2070 (14-pin, TI-14 pinout in… | 1 | TC2070-IDC-NL footprint | Tag-Connect | n/a  | 0.0000 | 0.00 | n/a |
| 99 | Misc | Temperature sensor near SiP (I2C0 @0x48) | 1 | TMP102AIDRLR | Texas Instruments | LCSC/JLCPCB (C99269) | 0.5420 | 0.54 | 38027 |
| 100 | Misc | Board-ID EEPROM for TI U-Boot board detect (I2C0 @0x51, 2-b… | 1 | AT24C512C-SSHD-T | Microchip | LCSC/JLCPCB (C12371) | 0.4229 | 0.42 | 28988 |
| 101 | Misc | LEDs green: 3V3 power, heartbeat, user1, debug-USB power | 4 | KT-0805G | Hubei KENTO | LCSC/JLCPCB (C2297) | 0.0164 | 0.07 | 2660137 |
| 102 | Misc | LEDs red: user2, 5 V input present | 2 | KT-0603R | Hubei KENTO | LCSC/JLCPCB (C2286) | 0.0076 | 0.02 | 7572604 |
| 103 | Misc | Red-LED series resistors | 2 | 0402WGF1001TCE | UNI-ROYAL | LCSC/JLCPCB (C11702) | 0.0035 | 0.01 | 13763230 |
| 104 | Misc | Green-LED series resistors | 4 | 0402WGF3300TCE | UNI-ROYAL | LCSC/JLCPCB (C25104) | 0.0011 | 0.00 | 1897480 |
| 105 | Misc | Test points (spare UART consoles, OBSCLK, PORz/RESETSTATz,… | 12 | bare SMD test pad | - | n/a  | 0.0000 | 0.00 | n/a |
| 106 | Passives (SiP + generic) | SiP decoupling Table 4-3: 4.7 uF on VDDA_CORE_CSIRX0/USB/VD… | 9 | CL05A475MP5NRNC | Samsung | LCSC/JLCPCB (C23733) | 0.0206 | 0.19 | 2106975 |
| 107 | Passives (SiP + generic) | Generic 100 nF: oscillator 1, logic gates 7, button RC 2, I… | 29 | CL05B104KO5NNNC | Samsung | LCSC/JLCPCB (C1525) | 0.0051 | 0.15 | 24757290 |
| 108 | Passives (SiP + generic) | SiP decoupling per OSD62x-PM DS Rev 2.0 Table 4-3: VDD_CORE… | 26 | CL05B104KO5NNNC | Samsung | LCSC/JLCPCB (C1525) | 0.0051 | 0.13 | 24757290 |
| 109 | Passives (SiP + generic) | SiP IO/aux rails not in Table 4-3 (VDDSHV0-6, VDDSHV_MCU, V… | 16 | CL05B104KO5NNNC | Samsung | LCSC/JLCPCB (C1525) | 0.0051 | 0.08 | 24757290 |
| 110 | Passives (SiP + generic) | SiP IO/aux rails not in Table 4-3: 1 uF (9 VDDSHV rails + V… | 10 | CL05A105KA5NQNC | Samsung | LCSC/JLCPCB (C52923) | 0.0068 | 0.07 | 9087216 |
| 111 | Passives (SiP + generic) | 10 k pulls: RESET_REQz, MCU_RESETz, 3 buttons, PORz_OUT/RES… | 36 | 0402WGF1002TCE | UNI-ROYAL | LCSC/JLCPCB (C25744) | 0.0015 | 0.05 | 20292880 |
| 112 | Passives (SiP + generic) | Generic 4.7 uF (FT4232 VPHY/VPLL after ferrites) | 2 | CL05A475MP5NRNC | Samsung | LCSC/JLCPCB (C23733) | 0.0206 | 0.04 | 2106975 |
| 113 | Passives (SiP + generic) | 47 pF slew limiters: EXTINTn + MCU_I2C0/WKUP_I2C0 (62 R + 4… | 5 | 0402CG470J500NT | FH (Fenghua) | LCSC/JLCPCB (C1567) | 0.0081 | 0.04 | 562346 |
| 114 | Passives (SiP + generic) | SiP decoupling Table 4-3: 10 uF on VDD_CORE | 1 | CL10A106KP8NNNC | Samsung | LCSC/JLCPCB (C19702) | 0.0271 | 0.03 | 11164622 |
| 115 | Passives (SiP + generic) | Generic 10 uF (debug USB VBUS bulk) | 1 | CL10A106KP8NNNC | Samsung | LCSC/JLCPCB (C19702) | 0.0271 | 0.03 | 11164622 |
| 116 | Passives (SiP + generic) | SiP decoupling Table 4-3: 1 uF on VDDA_1P8_OLDI0 (1), VPP e… | 3 | CL05A105KA5NQNC | Samsung | LCSC/JLCPCB (C52923) | 0.0068 | 0.02 | 9087216 |
| 117 | Passives (SiP + generic) | Generic 1 uF (debug LDO in/out, FT4232 VREGOUT) | 3 | CL05A105KA5NQNC | Samsung | LCSC/JLCPCB (C52923) | 0.0068 | 0.02 | 9087216 |
| 118 | Passives (SiP + generic) | 100 k pull-downs: MCU_PORz, peripheral reset AND in/outputs… | 12 | 0402WGF1003TCE | UNI-ROYAL | LCSC/JLCPCB (C25741) | 0.0016 | 0.02 | 9217948 |
| 119 | Passives (SiP + generic) | 2.2 k: I2C0/MCU_I2C0/WKUP_I2C0 pull-ups (6), FT4232 EEPROM… | 7 | 0402WGF2201TCE | UNI-ROYAL | LCSC/JLCPCB (C25879) | 0.0011 | 0.01 | 2128914 |
| 120 | Passives (SiP + generic) | 1 k: button RC series (2) | 2 | 0402WGF1001TCE | UNI-ROYAL | LCSC/JLCPCB (C11702) | 0.0035 | 0.01 | 13763230 |
| 121 | Passives (SiP + generic) | 62 R: EXTINTn + MCU_I2C0/WKUP_I2C0 slew limiters | 5 | 0402WGF620JTCE | UNI-ROYAL | LCSC/JLCPCB (C4962) | 0.0012 | 0.01 | 25661 |
| 122 | Passives (SiP + generic) | Generic 2.2 uF (debug LDO output) | 1 | CL05A225MQ5NSNC | Samsung | LCSC/JLCPCB (C12530) | 0.0054 | 0.01 | 4363220 |
| 123 | Passives (SiP + generic) | 22 pF glitch filters on MCU_PORz and RESET_REQz | 2 | 0402CG220J500NT | FH (Fenghua) | LCSC/JLCPCB (C1555) | 0.0026 | 0.01 | 1917083 |
| 124 | Passives (SiP + generic) | 47 R: I2C0 (emulated open-drain) series | 2 | 0402WGF470JTCE | UNI-ROYAL | LCSC/JLCPCB (C25118) | 0.0023 | 0.00 | 331205 |
| 125 | Passives (SiP + generic) | Generic 10 nF (FT4232 VPLL/LDO NR) | 1 | CL05B103KB5NNNC | Samsung | LCSC/JLCPCB (C15195) | 0.0041 | 0.00 | 6164399 |
| 126 | Passives (SiP + generic) | 22 R: 25 MHz clock series, JTAG TDO series | 2 | 0402WGF220JTCE | UNI-ROYAL | LCSC/JLCPCB (C25092) | 0.0015 | 0.00 | 3973198 |
| 127 | Passives (SiP + generic) | 0 R: debug USB shield link | 1 | 0402WGF0000TCE | UNI-ROYAL | LCSC/JLCPCB (C17168) | 0.0011 | 0.00 | 8664410 |
| 128 | Storage (module, plug-in) | eMMC module 32 GB (plugs into J_EMMC1) | 1 | 32GB eMMC Module | PINE64 | PINE64 store (32GB eMMC Module) | 24.9500 | 24.95 | In stock (qty not publish… |
| 129 | Wireless (module, plug-in) | Wi-Fi 6 + BLE M.2 2230 Key-E card | 1 | M2-CC3351 | Texas Instruments | TI.com (M2-CC3351) | 55.0000 | 55.00 | TI.com 74 (store inventor… |
| 130 | PCB + Assembly | Bare PCB fabrication | 1 | APE-SBC rev A (JLC06161H-3313) | JLCPCB | JLCPCB (JLC06161H-3313) | 16.2530 | 16.25 | n/a |
| 131 | PCB + Assembly | Feeder loading fee (unique parts) | 1 | 70 unique part numbers x $1.53 | JLCPCB | JLCPCB (Standard PCBA) | 10.7100 | 10.71 | n/a |
| 132 | PCB + Assembly | X-ray inspection | 1 | ~20 X-ray parts/board | JLCPCB | JLCPCB (Standard PCBA) | 9.8000 | 9.80 | n/a |
| 133 | PCB + Assembly | SiP consignment (handling + inbound courier) | 1 | OSD6254-1G-IPM consigned (JLC… | JLCPCB | JLCPCB (C49026186) | 5.5000 | 5.50 | n/a |
| 134 | PCB + Assembly | SMT placement (per joint) | 1 | ~1900 SMT joints/board x $0.0… | JLCPCB | JLCPCB (Standard PCBA) | 3.0400 | 3.04 | n/a |
| 135 | PCB + Assembly | PCBA setup (engineering) fee | 1 | Standard PCBA setup, single s… | JLCPCB | JLCPCB (Standard PCBA) | 2.5560 | 2.56 | n/a |
| 136 | PCB + Assembly | Assembly fixture (Standard, rigid) | 1 | 2 fixtures (1-29 pcs) x $8.21 | JLCPCB | JLCPCB (Standard PCBA) | 1.6420 | 1.64 | n/a |
| 137 | PCB + Assembly | THT hand/wave soldering | 1 | ~70 THT joints/board x $0.016… | JLCPCB | JLCPCB (Standard PCBA) | 1.5060 | 1.51 | n/a |
| 138 | PCB + Assembly | SMT stencil | 1 | Standard PCBA stencil, single… | JLCPCB | JLCPCB (Standard PCBA) | 0.8210 | 0.82 | n/a |
| 139 | PCB + Assembly | MSL bake of SiP (MSL 4) | 1 | 48 h bake service | JLCPCB | JLCPCB (Bake service) | 0.8000 | 0.80 | n/a |
| 140 | PCB + Assembly | Packing + confirm parts placement | 1 | packing $0.50 + area; placeme… | JLCPCB | JLCPCB (Standard PCBA) | 0.0950 | 0.10 | n/a |
