# APE-SBC power subsystem: BOM notes

**Date:** 2026-10-17

**Scope:** the USB-PD input through every regulator, load switch, power magnetic, ferrite and bulk capacitor for the OSD6254-1G-IPM SBC (100 x 70 mm, 6-layer, JLCPCB PCBA).

**BOM file:** `bom_power.csv`, in this folder.

**Section subtotal: $15.23 per board.**
- That covers 33 placed BOM lines (144 placements), priced at the 10-board price break.
- JLCPCB assembly fees are not included; see §4.
- **Every placed line is STOCK OK:** its chosen supplier holds at least 50 boards' worth today.
- The only STOCK RISK rows are two qty-0 alternates.

---

## 0. Stock check (requirement: stock ≥ 10 boards, preferably ≥ 50 boards, at the chosen supplier)

Stock figures were checked 2026-10-17 through the JLCPCB parts API, the LCSC API, and the Digi-Key, Mouser, Arrow and TI store pages. Two parts changed because of stock:

| Item | First choice | Stock problem | In-stock choice now in the BOM |
|---|---|---|---|
| PMIC U4 | TPS6521904**RHBR** (SK part, 5x5 mm) | JLC/LCSC 19 pcs. Digi-Key **0** (26 wk; ~3,000 due 09-Dec-2026). Mouser **0** (2,894 expected 02-Nov-2026). TI store out of stock. Not listed at Arrow. | **TPS6521904RSMR** (same NVM 04, 4x4 mm QFN-32, 0.4 mm pitch). Digi-Key **2,524** at $3.449 @10 (296-TPS6521904RSMRCT-ND). Mouser **2,680** at $3.49 @10 (595-TPS6521904RSMR). Arrow: quote only. TI store: out of stock. JLC library: C32975654, 5 pcs only. Buy through JLC global sourcing or consign it. |
| PD controller U1 | TPS25730**A**DREFR | JLC 39 pcs (fewer than 50 boards; Digi-Key has 1,739) | **TPS25730DREFR**, JLC **283** pcs. Same REF package and pinout. |

**TPS6521904 is in stock, so no NVM substitution (TPS6521907 or TPS6521905) is needed.** The cost of staying on 04 is a different footprint: RSM instead of the SK's RHB. TI's TPS65219EVM-RSM is the layout reference.

Every other placed part has at least 185 boards' worth at JLC. The tightest are:
- the 150 µF polymer: 370 pcs, 2 per board
- MWSA0402S-1R5MT: 623 pcs
- LM61460AANRJRR: 956 pcs
- TVS2200DRVR: 1,365 pcs

---

## 1. USB-PD sink controller: comparison and recommendation

The PD controller has to work with no firmware and no host, because it negotiates before the SoC boots. D+/D- go straight from the receptacle to SoC USB0 for gadget and DFU. Prices are the JLC unit price at qty 10.

