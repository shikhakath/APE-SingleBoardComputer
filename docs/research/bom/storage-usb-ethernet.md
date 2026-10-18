# BOM notes: Storage, USB and Ethernet (APE-SBC, OSD6254)

- Date: 2026-10-17. Prices are for a 10-board build, at the price break for 10 × the per-board count.
- Source order: JLCPCB/LCSC parts library first, then Digi-Key. All JLC/LCSC figures come from the JLC parts-search API and the LCSC product API on this date.
- CSV: `bom_storage_usb_eth.csv` (22 lines).
- The coordinator added an in-stock rule mid-task. Every line now carries **STOCK OK** or **STOCK RISK**.

## 0. Summary

| Block | Choice | $/board |
|---|---|---|
| eMMC | **GB042 "Odroid-standard" removable eMMC module.** Board side: LS Mtron **GB042-34P-H10** (34-pin plug only; the 30-pin mounting plug is footprint-only, DNP). Module: **PINE64 32 GB** at $24.95, in stock. | 0.60 connector + 24.95 module |
| microSD | Korean Hroparts **TF-01A** push-push socket (C91145) + 2× **TPD4E05U06DQAR** ESD | 0.36 |
| USB hub | WCH **CH335F** (4-port MTT, -40 to 85 °C, single 3.3 V) + 12 MHz crystal, no load caps | 1.01 |
| USB-A | Bossie **BX-TYPE-A-MWC44** dual-stacked + 2× Sunlord **SDCW2012-2-900TF** CMC + 2× ST **USBLC6-2SC6** | 0.77 |
| USB0 extras (may overlap the USB-C/power BOM) | CMC + ESD122 + 6.8 V zener (+ the divider, which is in the passives line) | 0.43 |
| Ethernet | TI **DP83867ISRGZR** (in stock; drop-in for the SK's IRRGZ) + YXC 25 MHz crystal + HanRun **HR911130A** gigabit MagJack | 7.27 incl. passives |

**Subtotals per board, from the CSV:**
- Storage on-board: **$1.11**
- Storage plug-in module: **$24.95**
- USB: **$2.36**
- Ethernet: **$7.27**
- **Section total: $35.69** ($10.74 without the eMMC module)

×10 boards = **$356.9**.

**Not in the subtotal:** JLC extended-part loading fees. There are about 11 extended part types × $3 = about $33 per order, which is about $3.30/board at 10 boards. The RJ45 and USB-A are through-hole, so JLC's THT soldering fee also applies.

## 1. Removable eMMC: ecosystem research

### 1.1 Who shares what

| Ecosystem | Board-side connector | Module side | Compatible with the others? | Evidence |
|---|---|---|---|---|
| **Hardkernel ODROID** (orange eMMC 5.1 modules; C0/C1/C2/C4/C5/N2/N2L/M1/XU4/H2/H3) | LS Mtron GB042-34P-H10, 34-pin plug | GB042-34S-H10 | Reference pinout. Radxa's wiki thanks Odroid for the pinout. | Odroid reference chart (Cloudflare-blocked; quoted via search). Radxa wiki ROCK 3 eMMC page. |
| **Radxa** (ROCK 3A/3B/3C/4A/4B/4C+/4SE/5A/5B; Radxa-made modules also sold by Allnet, OKdo/Arduino "Rock" and Seeed) | GB042-34P-H10 (signals) + GB042-30P-H10 (mechanical only, no signals) | GB042-34S-H10 + GB042-30S-H10 | Yes. Radxa staff: the 34-pin is the same connector and signals as Odroid, and the 30-pin is only for mounting. Dual-connector modules work on 34-pin-only boards. | Radxa product brief RAD-DOC-0126 rev 1.1. Radxa forum threads /t/149 and /t/8228. |
| **PINE64** (ROCK64, ROCKPro64, Quartz64, SOQuartz, Star64, Pinebook Pro…) | 34-pin GB042-class | 34-pin socket (ROCKPro64 modules are 34-pin only) | Yes. Radxa tested PINE64 modules on its boards. Users run orange Odroid modules on ROCK64. ROCK64 grounds pins 13 and 15 (no strobe or detect). | PINE64 forum tid=6279. Radxa forum /t/149. |
| **FriendlyElec** "Matrix eMMC module" | Proprietary 20-pin, 2×10 | — | **No.** Different pinout and connector. | FriendlyElec wiki. |
| Orange Pi 5 Plus eMMC socket | Not verified | — | Unknown. Excluded. | — |

**Recommendation:** use the **GB042 34-pin "Odroid/Radxa/PINE64" standard.** It is the only multi-vendor ecosystem, and all three vendors still sell modules.
- Put the 34-pin plug on the board.
- Keep a DNP footprint for the 30-pin mounting plug, so Radxa dual-connector modules can be retained better later.

### 1.2 34-pin pinout

This table is from the Radxa product brief rev 1.1, cross-checked against the host schematics of the Radxa ROCK 3A v1.31 and ROCK 5A v1.1. It is shown from the host-board side.

| Pin | Signal | Pin | Signal |
|---|---|---|---|
| 1 | GND | 18 | GND |
| 2 | DAT5 | 19 | GND |
| 3 | GND | 20 | **VCCQ 1.8 V (from host)** |
| 4 | DAT4 | 21 | **VCCQ 1.8 V (from host)** |
| 5 | GND | 22 | **VCC 3.3 V (from host)** |
| 6 | DAT0 | 23 | **VCC 3.3 V (from host)** |
| 7 | GND | 24 | GND |
| 8 | CLK | 25 | CMD |
| 9 | GND | 26 | GND |
| 10 | DAT3 | 27 | DAT2 |
| 11 | GND | 28 | GND |
| 12 | **RST_n** (see note) | 29 | DAT1 |
| 13 | GND on module (Odroid uses it as module-detect "CDN") | 30 | GND |
| 14 | GND | 31 | DAT7 |
| 15 | Data STROBE (HS400 only; NC on AM62x) | 32 | GND |
| 16 | GND | 33 | DAT6 |
| 17 | GND | 34 | GND |

**Pin 12 (RST_n):**
- Radxa's module brief labels it "VCC 1V8".
- Radxa's host schematics label it **RSTN**, with a **10 kΩ pull-up to VCCIO_FLASH (1.8 V)** and the link to the SoC's eMMC_RSTn **not fitted**.
- ODROID-N2 (mainline `meson-g12b-odroid.dtsi`) drives eMMC reset through `mmc-pwrseq-emmc reset-gpios`.

**Design rule for pin 12:**
- Fit a 10 kΩ pull-up to VCCQ.
- Add a **DNP** 0 Ω (or 1 kΩ) link to the SK-style AND(GPIO, RESETSTATz) reset.
- Populate the link only after checking that the chosen module routes pin 12 to eMMC RST_n, not to a supply plane.

**Supplies:**
- **VCC (3.3 V) and VCCQ (1.8 V) both come from the host.** The documented modules have no on-module regulator.
- Host device trees and schematics show this: ROCK 3A `vqmmc-supply = <&vcc_1v8>`, ROCK64 `vqmmc-supply = <&vcc18_emmc>`, and ROCK 3A/5A tie pins 20/21 to VCCIO_FLASH.
- For HS200, VCCQ must be the 1.8 V VDDSHV4 rail.

**HS200 at 1.8 V is supported.** Mainline DTs run these modules at HS200 or faster:
- ODROID-N2: `mmc-hs200-1_8v`, 200 MHz
- ROCK 3A: 200 MHz
- ROCK64 and ROCKPro64: `mmc-hs200-1_8v`
- ROCK Pi 4 and ROCK 5A: HS400ES

The AM62x supports at most HS200 on MMC0, so the strobe pin stays NC.

**Mechanical:**
- GB042 "H10" means about a 1.0 mm mated stack height.
- Module is about 18 × 13 mm (Radxa states 13 × 18 × 1.5 mm).
- Height above the host PCB is about **2.5–3 mm** (EST: 1.0 mm stack + module PCB + eMMC BGA).
- Do not hot-plug. A PINE64 forum user reports bricking an XU4 that way.

### 1.3 Board-side connector sourcing (STOCK RISK)

- **GB042-34P-H10(-E3000) and GB042-30P-H10 are not stocked by LCSC, Digi-Key or Mouser.**
  - Digi-Key: no match.
  - JLC library: only C99000xxxx "JLCPCB Assembly" placeholders with 0 stock.
- Only HK/CN brokers list it:
  - IC Components: 2,740 pcs of -E3000, "2–3 days"
  - Jotrin: 7,310 pcs, plus 50,000 of the 30P
  - Xecor: 2,109 pcs
  - Price is about **$0.50–0.57** each (EST $0.60).
- Plan:
  - Buy about 20 pcs from a broker now.
  - Test-mate one with a PINE64 or Radxa module.
  - Ship to JLC as a **customer-supplied (consigned) part**.
- I found **no mating-compatible connector at an authorized distributor**, so there is no in-stock "functional equivalent" that keeps module compatibility.
- **Fallback if the broker part can't be obtained:** a soldered BGA-153 eMMC on the same MMC0 net. In stock at JLC, but expensive in 2026:
  - Samsung KLMBG2JETD-B041 32 GB: C2803245, $44.96 @10, 565 pcs
  - MK MKEMF032GT1E-C 32 GB: $51.52, 416 pcs

  The plug-in module is **cheaper** than a soldered chip right now.

### 1.4 Module price and stock (2026-10-17)

| Vendor | 16 GB | 32 GB | 64 GB | Stock |
|---|---|---|---|---|
| **PINE64 store** (pine64.com) | **$15.95** | **$24.95** | $34.95 | 16/32 GB: In stock (max 10 per order). 64 GB: **out of stock** |
| Hardkernel direct (C5/N2L etc. orange modules, OS preinstalled) | $40 | $45 | $55 | "Add to cart". No stock count shown |
| Ameridroid (Hardkernel "No OS, Orange Dot") | $49.95 | $53.95 | $64.95 | Available |
| Ameridroid "ROCK/Radxa eMMC" | — | — | $54.95 | Available (inventory-tracked) |
| Allnet China (Radxa eMMC 5.1) | $39.95 | out of stock | $55.95 | 16/64 GB available |
| Arace (Radxa official) | $9.99 | $19.99 | $35.00 | **All out of stock** |

- **The CSV line uses PINE64 32 GB at $24.95.** It is the cheapest in-stock option. PINE64 16 GB at $15.95 saves $9/board.
- For **64 GB**, the cheapest in-stock source is Ameridroid Radxa at $54.95 or Hardkernel at $55.
- Shipping, tariffs and taxes are excluded.
- Buy one USB eMMC writer for the lab:
  - PINE64 USB adapter: $4.99
  - Hardkernel Writer 2: $9.90
  - On-board flashing over USB0 DFU/UMS also works.

### 1.5 HS200 signal-integrity caveats through the connector

- **AM62x MMC0 limits** (DS Tables 6-81/6-82): trace delay 126–756 ps, **≤ 8 ps mismatch**, C_L ≤ 10 pF.
- The module adds its own routing, about 10–15 mm, which is unknown and differs by vendor. You **cannot length-match across the connector.**
- Mitigations:
  - Keep host-side MMC0 routes short (aim for 40 mm or less, roughly 250 ps) and matched among themselves.
  - Put the connector next to the SiP.
  - Put the 0–22 Ω CLK series resistor at the SoC.
  - Avoid stubs: no pull-up stubs on CLK, and pull-ups at the connector end.
- The GB042 pinout puts a GND between every signal, which is good for return paths.
- HS200 tuning absorbs CLK-to-data skew. Other SoCs run 200 MHz HS200/HS400 through this connector in mainline.
- If a module is marginal, drop to HS/DDR52 in the device tree.
- **Warm reset:** RST_n is not guaranteed (pin 12 above). Recommended: power the module's VCC and VCCQ through a load switch reset by RESETSTATz/PMIC. That switch is priced by the power agent. Also leave EXT_CSD RST_n_ENABLE as is.

## 2. microSD

- **Socket:** Korean Hroparts **TF-01A** (C91145).
  - $0.193, 184,825 in stock.
  - Push-push, 9 pads: 8 card contacts + card-detect contact. 1.85 mm high, locating pins.
  - The SK's GCT MEM2051-00-195-00-A (C5137462) has **0 stock** at JLC.
  - Gold-contact alternate: Hirose **DM3AT-SF-PEJM5** (C114218, $1.16, 16,552 in stock).
  - The AM62x ROM needs MMC1_SDCD = 0 to SD-boot, so wire the CD switch to GND-on-insert, with a 47 k pull-up and 100 Ω series (SK).
- **ESD:** 2× TI **TPD4E05U06DQAR** (C138714, 0.5 pF, $0.083, 215 k in stock) cover CLK, CMD, DAT0–3, CD + 1 spare.
  - Cheaper and lower capacitance than the SK's TPD6E001RSER ($0.33, 852 pcs) + TPD2E001DRLR ($0.16).
- **Not priced here:** UHS-I support (LDO1 VSEL 3.3/1.8 V and the card-power load switch). That belongs to the power section.

## 3. USB 2.0 hub: comparison

JLC/LCSC price @10 and stock as of today.

| Hub | Ports / TT | Clock | Supplies | Temp | $ @10 | Stock | Notes |
|---|---|---|---|---|---|---|---|
| TI TUSB4041IPAPR | 4 / MTT | 24 MHz xtal | **3.3 V + 1.1 V** | -40 to 85 | 6.93 | **10 (RISK)** | 64-HTQFP, needs an extra 1.1 V rail. Rejected. |
| Microchip USB2422T-I/MJ | 2 / single TT | 24 MHz xtal + caps | 3.3 V single | -40 to 85 | 2.04 | 740 | Small QFN-24, proven. STT shares FS/LS bandwidth. |
| Microchip USB2512B-I/M2 | 2 / MTT | 24 MHz | 3.3 V | -40 to 85 | 3.58 | **38 (RISK)** | — |
| Microchip USB2514BI-AEZG-TR | 4 / MTT | 24 MHz + 12k RBIAS | 3.3 V | -40 to 85 | 2.04 | 9,424 | **Conservative fallback.** Long Linux track record. |
| Genesys GL850G | 4 / STT | 12 MHz | 5 V/3.3 V | 0 to 70 | 0.34 | **0 (RISK)** | — |
| Terminus FE1.1s (QFN24) | 4 / STT | 12 MHz | 5 V/3.3 V | **0 to 70** | 0.67 | 18,521 | Commercial temperature only. |
| WCH CH334F | 4 / MTT | 12 MHz (internal caps; crystal-less option) | 3.3 V single (or 5 V via internal LDO) | -40 to 85 | 0.53 | 8,489 | GANG power/OC only |
| **WCH CH335F** | 4 / **MTT** | 12 MHz, **no external caps** | **3.3 V single** (tie V5 and VDD33 together per WCH) | **-40 to 85** (WCH: tested to 105 on 3.3 V) | **0.92** | **6,199** | **Recommended.** Per-port power/OC control. WCH's preferred part for new designs. 6 kV ESD on USB pins. |

- **Linux:** every candidate is a class-compliant hub on the generic `hub` driver, with no vendor driver. The AM62x DWC3 xHCI handles MTT hubs natively.
- **Why CH335F:**
  - Cheapest MTT, industrial-temperature part in stock.
  - Single 3.3 V rail.
  - Fewest support parts: one 12 MHz crystal with no load caps, about 6 decoupling caps, and PSELF/RESET resistors. No RBIAS, no EEPROM.
  - Per-port PWREN/OVCUR suits one power switch per USB-A port.
- **Field risk:** WCH has less field history than Microchip. If the user prefers that pedigree, switch to **USB2514BI-AEZG-TR**: +$1.12/board, plus a 24 MHz crystal, 2 caps and 12 k RBIAS. The footprint is different.
- **Do not use crystal-less mode.** WCH says it may deviate from the USB spec.
- **Support parts:**
  - 12 MHz YXC X322512MSB4SI (C9002, basic)
  - V5 and VDD33 tied to 3.3 V with 1 µF + 2×0.1 µF + 10 µF
  - RESET# to a SoC GPIO or RESETSTATz (internal pull-up)
  - PSELF strap for self-powered
  - Unused downstream ports 3/4: leave DP/DM open

## 4. USB-A host ports

- **Receptacle:** Bossie **BX-TYPE-A-MWC44** dual-stacked USB 2.0 Type-A, THT (C18077688, $0.29, 468 pcs).
  - It saves edge length on the 100 × 70 mm board.
  - Alternates: USAKRO C698206 ($0.23, 300 pcs). Wurth 61400826021 ($2.34, **99 pcs, RISK**).
  - Two singles: Amphenol 87520-0010BLF C599115 ($0.56, 18 k pcs).
- **CMC:** Sunlord **SDCW2012-2-900TF** (C54888, $0.059, 65 k pcs), fitted, with 0 Ω bypass footprints DNP.
  - The SK's Murata DLW21SZ900HQ2B is not in the JLC library.
  - The AM62x DS allows only a CMC with a 0 Ω bypass on DP/DM.
- **ESD:** ST **USBLC6-2SC6** per port (C7519, $0.177, 34 k pcs). It clamps D+, D− and VBUS.
  - Less than half the price of TPD4S012DRYR ($0.39).
  - Budget alternate: TECH PUBLIC USBLC6-2SC6 C2827654 at $0.045.
- **Not priced here:** port power switches (power agent). The 120 µF/port VBUS bulk is assumed to sit with them. 2× 22 µF ceramics are in the USB passives line.
- **USB0 lines (CMC, ESD122DMXR, 6.8 V zener, VBUS divider; $0.43 total):** included so nothing is missed. **Remove them if the USB-C/power BOM already carries them.**
  - USBLC6 is not used on USB0, because a PD source can raise VBUS above its 5.25 V rating.

## 5. Ethernet: PHY, crystal, RJ45

### PHY

| Option | LCSC/JLC $ @10 | Stock | Digi-Key @10 | Verdict |
|---|---|---|---|---|
| DP83867IRRGZR (SK part) | 3.37 | **0** | $5.47, **0 stock, ETA 2027-02-02** | RISK |
| DP83867IRRGZT | 4.87 | **14** | $9.58, 0 stock | RISK (only 14) |
| DP83867CSRGZR (0 to 70 °C) | 5.48 | 185 | $5.31, 1,163 pcs | **Not cheaper.** Commercial temperature. |
| **DP83867ISRGZR** | **4.53** | **777** | — | **Chosen** |
| RTL8211F-CG / RTL8211FI-CG | 1.11 / 1.89 | 78 k / 16.8 k | — | Cost-down option, not chosen |

**Why DP83867IS:**
- **Same RGZ pinout, same PHY ID and Linux `dp83867` driver, -40 to 85 °C.** It adds SGMII on RX_D0..3/TX_D0..1, which stays off.
- Keep the LED_1 strap at its default (SGMII Enable = 0).
- RX_CTRL must be strapped to mode 3/4, as for IR.
- If RX_D0/RX_D2 are strapped, fit matching **dummy straps on RX_D1/RX_D3** (IS datasheet notes).
- RGMII on the AM62x: the MAC always adds the TX delay, so set the PHY to RX delay only (`rgmii-rxid`). Straps matter because the ROM does Ethernet boot without configuring the PHY.

**About the RTL8211F:**
- It would save about $3.40/board.
- But the TI SDK and Octavo device trees, the SK strap set and Ethernet-boot practice are all built around the DP83867.
- Not recommended for spin 1.

### Supplies (power agent)

- **Two-supply mode** (DS Fig 9-7): VDDA2P5 = 2.5 V, VDD1P0 = 1.0 V, VDDIO = 3.3 V.
- The VDDA1P8 pins are left unconnected.
- There is no sequencing requirement in two-supply mode.

### Crystal

- YXC **X322525MOB4SI** 25 MHz ±10 ppm, CL 12 pF (C9006, basic, 244 k pcs) with 2× 15–18 pF caps.
- The DP83867 needs 25 MHz ±50 ppm.
- Option: buffer the SoC's 25 MHz oscillator to the PHY XI instead, as the SK does with LMK1C1103. The PHY XI amplitude is limited to 1.8 V, so a 3.3 V clock needs a cap divider. That would save the crystal, but costs a buffer.

### RJ45

- HanRun **HR911130A** (C54408, $2.35, JLC 20,781 / LCSC 1,707 pcs).
- **Confirmed gigabit** from the HanRun datasheet: "100/1000Base-T", "Meets or Exceeds IEEE802.3ab for 1000Base-T".
- Four 1CT:1CT channels, 1500 Vrms, Bob-Smith 4×75 Ω + 1 nF/2 kV, green and yellow LEDs, shielded, THT, 0 to 70 °C.
- Single chip-side center tap (P1): 0.1 µF to GND, suitable for the voltage-mode DP83867.
- The SK's LINK-PP LPJG16314A4NL has only 10 pcs at JLC (RISK, $4.38).

### Ethernet passive count (CSV)

- **Resistors:** 12× 22 Ω RGMII series, about 12 strap resistors (including dummies), RBIAS 11 k 1%.
- **Other passives (about 34):**
  - Decoupling: 9× 1 µF, 10× 0.1 µF, 3× 10 µF, 3× 10 nF
  - 2 crystal caps
  - 2× 470 Ω LED
  - 2.2 k MDIO pull-up
  - RESET/INT pull-ups
  - 62 Ω + 47 pF INT RC
  - Center-tap cap
- This matches the SK PHY sheet p.25, about 36 R / 27 C including the series resistors.

## 6. Stock status (in-stock rule)

- **STOCK OK** (supplier stock ≥ 50 boards' worth, except where noted): TF-01A, TPD4E05U06, CH335F, 12/25 MHz crystals, Bossie USB-A (468 = 46 boards' worth), SDCW2012, USBLC6-2SC6, ESD122, LBZX84C6V8, DP83867ISRGZR (777), HR911130A, and all basic passives.
- **PINE64 eMMC modules:** "In stock", but the store does not publish a quantity and allows 10 per order. Several alternate vendors are also in stock. Marked STOCK OK.
- **STOCK RISK:** **GB042-34P-H10** (broker-only), and GB042-30P-H10 (DNP).
- Parts swapped out because of stock:

| SK / preferred part | Problem | Replacement |
|---|---|---|
| DP83867IRRGZ | 0–14 pcs | DP83867ISRGZR |
| LPJG16314A4NL | 10 pcs | HR911130A |
| MEM2051 | 0 pcs | TF-01A |
| TPD6E001 + TPD2E001 | — | 2× TPD4E05U06 |
| TPD4S012 | — | USBLC6-2SC6 |
| DLW21SZ900HQ2B | not in the JLC library | SDCW2012-2-900TF |
| TUSB4041I | 10 pcs | CH335F |
| GL850G | 0 pcs | CH335F |
| USB2512B | 38 pcs | CH335F |
| Wurth stacked USB-A | 99 pcs | Bossie |

## 7. Risks

1. **GB042 connector sourcing** (broker-only, authenticity and lead time). Order now, test-mate it, and keep the BGA-153 fallback in mind.
2. **Module variability:** pin 12 RST_n usage, internal trace length, and eMMC vendor (Samsung, Foresee, SanDisk, Kingston). Validate HS200 tuning with 2 brands (PINE64 + Hardkernel or Radxa). DT fallback to HS/DDR52.
3. **eMMC warm-reset robustness without RST_n.** Add a module power-cycle load switch tied to reset (power agent).
4. **Module prices are inflated by the 2026 NAND market.** Hardkernel is at $40–55. PINE64's prices may be old list prices and could rise.
5. **CH335F field history** is shorter than Microchip's. Fallback: USB2514BI. Hub-reset glitches on hot-plug: WCH recommends 3.3 V-direct supply plus large VBUS/3.3 V capacitance.
6. **DP83867IS vs IR strap nuances** (dummy straps, SGMII off). Low risk, but review the strap sheet against the IS datasheet SNLS504G.
7. **Commercial-temperature parts:** HR911130A and the Bossie USB-A are rated 0 to 70 °C / -20 to 70 °C. That is fine for a general SBC, not for industrial use.
8. **THT parts** (RJ45, USB-A) add JLC THT-assembly cost. There are also about 11 extended-part setup fees (about $33 per order).

## 8. Coordination with other agents

- **Power agent:**
  - DP83867 2.5 V and 1.0 V rails
  - SD UHS-I VSEL and card-power switch
  - eMMC module VCC/VCCQ (3.3 V / 1.8 V at about 100–200 mA). Ideally switched, for warm reset.
  - USB-A port power switches and VBUS bulk
  - CH335F 3.3 V (about 85 mA max)
- **USB-C/power agent:** de-duplicate the USB0 CMC, ESD122, zener and divider.
- **Clocks/boot agent:**
  - PHY uses its own crystal, unless you choose to share the SoC 25 MHz oscillator.
  - Boot-mode default SD vs eMMC. A module boots from MMC0 like a soldered eMMC.

## Sources

- Radxa eMMC module product brief RAD-DOC-0126 rev 1.1: https://dl.radxa.com/accessories/emmc-module/
- Radxa docs: https://docs.radxa.com/en/accessories/storage/emmc_module
- Radxa wiki ROCK 3 eMMC: https://wiki.radxa.com/Rock3/hardware/emmc
- ROCK 3A v1.31 schematic: https://dl.radxa.com/rock3/docs/hw/3a/radxa_rock_3a_v1310_schematic.pdf
- ROCK 5A v1.1 schematic: https://dl.radxa.com/rock5/5a/docs/hw/radxa_rock5a_V1.1_sch.pdf
- Radxa forum: https://forum.radxa.com/t/emmc-dual-vs-single-connector/149 and https://forum.radxa.com/t/emmc-compatibility-for-rock-3a-and-rock-pi-4/8228
- PINE64 forum: https://forum.pine64.org/showthread.php?tid=6279
- Mainline Linux DTs (torvalds/linux master): rk3568-rock-3a.dts, meson-g12b-odroid.dtsi, rk3328-rock64.dts, rk3399-rockpro64.dtsi, rk3588s-rock-5a.dts
- Stores, checked 2026-10-17:
  - https://pine64.com/product/32gb-emmc-module/ (also /16gb-, /64gb-)
  - https://www.hardkernel.com/product-category/memories/
  - ameridroid.com and shop.allnetchina.cn (Shopify product JSON)
  - arace.tech/products/emmc-module
- GB042 broker listing: https://www.ic-components.com/products/1b3719006/GB042-34P-H10-E3000.pdf
- FriendlyElec Matrix eMMC: https://wiki.friendlyelec.com/wiki/index.php/Matrix_-_eMMC_Module
- WCH CH334/CH335 datasheet V2.91 (LCSC C5187527 datasheet)
- TI DP83867IR/CR (SNLS484J) and DP83867E/IS/CS (SNLS504G) datasheets
- HanRun HR911130A datasheet (LCSC C54408)
- Hroparts TF-01A drawing (LCSC C91145)
- Digi-Key search results for DP83867IRRGZR, DP83867CSRGZR and GB042-34P-H10
- JLCPCB parts library and LCSC product API for all C-numbers in the CSV
