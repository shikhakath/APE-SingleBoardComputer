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
import placement
import schgen

MIL = 10000                     # Altium coords per mil


def mm(v: float) -> int:
    return round(v / 0.0254 * MIL)


def mil(v: float) -> int:
    return round(v * MIL)


# ------------------------------------------------------------------ outline
# Size from placement.py (docs/pcb-placement.md has the numbers behind it);
# lower-left corner at (1000 mil, 1000 mil) in Altium's absolute coordinates, and
# the board origin is set there. `build.py pcb outline` draws square corners:
# `placement.py board` draws the final R3 corners, so run it after that step.
BOARD_W_MM, BOARD_H_MM = placement.BOARD_W, placement.BOARD_H
BOARD_X0, BOARD_Y0 = mil(1000), mil(1000)


def outline_spec(pcb: Path) -> str:
    return (f"{pcb}\nOUTLINE|{BOARD_X0}|{BOARD_Y0}|{mm(BOARD_W_MM)}|{mm(BOARD_H_MM)}\n")


# -------------------------------------------------------------------- stack
# JLC08161H-3313, TOP / GND / SIG / PWR / PWR / SIG / GND / BOT (section 8 of the stackup doc). Every
# signal layer sits 0.1 mm from GND, so splits on the power planes cut no return path. Section 5 asks
# for the calculator's model in the Layer Stack Manager: Dk 4.3 for 3313 and the cores, 4.2 for 2116,
# outer copper T = 1.6 mil (1 oz finished, plated), inner 0.6 mil (0.5 oz), solder mask 1.0 mil, Dk 3.8.
# (name, V7 layer id, copper mil, placement 0/1 top/2 bottom, orientation 0 up / 1 down)
COPPER = [
    ("L1_TOP", 16777217, 1.6, 1, 0),
    ("L2_GND", 16777218, 0.6, 0, 0),
    ("L3_SIG", 16777219, 0.6, 0, 1),
    ("L4_PWR", 16777220, 0.6, 0, 0),
    ("L5_PWR", 16777221, 0.6, 0, 1),
    ("L6_SIG", 16777222, 0.6, 0, 0),
    ("L7_GND", 16777223, 0.6, 0, 1),
    ("L8_BOT", 16842751, 1.6, 2, 1),
]
# dielectric below each copper layer but the last: (name, type 0 core / 2 prepreg,
# material, height mm, Dk, loss tangent)
DIELECTRIC = [
    ("PP 3313 L1-L2", 2, "3313 RC57%", 0.0994, 4.3, 0.02),
    ("Core L2-L3", 0, "FR-4 core H/H", 0.10, 4.3, 0.02),
    ("PP 2116x3 L3-L4", 2, "2116 RC54% x3", 0.3568, 4.2, 0.02),
    ("Core L4-L5", 0, "FR-4 core H/H", 0.30, 4.3, 0.02),
    ("PP 2116x3 L5-L6", 2, "2116 RC54% x3", 0.3568, 4.2, 0.02),
    ("Core L6-L7", 0, "FR-4 core H/H", 0.10, 4.3, 0.02),
    ("PP 3313 L7-L8", 2, "3313 RC57%", 0.0994, 4.3, 0.02),
]
MASK_MIL, MASK_DK = 1.0, 3.8
LAYER_IDS = {"Top Paste": 16973832, "Top Overlay": 16973830, "Top Solder": 16973834,
             "Bottom Solder": 16973835, "Bottom Overlay": 16973831, "Bottom Paste": 16973833}
DIEL_ID0 = 17039361             # dielectric layer ids are 17039361 + n
# The impedance profiles and the routing-layers rule are indexed by the old layer numbers (file
# keys "TOP LAYER_V5", "MID LAYER 1_V5", ...). A new-style id from COPPER is ignored without an
# error: every profile then had one entry on no layer (found by reading the file back, AD26).
V5_LAYER = {"L1_TOP": 1, "L2_GND": 2, "L3_SIG": 3, "L4_PWR": 4, "L5_PWR": 5, "L6_SIG": 6, "L7_GND": 7, "L8_BOT": 32}


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
# Section 8, JLCPCB calculator: width / gap in mil per routing layer. L1 and L8 are microstrip over GND
# (same geometry as the 6-layer board's L1); L3 and L6 are asymmetric stripline, 3.94 mil from GND and
# 14.64 mil from the power plane. L2, L4, L5 and L7 carry no impedance traces.
# (profile, ohms, diff, {layer: (width, gap)})
IMPEDANCE = [
    ("SE50", 50, False, {"L1_TOP": (5.94, 0), "L3_SIG": (4.83, 0), "L6_SIG": (4.83, 0), "L8_BOT": (5.94, 0)}),
    ("DIFF90", 90, True, {"L1_TOP": (5.34, 6.0), "L3_SIG": (4.65, 6.0), "L6_SIG": (4.65, 6.0), "L8_BOT": (5.34, 6.0)}),
    ("DIFF100", 100, True, {"L1_TOP": (4.69, 8.0), "L3_SIG": (4.01, 8.0), "L6_SIG": (4.01, 8.0), "L8_BOT": (4.69, 8.0)}),
]
REFS = {"L1_TOP": ("", "L2_GND"), "L3_SIG": ("L2_GND", "L4_PWR"), "L6_SIG": ("L5_PWR", "L7_GND"), "L8_BOT": ("L7_GND", "")}
IMP_TOLERANCE = 10              # percent; JLCPCB impedance control is +/-10 %
TMDS_W_MIL, TMDS_GAP_MIL = next(p[3]["L1_TOP"] for p in IMPEDANCE if p[0] == "DIFF100")   # 4.69 / 8.0 mil


