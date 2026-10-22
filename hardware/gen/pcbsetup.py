"""APE-SBC PCB setup as code: board outline, layer stack, impedance profiles,
net and differential-pair classes, the SiP room and the design rules.

Sources:
- docs/research/bom/jlcpcb-stackup-and-cost.md: section 2.2 (stack), 3.1 (impedance
  widths), 4 (SiP via padstacks) and 5 (Altium rule values).
- docs/research/osd62x-pm-sip.md section 1.10: Octavo layout guide (3/3 mil fan-out,
  one via between four balls, 0.20 mm NSMD lands).

build.py writes each spec below to the bridge folder and runs the matching
ApeScripts procedure (PcbOutline, PcbStack, PcbImpedance, PcbClasses, PcbRules).
All lengths in the specs are Altium coords (1 mil = 10000), so no decimal
separator is ever parsed in Altium.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import footprints
import schgen

MIL = 10000                     # Altium coords per mil


def mm(v: float) -> int:
    return round(v / 0.0254 * MIL)


def mil(v: float) -> int:
    return round(v * MIL)


# ------------------------------------------------------------------ outline
# 100 x 70 mm, square corners; lower-left corner at (1000 mil, 1000 mil) in
# Altium's absolute coordinates, and the board origin is set there.
BOARD_W_MM, BOARD_H_MM = 100.0, 70.0
BOARD_X0, BOARD_Y0 = mil(1000), mil(1000)


def outline_spec(pcb: Path) -> str:
    return (f"{pcb}\nOUTLINE|{BOARD_X0}|{BOARD_Y0}|{mm(BOARD_W_MM)}|{mm(BOARD_H_MM)}\n")


# -------------------------------------------------------------------- stack
# JLC06161H-3313, TOP / GND / SIG / GND / PWR / BOT (section 2.2). Section 5
# asks for the calculator's model in the Layer Stack Manager: Dk 4.3 for 3313
# and the cores, 4.2 for 2116, outer copper T = 1.6 mil (1 oz finished, plated),
# inner 0.6 mil (0.5 oz), solder mask 1.0 mil with Dk 3.8.
# (name, V7 layer id, copper mil, placement 0/1 top/2 bottom, orientation 0 up / 1 down)
COPPER = [
    ("L1_TOP", 16777217, 1.6, 1, 0),
    ("L2_GND", 16777218, 0.6, 0, 0),
    ("L3_SIG", 16777219, 0.6, 0, 1),
    ("L4_GND", 16777220, 0.6, 0, 0),
    ("L5_PWR", 16777221, 0.6, 0, 1),
    ("L6_BOT", 16842751, 1.6, 2, 1),
]
# dielectric below each copper layer but the last: (name, type 0 core / 2 prepreg,
# material, height mm, Dk, loss tangent)
DIELECTRIC = [
    ("PP 3313 L1-L2", 2, "3313 RC57%", 0.0994, 4.3, 0.02),
    ("Core L2-L3", 0, "FR-4 core H/H", 0.55, 4.3, 0.02),
    ("PP 2116 L3-L4", 2, "2116 RC54%", 0.1088, 4.2, 0.02),
    ("Core L4-L5", 0, "FR-4 core H/H", 0.55, 4.3, 0.02),
    ("PP 3313 L5-L6", 2, "3313 RC57%", 0.0994, 4.3, 0.02),
]
MASK_MIL, MASK_DK = 1.0, 3.8
LAYER_IDS = {"Top Paste": 16973832, "Top Overlay": 16973830, "Top Solder": 16973834,
             "Bottom Solder": 16973835, "Bottom Overlay": 16973831, "Bottom Paste": 16973833}
DIEL_ID0 = 17039361             # dielectric layer ids are 17039361 + n


def read_board6(pcb: Path) -> dict:
    """Key=value records of the PcbDoc's Board6 stream (needs olefile)."""
    import olefile
    with olefile.OleFileIO(str(pcb)) as ole:
        raw = ole.openstream("Board6/Data").read()
    rec = {}
    for item in raw[4:].decode("latin-1").split("|"):
        if "=" in item:
            k, v = item.split("=", 1)
            rec[k] = v
    return rec