| Option | JLC C# / price / stock | Configuration | Voltage request and fallback | Power path and protection | I2C status | USB2 data impact | Verdict |
|---|---|---|---|---|---|---|---|
| **TI TPS25730D** (exists; datasheet SLVSGP9, Oct 2023) | C22438973 / **$2.57** / 283 | Resistor straps on ADCIN1-4. No EEPROM, MCU or firmware. | Sets a minimum voltage (5/9/12/15/20 V), a maximum voltage (9/12/15/20 V) and an operating/max current. It requests a PDO inside that window. With the minimum at 5 V it falls back to 5 V, and non-PD 5 V sources work as an implicit contract. | **Integrated 16 mΩ, 5 A PPHV switch with OVP (2-4 µs) and reverse-current protection.** VBUS 4-22 V operating, 28 V abs max. Dead-battery LDO from VBUS. | Yes: I2C target at 0x20/0x21. GPIOs: SINK_EN, PLUG_EVENT, CAP_MIS, PLUG_FLIP, DBG_ACC, plus FAULT_IN. | None (CC pins only; no D+/D- pins) | **Recommended** |
| TI TPS25730A (PD3.2 certified, TID 15340; datasheet Rev A, Jul 2026) | C55128590 / $2.19 / 39. Digi-Key: 1,739 | Same straps | Same | Same | Same | None | Pin-compatible alternate. Its dead-battery mode is EnableSinkAfterContract. |
| TI TPS25730S | C22390380 / $1.94 / 786 | Same | Same | Gate drive for external back-to-back NFETs | Yes | None | Cheaper IC, but the external FETs cancel the saving |
| TI TPS25750D | C2868209 / $2.20 / 320 | Needs a config image in an I2C EEPROM, or a host patch download each boot | Fully configurable; can also act as DRP/source | Integrated 20 V / 5 A | Yes. Mainline Linux tps6598x driver. | None | Capable, but not standalone: needs an EEPROM and a tool flow |
| ST STUSB4500 | C2678061 / $2.41 / 5,345 | 3 sink PDOs in on-chip NVM | Takes the highest matching PDO; falls back to 5 V | External PMOS (VBUS_EN_SNK) | Yes (0x28) | None | **Factory NVM asks for 15 V and 20 V (PDO2/PDO3)**, which is above the 16 V buck-boost rating until the NVM is reprogrammed |
| WCH CH224K / CH224D (and Q/A) | K: C970725 / $0.39 / **0**. D: C3975094 / $0.34 / 14,500. Q: C46061833 / $0.36 / 11,705 | One CFG resistor picks one fixed voltage; leaving CFG open requests 20 V | Fallback when the voltage is not offered is not documented in English | No protected power path | K/D: no. Q/A: yes (unverified addresses) | Has D+/D- pins for BC1.2/QC; leave them unconnected | Cheapest, weak documentation, no OVP switch |
| Hynetek HUSB238 (runner-up) | C7471904 / $0.47 / 13,742 | VSET/ISET resistors | Highest PDO at or below VSET, else the next lower | External PMOS gate driver; OVP/UVP | Yes (0x08) | Has D+/D- pins for BC1.2; leave them unconnected | USB-IF certified (TID 3666). About $2 cheaper with its PFET, but no integrated protected switch. |
| TI TPS65988 (as on the SK) | C2156209 / $8.28 / 200 | Dual-port, config in SPI flash | Fully configurable | Two integrated paths | Yes | None | Overkill |

**Recommendation: TPS25730DREFR, configured for 5 V minimum and 9 V maximum.**
- It is standalone and certified, and its integrated power switch has OVP and RCP. That replaces a separate eFuse/OVP stage.
- Its I2C status is readable from Linux, and it does not touch D+/D-.
- The A revision is the same footprint, so either can be fitted.

**Straps** (datasheet Table 8-1 / 8-3 / 8-6):
- **ADCIN1 = GND:** decoded 0, so the minimum is 5 V and the I2C address is 0x20.
- **ADCIN2 = 100 kΩ to LDO_3V3, 4.99 kΩ to GND:** DIV ≈ 0.0475, decoded 1, so the maximum is 9 V. For 15 V, tie ADCIN2 to LDO_1V5 (decoded 5) instead.
- **This 5 V / 9 V pair selects dead-battery mode AlwaysEnableSink.** The sink path closes on any source, so legacy 5 V chargers and PC ports always power the board.
- **ADCIN3 = decoded 1 (same divider), ADCIN4 = LDO_1V5 (decoded 5):** operating current 1.5 A, maximum 3 A. CAP_MIS then flags a source that is too weak, and Linux reads the contract over I2C to budget the USB-A ports.
- **FAULT_IN:** pull high, or drive it from a SoC GPIO so software can force a re-attach.
- **If you fit TPS25730A instead:** its dead-battery mode is EnableSinkAfterContract. Set the operating current to 0.5 A (ADCIN3 = 0, ADCIN4 = LDO_1V5) so a 5 V / 500 mA source still enables the path.

**Why 9 V rather than 15 V:**
- Every PD charger of 18 W or more offers 9 V. 9 V x 3 A = 27 W, which covers the ~20 W non-simultaneous worst case.
- At 9 V, the 16 V-max buck-boost and all VMAIN capacitors keep a wide margin. At 15 V (up to 15.75 V within tolerance), the TPS63070 would have only about 0.25 V of headroom.

---

## 2. Power tree (VBUS 5 V implicit or 9 V PD; parts after the switch rated ≥ 16 V, controller rated 28 V)

