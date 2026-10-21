"""APE SBC schematic build driver.

Run from anywhere (paths are resolved from this file's location):

  python build.py check             offline checks + netlist/BOM reports in gen/out/ (no Altium)
  python build.py project           register sheets + library in the .PrjPcb
                                    (close the project in Altium first)
  python build.py register          same, through Altium, while the project is open
  python build.py smoke             build gen/out/smoke.SchDoc: proves the toolchain end to end
  python build.py lib               create the symbols in lib/APE-SBC.SchLib and save it
  python build.py footprints [--fresh] [NAME ...]
                                    create the footprints in lib/APE-SBC.PcbLib and save it
                                    (--fresh: delete and regenerate the whole library;
                                    NAME: add only these footprints to an existing one)
  python build.py sheet 02_PMIC     build one or more sheets by name
  python build.py sheets            build every sheet

Altium must be running with a valid license. The Altium MCP server must be
installed at %USERPROFILE%\\mcp-servers\\altium-mcp (see gen/README.md).
"""
from __future__ import annotations

import csv
import importlib
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

GEN = Path(__file__).resolve().parent
HW = GEN.parent
sys.path.insert(0, str(GEN))

import footprints  # noqa: E402
import schgen  # noqa: E402
import symbols  # noqa: E402

LIB_PATH = HW / "lib" / "APE-SBC.SchLib"
PCBLIB_PATH = HW / "lib" / "APE-SBC.PcbLib"
SCH_DIR = HW / "sch"
TEMPLATE_SHEET = HW / "Main.SchDoc"
PRJ_PATH = HW / "APE - Single Board Computer.PrjPcb"
OUT = GEN / "out"
BRIDGE = Path("C:/Users/Public/altium_mcp")

# Sheet modules are gen/sheets/sNN_*.py, built in NN order; each defines
# build(sch_dir) -> Sheet. List a module stem here to stop regenerating a sheet
# that has been hand-edited in Altium (see README section 7).
FROZEN_SHEETS: set[str] = set()


def sheet_modules():
    return sorted(p.stem for p in (GEN / "sheets").glob("s[0-9][0-9]_*.py"))


def load_sheets(include_frozen=True):
    sheets = []
    for name in sheet_modules():
        if name in FROZEN_SHEETS and not include_frozen:
            continue
        sh = importlib.import_module(f"sheets.{name}").build(str(SCH_DIR))
        assign_footprints(sh)
        sheets.append(sh)
    return sheets


def assign_footprints(sh):
    """Give every placed part its footprint name (footprints.resolve)."""
    for pl in sh.placed:
        pl.footprint = footprints.resolve(pl.symbol, pl.comment, pl.params, pl.footprint)


def all_symbols():
    """symbols.ALL plus SYMBOLS from every gen/symlib/*.py module."""
    syms = list(symbols.ALL)
    for p in sorted((GEN / "symlib").glob("*.py")):
        if p.stem != "__init__":
            syms += getattr(importlib.import_module(f"symlib.{p.stem}"), "SYMBOLS", [])
    seen = {}
    for s in syms:
        if s.name in seen and seen[s.name] is not s:
            raise ValueError(f"duplicate symbol name {s.name}")
        seen[s.name] = s
    return list(seen.values())


# ------------------------------------------------------------------ check

