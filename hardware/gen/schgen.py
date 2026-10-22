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


PASSIVE_PREFIXES = ("R", "C", "L", "FB", "D", "LED", "Y")
LABEL_CHAR_W = 56     # net-label character width (measured on AD26: ~55 mil/char at the default font)
NOTE_CHAR_W = 50      # mixed-case note text (measured on AD26: ~47 mil/char)
MAX_BUS_GAP = 500     # adjacent supply/ground pins further apart than this get separate ports


def label_stub(net: str) -> int:
    """Wire length that runs under the whole net label (label starts 50 mil out)."""
    return -(-(len(net) * LABEL_CHAR_W + 100) // GRID) * GRID


def display_comment(pl) -> tuple[str, str]:
    """(comment shown on the sheet, full text for a hidden Spec parameter).
    Passives show only their value so long text does not run across bus wires."""
    c = pl.comment or ""
    if pl.symbol.designator_prefix in PASSIVE_PREFIXES and c:
        shown = c.split(" (")[0].split()[0]
        return shown, (c if c != shown else "")
    return c, ""


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
        self._dy = None
        return self

    def note(self, x, y, text):
        self.notes.append((x, y, text))
        self._dy = None

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
                ends[(pl.designator, pl.part, p.number)] = (pl.x + ex, pl.y + ey + self.dy, p.orient)
        return ends

    @property
    def dy(self) -> int:
        """Vertical shift that puts the top of the content 700 mil below the
        top border: up on a sheet larger than the layout was drawn for, down
        when the layout was drawn taller than the real sheet."""
        if getattr(self, "_dy", None) is None:
            self._dy = self._shift(self.effective_style(), self.extent_boxes())
        return self._dy

    def _shift(self, style, boxes) -> int:
        if not boxes:
            return 0
        _, h = self.SHEET_SIZE[style]
        return ((h - 700) - max(b[4] for b in boxes)) // GRID * GRID

    def spec(self, lib_path: str) -> str:
        style = self.effective_style()
        w, h = self.SHEET_SIZE[style]
        out = [f"SHEET|{self.path}", f"STYLE|{style}|{w}|{h}"]
        for pl in self.placed:
            pid = pl.part if pl.symbol.part_count > 1 else 0
            out.append(f"PART|{pl.designator}|{lib_path}|{pl.symbol.name}|{pid}|{pl.x}|{pl.y + self.dy}|0|0")
            shown, spec_text = display_comment(pl)
            if shown:
                out.append(f"COMMENT|{shown}")
            if pl.footprint or pl.symbol.footprint:
                out.append(f"FOOTPRINT|{pl.footprint or pl.symbol.footprint}")
            for k, v in pl.params.items():
                out.append(f"PARAM|{k}|{v}")
            if spec_text:
                out.append(f"PARAM|Spec|{spec_text}")
        out += self.drawing()[0]
        for x, y, t in self.notes:
            out.append(f"NOTE|{x}|{y + self.dy}|* {t}")
        out += self.extra
        return "\n".join(out) + "\n"

    # drawing ------------------------------------------------------------
    def _placed(self, desig, part):
        return next(p for p in self.placed if p.designator == desig and p.part == part)

    def body_boxes(self):
        """Drawn body of every placed part (no pins, no text): (desig, x1, y1, x2, y2)."""
        boxes = []
        for pl in self.placed:
            xs, ys = [], []
            for p in pl.symbol.pins:
                if pl.symbol.part_count == 1 or p.part == pl.part:
                    xs.append(p.x)
                    ys.append(p.y)
            for g in pl.symbol.graphics:
                f = g.split("|")
                nums = [int(v) for v in f[2:] if v.lstrip("-").isdigit()]
                if f[0] == "rectangle" and (pl.symbol.part_count == 1 or int(f[1]) == pl.part):
                    xs += [nums[2], nums[4]]
                    ys += [nums[3], nums[5]]
            if pl.symbol.designator_prefix in PASSIVE_PREFIXES:
                ys += [-60, 60]
            if xs:
                boxes.append((pl.designator, pl.x + min(xs), pl.y + self.dy + min(ys),
                              pl.x + max(xs), pl.y + self.dy + max(ys)))
        return boxes

    def side_key(self, pl, pin):
        """Pins whose wires share one length: one side of a part, or one side
        of a column of two-terminal parts (same x)."""
        dx = DIR[pin.orient][0]
        if pl.symbol.designator_prefix in PASSIVE_PREFIXES and len(pl.symbol.pins) <= 2:
            return ("column", pl.x, dx)
        return (pl.designator, pl.part, dx)

    def side_lengths(self):
        """Wire length per side: the longest any label on that side needs, so
        every wire on a side ends on the same line."""
        lengths = {}
        for pl in self.placed:
            base = 100 if pl.symbol.designator_prefix in PASSIVE_PREFIXES else 200
            for p in pl.symbol.pins:
                if pl.symbol.part_count > 1 and p.part != pl.part:
                    continue
                net = pl.nets.get(p.number)
                if net in (None, "NC"):
                    continue
                need = base if net in GROUND_NETS else max(base, label_stub(net))
                key = self.side_key(pl, p)
                lengths[key] = max(lengths.get(key, 0), need)
        return lengths

    def drawing(self):
        """Records for every pin termination, plus [(net, x1, y1, x2, y2)] wire segments.

        Conventions:
          * signal nets: a stub as long as the net label, label sitting on it;
          * ground and supply pins that are vertically adjacent on the same
            line (one side of a part, or a column of passives) share one bus
            wire and a single port - ground at the bottom pointing down, a
            supply at the top pointing up - with junctions where 3 wires meet;
          * a lone ground/supply pin gets its own port (down/up when there is room).
        """
        rec, segs = [], []

        def wire(net, x1, y1, x2, y2):
            if (x1, y1) != (x2, y2):
                rec.append(f"WIRE|{x1}|{y1}|{x2}|{y2}")
                segs.append((net, x1, y1, x2, y2))

        lengths = self.side_lengths()
        pins = []
        for (desig, part, num), (x, y, o) in self.pin_ends().items():
            pl = self._placed(desig, part)
            net = pl.nets.get(num)
            if net is None:
                continue
            if net == "NC":
                rec.append(f"NOERC|{x}|{y}")
                continue
            if o not in (0, 2):
                raise ValueError(f"{desig}.{num}: vertical pins are not supported by the drawing")
            length = lengths[self.side_key(pl, pl.symbol.pin(num))]
            pins.append({"net": net, "x": x, "y": y, "dx": DIR[o][0], "o": o, "base": length})

        # occupancy for the bus checks: every horizontal stub, every body
        spans = []
        port_pins = []
        for p in pins:
            if p["net"] in GROUND_NETS or is_rail(p["net"]):
                p["sx"] = p["x"] + p["dx"] * p["base"]
                port_pins.append(p)
                spans.append((p["y"], min(p["x"], p["sx"]), max(p["x"], p["sx"]), p["net"]))
            else:
                ex = p["x"] + p["dx"] * p["base"]
                wire(p["net"], p["x"], p["y"], ex, p["y"])
                just = 0 if p["dx"] > 0 else 2
                rec.append(f"NETLABEL|{p['x'] + p['dx'] * 50}|{p['y']}|0|{just}|{p['net']}")
                spans.append((p["y"], min(p["x"], ex), max(p["x"], ex), p["net"]))
        bodies = self.body_boxes()

        def clear(x, ylo, yhi, net):
            """No other net's stub and no body on the vertical line x, ylo < y < yhi."""
            for y, x1, x2, n in spans:
                if n != net and ylo < y < yhi and x1 <= x <= x2:
                    return False
            for _, bx1, by1, bx2, by2 in bodies:
                if bx1 <= x <= bx2 and by1 < yhi and ylo < by2:
                    return False
            return True

        pin_pts = [(x, y, self._placed(d, pt).nets.get(n)) for (d, pt, n), (x, y, _) in self.pin_ends().items()]

        def clear_row(y, xa, xb, net):
            """No other net's stub, pin end or body on the horizontal line y, xa..xb."""
            lo, hi = min(xa, xb), max(xa, xb)
            for yy, x1, x2, n in spans:
                if n != net and yy == y and x1 <= hi and lo <= x2:
                    return False
            for px, py, n in pin_pts:
                if n != net and py == y and lo <= px <= hi:
                    return False
            for _, bx1, by1, bx2, by2 in bodies:
                if by1 <= y <= by2 and bx1 <= hi and lo <= bx2:
                    return False
            return True

        groups = {}
        for p in port_pins:
            groups.setdefault((p["net"], p["o"], p["sx"]), []).append(p)
        for (net, o, sx), members in groups.items():
            members.sort(key=lambda p: -p["y"])
            runs = [[members[0]]]
            for p in members[1:]:
                prev = runs[-1][-1]
                if prev["y"] - p["y"] <= MAX_BUS_GAP and clear(sx, p["y"], prev["y"], net):
                    runs[-1].append(p)
                else:
                    runs.append([p])
            ground = net in GROUND_NETS
            for run in runs:
                if not ground and len(run) == 1:
                    # a lone supply pin: a label on its stub, like a signal
                    p = run[0]
                    wire(net, p["x"], p["y"], sx, p["y"])
                    rec.append(f"NETLABEL|{p['x'] + p['dx'] * 50}|{p['y']}|0|{0 if p['dx'] > 0 else 2}|{net}")
                    continue
                for p in run:
                    wire(net, p["x"], p["y"], sx, p["y"])
                for a, b in zip(run, run[1:]):
                    wire(net, sx, a["y"], sx, b["y"])
                end = run[-1] if ground else run[0]
                if ground:
                    room = clear(sx, end["y"] - 300, end["y"], net)
                    if room:
                        wire(net, sx, end["y"], sx, end["y"] - 100)
                        rec.append(f"POWER|{sx}|{end['y'] - 100}|3|5|GND|0")
                    else:
                        rec.append(f"POWER|{sx}|{end['y']}|{o}|5|GND|0")
                elif clear(sx, end["y"], end["y"] + 500, net):
                    wire(net, sx, end["y"], sx, end["y"] + 100)
                    rec.append(f"POWER|{sx}|{end['y'] + 100}|1|2|{net}|1")
                else:
                    # no room above the run: label the top member's own stub
                    rec.append(f"NETLABEL|{end['x'] + end['dx'] * 50}|{end['y']}|0|{0 if end['dx'] > 0 else 2}|{net}")

        # junction wherever three or more wire ends meet
        ends = {}
        for _, x1, y1, x2, y2 in segs:
            for pt in ((x1, y1), (x2, y2)):
                ends[pt] = ends.get(pt, 0) + 1
        for (x, y), n in sorted(ends.items()):
            if n >= 3:
                rec.append(f"JUNCTION|{x}|{y}")
        return rec, segs

    def check_geometry(self) -> list[str]:
        """Accidental connections and crossings in the drawing: a wire end or
        pin end of one net touching a wire of another net, or two wires of
        different nets crossing."""
        _, segs = self.drawing()
        points = [(n, x1, y1) for n, x1, y1, _, _ in segs] + [(n, x2, y2) for n, _, _, x2, y2 in segs]
        for (desig, part, num), (x, y, _) in self.pin_ends().items():
            net = self._placed(desig, part).nets.get(num)
            points.append((net if net not in (None, "NC") else f"<{desig}.{num}>", x, y))
        problems = []
        for net, px, py in points:
            for snet, x1, y1, x2, y2 in segs:
                if snet != net and min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2) \
                        and (x1 == x2 == px or y1 == y2 == py):
                    problems.append(f"{net} at ({px},{py}) touches a wire of {snet}")
        hor = [s for s in segs if s[2] == s[4]]
        ver = [s for s in segs if s[1] == s[3]]
        for hn, hx1, hy, hx2, _ in hor:
            for vn, vx, vy1, _, vy2 in ver:
                if hn != vn and min(hx1, hx2) < vx < max(hx1, hx2) and min(vy1, vy2) < hy < max(vy1, vy2):
                    problems.append(f"wire of {hn} crosses wire of {vn} at ({vx},{hy})")
        return sorted(set(problems))

    # Altium's ANSI sheet sizes (smaller than the paper sizes): A 9.5x7.5 in,
    # B 15x9.5, C 20x15, D 32x20, E 42x32. Verified on AD26: content placed for
    # 22x17 in came out "not completely within sheet boundaries" on C.
    SHEET_SIZE = {5: (9500, 7500), 6: (15000, 9500), 7: (20000, 15000), 8: (32000, 20000),
                  9: (42000, 32000)}

    def extent_boxes(self):
        """footprint_boxes() plus the notes' text."""
        boxes = self.footprint_boxes()
        for x, y, t in self.notes:
            boxes.append((f"note '{t[:20]}'", x, y - 20, x + (len(t) + 2) * NOTE_CHAR_W, y + 120))
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
        """The requested style, or the smallest larger one the content fits on
        once it is shifted to the top of the sheet."""
        boxes = self.extent_boxes()
        for style in sorted(self.SHEET_SIZE):
            if style < self.style:
                continue
            s = self._shift(style, boxes)
            if self._fits(style, [(n, x1, y1 + s, x2, y2 + s) for n, x1, y1, x2, y2 in boxes]):
                return style
        return max(self.SHEET_SIZE)

    def footprint_boxes(self):
        """Approximate drawn extent of each placed part: body, pins, stubs and
        label/port text (CHAR_W per character). Returns (label, x1, y1, x2, y2)."""
        lengths = self.side_lengths()
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
                    stub = lengths[self.side_key(pl, p)]
                    reach = stub + 50
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
            y1, y2 = y1 + self.dy, y2 + self.dy
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