def stack_layers():
    """The stack top to bottom as (name, layer id, kind, props) tuples."""
    rows = [("Top Paste", LAYER_IDS["Top Paste"], "other", {}),
            ("Top Overlay", LAYER_IDS["Top Overlay"], "other", {}),
            ("Top Solder", LAYER_IDS["Top Solder"], "mask", {})]
    for i, (name, lid, cu, place, orient) in enumerate(COPPER):
        rows.append((name, lid, "copper", dict(cu=cu, place=place, orient=orient)))
        if i < len(DIELECTRIC):
            dname, dtype, mat, h, dk, tan = DIELECTRIC[i]
            rows.append((dname, DIEL_ID0 + i, "diel",
                         dict(type=dtype, mat=mat, h_mil=h / 0.0254, dk=dk, tan=tan)))
    rows += [("Bottom Solder", LAYER_IDS["Bottom Solder"], "mask", {}),
             ("Bottom Overlay", LAYER_IDS["Bottom Overlay"], "other", {}),
             ("Bottom Paste", LAYER_IDS["Bottom Paste"], "other", {})]
    return rows


def stack_params(pcb: Path) -> list[str]:
    """V9 master-stack parameters for MasterLayerStack.Import_FromParameters.
    Layer GUIDs already in the document (stack or cache) are kept."""
    b6 = read_board6(pcb)
    ids = {}
    for k, v in b6.items():
        m = re.match(r"V9_(?:STACK|CACHE)_LAYER(\d+)_LAYERID$", k)
        if m:
            pre = k[:-len("LAYERID")]
            ids.setdefault(int(v), b6.get(pre + "ID"))
    sub = b6["V9_SUBSTACK0_ID"]
    out = [f"V9_MASTERSTACK_STYLE=0", f"V9_MASTERSTACK_ID={b6['V9_MASTERSTACK_ID']}",
           "V9_MASTERSTACK_NAME=Master layer stack",
           "V9_MASTERSTACK_SHOWTOPDIELECTRIC=FALSE", "V9_MASTERSTACK_SHOWBOTTOMDIELECTRIC=FALSE",
           "V9_MASTERSTACK_ISFLEX=FALSE",
           f"V9_SUBSTACK0_ID={sub}", "V9_SUBSTACK0_NAME=Board Layer Stack",
           "V9_SUBSTACK0_SHOWTOPDIELECTRIC=FALSE", "V9_SUBSTACK0_SHOWBOTTOMDIELECTRIC=FALSE",
           "V9_SUBSTACK0_ISFLEX=FALSE", "V9_SUBSTACK0_SERVICE=FALSE",
           "V9_SUBSTACK0_USEDBYPRIMS=FALSE", "V9_SUBSTACK0_TYPE=1"]
    for n, (name, lid, kind, p) in enumerate(stack_layers()):
        k = f"V9_STACK_LAYER{n}_"
        gid = ids.get(lid) or "{" + str(uuid.uuid4()).upper() + "}"
        out += [f"{k}{sub}CONTEXT=0", f"{k}{sub}USEDBYPRIMS=FALSE", f"{k}ID={gid}",
                f"{k}NAME={name}", f"{k}LAYERID={lid}", f"{k}USEDBYPRIMS=FALSE"]
        if kind == "mask":
            out += [f"{k}DIELTYPE=3", f"{k}DIELCONST={MASK_DK:.3f}", f"{k}DIELHEIGHT={MASK_MIL}mil",
                    f"{k}DIELMATERIAL=Solder Resist", f"{k}COVERLAY_EXPANSION=0mil"]
        elif kind == "copper":
            out += [f"{k}COPTHICK={p['cu']}mil"]
            if p["orient"]:
                out.append(f"{k}COPPERORIENTATION=1")
            out.append(f"{k}COMPONENTPLACEMENT={p['place']}")
        elif kind == "diel":
            out += [f"{k}DIELTYPE={p['type']}", f"{k}DIELCONST={p['dk']:.3f}",
                    f"{k}DIELHEIGHT={p['h_mil']:.4f}mil", f"{k}DIELMATERIAL={p['mat']}",
                    f"{k}DIELLOSSTANGENT={p['tan']:.3f}"]
    return out


def stack_spec(pcb: Path) -> str:
    return f"{pcb}\n" + "\n".join(stack_params(pcb)) + "\n"


# ------------------------------------------------------- impedance profiles
# Section 3.1, JLCPCB calculator: width / gap in mil per routing layer.
# L1 and L6 are microstrip (L6 referenced to L5 PWR); L3 is the asymmetric
# stripline between L2 and L4 (both GND). L2, L4 and L5 carry no impedance traces.
# (profile, ohms, diff, {layer: (width, gap)})
IMPEDANCE = [
    ("SE50", 50, False, {"L1_TOP": (5.94, 0), "L3_SIG": (5.59, 0), "L6_BOT": (5.94, 0)}),
    ("DIFF90", 90, True, {"L1_TOP": (5.34, 6.0), "L3_SIG": (5.03, 6.0), "L6_BOT": (5.34, 6.0)}),
    ("DIFF100", 100, True, {"L1_TOP": (4.69, 8.0), "L3_SIG": (4.33, 8.0), "L6_BOT": (4.69, 8.0)}),
]
REFS = {"L1_TOP": ("", "L2_GND"), "L3_SIG": ("L2_GND", "L4_GND"), "L6_BOT": ("L5_PWR", "")}
IMP_TOLERANCE = 10              # percent; JLCPCB impedance control is +/-10 %