def cmd_check():
    OUT.mkdir(exist_ok=True)
    sheets = load_sheets()
    nets = defaultdict(list)
    owners = {}
    problems = []
    exported = {s.name for s in all_symbols()}
    for sh in sheets:
        for pl in sh.placed:
            if pl.symbol.name not in exported:
                problems.append(f"{sh.title}: {pl.designator} uses {pl.symbol.name}, "
                                "which is not in symbols.ALL or any symlib SYMBOLS list")
        for pl in sh.placed:
            key = (pl.designator, pl.part)
            if key in owners:
                problems.append(f"duplicate {pl.designator} part {pl.part} on {owners[key]} and {sh.title}")
            owners[key] = sh.title
        for net, nodes in sh.netlist().items():
            nets[net] += nodes
        problems += [f"{sh.title}: {p}" for p in sh.check_geometry()]
        problems += [f"{sh.title}: layout: {p}" for p in sh.check_layout()]
    for net, nodes in sorted(nets.items()):
        if len(nodes) == 1 and not net.startswith("TP_"):
            problems.append(f"single-node net {net}: {nodes[0]}")
    fp_problems, fp_used = footprints.check(all_symbols(), sheets)
    problems += fp_problems
    with open(OUT / "netlist.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["net", "node_count", "nodes"])
        for net, nodes in sorted(nets.items()):
            w.writerow([net, len(nodes), " ".join(sorted(nodes))])
    with open(OUT / "rails.txt", "w") as f:
        f.write("Power nets and what connects to them (review: every rail needs a source)\n\n")
        for net, nodes in sorted(nets.items()):
            if schgen.is_rail(net) or net == "GND":
                parts = sorted({n.split(".")[0] for n in nodes})
                ics = [p for p in parts if not p.startswith(("C", "TP"))]
                f.write(f"{net:24s} {len(nodes):4d} pins  parts (no caps): {' '.join(ics)}\n")
    with open(OUT / "schematic_bom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["designator", "part", "symbol", "comment", "sheet", "parameters"])
        for sh in sheets:
            for pl in sh.placed:
                w.writerow([pl.designator, pl.part, pl.symbol.name, pl.comment, sh.title,
                            "; ".join(f"{k}={v}" for k, v in pl.params.items())])
    for sh in sheets:
        (OUT / f"{Path(sh.path).stem}.spec.txt").write_text(sh.spec(str(LIB_PATH)))
    (OUT / "symbols_spec.txt").write_text(symbol_spec())
    fps = footprints.all_footprints()
    (OUT / "footprints_spec.txt").write_text(footprints.library_spec(fps, PCBLIB_PATH))
    with open(OUT / "footprint_usage.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["footprint", "pads", "parts", "designators", "assumed_numbering"])
        for fp in fps:
            used = fp_used.get(fp.name, [])
            w.writerow([fp.name, len(fp.pad_names()), len(used), " ".join(used), fp.assumed])
    unused = [fp.name for fp in fps if fp.name not in fp_used]
    print(f"{len(sheets)} sheets, {len(owners)} placed parts, {len(nets)} nets, {len(fps)} footprints")
    if unused:
        print("footprints not used by any placed part: " + " ".join(unused))
    print("\n".join(problems) if problems else "no problems found")
    print(f"reports in {OUT}")
    return not problems


def symbol_spec() -> str:
    lines = [f"LIBRARY|{LIB_PATH}"]
    for sym in all_symbols():
        lines += sym.spec_lines()
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- project

def cmd_project():
    """Add every sheet and the symbol library to the .PrjPcb (text edit)."""
    raw = PRJ_PATH.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig").replace("\r\n", "\n")
    present = {line.split("=", 1)[1].strip().lower()
               for line in text.splitlines() if line.startswith("DocumentPath=")}
    numbers = [int(l[9:-1]) for l in text.splitlines()
               if l.startswith("[Document") and l.endswith("]") and l[9:-1].isdigit()]
    n = max(numbers, default=0)
    wanted = [Path(sh.path) for sh in load_sheets()] + [LIB_PATH, PCBLIB_PATH]
    blocks = []
    for p in wanted:
        rel = str(p.relative_to(HW)).replace("/", "\\")
        if rel.lower() in present:
            continue
        n += 1
        blocks.append(
            f"[Document{n}]\nDocumentPath={rel}\nAnnotationEnabled=1\nAnnotateStartValue=1\n"
            "AnnotationIndexControlEnabled=0\nAnnotateSuffix=\nAnnotateScope=All\nAnnotateOrder=-1\n"
            "DoLibraryUpdate=1\nDoDatabaseUpdate=1\nClassGenCCAutoEnabled=1\nClassGenCCAutoRoomEnabled=0\n"
            "ClassGenNCAutoScope=None\nDItemRevisionGUID=\nGenerateClassCluster=0\nDocumentUniqueId=\n")
        print(f"  adding {rel}")
    if not blocks:
        print("project already lists every sheet and both libraries")
        return True
    # insert after the last [DocumentN] block
    marker = "\n[Configuration1]"
    idx = text.find(marker) if marker in text else len(text)
    text = text[:idx].rstrip("\n") + "\n\n" + "\n".join(blocks) + text[idx:]
    data = text.replace("\n", "\r\n").encode("utf-8")
    PRJ_PATH.write_bytes((b"\xef\xbb\xbf" if bom else b"") + data)
    print(f"updated {PRJ_PATH.name}")
    return True


# ------------------------------------------------------------- altium ops

def mcp(tool, args, timeout=900):
    import mcp_client
    raw = mcp_client.call(tool, args, timeout=timeout)
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw": raw}


SCRIPT_PRJ = GEN / "altium" / "ApeScripts.PrjScr"


def altium_exe() -> str:
    r"""X2.EXE from ALTIUM_EXE, else the newest C:\Program Files\Altium\AD*."""
    import os
    if os.environ.get("ALTIUM_EXE"):
        return os.environ["ALTIUM_EXE"]
    found = sorted(Path("C:/Program Files/Altium").glob("AD*/X2.EXE"))
    if not found:
        raise SystemExit("Altium not found - set ALTIUM_EXE to the full path of X2.EXE")
    return str(found[-1])


def altium_dialogs(close=False):
    """Visible dialog windows owned by X2.EXE (titles); optionally close them."""
    import ctypes
    import ctypes.wintypes as wt
    import subprocess
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq X2.EXE", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    pids = {int(l.split(",")[1].strip('"')) for l in out.splitlines() if l.startswith('"X2')}
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(h):
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(h, cls, 64)
            if cls.value in ("#32770", "TMessageForm", "TDrillMillImportDlg"):
                title = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(h, title, 256)
                found.append(title.value or cls.value)
                if close:
                    user32.PostMessageW(h, 0x0010, 0, 0)  # WM_CLOSE
        return True

    user32.EnumWindows(cb, 0)
    return found


def run_ape(proc, timeout=300):
    """Run ApeScripts>proc in the running Altium; returns (ok, result dict)."""
    import subprocess
    import time
    BRIDGE.mkdir(parents=True, exist_ok=True)
    log, res = BRIDGE / "ape_log.txt", BRIDGE / "ape_result.json"
    for f in (log, res):
        if f.exists():
            f.unlink()
    cmd = (f'"{altium_exe()}" -RScriptingSystem:RunScript(ProjectName="{SCRIPT_PRJ}"'
           f'^|ProcName="ApeScripts>{proc}")')
    subprocess.Popen(cmd, shell=True)
    start = time.time()
    while time.time() - start < timeout:
        if res.exists():
            time.sleep(0.3)
            text = res.read_text(encoding="cp1252", errors="replace").strip()
            try:
                data = json.loads(text)
            except ValueError:
                return False, {"error": "unreadable result", "raw": text}
            return bool(data.get("success")), data
        if not log.exists() and time.time() - start > 20:
            dialogs = altium_dialogs()
            if dialogs:
                return False, {"error": "script did not start (compile error or modal dialog)",
                               "dialogs": dialogs, "hint": "python build.py unwedge"}
        time.sleep(0.5)
    last = log.read_text(encoding="cp1252", errors="replace").splitlines()[-1:] if log.exists() else []
    if not log.exists() and not altium_dialogs():
        return False, {"error": f"ApeScripts>{proc} never started: Altium runs nothing (and says nothing) "
                                "for an unknown procedure name - check it exists in ApeScripts.pas"}
    return False, {"error": f"no result after {timeout} s", "last_log_line": last,
                   "dialogs": altium_dialogs(), "hint": "python build.py unwedge"}


def cmd_unwedge():
    """Stop a paused script (Altium's debugger) and close Altium dialogs."""
    import subprocess
    print("closing dialogs:", altium_dialogs(close=True))
    subprocess.Popen(f'"{altium_exe()}" -REditScript:Stop', shell=True)
    import time
    time.sleep(3)
    ok, res = run_ape("Ping", timeout=60)
    print("script executor", "alive" if ok else f"still blocked: {res}")
    return ok


def save_docs(entries):
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / "ape_save_list.txt").write_text("\n".join(f"{k}|{p}" for k, p in entries) + "\n",
                                              encoding="cp1252", errors="replace")
    ok, res = run_ape("SaveDocs", timeout=120)
    if not ok:
        print("  save failed:", json.dumps(res)[:600])
    return ok


def new_lib(path: Path, kind: str = "SCHLIB") -> bool:
    """Create an empty SCHLIB or PCBLIB at path and save it (ApeScripts>NewLib)."""
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / "ape_new_lib.txt").write_text(f"{path}\n{kind}\n", encoding="cp1252", errors="replace")
    ok, res = run_ape("NewLib", timeout=120)
    if not ok:
        print("  " + json.dumps(res)[:600])
    return ok and path.exists()


def symbol_batches(max_pins=250):
    """Split the library into batches: create_symbols_batch has a fixed 120 s
    bridge timeout, so a whole library (or one 500-pin SiP) must not go at once."""
    batch, pins = [], 0
    for sym in all_symbols():
        n = len(sym.pins)
        if batch and pins + n > max_pins:
            yield batch
            batch, pins = [], 0
        batch.append(sym)
        pins += n
    if batch:
        yield batch


def cmd_lib(names=None):
    """Create lib/APE-SBC.SchLib if needed, add the symbols in batches, save.
    `build.py lib NAME ...` limits the run to the named symbols."""
    import time
    LIB_PATH.parent.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    if not LIB_PATH.exists():
        print(f"creating empty {LIB_PATH.name}")
        if not new_lib(LIB_PATH, "SCHLIB"):
            print("could not create the library - create an empty SchLib at that path in Altium")
            return False
    ok = True
    for i, batch in enumerate(symbol_batches()):
        if names:
            batch = [s for s in batch if s.name in names]
            if not batch:
                continue
        spec = OUT / f"symbols_spec_{i:02d}.txt"
        lines = [f"LIBRARY|{LIB_PATH}"]
        for sym in batch:
            lines += sym.spec_lines()
        spec.write_text("\n".join(lines) + "\n", encoding="cp1252", errors="replace")
        t0 = time.time()
        res = mcp("create_symbols_batch", {"spec_file": str(spec)})
        took = time.time() - t0
        created = res.get("created", res.get("created_count", "?")) if isinstance(res, dict) else "?"
        failed = res.get("failed", []) if isinstance(res, dict) else []
        print(f"  batch {i:02d}: {len(batch)} symbols, {sum(len(s.pins) for s in batch)} pins, "
              f"{took:.0f} s, created={created} failed={failed}")
        if not res.get("success", True) or failed:
            print("  " + json.dumps(res)[:600])
            ok = False
            break
    return save_docs([("SchLib", str(LIB_PATH))]) and ok


def cmd_footprints(args):
    """Create the footprints in lib/APE-SBC.PcbLib (see README section 5)."""
    fresh = "--fresh" in args
    names = [a for a in args if not a.startswith("--")]
    fps = footprints.all_footprints()
    if names:
        unknown = sorted(set(names) - {fp.name for fp in fps})
        if unknown:
            print("no such footprint: " + " ".join(unknown))
            return False
        fps = [fp for fp in fps if fp.name in names]
    PCBLIB_PATH.parent.mkdir(exist_ok=True)
    if PCBLIB_PATH.exists() and fresh:
        # create_footprints_batch appends: a footprint that already exists
        # would be added a second time, so regenerate the whole file
        try:
            PCBLIB_PATH.unlink()
        except PermissionError:
            print(f"cannot delete {PCBLIB_PATH.name}: close it in Altium and rerun")
            return False
        print(f"deleted {PCBLIB_PATH.name} (it must be closed in Altium)")
    elif PCBLIB_PATH.exists() and not names:
        print(f"{PCBLIB_PATH.name} exists and create_footprints_batch adds footprints rather than "
              "replacing them. Close the library in Altium and rerun with --fresh, or name only "
              "the footprints that are new.")
        return False
    if not PCBLIB_PATH.exists():
        # create_footprints_batch only opens an existing library (FPLIB record),
        # and opening a missing path does NOT create one (verified on AD26)
        print(f"creating empty {PCBLIB_PATH.name}")
        if not new_lib(PCBLIB_PATH, "PCBLIB"):
            print("could not create the library - create an empty PcbLib at that path in Altium")
            return False
    OUT.mkdir(exist_ok=True)
    spec = OUT / "footprints_spec.txt"
    spec.write_text(footprints.library_spec(fps, PCBLIB_PATH), encoding="cp1252", errors="replace")
    print(f"creating {len(fps)} footprints in {PCBLIB_PATH}")
    res = mcp("create_footprints_batch", {"spec_file": str(spec)})
    print(json.dumps(res, indent=2)[:2000])
    if not save_docs([("PcbLib", str(PCBLIB_PATH))]):
        return False
    if not names:
        # a new library starts with an empty PCBComponent_1
        (BRIDGE / "ape_new_lib.txt").write_text(f"{PCBLIB_PATH}\n", encoding="cp1252", errors="replace")
        ok, drop = run_ape("DropDefaultFootprint", timeout=120)
        print("  DropDefaultFootprint: " + json.dumps(drop))
    assumed = [fp for fp in fps if fp.assumed]
    if assumed:
        print("pad numbering assumed (check against the part before layout):")
        for fp in assumed:
            print(f"  {fp.name}: {fp.assumed}")
    query = footprints.paste_rule_query(fps)
    if query:
        print("exposed pads with windowed paste: add a Paste Mask Expansion rule of -2.5 mm for")
        print("  " + query)
    return (res.get("created") == len(fps) and not res.get("failed")
            and not res.get("primitive_errors"))


def build_sheet(sh) -> bool:
    path = Path(sh.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Start every build from a fresh template copy: close the sheet in Altium
    # first (it would otherwise keep its in-memory copy), then overwrite it.
    if path.exists():
        BRIDGE.mkdir(parents=True, exist_ok=True)
        (BRIDGE / "ape_close_list.txt").write_text(str(path) + "\n", encoding="cp1252", errors="replace")
        ok, res = run_ape("CloseDocs", timeout=60)
        if not ok:
            print("  could not close the sheet in Altium:", json.dumps(res)[:300])
            return False
    shutil.copyfile(TEMPLATE_SHEET, path)
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / "ape_sheet_spec.txt").write_text(sh.spec(str(LIB_PATH)), encoding="cp1252", errors="replace")
    pin_map = BRIDGE / "ape_pin_map.txt"
    if pin_map.exists():
        pin_map.unlink()
    print(f"building {path.name} ({len(sh.placed)} parts)")
    ok, res = run_ape("BuildSheet", timeout=600)
    print("  " + str(res.get("result", res))[:500])
    if not ok or not pin_map.exists():
        return False
    problems = sh.check_pin_map(pin_map.read_text(encoding="cp1252", errors="replace"))
    if problems:
        print(f"  PIN MAP MISMATCH ({len(problems)}):")
        print("\n".join("    " + p for p in problems[:40]))
        return False
    print("  pin map matches the generator: every stub lands on its pin")
    return True


def cmd_sheets(names=None):
    ok = True
    for sh in load_sheets(include_frozen=bool(names)):
        if names and Path(sh.path).stem not in names and not any(
                Path(sh.path).stem.startswith(n) for n in names):
            continue
        ok &= build_sheet(sh)
    return ok


def cmd_register():
    """Add every sheet and the symbol library to the project while it is OPEN
    in Altium (the `project` command edits the .PrjPcb and needs it closed)."""
    docs = [str(Path(sh.path)) for sh in load_sheets() if Path(sh.path).exists()]
    for lib in (LIB_PATH, PCBLIB_PATH):
        if lib.exists():
            docs.append(str(lib))
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / "ape_add_list.txt").write_text("\n".join([str(PRJ_PATH)] + docs) + "\n",
                                             encoding="cp1252", errors="replace")
    ok, res = run_ape("AddToProject", timeout=120)
    print("  " + str(res.get("result", res))[:400])
    return ok


