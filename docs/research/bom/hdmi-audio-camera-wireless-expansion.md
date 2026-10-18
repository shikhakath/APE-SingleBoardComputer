# BOM notes: HDMI, audio, camera, wireless and expansion (OSD6254 SBC)

Checked 2026-10-17. The line items are in `bom_av_wireless_io.csv`, which has 27 rows. Lines with qty 0 are alternatives or rejected parts and are not counted in the subtotals.

Sources, in order of preference:
- JLCPCB parts API, for price, stock and basic/extended class.
- LCSC product pages.
- TI.com store inventory API (`/storeservices/cart/opninventory`) and TI part pages.
- Digi-Key search.
- Findchips, for broker stock only.
- Mouser could not be reached: its pages timed out. A Mouser-domain search shows SiI9022ACNU as "Non-Stocked".

Prices are at the break that applies to a 10-board build (10 x qty per board). "EST" marks an estimate and gives its basis.

**Scope changes applied**
- The 40-pin LVDS/OLDI FPC and its support parts were dropped (user). No lines for them.
- The SiI9022A was dropped because it is not in stock (user).
- New rule (user): every line must be in stock at a real distributor for at least 10 boards, and preferably 50. Every CSV row is tagged STOCK OK or STOCK RISK.
  - All counted lines are STOCK OK.
  - STOCK RISK appears only on rejected parts (qty 0).

---

## 1. HDMI bridge: comparison and recommendation

| Candidate | Video input | In stock today (supplier, qty) | Price @10 | Linux driver | HDMI audio | Supplies / clocks | Verdict |
|---|---|---|---|---|---|---|---|
| SiI9022ACNU (SK part) | 24-bit DPI | **None.** Digi-Key 0 (104 due 2027-01-18, 20-wk lead); LCSC/JLC C369565 0; Mouser non-stocked; brokers about $93+ | DK $5.85 / LCSC $19.88 | mainline `sii902x`, plus SK DT in TI SDK | Yes (MCLK optional, internal PLL) | 1.2 V + 3.3 V | **Dropped (no stock)** |
| ITE IT66121FN | 24-bit DPI | **Brokers only.** Win Source 5,200 at $4.11–5.28, and others. JLC C2684803 0; not at LCSC, Digi-Key or Mouser | EST $4.1–5.3 | mainline `ite-it66121` (BeaglePlay AM625 DT, audio supported) | Yes | 3.3 + 1.8 + 1.2 V; no MCLK | Rejected (stock) |
| Lontium LT8618SXB | 24-bit RGB/BT1120 | **None.** JLC C7424659 0 ($2.27 list); LCSC "not available" | $2.27 (no stock) | **No mainline driver** (vendor code only) | Yes | 1.8 + 3.3 V | Rejected (stock and driver) |
| **TI TFP410PAPR** | 24-bit DPI (3.3 V, single-edge) | **JLC 110 / LCSC 109; TI.com 11,487.** Tray TFP410PAP: LCSC 394 | **JLC $4.60** (TI.com $7.10 @1–99) | mainline `ti-tfp410` (`ti,tfp410`; strap mode needs no I2C) | **No** (DVI: no audio, no CEC, no infoframes) | **3.3 V only**; no crystal, no 1.2 V rail; RTFADJ 510 Ω | **RECOMMENDED** |
| ITE IT6263FN (OLDI/LVDS→HDMI) | OLDI0 single or dual link | **Brokers only.** Win Source 1,800 at $4.30–6.45; Shengyu claims 15k. JLC C5184443 0 | EST $4.3–6.5 | mainline `ite-it6263` (2024, NXP); dual-link OK; **video only** | Driver has no audio | 9 supply pins (1.8 / 3.3 V) | Rejected (stock). Would have freed the DPI/BOOTMODE balls |
| ADI ADV7513BSWZ | 24-bit DPI | **JLC 93 / LCSC 90** | $26.55 | mainline `adv7511` (adv7513), audio + CEC | Yes | 1.8 + 3.3 V | In-stock **upgrade path** if HDMI audio is required (+$21.9/board) |
| ADI ADV7511KSTZ | 24-bit DPI | JLC 44 (less than 50 boards) | $13.23 | mainline `adv7511` | Yes | 1.8 + 3.3 V, LQFP-100 14×14 | Possible if 44 pcs is enough. Large package |
| Macrosilicon MS7210 | RGB/BT1120 | JLC 138 | $1.49 | **none** | Yes | 1.8 / 2.5 / 3.3 V | Rejected (no Linux driver) |

