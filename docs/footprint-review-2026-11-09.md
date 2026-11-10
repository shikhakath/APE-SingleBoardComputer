# Footprint review 2026-11-09 (Project Errors.xlsx, sheet 1)

Response to the footprint and stock review. All fixes are in the footprint sources (`hardware/gen/fplib/`, `hardware/gen/footprints.py`); nothing in the schematic sheets, the BOM or `PCB.PcbDoc` was changed.

## Why the stencil items came up

The windowed paste for exposed pads was already drawn as fills on Top Paste, but each pad still printed its own full paste unless the board rule `Paste_Windowed` applied. The library view, and any board without that rule, showed the pad as one piece. Each pad under a stencil window now carries its own "no paste" setting, so the footprint prints TI's windows on its own. `create_footprints_batch` cannot set this, so `build.py footprints` applies it with a new script, `hardware/gen/altium/ApeFootprints.pas`.

## Footprint and stencil fixes

| Sheet | Part (ref) | Reported | Fix | Source |
|---|---|---|---|---|
| 01 | TPS63070RNMR (U102), `VQFN-HR15_RNM_2.5X3` | Stencil: pads 9, 10, 11 one piece | Two windows per pad, now self-contained | RNM0015A stencil p.41 |
| 01 | TPS25730DREFR (U100), `WQFN38_REF_4X6` | No vias in the large pads; stencil one piece | 8 vias (5 in pad 39, 3 in pad 40); 4 + 2 windows self-contained | REF0038A layout p.65, stencil p.66 |
| 01 | TVS2200DRVR (D100), `WSON6_DRV_2X2` | No vias in the centre pad | 2 vias; 2 windows self-contained | DRV0006A p.19–20 |
| 01 | LM61460AANRJRR (U101), `VQFN-HR14_RJR_3.5X4` | Stencil: pad 10 one piece | Pad 10 two windows (and the L-pads 1/5/9/11), self-contained | RJR0014A stencil p.57 |
| 02 | TPS6521904RSMR (U200), `VQFN32_RSM_4X4` | Pad 33: no vias; stencil one piece | 5 vias; 4 windows self-contained | RSM0032B p.158–159 |
| 02 | TPS22965DSGR (U201), `WSON8_DSG_2X2` | Pad 9: no vias; stencil one piece | 2 vias; 2 windows self-contained | DSG0008A p.30–31 |
| 07 | TF-01A (J702), `MICROSD_HRO_TF-01A` | Pads 11–13 labelled differently | Shell tabs renumbered to match the LCSC footprint (C91145): 10 rear-left, 11 front-left, 12 front-right, 13 rear-right. All four are GND, so no schematic change. | LCSC/EasyEDA footprint |
| 08 | DP83867ISRGZR (U800), `VQFN48_RGZ_7X7` | No vias; stencil one piece | 12 vias (on the stencil webs); 9 windows self-contained | RGZ0048B p.127–128 |
| 09 | BX-TYPE-A-MWC44 (J900), `USBA_2X_BX-TYPE-A-MWC44` | Two circles should be squares | VBUS pads 1 and 5 (pin 1 of each port) are square, as in the LCSC footprint (C18077688) | LCSC/EasyEDA footprint |
| 10 | TFP410PAPR (U1000), `HTQFP64_PAP_10X10` | Pad 65 too small, no vias | Pad 65 is now TI's 8.0 × 8.0 mm thermal land with its own −1.5 mm mask and paste expansion (5.0 mm solder-mask-defined opening, 5.0 mm paste), and 36 vias on a 6 × 6 grid at 1.3 mm | PAP land pattern p.43 |
| 11 | TLV320AIC3104IRHBR (U1100), `VQFN32_RHB_5X5` | Stencil: pad 33 one piece | 4 windows self-contained. Also added TI's 5 vias (not on the list, but the layout shows them) | RHB0032E p.101–102 |
| 15 | TYPE-C-31-M-12 (J100, J1500), `USB-C_HRO_TYPE-C-31-M-12` | S1–S4 mislabelled | S1–S4 now follow the LCSC footprint's shell pads 1–4 (C165948): S1 rear-right, S2 front-right, S3 front-left, S4 rear-left. All four are one net on each sheet, so no schematic change. | LCSC/EasyEDA footprint |