# -------------------------------------------------------------------- pcb

PCB_PATH = HW / "PCB.PcbDoc"
PCB_STEPS = ["eco-options", "outline", "stack", "impedance", "import", "classes", "rules", "report"]
# `clear` deletes every component (before placement only): the ECO compares
# footprint names, so changed footprints need `pcb clear import`.
PCB_EXTRA = ["clear"]


def pcb_nets() -> list[str]:
    nets = set()
    for sh in load_sheets():
        nets.update(sh.netlist())
    return sorted(nets)


def pcb_run(proc, spec_name, text, timeout=300):
    """Write one spec to the bridge folder and run ApeScripts>proc on it."""
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / spec_name).write_text(text, encoding="cp1252", errors="replace")
    ok, res = run_ape(proc, timeout=timeout)
    print(f"  {proc}: " + json.dumps(res)[:1500])
    return ok


def x2_windows(title):
    """Visible top-level X2.EXE windows whose title contains title."""
    import ctypes
    import ctypes.wintypes as wt
    import subprocess
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq X2.EXE", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    pids = {int(l.split(",")[1].strip('"')) for l in out.splitlines() if l.startswith('"X2')}
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        pid = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, buf, 256)
            if title.lower() in buf.value.lower():
                found.append(h)
        return True

    user32.EnumWindows(cb, 0)
    return found


