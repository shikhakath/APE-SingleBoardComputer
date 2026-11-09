"""APE-SBC power planes from planes.txt: polygons with straight edges, drawn by hand, and as few tracks as possible.

Power copper comes in three kinds, and nothing searches for the shape of a plane:
1. planes.txt: each region as drawn. Altium pours them in file order, each around the ones before it.
2. A via with no region of its own rail there: a straight strip on L4 or L5, which the plane around it pours around. A small
   scripted router on a 0.125 mm grid does this. It can end by running into the rail's own region.
3. A via boxed in on both plane layers (under other rails' regions) takes a short hop on L8 to the nearest place a plane
   layer is open, drops a via there, and does the long run on the plane layer. Rails that stay under the SiP go on L8 first:
   their balls are too close together for plane copper to reach all of them.
4. L6 and L3 are the signals'. Power goes there only if none of the above finds a way, and the report lists it.

L2 and L7 are GND, whole.

    python planes.py ir          only the IR drop on the core and DDR rails, in under a minute
    python planes.py check       regions, strips, tracks, IR drop; out/plane_L4.png, plane_L5.png, plane_tracks.png
    python planes.py apply       writes vias, tracks and polygons to the PcbDoc (take the Altium lock)

Frame: mm, origin at the board's lower-left corner.
"""
from __future__ import annotations

import heapq
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

import fanout
import pcbsetup as S
import placement as P
import powerplanes as PP

SPEC = Path(__file__).parent / "planes.txt"
EDGE = 0.55             # plane copper to the outline
OUT = P.OUT
PITCH = 0.125           # the router's grid
EDGE_REACH = 0.15       # a via this far inside a region's edge still lands on its copper

PLANES = ("L5", "L4")
SIGNALS = ("L8", "L6", "L3")
OLD_LAYER = {"L8": 32, "L6": 6, "L3": 3, "L4": S.V5_LAYER["L4_PWR"], "L5": S.V5_LAYER["L5_PWR"]}
W_PLANE = 0.20          # a strip on L4 or L5: these rails carry little, and it fits wherever a signal track would
W_SIGNAL = 0.20         # a track on a signal layer: W_PWR and W_PWR_HI both allow it
W_ROOM = 0.09           # inside the SiP's room: W_SiP's minimum. Anything wider doesn't fit between the vias, 0.5 mm apart
CLR = 0.10              # Clr_Default
CLR_ROOM = 0.09         # Clr_SiP
SAFE = 0.04             # the grid's rounding
DROP_VIA = (0.20, 0.35)     # a track dropping onto its plane: the smallest Via_PWR
ROOM_VIA = PP.SIP_VIA       # the same inside the room
STITCH_VIA = (0.30, 0.50)   # Via_PWR preferred
ROW_COST = 8.0          # on L3 and L6, a step through the SiP's signal rows costs this much
DROP_COST = 2.0         # mm: what a new via is worth
TURN_COST = 0.5         # mm per 45 degrees: keeps strips straight
OTHER_PLANE = 1.2       # a mm on the rail's other plane
GREED = 1.3             # how hard the search pulls towards its target: above 1 it finds a good path, not the very best, fast
MAX_POPS = 40000       # a search that hasn't arrived after this many steps gives up on that layer
SIGNAL_BIAS = {"L8": 3.0}     # a mm on L8, against a mm on a plane layer
MAX_HOP = 12.0          # mm: the longest hop on L8 to reach an open plane layer
FULL = "L4_PWR", "L5_PWR"

# These fill what the others leave on their layer, so a strip of another rail may cross them; they pour around it
FILLERS = {"L5": {"VCC_3V3_SYS", "VCC_3V3_MAIN"}, "L4": {"VDD_1V8", "VCC_5V0"}}
# The rails that take L4 first: the 1.8 V family, and the 5 V family. The rest take L5, the 3.3 V layer.
ON_L4 = {"VDD_1V8", "VDDSHV1", "VDDSHV4", "VDDSHV6", "VDD_1V8_M2", "VDD_1V8_DBG", "VDD_1V0_PHY", "VCC_5V0", "VCC_5V0_HDR",
         "VCC_5V0_HDMI", "VBUS_USBA1", "VBUS_USBA2", "VBUS_DBG", "VBUS_USBC", "VSYS_PD", "VDD_CORE_0V85", "VDDS_DDR_1V2"}
# Rails that stay under the SiP, from its balls to the caps beside it: L8 first
UNDER_SIP = {"VDDA_1V8_OLDI", "VDDA_1V8_USB", "VDDA_1V8_CSI", "VDDA_1V8_PLL0", "VDDA_1V8_PLL1", "VDDA_1V8_PLL2",
             "VDDA_CORE_USB_0V85", "VDDA_CORE_CSI_0V85", "VDDA_3P3_USB", "DDR4_VPP_2V5_SIP", "VDDA_1V8_MCU"}
ROSE = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def corners_clear_outline(pts):
    """Pull a region inside the outline. A corner on the board's corner gets a chamfer tangent to the rounded edge, EDGE
    inside it, so that nothing on the board's corner misses the plane."""
    W, H, r = P.BOARD_W, P.BOARD_H, P.CORNER_R
    pts = [(min(max(x, EDGE), W - EDGE), min(max(y, EDGE), H - EDGE)) for x, y in pts]
    c = 2 * r - (r - EDGE) * math.sqrt(2) - 2 * EDGE    # along each edge, from the inset corner
    out = []
    for i, (x, y) in enumerate(pts):
        if x in (EDGE, W - EDGE) and y in (EDGE, H - EDGE):
            a = pts[i - 1]
            sx = c if x == EDGE else -c
            sy = c if y == EDGE else -c
            first = (x, y + sy) if a[0] == x else (x + sx, y)
            second = (x + sx, y) if a[0] == x else (x, y + sy)
            out += [first, second]
        else:
            out.append((x, y))
    return out


def load_regions(path=SPEC):
    """[(layer, rail, [corners])], in pour order."""
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        f = raw.split("#")[0].split()
        if not f or f[0] == "STITCH":
            continue
        layer, rail, kind = f[0], f[1], f[2]
        if kind == "rect":
            x1, y1, x2, y2 = map(float, f[3:7])
            pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        elif kind == "board":
            pts = [(0.0, 0.0), (P.BOARD_W, 0.0), (P.BOARD_W, P.BOARD_H), (0.0, P.BOARD_H)]
        else:
            pts = [tuple(map(float, c.split(","))) for c in f[3:]]
        out.append((layer, rail, corners_clear_outline(pts)))
    return out


