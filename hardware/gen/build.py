"""APE SBC schematic build driver.

Run from anywhere (paths are resolved from this file's location):

  python build.py check             offline checks + netlist/BOM reports in gen/out/ (no Altium)
  python build.py project           register sheets + library in the .PrjPcb
                                    (close the project in Altium first)
  python build.py smoke             build gen/out/smoke.SchDoc: proves the toolchain end to end
  python build.py lib               create the symbols in lib/APE-SBC.SchLib and save it
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

import schgen  # noqa: E402
import symbols  # noqa: E402

LIB_PATH = HW / "lib" / "APE-SBC.SchLib"
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
        sheets.append(importlib.import_module(f"sheets.{name}").build(str(SCH_DIR)))
    return sheets


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
    print(f"{len(sheets)} sheets, {len(owners)} placed parts, {len(nets)} nets")
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
    wanted = [Path(sh.path) for sh in load_sheets()] + [LIB_PATH]
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
        print("project already lists every sheet and the library")
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


def run_pas(name, timeout=600):
    script = (GEN / "altium" / name).read_text(encoding="utf-8")
    res = mcp("run_altium_script", {"script": script, "timeout_seconds": timeout}, timeout + 60)
    ok = res.get("success", False)
    if not ok:
        print(json.dumps(res, indent=2)[:4000])
    return ok, res


def save_docs(entries):
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / "ape_save_list.txt").write_text("\n".join(f"{k}|{p}" for k, p in entries) + "\n",
                                              encoding="cp1252", errors="replace")
    return run_pas("ape_save_docs.pas")[0]


def cmd_lib():
    LIB_PATH.parent.mkdir(exist_ok=True)
    spec = OUT / "symbols_spec.txt"
    OUT.mkdir(exist_ok=True)
    spec.write_text(symbol_spec(), encoding="cp1252", errors="replace")
    if not LIB_PATH.exists():
        # create_symbols_batch only opens an EXISTING library. With no library
        # it adds symbols to whatever document is focused, dies, and wedges
        # Altium's script executor. Opening a missing path makes Altium create
        # an empty library, which the save script then writes to disk.
        print(f"creating empty {LIB_PATH.name}")
        if not save_docs([("SchLib", str(LIB_PATH))]) or not LIB_PATH.exists():
            print("could not create the library - create an empty SchLib at that path in Altium")
            return False
    print(f"creating {len(all_symbols())} symbols in {LIB_PATH}")
    res = mcp("create_symbols_batch", {"spec_file": str(spec)})
    print(json.dumps(res, indent=2)[:2000])
    return save_docs([("SchLib", str(LIB_PATH))])


def build_sheet(sh) -> bool:
    path = Path(sh.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        shutil.copyfile(TEMPLATE_SHEET, path)
        print(f"  created {path.name} from {TEMPLATE_SHEET.name}")
    BRIDGE.mkdir(parents=True, exist_ok=True)
    (BRIDGE / "ape_sheet_spec.txt").write_text(sh.spec(str(LIB_PATH)), encoding="cp1252", errors="replace")
    pin_map = BRIDGE / "ape_pin_map.txt"
    if pin_map.exists():
        pin_map.unlink()
    print(f"building {path.name} ({len(sh.placed)} parts)")
    ok, res = run_pas("ape_sheet_builder.pas", timeout=900)
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


def cmd_smoke():
    """Two resistors, a capacitor and the PMIC on a scratch sheet."""
    sh = schgen.Sheet(str(OUT / "smoke.SchDoc"), "Smoke test", style=6)
    sh.add("R1", symbols.RES, 2000, 6000, {"1": "SMOKE_A", "2": "SMOKE_B"}, comment="10k")
    sh.add("C1", symbols.CAP, 2000, 5600, {"1": "VCC_3V3_SYS", "2": "GND"}, comment="100nF")
    sh.add("U1", symbols.TPS65219, 5000, 7000, {"13": "VCC_3V3_MAIN", "33": "GND", "9": "SMOKE_A",
                                                "10": "SMOKE_B"}, comment="TPS6521904RHBR")
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
        "smoke": lambda: cmd_smoke(),
        "lib": lambda: cmd_lib(),
        "sheet": lambda: cmd_sheets(rest),
        "sheets": lambda: cmd_sheets(),
    }
    if cmd not in actions:
        print(__doc__)
        return 1
    return 0 if actions[cmd]() else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
