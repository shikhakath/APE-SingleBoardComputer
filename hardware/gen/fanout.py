"""Fan-outs for the placed board, computed offline and written to PCB.PcbDoc. No autorouter: everything is scripted.

Only fan-outs: a stub and a via at a pad. Nothing here joins one part to another, except that a pad may share a
same-net via already beside it, and the switch nodes, which stay on the surface between their pads.

- SiP power and GND balls: one via per ball on a checkerboard of sites (powerplanes.fanout_sip).
- SiP signal balls, outer row: a straight stub on L1 to just past the ball field.
- SiP signal balls, second row: a short jog into the gap between two outer balls, then straight out on L1.
- SiP signal balls further in: one via on a free site beside the ball, on L3 or L6 from there. A ball in the outer two
  rows that has no clear way out gets a via too. These sites are chosen together with the power and GND balls' sites,
  and stay off the channels (in_channel): vias on every 0.5 mm site are a wall, for a 0.09 mm track and for the planes.
- Caps under the SiP: a stub to a same-rail via beside them, or a new via on a free site.
- Every other SMD power and GND pad on the board: a via and a short stub (powerplanes.fanout_pads).

    python fanout.py plan       report, out/fanout_sip.png
    python fanout.py apply      writes the copper to the PcbDoc (take the Altium lock)

Frame: mm, origin at the board's lower-left corner.
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict

from PIL import Image, ImageDraw, ImageFont

import pcbsetup as S
import placement as P
import powerplanes as PP

BEYOND = 1.0            # an escape stub ends this far past the outermost ball
W_SIG = 0.09            # W_SiP
W_CAP = 0.15            # the top of W_SiP's range
CLR_SIP = 0.095         # Clr_SiP is 0.09 mm
SIGNET_MARGIN = 2.0     # earlier fan-out copper on signal nets is replaced only this close to the SiP
# The AM625 wants VDD_CORE and VDDA_CORE_USB within 1 % (datasheet 6.5 note 2). These bead inputs get no via into the core
# plane, where they would sit near the regulator: planes.py runs them to a core ball's via, on the SiP's side of the drop.
TAPS = {("FB300", "1"), ("FB301", "1")}
TAP_BALL = "L15"


def in_channel(x, y, ux, uy):
    """The via sites kept free through the SiP's signal rows, every 1.5 mm on the north, east and south sides. A track fits
    between vias 1.0 mm apart, not 0.5 mm (0.25 mm between the pads, 0.27 mm needed), and plane copper needs the same gap.
    In a row, 2 sites of 3 stay usable, which is just enough: the 2 inner rows need 4 vias per mm in 3 rows of sites."""
    i, j = round((x - ux) * 4), round((y - uy) * 4)
    if 16 <= i <= 24:
        return abs(j) <= 14 and j % 6 == 0
    return 8 <= abs(j) <= 16 and i % 6 == 0


def clear(cu, side, a, b, w, net, clr):
    """A segment clears everything of another net on this side."""
    m = w / 2 + clr + 0.3
    rect = (min(a[0], b[0]) - m, min(a[1], b[1]) - m, max(a[0], b[0]) + m, max(a[1], b[1]) + m)
    for kind, layers, onet, rc, seg, ref in cu.near(*rect):
        if onet == net or side not in layers:
            continue
        if seg:
            gap = PP.seg_seg_gap((a[0], a[1], b[0], b[1]), seg[:4]) - seg[4] / 2 - w / 2
        elif kind == "via" or ref == "U1":       # both round: a ball's land is not its bounding square
            cx, cy, r = (rc[0] + rc[2]) / 2, (rc[1] + rc[3]) / 2, (rc[2] - rc[0]) / 2
            gap = PP.seg_seg_gap((a[0], a[1], b[0], b[1]), (cx, cy, cx, cy)) - r - w / 2
        else:
            gap = PP.seg_rect_gap(a[0], a[1], b[0], b[1], rc) - w / 2
        if gap < clr:
            return False
    return True


def add_stub(plan, cu, side, a, b, w, net):
    plan.stubs.append((side, round(a[0], 3), round(a[1], 3), round(b[0], 3), round(b[1], 3), w, net))
    m = w / 2
    cu.add("stub", side, net, (min(a[0], b[0]) - m, min(a[1], b[1]) - m, max(a[0], b[0]) + m, max(a[1], b[1]) + m),
           seg=(a[0], a[1], b[0], b[1], w))


def add_via(plan, cu, x, y, net, how):
    plan.vias.append((round(x, 3), round(y, 3), PP.SIP_VIA[0], PP.SIP_VIA[1], net, how))
    plan.by_net[net].append((x, y, PP.SIP_VIA[1]))
    r = PP.SIP_VIA[1] / 2
    cu.add("via", "TB", net, (x - r, y - r, x + r, y + r))


def site_ok(cu, plan_sites, x, y, net, clr=CLR_SIP):
    """A SiP via here clears other nets' copper on both sides, and other vias."""
    if (round(x, 3), round(y, 3)) in plan_sites:
        return False
    r = PP.SIP_VIA[1] / 2
    for side in "TB":
        if not clear(cu, side, (x, y), (x, y), PP.SIP_VIA[1], net, clr):
            return False
    for kind, layers, onet, rc, seg, ref in cu.near(x - 0.6, y - 0.6, x + 0.6, y + 0.6):
        if kind == "via" and math.hypot((rc[0] + rc[2]) / 2 - x, (rc[1] + rc[3]) / 2 - y) < 0.34:
            return False
    return True