### Recommendation: TI TFP410PAPR, with TPD12S016PWR and an XFCN HDMI-A receptacle

**Why this part:**
- **It is the only cheap bridge with real distributor stock and a mainline driver.** Stock is 110 at JLC/LCSC, enough for 110 boards, with 11,487 more at TI.com as backup. The driver needs no vendor code.
- **It is the simplest option.**
  - 3.3 V only, so it needs no 1.2 V tap on the SiP DDR rail and no new regulator.
  - No crystal or MCLK.
  - It can be strap-configured, so it needs no I2C: ISEL=0, BSEL=1 (24-bit single-edge), EDGE to match the DSS PCLK edge, DKEN=0, VREF=VDD, PD# pulled up or driven by a GPIO.
- **It handles 1080p60:** the maximum pixel clock is 165 MHz and 1080p60 needs 148.5 MHz.
- **It is cheap:** about $5.88 per board for the whole HDMI section.

**What you give up:**
- **No HDMI audio.** Audio comes only from the analog codec. A side benefit is that McASP1 no longer needs the SK's codec/HDMI FET mux.
- No CEC.
- **The link is DVI:** RGB only, with no infoframes. Monitors and TVs accept DVI on an HDMI connector, though some TVs show a "PC/DVI" mode.

**Design notes:**
- **Heat.** IDD is 200 mA typical and 250 mA max at 3.3 V, so up to about 0.8 W. Solder the PowerPAD to the GND plane with a via array.
- **Temperature.** It is a 0–70 °C part.
- **Device tree.** The chain is tidss VP2 (DPI) → `ti,tfp410` bridge → `hdmi-connector` (type "a", `ddc-i2c-bus` = the SoC I2C behind TPD12S016, `hpd-gpios`).
- **Kernel config.** Check that `CONFIG_DRM_TI_TFP410` is enabled in the TI SDK kernel config.
- **BOOTMODE straps.** The DPI/BOOTMODE[15:8] ball sharing still applies, so the fixed 10 k straps from DESIGN_PROPOSAL §5.2 stay.

**Companion parts (all in stock):**
- **TPD12S016PWR** (JLC 3,447; TI.com 20,549) for DDC/HPD level shift, the 5 V/55 mA HDMI 5 V pin and 12-channel ESD. A discrete equivalent saves under $0.40 and adds 4–6 parts, so it is not worth it.
- **XFCN HDMI-A-19F-S-D** (JLC 3,436), $0.185. The SK's Amphenol 10029449-001RLF has only 3 in stock.

**If HDMI audio is a must:**
- Swap in **ADV7513BSWZ** (93 in stock, $26.55, mainline `adv7511` with audio).
- It adds a 1.8 V supply and +$21.9 per board.
- In that case, also decide how McASP1 is shared with the codec. The options are a separate McASP or wiring both receivers in parallel, since an HDMI TX is always an I2S slave.

---

## 2. Audio codec: comparison and recommendation

All prices are JLC at the 10+ break, with JLC stock.

