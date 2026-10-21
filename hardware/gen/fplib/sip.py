"""Octavo OSD62x-PM system-in-package (sheet 03-05)."""
import csv
from pathlib import Path

from footprints import Footprint, bga

# Octavo OSD62x-PM, 500-ball BGA, 9 x 14 mm, 0.5 mm pitch.
# Package: OSD62x-PM Datasheet Rev 2.0 (1/16/2026), section 8.1 Mechanical
# Dimensions, p.30: D = 9, E = 14 BSC; 18 rows A-V (JEDEC letters, no I/O/Q/S) x
# 28 columns, e = 0.5 BSC, D1 = 8.5, E1 = 13.5 (array centred, SD = SE = 0.25);
# ball width b = 0.2-0.3 mm; A1 corner index top left in the top view.
#   https://octavosystems.com/wp-content/uploads/2026/01/OSD62x-PM-Datasheet.pdf
# Land: 0.20 mm round NSMD, section 8.1.1 p.31 (IPC-7351A range 0.20-0.25 mm,
# Octavo footprints use the 0.20 minimum) and the OSD62x-PM Layout Guide rev
# 10/03/2025 ("Landing pad 0.20 mm (NSMD)", docs/research/osd62x-pm-sip.md 1.10).
# Solder mask on these lands must be 1:1 (rule InComponent('U1'), expansion 0)
# and paste 0 (JLCPCB cuts 0.25-0.27 mm BGA apertures on request), see
# docs/research/bom/jlcpcb-stackup-and-cost.md sections 4-5.
# Ball names come from data/osd6254_ballmap.csv: 504 sites minus the four
# corners A1, A28, V1, V28.
_BALLS = {r["ball"] for r in csv.DictReader(
    open(Path(__file__).resolve().parent.parent / "data" / "osd6254_ballmap.csv", newline="", encoding="utf-8"))}
_CORNERS = ("A1", "A28", "V1", "V28")

OSD62X_PM_BGA500 = Footprint(
    "OSD62X-PM_BGA500", "Octavo OSD62x-PM SiP, 500-ball BGA 9x14 mm, 0.5 mm pitch, 0.20 mm NSMD lands",
    bga(18, 28, 0.5, 0.20, missing=_CORNERS),
    body=(14.0, 9.0), marker="corner", marker_pad="A2", silk_offset=0.15, courtyard=0.5)
if OSD62X_PM_BGA500.pad_names() != _BALLS:
    raise ValueError("BGA grid does not match data/osd6254_ballmap.csv")

FOOTPRINTS = [OSD62X_PM_BGA500]
