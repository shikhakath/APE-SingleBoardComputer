"""Sheet 05 - OSD6254 SiP signal balls (parts D-I).

Every net name comes from data/pinmux_allocation.csv, which is the contract
for all interface sheets: they connect to the SoC by these names. Balls with
no allocation get a No-ERC marker (default pad state after reset is off).

Shared balls: BOOTMODE[15:8] are the same balls as VOUT0_DATA16-23, so the
net is DPI_D16..DPI_D23 and the boot-strap resistors on sheet 06 attach to
those nets. BOOTMODE[7:0] are strap-only nets BOOTMODE00..BOOTMODE07.
"""
import csv
from pathlib import Path

from schgen import Sheet
from symbols import OSD6254

DATA = Path(__file__).resolve().parent.parent / "data"


def ball_nets() -> dict[str, str]:
    with open(DATA / "pinmux_allocation.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cands: dict[str, list[str]] = {}
    for r in rows:
        if r["ball"] and r["net_name"] and r["net_name"] != "NC":
            cands.setdefault(r["ball"], []).append(r["net_name"])
    nets = {}
    for ball, names in cands.items():
        names = list(dict.fromkeys(names))
        dpi = [n for n in names if n.startswith("DPI_")]
        if dpi:
            nets[ball] = dpi[0]
        elif len(names) == 1:
            nets[ball] = names[0]
        else:
            raise ValueError(f"ball {ball} has several nets: {names}")
    return nets


# part number -> top-left body position (D-size sheet, 34 x 22 in)
PLACEMENT = {4: (3500, 20500), 5: (14500, 20500), 6: (25500, 20500),
             7: (3500, 11500), 8: (14500, 11500), 9: (25500, 11500)}


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/05_SiP_IO.SchDoc", "SiP signals", style=8)
    nets = ball_nets()
    used = set()
    for part, (x, y) in PLACEMENT.items():
        pins = {}
        for p in OSD6254.pins:
            if p.part == part:
                pins[p.number] = nets.get(p.number, "NC")
                used.add(p.number)
        sh.add("U1", OSD6254, x, y, pins, part=part, comment="OSD6254-1G-IPM")
    stray = sorted(set(nets) - used)
    if stray:
        raise ValueError(f"pinmux nets on balls outside parts D-I: {stray}")
    sh.note(3000, 21300, "Net names = data/pinmux_allocation.csv. Balls marked No-ERC are unused (pad off after reset).")
    sh.note(3000, 21100, "BOOTMODE[15:8] share balls with DPI_D16..23: fixed 10k straps only, no DIP switch (sheet 06).")
    return sh