| Codec | Price @10 | JLC stock | Linux (ASoC) | Notes |
|---|---|---|---|---|
| TLV320AIC3106IRGZT (SK) | $2.81 | 25 | `tlv320aic3x`; SK DT | VQFN-48 7×7; 25 pcs covers 25 boards, under the 50-board preference; $1.58 more than the AIC3104 |
| **TLV320AIC3104IRHBR** | **$1.23** | **769** (TI.com 14,577) | **`tlv320aic3x`** (`ti,tlv320aic3104`) | Same family and driver as SK. VQFN-32 5×5. HP + line out, 2 mic/line in + bias. PLL takes MCLK, BCLK or GPIO2 |
| TLV320AIC3100IRHBR | $2.21 | 3,337 | `tlv320aic31xx` | Mono ADC, stereo HP, mono class-D |
| TLV320AIC3110IRHBR | $4.65 | 10 | `tlv320aic31xx` | Stereo class-D. Stock is thin |
| TLV320AIC23B | $1.17–5.84 | 0 | `tlv320aic23` | Out of stock |
| WM8960CGEFL | $2.34–12.99 | 0 | `wm8960` | Out of stock |
| NAU8822LYG | $5.72 | 0 | `nau8822` | Out of stock |
| ES8388 | $0.93 | 45,964 | `es8328` (`everest,es8388`) | Needs MCLK and HP coupling caps |
| ES8316 | $0.73 | 5,078 | `es8316` (Pinebook Pro, RK3399) | Stereo DAC + mono ADC. Ground-centred charge-pump HP, so no HP caps |
| ES8311 | $0.43 | 111,268 | `es8311` | **Mono** only, so not suitable for stereo headphones |
| SGTL5000 | $4.44 | 0 | `sgtl5000` | Out of stock |
| MAX98090 | $6.53 | 37 | `max98090` | Expensive |

### Recommendation: TLV320AIC3104IRHBR ($1.23, 769 in stock), with one 12.288 MHz oscillator and one TRRS jack

**Why this part:**
- It is the cheapest TI codec that covers headphone out and mic in.
- It uses the **same mainline driver as the SK's AIC3106**. The SK `simple-audio-card` DT carries over with the compatible string and routing changed (the AIC3104 has no MIC3).
- It is TI-supported on AM62x.

**Supplies:** 3.3 V for AVDD, DRVDD and IOVDD; 1.8 V for DVDD (the board already has a 1.8 V rail).

**Headphone output:** AC-coupled with 2×47 µF caps. Capless HPCOM cannot be used because the TRRS sleeve/ring ground is shared with the mic.

**Cost-down alternative: ES8316 ($0.73, 5,078 in stock).**
- About $0.70 per board cheaper, counting the HP caps it does not need.
- It still needs MCLK.
- Documentation is thinner, and moving to it adds more DT work than the AIC3104.

**MCLK:**
- Keep **one 12.288 MHz CMOS XO**: SJK 3N12288G33YC, $0.54, 448 in stock.
  - It gives exact 48 kHz-family rates.
  - It matches the SK DT, where a fixed 12.288 MHz clock feeds the codec and the codec is clock master.
  - Put a 10 k pull-down at the MCLK input (SK D-note).
- The AM62x AUDIO_EXT_REFCLK output cannot make exactly 12.288 MHz. A Toradex AM62 thread measured 12.345679 MHz. TI's J722S EVM moved from audio_refclk1 to an external 12.288 MHz oscillator.
- An oscillator-less variant is possible: run the AIC3104 PLL from BCLK with McASP as master, using an internal AUXCLK as BeaglePlay does (`auxclk-fs-ratio`). Sample rates are then slightly off nominal. Not recommended for a $0.54 saving.
- With TFP410 there is no HDMI audio, so the SK's second 12.288 MHz oscillator (U7) and its FET mux (SN74CB3Q3257) are both gone.

**Jack:**
- **Korean Hroparts PJ-320DB-5A**: TRRS, SMD, $0.145, 412 in stock.
- The SK's CUI SJ-43514-SMT-TR has only 9 in stock at JLC (STOCK RISK).
- Confirm the CTIA pin map and detect contact in the datasheet before layout.

---

## 3. Connector and mechanical choices

**Camera FPC**
- **TE 1-1734248-5**, the exact SK part: JLC C2922285, $0.945, 3,324 in stock.
- Its contact side and orientation already match RPi 15-pin camera cables.
- A cheaper HDGC look-alike (C2914181, $0.148) would need its contact side checked.

**Camera I2C switch**
- TCA9543APWR is optional: $0.73, 357 in stock, priced at qty 0.
- Put the camera on its own I2C instead (MCU_I2C0, WKUP_I2C0 or I2C3).

**M.2 Key-E socket**
- **LOTES APCI0085-P002A**: H3.2, $0.364, 6,396 in stock.
  - It has the same 3.2 mm stack height as the SK's TE 2199119-4, which has 0 stock at JLC.
  - LCSC's spec table says "3 mm" but its key attributes say "H3.2". Confirm on the drawing.