def load_stitches(path=SPEC):
    """[(rail, how many, x1, y1, x2, y2)]: vias that join a rail's regions on two layers."""
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        f = raw.split("#")[0].split()
        if f and f[0] == "STITCH":
            out.append((f[1], int(f[2]), *map(float, f[3:7])))
    return out


def inside(pts, x, y):
    c = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def edge_distance(pts, x, y):
    d = 1e9
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy or 1)))
        d = min(d, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return d


def terminals(fan):
    """{rail: [(x, y, kind)]}: its vias, and its through-hole pads, which reach every layer too."""
    out = defaultdict(list)
    plan, power, pads = fan["plan"], fan["power"], fan["pads"]
    for v in plan.vias:
        if v[4] in power:
            out[v[4]].append((v[0], v[1], v[5]))
    for p in pads:
        if p.tht and p.net in power and p.net not in PP.SURFACE_ONLY:
            out[p.net].append((p.x, p.y, str(p)))
    return out


def on_region(regions, i, x, y):
    """Does region i have copper at this point? Not if a region poured before it, on its layer, is there."""
    layer, rail, pts = regions[i]
    if not inside(pts, x, y) or edge_distance(pts, x, y) < EDGE_REACH:
        return False
    return not any(regions[j][0] == layer and regions[j][1] != rail and inside(regions[j][2], x, y) for j in range(i))


def reach(regions, terms):
    """{rail: {region index: [terminals]}}, and {rail: [terminals on no region of their own]}."""
    hit = defaultdict(lambda: defaultdict(list))
    left = {}
    by_rail = defaultdict(list)
    for i, r in enumerate(regions):
        by_rail[r[1]].append(i)
    for rail, ts in terms.items():
        miss = []
        for t in ts:
            got = False
            for i in by_rail[rail]:
                if on_region(regions, i, t[0], t[1]):
                    hit[rail][i].append(t)
                    got = True
            if not got:
                miss.append(t)
        left[rail] = miss
    return hit, left


# ------------------------------------------------------------------ strips and tracks
class Router:
    """Copper as a count per grid cell, for the centre line of new copper on each layer, and for the centre of a new via."""

    def __init__(self, fan, regions):
        self.fan = fan
        self.regions = regions
        self.nx = int(P.BOARD_W / PITCH) + 1
        self.ny = int(P.BOARD_H / PITCH) + 1
        self.count = {layer: [0] * (self.nx * self.ny) for layer in PLANES + SIGNALS}
        self.via_count = [0] * (self.nx * self.ny)
        self.own = defaultdict(lambda: defaultdict(list))    # net -> layer -> cells it blocks
        self.tracks = []        # (layer, net, x1, y1, x2, y2, width)
        self.new_vias = []      # (x, y, hole, diameter, net)
        self.track_cells = defaultdict(lambda: defaultdict(set))     # net -> layer -> cells on its own copper
        self.masks = {}         # (rail, layer) -> bytes: 1 where the rail has a region on that layer
        self.closed = {}        # (rail, layer) -> bytes: other rails' regions
        self.samples = {}       # (rail, layer) -> points inside its region, 1 mm apart
        self.ux, self.uy = fan["place"]["U1"][:2]
        self.load()

    def in_room(self, x, y):
        return abs(x - self.ux) <= S.ROOM_W_MM / 2 - 0.05 and abs(y - self.uy) <= S.ROOM_H_MM / 2 - 0.05

    def signal_rows(self, x, y):
        dx, dy = x - self.ux, y - self.uy
        return abs(dx) < 7.5 and abs(dy) < 5.0 and (abs(dy) >= 2.0 or dx >= 4.0)

    def cell(self, x, y):
        return round(y / PITCH) * self.nx + round(x / PITCH)

    def xy(self, c):
        return (c % self.nx) * PITCH, (c // self.nx) * PITCH

    def margin(self, layer, x, y):
        """From copper to the centre line of new copper here."""
        if self.in_room(x, y):
            return W_ROOM / 2 + CLR_ROOM + 0.005
        return (W_PLANE if layer in PLANES else W_SIGNAL) / 2 + CLR + SAFE

    def stamp_disc(self, layer, net, x, y, r):
        n = int(r / PITCH) + 1
        ci, cj = round(x / PITCH), round(y / PITCH)
        arr = self.via_count if layer == "via" else self.count[layer]
        store = None if layer == "via" else self.own[net][layer]
        for j in range(max(0, cj - n), min(self.ny, cj + n + 1)):
            for i in range(max(0, ci - n), min(self.nx, ci + n + 1)):
                if math.hypot(i * PITCH - x, j * PITCH - y) < r:
                    c = j * self.nx + i
                    arr[c] += 1
                    if store is not None:
                        store.append(c)

    def stamp_rect(self, layer, net, x1, y1, x2, y2, m):
        arr = self.via_count if layer == "via" else self.count[layer]
        store = None if layer == "via" else self.own[net][layer]
        for j in range(max(0, math.ceil((y1 - m) / PITCH)), min(self.ny, math.floor((y2 + m) / PITCH) + 1)):
            for i in range(max(0, math.ceil((x1 - m) / PITCH)), min(self.nx, math.floor((x2 + m) / PITCH) + 1)):
                c = j * self.nx + i
                arr[c] += 1
                if store is not None:
                    store.append(c)

    def add_via(self, x, y, dia, net):
        for layer in PLANES + SIGNALS:
            self.stamp_disc(layer, net, x, y, dia / 2 + self.margin(layer, x, y))
        # a new via's centre: its own pad and hole clear this one
        small = ROOM_VIA[1] if self.in_room(x, y) else DROP_VIA[1]
        self.stamp_disc("via", net, x, y, dia / 2 + small / 2 + 0.20)

    def add_segment(self, layers, net, x1, y1, x2, y2, w):
        steps = max(1, int(math.hypot(x2 - x1, y2 - y1) / (PITCH * 0.75)))
        for k in range(steps + 1):
            x = x1 + (x2 - x1) * k / steps
            y = y1 + (y2 - y1) * k / steps
            for layer in layers:
                self.stamp_disc(layer, net, x, y, w / 2 + self.margin(layer, x, y))
            self.stamp_disc("via", net, x, y, w / 2 + DROP_VIA[1] / 2 + CLR + SAFE)

    def load(self):
        fan = self.fan
        plan = fan["plan"]
        rim = math.ceil(EDGE / PITCH)
        edge = [j * self.nx + i for j in range(self.ny) for i in range(self.nx)
                if i < rim or j < rim or i >= self.nx - rim or j >= self.ny - rim]
        for layer in list(PLANES + SIGNALS) + ["via"]:
            arr = self.via_count if layer == "via" else self.count[layer]
            for c in edge:
                arr[c] += 1
        for v in plan.vias:
            self.add_via(v[0], v[1], v[3], v[4])
        for p in fan["pads"]:
            if p.tht:
                for layer in PLANES + SIGNALS:
                    self.stamp_rect(layer, p.net, p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh, self.margin(layer, p.x, p.y) + 0.05)
                self.stamp_rect("via", p.net, p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh, DROP_VIA[1] / 2 + 0.20)
            else:
                if p.side == "B":
                    self.stamp_rect("L8", p.net, p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh, self.margin("L8", p.x, p.y))
                self.stamp_rect("via", p.net, p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh, DROP_VIA[1] / 2 + CLR + SAFE)
        for t in plan.stubs:
            self.add_segment(["L8"] if t[0] == "B" else [], t[6], t[1], t[2], t[3], t[4], t[5])
        # a strip can't run through another rail's region, only through the fillers
        size = 2 * math.ceil((W_PLANE / 2 + CLR + SAFE) / PITCH) + 1
        self.grown = {i: self.raster(r[2]).filter(ImageFilter.MaxFilter(size)) for i, r in enumerate(self.regions)
                      if r[1] not in FILLERS[r[0]]}

    def closed_to(self, rail, layer):
        """1 in each cell of this layer that a strip of this rail can't use: other rails' regions."""
        key = (rail, layer)
        if key not in self.closed:
            im = Image.new("L", (self.nx, self.ny), 0)
            for i, g in self.grown.items():
                if self.regions[i][0] == layer and self.regions[i][1] != rail:
                    im = ImageChops.lighter(im, g)
            self.closed[key] = im.tobytes()
        return self.closed[key]

    def raster(self, pts):
        im = Image.new("L", (self.nx, self.ny), 0)
        ImageDraw.Draw(im).polygon([(x / PITCH, y / PITCH) for x, y in pts], fill=255)
        return im

    def region_mask(self, rail, layer):
        """1 in each grid cell where this rail's regions on this layer have copper, well inside the edge."""
        key = (rail, layer)
        if key in self.masks:
            return self.masks[key]
        im = Image.new("L", (self.nx, self.ny), 0)
        for i, (lay, r, pts) in enumerate(self.regions):
            if r != rail or lay != layer:
                continue
            piece = self.raster(pts)
            pd = ImageDraw.Draw(piece)
            for j in range(i):
                if self.regions[j][0] == layer and self.regions[j][1] != rail:
                    pd.polygon([(x / PITCH, y / PITCH) for x, y in self.regions[j][2]], fill=0)
            im.paste(255, mask=piece)
        im = im.filter(ImageFilter.MinFilter(5))
        self.masks[key] = im.point(lambda v: 1 if v else 0).tobytes()
        return self.masks[key]

    def lift(self, net, sign):
        for layer, cells in self.own[net].items():
            arr = self.count[layer]
            for c in cells:
                arr[c] += sign

    def aim(self, rail, start, joined):
        """The nearest thing this rail could connect to: what a search pulls towards."""
        pts = [(t[0], t[1]) for t in joined]
        for layer in PLANES:
            key = (rail, layer)
            if key not in self.samples:
                m = self.region_mask(rail, layer)
                self.samples[key] = [self.xy(j * self.nx + i) for j in range(0, self.ny, 8) for i in range(0, self.nx, 8)
                                     if m[j * self.nx + i]]
            pts += self.samples[key]
        for cells in self.track_cells[rail].values():
            pts += [self.xy(c) for c in list(cells)[::8]]
        pts = [q for q in pts if q != (start[0], start[1])]
        if not pts:
            return start[0], start[1]
        return min(pts, key=lambda q: math.hypot(q[0] - start[0], q[1] - start[1]))

    def search(self, layer, rail, start, goals, limit, box, target, max_pops=MAX_POPS, may_drop=True):
        """Cheapest copper on one layer from a terminal to any goal: its rail's vias and copper, its region on this layer, or
        a place in its region on another layer where a via fits. Prefers straight lines.
        Returns (cost, path of cells, needs a via at the end)."""
        arr = self.count[layer]
        nx = self.nx
        bx1, by1, bx2, by2 = box
        rx1, ry1 = (self.ux - S.ROOM_W_MM / 2) / PITCH, (self.uy - S.ROOM_H_MM / 2) / PITCH
        rx2, ry2 = (self.ux + S.ROOM_W_MM / 2) / PITCH, (self.uy + S.ROOM_H_MM / 2) / PITCH
        rowed = layer in ("L3", "L6")
        same = self.region_mask(rail, layer) if layer in PLANES else None
        others = [self.region_mask(rail, q) for q in PLANES if q != layer]
        closed = self.closed_to(rail, layer) if layer in PLANES else None
        tx, ty = target[0] / PITCH, target[1] / PITCH
        h = [(0.0, 0.0, start, 8)]
        dist = {start * 9 + 8: 0.0}
        prev = {start * 9 + 8: None}
        pops = 0
        while h:
            _, d, c, way = heapq.heappop(h)
            if d > dist[c * 9 + way]:
                continue
            if d > limit:
                return None
            pops += 1
            if pops > max_pops:
                return None
            touch = c != start and (c in goals or (same is not None and same[c]))
            drop = may_drop and not touch and c != start and self.via_count[c] == 0 and any(m[c] for m in others)
            if touch or drop:
                path = []
                st = c * 9 + way
                while st is not None:
                    path.append(st // 9)
                    st = prev[st]
                return d + (DROP_COST if drop else 0.0), path, drop
            i, j = c % nx, c // nx
            for k, (dx, dy) in enumerate(ROSE):
                a, b = i + dx, j + dy
                if not (bx1 <= a <= bx2 and by1 <= b <= by2):
                    continue
                n = b * nx + a
                if arr[n] > 0 or (closed is not None and closed[n]):
                    continue
                inside_room = rx1 <= a <= rx2 and ry1 <= b <= ry2
                # Outside the room, no cutting a corner between two blocked cells. Inside it, that diagonal between two
                # vias is the only way out of the 0.5 mm via field.
                if not inside_room and dx and dy and arr[c + dx] > 0 and arr[c + dy * nx] > 0:
                    continue
                step = PITCH * (1.414 if dx and dy else 1.0)
                if inside_room:
                    if rowed and self.signal_rows(a * PITCH, b * PITCH):
                        step *= ROW_COST
                    # along a channel, keep to one side of it: down the middle, one track fills it
                    if (dy and not dx and a % 2 == 0) or (dx and not dy and b % 2 == 0):
                        step *= 1.5
                if way != 8 and way != k:
                    step += TURN_COST * min((k - way) % 8, (way - k) % 8)
                nd = d + step
                key = n * 9 + k
                if nd < dist.get(key, 1e18):
                    dist[key] = nd
                    prev[key] = c * 9 + way
                    # octile distance to the target, in mm
                    ax, ay = abs(a - tx), abs(b - ty)
                    rest = (max(ax, ay) + 0.414 * min(ax, ay)) * PITCH
                    heapq.heappush(h, (nd + GREED * rest, nd, n, k))
        return None

    def hop_out(self, rail, start, layer):
        """The shortest hop on L8 from a terminal to where `layer` is open for this rail and a via fits.
        Returns the path of cells, or None."""
        arr = self.count["L8"]
        closed = self.closed_to(rail, layer)
        open_arr = self.count[layer]
        nx = self.nx
        limit = MAX_HOP
        h = [(0.0, start)]
        dist = {start: 0.0}
        prev = {start: None}
        while h:
            d, c = heapq.heappop(h)
            if d > dist[c]:
                continue
            if d > limit:
                return None
            # far enough from where it started to need a via of its own
            if d > 0.6 and self.via_count[c] == 0 and not closed[c] and open_arr[c] == 0:
                path = []
                n = c
                while n is not None:
                    path.append(n)
                    n = prev[n]
                return path
            for dx, dy in ROSE:
                n = c + dx + dy * nx
                if not 0 <= n < len(arr) or arr[n] > 0:
                    continue
                nd = d + PITCH * (1.414 if dx and dy else 1.0)
                if nd < dist.get(n, 1e18):
                    dist[n] = nd
                    prev[n] = c
                    heapq.heappush(h, (nd, n))
        return None

    def connect(self, rail, start, joined):
        """Copper from one terminal to the rest of its rail. joined: the terminals already together."""
        self.lift(rail, -1)
        pref = "L4" if rail in ON_L4 else "L5"
        other = "L5" if pref == "L4" else "L4"
        bias = {pref: 1.0, other: OTHER_PLANE, **SIGNAL_BIAS}
        if rail in UNDER_SIP:
            bias["L8"] = 0.9
        order = sorted(bias, key=bias.get)
        near = min((abs(start[0] - t[0]) + abs(start[1] - t[1]) for t in joined), default=20.0)
        best = None
        target = self.aim(rail, start, joined)
        try:
            src = self.cell(start[0], start[1])
            box = (0, 0, self.nx - 1, self.ny - 1)
            for layer in order:
                goals = {self.cell(t[0], t[1]) for t in joined} | self.track_cells[rail][layer]
                limit = best[0] / bias[layer] if best else 1e9
                # A long run: worth a bigger budget on the plane layers before it settles for a signal layer
                pops = MAX_POPS * 5 if near > 15.0 and layer in PLANES else MAX_POPS
                got = self.search(layer, rail, src, goals, limit, box, target, pops)
                if got:
                    cost = got[0] * bias[layer]
                    if best is None or cost < best[0]:
                        best = (cost, layer, got[1], got[2])
                    if got[0] < near * 1.5 + 3.0:
                        break
            if best is None:
                # a long way, or a hard one: once more with a bigger budget, on the rail's own plane and on L8
                for layer in (pref, "L8"):
                    goals = {self.cell(t[0], t[1]) for t in joined} | self.track_cells[rail][layer]
                    got = self.search(layer, rail, src, goals, 1e9, box, target, MAX_POPS * 10)
                    if got:
                        best = (got[0] * bias[layer], layer, got[1], got[2])
                        break
            # Boxed in on the plane layers: a short hop on L8 to where one is open, then the long run there
            if rail not in UNDER_SIP and (best is None or best[1] == "L8") and near > MAX_HOP / 2:
                for layer in (pref, other):
                    hop = self.hop_out(rail, src, layer)
                    if not hop:
                        continue
                    goals = {self.cell(t[0], t[1]) for t in joined} | self.track_cells[rail][layer]
                    got = self.search(layer, rail, hop[0], goals, 1e9, box, target, MAX_POPS * 10)
                    if got:
                        cost = (got[0] + len(hop) * PITCH * SIGNAL_BIAS["L8"] + DROP_COST) * bias[layer]
                        if best is None or cost < best[0]:
                            best = (cost, layer, got[1], got[2], hop)
                        break
            # Nothing on L4, L5 or L8: the signal layers, as a last resort
            if best is None:
                for layer in ("L6", "L3"):
                    goals = {self.cell(t[0], t[1]) for t in joined} | self.track_cells[rail][layer]
                    got = self.search(layer, rail, src, goals, 1e9, box, target, MAX_POPS * 10)
                    if got:
                        best = (got[0], layer, got[1], got[2])
                        break
        finally:
            self.lift(rail, 1)
        if best is None:
            return False
        cost, layer, path, drop = best[:4]
        if len(best) == 5:
            # the hop: L8 from the terminal to a new via, and the plane layer from there
            hop = best[4]
            self.lay(rail, "L8", hop)
            x, y = self.xy(hop[0])
            h_hole, h_dia = ROOM_VIA if self.in_room(x, y) else DROP_VIA
            self.new_vias.append((x, y, h_hole, h_dia, rail))
            self.add_via(x, y, h_dia, rail)
        self.lay(rail, layer, path)
        if drop:
            x, y = self.xy(path[0])
            hole, dia = ROOM_VIA if self.in_room(x, y) else DROP_VIA
            self.new_vias.append((x, y, hole, dia, rail))
            self.add_via(x, y, dia, rail)
        return True

    def lay(self, rail, layer, path):
        """A path of cells as straight segments, each one wholly inside the SiP's room or wholly outside it."""
        pts = [self.xy(c) for c in path]
        self.track_cells[rail][layer] |= set(path)
        keep = [pts[0]]
        for k in range(1, len(pts) - 1):
            u, v, w = keep[-1], pts[k], pts[k + 1]
            turned = abs((v[0] - u[0]) * (w[1] - v[1]) - (v[1] - u[1]) * (w[0] - v[0])) > 1e-9
            crossed = self.in_room(v[0], v[1]) != self.in_room(w[0], w[1])
            if turned or crossed:
                keep.append(v)
        keep.append(pts[-1])
        for a, b in zip(keep, keep[1:]):
            room = self.in_room(a[0], a[1]) and self.in_room(b[0], b[1])
            w = W_ROOM if room else (W_PLANE if layer in PLANES else W_SIGNAL)
            self.tracks.append((layer, rail, a[0], a[1], b[0], b[1], w))
            self.add_segment([layer], rail, a[0], a[1], b[0], b[1], w)


LONG_RUNS = {"VDD_SDIO_LDO1", "DDR4_VPP_2V5"}


def route_rest(regions, fan, terms, hit, left):
    """Every terminal not on a region gets copper to the rest of its rail. The deepest balls go first: they have the fewest
    ways out."""
    r = Router(fan, regions)
    failed = defaultdict(list)
    for rail, n, x1, y1, x2, y2 in load_stitches():
        placed = []
        for j in range(math.ceil(y1 / PITCH), math.floor(y2 / PITCH) + 1):
            for i in range(math.ceil(x1 / PITCH), math.floor(x2 / PITCH) + 1):
                x, y = i * PITCH, j * PITCH
                if r.via_count[r.cell(x, y)] == 0 and all(math.hypot(x - q[0], y - q[1]) >= (x2 - x1) / n for q in placed) and len(placed) < n:
                    placed.append((x, y))
                    r.new_vias.append((x, y, STITCH_VIA[0], STITCH_VIA[1], rail))
                    r.add_via(x, y, STITCH_VIA[1], rail)
        print(f"stitching vias on {rail}: {len(placed)} of {n}", [(round(a, 2), round(b, 2)) for a, b in placed])
        for q in placed:
            for i, reg in enumerate(regions):
                if reg[1] == rail and on_region(regions, i, q[0], q[1]):
                    hit[rail][i].append((q[0], q[1], "stitch"))
    # The core's analog taps: from the bead input to a core ball's via, on L8, with no via into the plane on the way
    ball = next(p for p in fan["pads"] if p.ref == "U1" and p.name == fanout.TAP_BALL)
    tap_via = min((v for v in fan["plan"].vias if v[4] == ball.net and v[5] == "sip"), key=lambda v: math.hypot(v[0] - ball.x, v[1] - ball.y))
    for ref, pin in sorted(fanout.TAPS):
        p = next(q for q in fan["pads"] if q.ref == ref and q.name == pin)
        r.lift(p.net, -1)
        goals = {r.cell(tap_via[0], tap_via[1])} | r.track_cells[p.net]["L8"]
        got = r.search("L8", p.net, r.cell(p.x, p.y), goals, 1e9, (0, 0, r.nx - 1, r.ny - 1), tap_via[:2], MAX_POPS * 10, False)
        r.lift(p.net, 1)
        if got:
            r.lay(p.net, "L8", got[1])
        else:
            failed[p.net].append((p.x, p.y, ref))
    by_rail = defaultdict(list)
    for i, reg in enumerate(regions):
        by_rail[reg[1]].append(i)
    balls = {q[2] for q in fan["parts"]["U1"].pads}
    ux, uy = fan["place"]["U1"][:2]

    def depth(rail):
        best = 0.0
        for t in terms[rail]:
            if abs(t[0] - ux) < 7 and abs(t[1] - uy) < 4.5:
                best = max(best, min(7 - abs(t[0] - ux), 4.5 - abs(t[1] - uy)))
        return best

    def span(rail):
        ts = terms[rail]
        return max(t[0] for t in ts) - min(t[0] for t in ts) + max(t[1] for t in ts) - min(t[1] for t in ts)

    # The long PMIC runs claim their way along the plane layers before the strips around the SiP close it off
    order = sorted(terms, key=lambda n: (n not in LONG_RUNS, n not in balls, -depth(n), span(n)))
    t0 = time.perf_counter()
    for k, rail in enumerate(order):
        print(f"  {time.perf_counter() - t0:6.1f} s  {k + 1}/{len(order)} {rail}: {len(left[rail])} to connect", flush=True)
        todo = list(left[rail])
        joined = [t for ts in hit[rail].values() for t in ts]
        # The ball vias go last, each searching outwards: into the ball field from outside, a search finds a wall
        deep = lambda t: abs(t[0] - ux) < 7 and abs(t[1] - uy) < 4.5
        if not joined and not by_rail[rail]:
            first = sorted(todo, key=lambda t: (deep(t), abs(t[0] - ux) + abs(t[1] - uy)))[0]
            joined = [first]
            todo.remove(first)
        while todo:
            todo.sort(key=lambda t: (deep(t), min((abs(t[0] - q[0]) + abs(t[1] - q[1]) for q in joined), default=0.0)))
            t = todo.pop(0)
            if r.connect(rail, t, joined):
                joined.append(t)
            else:
                failed[rail].append(t)
    # Strips cut planes, and a pour can lose a corner around a via. Find what the pour would leave apart, and join it up.
    r.apart = {}
    for attempt in range(3):
        groups, pieces = pour_groups(regions, fan, r, terms)
        apart = {rail: g for rail, g in groups.items() if len(g) > 1}
        r.apart = {rail: len(g) for rail, g in apart.items()}
        print(f"  pour check {attempt + 1}: {sum(len(g) - 1 for g in apart.values())} pieces apart in {len(apart)} rails", flush=True)
        if not apart:
            break
        for rail, g in apart.items():
            g = sorted(g, key=len, reverse=True)
            main = list(g[0])
            for layer in PLANES:
                r.masks[(rail, layer)] = pieces(rail, layer, g[0])
            for other in g[1:]:
                best = min(other, key=lambda t: min(math.hypot(t[0] - q[0], t[1] - q[1]) for q in main))
                if r.connect(rail, best, main):
                    main += list(other)
    # What the last repairs left: the number the report gives is measured, not the one before them
    groups, _ = pour_groups(regions, fan, r, terms)
    apart = {rail: sorted(g, key=len, reverse=True) for rail, g in groups.items() if len(g) > 1}
    r.apart = {rail: len(g) for rail, g in apart.items()}
    r.apart_where = {rail: [sorted((round(t[0], 1), round(t[1], 1)) for t in piece)[:4] for piece in g[1:]] for rail, g in apart.items()}
    r.narrowed, r.tight = fit_widths(r, fan)
    return r, failed


def pour_groups(regions, fan, router, terms):
    """What the pours and tracks really join. Each layer is drawn for each rail as Altium will pour it: its regions, less
    regions poured before them, other rails' tracks and clearances round other rails' vias and through-hole pads; plus its own
    tracks, stubs and pads. Returns ({rail: [sets of terminals that copper joins]}, pieces), where pieces(rail, layer, group)
    gives the cells of that layer's copper that belong to a group."""
    nx, ny = router.nx, router.ny
    plan, power = fan["plan"], fan["power"]
    vias = list(plan.vias) + [(q[0], q[1], q[2], q[3], q[4], "new") for q in router.new_vias]
    tht = [p for p in fan["pads"] if p.tht]
    per_rail = defaultdict(lambda: defaultdict(list))
    for t in router.tracks:
        per_rail[t[1]][t[0]].append(t)
    for t in plan.stubs:
        layer = "L8" if t[0] == "B" else "L1"
        per_rail[t[6]][layer].append((layer, t[6], t[1], t[2], t[3], t[4], t[5]))
    smd = defaultdict(lambda: defaultdict(list))
    for p in fan["pads"]:
        if not p.tht and p.net in power:
            smd[p.net]["L8" if p.side == "B" else "L1"].append(p)

    def line(d, t, width, fill):
        # at least 2 cells: a one-cell diagonal has corners that a fill can't get through
        d.line([(t[2] / PITCH, t[3] / PITCH), (t[4] / PITCH, t[5] / PITCH)], fill=fill, width=max(2, round(width / PITCH)))

    def disc(d, x, y, r, fill):
        r /= PITCH
        d.ellipse([x / PITCH - r, y / PITCH - r, x / PITCH + r, y / PITCH + r], fill=fill)

    # what each rail's pour can't have, by plane layer
    base = {}
    for layer in PLANES:
        here = [(i, r) for i, r in enumerate(regions) if r[0] == layer]
        base[layer] = here
    labels = {}
    groups = {}
    for rail, ts in terms.items():
        ts = list(ts) + [(q[0], q[1], "new") for q in router.new_vias if q[4] == rail]
        if not ts:
            continue
        parent = {t: t for t in ts}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for layer in PLANES + SIGNALS + ("L1",):
            im = Image.new("L", (nx, ny), 0)
            d = ImageDraw.Draw(im)
            mine = [r for r in base.get(layer, []) if r[1][1] == rail]
            if mine:
                first = min(i for i, _ in mine)
                for _, r in mine:
                    d.polygon([(x / PITCH, y / PITCH) for x, y in r[2]], fill=255)
                # regions poured before this rail's take their copper, with the clearance
                earlier = Image.new("L", (nx, ny), 0)
                ed = ImageDraw.Draw(earlier)
                for i, r in base[layer]:
                    if i < first and r[1] != rail:
                        ed.polygon([(x / PITCH, y / PITCH) for x, y in r[2]], fill=255)
                d.bitmap((0, 0), earlier.filter(ImageFilter.MaxFilter(3)), fill=0)
                for o, by in per_rail.items():
                    if o != rail:
                        for t in by.get(layer, ()):
                            line(d, t, t[6] + 2 * CLR, 0)
                for v in vias:
                    if v[4] != rail:
                        disc(d, v[0], v[1], (0.275 if v[3] <= 0.26 else v[3] / 2 + 0.20), 0)
                for q in tht:
                    if q.net != rail:
                        disc(d, q.x, q.y, max(q.hw, q.hh) + 0.20, 0)
            for t in per_rail[rail].get(layer, ()):
                line(d, t, t[6], 255)
            for q in smd[rail].get(layer, ()):
                d.rectangle([(q.x - q.hw) / PITCH, (q.y - q.hh) / PITCH, (q.x + q.hw) / PITCH, (q.y + q.hh) / PITCH], fill=255)
            if not mine and not per_rail[rail].get(layer) and not smd[rail].get(layer):
                continue
            # every via of the rail has a pad on every layer
            for t in ts:
                disc(d, t[0], t[1], 0.13, 255)
            data = bytearray(im.tobytes())
            lab = 0
            seen = {}
            for t in ts:
                c = router.cell(t[0], t[1])
                if data[c] == 255:
                    lab += 1
                    st = [c]
                    data[c] = min(lab, 250)
                    me = data[c]
                    while st:
                        a = st.pop()
                        for b in (a - 1, a + 1, a - nx, a + nx):
                            if 0 <= b < len(data) and data[b] == 255:
                                data[b] = me
                                st.append(b)
                g = data[c]
                if g in seen:
                    parent[find(t)] = find(seen[g])
                else:
                    seen[g] = t
            labels[(rail, layer)] = (data, {t: data[router.cell(t[0], t[1])] for t in ts})
        out = defaultdict(set)
        for t in ts:
            out[find(t)].add(t)
        groups[rail] = list(out.values())

    def pieces(rail, layer, group):
        """A mask of the copper on this layer joined to this group, well inside its edge."""
        if (rail, layer) not in labels:
            return bytes(nx * ny)
        data, at = labels[(rail, layer)]
        keep = {at[t] for t in group if t in at and at[t]}
        table = bytes(255 if v in keep and v != 255 else 0 for v in range(256))
        im = Image.frombytes("L", (nx, ny), bytes(data).translate(table)).filter(ImageFilter.MinFilter(5))
        return im.point(lambda v: 1 if v else 0).tobytes()

    return groups, pieces




def fit_widths(router, fan):
    """The grid is coarse beside a via. Measure each new segment against the real copper, and narrow it until it fits.
    Returns (how many narrowed, the segments that still don't fit)."""
    ux, uy = fan["place"]["U1"][:2]
    plan = fan["plan"]
    round_things = defaultdict(list)    # 1 mm cell -> (x, y, r, net)
    rects = defaultdict(list)
    def bucket(x, y):
        return int(x), int(y)
    for v in list(plan.vias) + [(q[0], q[1], q[2], q[3], q[4]) for q in router.new_vias]:
        round_things[bucket(v[0], v[1])].append((v[0], v[1], v[3] / 2, v[4]))
    for p in fan["pads"]:
        if p.tht or p.side == "B":
            rects[bucket(p.x, p.y)].append((p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh, p.net, p.tht))
    segs = defaultdict(list)
    for t in plan.stubs:
        if t[0] == "B":
            segs["L8"].append((t[1], t[2], t[3], t[4], t[5], t[6]))
    for t in router.tracks:
        segs[t[0]].append((t[2], t[3], t[4], t[5], t[6], t[1]))
    narrowed = 0
    tight = []

    def gap_at(layer, net, x1, y1, x2, y2):
        """Smallest distance from this centre line to other nets' copper edges, on this layer."""
        best = 9.0
        i1, i2 = int(min(x1, x2)) - 2, int(max(x1, x2)) + 2
        j1, j2 = int(min(y1, y2)) - 2, int(max(y1, y2)) + 2
        for i in range(i1, i2 + 1):
            for j in range(j1, j2 + 1):
                for (cx, cy, rad, n) in round_things.get((i, j), ()):
                    if n != net:
                        best = min(best, PP.seg_seg_gap((x1, y1, x2, y2), (cx, cy, cx, cy)) - rad)
                for (a, b, c, d, n, tht) in rects.get((i, j), ()):
                    if n != net and (tht or layer == "L8"):
                        best = min(best, PP.seg_rect_gap(x1, y1, x2, y2, (a, b, c, d)))
        for (a, b, c, d, w2, n) in segs[layer]:
            if n != net and not (max(a, c) < i1 or min(a, c) > i2 or max(b, d) < j1 or min(b, d) > j2):
                best = min(best, PP.seg_seg_gap((x1, y1, x2, y2), (a, b, c, d)) - w2 / 2)
        return best

    for k, t in enumerate(router.tracks):
        layer, net, x1, y1, x2, y2, w = t
        room = router.in_room(x1, y1) or router.in_room(x2, y2)
        rule = CLR_ROOM + 0.005 if room else CLR + 0.005
        g = gap_at(layer, net, x1, y1, x2, y2)
        if g - w / 2 >= rule:
            continue
        floor = W_ROOM if room else 0.15
        fits = [n for n in (0.25, 0.20, 0.15, 0.12, 0.09) if floor <= n < w and g - n / 2 >= rule]
        if fits:
            router.tracks[k] = (layer, net, x1, y1, x2, y2, fits[0])
            narrowed += 1
        else:
            tight.append((layer, net, round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2), round(g, 3)))
    return narrowed, tight


# ------------------------------------------------------------------ IR drop
def ir_report(regions, fan):
    """The core and DDR rails on the copper as drawn, on the 0.25 mm grid of powerplanes.ir_drop."""
    plan, pads, nets = fan["plan"], fan["pads"], fan["nets"]
    g = PP.Grid(FULL)
    for v in plan.vias:
        r = PP.SIP_ANTI if v[3] <= 0.26 else v[3] / 2 + PP.ANTI_CLR
        if v[4] in fan["power"]:
            g.mark_anti(v[0], v[1], r, g.rid(v[4]))
        else:
            g.mark_anti(v[0], v[1], r, -1, terminal=False)
    for rail, n, x1, y1, x2, y2 in load_stitches():
        for q in range(n):
            g.mark_anti(x1 + (x2 - x1) * (q + 0.5) / n, (y1 + y2) / 2, STITCH_VIA[1] / 2 + PP.ANTI_CLR, g.rid(rail))
    for p in pads:
        if p.tht:
            g.mark_anti(p.x, p.y, max(p.hw, p.hh) + PP.ANTI_CLR, -1, terminal=False)
    name = {"L4": "L4_PWR", "L5": "L5_PWR"}
    for i, (layer, rail, pts) in reversed(list(enumerate(regions))):
        k = g.rid(rail)
        own = g.owner[name[layer]]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        for j in range(int(min(ys) / PP.GRID), int(max(ys) / PP.GRID) + 2):
            for a in range(int(min(xs) / PP.GRID), int(max(xs) / PP.GRID) + 2):
                if 0 <= a < PP.NX and 0 <= j < PP.NY:
                    c = j * PP.NX + a
                    if inside(pts, a * PP.GRID, j * PP.GRID) and g.ap[c] in (0, k):
                        own[c] = k
    pad_at = {(p.ref, p.name): p for p in pads}
    lines = []
    for net, src in PP.SOURCE.items():
        ref, pin = src.split(".")
        sp = pad_at[(ref, pin)]
        sources = [g.cell(v[0], v[1]) for v in plan.vias if v[4] == net and abs(v[0] - sp.x) < 3 and abs(v[1] - sp.y) < 3]
        loads = []
        for b in [n.split(".")[1] for n in nets[net] if n.startswith("U1.")]:
            bp = pad_at[("U1", b)]
            near = min((v for v in plan.vias if v[4] == net and v[5] == "sip"), key=lambda v: abs(v[0] - bp.x) + abs(v[1] - bp.y))
            loads.append(g.cell(near[0], near[1]))
        r = PP.ir_drop(g, net, sources, loads, PP.CURRENT.get(net, 0.5))
        if r is None:
            lines.append(f"{net}: no path on the planes")
            continue
        x, nodes, lv = r
        lines.append(f"{net}: {PP.CURRENT.get(net)} A from {src}: worst ball {abs(x[lv]).max() * 1e3:.1f} mV, mean ball {abs(x[lv]).mean() * 1e3:.1f} mV")
        if net == "VDD_CORE_0V85":
            ball = pad_at[("U1", fanout.TAP_BALL)]
            for tap in ("FB300", "FB301"):
                v = min((w for w in plan.vias if w[4] == net and w[5] == "sip"), key=lambda w: math.hypot(w[0] - ball.x, w[1] - ball.y))
                c = g.cell(v[0], v[1])
                for li in range(len(g.planes)):
                    n = nodes.get((li, c))
                    if n is not None:
                        lines.append(f"  {tap} input {abs(x[n]) * 1e3:.1f} mV: {abs(abs(x[lv]).mean() - abs(x[n])) * 1e3:.1f} mV from the mean ball (limit 8.5 mV)")
                        break
    return lines


# ------------------------------------------------------------------ output
def spec_text(regions, fan, router, pcb):
    def co(v):
        return int(round(v / 0.0254 * 10000))

    plan, power = fan["plan"], fan["power"]
    lines = [str(pcb)]
    lines += [f"NET|{n}" for n in sorted(set(power) | {"GND"})]
    signal_nets = ({t[6] for t in plan.stubs} | {v[4] for v in plan.vias}) - set(power) - {"GND"}
    lines += [f"SIGNET|{n}" for n in sorted(signal_nets)]
    b = P.crt_rect(fan["parts"]["U1"], *fan["place"]["U1"])
    m = fanout.SIGNET_MARGIN
    lines.append(f"AREA|{co(b[0] - m)}|{co(b[1] - m)}|{co(b[2] + m)}|{co(b[3] + m)}")
    rows = []
    for v in plan.vias:
        rows.append((v[4], 0, f"VIA|{co(v[0])}|{co(v[1])}|{co(v[2])}|{co(v[3])}|{v[4]}"))
    for x, y, hole, dia, net in router.new_vias:
        rows.append((net, 0, f"VIA|{co(x)}|{co(y)}|{co(hole)}|{co(dia)}|{net}"))
    for t in plan.stubs:
        layer = 1 if t[0] == "T" else 32
        rows.append((t[6], 1, f"TRK|{layer}|{co(t[1])}|{co(t[2])}|{co(t[3])}|{co(t[4])}|{co(t[5])}|{t[6]}"))
    for layer, net, x1, y1, x2, y2, w in router.tracks:
        rows.append((net, 1, f"TRK|{OLD_LAYER[layer]}|{co(x1)}|{co(y1)}|{co(x2)}|{co(y2)}|{co(w)}|{net}"))
    rows.sort(key=lambda r: (r[0], r[1]))
    lines += [r[2] for r in rows]
    order = 1
    name = {"L4": "L4_PWR", "L5": "L5_PWR"}
    for layer, rail, pts in regions:
        lines.append(f"POLY|{S.V5_LAYER[name[layer]]}|{rail}|{order}|" + ";".join(f"{co(x)},{co(y)}" for x, y in pts))
        order += 1
    whole = corners_clear_outline([(0.0, 0.0), (P.BOARD_W, 0.0), (P.BOARD_W, P.BOARD_H), (0.0, P.BOARD_H)])
    for pl in ("L2_GND", "L7_GND"):
        lines.append(f"POLY|{S.V5_LAYER[pl]}|GND|{order}|" + ";".join(f"{co(x)},{co(y)}" for x, y in whole))
        order += 1
    return "\n".join(lines) + "\n"


def report(regions, fan, terms, hit, left, router, failed):
    print(f"{len(regions)} regions")
    on_planes = sum(1 for r in terms if not left[r] and hit[r])
    print("rails all on regions:", on_planes, "of", len(terms), "; vias reached by a strip or track:", sum(len(v) for v in left.values()))
    length = Counter()
    per_rail = defaultdict(Counter)
    for t in router.tracks:
        d = math.hypot(t[4] - t[2], t[5] - t[3])
        length[t[0]] += d
        per_rail[t[1]][t[0]] += d
    print("mm per layer:", {k: round(v) for k, v in sorted(length.items())}, "total", round(sum(length.values())))
    sig = {r: {k: round(v) for k, v in c.items() if k in SIGNALS} for r, c in per_rail.items()}
    print("on signal layers:", sorted(((r, c) for r, c in sig.items() if c), key=lambda rc: -sum(rc[1].values())))
    pl = {r: {k: round(v) for k, v in c.items() if k in PLANES} for r, c in per_rail.items()}
    print("strips on the plane layers:", sorted(((r, c) for r, c in pl.items() if c), key=lambda rc: -sum(rc[1].values())))
    print("new vias:", len(router.new_vias))
    print("narrowed to fit:", router.narrowed, "; still too close:", len(router.tight), router.tight[:12])
    print("terminals with nothing found:", {k: [(round(t[0], 1), round(t[1], 1)) for t in v] for k, v in failed.items()})
    print("rails the pour would still leave in pieces:", router.apart)
    for rail, where in router.apart_where.items():
        print(f"  {rail} apart from its main piece: {where}")
    thin = [(int(t[0][1]), t[2], t[3], t[4], t[5], t[6]) for t in router.tracks if t[0] in ("L3", "L6")]
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(2) as pool:
        escape = pool.submit(fanout.escape_check, fan, 0.05, fanout.W_SIG, 0.09, thin)
        drops = pool.submit(ir_report, regions, fan)
        print("SiP signal vias that can get out, with the tracks down:", escape.result())
        for line in drops.result():
            print(line)


def render(regions, fan, router, left):
    """One picture per plane layer, as drawn, with its strips; and one of what is left on the signal layers."""
    s = 16
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
    colours = {}
    palette = [(214, 112, 112), (112, 170, 214), (130, 200, 130), (214, 180, 96), (170, 130, 214), (96, 200, 190),
               (214, 140, 190), (160, 170, 110), (120, 140, 214), (214, 150, 110), (140, 200, 160), (190, 190, 120)]
    files = []
    X = lambda v: v * s
    Y = lambda v: (P.BOARD_H - v) * s
    for layer in ("L4", "L5"):
        im = Image.new("RGB", (int(P.BOARD_W * s), int(P.BOARD_H * s)), (28, 28, 32))
        d = ImageDraw.Draw(im)
        here = [r for r in regions if r[0] == layer]
        for _, rail, pts in reversed(here):
            col = colours.setdefault(rail, palette[len(colours) % len(palette)])
            d.polygon([(X(x), Y(y)) for x, y in pts], fill=col)
        for _, rail, pts in here:
            d.line([(X(x), Y(y)) for x, y in pts + pts[:1]], fill=(15, 15, 18), width=3)
        for t in router.tracks:
            if t[0] == layer:
                d.line([(X(t[2]), Y(t[3])), (X(t[4]), Y(t[5]))], fill=(15, 15, 18), width=max(3, round(t[6] * s) + 4))
                d.line([(X(t[2]), Y(t[3])), (X(t[4]), Y(t[5]))], fill=(255, 255, 255), width=max(2, round(t[6] * s)))
        for _, rail, pts in here:
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            if not inside(pts, cx, cy):
                cx, cy = pts[0][0] + 1.5, pts[0][1] + 1.5
            d.text((X(cx) - 30, Y(cy) - 8), rail, fill=(10, 10, 12), font=font)
        for v in fan["plan"].vias:
            if v[4] in fan["power"]:
                d.ellipse([X(v[0]) - 2, Y(v[1]) - 2, X(v[0]) + 2, Y(v[1]) + 2], fill=(40, 40, 44))
        path = OUT / f"plane_{layer}.png"
        im.save(path)
        files.append(path)
    im = Image.new("RGB", (int(P.BOARD_W * s), int(P.BOARD_H * s)), (20, 20, 24))
    d = ImageDraw.Draw(im)
    tone = {"L8": (110, 170, 255), "L6": (255, 190, 90), "L3": (255, 100, 100)}
    for t in router.tracks:
        if t[0] in SIGNALS:
            d.line([(X(t[2]), Y(t[3])), (X(t[4]), Y(t[5]))], fill=tone[t[0]], width=2)
    for v in fan["plan"].vias:
        if v[4] in fan["power"]:
            d.ellipse([X(v[0]) - 1, Y(v[1]) - 1, X(v[0]) + 1, Y(v[1]) + 1], fill=(120, 120, 120))
    path = OUT / "plane_tracks.png"
    im.save(path)
    files.append(path)
    return files


def main(argv):
    cmd = argv[0] if argv else "check"
    t0 = time.perf_counter()
    regions = load_regions()
    fan = fanout.build_cached()
    t1 = time.perf_counter()
    if cmd == "ir":
        print("\n".join(ir_report(regions, fan)))
        return 0
    terms = terminals(fan)
    hit, left = reach(regions, terms)
    router, failed = route_rest(regions, fan, terms, hit, left)
    t2 = time.perf_counter()
    report(regions, fan, terms, hit, left, router, failed)
    t3 = time.perf_counter()
    print([str(p) for p in render(regions, fan, router, left)])
    import build
    (P.BRIDGE / "ape_place_power.txt").write_text(spec_text(regions, fan, router, build.PCB_PATH))
    t4 = time.perf_counter()
    print(f"seconds: fan-out {t1 - t0:.1f}, strips and tracks {t2 - t1:.1f}, report {t3 - t2:.1f}, pictures and spec {t4 - t3:.1f}")
    if cmd == "apply":
        print(P.run_place("PlacePower", timeout=1800))
        print(f"seconds in Altium: {time.perf_counter() - t4:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
