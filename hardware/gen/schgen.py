"""Schematic generator for the APE SBC Altium project.

Symbols and sheets are described in Python; this module turns them into
spec files for the altium-mcp tools:

* ``create_symbols_batch``   (symbol library, ``lib/APE-SBC.SchLib``)
* ``ape_sheet_builder.pas``   (one sheet per spec, run through run_altium_script)

Drafting style: every pin gets a short wire stub ending in a net label,
power port or ground port, so connectivity is by net name (the project uses
Automatic net scope with no ports, which makes net labels global). Local
passives are placed in columns next to the part they serve.

Coordinates are mils. Symbols are drawn with origin at the top-left corner of
the body; pins sit on the left/right body edges on a 100 mil pitch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

GRID = 100
PIN_LEN_IC = 200
CHAR_W = 60          # approximate pin-name/net-label character width at 10 pt

PIN_TYPES = {
    "in": "eElectricInput", "out": "eElectricOutput", "io": "eElectricIO",
    "pwr": "eElectricPower", "pas": "eElectricPassive", "oc": "eElectricOpenCollector",
    "hiz": "eElectricHiZ",
}
# Altium pin orientation: 0 right, 1 up, 2 left, 3 down
ORIENT_NAME = {0: "eRotate0", 1: "eRotate90", 2: "eRotate180", 3: "eRotate270"}
DIR = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}

GROUND_NETS = {"GND"}
# Power-port nets: supply rails. Control signals that merely start with a rail
# prefix (VPP_EFUSE_EN, VBUS_DET, ...) stay net labels.
RAIL_RE = re.compile(r"^(?!.*_(EN|N|DIV|DET|SEL|OK|FLT|PG)$)(VCC|VDD|VBUS|VSYS|DDR4_VPP|VPP_)")


def is_rail(net: str) -> bool:
    return bool(RAIL_RE.match(net))


def overbar(name: str) -> str:
    """'nRESET' -> Altium overbar syntax for the active-low part."""
    if name.startswith("n") and len(name) > 1 and name[1].isupper():
        return "".join(c + "\\" for c in name[1:])
    if name.endswith("z") and name[:-1].isupper():
        return "".join(c + "\\" for c in name[:-1])
    return name


@dataclass
class Pin:
    number: str
    name: str
    kind: str = "io"            # key of PIN_TYPES
    side: str = "L"             # L or R
    part: int = 1               # owner part (1-based)
    length: int = PIN_LEN_IC
    x: int = 0                  # body-edge location, filled in by layout()
    y: int = 0
    orient: int = 0

    def end(self) -> tuple[int, int]:
        dx, dy = DIR[self.orient]
        return self.x + dx * self.length, self.y + dy * self.length


@dataclass
class Symbol:
    name: str
    description: str
    pins: list[Pin]
    part_count: int = 1
    graphics: list[str] = field(default_factory=list)   # explicit body; empty = auto box
    designator_prefix: str = "U"
    footprint: str = ""
    body_width: dict[int, int] = field(default_factory=dict)
    show_names: bool = True
    show_numbers: bool = True

    def layout(self) -> "Symbol":
        """Assign pin coordinates for box symbols (no explicit graphics)."""
        if self.graphics:
            return self
        for part in range(1, self.part_count + 1):
            left = [p for p in self.pins if p.part == part and p.side == "L"]
            right = [p for p in self.pins if p.part == part and p.side == "R"]
            longest = lambda ps: max((len(p.name) for p in ps), default=0)
            w = max(800, (longest(left) + longest(right)) * CHAR_W + 300)
            w = -(-w // GRID) * GRID
            self.body_width[part] = w
            rows = max(len(left), len(right))
            h = (rows + 1) * GRID
            for i, p in enumerate(left):
                if p.name:              # blank names are spacer rows
                    p.x, p.y, p.orient = 0, -GRID * (i + 1), 2
            for i, p in enumerate(right):
                if p.name:
                    p.x, p.y, p.orient = w, -GRID * (i + 1), 0
            self.graphics.append(f"rectangle|{part}|1|0|0|0|{w}|{-h}")
        self.pins = [p for p in self.pins if p.name]
        return self

    def spec_lines(self) -> list[str]:
        out = [f"SYMBOL|{self.name}|{self.description}|{self.part_count}"]
        for p in self.pins:
            owner = p.part if self.part_count > 1 else 1
            out.append("PIN|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}".format(
                p.number, overbar(p.name), PIN_TYPES[p.kind], ORIENT_NAME[p.orient],
                p.x, p.y, owner, p.length, int(self.show_names), int(self.show_numbers)))
        out += [f"GRAPHIC|{g}" for g in self.graphics]
        return out

    def pin(self, number: str) -> Pin:
        for p in self.pins:
            if p.number == number:
                return p
        raise KeyError(f"{self.name}: no pin {number}")


def box(name, description, pins, part_count=1, prefix="U", footprint=""):
    """Rectangle-body IC. ``pins``: tuples (number, name, kind, side[, part])."""
    ps = []
    for t in pins:
        num, nm, kind, side = t[:4]
        part = t[4] if len(t) > 4 else 1
        ps.append(Pin(str(num), nm, kind, side, part))
    return Symbol(name, description, ps, part_count, designator_prefix=prefix,
                  footprint=footprint).layout()


def two_pin(name, description, graphics, prefix, pin_names=("1", "2"), kind="pas", reach=200,
            body=30, footprint=""):
    """Horizontal two-terminal symbol, pin ends at x = -reach and +reach."""
    p1 = Pin("1", pin_names[0], kind, "L", 1, reach - body, -body, 0, 2)
    p2 = Pin("2", pin_names[1], kind, "R", 1, reach - body, body, 0, 0)
    return Symbol(name, description, [p1, p2], graphics=graphics, designator_prefix=prefix,
                  footprint=footprint, show_names=False, show_numbers=False)


# ---------------------------------------------------------------- sheets

@dataclass
class Placed:
    designator: str
    symbol: Symbol
    part: int
    x: int
    y: int
    nets: dict[str, str]
    comment: str = ""
    params: dict[str, str] = field(default_factory=dict)
    footprint: str = ""         # per-part footprint (generic symbols); see footprints.resolve


class Sheet:
    def __init__(self, path: str, title: str, style: int = 6):
        self.path = str(Path(path))
        self.title = title
        self.style = style            # 5=A, 6=B, 7=C, 8=D
        self.placed: list[Placed] = []
        self.notes: list[tuple[int, int, str]] = []
        self.extra: list[str] = []

    # placement --------------------------------------------------------
    def add(self, designator, symbol, x, y, nets, part=1, comment="", footprint="", **params):
        missing = [n for n in nets if n not in {p.number for p in symbol.pins}]
        if missing:
            raise KeyError(f"{designator}: unknown pins {missing}")
        self.placed.append(Placed(designator, symbol, part, x, y, dict(nets), comment, params,
                                  footprint))
        return self

    def note(self, x, y, text):
        self.notes.append((x, y, text))

    def column(self, x, y, entries, pitch=400):
        """Stack two-terminal parts vertically at x, starting at y.

        entries: (designator, symbol, net_pin1, net_pin2, comment[, params])
        """
        for i, e in enumerate(entries):
            desig, sym, n1, n2, comment = e[:5]
            params = e[5] if len(e) > 5 else {}
            self.add(desig, sym, x, y - i * pitch, {"1": n1, "2": n2}, comment=comment, **params)
        return y - len(entries) * pitch

    # emission ---------------------------------------------------------
    def pin_ends(self):
        """Predicted electrical end of every placed pin: (desig, part, num) -> (x, y, orient)."""
        ends = {}
        for pl in self.placed:
            for p in pl.symbol.pins:
                if pl.symbol.part_count > 1 and p.part != pl.part:
                    continue
                ex, ey = p.end()
                ends[(pl.designator, pl.part, p.number)] = (pl.x + ex, pl.y + ey, p.orient)
        return ends

    def spec(self, lib_path: str) -> str:
        style = self.effective_style()
        w, h = self.SHEET_SIZE[style]
        out = [f"SHEET|{self.path}", f"STYLE|{style}|{w}|{h}"]
        for pl in self.placed:
            pid = pl.part if pl.symbol.part_count > 1 else 0
            out.append(f"PART|{pl.designator}|{lib_path}|{pl.symbol.name}|{pid}|{pl.x}|{pl.y}|0|0")
            if pl.comment:
                out.append(f"COMMENT|{pl.comment}")
            if pl.footprint or pl.symbol.footprint:
                out.append(f"FOOTPRINT|{pl.footprint or pl.symbol.footprint}")
            for k, v in pl.params.items():
                out.append(f"PARAM|{k}|{v}")
        for (desig, part, num), (x, y, o) in self.pin_ends().items():
            pl = next(p for p in self.placed if p.designator == desig and p.part == part)
            net = pl.nets.get(num)
            out += self._terminate(x, y, o, net, pl.symbol)
        for x, y, t in self.notes:
            out.append(f"NOTE|{x}|{y}|* {t}")
        out += self.extra
        return "\n".join(out) + "\n"

    @staticmethod
    def _terminate(x, y, orient, net, symbol):
        if net is None:
            return []
        if net == "NC":
            return [f"NOERC|{x}|{y}"]
        dx, dy = DIR[orient]
        stub = 100 if symbol.designator_prefix in ("R", "C", "L", "FB", "D", "LED", "Y") else 200
        sx, sy = x + dx * stub, y + dy * stub
        lines = [f"WIRE|{x}|{y}|{sx}|{sy}"]
        if net in GROUND_NETS:
            # Ground symbol points along the stub. Turning the stub down would
            # land on the next pin row's stub end (100 mil pitch) and short it.
            lines.append(f"POWER|{sx}|{sy}|{orient}|5|GND|0")
        elif is_rail(net):
            lines.append(f"POWER|{sx}|{sy}|{orient}|2|{net}|1")
        else:
            just = 2 if orient == 2 else 0
            lx = x + dx * 20 if orient in (0, 2) else x
            lines.append(f"NETLABEL|{lx}|{y}|0|{just}|{net}")
        return lines

    def check_geometry(self) -> list[str]:
        """Find accidental connections: a stub end or pin end of one net lying
        on a wire of another net, or two parts' pins at the same point."""
        segs = []        # (net, x1, y1, x2, y2)
        points = []      # (net, x, y, what)
        for (desig, part, num), (x, y, o) in self.pin_ends().items():
            pl = next(p for p in self.placed if p.designator == desig and p.part == part)
            net = pl.nets.get(num)
            points.append((net or f"<unconnected {desig}.{num}>", x, y, f"{desig}.{num}"))
            for line in self._terminate(x, y, o, net, pl.symbol):
                f = line.split("|")
                if f[0] == "WIRE":
                    c = list(map(int, f[1:]))
                    for i in range(0, len(c) - 2, 2):
                        segs.append((net, c[i], c[i + 1], c[i + 2], c[i + 3]))
                    points.append((net, c[-2], c[-1], f"{desig}.{num} stub end"))
        problems = []
        for net, px, py, what in points:
            for snet, x1, y1, x2, y2 in segs:
                if snet == net:
                    continue
                if min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2) and \
                        (x1 == x2 == px or y1 == y2 == py):
                    problems.append(f"{what} ({net}) touches a wire of {snet} at ({px},{py})")
        return problems

    # Altium's ANSI sheet sizes (smaller than the paper sizes): A 9.5x7.5 in,
    # B 15x9.5, C 20x15, D 32x20, E 42x32. Verified on AD26: content placed for
    # 22x17 in came out "not completely within sheet boundaries" on C.
    SHEET_SIZE = {5: (9500, 7500), 6: (15000, 9500), 7: (20000, 15000), 8: (32000, 20000),
                  9: (42000, 32000)}

    def extent_boxes(self):
        """footprint_boxes() plus the notes' text."""
        boxes = self.footprint_boxes()
        for x, y, t in self.notes:
            boxes.append((f"note '{t[:20]}'", x, y - 20, x + (len(t) + 2) * CHAR_W, y + 120))
        return boxes

    def _fits(self, style, boxes):
        w, h = self.SHEET_SIZE[style]
        for _, x1, y1, x2, y2 in boxes:
            if x1 < 300 or y1 < 300 or x2 > w - 300 or y2 > h - 300:
                return False
            if x2 > w - 6500 and y1 < 1700:
                return False
        return True

    def effective_style(self):
        """The requested style, or the smallest larger one the content fits on."""
        boxes = self.extent_boxes()
        for style in sorted(self.SHEET_SIZE):
            if style >= self.style and self._fits(style, boxes):
                return style
        return max(self.SHEET_SIZE)

    def footprint_boxes(self):
        """Approximate drawn extent of each placed part: body, pins, stubs and
        label/port text (CHAR_W per character). Returns (label, x1, y1, x2, y2)."""
        boxes = []
        for pl in self.placed:
            pins = [p for p in pl.symbol.pins
                    if pl.symbol.part_count == 1 or p.part == pl.part]
            xs, ys = [], []
            for p in pins:
                ex, ey = p.end()
                xs += [p.x, ex]
                ys += [p.y, ey]
                net = pl.nets.get(p.number)
                if net and net != "NC":
                    stub = 100 if pl.symbol.designator_prefix in ("R", "C", "L", "FB", "D", "LED", "Y") else 200
                    reach = stub + (0 if net in GROUND_NETS else len(net) * CHAR_W + 150)
                    if net in GROUND_NETS:
                        reach += 150
                    dx, dy = DIR[p.orient]
                    xs.append(ex + dx * reach)
                    ys.append(ey + dy * reach)
            for g in pl.symbol.graphics:
                nums = [int(v) for v in g.split("|")[2:] if v.lstrip("-").isdigit()]
                if g.startswith("rectangle"):
                    xs += [nums[2], nums[4]]
                    ys += [nums[3], nums[5]]
            if not xs:
                continue
            boxes.append((f"{pl.designator}{'/' + str(pl.part) if pl.symbol.part_count > 1 else ''}",
                          pl.x + min(xs), pl.y + min(ys) - 60, pl.x + max(xs), pl.y + max(ys) + 60))
        return boxes

    def check_layout(self) -> list[str]:
        """Overlapping parts (including their label text) and parts off the sheet."""
        problems = []
        boxes = self.footprint_boxes()
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]:
                    problems.append(f"{a[0]} overlaps {b[0]}")
        style = self.effective_style()
        w, h = self.SHEET_SIZE[style]
        for lbl, x1, y1, x2, y2 in self.extent_boxes():
            if x1 < 300 or y1 < 300 or x2 > w - 300 or y2 > h - 300:
                problems.append(f"{lbl} extends off the sheet ({x1},{y1})-({x2},{y2}) on {w}x{h}")
            if x2 > w - 6500 and y1 < 1700:
                problems.append(f"{lbl} runs into the title block area")
        return problems

    def check_pin_map(self, pin_map_text: str) -> list[str]:
        """Compare Altium's measured pin ends with the predicted ones."""
        measured = {}
        for line in pin_map_text.splitlines():
            f = line.strip().split("|")
            if len(f) == 6 and f[0] == "PIN":
                measured[(f[1], int(f[2]), f[3])] = (int(f[4]), int(f[5]))
        problems = []
        for (desig, part, num), (x, y, _) in self.pin_ends().items():
            key = (desig, part if part else 0, num)
            got = measured.get((desig, part, num)) or measured.get(key)
            if got is None:
                problems.append(f"{desig}.{num}: not in pin map")
            elif got != (x, y):
                problems.append(f"{desig}.{num}: predicted {(x, y)} measured {got}")
        return problems

    def netlist(self) -> dict[str, list[str]]:
        nets: dict[str, list[str]] = {}
        for pl in self.placed:
            for num, net in pl.nets.items():
                if net != "NC":
                    nets.setdefault(net, []).append(f"{pl.designator}.{num}")
        return nets