def destination_of(net, parts, nets, place):
    """Middle of the net's other pads."""
    px, py = [], []
    for nd in nets.get(net, []):
        r, n = nd.split(".", 1)
        if r == "U1" or r not in parts or r not in place:
            continue
        q = next((c for c in parts[r].pads if c[4] == n), None)
        if q:
            a = P.xform(q[0], q[1], *place[r])
            px.append(a[0])
            py.append(a[1])
    if not px:
        return place["U1"][0], place["U1"][1]
    return sum(px) / len(px), sum(py) / len(py)


def inner_signal_balls(parts, place, power):
    """Signal balls that are not in the outer two rows, and every SiP ball's position."""
    u1 = place["U1"]
    balls = {}
    for q in parts["U1"].pads:
        x, y = P.xform(q[0], q[1], *u1)
        balls[q[4]] = (round(x, 3), round(y, 3), q[2])
    xs = sorted({b[0] for b in balls.values()})
    ys = sorted({b[1] for b in balls.values()})
    inner = {}
    for b, (x, y, net) in balls.items():
        if not net or net == "GND" or net in power:
            continue
        d = {"W": xs.index(x), "E": len(xs) - 1 - xs.index(x), "S": ys.index(y), "N": len(ys) - 1 - ys.index(y)}
        if min(d.values()) >= 2:
            inner[b] = min(d, key=d.get)
    return balls, inner


def site_choices(parts, nets, place, cu, power):
    """Each ball's usable sites, best first, while only the pads are down: signals towards their own edge of the package,
    power and GND on the even sites. A second-row ball needs no via, but it does need one of the two gaps it can leave by on
    L1, and a via in that gap would close it, so the gaps go into the same matching."""
    balls, inner = inner_signal_balls(parts, place, power)
    xs = sorted({b[0] for b in balls.values()})
    ys = sorted({b[1] for b in balls.values()})
    second = {}
    for b, (x, y, net) in balls.items():
        if not net or net == "GND" or net in power or b in inner:
            continue
        d = {"W": xs.index(x), "E": len(xs) - 1 - xs.index(x), "S": ys.index(y), "N": len(ys) - 1 - ys.index(y)}
        if min(d.values()) == 1:
            sides = [k for k, v in d.items() if v == 1]
            dx, dy = destination_of(net, parts, nets, place)
            unit = {"W": (-1, 0), "E": (1, 0), "S": (0, -1), "N": (0, 1)}
            side = max(sides, key=lambda k: unit[k][0] * (dx - x) + unit[k][1] * (dy - y))
            sx, sy = unit[side]
            first = 1 if ((dy - y) if sx else (dx - x)) >= 0 else -1
            if sx:
                second[b] = [(round(x + sx * 0.25, 3), round(y + o * 0.25, 3)) for o in (first, -first)]
            else:
                second[b] = [(round(x + o * 0.25, 3), round(y + sy * 0.25, 3)) for o in (first, -first)]
    ux, uy = place["U1"][:2]
    step = {"W": (-1, 0), "E": (1, 0), "S": (0, -1), "N": (0, 1)}
    x0, x1 = min(b[0] for b in balls.values()), max(b[0] for b in balls.values())
    y0, y1 = min(b[1] for b in balls.values()), max(b[1] for b in balls.values())
    usable = {}
    for b, (x, y, net) in balls.items():
        if b not in inner and net != "GND" and net not in power:
            continue
        opts = []
        for a in (-0.25, 0.25):
            for c in (-0.25, 0.25):
                sx, sy = round(x + a, 3), round(y + c, 3)
                if b in inner:
                    key = -(a * step[inner[b]][0] + c * step[inner[b]][1])
                else:
                    # a site outside the ball field blocks the outer balls' stubs on both sides of it
                    ring = not (x0 < sx < x1 and y0 < sy < y1)
                    even = (round(sx / 0.5) + round(sy / 0.5)) % 2 == 0
                    key = (ring, not even, abs(sx - ux) + abs(sy - uy))
                opts.append((key, sx, sy))
        usable[b] = [(o[1], o[2]) for o in sorted(opts) if site_ok(cu, set(), o[1], o[2], net)]
    usable.update(second)
    return usable, set(inner), set(second)