- **Standoff:** Würth 9774015243R, the SK's 1.5 mm M2 SMT standoff ($0.61, 1,763 in stock).
- **Screw:** Shuntian PM2X4 M2×4 pan-head ($0.0018, 11,579 in stock), fitted by hand.

**Wireless level shifters**
- **SN74AVC4T245PWR is needed** ($0.24, 18,217 in stock). The AM62x UART1 pin options are on VDDSHV0 (3.3 V) and the CC3351 IO is 1.8 V. It is the TSSOP version of the SK's DGV part ($1.34).
- **TXS0104ERGYR for BT_EN is kept** as on the SK ($0.40). Drop it if BT_EN is moved to a 1.8 V-domain GPIO (VDDSHV1 or VDDSHV6).
- The 32 kHz slow clock comes from the SoC, so it needs no part.

**Wi-Fi module**
- **M2-CC3351 costs $55.00 at TI.com, and the store inventory API returns 74 in stock.**
- TI.com is the only source; there is no Digi-Key or Mouser listing.
- TI may cap EVM quantity per order.

**40-pin header**
- **HanElectricity 2541WV-2x20P**: THT, gold, $0.138, 3,873 in stock.
- The SK's Sullins PEC20DAAN has 0 stock.
- THT adds JLC hand or wave soldering cost. The SMD option (Kinghelm, 50 pcs) is weaker mechanically.

**Header series resistors**
- **Count: 28** × 33 Ω 0402, which is every non-power pin, including I2C 3/5/27/28.
- Use 24 if the I2C pins are left without series resistors.
- They are JLC basic (C25105, $0.0012), so there is no loading fee. Seven 4× arrays (C25501, extended) are an option if area is tight.

**HAT-ID EEPROM**
- **BL24C32A-SFRC** ($0.108, 11,669 in stock), priced as requested.
- On a Raspberry Pi the HAT-ID EEPROM is **on the HAT**. The host only routes ID_SD/ID_SC (pins 27/28) on a dedicated bus with pull-ups. Confirm whether an on-board part is wanted. The board-ID EEPROM (§5.9) is a separate item.

---

## 4. Section subtotals (recommended configuration; qty-0 lines excluded)

| Group | Per board | 10 boards |
|---|---|---|
| HDMI (TFP410 + TPD12S016 + connector + passives) | $5.88 | $58.83 |
| Audio (AIC3104 + 12.288 MHz XO + TRRS + passives) | $2.25 | $22.55 |
| Camera (FPC + passives) | $1.01 | $10.05 |
| Wireless, board parts (socket, standoff, screw, 2 level shifters, passives) | $1.91 | $19.06 |
| Expansion (header, HAT EEPROM, 28× 33 Ω, passives) | $0.34 | $3.39 |
| **Board-mounted subtotal** | **$11.39** | **$113.88** |
| Wireless module, plug-in (M2-CC3351) | $55.00 | $550.00 |
| **Section total including module** | **$66.39** | **$663.88** |

**Optional adders, per board:**
- TCA9543A: +$0.73.
- ADV7513 instead of TFP410: +$21.94.
- ES8316 instead of AIC3104: about −$0.70, counting the HP caps it does not need.
- Removing TXS0104: −$0.40.
- Removing the HAT EEPROM: −$0.11.

**JLC fees, not in unit prices:**
- 13 unique placed extended parts (the screw is hand-fit) at $1.50–3.00 each per order (the published rate is $3; a third party reports $1.50 since 2025-12). That is about $20–39 per order, or $2–4 per board for 10 boards.
- The THT header adds the through-hole soldering charge.

---

## 5. Stock summary

**All counted lines are STOCK OK, but some have thinner margins:**
- **TFP410PAPR:** JLC 110, enough for 110 boards. TI.com holds 11,487 at $7.10 as backup.
- **M2-CC3351:** TI.com 74, the only source.
- **PJ-320DB-5A:** 412.
- **12.288 MHz XO:** 448. Backup is HELE HSO321S C160458 (1,641).
- **TCA9543A:** 357 (optional).
- **TLV320AIC3104:** 769 at JLC, with 14,577 at TI.com.
- Everything else has more than 1,700 in stock, and basic passives more than 1 M.