The same change also covers two footprints that were not on the list: the CH335F pad 29 (`QFN28_4X4_P0.4`) windows and the Tag-Connect pads (`TC2070-NL`, no paste) no longer depend on board rules.

All thermal vias are 0.2 mm drill / 0.4 mm pad (the `VIA_SIG` style) at TI's "(0.2) TYP VIA" positions. Order them filled and capped (JLCPCB POFV, the 6+ layer default).

## Still to do (needs Altium; not run while the board is being routed by hand)

1. Rebuild the changed footprints in `hardware/lib/APE-SBC.PcbLib` (this touches only the library, not `PCB.PcbDoc`):

   ```bash
   python hardware/gen/build.py footprints --replace VQFN-HR15_RNM_2.5X3 WQFN38_REF_4X6 WSON6_DRV_2X2 VQFN-HR14_RJR_3.5X4 VQFN32_RSM_4X4 WSON8_DSG_2X2 MICROSD_HRO_TF-01A VQFN48_RGZ_7X7 USBA_2X_BX-TYPE-A-MWC44 HTQFP64_PAP_10X10 VQFN32_RHB_5X5 USB-C_HRO_TYPE-C-31-M-12 QFN28_4X4_P0.4 TC2070-NL
   ```

   `ApeFootprints.pas` has not run in Altium yet. If it stops, `python hardware/gen/build.py unwedge` and report the last line of `C:\Users\Public\altium_mcp\ape_log.txt`.
2. In the PCB, pull the new footprints in with **Tools » Update From PCB Libraries** for U100, U101, U102, D100, U200, U201, J702, U800, J900, U1000, U1100, J100, J1500, U900 and J1501.
3. After the update, check that the vias inside the exposed pads have the pad's net (GND, or DRAIN for U100 pad 40) and that the TFP410 pad 65 shows a 5.0 mm mask opening in 3D/mask view.

## Out of stock or sourcing (noted only; no changes yet)

| Sheet | Part | Ref | Note |
|---|---|---|---|
| 06 | SN74LVC1G11DCKR | U601 | Out of stock ([Digi-Key](https://www.digikey.com/en/products/detail/texas-instruments/SN74LVC1G11DCKR/770206)). Needs an in-stock SC70-6 3-input AND (same `SC70-6` footprint if pin-compatible). |
| 07 | GB042-34P-H10-E3000 | J700 | Out of stock ([JLC](https://jlcpcb.com/partdetail/20541642-GB042_34P_H10E3000/C9900072839)); already broker-only (open item A1). |
| 07 | GB042-30P-H10-E3000 | J701 | Out of stock ([JLC](https://jlcpcb.com/partdetail/57874060-GB042_30P_H10E3000/C9900268013)); DNP retention plug. |
| 07 | TPS22996DRLR | U700 | Out of stock ([Digi-Key](https://www.digikey.com/en/products/detail/texas-instruments/TPS22996DRLR/22147193)). |
| 09 | BX-TYPE-A-MWC44 | J900 | "Where to get part?" — LCSC/JLC C18077688 (Bossie). Check stock there. |
| 11 | 3N12288G33YC | Y1100 | Out of stock ([utsource](https://www.utsource.net/pro/3N12288G33YC.html)). Needs a 12.288 MHz 3.2 × 2.5 mm oscillator with OE on pad 1. |
| 15 | X322512MSB4SI | Y1500 (also Y900) | The review links ECS-120-12-33-AEN-TR ([Digi-Key](https://www.digikey.com/en/products/detail/ecs-inc/ECS-120-12-33-AEN-TR/9648812)): 12 MHz, ±25 ppm, **12 pF** load, 4-pad SMD. Its family is 3.2 × 2.5 mm, but the size of this exact suffix is not confirmed. Y1500 is 20 pF today with 33 pF load caps, so swapping it means new load caps, and its pad numbering must be checked against `XTAL_3225_4P`. |

Sheets 2 and 3 of the workbook (62_CONFIG checks, R611 to 10k) are schematic items and were not part of this pass.