def pad_copper(pads):
    cu = PP.Copper()
    for p in pads:
        layers = "TB" if p.tht else p.side
        cu.add("hole" if p.tht else "pad", layers, p.net, (p.x - p.hw, p.y - p.hh, p.x + p.hw, p.y + p.hh), ref=p.ref)
    return cu


def sip_balls_without_site(parts, nets, place):
    """For blocks.py: with these parts on the back, does every SiP ball that needs a via still get one?"""
    classes = S.net_classes(PP._nets())
    power = set(classes["PWR"]) | set(classes["PWR_HI"])
    cu = pad_copper(PP.load_pads(parts, place))
    usable, inner, second = site_choices(parts, nets, place, cu, power)
    ux, uy = place["U1"][:2]
    sip = PP.fanout_sip(parts, place, PP.Plan(), cu, power, usable, inner | second,
                        lambda x, y: in_channel(x, y, ux, uy), exempt=second)
    return [b for b in sip["no_site"] if b not in second]


def sip_signals(parts, nets, place, plan, cu, power, reserved=None, gaps_chosen=None):
    """Escape stubs and dog-bone vias for every connected signal ball. reserved: {ball: site} already chosen. gaps_chosen:
    {ball: the site in the gap it leaves by}."""
    reserved = reserved or {}
    gaps_chosen = gaps_chosen or {}
    u1 = place["U1"]
    balls = {}
    for q in parts["U1"].pads:
        x, y = P.xform(q[0], q[1], *u1)
        balls[q[4]] = (round(x, 3), round(y, 3), q[2])
    xs = sorted({b[0] for b in balls.values()})
    ys = sorted({b[1] for b in balls.values()})
    nx, ny = len(xs), len(ys)
    sites_taken = {(v[0], v[1]) for v in plan.vias}
    step = {"W": (-1, 0), "E": (1, 0), "S": (0, -1), "N": (0, 1)}
    edge = {"W": xs[0] - BEYOND, "E": xs[-1] + BEYOND, "S": ys[0] - BEYOND, "N": ys[-1] + BEYOND}

    def destination(net, name):
        return destination_of(net, parts, nets, place)

    def side_of(b):
        x, y, net = balls[b]
        ix, iy = xs.index(x), ys.index(y)
        d = {"W": ix, "E": nx - 1 - ix, "S": iy, "N": ny - 1 - iy}
        m = min(d.values())
        cands = [k for k, v in d.items() if v == m]
        if len(cands) > 1:
            dx, dy = destination(net, b)
            dx, dy = dx - x, dy - y
            cands.sort(key=lambda k: -(step[k][0] * dx + step[k][1] * dy))
        return m, cands[0]

    signals = sorted((b for b, v in balls.items() if v[2] and v[2] != "GND" and v[2] not in power), key=P._natural)
    rows = defaultdict(list)
    for b in signals:
        rows[side_of(b)[0]].append(b)
    need_via = []
    stats = Counter()
    # ---- vias whose sites are already chosen go down first: the stubs below have to clear them
    for b, s in sorted(reserved.items()):
        x, y, net = balls[b]
        add_via(plan, cu, s[0], s[1], net, "sip signal")
        add_stub(plan, cu, "T", (x, y), s, W_SIG, net)
        sites_taken.add(s)
        stats["signal via"] += 1
    # ---- outer row: straight out
    for b in rows.get(0, []):
        x, y, net = balls[b]
        _, s = side_of(b)
        end = (edge[s], y) if step[s][0] else (x, edge[s])
        if clear(cu, "T", (x, y), end, W_SIG, net, CLR_SIP):
            add_stub(plan, cu, "T", (x, y), end, W_SIG, net)
            stats["outer row escape"] += 1
        else:
            need_via.append(b)
    # ---- second row: through a gap between two outer balls
    escaped = set()

    def side_candidates(b, k):
        x, y, net = balls[b]
        ix, iy = xs.index(x), ys.index(y)
        return {"W": ix, "E": nx - 1 - ix, "S": iy, "N": ny - 1 - iy}[k] == 1

    gaps = set()
    second_row = list(rows.get(1, []))
    # the balls with a chosen gap go first, in it, so that a ball that has to use its other gap can't take a neighbour's
    for b, only_chosen in [(b, True) for b in second_row if b in gaps_chosen] + [(b, False) for b in second_row]:
        if b in escaped:
            continue
        x, y, net = balls[b]
        _, s = side_of(b)
        sx, sy = step[s]
        dx, dy = destination(net, b)
        order = (1, -1) if ((dy - y) if sx else (dx - x)) >= 0 else (-1, 1)
        if only_chosen:
            g = gaps_chosen[b]
            # the gap may be on another side of a corner ball
            s = next(k for k in step if step[k][0] * (g[0] - x) + step[k][1] * (g[1] - y) > 0 and
                     abs(step[k][0]) * abs(g[0] - x) + abs(step[k][1]) * abs(g[1] - y) > 0 and
                     ((x, y) and side_candidates(b, k)))
            sx, sy = step[s]
            o = 1 if ((g[1] - y) if sx else (g[0] - x)) > 0 else -1
            order = (o,)
        done = False
        for o in order:
            if sx:
                mid = (x + sx * 0.25, y + o * 0.25)
                end = (edge[s], y + o * 0.25)
                key = (s, round(y + o * 0.25, 3))
            else:
                mid = (x + o * 0.25, y + sy * 0.25)
                end = (x + o * 0.25, edge[s])
                key = (s, round(x + o * 0.25, 3))
            if key in gaps:
                continue
            if clear(cu, "T", (x, y), mid, W_SIG, net, CLR_SIP) and clear(cu, "T", mid, end, W_SIG, net, CLR_SIP):
                add_stub(plan, cu, "T", (x, y), mid, W_SIG, net)
                add_stub(plan, cu, "T", mid, end, W_SIG, net)
                gaps.add(key)
                stats["second row escape"] += 1
                escaped.add(b)
                done = True
                break
        if not done and not only_chosen:
            need_via.append(b)
    # ---- everything else: a via on a free site, matched so that every ball gets one
    for m, bs in sorted(rows.items()):
        if m >= 2:
            need_via += [b for b in bs if b not in reserved]
    def sites(b):
        x, y, net = balls[b]
        _, s = side_of(b)
        sx, sy = step[s]
        opts = []
        for a in (-0.25, 0.25):
            for c in (-0.25, 0.25):
                # towards its edge of the package first
                sa, sb = round(x + a, 3), round(y + c, 3)
                opts.append((in_channel(sa, sb, u1[0], u1[1]), -(a * sx + c * sy), sa, sb))
        return [(o[2], o[3]) for o in sorted(opts)]

    usable = {}
    for b in need_via:
        x, y, net = balls[b]
        usable[b] = [s for s in sites(b) if site_ok(cu, sites_taken, s[0], s[1], net)
                     and clear(cu, "T", (x, y), s, W_SIG, net, CLR_SIP)]
    holder = {}

    def assign(b, seen):
        for s in usable[b]:
            if s in seen:
                continue
            seen.add(s)
            if s not in holder or assign(holder[s], seen):
                holder[s] = b
                return True
        return False

    stuck = [b for b in need_via if not assign(b, set())]
    for s, b in sorted(holder.items()):
        x, y, net = balls[b]
        add_via(plan, cu, s[0], s[1], net, "sip signal")
        add_stub(plan, cu, "T", (x, y), s, W_SIG, net)
        stats["signal via"] += 1
    stats["no fan-out"] = len(stuck)
    return dict(stats), stuck