def impedance_spec(pcb: Path) -> str:
    ids = V5_LAYER
    lines = [str(pcb)]
    for name, ohms, diff, layers in IMPEDANCE:
        lines.append(f"IMP|{name}|{ohms}|{int(diff)}|{IMP_TOLERANCE}")
        for lname, (w, g) in layers.items():
            top, bot = REFS[lname]
            outer = lname in ("L1_TOP", "L8_BOT")      # solder mask over the trace and between
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
                     r"|WL_SDIO_(CLK|CMD|D\d)|DPI_.*|TFP_IDCK|OSC_25M|OSC25M_SRC"
                     r"|AUD_MCLK|AUD_MCLK_OSC)$")

# ---- High-speed interfaces: limits are in the constraint table, README section 11.
# class: (load part, [(net at the SiP, net at the load), ...]). The two names differ
# where a series part sits in between, which is why these are xSignals, not nets.
_DPI = [(f"DPI_D{i}", f"DPI_D{i}") for i in range(24)] + [("DPI_DE", "DPI_DE"), ("DPI_HSYNC", "DPI_HSYNC"),
                                                         ("DPI_VSYNC", "DPI_VSYNC"), ("DPI_PCLK", "TFP_IDCK")]
BUSES = {
    "RGMII_TX": ("U800", [(f"ETH_TD{i}", f"PHY_TX_D{i}") for i in range(4)]
                 + [("ETH_TXC", "PHY_GTX_CLK"), ("ETH_TX_CTL", "PHY_TX_CTRL")]),
    "RGMII_RX": ("U800", [(f"ETH_RD{i}", f"PHY_RX_D{i}") for i in range(4)]
                 + [("ETH_RXC", "PHY_RX_CLK"), ("ETH_RX_CTL", "PHY_RX_CTRL")]),
    "MMC0": ("J700", [("EMMC_CLK", "EMMC_MOD_CLK"), ("EMMC_CMD", "EMMC_CMD")]
             + [(f"EMMC_D{i}", f"EMMC_D{i}") for i in range(8)]),
    # SD_CLK and the SDIO nets lost their 0R series links on 2026-11-10, so each is one net end to end
    "MMC1": ("J702", [("SD_CLK", "SD_CLK"), ("SD_CMD", "SD_CMD")] + [(f"SD_D{i}", f"SD_D{i}") for i in range(4)]),
    "MMC2": ("J1300", [(f"WL_SDIO_{s}", f"WL_SDIO_{s}") for s in ("CLK", "CMD", "D0", "D1", "D2", "D3")]),
    "DPI": ("U1000", _DPI),
}
MCASP_NETS = ["AUD_BCLK", "AUD_FSYNC", "AUD_DIN", "AUD_DOUT"]
# Clocks and other periodic signals: differential pairs keep 50 mil from these
PERIODIC_RE = re.compile(r"^(OSC_25M|OSC25M_SRC|AUD_MCLK|AUD_MCLK_OSC|AUD_BCLK|ETH_TXC|PHY_GTX_CLK|ETH_RXC|PHY_RX_CLK"
                         r"|EMMC_CLK|EMMC_MOD_CLK|SD_CLK|WL_SDIO_CLK|DPI_PCLK|TFP_IDCK"
                         r"|PHY_X.|HUB_X.|FT_OSC.|LFOSC_.*)$")

# Propagation delay used to turn the datasheets' ps into mm. L3 stripline: sqrt(4.25) / c =
# 6.88 ps/mm, the slowest layer here, so a tolerance in ps gives the shortest (safest) mm.
# L1 microstrip is about 6.1 ps/mm (Hammerstad, 0.151 / 0.0994 mm, with solder mask; estimate).
PS_PER_MM_L3, PS_PER_MM_L1 = 6.88, 6.1


def ps_tol(ps):
    return ps / PS_PER_MM_L3


def ps_min_len(ps):
    """Shortest route that gives this delay whichever layer it is on (L1 is the fast one)."""
    return ps / PS_PER_MM_L1


def ps_max_len(ps):
    """Longest route that stays under this delay whichever layer it is on (L3 is the slow one)."""
    return ps / PS_PER_MM_L3


MIL_MM = 0.0254

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
    for bus, (_, pairs) in BUSES.items():
        classes["HS_" + bus] = sorted({n for pair in pairs for n in pair})
    classes["HS_MCASP"] = list(MCASP_NETS)
    classes["HS_CLK"] = sorted(n for n in nets if PERIODIC_RE.match(n))
    return classes


def classes_spec(pcb: Path, nets: list[str]) -> str:
    lines = [str(pcb)]
    for name, members in net_classes(nets).items():
        lines.append("NETCLASS|" + name + "|" + "|".join(members))
    for cls, pairs in DIFF_PAIRS.items():
        for pair, p, n in pairs:
            lines.append(f"DIFFPAIR|{pair}|{p}|{n}")
        lines.append("DPCLASS|" + cls + "|" + "|".join(pair for pair, _, _ in pairs))
    names = xsignal_names(pcb)
    for bus in BUSES:
        members = [names[frozenset(pins)] for pins in xsignal_pins(bus) if frozenset(pins) in names]
        if members:
            lines.append("XCLASS|" + bus + "|" + "|".join(members))
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------- xSignals
def _netlist() -> dict:
    """{net: [REF.PIN, ...]} from out/netlist.csv (build.py check writes it)."""
    import csv
    nets = {}
    with open(Path(__file__).resolve().parent / "out" / "netlist.csv", newline="") as f:
        for r in csv.DictReader(f):
            nets[r["net"]] = r["nodes"].split()
    return nets


