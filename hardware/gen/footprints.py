"""PCB footprint definitions for lib/APE-SBC.PcbLib.

Footprints are written in millimetres, as the manufacturer drawings are, and
emitted in mils for the altium-mcp tool ``create_footprints_batch``. Each
footprint lives in a ``fplib/*.py`` module (``FOOTPRINTS = [...]``), with the
land-pattern source (URL, page, figure) in a comment above it. Pad names are
the symbol pin numbers; ``build.py check`` fails if a symbol pin has no pad or
a named pad has no pin.

Conventions
-----------
* Units: mm. +x is right, +y is UP (top view). Manufacturer drawings usually
  have y down; flip them.
* Origin: the centre of ``body``. Footprints are authored in any frame (often
  the drawing's datum) and shifted on emission.
* Orientation: IPC-7351 zero orientation where it makes sense: pin 1 top left
  for ICs (left column / left side first, counter-clockwise for quads), pad 1
  on the left for two-terminal parts. Connectors keep the drawing's view with
  the mating face down (-y) where possible.
* Pads: SMD pads are on Top Layer, through-hole pads on Multi-Layer. Unnamed
  pads are mechanical (locating holes) and are ignored by the pad check.
* Graphics: body outline on Mechanical 13 (0.10 mm); courtyard on
  Mechanical 15 (0.05 mm), ``courtyard`` mm around body and pads (default
  0.25); silkscreen on Top Overlay (0.15 mm lines, kept 0.15 mm from copper,
  JLCPCB legend rules) with a pin-1 / cathode / plus marker.
* Solder mask and paste: the batch tool has no per-pad mask fields, so mask
  and paste come from the board rules (mask +0.05 mm, SiP lands 0, paste 0;
  docs/research/bom/jlcpcb-stackup-and-cost.md section 5). Exposed pads whose
  datasheet shows a windowed stencil carry the windows as fills on Top Paste;
  the board needs a paste-mask rule that removes those pads' own paste
  (``paste_rule_query()`` prints the query).

Altium enums used in the spec (TShape / TExtendedHoleType):
  shape 1 = eRounded (round or oval), 2 = eRectangular, 3 = eOctagonal,
  9 = eRoundedRectangular (corner radius in % of half the shorter side;
  the default 50 gives a radius of 1/4 of the shorter side, as IPC-7351C);
  hole type 0 = round, 2 = slot (hole_size = slot width, hole_width = slot length).
"""
from __future__ import annotations

import importlib
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

MIL_PER_MM = 1 / 0.0254

SILK_W = 0.15          # legend line width (JLCPCB min 0.15)
SILK_CLEAR = 0.15      # legend to pad (JLCPCB min 0.15)
BODY_W = 0.10
CRTYD_W = 0.05
DOT_R = 0.20           # pin-1 dot radius (filled)

SHAPES = {"round": 1, "rect": 2, "octagon": 3, "roundrect": 9}
L_TOP, L_MULTI = "Top Layer", "Multi-Layer"
L_SILK, L_PASTE = "Top Overlay", "Top Paste"
L_BODY, L_CRTYD = "Mechanical 13", "Mechanical 15"


@dataclass
class Pad:
    name: str
    x: float
    y: float
    w: float
    h: float
    shape: str = "roundrect"
    rot: float = 0.0
    hole: float = 0.0          # drill diameter, or slot width; 0 = SMD
    slot: float = 0.0          # slot length; 0 = round hole
    slot_rot: float = 0.0      # slot direction (0 = along x)
    plated: bool = True
    corner: int = 50           # roundrect corner radius, % of HALF the shorter side (Altium; 100 = round ends)

    def bbox(self):
        """Axis-aligned extent of the copper (and hole), any rotation."""
        hw, hh = self.w / 2, self.h / 2
        c, s = math.cos(math.radians(self.rot)), math.sin(math.radians(self.rot))
        ex = abs(hw * c) + abs(hh * s)
        ey = abs(hw * s) + abs(hh * c)
        if self.slot:
            a = math.radians(self.slot_rot)
            hl, hd = self.slot / 2, self.hole / 2
            hx, hy = abs(hl * math.cos(a)) + abs(hd * math.sin(a)), abs(hl * math.sin(a)) + abs(hd * math.cos(a))
        else:
            hx = hy = self.hole / 2
        ex, ey = max(ex, hx), max(ey, hy)
        return self.x - ex, self.y - ey, self.x + ex, self.y + ey

    def moved(self, dx, dy) -> "Pad":
        return Pad(self.name, self.x + dx, self.y + dy, self.w, self.h, self.shape, self.rot,
                   self.hole, self.slot, self.slot_rot, self.plated, self.corner)