def under_body_caps(parts, place, pads, plan, cu, power):
    """Caps on the back under the SiP. Their pads reach a same-net via beside them, or get a new one on a free site."""
    body = P.crt_rect(parts["U1"], *place["U1"])
    todo = [p for p in pads if p.ref != "U1" and p.side == "B" and not p.tht and (p.net == "GND" or p.net in power)
            and body[0] < p.x < body[2] and body[1] < p.y < body[3]]
    sites_taken = {(v[0], v[1]) for v in plan.vias}
    xs = sorted({round(P.xform(q[0], q[1], *place["U1"])[0], 3) for q in parts["U1"].pads})
    ys = sorted({round(P.xform(q[0], q[1], *place["U1"])[1], 3) for q in parts["U1"].pads})
    lattice = [(round(x + a, 3), round(y + b, 3)) for x in xs for y in ys for a in (-0.25, 0.25) for b in (-0.25, 0.25)]
    lattice = sorted(s for s in set(lattice) if not in_channel(s[0], s[1], *place["U1"][:2]))
    handled, failed = [], []
    stats = Counter()
    for p in todo:
        a = (p.x, p.y)
        done = False
        for w in (W_CAP, W_SIG):
            near = sorted((math.hypot(v[0] - p.x, v[1] - p.y), v[0], v[1]) for v in plan.by_net[p.net])
            for dist, vx, vy in near[:8]:
                if dist <= 1.3 and clear(cu, "B", a, (vx, vy), w, p.net, CLR_SIP):
                    add_stub(plan, cu, "B", a, (vx, vy), w, p.net)
                    stats["cap to ball via"] += 1
                    done = True
                    break
            if done:
                break
            for dist, x, y in sorted((math.hypot(s[0] - p.x, s[1] - p.y), s[0], s[1]) for s in lattice)[:40]:
                if dist <= 1.6 and site_ok(cu, sites_taken, x, y, p.net, 0.10) and clear(cu, "B", a, (x, y), w, p.net, CLR_SIP):
                    add_via(plan, cu, x, y, p.net, "sip cap")
                    sites_taken.add((x, y))
                    add_stub(plan, cu, "B", a, (x, y), w, p.net)
                    stats["cap own via"] += 1
                    done = True
                    break
            if done:
                break
        if not done and site_ok(cu, sites_taken, p.x, p.y, p.net, 0.10):
            # a filled via in the pad: JLC caps it for free
            add_via(plan, cu, p.x, p.y, p.net, "sip cap in pad")
            sites_taken.add((round(p.x, 3), round(p.y, 3)))
            stats["cap via in pad"] += 1
            done = True
        if not done:
            # anywhere near the pad, off the lattice: mostly at the edge of the ball field
            spots = []
            for i in range(-32, 33):
                for j in range(-32, 33):
                    dist = math.hypot(i * 0.05, j * 0.05)
                    if dist <= 1.6:
                        spots.append((dist, round(p.x + i * 0.05, 3), round(p.y + j * 0.05, 3)))
            spots.sort()
            for dist, x, y in spots:
                if site_ok(cu, sites_taken, x, y, p.net, 0.10) and clear(cu, "B", a, (x, y), W_SIG, p.net, CLR_SIP):
                    add_via(plan, cu, x, y, p.net, "sip cap")
                    sites_taken.add((x, y))
                    add_stub(plan, cu, "B", a, (x, y), W_SIG, p.net)
                    stats["cap own via, off the lattice"] += 1
                    done = True
                    break
        if done:
            handled.append(p)
        else:
            failed.append(p)
    return handled, failed, dict(stats)