def _pin_on(nets, net, ref):
    pins = [nd for nd in nets[net] if nd.split(".", 1)[0] == ref]
    if not pins:
        raise ValueError(f"net {net} has no pin on {ref}")
    return pins[0].replace(".", "-", 1)


def xsignal_pins(bus, nets=None):
    """[(SiP pin, load pin), ...] as Altium pin descriptors, for one bus."""
    nets = nets or _netlist()
    load, pairs = BUSES[bus]
    return [(_pin_on(nets, a, "U1"), _pin_on(nets, b, load)) for a, b in pairs]


class _PinSets(dict):
    """xSignal names by pin set. Altium writes either the two end pins or, after some saves, every pin along the
    path (series parts too, e.g. R802-1,R802-2,U1-U25,U800-28), so a lookup by the two end pins also finds a
    record that holds them."""
    def _find(self, pins):
        pins = frozenset(pins)
        if dict.__contains__(self, pins):
            return dict.__getitem__(self, pins)
        return next((v for k, v in self.items() if pins <= k), None)

    def __getitem__(self, pins):
        v = self._find(pins)
        if v is None:
            raise KeyError(pins)
        return v

    def __contains__(self, pins):
        return self._find(pins) is not None

    def get(self, pins, default=None):
        v = self._find(pins)
        return default if v is None else v


def xsignal_names(pcb: Path) -> dict:
    """{frozenset of pin descriptors: xSignal name} read back from the PcbDoc's Board6."""
    b6 = read_board6(pcb)
    out = _PinSets()
    for i in range(int(b6.get("PINPAIRCOUNT", 0))):
        pins = b6.get(f"PINPAIRPINS{i}", "")
        out[frozenset(pins.split(","))] = b6.get(f"PINPAIRNAME{i}", "")
    return out


def xsignals_spec(pcb: Path) -> str:
    """The xSignals not yet in the PcbDoc, so the step can be re-run."""
    have = xsignal_names(pcb)
    lines = [str(pcb)]
    for bus in BUSES:
        for a, b in xsignal_pins(bus):
            if frozenset((a, b)) not in have:
                lines.append(f"XS|{a}|{b}")
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
# body plus 1 mm for the fan-out vias on every side, around U1 as placed by
# placement.py (zero orientation: 14 mm along x), with 0.3 mm more so that it holds
# the whole footprint, pin-1 dot and courtyard included (else a confinement violation).
ROOM_W_MM, ROOM_H_MM = 16.6, 11.6
SIP_ROOM = "U1_SiP"
SIP = f"WithinRoom('{SIP_ROOM}')"
# Where the high-speed pairs fan out from 0.5 mm balls to their 30 mil spacing: the SiP room plus this much on every side.
# Pairs side by side need 1.20 mm centre to centre, against 0.50 mm at the balls, which takes about 2 mm of run at 45 degrees.
ESCAPE_ROOM = "U1_Escape"
ESCAPE_MM = 3.0
# HDMI from U1000's TMDS pins to J1000's: all of it is package escape or connector termination, where TI
# lifts the 30 mil (SPRAAR7J §3.3, §3.4). U1000's break-out may run 0.25 in (6.35 mm) and reaches under
# U1001, the connector's ESD part, and the pairs pass U1001's 0.65 mm pads and J1000's 0.5 mm pins with no
# GND between neighbours. Board mm, drawn round U1000 at (77.0, 40.0), U1001 and J1000 at (105.3, 36.95) as
# placed by hand on 2026-11-09: their TMDS pads and the routes over and under U1001's ends. Move it with them.
HDMI_ROOM = "HDMI_Escape"
HDMI_ROOM_MM = (81.9, 32.9, 101.5, 46.75)       # x1, y1, x2, y2
# MDI at U800's 0.5 mm pins: each MDI pin sits next to a power or bias pin (VDDA_2V5 on 3 and 9, VDD_1V0 on 6,
# RBIAS on 12) whose track is 0.3-0.4 mm away, so the 30 mil stops every pair 0.5 mm short of the PHY. Pair to
# pair is 1.0 mm there and meets 30 mil. Package escape (SPRAAR7J §3.4): U800's body, at (69.2, 25.3) as placed
# on 2026-11-09, plus 2 mm on every side (1.8 mm past the MDI pins' outer ends). Move it with U800.
ETH_ROOM = "U800_Escape"
ETH_ROOM_MM = (63.7, 19.8, 74.7, 30.8)
# Debug USB-C, connector termination: CC1 (A5) sits 0.5 mm from DBG_USB_DM (B7), so no CC1 track could leave its pin.
# J1500 at (3.19, 60.0) as placed on 2026-11-09, its pins plus 2 mm, and up to R1500 (CC1's Rd). Move it with J1500.
USBDBG_ROOM = "J1500_Escape"
USBDBG_ROOM_MM = (-2.0, 54.5, 9.5, 67.5)
# Hub escape: U900's 0.4 mm pins put USB1_DM (pin 20) 0.4 mm from the VCC_3V3_SYS link on pins 18-19, and HUB_P1 / HUB_P2
# 0.63 mm apart at the corner (pins 7, 8). U900 at (45.5, 20.0) as placed on 2026-11-09, plus 2 mm. Move it with U900.
HUB_ROOM = "U900_Escape"
HUB_ROOM_MM = (41.5, 16.0, 49.5, 24.0)
# name, part it must hold, board mm box, pair class it relaxes, Clearance rule, what it is for
PART_ROOMS = [
    (HDMI_ROOM, "U1001", HDMI_ROOM_MM, "HDMI_TMDS", "Clr_HDMI_Escape",
     "HDMI escape and connector termination (gen/pcbsetup.py); move it with U1000, U1001, J1000"),
    (ETH_ROOM, "U800", ETH_ROOM_MM, "ETH_MDI", "Clr_ETH_Escape", "MDI escape at the PHY (gen/pcbsetup.py); move it with U800"),
    (USBDBG_ROOM, "J1500", USBDBG_ROOM_MM, "USB_DBG", "Clr_USBDBG_Escape",
     "Debug USB-C termination (gen/pcbsetup.py); move it with J1500"),
    (HUB_ROOM, "U900", HUB_ROOM_MM, "USB1", "Clr_USB1_Escape", "USB hub escape (gen/pcbsetup.py); move it with U900"),
]