@dataclass
class Footprint:
    name: str
    description: str
    pads: list[Pad]
    body: tuple                    # (w, h) centred on (0, 0), or (x1, y1, x2, y2)
    marker: str = "pin1"           # pin1 | corner | cathode | plus | none
    marker_pad: str = "1"          # pad the marker refers to (cathode: usually "2")
    marker_at: tuple | None = None  # explicit (x, y) for the dot, authoring frame
    courtyard: float | tuple = 0.25  # margin, or (x1, y1, x2, y2) in the authoring frame
    paste: list = field(default_factory=list)   # (cx, cy, w, h) windows on Top Paste
    silk: bool = True
    silk_offset: float = 0.0       # draw the silk outline this far outside the body
    joined: tuple = ()             # groups of pad names that are one piece of package metal
                                   # (pads of a group may touch; build.py checks one net per group)
    assumed: str = ""              # pad numbering not given by the drawing: what was assumed
    extra: list = field(default_factory=list)   # additional raw spec lines (mils, emitted as-is)

    # ---------------------------------------------------------------- geometry
    def body_rect(self):
        b = self.body
        if len(b) == 2:
            return -b[0] / 2, -b[1] / 2, b[0] / 2, b[1] / 2
        return tuple(b)

    def silk_rect(self):
        x1, y1, x2, y2 = self.body_rect()
        o = self.silk_offset
        return x1 - o, y1 - o, x2 + o, y2 + o

    def origin(self):
        x1, y1, x2, y2 = self.body_rect()
        return (x1 + x2) / 2, (y1 + y2) / 2

    def pad_names(self) -> set[str]:
        return {p.name for p in self.pads if p.name}

    def courtyard_rect(self):
        if isinstance(self.courtyard, tuple):
            return self.courtyard
        x1, y1, x2, y2 = self.body_rect()
        boxes = [p.bbox() for p in self.pads]
        for m in self.marker_shapes():
            if m[0] == "dot":
                boxes.append((m[1] - DOT_R, m[2] - DOT_R, m[1] + DOT_R, m[2] + DOT_R))
            else:
                h = SILK_W / 2
                boxes.append((min(m[1], m[3]) - h, min(m[2], m[4]) - h, max(m[1], m[3]) + h, max(m[2], m[4]) + h))
        for a, b, c, d in boxes:
            x1, y1, x2, y2 = min(x1, a), min(y1, b), max(x2, c), max(y2, d)
        m = self.courtyard
        g = 0.05
        return (math.floor((x1 - m) / g) * g, math.floor((y1 - m) / g) * g,
                math.ceil((x2 + m) / g) * g, math.ceil((y2 + m) / g) * g)

    def _keepouts(self):
        k = SILK_CLEAR + SILK_W / 2
        return [(a - k, b - k, c + k, d + k) for a, b, c, d in (p.bbox() for p in self.pads)]

    def silk_segments(self):
        """Body outline split around the pads. Pieces shorter than 0.6 mm are
        kept only at the corners (stubs between two pads are dropped)."""
        if not self.silk:
            return []
        x1, y1, x2, y2 = self.silk_rect()
        keep = self._keepouts()
        out = []
        for horiz, fixed, lo, hi in [(True, y1, x1, x2), (True, y2, x1, x2),
                                     (False, x1, y1, y2), (False, x2, y1, y2)]:
            blocked = sorted((kx1, kx2) if horiz else (ky1, ky2)
                             for kx1, ky1, kx2, ky2 in keep
                             if (ky1 < fixed < ky2 if horiz else kx1 < fixed < kx2))
            pos = lo
            for s, e in blocked + [(hi, hi)]:
                end = min(s, hi)
                n = end - pos
                if n >= 0.6 or (n >= 0.2 and (pos == lo or end == hi)):
                    out.append((pos, fixed, end, fixed) if horiz else (fixed, pos, fixed, end))
                pos = max(pos, e)
                if pos >= hi:
                    break
        return out

    def marker_shapes(self):
        """('dot', x, y) / ('line', x1, y1, x2, y2) items in the authoring frame."""
        if self.marker == "none" or not self.silk:
            return []
        pad = next((p for p in self.pads if p.name == self.marker_pad), None)
        bx1, by1, bx2, by2 = self.body_rect()
        if self.marker_at:
            return [("dot", *self.marker_at)]
        if pad is None:
            return []
        px1, py1, px2, py2 = pad.bbox()
        cx, cy = (px1 + px2) / 2, (py1 + py2) / 2
        gap = SILK_CLEAR + DOT_R + 0.02
        if self.marker == "corner":
            bx1, by1, bx2, by2 = self.silk_rect()
            gap = SILK_W / 2 + DOT_R + 0.05
            mx = bx1 - gap if cx < (bx1 + bx2) / 2 else bx2 + gap
            my = by2 + gap if cy > (by1 + by2) / 2 else by1 - gap
            return [("dot", mx, my)]
        # side of the body the pad is nearest to
        d = {"L": cx - bx1, "R": bx2 - cx, "B": cy - by1, "T": by2 - cy}
        side = min(d, key=d.get)
        if self.marker == "pin1":
            if side == "L":
                return [("dot", min(px1, bx1) - gap, cy)]
            if side == "R":
                return [("dot", max(px2, bx2) + gap, cy)]
            if side == "B":
                return [("dot", cx, min(py1, by1) - gap)]
            return [("dot", cx, max(py2, by2) + gap)]
        k = SILK_CLEAR + SILK_W / 2 + 0.02
        if self.marker == "cathode":
            # bar just outside the pad's outer edge, as long as the pad
            if side == "L":
                x = px1 - k
                return [("line", x, py1, x, py2)]
            if side == "R":
                x = px2 + k
                return [("line", x, py1, x, py2)]
            if side == "B":
                y = py1 - k
                return [("line", px1, y, px2, y)]
            y = py2 + k
            return [("line", px1, y, px2, y)]
        if self.marker == "plus":
            s = 0.3
            if side in ("L", "R"):
                x = px1 - k - s if side == "L" else px2 + k + s
                y = py2 + k + s
            else:
                x, y = px1 - k - s, (py2 + k + s if side == "T" else py1 - k - s)
            return [("line", x - s, y, x + s, y), ("line", x, y - s, x, y + s)]
        raise ValueError(f"{self.name}: unknown marker {self.marker}")

    # ---------------------------------------------------------------- checks
    def problems(self) -> list[str]:
        out = []
        if not self.pads:
            out.append("no pads")
        named = [p for p in self.pads if p.name]
        same = {frozenset((a, b)) for g in self.joined for a in g for b in g if a != b}
        for g in self.joined:
            if set(g) - self.pad_names():
                out.append(f"joined group {g}: no pad {' '.join(sorted(set(g) - self.pad_names()))}")
        for i, a in enumerate(self.pads):
            ax1, ay1, ax2, ay2 = a.bbox()
            for b in self.pads[i + 1:]:
                if a.name and (a.name == b.name or frozenset((a.name, b.name)) in same):
                    continue
                bx1, by1, bx2, by2 = b.bbox()
                gx = max(bx1 - ax2, ax1 - bx2)
                gy = max(by1 - ay2, ay1 - by2)
                gap = gx if gy < 0 else (gy if gx < 0 else math.hypot(gx, gy))
                if gap < 0.1:
                    out.append(f"pads {a.name or '(mech)'} and {b.name or '(mech)'} are {gap:.3f} mm apart")
            if a.hole and a.hole < 0.15:
                out.append(f"pad {a.name}: hole {a.hole} mm is below the 0.15 mm minimum")
            if a.hole and a.plated and a.name and min(a.w, a.h) - max(a.hole, 0) < 0.3 - 1e-9 and not a.slot:
                out.append(f"pad {a.name}: annular ring {(min(a.w, a.h) - a.hole) / 2:.3f} mm < 0.15 mm")
            if a.shape not in SHAPES:
                out.append(f"pad {a.name}: unknown shape {a.shape}")
        line_keep = self._keepouts()             # pad + clearance + half a line width
        dot_keep = [(a - SILK_CLEAR, b - SILK_CLEAR, c + SILK_CLEAR, d + SILK_CLEAR)
                    for a, b, c, d in (p.bbox() for p in self.pads)]
        for m in self.marker_shapes():
            if m[0] == "dot":
                _, x, y = m
                box, keep = (x - DOT_R, y - DOT_R, x + DOT_R, y + DOT_R), dot_keep
            else:
                _, xa, ya, xb, yb = m
                box, keep = (min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)), line_keep
            for k in keep:
                if box[0] < k[2] and k[0] < box[2] and box[1] < k[3] and k[1] < box[3]:
                    out.append(f"{self.marker} marker at ({box[0]:.2f},{box[1]:.2f}) is within "
                               f"{SILK_CLEAR} mm of a pad; set marker_at")
                    break
        if not named:
            out.append("no named pads")
        for text in [self.name, self.description] + [p.name for p in self.pads]:
            if "|" in text or not text.isascii():
                out.append(f"'{text}' must be ASCII without '|' (spec file field)")
        return out

    # ---------------------------------------------------------------- emission
    def spec_lines(self) -> list[str]:
        ox, oy = self.origin()
        f = lambda v: _mil(v)
        out = [f"FOOTPRINT|{self.name}|{self.description}"]
        for p in self.pads:
            x, y = p.x - ox, p.y - oy
            if p.hole:
                layer, hole = L_MULTI, p.hole
                htype, hwidth = (2, p.slot) if p.slot else (0, 0)
            else:
                layer, hole, htype, hwidth = L_TOP, 0, 0, 0
            rec = [p.name, f(x), f(y), _num(p.rot), layer, "1" if p.plated else "0", f(hole),
                   str(htype), f(hwidth), _num(p.slot_rot), f(p.w), f(p.h), str(SHAPES[p.shape])]
            if p.shape == "roundrect":
                rec.append(str(p.corner))
            out.append("PAD|" + "|".join(rec))
        x1, y1, x2, y2 = self.body_rect()
        out += _rect_tracks(x1 - ox, y1 - oy, x2 - ox, y2 - oy, BODY_W, L_BODY)
        cx1, cy1, cx2, cy2 = self.courtyard_rect()
        out += _rect_tracks(cx1 - ox, cy1 - oy, cx2 - ox, cy2 - oy, CRTYD_W, L_CRTYD)
        for xa, ya, xb, yb in self.silk_segments():
            out.append(f"TRACK|{f(xa - ox)}|{f(ya - oy)}|{f(xb - ox)}|{f(yb - oy)}|{f(SILK_W)}|{L_SILK}")
        for m in self.marker_shapes():
            if m[0] == "dot":
                out.append(f"ARC|{f(m[1] - ox)}|{f(m[2] - oy)}|{f(DOT_R / 2)}|0|360|{f(DOT_R)}|{L_SILK}")
            else:
                _, xa, ya, xb, yb = m
                out.append(f"TRACK|{f(xa - ox)}|{f(ya - oy)}|{f(xb - ox)}|{f(yb - oy)}|{f(SILK_W)}|{L_SILK}")
        for cx, cy, w, h in self.paste:
            out.append(f"FILL|{f(cx - w / 2 - ox)}|{f(cy - h / 2 - oy)}|{f(cx + w / 2 - ox)}|"
                       f"{f(cy + h / 2 - oy)}|0|{L_PASTE}")
        out += self.extra
        return out