**STOCK RISK, so not used:**
- SiI9022ACNU, IT66121FN, IT6263FN, LT8618SXB.
- TE 2199119-4 (0), Amphenol 10029449 (3), CUI SJ-43514 (9), Sullins PEC20DAAN (0).
- TLV320AIC3106 (25), WM8960 / NAU8822 / AIC23B / SGTL5000 (0).

Stock moves daily. Re-check at order time and lock the parts with a JLC parts pre-order.

---

## 6. Risks

1. **DVI-only HDMI.** There is no HDMI audio or CEC, and some TVs show a "PC" mode. The upgrade path is the ADV7513 (in stock, +$22/board), which adds a 1.8 V rail.
2. **TFP410 thermal and range.** It dissipates up to 0.8 W and is a 0–70 °C part. Solder the PowerPAD with a via array.
3. **DPI/BOOTMODE[15:8] sharing remains** because TFP410 uses DPI. The IT6263-over-OLDI path that would avoid it has no distributor stock.
4. **The TI SDK kernel must have `CONFIG_DRM_TI_TFP410`.** The TI SDK has no reference DT for TFP410 on AM62x, so the DT is new (small) work.
5. **The AIC3104 DT differs from the SK's AIC3106**: compatible string, routing (no MIC3) and the 1.8 V DVDD supply.
6. **The M.2 socket footprint differs from the SK's TE part.** Verify the 3.2 mm stack height against the 1.5 mm standoff and the module's screw position (30 mm).
7. **Footprints and pinouts to check before layout:** the TRRS jack and the HDMI receptacle.
8. **The Wi-Fi module is the dominant cost.** M2-CC3351 at $55 is $550 for 10 boards, and its only source is TI.com (74 pcs, possible per-order cap).

---

## 7. Decisions needed from the user

1. **Accept DVI-only HDMI (TFP410, $4.60) or pay +$21.9 per board for full HDMI with audio (ADV7513, 93 in stock)?**
2. Codec: **TLV320AIC3104** (recommended, SK driver) or **ES8316** (cheapest)?
3. Fit the M2-CC3351 on all 10 boards ($550), or only on some?
4. Keep the on-board HAT-ID EEPROM, given that RPi practice puts it on the HAT?
5. Through-hole or SMD 40-pin header?
6. Camera I2C: a dedicated bus (no TCA9543A, recommended) or the SK-style switch?
7. BT_EN: move it to a 1.8 V GPIO and drop the TXS0104, or keep the SK topology?

---

## Sources

- JLCPCB parts library / API: https://jlcpcb.com/parts (part links in the CSV `url` column)
- LCSC product pages, for example https://www.lcsc.com/product-detail/C7498519.html, C1543847, C369565, C408901, C841649
- Digi-Key: https://www.digikey.com/en/products/result?keywords=SII9022ACNU and ?keywords=TFP410PAPR
- TI: https://www.ti.com/tool/M2-CC3351 ($55.00) and https://www.ti.com/storeservices/cart/opninventory?opn=M2-CC3351 (inventory 74). TFP410 page and datasheet: https://www.ti.com/product/TFP410/part-details/TFP410PAPR and https://www.ti.com/lit/ds/symlink/tfp410.pdf
- SiI9022A/24A datasheet (Aug 2016, via Digi-Key): MCLK not required (internal PLL); power table
- Findchips broker listings: https://www.findchips.com/search/IT66121FN, /IT6263FN, /SII9022ACNU
- Linux mainline sources:
  - `drivers/gpu/drm/bridge/ti-tfp410.c`, `ite-it66121.c`, `ite-it6263.c`, `sii902x.c`
  - `arch/arm64/boot/dts/ti/k3-am625-beagleplay.dts`
  - `k3-am62x-sk-common.dtsi` (codec fixed-clock 12.288 MHz)
- AM62 MCLK accuracy: https://community.toradex.com/t/mclk-setup-for-custom-codec-on-mallow-v1-1-and-am62/23550 and https://lkml.iu.edu/2607.3/01879.html
- JLC fees: https://jlcpcb.com/help/article/pcb-assembly-price and https://techoverflow.net/2024/04/09/jlcpcb-pcba-assembly-price-overview/