```
USB-C J1 (VBUS 5 V / 9 V; D+/D- -> SoC USB0)
 ├─ D1 TVS2200 (VBUS), D2/D3 PESD24VL1BA (CC1/CC2)
 └─ U1 TPS25730D  PPHV 16 mΩ 5 A, OVP/RCP  ->  VMAIN 5-9 V (≤27 W)
      ├─ U2 LM61460 (3-36 V, 6 A) -> VCC_3V3_MAIN 3.3 V (always on)
      │    ├─ U4 TPS6521904RSMR VSYS + PVIN_B1/B2/B3/LDO1/LDO34
      │    │    ├─ Buck1 0.85 V 3.5 A -> VDD_CORE + VDDR_CORE + VDD_CANUART; FB9/FB10 26 Ω -> VDDA_CORE_USB/_CSIRX
      │    │    ├─ Buck2 1.8 V 2 A   -> VDDSHV1/4/6, eMMC VCCQ, M.2 1.8 V, codec 1.8 V, OSPI; U7 TLV75710 -> 1.0 V PHY core
      │    │    ├─ Buck3 1.2 V 2 A   -> SiP VDDS_DDR (DDR4 VDD/VDDQ), HDMI bridge 1.2 V
      │    │    ├─ LDO1 3.3/1.8 V    -> U8 TPS22996 ch2 -> VDDSHV5 (SD IO)
      │    │    ├─ LDO3 1.8 V (slow) -> VDDA_1V8 -> FB1-FB6 120 Ω -> analog 1.8 V, VDDS_OSC0
      │    │    ├─ LDO4 2.5 V (slow) -> FB7 -> DDR_VPP ; FB8 -> DP83867 VDDA2P5
      │    │    └─ GPO2 -> U5 TPS22965 ON
      │    ├─ U5 TPS22965 (CT 220 pF, QOD) -> VCC_3V3_SYS 3.3 V
      │    │    ├─ U8 TPS22996 ch1 -> VDD_SD ; U6 TLV75518 (DNP) -> VPP_1V8 eFuse
      │    │    └─ VDDSHV0/2/3, VDDSHV_MCU, VDDA_3P3_USB, M.2 3.3 V, PHY VDDIO, codec, header 3.3 V ...
      │    └─ VDDSHV_CANUART (always on), U1 VIN_3V3
      └─ U3 TPS63070 buck-boost (2-16 V) -> VCC_5V0 5.0 V
           ├─ U9/U10 TPS2051B (0.5 A each) -> USB-A VBUS x2 (150 µF polymer each)
           ├─ F1 1.1 A PTC -> 40-pin header 5 V
           ├─ HDMI +5 V (≤55 mA; its limit/ESD part lives in the HDMI section)
           └─ VMON_VSYS divider 10 k / 1.1 k + 22 pF -> SoC VMON_VSYS (trip ≈ 4.54 V)
```