def _num(v: float) -> str:
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _mil(mm: float) -> str:
    return _num(mm * MIL_PER_MM)


def _rect_tracks(x1, y1, x2, y2, w, layer):
    f = _mil
    pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
    return [f"TRACK|{f(a[0])}|{f(a[1])}|{f(b[0])}|{f(b[1])}|{f(w)}|{layer}" for a, b in zip(pts, pts[1:])]


# ------------------------------------------------------------------ builders

def smd(name, x, y, w, h, shape="roundrect", rot=0.0, corner=50) -> Pad:
    return Pad(str(name), x, y, w, h, shape, rot, corner=corner)


def with_radius(pads, r) -> list[Pad]:
    """Give the roundrect pads in ``pads`` a corner radius of ``r`` mm."""
    for p in pads:
        if p.shape == "roundrect":
            p.corner = max(1, min(100, round(200 * r / min(p.w, p.h))))
    return pads


def tht(name, x, y, w, h=None, hole=0.0, shape="round", slot=0.0, slot_rot=0.0, plated=True) -> Pad:
    """Through-hole pad. ``w``/``h`` = copper size (h defaults to w); ``hole`` =
    drill or slot width; ``slot`` = slot length along ``slot_rot``."""
    return Pad(str(name), x, y, w, w if h is None else h, shape, 0.0, hole, slot, slot_rot, plated)