def room_spec(name=SIP_ROOM, grow=0.0) -> str:
    cx, cy = BOARD_X0 + mm(placement.U1_XY[0]), BOARD_Y0 + mm(placement.U1_XY[1])
    return (f"ROOM|{name}|InComponent('U1')|{cx - mm(ROOM_W_MM / 2 + grow)}|{cy - mm(ROOM_H_MM / 2 + grow)}"
            f"|{cx + mm(ROOM_W_MM / 2 + grow)}|{cy + mm(ROOM_H_MM / 2 + grow)}")


def part_room_specs() -> list[str]:
    return [f"ROOM|{name}|InComponent('{part}')|{BOARD_X0 + mm(x1)}|{BOARD_Y0 + mm(y1)}|{BOARD_X0 + mm(x2)}"
            f"|{BOARD_Y0 + mm(y2)}|{note}" for name, part, (x1, y1, x2, y2), _, _, note in PART_ROOMS]


def part_room_rules() -> list[list]:
    """0.10 mm between a pair of that class and any track, ahead of the 30 mil rules, when either track is wholly
    inside the room: the pair's (first rule) or the other one (second). A long pair segment leaving the room then
    no longer holds a short track at a neighbouring pin to 30 mil."""
    rows = []
    for name, _, _, cls, rule, _ in PART_ROOMS:
        pair = f"InDifferentialPairClass('{cls}') And IsTrack"
        rows.append(["CLEARANCE", rule, f"WithinRoom('{name}') And {pair}", "IsTrack", mm(0.10)])
        rows.append(["CLEARANCE", f"{rule}_Other", f"WithinRoom('{name}') And IsTrack", pair, mm(0.10)])
    return rows


# ------------------------------------------------------------------ rules
def _or(fn, names):
    return " Or ".join(f"{fn}('{n}')" for n in names)


def _per_layer(profile: str) -> str:
    """'layer:width:gap;...' for every copper layer from an impedance profile;
    the plane layers L2 / L4 / L5 take the L3 stripline values."""
    widths = next(layers for name, _, _, layers in IMPEDANCE if name == profile)
    return ";".join(f"{V5_LAYER[name]}:{mil(widths.get(name, widths['L3_SIG'])[0])}"
                    f":{mil(widths.get(name, widths['L3_SIG'])[1])}" for name, *_ in COPPER)


def _dp_classes(names):
    return "(" + " Or ".join(f"InDifferentialPairClass('{n}')" for n in names) + ")"


V5_KEY = {"L1_TOP": "TOP LAYER_V5", "L2_GND": "MID LAYER 1_V5", "L3_SIG": "MID LAYER 2_V5",
          "L4_PWR": "MID LAYER 3_V5", "L5_PWR": "MID LAYER 4_V5", "L6_SIG": "MID LAYER 5_V5",
          "L7_GND": "MID LAYER 6_V5", "L8_BOT": "BOTTOM LAYER_V5"}


def _layers(*allowed):
    """Old layer number:0 or 1 for every copper layer."""
    return ";".join(f"{V5_LAYER[name]}:{int(name in allowed)}" for name, *_ in COPPER)


def hs_clearance_rules() -> list[list]:
    """TI SPRAAR7J Table A-7 (AM62x): differential pair to a clock or periodic signal 50 mil, to any
    other signal 30 mil; section 3.4 applies the 30 mil between pairs too. Track to track only, so that
    pads at a connector or IC pin don't count: TI scopes this "after package escape and before connector
    termination". One rule per pair, so that the pair's own two nets are exempt. GND tracks are exempt
    too: the spacing is from other signals, and a GND stub beside a connector pin isn't one. The SiP room's
    higher-priority rule still applies inside the room, and Clr_HS_Escape gives way to these only past
    the escape room. A track crossing that room's edge counts as outside it unless the other track is
    wholly inside, so end a fan-out segment before the edge if two pairs leave it close together."""
    all_dp = _dp_classes(DIFF_PAIRS)
    rows = [["CLEARANCE", "Clr_HS_DP_Periodic", f"InNetClass('HS_CLK') And IsTrack", f"{all_dp} And IsTrack", mm(50 * MIL_MM)]]
    for pairs in DIFF_PAIRS.values():
        for pair, _, _ in pairs:
            rows.append(["CLEARANCE", f"Clr_HS_{pair}", f"InDifferentialPair('{pair}') And IsTrack",
                         f"(Not InDifferentialPair('{pair}')) And IsTrack And (Not InNet('GND'))", mm(30 * MIL_MM)])
    return rows


# All four signal layers reference GND at 0.1 mm, so any of them may carry a high-speed route
SIGNAL_LAYERS = ("L1_TOP", "L3_SIG", "L6_SIG", "L8_BOT")


