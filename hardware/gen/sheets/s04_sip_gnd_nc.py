"""Sheet 04 - OSD6254 SiP ground balls (part B) and NC / reserved balls (part C).

The 93 NC balls and 10 RSVD balls must stay unconnected and must not be routed
through (Octavo OSD62x-PM datasheet Rev 2.0 section 5.3); each gets a No-ERC
marker. Every VSS ball goes to GND with at least one via per ball (layout guide).
"""
from schgen import Sheet
from symbols import OSD6254


def build(sch_dir: str) -> Sheet:
    sh = Sheet(f"{sch_dir}/04_SiP_GND_NC.SchDoc", "SiP ground and no-connect balls", style=7)
    gnd = {p.number: "GND" for p in OSD6254.pins if p.part == 2}
    nc = {p.number: "NC" for p in OSD6254.pins if p.part == 3}
    sh.add("U1", OSD6254, 3000, 15500, gnd, part=2, comment="OSD6254-1G-IPM")
    sh.add("U1", OSD6254, 11000, 15500, nc, part=3, comment="OSD6254-1G-IPM")
    sh.note(10500, 16200, "NC and RSVD balls: leave unconnected and do not route through them (Octavo DS 5.3)")
    sh.note(2500, 16200, "VSS: one via per ball minimum (Octavo layout guide)")
    return sh