def dialog_buttons(dlg):
    """{caption without '&': hwnd} of the visible child controls of dlg."""
    import ctypes
    import ctypes.wintypes as wt
    user32 = ctypes.windll.user32
    found = {}

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        if buf.value:
            found[buf.value.replace("&", "")] = h
        return True

    user32.EnumChildWindows(dlg, cb, 0)
    return found


def press(button, dlg, settle=2.0, timeout=600):
    """Click a VCL button in a dialog that is not the active window, then wait
    until the dialog answers messages again. BM_CLICK is ignored by inactive
    dialogs (verified on AD26), so send the parent the button's BN_CLICKED."""
    import ctypes
    import time
    user32 = ctypes.windll.user32
    user32.PostMessageW(user32.GetParent(button), 0x0111, user32.GetDlgCtrlID(button) & 0xFFFF, button)
    time.sleep(settle)
    res = ctypes.c_size_t()
    start = time.time()
    while time.time() - start < timeout:
        if user32.SendMessageTimeoutW(dlg, 0, 0, 0, 0x0002, 5000, ctypes.byref(res)):   # WM_NULL
            return True
        time.sleep(1)
    return False


def window_png(hwnd, path):
    """Save one window as PNG with PrintWindow (it may be covered); needs Pillow."""
    try:
        import ctypes
        import ctypes.wintypes as wt
        from PIL import Image
    except ImportError:
        return False
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)
    header = (ctypes.c_int32 * 10)(40, w, -h, 1 | (32 << 16), 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, header, 0)
    Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB").save(path)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)
    return True


