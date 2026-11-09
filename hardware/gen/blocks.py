"""Builds placement.csv from the hand-written files in blocks/, one per schematic function.

A file holds one directive per line, # starts a comment. Coordinates are board mm, origin at the lower-left corner.

    at   SIDE ROT X Y REF                 one part
    pin  SIDE ROT X Y REF                 one part, exactly so: never shifted or turned
    row  SIDE ROT X Y DX DY REF REF ...   a row or column of parts, each DX, DY from the last
    near SIDE TARGET REF REF ...          each part at the free spot nearest TARGET on SIDE
    keep SIDE X1 Y1 X2 Y2 why             "near" stays out of this rectangle
    shift DX DY                           later at and row lines in this file are moved by this much

SIDE is T or B. TARGET is a pin (U800.19) or a point (30.5,41). The file says which pin a part serves and on which
side; "near" only finds the spot, and tries all four rotations with the part's pad on that net towards the pin. A
two-pin part placed with at or row may turn 180 degrees so that the pad on the net it serves faces the pin.

at and row run first, for all files, then near in file order. Nothing is moved to make a row fit: an overlap is an
error to fix in the file.

    python blocks.py build     check, then write placement.csv
    python blocks.py check     check only
    python blocks.py images    out/place_top.png, out/place_bot.png
"""
from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

import numpy as np

import placement as P

HERE = Path(__file__).resolve().parent / "blocks"
NEAR_GAP = 0.50          # a part found by "near" keeps this far from its neighbours: room for a via at each pad
REACH = 14.0


class Board:
    def __init__(self, parts, nets):
        self.parts, self.nets = parts, nets
        self.place = {}
        self.source = {}
        self.keep = []
        self.rects = {"T": {}, "B": {}}
        self.errors = []
        self.far = []
        self.pinned = set()

    def add(self, d, x, y, rot, side, src):
        if d not in self.parts:
            self.errors.append(f"{src}: {d} is not on the netlist")
            return
        if d in self.place:
            self.errors.append(f"{src}: {d} placed twice, first in {self.source[d]}")
            return
        self.place[d] = (x, y, rot, side)
        self.source[d] = src
        self.rects[side][d] = P.crt_rect(self.parts[d], x, y, rot, side)

    def free(self, side, r, gap, ignore=None):
        for d, q in self.rects[side].items():
            if d != ignore and r[0] - gap < q[2] and q[0] - gap < r[2] and r[1] - gap < q[3] and q[1] - gap < r[3]:
                return False
        return True

    def pin(self, spec):
        """(x, y, net) for U800.19, or (x, y, None) for 30.5,41."""
        if "," in spec:
            x, y = spec.split(",")
            return float(x), float(y), None
        d, n = spec.split(".", 1)
        if d not in self.place:
            raise KeyError(f"{spec}: {d} is not placed yet")
        q = next(q for q in self.parts[d].pads if q[4] == n)
        x, y = P.xform(q[0], q[1], *self.place[d])
        return x, y, q[2]

    def holes_on(self, side):
        out = []
        for d, v in self.place.items():
            if v[3] == side:
                continue
            for h in self.parts[d].holes:
                a, b = P.xform(h[0], h[1], *v), P.xform(h[2], h[3], *v)
                out.append((min(a[0], b[0]) - 0.3, min(a[1], b[1]) - 0.3, max(a[0], b[0]) + 0.3, max(a[1], b[1]) + 0.3))
        return out

    def near(self, d, side, spec, src):
        pt = self.parts[d]
        tx, ty, tnet = self.pin(spec)
        names = {q[2] for q in pt.pads if q[2]}
        pads = [q for q in pt.pads if q[2] and (q[2] == tnet or (tnet not in names and q[2] != "GND"))]
        if not pads:
            pads = [q for q in pt.pads if q[2]] or pt.pads
        keep = [k[1:] for k in self.keep if k[0] == side]
        blocked = keep + self.holes_on(side) + self.thermal[side]
        xs = np.arange(max(tx - REACH, 0.5), min(tx + REACH, P.BOARD_W - 0.5) + 1e-6, 0.25)
        ys = np.arange(max(ty - REACH, 0.5), min(ty + REACH, P.BOARD_H - 0.5) + 1e-6, 0.25)
        gx, gy = np.meshgrid(xs, ys, indexing="ij")
        options = []
        for rot in (0, 90, 180, 270):
            local = [(q[0], q[1]) for q in pads]
            # where the served pad lands for each candidate centre
            lx, ly = P.xform(local[0][0], local[0][1], 0.0, 0.0, rot, side)
            cost = np.hypot(gx + lx - tx, gy + ly - ty)
            options.append((rot, cost))
        order = []
        for rot, cost in options:
            order += [(float(c), rot, i) for i, c in enumerate(cost.flat)]
        order.sort()
        o = {rot: P.crt_rect(pt, 0.0, 0.0, rot, side) for rot in (0, 90, 180, 270)}
        for dist, rot, i in order:
            a, b = np.unravel_index(i, gx.shape)
            x, y = float(gx[a, b]), float(gy[a, b])
            r = (x + o[rot][0], y + o[rot][1], x + o[rot][2], y + o[rot][3])
            if r[0] < P.EDGE_CLR or r[1] < P.EDGE_CLR or r[2] > P.BOARD_W - P.EDGE_CLR or r[3] > P.BOARD_H - P.EDGE_CLR:
                continue
            if any(r[0] < k[2] and k[0] < r[2] and r[1] < k[3] and k[1] < r[3] for k in blocked):
                continue
            if self.free(side, r, NEAR_GAP):
                self.add(d, x, y, rot, side, src)
                if dist > 8.0:
                    self.far.append((round(dist, 1), d, spec))
                return
        self.errors.append(f"{src}: no room for {d} near {spec} on {side}")

    def served_cost(self, d, v):
        """How far the pads are from what they serve, for a two-pin part at v."""
        total = 0.0
        pt = self.parts[d]
        for q in pt.pads:
            net = q[2]
            if not net or net == "GND" or net not in self.nets or len(self.nets[net]) > 60:
                continue
            if d[0] == "L" and P.is_rail(net, self.nets[net]):      # an inductor turns its switch node to the pin
                continue
            a = P.xform(q[0], q[1], *v)
            best = None
            for nd in self.nets[net]:
                r, n = nd.split(".", 1)
                if r == d or r not in self.place or r not in self.parts:
                    continue
                c = next((c for c in self.parts[r].pads if c[4] == n), None)
                if c:
                    b = P.xform(c[0], c[1], *self.place[r])
                    dist = math.hypot(a[0] - b[0], a[1] - b[1])
                    if best is None or dist < best:
                        best = dist
            if best is not None:
                total += best
        return total

    def flip_two_pin(self, only=None):
        for d in list(only if only is not None else self.place):
            pt = self.parts[d]
            if len(pt.pads) != 2 or d[0] == "Y" or d in self.pinned:     # a crystal's rotation is chosen by hand
                continue
            x, y, rot, side = self.place[d]
            other = (x, y, (rot + 180) % 360, side)
            if self.served_cost(d, other) < self.served_cost(d, self.place[d]) - 0.01:
                self.place[d] = other
                self.rects[side][d] = P.crt_rect(pt, *other)


