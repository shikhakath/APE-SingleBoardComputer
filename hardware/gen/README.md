# Schematic generator: handoff guide

This folder builds the APE-SBC Altium schematic and libraries from Python. Symbols, footprints and sheets are defined as code (`symbols.py`, `fplib/*.py`, `sheets/*.py`). `build.py` drives a running Altium Designer through the [altium-mcp](https://github.com/coffeenmusic/altium-mcp) server to create the symbol library, the footprint library and the sheets.

**Status: built and compiled on Altium Designer 26.6 (2026-10-20).**
- `lib` built 65 symbols in 41 s and `footprints` built 65 footprints with 0 primitive errors.
- `sheets` built all 16 sheets in about 2 minutes, each matching the generator pin for pin.
- The project compiles with **0 fatal errors and no unexpected ERC violations**. The MCP's `get_erc_violations` also lists the No-ERC-marked pins it should ignore: 7 "floating input" plus 259 "unconnected pin" entries, every one a deliberate no-connect. The other 65 warnings are pin-type notices (passive-only nets, IO and output pins on one net).

Section 8 lists what that run proved and fixed.

**PCB set up (2026-10-20), [section 11](#11-pcb-setup):** `build.py pcb` gives `PCB.PcbDoc` the 100 × 70 mm outline, the JLC06161H-3313 6-layer stack, three impedance profiles, net and differential-pair classes, the SiP room and the design rules, and imports the schematic. All 707 parts (660 fitted, 47 DNP) arrive with their footprints, 449 nets, and every pad's net matched the generator at that point. The sheets have since moved to 717 parts and 458 nets (2026-11-04); the next Update PCB brings those in.

**Schematic v0.1:** 16 sheets, 717 designators, 458 nets. `build.py check` passes with no single-node nets, no accidental connections and no overlaps. Open questions are in [`docs/schematic-open-items.md`](../../docs/schematic-open-items.md).

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
| a. Check Altium | `python hardware/gen/build.py ping` | Prints nothing and exits 0 when Altium runs scripts. If it fails, see section 9. |
| b. Library | `python hardware/gen/build.py lib` | It creates `lib/APE-SBC.SchLib` if missing, then adds the symbols in six batches (each under the MCP's fixed 120 s limit; the whole library takes about 40 s). Open the library: `TPS65219` has pins pointing outward with names inside the body; `RES`/`CAP` are horizontal. |
| b2. Footprints | `python hardware/gen/build.py footprints` | Open `APE-SBC.PcbLib` (the empty `PCBComponent_1` Altium puts in a new library is removed automatically). Check `SOT23-5`: pad 1 top left, pads 1-3 on the left. Check `OSD62X-PM_BGA500`: 500 round 0.20 mm pads, A1 dot top left. Check `USB-C_HRO_TYPE-C-31-M-12`: slotted shell holes, not round ones. Then run the PCB library's **Reports » Component Rule Check**. |
| c. Smoke test | `python hardware/gen/build.py smoke` | Prints `pin map matches the generator`. Open `hardware/gen/out/smoke.SchDoc`. |
| d. Sheets | `python hardware/gen/build.py sheets`, or one sheet: `python hardware/gen/build.py sheet 02_PMIC` | Each sheet prints `pin map matches`. |
| e. Register | `python hardware/gen/build.py register` (project open) or `project` (project closed) | The sheets and libraries appear in the Projects panel. Then **Project » Validate PCB Project** and review the Messages panel. |
| e2. Variant | `python hardware/gen/build.py variant` | **Project » Variants** shows `Production` with every DNP part Not Fitted. Rerun it when a sheet's DNP flags change, and choose this variant for BOM and pick-and-place outputs. |
| f. PCB | `python hardware/gen/build.py pcb` | Prints `pads match the schematic netlist`. See section 11. |
| g. Commit | `git add hardware && git commit && git push` (from the repository root, see section 9) | Altium binary files are committed as-is; `gen/out/` is ignored |

`lib`, `footprints` and `sheets` also save the documents. The MCP tools themselves never save, so if a run stops halfway, save manually (File » Save All).

## 6. Using Claude Code instead of typing commands

Open the repository folder in Claude Code and approve the `altium` MCP server when asked. Then prompt:

> Read hardware/gen/README.md and DESIGN_PROPOSAL.md. Run the build steps in section 5 in order, stop at the first failure, diagnose it, fix the generator, and continue.

## 7. Rules for editing

- **Rebuilding a sheet erases it.** The builder clears every component, wire, net label, power port, junction and No-ERC marker on the target sheet, plus notes that start with `* `. Once you hand-edit a sheet in Altium, add its module name (for example `s02_pmic`) to `FROZEN_SHEETS` in `build.py`. `build.py sheets` then skips it; naming it explicitly with `build.py sheet` still rebuilds it.
- Sheets are found automatically (`sheets/sNN_*.py`), and so are symbols (`symbols.py` plus `SYMBOLS` in every `symlib/*.py`). Who owns which file, the fixed rail names and the SoC net names are in [`SHEET_CONTRACT.md`](SHEET_CONTRACT.md).
- **Drawing conventions** (all applied by `Sheet.drawing()` in `schgen.py`; no sheet code needed):
  - Every net label sits on a wire that runs under the whole label.
  - Vertically adjacent pins on the same supply or ground share one bus wire, with junction dots where three wires meet, and a single port. This covers one side of a part, or a column of passives. Ground hangs below the run; a supply sits on top, if there is 500 mil of room.
  - A lone supply pin gets a net label. A sideways port is used only when the label would run into something.
  - Passives show only their value (`4.7uF`). The full text goes in a hidden `Spec` parameter.
  - `build.py check` rejects a wire end touching another net and any crossing of two different nets.
- Connectivity is **by net name**. Every pin gets a short stub with a net label or a power/ground port. The project uses *Automatic* net scope and has no ports or sheet entries, so Altium treats net labels as global. Do not add ports or sheet entries unless you switch the whole project to hierarchical.
- Net-name conventions:
  - Power rails are `<RAIL>_<VOLTAGE>`, for example `VCC_3V3_SYS`, `VDDS_DDR_1V2`, `DDR4_VPP_2V5`.
  - Active-low signals end in `_N`.
  - Nets that go only to a test point start with `TP_`.
  - **`VPP_EFUSE_1V8` is the AM62x eFuse pin and `DDR4_VPP_2V5` is the DDR4 VPP.** Never merge them.
  - **Merged names.** The design has no 0R links: all 35 were dropped on 2026-11-10, DNP ones simply removed. Each fitted link's two nets are one net now, listed in `MERGED_NETS` in `schgen.py` (old name to the name kept) and applied as every pin is placed. So the sheets can keep naming the IO bank behind a pull-up (`VDDSHV0` is `VCC_3V3_SYS`, `VDDSHV1` is `VDD_1V8`), and `M2_SDIO_*` is `WL_SDIO_*`. The DNP caps `C831` and `C913` now have GND on both pins.
- Designators are numbered by sheet: sheet 02 uses `x2xx` (U200, C200, ...).
- **DNP options:** mark a part with `{"DNP": "1"}`, then run `build.py variant`. Outputs on `[No Variations]` still treat it as fitted, so give every option a value that is safe if fitted, or leave the footprint out.
- **Footprints.** A symbol with a fixed package names its footprint (`footprint=` in `box()` / `two_pin()` / `Symbol`), and that footprint must exist in `fplib/` with exactly one pad name per pin number. Generic symbols (`RES`, `CAP`, `FERRITE`, `LED`, `DIODE`, `TVS_BI`, `IND`, `CAP_POL`, `XTAL2`) get a footprint per placed part, in this order: `footprint=` passed to `Sheet.add()` (or in a `column()` params dict); `PART_RULES` in `footprints.py` (MPN or comment, for example `BLM15` → `FB0402`, `SS34` → `DIO_SMA`); the EIA size code in the comment with the symbol's prefix (`10k 1% 0402` → `R0402`, `KT-0805G` → `LED0805`). The sheet builder writes that name into each part's PCB model.

## 8. What the AD26 run proved and fixed

**Verified:**
- The pin model: a symbol pin's `x,y` is its body end, the electrical end is `PinLength` further along, and `eRotate0/90/180/270` are right/up/left/down.
- `CurrentPartID`, net-label `Justification`, `SheetStyle`, `eNoERC`, and `DoFileSave('')` after `SetFileName` all work from a script.

**Fixed (each one used to stall the build):**

| Problem | Fix |
|---|---|
| The MCP's `run_altium_script` sandbox has only a few scratch variables and no helper functions. Any other identifier (for example `SbxField`) pauses the script in Altium's debugger, and every later script then does nothing. | All builder code lives in its own script project, `altium/ApeScripts.PrjScr`, with declared locals and helpers. `build.py` runs it directly (`run_ape`). |
| A procedure named `Register` fails to compile with "Program name expected" (it is a reserved word). | Renamed. Avoid Pascal reserved words for procedure names. |
| Opening a missing `.SchLib`/`.PcbLib` path does **not** create it, and `WorkspaceManager:SaveObject` with `SaveAs` always opens a Save As dialog. | `ApeScripts>NewLib`: `DM_CreateNewDocument`, then `SetFileName`, then `DoFileSave`. |
| Calling `Client.OpenDocument` on a document that is already open, then saving it, kills the script. | Reuse the open document (`Client.IsDocumentOpen` / `GetDocumentByPath`). |
| `create_symbols_batch` waits at most 120 s. | `lib` sends batches of about 250 pins. |
| When a script has a compile error, Altium opens it in its editor and later runs use that in-memory copy. | After editing `ApeScripts.pas`, close it in Altium (or restart Altium) before the next run. |
| Rebuilding a sheet by deleting its objects in place left the old copies, which gave 529 duplicate designators. | `build_sheet` closes the sheet in Altium (`CloseDocs`) and starts from a fresh copy of `altium/SheetTemplate.SchDoc`. |
| Setting `SheetStyle` alone leaves the in-memory sheet at the template's A size, so ERC reported 1000 "off sheet" objects. | The builder also sets a custom size. Each sheet picks the smallest Altium sheet its content fits once shifted to the top border: Altium's B/C/D/E are 15×9.5, 20×15, 32×20 and 42×32 in, smaller than the paper sizes. Even then, the open sheet keeps the old size until it is reloaded, so `build.py sheets` closes the sheets it built. |
| The project compile reuses cached results for sheets it considers unchanged. | After `sheets`, if ERC still shows stale results, save all sheets (File » Save All, or `save_docs`) and compile again. |
| `WorkspaceManager:SaveObject` with ObjectKind `Project` saves nothing. | `AddToProject` saves the project's own server document. |
| A script-created No-ERC marker suppresses nothing by default. | The builder sets `IsActive` and `SuppressAll`. The MCP's ERC reader still lists those pins; check against the generator's `NC` nets. |
| Every sheet rebuild gave components new unique IDs, which would orphan the variant's entries and the PCB's component links. | `BuildSheet` sets an ID derived from the designator (`schgen.unique_id`). |
| A part sometimes came out with no pins (`93LC46B_OT`, the first symbol alphabetically, or the last symbol created): `Replicate` drops the pins of the symbol the library editor is showing. | `BuildSheet` shows a different symbol before copying that one. |
| Running an unknown procedure name makes Altium do nothing, with no message. | `run_ape` reports "never started" when no log appears and no dialog is open. |
| The first PCB import reported "Footprint Not Found" for every part: the sheets set `UseComponentLibrary`, so Altium looked for footprints in the symbol's `.SchLib`. | `BuildSheet` sets it to False ("Any" library); the project's `APE-SBC.PcbLib` is found. |
| Every through-hole pad imported without a net, and body and courtyard lines sat on no layer: `create_footprints_batch` maps layer names with `String2Layer`, which on AD26 returns no layer for `Multi-Layer` and `Mechanical 13`. | `footprints.py` writes `Multi Layer`, `Mechanical Layer 13` and `Mechanical Layer 15`. |

`create_footprints_batch` field values are now verified: `build.py pcb report` checks every pad's net against the generator, and the pads, body and courtyard land on Multi-Layer, Mechanical 13 and Mechanical 15. **Still unverified:** whether re-running `lib` on an existing library updates symbols or duplicates them. Until that is known, delete `APE-SBC.SchLib` before a full re-run.

## 9. Troubleshooting

- **A command times out, or `ping` fails.** Run `python hardware/gen/build.py unwedge`. It closes Altium dialogs, stops a paused script (`X2.EXE -REditScript:Stop`), and pings again. If it still fails, restart Altium.
- **The result names the dialogs it found.** "Information" or "Error" right after a script starts usually means a compile error. Read it in Altium, fix `ApeScripts.pas`, then close the script in Altium.
- **Altium shows "Import Drill Data" at startup.** Altium is reopening a drill file left in its workspace. On the development machine it was `gassensor-NPTH.drl` under *Free Documents*. Close that document and the prompt stops. If an `X2.EXE` stays stuck on the dialog, end it in Task Manager.
- **Symbol `MISSING` in a sheet result.** Run `build.py lib` first.
- **`git status` inside `hardware/` shows `gen/`, `lib/` and `sch/` as untracked.** `hardware/.git` is Altium's own version-control repository for the project, nested in this one. Run git from the repository root.
- **Altium opens "Save APE - Single Board Computer to Server" when the project closes.** That is Altium 365 committing and pushing `hardware/.git`. Press Cancel; `build.py pcb eco-options` closes it by itself and uploads nothing.

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

Mask and paste come from these board rules (values from `docs/research/bom/jlcpcb-stackup-and-cost.md` section 5); `build.py pcb rules` creates them (section 11). Pads that need something else carry it in the footprint (`Pad.paste` / `Pad.mask`): every pad under a stencil window prints no paste of its own, the Tag-Connect pads print none, and TFP410 pad 65 has its own mask and paste. `create_footprints_batch` cannot set these, so `build.py footprints` applies them with `altium/ApeFootprints.pas` (PadMasks). The last two paste rules below are therefore only a backstop:

| Rule | Scope | Value |
|---|---|---|
| Solder mask expansion | All | 0.05 mm |
| Solder mask expansion | `InComponent('U1')`: SiP lands, 0.20 mm NSMD | 0 (1:1 opening) |
| Paste mask expansion | All | 0 |
| Paste mask expansion | The query that `build.py footprints` prints: exposed and HotRod pads whose stencil is split into windows (the windows are fills on Top Paste) | −2.5 mm (backstop; the pads already print no paste) |
| Paste mask expansion | `HasFootprint('TC2070-NL')` | −2.5 mm (the Tag-Connect pads stay bare) |

Layout items that are not in the footprints:

- **Thermal vias** are in the footprints (`Footprint.vias`, 0.2 / 0.4 mm at the positions of each TI example layout, including the 36 under TFP410 pad 65, which is TI's 8.0 mm land with a 5.0 mm mask-defined opening). After updating a part from the library, check that its vias took the pad's net.
- **Murata beads (`FB0402`, `FB0603`):** Murata's lands are mask-defined, so the pad is the opening. Route at least 0.7 mm of copper into each land, or 3.3 mm for the 6 A BLM18SG260.
- **`USON10_DQA`:** the DQA0010B variant joins pads 3 and 8 (both GND) with a 0.3 mm bar. Draw a GND track between them.
- **`STANDOFF_WE_9774015243R`:** the copper ring is on both layers (non-plated through-hole pad), and the paste ring is drawn on Top Paste. Check that Altium adds no paste of its own.

### Pad numbering to verify before layout

The manufacturer drawings for these parts do not give the pad numbering used here. Each footprint has an `assumed` note in the code, which `build.py footprints` prints and `out/footprint_usage.csv` lists. They correspond to open items B2–B11 in [`docs/schematic-open-items.md`](../../docs/schematic-open-items.md).

| Footprint | Parts | Assumed | Item |
|---|---|---|---|
| `USB-C_HRO_TYPE-C-31-M-12` | J100, J1500 | Shell slots follow the LCSC footprint's pads 1–4: S1 rear-right, S2 front-right, S3 front-left, S4 rear-left (rear 0.6 × 1.7 mm, front 0.6 × 1.4 mm). The shared pads A1B12, A4B9, B4A9 and B1A12 are as drawn. | B2 |
| `HDMI_A_XFCN_19F_S_D` | J1000 | Pins 1–19 in HDMI type-A order, pin 1 at +x with the opening down (as on SK-AM62B J5); legs 20–23 | B3 |
| `JACK_HRO_PJ-320DB` | J1100 | The drawing numbers the pads. Only the contact roles (sleeve, tip, rings) come from its schematic. | B4 |
| `FPC_TE_1-1734248-5` | J1200 | Both tails of circuit n are pad n; circuit 1 at the right, as drawn | B5 |
| `B2B_LSM_GB042-34P-H10`, `-30P-H10` | J700, J701 | The LS Mtron catalogue gives geometry but no pin numbers. Numbering: 1–17 along one row and 18–34 back along the other, taken from a third-party flex board with this plug and the ROCK64 / ROCK 3A symbols. There are no hold-down pads, so pins 35–38 / 31–34 were removed from the symbols. | B6 |
| `MICROSD_HRO_TF-01A` | J702 | Card detect "Cd" = 9; shell tabs as the LCSC footprint: 10 rear-left, 11 front-left, 12 front-right, 13 rear-right | B7 |
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
4. In Altium, run `build.py footprints NAME` for a new footprint, `build.py footprints --replace NAME ...` after a change (deletes the old copies first), or `build.py footprints --fresh` to rebuild the whole library (close it first). Then update the board's parts from the library.


**Layout notes from the footprint check (2026-10-21):** keep vias and copper out from between the pads of the PMIC inductors L200–L202 (Murata DFE252012F: no copper under the coil). Route no tracks between the pads of the 32.768 kHz crystal Y600 (Epson FC-135). Check D101–D103, D902 and LED1600–LED1603 in JLCPCB's placement preview: pad 1 is the anode, matching the symbols, not IPC's cathode-on-pin-1.

## 11. PCB setup

`python hardware/gen/build.py pcb` sets up `hardware/PCB.PcbDoc` with the project open in Altium. It runs the steps below in order; name some to run only those (`build.py pcb rules report`). All values are in `pcbsetup.py`, from `docs/research/bom/jlcpcb-stackup-and-cost.md` (sections 2.2, 3.1, 4, 5), the Octavo layout notes in `docs/research/osd62x-pm-sip.md` section 1.10 and the sources in [High-speed constraints](#high-speed-constraints). Now that the board is placed, name the steps you need rather than running a bare `build.py pcb`: its `outline` step replaces the R3 outline below.

| Step | What it does |
|---|---|
| `eco-options` | Stops Design » Import Changes from deleting the PCB-only objects below. It turns off the change orders Remove Net Classes, Remove Net Class Members, Remove Differential Pairs, Remove Differential Pair Classes and their members, and Remove Rooms. It closes the project, edits `[Modification Levels]` in the `.PrjPcb`, and opens the project again. It does nothing if they are already off. |
| `outline` | 110 × 80 mm rectangle with square corners, lower-left corner at (1000, 1000) mil. The board origin is that corner. `python placement.py board` redraws it with the Pi's R3 corners and adds the module and card notes on Mechanical 13; run that afterwards. |
| `stack` | JLC08161H-3313, see the table below. |
| `impedance` | Profiles SE50, DIFF90 and DIFF100 with JLCPCB's widths and gaps per layer, locked, ±10 %. It is always followed by `rules`, because the rules refer to the profiles by id. |
| `import` | Design » Import Changes. It presses Validate, Execute and Close in the ECO dialog and saves `out/eco_validate.png` and `out/eco_execute.png`. When nothing has changed, Altium says "Differences detected but no ECO generated" (the PCB-only objects); the step accepts that. |
| `classes` | Net classes, differential pairs, differential-pair classes and xSignal classes, see below. |
| `rules` | The `U1_SiP` room and the design rules, see below. The length rules name xSignals, so these must exist first. |
| `report` | Writes `out/pcb_report.txt` and checks every component, footprint and pad net against the generator. |
| `clear` | Not in the default run. Deletes every component, so `build.py pcb clear import classes report` brings in changed footprints (the ECO compares footprint names only). Use it before placement only. |

Three more commands live in `pcbsetup.py` itself, with Altium open:

| Command | What it does |
|---|---|
| `python pcbsetup.py xsignals` | Creates the 62 xSignals that are not in the file yet (Altium's Pin Pairs, from U1's pin to the load's pin, through the series part). Run it after `import` and before `classes` and `rules`. |
| `python pcbsetup.py verify` | Reads `Board6`, `Rules6`, `Classes6` and `SignalClasses` from the saved file and compares the stack, per-layer profiles, classes, pairs, xSignals, rule values, scopes and priorities with `pcbsetup.py`. Needs no Altium. |
| `python pcbsetup.py drc` | Batch DRC. The process opens its dialog whatever the parameters say, so this raises "Stop when N violations found" (500 by default) and presses Run. The report goes to `Project Outputs for APE - Single Board Computer/`. Component Clearance is off for batch by default, so a report with no row for that rule hasn't tested it. Tick it under Rule Types to Check » Placement, click another row to commit it, and press OK. Afterwards it runs `PcbClearMarkers`: markers left on the board draw two ticks across every unrouted connection. This has to be a separate run, because inside `PcbDrc` the reset fires before the DRC has written its markers. |

**Layer stack** (TOP / GND / SIG / PWR / PWR / SIG / GND / BOT; section 8 of the stackup doc. Calculator's model: Dk 4.3 for 3313 and the cores, 4.2 for 2116, outer copper 1.6 mil plated):

| Layer | Thickness | Dk | Note |
|---|---|---|---|
| Top Solder | 1.0 mil | 3.8 | |
| L1_TOP | 1.6 mil (1 oz) | | Components, microstrip referenced to L2 |
| PP 3313 L1-L2 | 3.9134 mil (0.0994 mm) | 4.3 | Prepreg |
| L2_GND | 0.6 mil (0.5 oz) | | |
| Core L2-L3 | 3.937 mil (0.10 mm) | 4.3 | |
| L3_SIG | 0.6 mil | | Stripline, L2 GND at 3.94 mil, L4 at 14.64 mil |
| PP 2116 x3 L3-L4 | 14.047 mil (0.3568 mm) | 4.2 | Prepreg |
| L4_PWR | 0.6 mil | | |
| Core L4-L5 | 11.811 mil (0.30 mm) | 4.3 | |
| L5_PWR | 0.6 mil | | |
| PP 2116 x3 L5-L6 | 14.047 mil | 4.2 | Prepreg |
| L6_SIG | 0.6 mil | | Stripline, L7 GND at 3.94 mil, L5 at 14.64 mil |
| Core L6-L7 | 3.937 mil | 4.3 | |
| L7_GND | 0.6 mil | | |
| PP 3313 L7-L8 | 3.9134 mil | 4.3 | Prepreg |
| L8_BOT | 1.6 mil | | Components, microstrip referenced to L7 |
| Bottom Solder | 1.0 mil | 3.8 | |

All eight copper layers are signal layers in Altium, so L2, L4, L5 and L7 take positive pours. The stack adds up to 1.57 mm.

**Impedance profiles** (drawn width / gap in mil; L1 and L8 are the same, L3 and L6 are the same): SE50 5.94, 4.83; DIFF90 5.34/6, 4.65/6; DIFF100 4.69/8, 4.01/8. Altium computes its own impedance for these when the Layer Stack Manager's Impedance tab is opened; that has not been compared with JLCPCB's numbers yet.

**Classes:**
- Net classes: `PWR` (all rails), split into `PWR_IN`, `PWR_CORE`, `PWR_DDR`, `PWR_1V8`, `PWR_3V3`, `PWR_OTHER`; `PWR_HI` (the 1 A rails and the switch nodes); `SE50` (RGMII, eMMC, SD, SDIO, DPI, reference clocks); one `HS_` class per interface, listed under [High-speed constraints](#high-speed-constraints).
- xSignal classes: `RGMII_TX`, `RGMII_RX`, `MMC0`, `MMC1`, `MMC2`, `DPI`. Matching has to span the series resistors, so it is on xSignals, not nets.
- Differential-pair classes: `USB0` (USB0, USBC1), `USB1` (USB1, HUB_P1, HUB_P2, USBA1, USBA2), `USB_DBG` (DBG_USB), `ETH_MDI` (MDI0–3), `HDMI_TMDS` (TX0–2, TXC), `CSI` (CLK, D0, D1). 19 pairs in all.

**Rules**, highest priority first within each kind:

| Kind | Rules |
|---|---|
| Clearance | `Clr_InnerPour_SiPVia` pours on L2/L4/L5/L7 to SiP vias 0.15 mm; `Clr_InnerPour_Hole` the same pours to other vias and pads 0.20 mm; `Clr_SiP` 0.09 mm in the room; `Clr_HS_Escape` 0.10 mm track to track in the `U1_Escape` room (the SiP room plus 3 mm); `Clr_HDMI_Escape` 0.10 mm from HDMI tracks in the `HDMI_Escape` room (U1000's TMDS pins to J1000's); `Clr_ETH_Escape` 0.10 mm from MDI tracks in the `U800_Escape` room (U800 plus 2 mm); `Clr_USBDBG_Escape` 0.10 mm from DBG_USB tracks in the `J1500_Escape` room; `Clr_USB1_Escape` 0.10 mm from USB1-class tracks in the `U900_Escape` room (U900 plus 2 mm); each of these four also has an `_Other` rule for when the other track is the one wholly inside; `Clr_HS_DP_Periodic` 50 mil and 19 `Clr_HS_<pair>` 30 mil, tracks only, GND tracks exempt; `Clr_SMD_SMD` 0.15 mm; `Clr_Default` 0.10 mm |
| Width | `W_SiP` 0.09 / 0.09 / 0.15 mm in the room; `W_SE50` from profile SE50; `W_PWR_HI` 0.20 / 1.00 / 3.0; `W_PWR` 0.15 / 0.40 / 3.0; `W_Default` 0.10 / 0.15 / 3.0 |
| Differential pairs | `DP_90R_USB` (USB0, USB1, USB_DBG) from DIFF90; `DP_100R` (ETH_MDI, HDMI_TMDS, CSI) from DIFF100. Width and gap down to 0.09 mm for the SiP neck-down, 5 mm maximum uncoupled length. `DP_100R_TMDS`, ahead of `DP_100R`, pins HDMI width to the L1 value, 0.119 mm (4.69 mil), gap preferred 0.203 mm |
| Routing via | `Via_SiP` 0.15 / 0.25 mm in the room; `Via_PWR` (PWR and GND) 0.30 / 0.50 preferred; `Via_Default` 0.20 / 0.40 preferred, holes up to 0.50 mm for POFV |
| Holes | Hole size 0.15–6.3 mm; annular ring 0.05 mm on vias and 0.15 mm on pads; hole to hole 0.45 mm between pads, 0.20 mm otherwise |
| Masks | Solder mask 0 on U1 (1:1 on the NSMD lands), -0.30 mm on vias (`Mask_Via`: this tents them, because `IsTenting_Top` and `_Bottom` set by script do not stick on AD26), 0.05 mm elsewhere; paste −2.5 mm on the windowed exposed pads (the query `build.py footprints` prints) and on `TC2070-NL`, 0 elsewhere; mask sliver 0.10 mm; silk to mask 0.15 mm |
| Board outline | 0.30 mm |
| Length, matched length, via count, routing layers | See [High-speed constraints](#high-speed-constraints) |

The template's polygon-connect rules (relief, four 10 mil spokes, 10 mil gap; vias direct) already match section 5 and are kept. The SiP region rules use `WithinRoom('U1_SiP')`: the room is the 9 × 14 mm body plus 1 mm, centred on U1 at `placement.U1_XY`.

**What `build.py pcb` verified on AD26:** 717 components with their footprints, 458 nets, every pad's net equal to the generator's; rule priorities as listed; the impedance-driven rules point at the current profiles. `pcbsetup.py verify` confirms the stack, profiles, classes and rules in the saved file.

### High-speed constraints

Delay limits become lengths with two figures from this stack. Tolerances and maximums use 6.88 ps/mm (L3 stripline, √4.25 / c, the slowest layer, so a limit in ps gives the shortest length). Minimums use 6.1 ps/mm (L1, Hammerstad with solder mask, an estimate), which gives the longest.

Sources: **SPRSP58C** is `datasheets/am625.pdf`. **SPRAAR7J** is TI's High-Speed Interface Layout Guidelines; its AM62x table is A-7 on p19. **SNLS504G** is the DP83867, **SLDS145D** the TFP410, **SLLSE96F** the TPD12S016.

"Manhattan" is the pad-to-pad length through any series part on the current placement. It is a lower bound: a maximum that fails it can't be met, and one that passes is only plausible. Altium's own estimates for the eMMC xSignals are the same figures plus about 1.5 mm, the board thickness, where the two ends are on opposite sides. Altium estimates xSignals only: rules on plain nets and pairs see routed copper alone, so they can't fire before routing, and a minimum on them fires at 0 mm.

| Interface | Constraint | Value | Rule | Source | Manhattan on this placement |
|---|---|---|---|---|---|
| RGMII | Impedance | 50 Ω | `W_SE50` | SNLS504G §9.2.2.1.2 p113 | |
| | Length | ≤ 50.8 mm (2 in) | `L_RGMII` | SNLS504G §9.2.2.1.2: under 2 in recommended, 6 in maximum | 20.2–25.3 mm |
| | Data skew | 60 mil (1.52 mm) | `M_RGMII_TXD`, `M_RGMII_RXD` | SNLS504G §9.2.2.1.2: under 11 ps | TXD spread 1.5, RXD 1.5 mm: inside the limit before any routing detour |
| | Skew with clock and control | 50 ps (7.27 mm) | `M_RGMII_TX`, `M_RGMII_RX` | SPRSP58C Table 6-35 p133 | Spread 5.0 and 3.0 mm |
| | Layers | L1, L3 | `RL_RGMII` | SPRAAR7J §2.4, see below | All pads on top |
| MMC0 (eMMC) | Delay | 126–756 ps | `L_MMC0` 10.66–40 mm | SPRSP58C Table 6-82 p181. Minimum: 126 ps ÷ 6.1, less 10 mm in the module. Maximum 40 mm: project target, `docs/research/bom/storage-usb-ethernet.md` | **10.4–15.0 mm. About 13 mm of meander in all, set by the mismatch limit below, not the minimum** |
| | Mismatch | 8 ps (1.16 mm) | `M_MMC0` | SPRSP58C Table 6-82: HS SDR, HS200 | Spread 4.6 mm; the meander above covers it |
| MMC1 (SD) | Delay | 126–1386 ps | `L_MMC1` 20.66–201 mm | SPRSP58C Table 6-101 p193 | 42.7–49.9 mm |
| | Mismatch | 8 ps (1.16 mm) | `M_MMC1` | SPRSP58C Table 6-101: HS, SDR104. 20 ps for DDR50, 100 ps otherwise | Spread 7.2 mm. About 17 mm of meander in all, up to 6.0 mm on `SD_D2` |
| MMC2 (SDIO) | Delay | ≤ 1386 ps | `L_MMC2` ≤ 201 mm | SPRSP58C Table 6-101. Minimum is open: the card's own route is unknown | 33.8–35.8 mm |
| | Mismatch | 8 ps (1.16 mm) | `M_MMC2` | SPRSP58C Table 6-101 | Spread 2.0 mm. About 1 mm of meander in all |
| DPI | Length | ≤ 71.1 mm (2.8 in) | `L_DPI` | SLDS145D §7.2.2.1 p26 | 13.0–24.0 mm |
| | Mismatch | 100 ps (14.5 mm) | `M_DPI` | SPRSP58C Table 6-44 p139 | Spread 10.9 mm: 3.6 mm spare |
| McASP | Delay | 100–1100 ps | `L_MCASP` 16.4–160 mm | SPRSP58C Table 6-73 p169 | 52.1–54.1 mm |
| | Mismatch | 100 ps (14.5 mm) | `M_MCASP` | SPRSP58C Table 6-73 | Spread 2.0 mm |
| SE50 (all) | Impedance | 50 Ω | `W_SE50` | Project stack table, `docs/research/bom/jlcpcb-stackup-and-cost.md` line 146. Only RGMII has a part-maker figure | |
| USB 2.0 | Impedance | 81–99 Ω, built as 90 Ω | `DP_90R_USB` | SPRAAR7J Table A-7 | |
| | Length | ≤ 304.8 mm (12000 mil) | `L_USB` | SPRAAR7J Table A-7 | U1 to J100 44 mm, U1 to U900 22 mm |
| | Within-pair skew | 50 mil; 25 mil per segment where a choke splits the pair | `M_USB_DBG_Pair`; `M_USB0_Pair`, `M_USB1_Pair` | SPRAAR7J Table A-7, halved for two segments | |
| | Vias | ≤ 4 per trace; 2 per segment where split | `V_USB_DBG`; `V_USB_Split` | SPRAAR7J Table A-7, halved | Each segment needs 1 or 2 |
| | Stubs, test points | 0 | No DRC rule exists | SPRAAR7J Table A-7 | No test points. **No stub: the DNP choke bypass on `L900` went with the 0R links on 2026-11-10** |
| CSI | Impedance | 85–115 Ω, built as 100 Ω | `DP_100R` | SPRAAR7J Table A-7 | |
| | Length | ≤ 254 mm (10 in) | `L_CSI` | SPRAAR7J Table A-7 | 39.2–44.7 mm |
| | Pair skew | 8 ps (1.16 mm) | `M_CSI_Pair` | SPRAAR7J: general estimate of UI ÷ 50, at 400 ps UI | |
| | Lane skew | 40 ps (5.8 mm) | `M_CSI_Lanes` | SPRAAR7J Table A-7 | Spread 5.5 mm: 0.3 mm spare before any routing detour |
| | Vias | ≤ 2 | `V_CSI` | SPRAAR7J Table A-7 | **At the limit:** one to leave ball row 3, one to come back to L1. `CSI_CLK` must also cross D0 and D1 (ball order D1, D0, CLK), which L1 and L3 allow |
| Ethernet MDI | Impedance | 100 Ω | `DP_100R` | SNLS504G §9.2.2.2.1 | |
| | Vias | ≤ 1 | `V_MDI` | Derived: SNLS504G asks for one layer, and J800's pin order forces one crossing. J800's through-hole pads take the second layer change | |
| HDMI TMDS | Impedance | 90–110 Ω, built as 100 Ω | `DP_100R_TMDS`: width fixed at 0.119 mm | SPRAAR7J Table A-2. That table is AM57xx; it is the closest HDMI figure | `DP_100R`'s 0.09–0.13 mm range let pairs come out at 0.09 mm (about 113 Ω) or 0.13 mm (about 96 Ω), depending on the router's width mode. TMDS is L1 only and needs no neck-down, so it has no range |
| | Length | ≤ 50.8 mm (2 in) | `L_TMDS` | SLDS145D §7.4.1.2 p29 | About 19 mm via U1001 |
| | Pair skew | 5 mil | `M_TMDS_Pair` | SPRAAR7J Table A-2 (AM57xx) | |
| | Vias, layers | 0 vias, L1 only | `V_TMDS`, `RL_TMDS` | SLLSE96F §10.1 p21 and Figure 20 p22; SLDS145D §7.4.1.2; SPRAAR7J Table A-2 | Pair order is the same at U1000, U1001 and J1000, as in Figure 20. Pairs run under U1001's body and reach its pads from inside |
| Pairs | Pair to clock or periodic signal | ≥ 50 mil | `Clr_HS_DP_Periodic` | SPRAAR7J Table A-7 | Can't be judged before routing |
| | Pair to any other signal or power track (GND tracks exempt) | ≥ 30 mil | 19 `Clr_HS_<pair>` | SPRAAR7J Table A-7 and §3.4 | **Not achievable at the pins**, see below |
| | Uncoupled length | ≤ 5 mm | `DP_90R_USB`, `DP_100R` | No source found: value from the earlier setup, kept | |

**Layer rules.** L2, L4, L5 and L7 carry no impedance-controlled route. L1, L3, L6 and L8 each sit 0.10 mm from GND, so SPRAAR7J §2.4 ("does not recommend high-speed signal references to power planes") no longer limits any of them: `RL_RGMII`, `RL_MDI_CSI` and `RL_SE50_USB` allow all four, and only TMDS is held to L1 (`RL_TMDS`). A signal on L3 or L6 still has a power pour 14.64 mil away on its other side. Stitch GND vias where a route changes reference between L2 and L7 (§2.4); DRC can't check that.

**The 30 mil rule at the pins.** TI scopes it "after package escape and before connector termination", and the rule covers tracks only, but pin spacing alone breaks it near some parts. Neighbouring pairs' tracks can be at most 0.38 mm apart at `J1000`, 0.53 mm at `U1001` and 0.63 mm at `U900`, against 0.76 mm required. It will also flag tracks on pins next to a pair at any fine-pitch part (`U800`, `U1000`, `U1500`). Treat hits within about 1 mm of those pins as waivers. Inside the `U1_SiP` room `Clr_SiP` applies instead, at `U1001` and `J1000` `Clr_HDMI_Escape` does, at `U800` `Clr_ETH_Escape`, at `J1500` `Clr_USBDBG_Escape`, and at `U900` `Clr_USB1_Escape` (below).

**Escape from the SiP.** Pairs side by side need 1.20 mm centre to centre to keep 30 mil, against 0.50 mm at the balls, which takes about 2 mm of run at 45 degrees. So `Clr_HS_Escape` (0.10 mm, `U1_Escape`, 3 mm past the SiP room) sits ahead of the 30 mil rules. TI gives no figure for where escape ends: the 3 mm is ours, `ESCAPE_MM` in `pcbsetup.py`. Altium's `WithinRoom` means wholly inside, so a track crossing the room's edge counts as outside unless the track it is measured against is wholly inside. End a fan-out segment before the edge if two pairs leave close together.

**HDMI escape and termination.** The 30 mil rule stopped every HDMI pair after the first: U1001's pads are 0.65 mm apart and J1000's pins 0.5 mm, with no GND between neighbouring pairs, so the second pair can't reach its pads. TI lifts the 30 mil for package escape and connector termination (SPRAAR7J §3.4) and lets break-out run 0.25 in from the package (§3.3). Here that covers the whole run: U1000's break-out reaches under U1001, which is the connector's ESD part, 6 mm from J1000. So `Clr_HDMI_Escape` gives HDMI tracks wholly inside the `HDMI_Escape` room 0.10 mm to any track. The room is board mm (81.9, 32.9) to (101.5, 46.75), `HDMI_ROOM_MM` in `pcbsetup.py`, drawn round U1000, U1001 and J1000 as placed by hand on 2026-11-09: move it with them. Keep the pairs apart where there is room; §3.3 asks for the deviations to be as short as possible.

**MDI escape at the PHY.** On U800 every MDI pin sits 0.5 mm from a power or bias pin with a track on it: VDDA_2V5 on pins 3 and 9, VDD_1V0 on 6, RBIAS on 12. The 30 mil rule stopped each pair about 0.5 mm short of its pins. Pair to pair is 1.0 mm there, which meets 30 mil. So `Clr_ETH_Escape` gives MDI tracks wholly inside the `U800_Escape` room 0.10 mm to any track. The room is U800's body plus 2 mm on every side, board mm (63.7, 19.8) to (74.7, 30.8), `ETH_ROOM_MM` in `pcbsetup.py`: move it with U800. End each pair's first segment inside the room, about 1.8 mm past the pins.

**Debug USB-C termination.** On J1500, CC1 (A5) sits 0.5 mm from DBG_USB_DM (B7), and DM's track runs straight out, so no CC1 track could leave its pin. `Clr_USBDBG_Escape` gives DBG_USB tracks 0.10 mm in the `J1500_Escape` room: J1500's pins plus 2 mm, up to R1500 (CC1's Rd), board mm (-2.0, 54.5) to (9.5, 67.5), `USBDBG_ROOM_MM` in `pcbsetup.py`. Move it with J1500.

**USB hub escape.** U900's pins are 0.4 mm apart. USB1_DM (pin 20) sits 0.4 mm from the VCC_3V3_SYS track joining pins 18 and 19, and the downstream pairs HUB_P1 and HUB_P2 are 0.63 mm apart at the corner (pins 7, 8). `Clr_USB1_Escape` gives USB1-class tracks 0.10 mm in the `U900_Escape` room: U900 plus 2 mm, board mm (41.5, 16.0) to (49.5, 24.0), `HUB_ROOM_MM` in `pcbsetup.py`. Move it with U900.

**Either track inside.** Each part room has two rules: `Clr_<x>_Escape` applies when the pair's track is wholly inside the room, `Clr_<x>_Escape_Other` when the other track is. A pair segment that runs out of the room, like DBG_USB's from J1500 to U1500, would otherwise still hold a short track at the next pin to 30 mil.

**Mixed layers.** L1 and L3 differ by about 0.78 ps/mm, so a bus can use up its 8 ps across only 10 mm of layer difference. Route each MMC bus with the same mix of layers on every net.

**Open, with no sourced limit, so no rule:** MDI within-pair and pair-to-pair skew (SNLS504G gives none); TMDS pair-to-pair skew; via limits for RGMII, DPI and MMC; spacing between single-ended nets (SLDS145D's 5 × height is a guideline, and as a rule it would flag every pin fan-in); MMC2's minimum length. JTAG (SPRSP58C Table 6-52) and MDIO (Table 6-28) have limits that this board can't approach, so they have no rule.

**High-speed nets by interface** (`SE50` also holds every single-ended net below except McASP and the crystals):

| Interface | Class | Nets |
|---|---|---|
| RGMII TX | `HS_RGMII_TX` | `ETH_TD0`–`3`, `ETH_TXC`, `ETH_TX_CTL`, `PHY_TX_D0`–`3`, `PHY_GTX_CLK`, `PHY_TX_CTRL` |
| RGMII RX | `HS_RGMII_RX` | `ETH_RD0`–`3`, `ETH_RXC`, `ETH_RX_CTL`, `PHY_RX_D0`–`3`, `PHY_RX_CLK`, `PHY_RX_CTRL` |
| eMMC | `HS_MMC0` | `EMMC_CLK`, `EMMC_MOD_CLK`, `EMMC_CMD`, `EMMC_D0`–`7`; `EMMC_MOD_DS` is in `SE50` only |
| SD | `HS_MMC1` | `SD_CLK`, `SD_SOCK_CLK`, `SD_CMD`, `SD_D0`–`3` |
| SDIO | `HS_MMC2` | `WL_SDIO_CLK`, `WL_SDIO_CMD`, `WL_SDIO_D0`–`3` (one net each since the 0R series links were dropped) |
| DPI | `HS_DPI` | `DPI_D0`–`23`, `DPI_DE`, `DPI_HSYNC`, `DPI_VSYNC`, `DPI_PCLK`, `TFP_IDCK` |
| McASP | `HS_MCASP` | `AUD_BCLK`, `AUD_FSYNC`, `AUD_DIN`, `AUD_DOUT` |
| Clocks and crystals | `HS_CLK` | `OSC_25M`, `OSC25M_SRC`, `AUD_MCLK`, `AUD_MCLK_OSC`, `AUD_BCLK`, `ETH_TXC`, `PHY_GTX_CLK`, `ETH_RXC`, `PHY_RX_CLK`, `EMMC_CLK`, `EMMC_MOD_CLK`, `SD_CLK`, `WL_SDIO_CLK`, `DPI_PCLK`, `TFP_IDCK`, `PHY_XI`, `PHY_XO`, `HUB_XI`, `HUB_XO`, `FT_OSCI`, `FT_OSCO`, `LFOSC_XI`, `LFOSC_XO` |
| USB | `USB0`, `USB1`, `USB_DBG` (pair classes) | `USB0`, `USBC1`; `USB1`, `HUB_P1`, `HUB_P2`, `USBA1`, `USBA2`; `DBG_USB` |
| Ethernet MDI | `ETH_MDI` (pair class) | `ETH_MDI0`–`3` |
| HDMI | `HDMI_TMDS` (pair class) | `HDMI_TX0`–`2`, `HDMI_TXC` |
| Camera | `CSI` (pair class) | `CSI_CLK`, `CSI_D0`, `CSI_D1` |

**Notes from the AD26 run:**
- Altium gives every new rule priority 1, so `PcbRules` adds the rules last to first.
- The descriptors of some rules show stale values. The board-outline rule says `Gap=0mil` while `GetClearance` returns 0.30 mm, and the width and differential-pair rules show the template's widths while the per-layer values come from the profiles. `pcb report` lists the descriptors as Altium prints them.
- AD26 has no `IsSMDPad` query keyword; an unknown keyword stops the script with an "Undeclared identifier" dialog. Use `IsSMTPin`.
- `[Modification Levels]` in the `.PrjPcb` holds Type1–Type161 for Altium's `eModification_*` values 0–160, so value N is TypeN+1.
- The ECO dialog's buttons ignore `BM_CLICK` while the dialog is not the active window. `build.py` sends the button's `BN_CLICKED` to its parent instead.
- The MCP's `get_pcb_layer_stackup` omits the cores and prints wrong µm values (mil ÷ 254). Use the Layer Stack Manager or `pcb report`.
- Impedance profiles and the routing-layers rule are indexed by the old layer numbers (1, 2, 3, 4, 5, 32). A new-style id from `COPPER` is ignored without an error: every profile had one entry on no layer until the file was read back. `pcb report` still prints the first entry only (`0=59400/0/0`), so use `verify`.
- Nothing in `IPCB_PinPairsManager` that was tried creates a pin pair. Select the two pads and run `PCB:ManagePinPairs` with `Action=CreatePinPair`. Names are `<net>-<net>_PP1`, or `<net>_PP1` where both ends share a net.
- Rule query keywords that exist on AD26: `InxSignal`, `InxSignalClass`, `InDifferentialPair`, `InDifferentialPairClass`, `IsTrack`.

**Not done yet (layout):** routing, fiducials (3 global, 2 local at U1; they are not in the schematic), the pours on L2, L4, L5 and L7, via templates with tenting and removal of unused `VIA_BGA` pads on the inner layers, and the footprint-related layout items listed in section 10. Fan-outs are on the board (`fanout.py`). `powerplanes.py` holds the pour planner for L4 and L5; it has to be re-run on the current placement.

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
| `pcbsetup.py` | PCB setup as data: outline, layer stack, impedance profiles, net and differential-pair classes, SiP room, design rules, ECO options |
| `blocks/*.txt`, `blocks.py` | Every part's position, by hand, one file per schematic function; `blocks.py` checks them and writes `placement.csv` |
| `placement.py`, `placement_check.py` | Part geometry, offline checks, renders, and applying `placement.csv` to the PcbDoc; Altium's `check_placement` in batches |
| `floorplan.py`, `floorplan_draw.py` | The floorplan behind `docs/pcb-floorplan.md`, its numbers and image, and the distance, ratsnest and demand measures used to judge a placement |
| `fanout.py` | Fan-outs for the placed board: SiP escape stubs and dog-bones, and vias for every SMD power and GND pad. Written to Altium by `ApePlace>PlacePower`. No autorouter |
| `powerplanes.py` | Planner for the L4 and L5 pours, and the power fan-out `fanout.py` uses |
| `altium/SheetTemplate.SchDoc` | Empty sheet that every build starts from |
| `altium/ApeScripts.PrjScr`, `altium/ApeScripts.pas` | Altium script project run by `build.py`. Procedures: `Ping`, `SaveDocs`, `CloseDocs`, `NewLib`, `DropDefaultFootprint`, `AddToProject`, `CloseApeProject`, `OpenApeProject`, `BuildSheet`, and for the PCB `PcbOutline`, `PcbStack`, `PcbImpedance`, `PcbImport`, `PcbClear`, `PcbClasses`, `PcbRules`, `PcbReport`, `PcbDrc`, `PcbClearMarkers`. Input and output files are in `C:\Users\Public\altium_mcp\` (`ape_*.txt`, `ape_log.txt`, `ape_result.json`). |
| `altium/ApeFootprints.PrjScr`, `altium/ApeFootprints.pas` | Script project run by `build.py footprints` (through `footprints.run_fp`): `RemoveFootprints` (for `--replace`) and `PadMasks`, which sets each pad's paste and solder mask expansion from the `PADMASK` records of the footprint spec. Not yet run in Altium. |