def length_rules(pcb: Path) -> list[list]:
    """Matched-length, length, via-count and layer rules. README section 11 has the source of each."""
    names = xsignal_names(pcb)

    def xs(bus, picks=None):
        """Scope for a bus, or for the pairs of a bus whose SiP net is in ``picks``."""
        if picks is None:
            return f"InxSignalClass('{bus}')"
        nets = _netlist()
        out = []
        for a, b in BUSES[bus][1]:
            if a in picks:
                pins = frozenset((_pin_on(nets, a, "U1"), _pin_on(nets, b, BUSES[bus][0])))
                out.append(f"InxSignal('{names[pins]}')")
        return " Or ".join(out)

    txd = [f"ETH_TD{i}" for i in range(4)]
    rxd = [f"ETH_RD{i}" for i in range(4)]
    return [
        # matched lengths: kind, name, scope, "", tolerance, nets within a pair, pair against pair
        ["MATCHED", "M_RGMII_TXD", xs("RGMII_TX", txd), "", mm(60 * MIL_MM), 0, 0],
        ["MATCHED", "M_RGMII_RXD", xs("RGMII_RX", rxd), "", mm(60 * MIL_MM), 0, 0],
        ["MATCHED", "M_RGMII_TX", xs("RGMII_TX"), "", mm(ps_tol(50)), 0, 0],
        ["MATCHED", "M_RGMII_RX", xs("RGMII_RX"), "", mm(ps_tol(50)), 0, 0],
        ["MATCHED", "M_MMC0", xs("MMC0"), "", mm(ps_tol(8)), 0, 0],
        ["MATCHED", "M_MMC1", xs("MMC1"), "", mm(ps_tol(8)), 0, 0],
        ["MATCHED", "M_MMC2", xs("MMC2"), "", mm(ps_tol(8)), 0, 0],
        ["MATCHED", "M_DPI", xs("DPI"), "", mm(ps_tol(100)), 0, 0],
        ["MATCHED", "M_MCASP", "InNetClass('HS_MCASP')", "", mm(ps_tol(100)), 0, 0],
        # within a pair. USB0 and the hub's downstream ports pass a common-mode choke, so each pair
        # gets half of TI's 50 mil for each of its two segments.
        ["MATCHED", "M_USB0_Pair", "InDifferentialPairClass('USB0')", "", mm(25 * MIL_MM), 1, 0],
        ["MATCHED", "M_USB1_Pair", "InDifferentialPairClass('USB1')", "", mm(25 * MIL_MM), 1, 0],
        ["MATCHED", "M_USB_DBG_Pair", "InDifferentialPairClass('USB_DBG')", "", mm(50 * MIL_MM), 1, 0],
        ["MATCHED", "M_CSI_Pair", "InDifferentialPairClass('CSI')", "", mm(ps_tol(8)), 1, 0],
        ["MATCHED", "M_CSI_Lanes", "InDifferentialPairClass('CSI')", "", mm(ps_tol(40)), 0, 1],
        ["MATCHED", "M_TMDS_Pair", "InDifferentialPairClass('HDMI_TMDS')", "", mm(5 * MIL_MM), 1, 0],
        # length limits: kind, name, scope, "", min, max
        ["LENGTH", "L_RGMII", f"{xs('RGMII_TX')} Or {xs('RGMII_RX')}", "", 0, mm(2 * 25.4)],
        ["LENGTH", "L_MMC0", xs("MMC0"), "", mm(ps_min_len(126) - 10.0), mm(40.0)],
        ["LENGTH", "L_MMC1", xs("MMC1"), "", mm(ps_min_len(126)), mm(ps_max_len(1386))],
        ["LENGTH", "L_MMC2", xs("MMC2"), "", 0, mm(ps_max_len(1386))],
        ["LENGTH", "L_DPI", xs("DPI"), "", 0, mm(2.8 * 25.4)],
        ["LENGTH", "L_MCASP", "InNetClass('HS_MCASP')", "", mm(ps_min_len(100)), mm(ps_max_len(1100))],
        ["LENGTH", "L_USB", _dp_classes(("USB0", "USB1", "USB_DBG")), "", 0, mm(12000 * MIL_MM)],
        ["LENGTH", "L_CSI", "InDifferentialPairClass('CSI')", "", 0, mm(10 * 25.4)],
        ["LENGTH", "L_TMDS", "InDifferentialPairClass('HDMI_TMDS')", "", 0, mm(2 * 25.4)],
        # vias per net. TI allows 4 per USB 2.0 trace end to end; the split pairs get 2 per segment.
        ["VIACOUNT", "V_TMDS", "InDifferentialPairClass('HDMI_TMDS')", "", 0],
        ["VIACOUNT", "V_MDI", "InDifferentialPairClass('ETH_MDI')", "", 1],
        ["VIACOUNT", "V_CSI", "InDifferentialPairClass('CSI')", "", 2],
        ["VIACOUNT", "V_USB_Split", _dp_classes(("USB0", "USB1")), "", 2],
        ["VIACOUNT", "V_USB_DBG", "InDifferentialPairClass('USB_DBG')", "", 4],
        # layers: L2, L4, L5 and L7 are planes, so no impedance route goes there
        ["LAYERS", "RL_TMDS", "InDifferentialPairClass('HDMI_TMDS')", "", _layers("L1_TOP")],
        ["LAYERS", "RL_MDI_CSI", _dp_classes(("ETH_MDI", "CSI")), "", _layers(*SIGNAL_LAYERS)],
        ["LAYERS", "RL_RGMII", "InNetClass('HS_RGMII_TX') Or InNetClass('HS_RGMII_RX')", "",
         _layers(*SIGNAL_LAYERS)],
        ["LAYERS", "RL_SE50_USB", "InNetClass('SE50') Or " + _dp_classes(("USB0", "USB1", "USB_DBG")), "",
         _layers(*SIGNAL_LAYERS)],
        ["LAYERS", "RoutingLayers", "All", "", _layers(*[name for name, *_ in COPPER])],
    ]