def join_failed(pads, plan, cu):
    """A pad with no room for a via joins a same-net pad beside it on the surface, as a pin under its own decoupling cap."""
    left = []
    for p in plan.failed:
        same = sorted((math.hypot(q.x - p.x, q.y - p.y), id(q), q) for q in pads
                      if q is not p and q.net == p.net and q.side == p.side and not q.tht and q.ref != p.ref)
        joined = False
        for dist, _, q in same[:4]:
            if dist > 6.0:
                break
            path = PP.surface_path(cu, p.side, p.net, (p.x, p.y), (q.x, q.y), 0.15)
            if path:
                for a, b in zip(path, path[1:]):
                    add_stub(plan, cu, p.side, a, b, 0.15, p.net)
                joined = True
                break
        if not joined:
            left.append(p)
    plan.failed[:] = left


def tidy_widths(plan, cu, place, classes):
    """Width rules, once all the copper is known. In the SiP's room W_SiP allows 0.15 mm at most. PWR_HI wants 0.20 mm at
    least where it fits. A wide switch-node track narrows where it would pass too close to another net's pad."""
    ux, uy = place["U1"][:2]
    in_room = lambda x, y: abs(x - ux) <= S.ROOM_W_MM / 2 + 0.2 and abs(y - uy) <= S.ROOM_H_MM / 2 + 0.2
    hi = set(classes["PWR_HI"])
    power = set(classes["PWR"]) | hi
    stats = Counter()
    for i, t in enumerate(plan.stubs):
        side, x1, y1, x2, y2, w, net = t
        a, b = (x1, y1), (x2, y2)
        new = w
        if in_room(x1, y1) or in_room(x2, y2) or in_room((x1 + x2) / 2, (y1 + y2) / 2):
            if new > W_CAP:
                new = W_CAP
                stats["narrowed in the room"] += 1
            elif new < W_CAP and (net in power or net == "GND") and clear(cu, side, a, b, W_CAP, net, CLR_SIP):
                # the Octavo layout guide escapes power balls at 6 mil
                new = W_CAP
                stats["power escape at 6 mil"] += 1
        else:
            if net in hi and new < 0.20:
                if clear(cu, side, a, b, 0.20, net, 0.10):
                    new = 0.20
                    stats["widened to 0.20"] += 1
                else:
                    stats["PWR_HI under 0.20, no room"] += 1
            if not clear(cu, side, a, b, new, net, 0.102):
                for w2 in (0.8, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15):
                    if w2 < new and clear(cu, side, a, b, w2, net, 0.102):
                        new = w2
                        stats["narrowed near a pad"] += 1
                        break
        if new != w:
            plan.stubs[i] = (side, x1, y1, x2, y2, new, net)
    return dict(stats)