def impedance_spec(pcb: Path) -> str:
    ids = {name: lid for name, lid, *_ in COPPER}
    lines = [str(pcb)]
    for name, ohms, diff, layers in IMPEDANCE:
        lines.append(f"IMP|{name}|{ohms}|{int(diff)}|{IMP_TOLERANCE}")
        for lname, (w, g) in layers.items():
            top, bot = REFS[lname]
            outer = lname in ("L1_TOP", "L6_BOT")      # solder mask over the trace and between
            mask = f"{mil(0.6)}|{mil(MASK_MIL)}" if outer else "0|0"
            lines.append(f"TRACE|{ids[lname]}|{mil(w)}|{mil(g)}|{ids.get(top, 0)}|{ids.get(bot, 0)}|{mask}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------- classes and pairs
DIFF_PAIRS = {
    # class: [(pair name, positive net, negative net)]
    "USB0": [("USB0", "USB0_DP", "USB0_DM"), ("USBC1", "USBC1_DP", "USBC1_DM")],
    "USB1": [("USB1", "USB1_DP", "USB1_DM"), ("HUB_P1", "HUB_P1_DP", "HUB_P1_DM"),
             ("HUB_P2", "HUB_P2_DP", "HUB_P2_DM"), ("USBA1", "USBA1_DP", "USBA1_DM"),
             ("USBA2", "USBA2_DP", "USBA2_DM")],
    "USB_DBG": [("DBG_USB", "DBG_USB_DP", "DBG_USB_DM")],
    "ETH_MDI": [(f"ETH_MDI{i}", f"ETH_MDI{i}_P", f"ETH_MDI{i}_N") for i in range(4)],
    "HDMI_TMDS": [(f"HDMI_{c}", f"HDMI_{c}_P", f"HDMI_{c}_N") for c in ("TX0", "TX1", "TX2", "TXC")],
    "CSI": [(f"CSI_{c}", f"CSI_{c}_P", f"CSI_{c}_N") for c in ("CLK", "D0", "D1")],
}
DP_90R = ("USB0", "USB1", "USB_DBG")
DP_100R = ("ETH_MDI", "HDMI_TMDS", "CSI")

# 50 ohm single-ended: RGMII, eMMC / SD / SDIO, DPI and the reference clocks
SE50_RE = re.compile(r"^(ETH_(TD\d|RD\d|TXC|RXC|TX_CTL|RX_CTL)|PHY_(TX_D\d|RX_D\d|TX_CTRL|RX_CTRL|GTX_CLK"
                     r"|RX_CLK)|EMMC_(CLK|CMD|D\d|MOD_CLK|MOD_DS)|SD_(CLK|CMD|D\d|SOCK_CLK)"
                     r"|M2_SDIO_(CMD|D\d)|WL_SDIO_(CLK|CMD|D\d)|DPI_.*|TFP_IDCK|OSC_25M|AUD_MCLK)$")

# Power rails by group; PWR holds every rail. PWR_HI are the rails and switch
# nodes that carry an amp or more (USB-C input, 5 V, 3.3 V, core, DDR, 1.8 V).
PWR_GROUPS = [
    ("PWR_IN", re.compile(r"^(VBUS_|VSYS_|VCC_5V0)")),
    ("PWR_CORE", re.compile(r"_0V85$")),
    ("PWR_DDR", re.compile(r"^(VDDS_DDR_|DDR4_VPP_)")),
    ("PWR_1V8", re.compile(r"_1V8")),
    ("PWR_3V3", re.compile(r"_3V3")),
]
PWR_HI = ["VBUS_USBC", "VSYS_PD", "VCC_5V0", "VCC_3V3_MAIN", "VCC_3V3_SYS", "VDD_CORE_0V85",
          "VDDS_DDR_1V2", "VDD_1V8", "LM_SW", "BB_L1", "BB_L2", "PMIC_LX_B1", "PMIC_LX_B2",
          "PMIC_LX_B3"]


def net_classes(nets: list[str]) -> dict[str, list[str]]:
    rails = sorted(n for n in nets if schgen.is_rail(n) and n != "GND")
    classes = {"PWR": rails}
    rest = list(rails)
    for name, rx in PWR_GROUPS:
        classes[name] = [n for n in rest if rx.search(n)]
        rest = [n for n in rest if n not in classes[name]]
    classes["PWR_OTHER"] = rest
    classes["PWR_HI"] = [n for n in PWR_HI if n in nets]
    classes["SE50"] = sorted(n for n in nets if SE50_RE.match(n))
    return classes


def classes_spec(pcb: Path, nets: list[str]) -> str:
    lines = [str(pcb)]
    for name, members in net_classes(nets).items():
        lines.append("NETCLASS|" + name + "|" + "|".join(members))
    for cls, pairs in DIFF_PAIRS.items():
        for pair, p, n in pairs:
            lines.append(f"DIFFPAIR|{pair}|{p}|{n}")
        lines.append("DPCLASS|" + cls + "|" + "|".join(pair for pair, _, _ in pairs))
    return "\n".join(lines) + "\n"


def check_nets(nets: list[str]) -> list[str]:
    """Nets named by the classes and pairs that the schematic does not have."""
    have = set(nets)
    missing = [n for pairs in DIFF_PAIRS.values() for _, p, q in pairs for n in (p, q) if n not in have]
    missing += [n for n in PWR_HI if n not in have]
    return missing


# ------------------------------------------------------------ ECO options
# The classes, pairs and room above exist only in the PCB, and with the
# template's options every later Design >> Import Changes removes them (seen
# on AD26). The project's ECO Generation options stop it generating these
# change orders: [Modification Levels] in the .PrjPcb has Type1..Type161 for
# Altium's eModification_* values 0..160, so value N is TypeN+1 (verified on
# AD26: Type19 = Remove Net Classes), and 0 means "do not generate".
ECO_SKIP = {
    3: "Remove Net Class Members",
    18: "Remove Net Classes",
    19: "Remove Differential Pairs",
    33: "Remove Rooms",
    112: "Remove Differential Pair Classes",
    115: "Remove Differential Pair Class Members",
}


def set_eco_levels(text: str) -> str:
    """Project file text with the ECO_SKIP change orders turned off."""
    lines = text.split("\n")
    sec = None
    for i, line in enumerate(lines):
        if line.startswith("["):
            sec = line.strip()
        elif sec == "[Modification Levels]" and line.startswith("Type") and "=" in line:
            n = line[4:line.index("=")]
            if n.isdigit() and int(n) - 1 in ECO_SKIP:
                lines[i] = f"Type{n}=0"
    return "\n".join(lines)


# --------------------------------------------------------------- SiP room
# The SiP region (section 5: WithinRoom('U1_SiP')). The room is the 9 x 14 mm
# body plus 1 mm for the fan-out vias on every side. It starts at the board
# centre; move it with U1 during placement (rooms carry their components).
ROOM_W_MM, ROOM_H_MM = 11.0, 16.0
SIP_ROOM = "U1_SiP"
SIP = f"WithinRoom('{SIP_ROOM}')"


def room_spec() -> str:
    cx, cy = BOARD_X0 + mm(BOARD_W_MM / 2), BOARD_Y0 + mm(BOARD_H_MM / 2)
    return (f"ROOM|{SIP_ROOM}|InComponent('U1')|{cx - mm(ROOM_W_MM / 2)}|{cy - mm(ROOM_H_MM / 2)}"
            f"|{cx + mm(ROOM_W_MM / 2)}|{cy + mm(ROOM_H_MM / 2)}")


# ------------------------------------------------------------------ rules
def _or(fn, names):
    return " Or ".join(f"{fn}('{n}')" for n in names)


def _per_layer(profile: str) -> str:
    """'layer:width:gap;...' for every copper layer from an impedance profile;
    the plane layers L2 / L4 / L5 take the L3 stripline values."""
    widths = next(layers for name, _, _, layers in IMPEDANCE if name == profile)
    return ";".join(f"{lid}:{mil(widths.get(name, widths['L3_SIG'])[0])}"
                    f":{mil(widths.get(name, widths['L3_SIG'])[1])}" for name, lid, *_ in COPPER)


def rules() -> list[list]:
    """One list per rule: kind, name, scope1, scope2, values...; the order
    within a kind is the priority (first = highest). The template's polygon
    connect rules (relief 4 x 10 mil spokes, 10 mil gap; vias direct) already
    match section 5 and are kept."""
    inner = "(OnLayer('L2_GND') Or OnLayer('L4_GND') Or OnLayer('L5_PWR'))"
    paste_query = footprints.paste_rule_query(footprints.all_footprints())
    dp90, dp100 = _or("InDifferentialPairClass", DP_90R), _or("InDifferentialPairClass", DP_100R)
    se50 = ";".join(v.rsplit(":", 1)[0] for v in _per_layer("SE50").split(";"))
    return [
        # clearance: inner-layer pours 0.20 mm from holes (also under the SiP:
        # the 0.55 mm anti-pad of section 4), 0.09 mm (3.5 mil) in the SiP
        # fan-out, SMD pads 0.15 mm, 0.10 mm elsewhere
        ["CLEARANCE", "Clr_InnerPour_Hole", f"InPolygon And {inner}", "IsVia Or IsPad", mm(0.20)],
        ["CLEARANCE", "Clr_SiP", SIP, "All", mm(0.09)],
        ["CLEARANCE", "Clr_SMD_SMD", "IsSMTPin", "IsSMTPin", mm(0.15)],   # AD26 has no IsSMDPad
        ["CLEARANCE", "Clr_Default", "All", "All", mm(0.10)],
        # width: min | preferred | max | impedance profile | layer:preferred;...
        ["WIDTH", "W_SiP", SIP, "", mm(0.09), mm(0.09), mm(0.15), "", ""],
        ["WIDTH", "W_SE50", "InNetClass('SE50')", "", mm(0.09), mm(0.151), mm(0.20), "SE50", se50],
        ["WIDTH", "W_PWR_HI", "InNetClass('PWR_HI')", "", mm(0.20), mm(1.00), mm(3.0), "", ""],
        ["WIDTH", "W_PWR", "InNetClass('PWR')", "", mm(0.15), mm(0.40), mm(3.0), "", ""],
        ["WIDTH", "W_Default", "All", "", mm(0.10), mm(0.15), mm(3.0), "", ""],
        # diff pairs: min / max width, min / max gap, max uncoupled length,
        # impedance profile, layer:preferred width:preferred gap;...
        ["DIFFPAIR", "DP_90R_USB", dp90, "", mm(0.09), mm(0.15), mm(0.09), mm(0.20), mm(5.0),
         "DIFF90", _per_layer("DIFF90")],
        ["DIFFPAIR", "DP_100R", dp100, "", mm(0.09), mm(0.13), mm(0.09), mm(0.25), mm(5.0),
         "DIFF100", _per_layer("DIFF100")],
        # via style: hole min / preferred / max, diameter min / preferred / max
        ["VIA", "Via_SiP", SIP, "", mm(0.15), mm(0.15), mm(0.15), mm(0.25), mm(0.25), mm(0.25)],
        ["VIA", "Via_PWR", "InNetClass('PWR') Or InNet('GND')", "",
         mm(0.20), mm(0.30), mm(0.50), mm(0.35), mm(0.50), mm(0.80)],
        ["VIA", "Via_Default", "All", "", mm(0.20), mm(0.20), mm(0.50), mm(0.35), mm(0.40), mm(0.80)],
        ["HOLESIZE", "Hole_Size", "All", "", mm(0.15), mm(6.3)],
        ["ANNULAR", "Ring_Via", "IsVia", "", mm(0.05)],
        ["ANNULAR", "Ring_PTH", "IsPad", "", mm(0.15)],
        ["HOLE2HOLE", "HoleToHole_Pads", "IsPad", "IsPad", mm(0.45)],
        ["HOLE2HOLE", "HoleToHole", "All", "All", mm(0.20)],
        ["MASK", "Mask_SiP", "InComponent('U1')", "", 0],
        ["MASK", "Mask_Default", "All", "", mm(0.05)],
        ["PASTE", "Paste_Windowed", paste_query, "", -mm(2.5)],
        ["PASTE", "Paste_TagConnect", "HasFootprint('TC2070-NL')", "", -mm(2.5)],
        # 0.20 mm lands give 0.20 mm apertures: area ratio 0.50 on a 0.10 mm stencil, under
        # IPC-7525's 0.66. +0.03 mm -> 0.26 mm apertures (ratio 0.65).
        ["PASTE", "Paste_SiP", "InComponent('U1')", "", mm(0.03)],
        ["PASTE", "Paste_Default", "All", "", 0],
        ["SLIVER", "Mask_Sliver", "All", "All", mm(0.10)],
        ["SILKMASK", "Silk_To_Mask", "All", "All", mm(0.15)],
        ["OUTLINE", "Board_Outline", "All", "", mm(0.30)],
    ]


def rules_spec(pcb: Path) -> str:
    lines = [str(pcb), room_spec()]
    for rule in rules():
        lines.append("RULE|" + "|".join(str(v) for v in rule))
    return "\n".join(lines) + "\n"