| Rail | Source part | Input | Output | Rating | Budget (worst case) | Loads |
|---|---|---|---|---|---|---|
| VBUS / VMAIN | TPS25730D PPHV switch | USB-C VBUS | 5 V non-PD / 9 V PD | 5 A switch; 3 A cable | 20 W, about 2.3 A at 9 V. A 5 V source limits the board to what it offers (≤15 W). | LM61460, TPS63070 |
| VCC_3V3_MAIN | LM61460AANRJRR + 4.7 µH | VMAIN | 3.3 V | 6 A | ~5.3 A worst (SK budget 5.35 A); typically 1.5-2.5 A | PMIC VSYS/PVINs, TPS22965, CANUART IO, TPS25730 VIN_3V3 |
| VCC_5V0 | TPS63070RNMR + 1.5 µH | VMAIN | 5.0 V, regulated even from a 5 V input | 2 A | ~1.6 A | 2x USB-A (1 A total), header 5 V, HDMI 5 V, VMON |
| VDD_CORE | PMIC Buck1 + 0.47 µH | 3V3_MAIN | 0.85 V | 3.5 A | 2.7 A | VDD_CORE, VDDR_CORE, VDDA_CORE_*, VDD_CANUART |
| VDD_1V8 | PMIC Buck2 + 0.47 µH | 3V3_MAIN | 1.8 V | 2 A | ~1.2 A (includes the 0.22 A PHY LDO) | 1.8 V IO banks, eMMC VCCQ, M.2 1.8 V, codec, 1.0 V LDO |
| VDDS_DDR_1V2 | PMIC Buck3 + 0.47 µH | 3V3_MAIN | 1.2 V | 2 A | ~0.9 A | SiP VDDS_DDR (0.6-0.8 A), HDMI bridge 1.2 V |
| VDDSHV5_SD | PMIC LDO1 → TPS22996 ch2 | 3V3_MAIN | 3.3 V or 1.8 V (VSEL_SD) | 0.4 A | 50 mA | SoC VDDSHV5, SD pull-ups |
| VDDA_1V8 | PMIC LDO3, slow ramp | 3V3_MAIN | 1.8 V | 0.3 A | 0.2 A | Analog 1.8 V rails (through beads), VDDS_OSC0 |
| VDD_2V5 | PMIC LDO4, slow ramp | 3V3_MAIN | 2.5 V | 0.3 A | ~0.2 A (one PHY plus 60 mA VPP) | DDR_VPP, DP83867 VDDA2P5 |
| VCC_3V3_SYS | TPS22965DSGR, ON = GPO2 | 3V3_MAIN | 3.3 V | 6 A | ~2.9 A | 3.3 V IO banks and peripherals (M.2 0.8 A) |
| VDD_SD | TPS22996DRLR ch1 | 3V3_SYS | 3.3 V | 4 A | 0.2 A | microSD VDD |
| VDD_1V0_PHY | TLV75710PDBVR | VDD_1V8 | 1.0 V | 1 A | 0.22 A | DP83867 core |
| VPP_1V8 | TLV75518PDBVR (DNP) | 3V3_SYS | 1.8 V | 0.5 A | 0.4 A, only while programming eFuses | SoC VPP |
| USB-A VBUS x2 | TPS2051BDBVR x2 | VCC_5V0 | 5 V | 0.5 A each | 1 A total | USB-A ports |

**Start-up sequence:**
1. On attach, U1 powers itself from VBUS through its dead-battery LDO.
2. U1 closes the path at 5 V (AlwaysEnableSink). Both converters start, and VCC_3V3_MAIN brings up the PMIC.
3. U1 negotiates 9 V, normally before Linux is running.
4. VMAIN then steps from 5 V to 9 V at the slew the source controls. Both converters ride through the step.

**PMIC rule checks:**
- PVIN ≤ VSYS: all PVINs share the VSYS rail.
- LDO3 and LDO4 must use slow ramp (< 18 mV/µs). Confirm this in the NVM document SLVUCL1.
- The 3.3 V IO load switch on GPO2 needs active discharge. The TPS22965 non-N variant has it.

---

## 3. Part choices and deviations from SK-AM62B-P1

