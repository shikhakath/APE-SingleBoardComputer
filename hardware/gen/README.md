# Schematic generator: handoff guide

This folder builds the APE-SBC Altium schematic from Python. Symbols and sheets are defined as code (`symbols.py`, `sheets/*.py`). `build.py` drives a running Altium Designer through the [altium-mcp](https://github.com/coffeenmusic/altium-mcp) server to create the symbol library and the sheets.

**Status: written without Altium access.** Everything below `build.py check` has not run against a live Altium yet. Do the smoke test (step 5) before trusting any generated sheet, and report what breaks.

## How the work is split

| Who | Does what |
|---|---|
| Design side (Jay + Claude, no Altium needed) | Writes and edits symbols and sheets in Python, runs `build.py check`, pushes |
| Altium side (needs a license) | Pulls, runs `build.py lib` / `build.py sheets`, compiles and checks ERC in Altium, commits the generated `.SchDoc` / `.SchLib` files, pushes |

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

This writes `hardware/gen/out/`: `netlist.csv`, `schematic_bom.csv`, one `*.spec.txt` per sheet, and `symbols_spec.txt`. It lists single-node nets, which are expected for nets whose other end is on a sheet not written yet.

## 5. Build in Altium

Run these in order the first time.

| Step | Command | Then check in Altium |
|---|---|---|
| a. Register files | Close the project in Altium, run `python hardware/gen/build.py project`, reopen the project | The new sheets and `lib\APE-SBC.SchLib` appear in the Projects panel |
| b. Library | `python hardware/gen/build.py lib` | Open `APE-SBC.SchLib`. Check `TPS65219_RHB`: pins on the left and right edges pointing **outward**, names inside the body. Check `RES` and `CAP`: pins horizontal, ends at ±200 mil. |
| c. Smoke test | `python hardware/gen/build.py smoke` | The command prints `pin map matches the generator`. Open `hardware/gen/out/smoke.SchDoc`: every wire stub touches its pin, net labels sit on wires, GND symbols hang below. |
| d. Sheets | `python hardware/gen/build.py sheets`, or for one sheet `python hardware/gen/build.py sheet 02_PMIC` | Each sheet prints `pin map matches`. Then **Project » Validate PCB Project** and review the Messages panel. |
| e. Commit | `git add hardware && git commit && git push` | Altium binary files are committed as-is; `gen/out/` is ignored |

`lib` and `sheets` also save the documents. The MCP tools themselves never save, so if a run stops halfway, save manually (File » Save All).

## 6. Using Claude Code instead of typing commands

Open the repository folder in Claude Code and approve the `altium` MCP server when asked. Then prompt:

> Read hardware/gen/README.md and DESIGN_PROPOSAL.md. Run the build steps in section 5 in order, stop at the first failure, diagnose it, fix the generator, and continue.

## 7. Rules for editing

- **Rebuilding a sheet erases it.** The builder clears every component, wire, net label, power port, junction and No-ERC marker on the target sheet, plus notes that start with `* `. Once you hand-edit a sheet in Altium, remove it from `SHEETS` in `build.py` and edit it only in Altium from then on.
- Connectivity is **by net name**. Every pin gets a short stub with a net label or a power/ground port. The project uses *Automatic* net scope and has no ports or sheet entries, so Altium treats net labels as global. Do not add ports or sheet entries unless you switch the whole project to hierarchical.
- Net-name conventions:
  - Power rails are `<RAIL>_<VOLTAGE>`, for example `VCC_3V3_SYS`, `VDDS_DDR_1V2`, `DDR4_VPP_2V5`.
  - Active-low signals end in `_N`.
  - Nets that go only to a test point start with `TP_`.
  - **`VPP_EFUSE_1V8` is the AM62x eFuse pin and `DDR4_VPP_2V5` is the DDR4 VPP.** Never merge them.
- Designators are numbered by sheet: sheet 02 uses `x2xx` (U200, C200, ...).

## 8. What has not been verified (check during the smoke test)

| Assumption | Where | If wrong |
|---|---|---|
| A pin's `x,y` in the symbol spec is its **body-end** location and the electrical end is `PinLength` further along its orientation; `eRotate0/90/180/270` = right/up/left/down | `schgen.py` (`DIR`, `ORIENT_NAME`) | The smoke test reports a pin-map mismatch. Fix the mapping in `schgen.py` and rebuild. |
| `ISch_NetLabel.Justification`, `ISch_Document.SheetStyle`, `eNoERC` and `ISch_Component.CurrentPartID` can be set from a script | `altium/ape_sheet_builder.pas` | The tool output names the last statement that ran. Comment out that feature (labels default to bottom-left; set the sheet size by hand). |
| `IServerDocument.DoFileSave('')` saves in native format | `altium/ape_save_docs.pas`, builder | Save manually; report the error |
| `create_symbols_batch` creates `APE-SBC.SchLib` when the file does not exist | `build.py lib` | Create an empty SchLib at `hardware/lib/APE-SBC.SchLib` in Altium, save it, rerun `lib` |
| Re-running `lib` on an existing library updates symbols rather than duplicating them | `build.py lib` | Delete `APE-SBC.SchLib` and rerun |

## 9. Troubleshooting

- **`No response received from Altium (timeout)`.** Altium is not running, is still starting, has a dialog open, or has no license. Fix that and rerun.
- **Script executor wedged** (calls return instantly and do nothing). Run `python "%USERPROFILE%\mcp-servers\altium-mcp\dev\unwedge.py"`, or press Ctrl+F3 in Altium, or restart Altium.
- **`Select Item To Run` dialog.** Altium cannot find the script project. Rerun `start_server.py --build` and check `get_server_status`.
- **Symbol `MISSING` in the builder result.** Run `build.py lib` first. Also check that the `LIBRARY` path in `out/symbols_spec.txt` is the same file the sheet references.

## Files

| File | Purpose |
|---|---|
| `schgen.py` | Generator core: symbol layout, sheet placement, stubs and labels, pin-map check |
| `symbols.py` | Every symbol, each IC with its datasheet pin-table reference |
| `sheets/sNN_*.py` | One module per sheet; `build(sch_dir)` returns a `Sheet` |
| `build.py` | Command-line driver |
| `mcp_client.py` | Minimal stdio client for the Altium MCP server (no Claude needed) |
| `altium/ape_sheet_builder.pas` | DelphiScript run through the MCP `run_altium_script` sandbox: builds one sheet from `C:\Users\Public\altium_mcp\ape_sheet_spec.txt` and saves it |
| `altium/ape_save_docs.pas` | Saves the documents listed in `C:\Users\Public\altium_mcp\ape_save_list.txt` |