def npth(x, y, hole) -> Pad:
    """Non-plated mechanical hole (unnamed: not a pin)."""
    return Pad("", x, y, hole, hole, "round", 0.0, hole, plated=False)


def chip(pad_l, pad_w, gap, names=("1", "2"), shape="roundrect") -> list[Pad]:
    """Two pads along x: ``pad_l`` along x, ``pad_w`` along y, ``gap`` between
    the inner edges. Pad 1 on the left."""
    c = (gap + pad_l) / 2
    return [smd(names[0], -c, 0, pad_l, pad_w, shape), smd(names[1], c, 0, pad_l, pad_w, shape)]


def row(names, x, y, dx, dy, w, h, shape="roundrect") -> list[Pad]:
    """Pads ``names`` starting at (x, y), stepping (dx, dy). ``None`` skips a site."""
    out = []
    for i, n in enumerate(names):
        if n is not None:
            out.append(smd(n, x + i * dx, y + i * dy, w, h, shape))
    return out


def dual(n, pitch, span, pad_l, pad_w, shape="roundrect") -> list[Pad]:
    """SOIC-style numbering: 1..n/2 down the left column, the rest up the
    right. ``span`` = pad-centre distance across; ``pad_l`` along x."""
    k = n // 2
    top = (k - 1) * pitch / 2
    return (row(range(1, k + 1), -span / 2, top, 0, -pitch, pad_l, pad_w, shape)
            + row(range(k + 1, n + 1), span / 2, -top, 0, pitch, pad_l, pad_w, shape))