def pcb_import(path):
    """Design >> Import Changes into the PCB: ApeScripts>PcbImport opens the
    ECO dialog, this presses Validate, Execute and Close, and saves PNGs of the
    dialog to gen/out/eco_*.png. The result is checked by `pcb report`."""
    import subprocess
    import time
    BRIDGE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    (BRIDGE / "ape_pcb_import.txt").write_text(f"{path}\n", encoding="cp1252", errors="replace")
    for f in (BRIDGE / "ape_log.txt", BRIDGE / "ape_result.json"):
        if f.exists():
            f.unlink()
    subprocess.Popen(f'"{altium_exe()}" -RScriptingSystem:RunScript(ProjectName="{SCRIPT_PRJ}"'
                     f'^|ProcName="ApeScripts>PcbImport")', shell=True)
    start, dlg, info = time.time(), None, None
    while time.time() - start < 180 and not dlg and not info:
        time.sleep(2)
        found = x2_windows("Engineering Change Order")
        dlg = found[0] if found else None
        # in sync: "Differences detected but no ECO generated" (the PCB-only
        # classes, pairs and room, whose removal the project options turn off)
        found = x2_windows("Information")
        info = found[0] if found and not dlg else None
    if info:
        print("  nothing to import (Altium: differences detected but no ECO generated)")
        press(dialog_buttons(info)["OK"], info, timeout=30)
    elif not dlg:
        print("  no ECO dialog after 180 s; dialogs open:", altium_dialogs())
        return False
    else:
        buttons = dialog_buttons(dlg)
        for step in ("Validate Changes", "Execute Changes"):
            print(f"  {step}")
            if not press(buttons[step], dlg):
                print(f"  the ECO dialog stopped answering after {step}")
                return False
            window_png(dlg, OUT / f"eco_{step.split()[0].lower()}.png")
        press(buttons["Close"], dlg, timeout=30)
    while time.time() - start < 600:
        res = BRIDGE / "ape_result.json"
        if res.exists():
            time.sleep(0.3)
            data = json.loads(res.read_text(encoding="cp1252", errors="replace"))
            print("  PcbImport: " + json.dumps(data))
            print(f"  ECO dialog images: {OUT}\\eco_*.png")
            return bool(data.get("success"))
        time.sleep(1)
    print("  no result from PcbImport")
    return False