def read_files():
    directives = []
    for path in sorted(HERE.glob("*.txt")):
        dx, dy = 0.0, 0.0
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            w = line.split()
            if w[0] == "shift":
                dx, dy = float(w[1]), float(w[2])
                continue
            if w[0] in ("at", "row"):
                w[3], w[4] = str(round(float(w[3]) + dx, 3)), str(round(float(w[4]) + dy, 3))
            directives.append((f"{path.name}:{i}", w))
    return directives


def build():
    parts, nets = P.load_parts()
    b = Board(parts, nets)
    directives = read_files()
    for src, w in directives:
        if w[0] == "keep":
            b.keep.append((w[1], float(w[2]), float(w[3]), float(w[4]), float(w[5])))
        elif w[0] == "at":
            b.add(w[5], float(w[3]), float(w[4]), int(w[2]), w[1], src)
        elif w[0] == "pin":
            b.add(w[5], float(w[3]), float(w[4]), int(w[2]), w[1], src)
            b.pinned.add(w[5])
        elif w[0] == "row":
            x, y, dx, dy = (float(v) for v in w[3:7])
            for i, d in enumerate(w[7:]):
                b.add(d, round(x + i * dx, 3), round(y + i * dy, 3), int(w[2]), w[1], src)
        elif w[0] != "near":
            b.errors.append(f"{src}: unknown directive {w[0]}")
    b.flip_two_pin()
    b.thermal = {"T": [], "B": []}
    for k in P.thermal_keepouts(parts, b.place):
        b.thermal[k[4]].append(k[:4])
    for src, w in directives:
        if w[0] == "near":
            before = set(b.place)
            for d in w[3:]:
                try:
                    b.near(d, w[1], w[2], src)
                except KeyError as e:
                    b.errors.append(f"{src}: {e}")
            # a part placed here may be what later parts serve
    return parts, nets, b


def problems(parts, nets, b):
    out = list(b.errors)
    missing = sorted((d for d in parts if d not in b.place), key=P._natural)
    if missing:
        out.append(f"{len(missing)} not placed: " + " ".join(missing))
    out += P.check(parts, b.place)
    for g, a, c in P.close_pairs(parts, b.place):
        if {a, c} in ({"H1602", "J1400"}, {"H1603", "J1400"}):
            continue
        out.append(f"closer than 10 mil ({g:.2f} mm): {a} {c}")
    # the SiP's via field: parts on the back must leave every ball a via site
    import fanout
    for ball in fanout.sip_balls_without_site(parts, nets, b.place):
        out.append(f"U1.{ball} has no via site left: a part on the back is on them")
    for k in P.thermal_keepouts(parts, b.place):
        for d, v in b.place.items():
            if v[3] != k[4]:
                continue
            r = P.crt_rect(parts[d], *v)
            if r[0] < k[2] and k[0] < r[2] and r[1] < k[3] and k[1] < r[3]:
                out.append(f"{d} ({k[4]}) is over the thermal vias of {k[5]}")
    return out


def main(argv):
    cmd = argv[0] if argv else "check"
    parts, nets, b = build()
    probs = problems(parts, nets, b)
    print("\n".join(probs) if probs else "no problems")
    if b.far:
        print("found more than 8 mm from their target:", sorted(b.far, reverse=True)[:30])
    print(f"{len(b.place)} of {len(parts)} placed, {sum(1 for v in b.place.values() if v[3] == 'B')} on the back")
    if cmd == "build" and not probs:
        P.write_csv(b.place)
        print("wrote", P.CSV_PATH)
    if cmd == "images":
        P.render(parts, nets, b.place, P.OUT / "place_top.png", P.OUT / "place_bot.png")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