def rules(pcb: Path = None) -> list[list]:
    """One list per rule: kind, name, scope1, scope2, values...; the order
    within a kind is the priority (first = highest). The template's polygon
    connect rules (relief 4 x 10 mil spokes, 10 mil gap; vias direct) already
    match section 5 and are kept."""
    inner = "(OnLayer('L2_GND') Or OnLayer('L4_PWR') Or OnLayer('L5_PWR') Or OnLayer('L7_GND'))"
    paste_query = footprints.paste_rule_query(footprints.all_footprints())
    dp90, dp100 = _or("InDifferentialPairClass", DP_90R), _or("InDifferentialPairClass", DP_100R)
    se50 = ";".join(v.rsplit(":", 1)[0] for v in _per_layer("SE50").split(";"))
    return [
        # clearance: inner-layer pours 0.20 mm from holes (also under the SiP:
        # the 0.55 mm anti-pad of section 4), 0.09 mm (3.5 mil) in the SiP
        # fan-out, SMD pads 0.15 mm, 0.10 mm elsewhere
        # SiP vias: pad 0.25 mm plus 0.15 mm is JLC's 0.20 mm from the 0.15 mm drill, the 0.55 mm anti-pad
        ["CLEARANCE", "Clr_InnerPour_SiPVia", f"InPolygon And {inner}", "IsVia And WithinRoom('U1_SiP')", mm(0.15)],
        ["CLEARANCE", "Clr_InnerPour_Hole", f"InPolygon And {inner}", "IsVia Or IsPad", mm(0.20)],
        ["CLEARANCE", "Clr_SiP", SIP, "All", mm(0.09)],
        # Ahead of the 30 mil rules: TI scopes those "after package escape". Track to track, as they are.
        ["CLEARANCE", "Clr_HS_Escape", f"WithinRoom('{ESCAPE_ROOM}') And IsTrack", "IsTrack", mm(0.10)],
        *part_room_rules(),
        *hs_clearance_rules(),
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
        # TMDS is L1 only (RL_TMDS) with no neck-down, so its width is pinned to the L1 100 ohm value: with
        # DP_100R's 0.09-0.13 mm the router took whichever end the routing width mode gave (0.09 mm is about 113 ohm).
        ["DIFFPAIR", "DP_100R_TMDS", "InDifferentialPairClass('HDMI_TMDS')", "", mil(TMDS_W_MIL), mil(TMDS_W_MIL),
         mm(0.09), mm(0.25), mm(5.0), "", ";".join(f"{V5_LAYER[n]}:{mil(TMDS_W_MIL)}:{mil(TMDS_GAP_MIL)}" for n, *_ in COPPER)],
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
        # Vias tented on both sides. IsTenting_Top and _Bottom don't stick when set by script on AD26, and an opening
        # beside every pad would break the mask sliver rule. Past the largest via's radius there is no opening.
        ["MASK", "Mask_Via", "IsVia", "", -mm(0.30)],
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
        *length_rules(pcb),
    ]


def rules_spec(pcb: Path) -> str:
    lines = [str(pcb), room_spec(), room_spec(ESCAPE_ROOM, ESCAPE_MM), *part_room_specs()]
    for rule in rules(pcb):
        lines.append("RULE|" + "|".join(str(v) for v in rule))
    return "\n".join(lines) + "\n"


# -------------------------------------------------------- read-back from the file
def read_rules(pcb: Path) -> list[dict]:
    """Every record of the PcbDoc's Rules6 stream."""
    import olefile
    import struct
    with olefile.OleFileIO(str(pcb)) as ole:
        raw = ole.openstream("Rules6/Data").read()
    out, pos = [], 0
    while pos + 6 <= len(raw):
        n = struct.unpack_from("<I", raw, pos + 2)[0]
        rec = raw[pos + 6:pos + 6 + n].decode("latin-1").rstrip("\x00")
        pos += 6 + n
        out.append(dict(x.split("=", 1) for x in rec.split("|") if "=" in x))
    return out


def read_classes(pcb: Path) -> dict:
    """{(stream kind, class name): [members]} from Classes6 and SignalClasses."""
    import olefile
    import struct
    out = {}
    with olefile.OleFileIO(str(pcb)) as ole:
        for st in ("Classes6/Data", "SignalClasses/Data"):
            raw = ole.openstream(st).read()
            pos = 0
            while pos + 4 <= len(raw):
                n = struct.unpack_from("<I", raw, pos)[0]
                rec = raw[pos + 4:pos + 4 + n].decode("latin-1").rstrip("\x00")
                pos += 4 + n
                d = dict(x.split("=", 1) for x in rec.split("|") if "=" in x)
                members = [v for k, v in d.items() if re.fullmatch(r"M\d+", k)]
                out[(d.get("KIND"), d.get("NAME"))] = members
    return out


def read_drc_report(pcb: Path) -> list:
    """(count, rule) for every rule with hits, from the HTML report beside the project."""
    import html
    report = pcb.parent / "Project Outputs for APE - Single Board Computer" / "Design Rule Check - PCB.html"
    text = re.sub(r"<[^>]+>", " ", report.read_text(encoding="utf-8", errors="replace"))
    text = re.sub(r"\s+", " ", html.unescape(text))
    i = text.find("Rule Violations Count")
    j = text.find("Total", i)
    return [(int(c), r.strip()[:110]) for r, c in re.findall(r"(.+?\))\s+(\d+)(?=\s)", text[i + 21:j + 1]) if int(c)]