def build():
    parts, nets = P.load_parts()
    place = P.read_csv()
    classes = S.net_classes(PP._nets())
    power = set(classes["PWR"]) | set(classes["PWR_HI"])
    pads = PP.load_pads(parts, place)
    cu = pad_copper(pads)
    plan = PP.Plan()
    usable, inner, second = site_choices(parts, nets, place, cu, power)
    ux, uy = place["U1"][:2]
    sip = PP.fanout_sip(parts, place, plan, cu, power, usable, inner | second,
                        lambda x, y: in_channel(x, y, ux, uy), exempt=second)
    chosen = sip.pop("signal_sites")
    reserved = {b: s for b, s in chosen.items() if b in inner}
    gaps_chosen = {b: s for b, s in chosen.items() if b in second}
    sip["no_site"] = [b for b in sip["no_site"] if b not in second]
    signals, stuck = sip_signals(parts, nets, place, plan, cu, power, reserved, gaps_chosen)
    stuck = stuck + sip["no_site"]
    handled, cap_fail, caps = under_body_caps(parts, place, pads, plan, cu, power)
    link_fail = PP.surface_links(pads, plan, cu)
    done_ids = {id(p) for p in handled}
    rest = [p for p in pads if id(p) not in done_ids and not (p in cap_fail) and (p.ref, p.name) not in TAPS]
    done = PP.fanout_pads(rest, parts, place, plan, cu, power)
    join_failed(pads, plan, cu)
    widths = tidy_widths(plan, cu, place, classes)
    return dict(widths=widths, parts=parts, nets=nets, place=place, power=power, pads=pads, plan=plan, sip=sip, signals=signals, stuck=stuck,
                caps=caps, cap_fail=cap_fail, link_fail=link_fail, done=done)


def build_cached():
    """build(), kept in out/ until an input changes: it takes 30 s or more, and most runs change nothing it depends on."""
    import hashlib
    import pickle
    h = hashlib.sha256()
    here = P.GEN
    for f in (here / "placement.csv", P.OUT / "netlist.csv", P.OUT / "footprint_usage.csv", here / "fanout.py",
              here / "powerplanes.py", here / "placement.py", here / "footprints.py"):
        h.update(f.read_bytes())
    key = h.hexdigest()
    cache = P.OUT / "fanout_cache.pkl"
    if cache.exists():
        try:
            with open(cache, "rb") as f:
                stored = pickle.load(f)
            if stored[0] == key:
                return stored[1]
        except Exception:
            pass
    res = build()
    with open(cache, "wb") as f:
        pickle.dump((key, res), f)
    return res


