# Schematic generator: handoff guide

This folder builds the APE-SBC Altium schematic and libraries from Python. Symbols, footprints and sheets are defined as code (`symbols.py`, `fplib/*.py`, `sheets/*.py`). `build.py` drives a running Altium Designer through the [altium-mcp](https://github.com/coffeenmusic/altium-mcp) server to create the symbol library, the footprint library and the sheets.

**Status: written without Altium access.** Everything below `build.py check` has not run against a live Altium yet. Do the smoke test (step 5) before trusting any generated sheet, and report what breaks.

**Schematic v0.1:** 16 sheets, 687 designators, 443 nets. `build.py check` passes with no single-node nets, no accidental connections and no overlaps. Open questions are in [`docs/schematic-open-items.md`](../../docs/schematic-open-items.md).

| Sheet | Content |
|---|---|
| 01 Power input | USB-C PD (TPS25730), LM61460 3.3 V, TPS63070 5 V |
| 02 PMIC | TPS6521904, 3.3 V IO switch, VPP and PHY 1.0 V LDOs |
| 03 SiP power | 72 supply balls, beads, decoupling, VMON |
| 04 SiP GND/NC | 104 VSS and 103 NC/RSVD balls |
| 05 SiP IO | 221 signal balls, from the pin-assignment table |
| 06 Clock/reset/boot | 25 MHz oscillator, 32 kHz crystal, MCU_PORz logic, buttons, boot straps and DIP switch |
| 07 Storage | eMMC-module connector, microSD with UHS-I switching |
| 08 Ethernet | DP83867IS, HR911130A |
| 09 USB | USB0 device path, CH335F hub, dual USB-A |
| 10 HDMI | TFP410, TPD12S016, HDMI-A |
| 11 Audio | TLV320AIC3104, 12.288 MHz oscillator, TRRS jack |
| 12 Camera | 15-pin Raspberry Pi CSI FPC |
| 13 Wireless | M.2 Key-E for M2-CC3351 |
| 14 Expansion | 40-pin header, HAT-ID EEPROM (DNP) |
| 15 Debug | FT4232HL quad UART, isolation buffers, Tag-Connect JTAG |
| 16 Misc | Board-ID EEPROM, TMP102, I2C0 pull-ups, LEDs, mounting holes |

**Footprints:** `footprints.py` and `fplib/*.py` define `lib/APE-SBC.PcbLib`, one footprint per package, each pad named after its symbol pin. `build.py check` fails if any symbol pin has no pad or any pad has no pin. See [section 10](#10-footprints).

## How the work is split

| Who | Does what |
|---|---|
| Design side (Jay + Claude, no Altium needed) | Writes and edits symbols and sheets in Python, runs `build.py check`, pushes |
| Altium side (needs a license) | Pulls, runs `build.py lib` / `build.py footprints` / `build.py sheets`, compiles and checks ERC in Altium, commits the generated `.SchDoc` / `.SchLib` / `.PcbLib` files, pushes |

## 1. Prerequisites

- Windows with **Altium Designer** installed under `C:\Program Files\Altium\AD*` and a working license (developed for AD26)
- **Python 3.10+** on `PATH`
- **Git** and **Git LFS** (`git lfs install` once, before cloning)
- Optional: **Claude Code**. The repo's `.mcp.json` registers the Altium MCP server automatically.

## 2. One-time setup

Commands are written for **Git Bash** (installed with Git for Windows). Run them from the repository root.

```bash
git clone https://github.com/shikhakath/APE-SingleBoardComputer.git
```

```bash
git clone https://github.com/coffeenmusic/altium-mcp.git "$USERPROFILE/mcp-servers/altium-mcp"
```

```bash
python "$USERPROFILE/mcp-servers/altium-mcp/start_server.py" --build
```

The `--build` step creates the server's virtual environment in `%USERPROFILE%\.altium-mcp\venvs\<id>\`, which takes about 90 s.

**Known upstream issue:** the server pins `mcp==1.5.0` but not pydantic, so pip installs a pydantic that is too new and the server fails with `ImportError: cannot import name 'eval_type_backport'`. Fix it by installing the repo's lockfile into that venv (replace `<id>` with the folder name):

```bash
"$USERPROFILE/.altium-mcp/venvs/<id>/Scripts/python.exe" -m pip install -r "$USERPROFILE/mcp-servers/altium-mcp/requirements.txt"
```

Check the server can see Altium:

```bash
python hardware/gen/mcp_client.py get_server_status
```

Expect `"altium_found": true` and `"script_found": true`.

## 3. Before every build session

1. Start Altium and wait until it is fully up: license accepted, no dialogs open.
2. Open `hardware/APE - Single Board Computer.PrjPcb`.
3. Keep Altium in the foreground-capable state. **Any modal dialog blocks the script bridge**, and calls then time out after 120 s.

## 4. Offline check (no Altium)

```bash
python hardware/gen/build.py check
```

This writes `hardware/gen/out/`: `netlist.csv`, `schematic_bom.csv`, one `*.spec.txt` per sheet, `symbols_spec.txt`, `footprints_spec.txt` and `footprint_usage.csv` (footprint, designators, assumed pad numbering). It lists single-node nets, which are expected for nets whose other end is on a sheet not written yet.

It also checks the footprints:

- every symbol pin number exists as a pad in the symbol's footprint, and every named pad is a pin;
- every placed part has a footprint (generic passives need their size code in the comment, see section 7);
- pads of different names are at least 0.1 mm apart, drills are at least 0.15 mm, plated rings at least 0.15 mm, and the pin-1 marker clears the copper.

To look at the footprints without Altium, render them to PNG:

```bash
python hardware/gen/footprints.py --png hardware/gen/out/fp
```

Copper is grey, holes white, paste windows orange, silkscreen black, courtyard magenta, body outline dashed blue.

## 5. Build in Altium

Run these in order the first time.

| Step | Command | Then check in Altium |
|---|---|---|
| a. Register files | Close the project in Altium, run `python hardware/gen/build.py project`, reopen the project | The new sheets, `lib\APE-SBC.SchLib` and `lib\APE-SBC.PcbLib` appear in the Projects panel |
| b. Library | `python hardware/gen/build.py lib` | Open `APE-SBC.SchLib`. Check `TPS65219_RHB`: pins on the left and right edges pointing **outward**, names inside the body. Check `RES` and `CAP`: pins horizontal, ends at ±200 mil. |
| b2. Footprints | `python hardware/gen/build.py footprints` | Open `APE-SBC.PcbLib`. Delete the empty `PCBCOMPONENT_1` that Altium puts in a new library. Check `SOT23-5`: pad 1 top left, pads 1-3 on the left. Check `OSD62X-PM_BGA500`: 500 round 0.20 mm pads, A1 dot top left. Check `USB-C_HRO_TYPE-C-31-M-12`: slotted shell holes, not round ones. Then run the PCB library's **Reports » Component Rule Check**. |
| c. Smoke test | `python hardware/gen/build.py smoke` | The command prints `pin map matches the generator`. Open `hardware/gen/out/smoke.SchDoc`: every wire stub touches its pin, net labels sit on wires, GND symbols hang below. |
| d. Sheets | `python hardware/gen/build.py sheets`, or for one sheet `python hardware/gen/build.py sheet 02_PMIC` | Each sheet prints `pin map matches`. Then **Project » Validate PCB Project** and review the Messages panel. |
| e. Commit | `git add hardware && git commit && git push` | Altium binary files are committed as-is; `gen/out/` is ignored |

`lib`, `footprints` and `sheets` also save the documents. The MCP tools themselves never save, so if a run stops halfway, save manually (File » Save All).

## 6. Using Claude Code instead of typing commands

Open the repository folder in Claude Code and approve the `altium` MCP server when asked. Then prompt:

> Read hardware/gen/README.md and DESIGN_PROPOSAL.md. Run the build steps in section 5 in order, stop at the first failure, diagnose it, fix the generator, and continue.

## 7. Rules for editing

- **Rebuilding a sheet erases it.** The builder clears every component, wire, net label, power port, junction and No-ERC marker on the target sheet, plus notes that start with `* `. Once you hand-edit a sheet in Altium, add its module name (for example `s02_pmic`) to `FROZEN_SHEETS` in `build.py`. `build.py sheets` then skips it; naming it explicitly with `build.py sheet` still rebuilds it.
- Sheets are found automatically (`sheets/sNN_*.py`), and so are symbols (`symbols.py` plus `SYMBOLS` in every `symlib/*.py`). Who owns which file, the fixed rail names and the SoC net names are in [`SHEET_CONTRACT.md`](SHEET_CONTRACT.md).
- Connectivity is **by net name**. Every pin gets a short stub with a net label or a power/ground port. The project uses *Automatic* net scope and has no ports or sheet entries, so Altium treats net labels as global. Do not add ports or sheet entries unless you switch the whole project to hierarchical.
- Net-name conventions:
  - Power rails are `<RAIL>_<VOLTAGE>`, for example `VCC_3V3_SYS`, `VDDS_DDR_1V2`, `DDR4_VPP_2V5`.
  - Active-low signals end in `_N`.
  - Nets that go only to a test point start with `TP_`.
  - **`VPP_EFUSE_1V8` is the AM62x eFuse pin and `DDR4_VPP_2V5` is the DDR4 VPP.** Never merge them.
- Designators are numbered by sheet: sheet 02 uses `x2xx` (U200, C200, ...).
- **Footprints.** A symbol with a fixed package names its footprint (`footprint=` in `box()` / `two_pin()` / `Symbol`), and that footprint must exist in `fplib/` with exactly one pad name per pin number. Generic symbols (`RES`, `CAP`, `FERRITE`, `LED`, `DIODE`, `TVS_BI`, `IND`, `CAP_POL`, `XTAL2`) get a footprint per placed part, in this order: `footprint=` passed to `Sheet.add()` (or in a `column()` params dict); `PART_RULES` in `footprints.py` (MPN or comment, for example `BLM15` → `FB0402`, `SS34` → `DIO_SMA`); the EIA size code in the comment with the symbol's prefix (`10k 1% 0402` → `R0402`, `KT-0805G` → `LED0805`). The sheet builder writes that name into each part's PCB model.

## 8. What has not been verified (check during the smoke test)

| Assumption | Where | If wrong |
|---|---|---|
| A pin's `x,y` in the symbol spec is its **body-end** location and the electrical end is `PinLength` further along its orientation; `eRotate0/90/180/270` = right/up/left/down | `schgen.py` (`DIR`, `ORIENT_NAME`) | The smoke test reports a pin-map mismatch. Fix the mapping in `schgen.py` and rebuild. |
| `ISch_NetLabel.Justification`, `ISch_Document.SheetStyle`, `eNoERC` and `ISch_Component.CurrentPartID` can be set from a script | `altium/ape_sheet_builder.pas` | The tool output names the last statement that ran. Comment out that feature (labels default to bottom-left; set the sheet size by hand). |
| `IServerDocument.DoFileSave('')` saves in native format | `altium/ape_save_docs.pas`, builder | Save manually; report the error |
| `create_symbols_batch` creates `APE-SBC.SchLib` when the file does not exist | `build.py lib` | Create an empty SchLib at `hardware/lib/APE-SBC.SchLib` in Altium, save it, rerun `lib` |
| Re-running `lib` on an existing library updates symbols rather than duplicating them | `build.py lib` | Delete `APE-SBC.SchLib` and rerun |
| Opening a missing `.PcbLib` path creates an empty PCB library that `ape_save_docs.pas` can save | `build.py footprints` | Create an empty PcbLib at `hardware/lib/APE-SBC.PcbLib` in Altium, save it, rerun |
| `create_footprints_batch` field values: pad shape 1 = round/oval, 2 = rectangle, 9 = rounded rectangle; slot holes take hole type 2 with `hole_size` = slot width and `hole_width` = slot length; `String2Layer` accepts `Mechanical 13`, `Mechanical 15`, `Top Paste`, `Top Overlay`, `Multi-Layer` | `footprints.py` (`SHAPES`, `Footprint.spec_lines`) | Draw one pad of each kind by hand, dump it with the MCP tool `get_footprint_primitives`, fix the constants, rerun `footprints --fresh` |
| Re-running `create_footprints_batch` on an existing library adds a second copy of each footprint (it registers new components and never deletes) | `build.py footprints` refuses to run on an existing library unless you pass `--fresh` (deletes and regenerates) or name only new footprints | Close the PcbLib in Altium before `--fresh` |

## 9. Troubleshooting

- **`No response received from Altium (timeout)`.** Altium is not running, is still starting, has a dialog open, or has no license. Fix that and rerun.
- **Script executor wedged** (calls return instantly and do nothing). Run `python "%USERPROFILE%\mcp-servers\altium-mcp\dev\unwedge.py"`, or press Ctrl+F3 in Altium, or restart Altium.
- **`Select Item To Run` dialog.** Altium cannot find the script project. Rerun `start_server.py --build` and check `get_server_status`.
- **Symbol `MISSING` in the builder result.** Run `build.py lib` first. Also check that the `LIBRARY` path in `out/symbols_spec.txt` is the same file the sheet references.

## 10. Footprints

`footprints.py` holds the data model, the checks and the footprint rules for generic parts. The footprints live in `fplib/`, one module per package family, with the land-pattern source (document, revision, page) in a comment above each one.

| Module | Footprints | Land pattern source |
|---|---|---|
| `sip.py` | `OSD62X-PM_BGA500` | Octavo datasheet section 8.1 and layout guide: 0.20 mm NSMD lands, A1/A28/V1/V28 empty, ball names from `data/osd6254_ballmap.csv` |
| `ti_power.py` | `VQFN32_RSM_4X4`, `WQFN38_REF_4X6`, `VQFN-HR14_RJR_3.5X4`, `VQFN-HR15_RNM_2.5X3`, `WSON8_DSG_2X2`, `WSON6_DRV_2X2`, `SOT583-8` | TI example board layouts and stencils |
| `sot_son.py` | `SOT23-3`, `SOT23-5`, `SOT23-6`, `SC70-6`, `SOT553-5`, `SOT563-6`, `USON10_DQA`, `X2SON3_DMX`, `X1SON2_DPY` | TI (LRC for `SOT23-3`); the other vendors' lands for the shared SOT-23s are compared in the comments |
| `so_diode.py` | `SOIC8_3.9X4.9_P1.27`, `TSSOP8_4.4X3.0_P0.65`, `TSSOP16_4.4X5.0_P0.65`, `TSSOP24_4.4X7.8_P0.65`, `SOD323`, `DIO_SMA` | Microchip, TI PW, Diodes, MDD |
| `ic_large.py` | `HTQFP64_PAP_10X10`, `VQFN32_RHB_5X5`, `VQFN48_RGZ_7X7`, `LQFP64_10X10_P0.5`, `QFN28_4X4_P0.4` | TI; **FTDI and WCH give no land pattern, so `LQFP64` and `QFN28` are derived per IPC-7351B** from the package tolerances |
| `chip.py` | `R0402`, `R0603`, `C0402`, `C0603`, `C0805`, `C1206`, `FB0402`, `FB0603`, `LED0603`, `LED0805`, `FUSE_BHFUSE_BSMD1206` | UNI-ROYAL, Samsung, Murata, KENTO, BHFUSE |
| `mag_xtal.py` | `IND_MURATA_DFE252012F`, `IND_SUNLORD_MWSA0402S`, `IND_SUNLORD_MWSA0603S`, `CP_SMD_D6.3X5.8`, `XTAL_EPSON_FC-135`, `XTAL_3225_4P`, `OSC_3225_4P`, `OSC_2520_4P`, `CMC_SUNLORD_SDCW2012` | Murata, Sunlord, Epson, YXC, SJK, ECS; **the Honor polymer cap has no land pattern, so `CP_SMD_D6.3X5.8` is derived per IPC-7351B** |
| `conn_io.py` | `USB-C_HRO_TYPE-C-31-M-12`, `HDMI_A_XFCN_19F_S_D`, `MICROSD_HRO_TF-01A`, `JACK_HRO_PJ-320DB`, `FPC_TE_1-1734248-5`, `B2B_LSM_GB042-34P-H10`, `B2B_LSM_GB042-30P-H10` | Connector drawings; GB042 from the LS Mtron catalogue |
| `conn_mech.py` | `RJ45_HANRUN_HR911130A`, `USBA_2X_BX-TYPE-A-MWC44`, `M2_KEYE_APCI0085`, `HDR_2X20_P2.54_THT`, `SW_DIP4_SMD_2.54`, `SW_TACT_5.1X5.1_SMD4`, `TC2070-NL`, `STANDOFF_WE_9774015243R`, `MH_M2.5_PLATED`, `TP_PAD_1.0` | Connector drawings, Raspberry Pi HAT mechanical spec |

The conventions are at the top of `footprints.py`:

- Units are mm, +y is up, and the origin is the body centre.
- Pin 1 is at the top left (IPC-7351 zero orientation).
- The body outline is on Mechanical 13 and the courtyard on Mechanical 15.
- Silkscreen lines are 0.15 mm wide and kept 0.15 mm off copper.
- Unnamed pads are mechanical holes.
- Some terminals are one piece of package metal carrying several pin numbers (TPS25730 REF, TPS63070 RNM). They are listed in `joined`, and `build.py check` makes sure those pins share a net.

### Board rules the footprints rely on

`create_footprints_batch` has no per-pad mask or paste fields, so the footprints carry copper only. The PCB needs these rules (values from `docs/research/bom/jlcpcb-stackup-and-cost.md` section 5):

| Rule | Scope | Value |
|---|---|---|
| Solder mask expansion | All | 0.05 mm |
| Solder mask expansion | `InComponent('U1')`: SiP lands, 0.20 mm NSMD | 0 (1:1 opening) |
| Paste mask expansion | All | 0 |
| Paste mask expansion | The query that `build.py footprints` prints: exposed and HotRod pads whose stencil is split into windows (the windows are fills on Top Paste) | −2.5 mm, so the pad itself adds no paste |
| Paste mask expansion | `HasFootprint('TC2070-NL')` | −2.5 mm (the Tag-Connect pads stay bare) |

Layout items that are not in the footprints:

- **TFP410 (`HTQFP64_PAP_10X10`):** TI's thermal land is 8.0 × 8.0 mm of GND copper under solder mask with a 5.0 mm opening. Pad 65 is only the opening. Add the 8 mm GND polygon and the 6 × 6 grid of 0.2 mm vias at 1.3 mm pitch.
- **Exposed pads:** add thermal vias as the TI layouts show.
- **Murata beads (`FB0402`, `FB0603`):** Murata's lands are mask-defined, so the pad is the opening. Route at least 0.7 mm of copper into each land, or 3.3 mm for the 6 A BLM18SG260.
- **`USON10_DQA`:** the DQA0010B variant joins pads 3 and 8 (both GND) with a 0.3 mm bar. Draw a GND track between them.
- **`STANDOFF_WE_9774015243R`:** the copper ring is on both layers (non-plated through-hole pad), and the paste ring is drawn on Top Paste. Check that Altium adds no paste of its own.

### Pad numbering to verify before layout

The manufacturer drawings for these parts do not give the pad numbering used here. Each footprint has an `assumed` note in the code, which `build.py footprints` prints and `out/footprint_usage.csv` lists. They correspond to open items B2–B11 in [`docs/schematic-open-items.md`](../../docs/schematic-open-items.md).

| Footprint | Parts | Assumed | Item |
|---|---|---|---|
| `USB-C_HRO_TYPE-C-31-M-12` | J100, J1500 | Shell slots S1/S2 front (0.6 × 1.4 mm, at the board edge), S3/S4 rear (0.6 × 1.7 mm). The shared pads A1B12, A4B9, B4A9 and B1A12 are as drawn. | B2 |
| `HDMI_A_XFCN_19F_S_D` | J1000 | Pins 1–19 in HDMI type-A order, pin 1 at +x with the opening down (as on SK-AM62B J5); legs 20–23 | B3 |
| `JACK_HRO_PJ-320DB` | J1100 | The drawing numbers the pads. Only the contact roles (sleeve, tip, rings) come from its schematic. | B4 |
| `FPC_TE_1-1734248-5` | J1200 | Both tails of circuit n are pad n; circuit 1 at the right, as drawn | B5 |
| `B2B_LSM_GB042-34P-H10`, `-30P-H10` | J700, J701 | The LS Mtron catalogue gives geometry but no pin numbers. Numbering: 1–17 along one row and 18–34 back along the other, taken from a third-party flex board with this plug and the ROCK64 / ROCK 3A symbols. There are no hold-down pads, so pins 35–38 / 31–34 were removed from the symbols. | B6 |
| `MICROSD_HRO_TF-01A` | J702 | Card detect "Cd" = 9; shell tabs 10/11 rear, 12/13 front | B7 |
| `USBA_2X_BX-TYPE-A-MWC44` | J900 | Pins 1–4 = lower port in the front row, VBUS–D−–D+–GND left to right seen from the front; 5–8 upper port; 9–12 shell | B8 |
| `M2_KEYE_APCI0085` | J1300 | SMT tabs 76 (left, pin-1 end) and 77 | B9 |
| `HDR_2X20_P2.54_THT` | J1400 | Raspberry Pi numbering, odd row toward −y, square pin 1 | B10 |
| `SW_DIP4_SMD_2.54` | SW602 | Pads 1–4 along the numbered edge, 5–8 along the ON edge, position k = pads k and 9−k | B11 |
| `RJ45_HANRUN_HR911130A` | J800 | Shield tabs: 15 on the pin-1 side, 16 the other | – |
| `SW_TACT_5.1X5.1_SMD4` | SW200, SW600, SW601 | Pads 1–4 = terminals A–D | – |
| `CMC_SUNLORD_SDCW2012` | L900–L902 | The catalogue does not say whether its view is top or bottom. A mirror reverses both windings together, so it is electrically the same. | – |

The pad sizes of `HDR_2X20_P2.54_THT` and `RJ45_HANRUN_HR911130A` were also chosen here; the drawings give hole sizes only.

### Adding or changing a footprint

1. Write it in the matching `fplib/` module with the source comment. Its name must be the symbol's `footprint=`.
2. Run `python hardware/gen/footprints.py <module>` until it reports no problems. Render it with `--png` and compare it with the drawing.
3. Run `python hardware/gen/build.py check`.
4. In Altium, run `build.py footprints NAME` for a new footprint, or `build.py footprints --fresh` after a change (close the library first).

## Files

| File | Purpose |
|---|---|
| `schgen.py` | Generator core: symbol layout, sheet placement, stubs and labels, pin-map check |
| `SHEET_CONTRACT.md` | Ownership, fixed rail and net names, rules for writing sheets |
| `symbols.py` | Generic, shared, PMIC and SiP symbols, each IC with its datasheet pin-table reference |
| `symlib/*.py` | Per-area symbols; each module exports `SYMBOLS` |
| `sheets/sNN_*.py` | One module per sheet; `build(sch_dir)` returns a `Sheet` |
| `data/osd6254_ballmap.csv` | All 500 SiP balls, verified against the Octavo datasheet |
| `data/pinmux_allocation.csv` | SoC pin assignment: the source of every SoC-side net name |
| `footprints.py` | Footprint data model and builders (mm, emitted in mils), pad-vs-pin check, per-part footprint rules for generic symbols, PNG renderer |
| `fplib/*.py` | Footprints by package family; each module exports `FOOTPRINTS`, with the land-pattern source and page above every footprint |
| `build.py` | Command-line driver |
| `mcp_client.py` | Minimal stdio client for the Altium MCP server (no Claude needed) |
| `altium/ape_sheet_builder.pas` | DelphiScript run through the MCP `run_altium_script` sandbox: builds one sheet from `C:\Users\Public\altium_mcp\ape_sheet_spec.txt` and saves it |
| `altium/ape_save_docs.pas` | Saves the documents listed in `C:\Users\Public\altium_mcp\ape_save_list.txt` |