def pcb_check(report: Path) -> bool:
    """Compare PcbReport's components, footprints and pad nets with the generator."""
    want_fp, want_net = {}, {}
    for sh in load_sheets():
        for pl in sh.placed:
            want_fp[pl.designator] = pl.footprint
            for num, net in pl.nets.items():
                want_net[(pl.designator, num)] = "" if net == "NC" else net
    have_fp, have_net = {}, {}
    for line in report.read_text(encoding="cp1252", errors="replace").splitlines():
        f = line.split("|")
        if f[0] == "COMP":
            have_fp[f[1]] = f[2]
        elif f[0] == "PAD" and f[2]:
            have_net.setdefault((f[1], f[2]), set()).add(f[3])
    problems = [f"{d} missing from the PCB" for d in sorted(set(want_fp) - set(have_fp))]
    problems += [f"{d} on the PCB but not in the schematic" for d in sorted(set(have_fp) - set(want_fp))]
    problems += [f"{d}: footprint {have_fp[d]}, expected {want_fp[d]}"
                 for d in sorted(set(want_fp) & set(have_fp)) if have_fp[d] != want_fp[d]]
    for key, net in sorted(want_net.items()):
        if key[0] in have_fp and have_net.get(key, {net}) != {net}:
            problems.append(f"{key[0]} pad {key[1]}: net {sorted(have_net[key])}, expected {net or 'none'}")
        elif key[0] in have_fp and key not in have_net:
            problems.append(f"{key[0]} pin {key[1]} has no pad")
    nets = {n for v in have_net.values() for n in v if n}
    print(f"  {len(have_fp)} components, {len(nets)} nets, {len(have_net)} named pads on the PCB; "
          f"schematic: {len(want_fp)} designators, {len({n for n in want_net.values() if n})} nets")
    print("\n".join("  " + p for p in problems[:60]) if problems else "  pads match the schematic netlist")
    return not problems