def escape_check(res, pitch=0.05, width=W_SIG, clr=0.09, thin=()):
    """Can every SiP signal via still get out of the ball field on L3 or L6? A check, not routing: nothing here goes on the
    board. One 0.09 mm track at a time, 0.09 mm from everything, each blocking the ones after it, nearest the edge first.
    thin: power links already on L3 and L6, as (layer, x1, y1, x2, y2, width).
    Returns {"L3": n, "L6": n, "stuck": [nets]}: tracks found this way exist, a stuck net may still have a way."""
    plan, place, parts = res["plan"], res["place"], res["parts"]
    u1 = place["U1"]
    pts = [P.xform(q[0], q[1], *u1) for q in parts["U1"].pads]
    x0, x1 = min(a[0] for a in pts) - 0.75, max(a[0] for a in pts) + 0.75
    y0, y1 = min(a[1] for a in pts) - 0.75, max(a[1] for a in pts) + 0.75
    nx, ny = int((x1 - x0) / pitch) + 1, int((y1 - y0) / pitch) + 1
    hits = [0] * (nx * ny)

    def disc(x, y, r):
        ci, cj = round((x - x0) / pitch), round((y - y0) / pitch)
        n = int(r / pitch) + 1
        for j in range(max(0, cj - n), min(ny, cj + n + 1)):
            for i in range(max(0, ci - n), min(nx, ci + n + 1)):
                if math.hypot(x0 + i * pitch - x, y0 + j * pitch - y) < r:
                    yield j * nx + i

    vias = [v for v in plan.vias if x0 <= v[0] <= x1 and y0 <= v[1] <= y1]
    for v in vias:
        for c in disc(v[0], v[1], v[3] / 2 + clr + width / 2):
            hits[c] += 1
    todo = [v for v in vias if v[5] == "sip signal"]
    todo.sort(key=lambda v: min(v[0] - x0, x1 - v[0], v[1] - y0, y1 - v[1]))
    taken = {"L3": [], "L6": []}
    for layer, ax, ay, bx, by, w in thin:
        steps = max(1, int(math.hypot(bx - ax, by - ay) / pitch))
        for k in range(steps + 1):
            px, py = ax + (bx - ax) * k / steps, ay + (by - ay) * k / steps
            if x0 <= px <= x1 and y0 <= py <= y1:
                taken[f"L{layer}"] += list(disc(px, py, w / 2 + clr + width / 2))
    # a track down the middle of a channel wastes it: anything left out goes first on the next try
    for attempt in range(4):
        out = attempt_escape(todo, hits, disc, nx, ny, x0, y0, pitch, width, clr, taken)
        if not out["stuck"]:
            break
        names = set(out["stuck"])
        todo = [v for v in todo if v[4] in names] + [v for v in todo if v[4] not in names]
    return out