def read_violations(pcb: Path) -> dict:
    """{violation stream: count} after a DRC, from the T*Violation streams in the file."""
    import olefile
    import struct
    out = {}
    with olefile.OleFileIO(str(pcb)) as ole:
        for st in ole.listdir():
            if st[0].endswith("Violation") and st[-1] == "Data":
                raw = ole.openstream(st).read()
                h = "/".join(st[:-1]) + "/Header"
                count = struct.unpack("<I", ole.openstream(h).read()[:4])[0] if ole.exists(h) else None
                out[st[0]] = (count, len(raw))
    return out


def press_drc_dialog(stop_at=100000, timeout=120):
    """PCB:DesignRuleCheck opens its dialog whatever the parameters say. Raise "Stop when N violations
    found" (500 by default, and the unrouted nets alone pass that), then press Run."""
    import ctypes
    import ctypes.wintypes as wt
    import time
    import build
    user32 = ctypes.windll.user32
    start = time.time()
    while time.time() - start < timeout:
        found = build.x2_windows("Design Rule Checker")
        if found:
            break
        time.sleep(1)
    else:
        return
    dlg = found[0]
    time.sleep(1)
    spin = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        cls = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(h, cls, 64)
        if cls.value == "TXPSpinEdit":
            spin.append(h)
        return True

    user32.EnumChildWindows(dlg, cb, 0)
    user32.SendMessageW(spin[0], 0x000C, 0, ctypes.c_wchar_p(str(stop_at)))     # WM_SETTEXT
    button = build.dialog_buttons(dlg)["Run Design Rule Check..."]
    user32.PostMessageW(user32.GetParent(button), 0x0111, user32.GetDlgCtrlID(button) & 0xFFFF, button)


def _mil(text):
    return float(text.replace("mil", ""))