def dismiss_server_prompt(stop):
    """Close Altium's "Save <project> to Server" window whenever it appears,
    until stop is set. Closing a project opens it (Altium's own VCS commit and
    push for hardware/.git); closing it uploads nothing."""
    import ctypes
    import time
    while not stop.is_set():
        for h in x2_windows("to Server"):
            print("  dismissing Altium's Save to Server prompt (nothing uploaded)")
            ctypes.windll.user32.PostMessageW(h, 0x0010, 0, 0)       # WM_CLOSE
        time.sleep(1)


def pcb_project_edit(edit) -> bool:
    """Apply edit(text) to the .PrjPcb: close the project in Altium, rewrite
    the file, open it again (Altium rewrites the file when it closes it)."""
    import threading
    text = PRJ_PATH.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    if edit(text) == text:
        print("  project options already set")
        return True
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / "ape_project.txt").write_text(f"{PRJ_PATH}\n{PCB_PATH}\n", encoding="cp1252", errors="replace")
    stop = threading.Event()
    watcher = threading.Thread(target=dismiss_server_prompt, args=(stop,), daemon=True)
    watcher.start()
    ok, res = run_ape("CloseApeProject", timeout=180)
    stop.set()
    print("  CloseApeProject: " + json.dumps(res))
    if not ok:
        return False
    raw = PRJ_PATH.read_bytes()             # as Altium saved it on closing
    bom = raw.startswith(b"\xef\xbb\xbf")
    new = edit(raw.decode("utf-8-sig").replace("\r\n", "\n"))
    PRJ_PATH.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.replace("\n", "\r\n").encode("utf-8"))
    print(f"  updated {PRJ_PATH.name}")
    ok, res = run_ape("OpenApeProject", timeout=120)
    print("  OpenApeProject: " + json.dumps(res))
    return ok