| SK part | This design | Why |
|---|---|---|
| TPS65988 dual-port + W25Q80 flash, 2x USB-C, 2x TVS2200, port-2 source FETs | TPS25730D single sink port, 1x TVS2200 | One port does sink power plus USB device. No firmware. About $9 less. **The Type-C port can no longer source 5 V or act as host.** |
| VMAIN 15 V / 3 A | VMAIN 5-9 V | Margin for the 16 V buck-boost; 9 V is offered by every PD charger |
| TPS6521904RHBR (5x5 mm) | **TPS6521904RSMR (4x4 mm, 0.4 mm pitch)** | Stock (§0). Same NVM, so the rail map and sequence are unchanged. The footprint and layout differ. |
| LM61460AANQRJRRQ1 ($3.61, 28 pcs) | LM61460AANRJRR ($1.59, 956 pcs) | Catalog grade. **The input range is 3.0-36 V, not 4.5-24 V as our SK notes say**, so the 5 V fallback works. |
| XAL6060-472 (not in the JLC library) | Sunlord MWSA0603S-4R7MT (9 A Isat, 33 mΩ) | 47k pcs at JLC. Bourns SRP7028A-4R7M (10 A Isat, 183 pcs) is the upgrade. |
| TPS630702 ($2.72, 146 pcs) | TPS63070RNMR ($1.13, 33k pcs) | Same converter; the 0702 version only adds output discharge |
| XFL4020-152 (0 at JLC) | Sunlord MWSA0402S-1R5MT (5.5 A Isat) | In stock at JLC |
| DFE201612E-R47M x3 (Isat 5.5 A) | DFE252012F-R47M x3 (Isat 7.4 A, 23 mΩ) | Meets the TPS65219 Buck1 rule (Isat ≥ 7.4 A). DFE322520F (8.5 A, 203 pcs) is an optional Buck1 upgrade. |
| TPS22965DSGT | TPS22965DSGR | Same part on a larger reel: $0.25 instead of $0.66 |
| TPS22996HQDYCRQ1 (32 pcs) | TPS22996DRLR (18.5k pcs) | Catalog version, QOD, VIN 0.6 V to VBIAS |
| TPS2051BD x1 | TPS2051BDBVR x2 | One switch per port, 1 A total budget |
| TPS22946 (header 5 V, 150 mA, off by default) | 1.1 A PTC, always on | Raspberry-Pi style. **Confirm** (decision 2). |
| TLV75510PDQNR (X2SON) | TLV75710PDBVR (SOT-23-5, 2,113 pcs) | TLV75510PDBVR has 4 pcs at JLC and 0 at LCSC. TLV757P has the same DBV pinout (IN/GND/EN/NC/OUT; checked in both datasheets). |
| TLV75801 VDD_CANUART LDO | Omitted; VDD_CANUART tied to VDD_CORE | One supply source is required unless Partial-IO is used |
| INA231 monitors + 10 mΩ shunts | 0 Ω test links (1206 on the bucks, 2 in parallel on Buck1; 0603 on the LDOs) | Saves cost; current can still be measured on pre-production boards |
| TPD1E01B04 on CC | PESD24VL1BA (24 V) | A diode with 6.4 V breakdown would fail on a CC-to-VBUS short at 9 V |
| VMON_VSYS from VCC_5V0 (10 k / 1.1 k + 22 pF) | Same | Known-good |

**Out of scope for this section:**
- USB D+/D- ESD.
- The USB0 VBUS-detect divider. It must now tolerate 9 V, and more above the OVP window.
- HDMI 5 V limiting.
- The FT4232H LDO.
- The PMIC button and reset logic.

---

## 4. Pricing basis and subtotal

**Price sources:**
- JLC/LCSC lines: JLCPCB parts-library API at the 10-boards x qty break, 2026-10-17. The LCSC API agrees within 1 %.
- PMIC: Digi-Key cut tape at qty 10. A JLC global-sourcing quote may add handling.
- Small passives: priced at the named basic part, for example 0402WGF1002TCE. Other values in the same basic series cost the same.
- No price is estimated.

| Category | Placements | $/board |
|---|---|---|
| ICs (U1-U5, U7-U10) | 9 | 9.91 |
| Power inductors | 5 | 0.72 |
| Connector, TVS, CC ESD, PTC | 5 | 1.05 |
| Bulk caps (22-47 µF MLCC, 10 µF / 50 V, 150 µF polymer) | 19 | 2.57 |
| Ferrite beads | 10 | 0.40 |
| Small R/C and 0 Ω links (all JLC basic) | 96 | 0.59 |
| **Total (U6 DNP and ALT rows excluded)** | **144** | **$15.23** |

**Fees not in the total:**
- **JLCPCB Standard PCBA** (needed for the BGA SiP and 6 layers): the Sept 2025 table charges about $1.5 feeder loading per unique part. That is 33 parts in this section, roughly $50 per order, or about $5 per board.
- **PMIC through JLC global sourcing:** a separate handling fee. Verify both fees on the quote.

The section is about 5 % of the $300 board target.

---

## 5. Risks and open items

1. **PMIC footprint and sourcing.**
   - RSM is a 0.4 mm-pitch QFN, which JLC can assemble. Layout comes from TI's TPS65219EVM-RSM, not the SK.
   - The part comes from Digi-Key or Mouser through JLC global sourcing or consignment, which adds lead time and handling.
   - Order early. Factory lead time is 26 weeks if distributor stock runs out.