def quad(n_side, n_end, pitch, span_x, span_y, pad_l, pad_w, first=1, shape="roundrect") -> list[Pad]:
    """QFN/QFP numbering, counter-clockwise from the top of the left side:
    ``n_side`` pads on the left and right, ``n_end`` on the bottom and top.
    ``span_x`` / ``span_y`` = pad-centre distance across; ``pad_l`` = pad
    length (perpendicular to the edge), ``pad_w`` = width along the edge."""
    pads, n = [], first
    ys = (n_side - 1) * pitch / 2
    xs = (n_end - 1) * pitch / 2
    for i in range(n_side):
        pads.append(smd(n, -span_x / 2, ys - i * pitch, pad_l, pad_w, shape)); n += 1
    for i in range(n_end):
        pads.append(smd(n, -xs + i * pitch, -span_y / 2, pad_w, pad_l, shape)); n += 1
    for i in range(n_side):
        pads.append(smd(n, span_x / 2, -ys + i * pitch, pad_l, pad_w, shape)); n += 1
    for i in range(n_end):
        pads.append(smd(n, xs - i * pitch, span_y / 2, pad_w, pad_l, shape)); n += 1
    return pads


BGA_ROWS = "ABCDEFGHJKLMNPRTUVWY"     # JEDEC: no I, O, Q, S, X, Z


def bga(n_rows, n_cols, pitch, land, missing=(), shape="round") -> list[Pad]:
    """Ball grid, A1 top left, rows down (-y), columns right (+x)."""
    pads = []
    for r in range(n_rows):
        for c in range(n_cols):
            name = f"{BGA_ROWS[r]}{c + 1}"
            if name in missing:
                continue
            pads.append(smd(name, (c - (n_cols - 1) / 2) * pitch, ((n_rows - 1) / 2 - r) * pitch,
                            land, land, shape))
    return pads