def verify(pcb: Path, nets: list[str]) -> list[str]:
    """Compare the saved PcbDoc with this file; returns the differences."""
    problems = []
    b6 = read_board6(pcb)
    # ---- stack
    names = {}
    for k, v in b6.items():
        m = re.fullmatch(r"V9_STACK_LAYER(\d+)_NAME", k)
        if m:
            names[int(m.group(1))] = v
    order = [names[i] for i in sorted(names)]
    want = [row[0] for row in stack_layers()]
    if order != want:
        problems.append(f"stack order {order} != {want}")
    for i, (name, lid, kind, p) in enumerate(stack_layers()):
        pre = f"V9_STACK_LAYER{i}_"
        if b6.get(pre + "LAYERID") != str(lid):
            problems.append(f"{name}: layer id {b6.get(pre + 'LAYERID')} != {lid}")
        if kind == "copper" and abs(_mil(b6.get(pre + "COPTHICK", "0mil")) - p["cu"]) > 0.01:
            problems.append(f"{name}: copper {b6.get(pre + 'COPTHICK')} != {p['cu']}")
        if kind == "diel":
            if abs(_mil(b6.get(pre + "DIELHEIGHT", "0mil")) - p["h_mil"]) > 0.01:
                problems.append(f"{name}: height {b6.get(pre + 'DIELHEIGHT')} != {p['h_mil']:.4f}")
            if abs(float(b6.get(pre + "DIELCONST", 0)) - p["dk"]) > 0.001:
                problems.append(f"{name}: Dk {b6.get(pre + 'DIELCONST')} != {p['dk']}")
    # ---- impedance profiles, per layer
    profile = {}
    for k, v in b6.items():
        m = re.fullmatch(r"V9_IMPEDANCEPROFILE(\d+)_NAME", k)
        if m:
            profile[b6[f"V9_IMPEDANCEPROFILE{m.group(1)}_ID"]] = v
    traces = {}
    i = 0
    while f"V9_TRACEIMPEDANCE{i}_PROFILE_ID" in b6:
        pre = f"V9_TRACEIMPEDANCE{i}_"
        traces[(profile.get(b6[pre + "PROFILE_ID"]), b6[pre + "LAYER_V7ID"])] = {
            k[len(pre):]: v for k, v in b6.items() if k.startswith(pre)}
        i += 1
    ids = {name: str(lid) for name, lid, *_ in COPPER}
    enabled = {k: [lay for (pn, lay), rec in traces.items() if pn == k and rec.get("ENABLED") == "TRUE"]
               for k in profile.values()}
    for name, ohms, diff, layers in IMPEDANCE:
        if len(enabled.get(name, [])) != len(layers):
            problems.append(f"profile {name}: {len(enabled.get(name, []))} enabled layers, expected {len(layers)}")
        if name not in profile.values():
            problems.append(f"profile {name} is missing")
        for lname, (w, g) in layers.items():
            rec = traces.get((name, ids[lname]))
            if rec is None:
                problems.append(f"profile {name} has no entry for {lname}")
                continue
            if rec.get("ENABLED") != "TRUE":
                problems.append(f"profile {name} {lname} is not enabled")
            if abs(_mil(rec.get("TRACE_WIDTH", "0mil")) - w) > 0.02:
                problems.append(f"profile {name} {lname}: width {rec.get('TRACE_WIDTH')} != {w}")
            if diff and abs(_mil(rec.get("DIFF_PAIR_GAP", "0mil")) - g) > 0.02:
                problems.append(f"profile {name} {lname}: gap {rec.get('DIFF_PAIR_GAP')} != {g}")
            top, bot = REFS[lname]
            for key, ref in (("REF_TOP_V7ID", top), ("REF_BOT_V7ID", bot)):
                if ref and rec.get(key) != ids[ref]:
                    problems.append(f"profile {name} {lname}: {key} {rec.get(key)} != {ref}")
    # ---- classes
    cl = read_classes(pcb)
    for name, members in net_classes(nets).items():
        have = cl.get(("0", name))
        if have is None:
            problems.append(f"net class {name} is missing")
        elif set(have) != set(members):
            problems.append(f"net class {name}: missing {sorted(set(members) - set(have))[:5]}, "
                            f"extra {sorted(set(have) - set(members))[:5]}")
    for dpc, pairs in DIFF_PAIRS.items():
        have = cl.get(("6", dpc))
        if have is None or set(have) != {p for p, _, _ in pairs}:
            problems.append(f"differential-pair class {dpc}: {have}")
    xnames = xsignal_names(pcb)
    for bus in BUSES:
        want_x = {xnames.get(frozenset(pins)) for pins in xsignal_pins(bus)}
        if None in want_x:
            problems.append(f"bus {bus}: an xSignal is missing")
        if set(cl.get(("10", bus), [])) != want_x - {None}:
            problems.append(f"xSignal class {bus}: {cl.get(('10', bus))}")
    # ---- rules
    file_kind = {"CLEARANCE": "Clearance", "WIDTH": "Width", "DIFFPAIR": "DiffPairsRouting", "VIA": "RoutingVias",
                 "HOLESIZE": "HoleSize", "ANNULAR": "MinimumAnnularRing", "HOLE2HOLE": "HoleToHoleClearance",
                 "MASK": "SolderMaskExpansion", "PASTE": "PasteMaskExpansion", "SLIVER": "MinimumSolderMaskSliver",
                 "SILKMASK": "SilkToSolderMaskClearance", "OUTLINE": "BoardOutlineClearance",
                 "MATCHED": "MatchedLengths", "LENGTH": "Length", "VIACOUNT": "MaximumViaCount", "LAYERS": "RoutingLayers"}
    saved = {(r.get("RULEKIND"), r.get("NAME")): r for r in read_rules(pcb)}

    def near(rule, key, coord):
        if key not in rule or abs(_mil(rule[key]) - coord / MIL) > 0.01:
            problems.append(f"rule {rule.get('NAME')}: {key} = {rule.get(key)}, expected {coord / MIL:.3f} mil")

    last = {}
    for row in rules(pcb):
        kind, name, s1, s2 = row[0], row[1], row[2], row[3]
        r = saved.get((file_kind[kind], name))
        if r is None:
            problems.append(f"rule {name} ({kind}) is missing")
            continue
        if r.get("SCOPE1EXPRESSION") != s1:
            problems.append(f"rule {name}: scope 1 {r.get('SCOPE1EXPRESSION')!r} != {s1!r}")
        if s2 and r.get("SCOPE2EXPRESSION") != s2:
            problems.append(f"rule {name}: scope 2 {r.get('SCOPE2EXPRESSION')!r} != {s2!r}")
        pr = int(r.get("PRIORITY", 0))
        if pr <= last.get(kind, 0):
            problems.append(f"rule {name}: priority {pr} is out of order")
        last[kind] = pr
        if kind in ("CLEARANCE", "HOLE2HOLE"):
            near(r, "GAP", row[4])
        elif kind == "WIDTH":
            near(r, "MINLIMIT", row[4])
            near(r, "MAXLIMIT", row[6])
        elif kind == "MATCHED":
            near(r, "TOLERANCE", row[4])
            if row[5] and r.get("CHECKNETSINDIFFPAIR") != "TRUE":
                problems.append(f"rule {name}: does not check nets within the pair")
            if row[6] and r.get("CHECKDIFFPAIRVSDIFFPAIR") != "TRUE":
                problems.append(f"rule {name}: does not check pair against pair")
            if not row[5] and not row[6] and r.get("CHECKXSIGNALS") != "TRUE":
                problems.append(f"rule {name}: does not check xSignals")
        elif kind == "LENGTH":
            near(r, "MINLIMIT", row[4])
            near(r, "MAXLIMIT", row[5])
        elif kind == "VIACOUNT":
            if r.get("LIMIT") != str(row[4]):
                problems.append(f"rule {name}: limit {r.get('LIMIT')} != {row[4]}")
        elif kind == "LAYERS":
            on = {lname: r.get(V5_KEY[lname]) for lname in V5_KEY}
            allowed = {V5_LAYER_NAME[int(item.split(":")[0])] for item in row[4].split(";") if item.endswith(":1")}
            for lname, val in on.items():
                if (val == "TRUE") != (lname in allowed):
                    problems.append(f"rule {name}: {lname} = {val}, allowed {sorted(allowed)}")
    return problems


V5_LAYER_NAME = {v: k for k, v in V5_LAYER.items()}


if __name__ == "__main__":
    import sys
    import build
    pcb = build.PCB_PATH
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "xsignals":
        # creates the xSignals; then run `build.py pcb classes rules`, which reads their names back
        spec = xsignals_spec(pcb)
        print(len(spec.splitlines()) - 1, "xSignals to create")
        build.pcb_run("PcbXSignals", "ape_pcb_xsignals.txt", spec, timeout=300)
    elif cmd == "drc":
        import threading
        threading.Thread(target=press_drc_dialog, daemon=True).start()
        build.pcb_run("PcbDrc", "ape_pcb_report_in.txt", f"{pcb}\n", timeout=1800)
        for count, rule in read_drc_report(pcb):
            print(f"{count:6d}  {rule}")
        build.pcb_run("PcbClearMarkers", "ape_pcb_report_in.txt", f"{pcb}\n", timeout=300)
        print("markers on the board:", {k: v[0] for k, v in read_violations(pcb).items()} or "none")
    elif cmd == "verify":
        found = verify(pcb, build.pcb_nets())
        print("\n".join(found) if found else "stack, profiles, classes, pairs, xSignals and rules match this file")
    else:
        print("usage: python pcbsetup.py xsignals | verify | drc")