def cmd_pcb(args):
    """Set up hardware/PCB.PcbDoc from gen/pcbsetup.py (README section 11).
    `build.py pcb` runs every step in order; `build.py pcb rules report` runs some."""
    import pcbsetup
    steps = args or PCB_STEPS
    unknown = [s for s in steps if s not in PCB_STEPS + PCB_EXTRA]
    if unknown:
        print("unknown pcb steps: " + " ".join(unknown) + "; steps are " + " ".join(PCB_STEPS + PCB_EXTRA))
        return False
    if "impedance" in steps and "rules" not in steps:
        # new profiles get new ids; the impedance-driven rules must point at them
        steps = steps + ["rules"]
    path = PCB_PATH
    for step in steps:
        print(f"pcb {step}")
        if step == "clear":
            ok = pcb_run("PcbClear", "ape_pcb_import.txt", f"{path}\n")
        elif step == "eco-options":
            ok = pcb_project_edit(pcbsetup.set_eco_levels)
        elif step == "outline":
            ok = pcb_run("PcbOutline", "ape_pcb_outline.txt", pcbsetup.outline_spec(path))
        elif step == "stack":
            ok = pcb_run("PcbStack", "ape_pcb_stack.txt", pcbsetup.stack_spec(path))
        elif step == "impedance":
            ok = pcb_run("PcbImpedance", "ape_pcb_imp.txt", pcbsetup.impedance_spec(path))
        elif step == "import":
            ok = pcb_import(path)
        elif step == "classes":
            nets = pcb_nets()
            missing = pcbsetup.check_nets(nets)
            if missing:
                print("  nets named in pcbsetup.py but not in the schematic: " + " ".join(missing))
                return False
            ok = pcb_run("PcbClasses", "ape_pcb_classes.txt", pcbsetup.classes_spec(path, nets))
        elif step == "rules":
            ok = pcb_run("PcbRules", "ape_pcb_rules.txt", pcbsetup.rules_spec(path))
        elif step == "report":
            ok = pcb_run("PcbReport", "ape_pcb_report_in.txt", f"{path}\n")
            if ok:
                OUT.mkdir(exist_ok=True)
                shutil.copyfile(BRIDGE / "ape_pcb_report.txt", OUT / "pcb_report.txt")
                print(f"  report in {OUT / 'pcb_report.txt'}")
                ok = pcb_check(OUT / "pcb_report.txt")
        if not ok:
            return False
    return True


def cmd_smoke():
    """Two resistors, a capacitor and the PMIC on a scratch sheet."""
    sh = schgen.Sheet(str(OUT / "smoke.SchDoc"), "Smoke test", style=6)
    sh.add("R1", symbols.RES, 2000, 6000, {"1": "SMOKE_A", "2": "SMOKE_B"}, comment="10k")
    sh.add("C1", symbols.CAP, 2000, 5600, {"1": "VCC_3V3_SYS", "2": "GND"}, comment="100nF")
    sh.add("U1", symbols.TPS65219, 5000, 7000, {"13": "VCC_3V3_MAIN", "33": "GND", "9": "SMOKE_A",
                                                "10": "SMOKE_B"}, comment="TPS6521904RHBR")
    assign_footprints(sh)
    OUT.mkdir(exist_ok=True)
    return build_sheet(sh)


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, rest = argv[0], argv[1:]
    actions = {
        "check": lambda: cmd_check(),
        "project": lambda: cmd_project(),
        "register": lambda: cmd_register(),
        "unwedge": lambda: cmd_unwedge(),
        "ping": lambda: run_ape("Ping", timeout=60)[0],
        "smoke": lambda: cmd_smoke(),
        "lib": lambda: cmd_lib(rest),
        "footprints": lambda: cmd_footprints(rest),
        "sheet": lambda: cmd_sheets(rest),
        "sheets": lambda: cmd_sheets(),
        "pcb": lambda: cmd_pcb(rest),
    }
    if cmd not in actions:
        print(__doc__)
        return 1
    return 0 if actions[cmd]() else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