def window_grid(cx, cy, w, h, pitch_x, pitch_y, nx, ny) -> list[tuple]:
    """Paste windows ``w`` x ``h`` on a ``pitch_x`` x ``pitch_y`` grid centred on (cx, cy)."""
    return [(cx + (i - (nx - 1) / 2) * pitch_x, cy + (j - (ny - 1) / 2) * pitch_y, w, h)
            for i in range(nx) for j in range(ny)]


# ------------------------------------------------------------------ library

GEN = Path(__file__).resolve().parent


def all_footprints(modules=None, errors=None) -> list[Footprint]:
    """FOOTPRINTS from every gen/fplib/*.py module (or only ``modules``). With
    an ``errors`` list, a module that fails to import is reported there
    instead of raising."""
    fps = []
    if str(GEN) not in sys.path:
        sys.path.insert(0, str(GEN))
    for p in sorted((GEN / "fplib").glob("*.py")):
        if p.stem == "__init__" or (modules and p.stem not in modules):
            continue
        try:
            fps += getattr(importlib.import_module(f"fplib.{p.stem}"), "FOOTPRINTS", [])
        except Exception as e:          # noqa: BLE001 - reported to the caller
            if errors is None:
                raise
            errors.append(f"fplib/{p.name}: {type(e).__name__}: {e}")
    seen = {}
    for fp in fps:
        if fp.name in seen:
            raise ValueError(f"duplicate footprint name {fp.name}")
        seen[fp.name] = fp
    return fps


def library_spec(fps, lib_path) -> str:
    lines = [f"FPLIB|{lib_path}"]
    for fp in fps:
        lines += fp.spec_lines()
    return "\n".join(lines) + "\n"


def paste_rule_query(fps) -> str:
    """Altium query for the pads whose paste comes from Top Paste windows."""
    terms = []
    for fp in fps:
        if fp.paste:
            inside = {p.name for p in fp.pads for cx, cy, w, h in fp.paste
                      if p.bbox()[0] <= cx <= p.bbox()[2] and p.bbox()[1] <= cy <= p.bbox()[3]}
            terms += [f"HasFootprintPad('{fp.name}','{n}')" for n in sorted(inside)]
    return " Or ".join(terms)


# ------------------------------------------------------- generic symbol parts
# Generic symbols (RES, CAP, FERRITE, LED, DIODE, ...) have no fixed package,
# so their footprint is chosen per placed part, in this order:
#   1. footprint="..." passed to Sheet.add() / in a column() params dict
#   2. the symbol's own footprint (fixed-package symbols)
#   3. PART_RULES: first pattern found in the MPN parameter or the comment
#   4. the EIA size code in the comment (0402, 0603, ...) with the prefix in
#      SIZE_PREFIX ("RES" + "0402" -> "R0402")
# A generic part that matches none of these is a build.py check problem.

PART_RULES = [
    (r"BLM15", "FB0402"),
    (r"BLM18", "FB0603"),
    (r"DFE252012F", "IND_MURATA_DFE252012F"),
    (r"MWSA0402S", "IND_SUNLORD_MWSA0402S"),
    (r"MWSA0603S", "IND_SUNLORD_MWSA0603S"),
    (r"RYHV10V150UF", "CP_SMD_D6.3X5.8"),
    (r"\bSS34\b", "DIO_SMA"),
    (r"BAT54WS", "SOD323"),
    (r"PESD24VL1BA", "SOD323"),
    (r"TPD1E10B06", "X1SON2_DPY"),
    (r"Q13FC135|FC-135", "XTAL_EPSON_FC-135"),
]
SIZE_PREFIX = {"RES": "R", "CAP": "C", "FERRITE": "FB", "LED": "LED"}
SIZE_RE = re.compile(r"(?<![0-9A-Za-z.])(0201|0402|0603|0805|1206|1210)(?![0-9])")


def resolve(symbol, comment="", params=None, explicit="") -> str:
    """Footprint name for one placed part ('' if it cannot be decided)."""
    if explicit:
        return explicit
    if symbol.footprint:
        return symbol.footprint
    text = f"{(params or {}).get('MPN', '')} {comment}"
    for pat, fp in PART_RULES:
        if re.search(pat, text):
            return fp
    m = SIZE_RE.search(comment)
    if m and symbol.name in SIZE_PREFIX:
        return SIZE_PREFIX[symbol.name] + m.group(1)
    return ""