def attempt_escape(todo, hits, disc, nx, ny, x0, y0, pitch, width, clr, taken):
    layers = {"L3": [0] * (nx * ny), "L6": [0] * (nx * ny)}
    for name, cells in taken.items():
        for c in cells:
            layers[name][c] = 1
    out = {"L3": 0, "L6": 0, "stuck": []}
    for v in todo:
        own = set(disc(v[0], v[1], v[3] / 2 + clr + width / 2))
        start = round((v[1] - y0) / pitch) * nx + round((v[0] - x0) / pitch)
        found = None
        for name, used in layers.items():
            prev = {start: -1}
            q = [start]
            for c in q:
                i, j = c % nx, c // nx
                if i in (0, nx - 1) or j in (0, ny - 1):
                    found = (name, c, prev)
                    break
                for dx, dy in PP.NB8:
                    n = c + dx + dy * nx
                    if n in prev or used[n]:
                        continue
                    if hits[n] - (1 if n in own else 0) > 0:
                        continue
                    prev[n] = c
                    q.append(n)
            if found:
                break
        if not found:
            out["stuck"].append(v[4])
            continue
        name, c, prev = found
        out[name] += 1
        while c != -1:
            for m in disc(x0 + (c % nx) * pitch, y0 + (c // nx) * pitch, clr + width):
                layers[name][m] = 1
            c = prev[c]
    return out


def report(res):
    plan = res["plan"]
    print("SiP power and GND:", {k: v for k, v in res["sip"].items() if k not in ("no_site", "signal_balls_no_site")},
          "balls with no site:", res["sip"]["no_site"])
    print("SiP signals:", res["signals"], "no fan-out:", res["stuck"])
    print("caps under the SiP:", res["caps"], "failed:", [str(p) for p in res["cap_fail"]])
    print("switch-node links that failed:", res["link_fail"])
    print("width changes:", res["widths"])
    print("other power and GND pads done:", res["done"], "failed:", [f"{p} {p.net}" for p in plan.failed])
    kinds = Counter(v[5] for v in plan.vias)
    length = sum(math.hypot(t[3] - t[1], t[4] - t[2]) for t in plan.stubs)
    print(f"{len(plan.vias)} vias {dict(kinds)}, {len(plan.stubs)} stubs, {length:.0f} mm of stub")
    longest = sorted(((round(math.hypot(t[3] - t[1], t[4] - t[2]), 1), t[6]) for t in plan.stubs), reverse=True)[:12]
    print("longest stubs:", longest)
    signal_nets = {t[6] for t in plan.stubs if t[6] != "GND" and t[6] not in res["power"]}
    print("signal nets with fan-out copper:", len(signal_nets))
    print("SiP signal vias that can get out:", escape_check(res))
    ux, uy = res["place"]["U1"][:2]
    in_ch = [v for v in plan.vias if abs(v[0] - ux) < 7 and abs(v[1] - uy) < 4.5 and in_channel(v[0], v[1], ux, uy)]
    print("vias left in a channel:", len(in_ch), [(v[4], round(v[0] - ux, 2), round(v[1] - uy, 2)) for v in in_ch])


def render(res, path=None):
    """The SiP's fan-out, top and back side by side."""
    place, parts, plan = res["place"], res["parts"], res["plan"]
    x0, y0 = place["U1"][:2]
    W, H = 19.0, 13.0
    s = 44
    im = Image.new("RGB", (int(2 * W * s) + 30, int(H * s) + 40), (20, 20, 24))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    for panel, side, ox in ((0, "T", 10), (1, "B", int(W * s) + 20)):
        X = lambda v: ox + (v - x0 + W / 2) * s
        Y = lambda v: 30 + (y0 + H / 2 - v) * s
        d.text((ox, 6), "Top: balls, L1 stubs, vias" if side == "T" else "Back, seen from the top: caps, stubs, vias", font=f, fill=(230, 230, 230))
        for p in res["pads"]:
            if p.side != side or abs(p.x - x0) > W / 2 or abs(p.y - y0) > H / 2:
                continue
            col = (70, 70, 80) if not p.net else ((90, 90, 90) if p.net == "GND" else ((215, 70, 70) if p.net in res["power"] else (70, 130, 220)))
            d.rectangle([X(p.x - p.hw), Y(p.y + p.hh), X(p.x + p.hw), Y(p.y - p.hh)], fill=col)
        for t in plan.stubs:
            if t[0] != side or abs(t[1] - x0) > W / 2 or abs(t[2] - y0) > H / 2:
                continue
            col = (150, 150, 150) if t[6] == "GND" else ((255, 120, 120) if t[6] in res["power"] else (120, 190, 255))
            d.line([(X(t[1]), Y(t[2])), (X(t[3]), Y(t[4]))], fill=col, width=max(1, int(t[5] * s)))
        for v in plan.vias:
            if abs(v[0] - x0) > W / 2 or abs(v[1] - y0) > H / 2:
                continue
            r = v[3] / 2 * s
            col = (200, 200, 200) if v[4] == "GND" else ((255, 150, 60) if v[4] in res["power"] else (90, 220, 255))
            d.ellipse([X(v[0]) - r, Y(v[1]) - r, X(v[0]) + r, Y(v[1]) + r], fill=col)
    path = path or (P.OUT / "fanout_sip.png")
    im.save(path)
    return path


def spec_text(res, pcb):
    """ape_place_power.txt for ApePlace>PlacePower. Lengths in Altium coords relative to the board origin. Power and GND
    nets are owned whole. A signal net's earlier fan-out is replaced only near the SiP, so copper elsewhere stays."""
    def co(v):
        return int(round(v / 0.0254 * 10000))

    plan = res["plan"]
    lines = [str(pcb)]
    lines += [f"NET|{n}" for n in sorted(set(res["power"]) | {"GND"})]
    signal_nets = sorted({t[6] for t in plan.stubs} - set(res["power"]) - {"GND"})
    signal_nets += sorted({v[4] for v in plan.vias} - set(res["power"]) - {"GND"} - set(signal_nets))
    lines += [f"SIGNET|{n}" for n in sorted(set(signal_nets))]
    b = P.crt_rect(res["parts"]["U1"], *res["place"]["U1"])
    m = SIGNET_MARGIN
    lines.append(f"AREA|{co(b[0] - m)}|{co(b[1] - m)}|{co(b[2] + m)}|{co(b[3] + m)}")
    rows = []
    for v in plan.vias:
        rows.append((v[4], 0, f"VIA|{co(v[0])}|{co(v[1])}|{co(v[2])}|{co(v[3])}|{v[4]}"))
    for t in plan.stubs:
        layer = 1 if t[0] == "T" else 32
        rows.append((t[6], 1, f"TRK|{layer}|{co(t[1])}|{co(t[2])}|{co(t[3])}|{co(t[4])}|{co(t[5])}|{t[6]}"))
    rows.sort(key=lambda r: (r[0], r[1]))
    lines += [r[2] for r in rows]
    return "\n".join(lines) + "\n"


def main(argv):
    cmd = argv[0] if argv else "plan"
    res = build()
    report(res)
    print(render(res))
    if cmd == "apply":
        import build as B
        (P.BRIDGE / "ape_place_power.txt").write_text(spec_text(res, B.PCB_PATH))
        print(P.run_place("PlacePower", timeout=590))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