2. **TPS25730 strap behavior.** TI marks it "firmware controlled and subject to change". Verify the straps on the TI EVM or the first boards.
3. **I2C address 0x20/0x21 for the TPS25730.**
   - It collides with TCA64xx IO-expander default addresses, so choose its bus or address deliberately.
   - No mainline Linux driver is confirmed. Plan on userspace i2c reads, or a small driver.
4. **Never strap the PD maximum above 9 V while U3 is a TPS63070** (16 V operating, 20 V abs max). Also keep total VMAIN capacitance ≤ 100 µF nominal (the TPS25730 PPHV limit), so do not add an electrolytic there.
5. **Weak 5 V sources.** A non-PD or 5 V-only source limits the board to its advertised current; a 0.5 A PC port will brown out under load. Software should gate the USB-A ports based on the contract.
6. **LM61460 inductor margin.** The high-side current limit (10.3 A typical) is above the inductor's 9 A Isat. Hiccup mode protects the part. Use SRP7028A-4R7M if you want more margin.
7. **Thermal.** The LM61460 dissipates about 1.5-2 W at 9 V in and 3.3 V / 5 A out. Follow the HotRod via guidance.
8. **PMIC power-on mode.** Confirm in SLVUCL1 whether NVM 04 enables first-supply detection (PU_ON_FSD). If it does not, a push-button configuration needs a button press at plug-in. This is already an open item in docs/research.
9. **Buck output capacitance and BW mode.** Confirm in SLVUCL1, counting the SiP-internal caps.

---

## 6. Decisions needed from you

1. **PD maximum voltage:** 9 V (recommended) or 15 V. 15 V needs a 5 V converter rated above 20 V in place of the TPS63070.
2. **Header 5 V:** always on behind a 1.1 A PTC, or switched and current-limited like the SK.
3. **USB-C port role:** confirm it is sink plus USB2 device only (gadget/DFU), with no host, OTG or 5 V source on that port.
4. **Confirm the omissions:** INA231 current monitors and the VDD_CANUART partial-IO LDO.
5. **PMIC RSM footprint, sourced from Digi-Key or Mouser:** confirm. The alternative is the RHB footprint, which needs JLC's 19 pcs reserved now and caps the build at about 19 boards until RHB restocks (Mouser expects 2,894 on 02-Nov-2026).

---

## Sources

**Datasheets (TI):**
- TPS25730 (SLVSGP9): https://www.ti.com/lit/ds/symlink/tps25730.pdf
- TPS25730A (SLVSJG8A): https://www.ti.com/lit/ds/symlink/tps25730a.pdf
- LM61460 (SNVSBD5D): https://www.ti.com/lit/ds/symlink/lm61460.pdf
- TPS63070 (SLVSC58B): https://www.ti.com/lit/ds/symlink/tps63070.pdf
- TPS22996 (SLVSH99A): https://www.ti.com/lit/ds/symlink/tps22996.pdf
- TLV757P and TLV755P: used for the DBV pinout check

**Other datasheets:**
- HUSB238 Rev 2.0: https://cdn.sparkfun.com/assets/9/1/7/a/4/USB_PD_Sink_HUSB238.pdf
- STUSB4500 default NVM (mirror): https://www.alldatasheet.net/html-pdf/1179076/STMICROELECTRONICS/STUSB4500/25029/11/STUSB4500.html
- CH224 (Chinese): https://static.chipdip.ru/lib/132/DOC042132154.pdf

**Stock and price, all checked 2026-10-17:**
- JLCPCB parts API, and the LCSC product API.
- Digi-Key search pages for TPS6521904RHBR, TPS6521904RSMR, TPS25730ADREFR and TLV75510PDBVR.
- Mouser search and product page for 595-TPS6521904RSMR.
- Arrow product page for TPS6521904RSMR (quote only, no stock shown).
- TI store part-detail pages for TPS6521904RHBR and TPS6521904RSMR (both out of stock).

**Fees:** JLCPCB assembly price page, https://jlcpcb.com/help/article/pcb-assembly-price

**Project documents:**
- DESIGN_PROPOSAL.md §5.1
- docs/research/sk-am62b-reference-design.md §2
- docs/research/am625-tps65219-constraints.md §B
- docs/research/osd62x-pm-sip.md §1.4 and §1.6
- SK BOM: bom_asm.tsv