def pad_problems(symbol, fp: Footprint) -> list[str]:
    pins = {p.number for p in symbol.pins}
    pads = fp.pad_names()
    out = []
    if pins - pads:
        out.append(f"{symbol.name} -> {fp.name}: pins without a pad: {' '.join(sorted(pins - pads, key=_nat))}")
    if pads - pins:
        out.append(f"{symbol.name} -> {fp.name}: pads without a pin: {' '.join(sorted(pads - pins, key=_nat))}")
    return out


def _nat(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def check(symbols, sheets) -> tuple[list[str], dict]:
    """Footprint problems for build.py check, plus {footprint: [designators]}."""
    fps = {fp.name: fp for fp in all_footprints()}
    problems = []
    for fp in fps.values():
        problems += [f"footprint {fp.name}: {p}" for p in fp.problems()]
    pairs = {}                    # (symbol name, footprint) -> symbol
    for s in symbols:
        if s.footprint:
            pairs[(s.name, s.footprint)] = s
    used = {}
    part_nets = {}                # designator -> {pin: net}, all parts of a multi-part symbol
    for sh in sheets:
        for pl in sh.placed:
            part_nets.setdefault(pl.designator, {}).update(pl.nets)
            name = pl.footprint or pl.symbol.footprint
            if not name:
                problems.append(f"{sh.title}: {pl.designator} ({pl.symbol.name}, '{pl.comment}') "
                                "has no footprint: add the size code to the comment or footprint=")
                continue
            pairs[(pl.symbol.name, name)] = pl.symbol
            used.setdefault(name, set()).add(pl.designator)
    for (sname, fname), sym in sorted(pairs.items()):
        if fname not in fps:
            problems.append(f"{sname}: footprint {fname} is not in fplib")
            continue
        problems += pad_problems(sym, fps[fname])
    for fname, desigs in used.items():
        for group in getattr(fps.get(fname), "joined", ()):
            for d in desigs:
                nets = {part_nets[d].get(n) for n in group}
                if len(nets) > 1:
                    problems.append(f"{d}: pins {'/'.join(group)} are one terminal of {fname} "
                                    f"but sit on different nets {sorted(map(str, nets))}")
    return problems, {k: sorted(v, key=_nat) for k, v in used.items()}


def render_png(fp: Footprint, path, scale=None):
    """Draw one footprint (top view, origin-shifted) to PNG through SVG + PyMuPDF:
    copper grey, holes white (non-plated: blue rim), paste windows orange, silk black, courtyard
    magenta, body blue, pad names in red."""
    import fitz
    ox, oy = fp.origin()
    cx1, cy1, cx2, cy2 = (v for v in fp.courtyard_rect())
    w, h = cx2 - cx1, cy2 - cy1
    s = scale or max(20.0, 900 / max(w, h))
    X = lambda x: (x - cx1) * s + 10
    Y = lambda y: (cy2 - y) * s + 10
    el = []
    for p in fp.pads:
        a, b, c, d = p.bbox() if p.rot % 90 == 0 else (p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)
        rx = min(c - a, d - b) * s / 2 * (1 if p.shape == "round" else p.corner / 100 if p.shape == "roundrect" else 0)
        el.append(f'<rect x="{X(a):.1f}" y="{Y(d):.1f}" width="{(c - a) * s:.1f}" height="{(d - b) * s:.1f}" '
                  f'rx="{rx:.1f}" fill="#999"/>')
        if p.hole:
            if p.slot:
                horiz = abs(math.cos(math.radians(p.slot_rot))) > 0.5
                lw, lh = (p.slot, p.hole) if horiz else (p.hole, p.slot)
                el.append(f'<rect x="{X(p.x - lw / 2):.1f}" y="{Y(p.y + lh / 2):.1f}" width="{lw * s:.1f}" '
                          f'height="{lh * s:.1f}" rx="{p.hole * s / 2:.1f}" fill="#fff"/>')
            else:
                edge = "" if p.plated else ' stroke="#36c" stroke-width="2"'
                el.append(f'<circle cx="{X(p.x):.1f}" cy="{Y(p.y):.1f}" r="{p.hole * s / 2:.1f}" fill="#fff"{edge}/>')
        if p.name:
            fs = max(8, min(c - a, d - b) * s * 0.5)
            el.append(f'<text x="{X(p.x):.1f}" y="{Y(p.y) + fs / 3:.1f}" font-size="{fs:.0f}" '
                      f'text-anchor="middle" fill="#c00" font-family="Arial">{p.name}</text>')
    for pcx, pcy, pw, ph in fp.paste:
        el.append(f'<rect x="{X(pcx - pw / 2):.1f}" y="{Y(pcy + ph / 2):.1f}" width="{pw * s:.1f}" '
                  f'height="{ph * s:.1f}" fill="none" stroke="#f80" stroke-width="2"/>')
    bx1, by1, bx2, by2 = fp.body_rect()
    el.append(f'<rect x="{X(bx1):.1f}" y="{Y(by2):.1f}" width="{(bx2 - bx1) * s:.1f}" height="{(by2 - by1) * s:.1f}" '
              f'fill="none" stroke="#36c" stroke-width="1" stroke-dasharray="4"/>')
    el.append(f'<rect x="{X(cx1):.1f}" y="{Y(cy2):.1f}" width="{w * s:.1f}" height="{h * s:.1f}" '
              f'fill="none" stroke="#c0c" stroke-width="1"/>')
    for xa, ya, xb, yb in fp.silk_segments():
        el.append(f'<line x1="{X(xa):.1f}" y1="{Y(ya):.1f}" x2="{X(xb):.1f}" y2="{Y(yb):.1f}" '
                  f'stroke="#000" stroke-width="{SILK_W * s:.1f}"/>')
    for m in fp.marker_shapes():
        if m[0] == "dot":
            el.append(f'<circle cx="{X(m[1]):.1f}" cy="{Y(m[2]):.1f}" r="{DOT_R * s:.1f}" fill="#000"/>')
        else:
            el.append(f'<line x1="{X(m[1]):.1f}" y1="{Y(m[2]):.1f}" x2="{X(m[3]):.1f}" y2="{Y(m[4]):.1f}" '
                      f'stroke="#000" stroke-width="{SILK_W * s:.1f}"/>')
    el.append(f'<circle cx="{X(ox):.1f}" cy="{Y(oy):.1f}" r="3" fill="#0a0"/>')
    W, H = w * s + 20, h * s + 40
    el.append(f'<text x="10" y="{H - 10:.0f}" font-size="14" font-family="Arial">{fp.name}  '
              f'({w:.2f} x {h:.2f} mm courtyard, {s:.0f} px/mm)</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}">'
           f'<rect width="100%" height="100%" fill="#fff"/>' + "".join(el) + "</svg>")
    doc = fitz.open(stream=svg.encode(), filetype="svg")
    doc[0].get_pixmap().save(str(path))


if __name__ == "__main__":
    # Self-check of the footprint data alone (no sheets):
    #   python footprints.py [MODULE ...]    problems + pad/pin mapping (all or some fplib modules)
    #   python footprints.py --png DIR [NAME ...]   draw footprints to DIR/NAME.png
    sys.path.insert(0, str(GEN))
    if len(sys.argv) > 2 and sys.argv[1] == "--png":
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        for fp in all_footprints(errors=[]):
            if len(sys.argv) == 3 or fp.name in sys.argv[3:]:
                render_png(fp, out / f"{fp.name}.png")
                print(out / f"{fp.name}.png")
        sys.exit(0)
    import build
    syms = build.all_symbols()
    probs = []
    fps = {fp.name: fp for fp in all_footprints(sys.argv[1:] or None, probs)}
    for fp in fps.values():
        probs += [f"footprint {fp.name}: {p}" for p in fp.problems()]
    for s in syms:
        if s.footprint and s.footprint in fps:
            probs += pad_problems(s, fps[s.footprint])
    missing = sorted({s.footprint for s in syms if s.footprint and s.footprint not in fps})
    print(f"{len(fps)} footprints")
    if missing:
        print("not written yet: " + " ".join(missing))
    print("\n".join(probs) if probs else "no footprint problems")
