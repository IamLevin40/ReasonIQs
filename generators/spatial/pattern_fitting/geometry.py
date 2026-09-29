"""Vector primitives and rectangular clipping in a 300×300 world canvas."""

from __future__ import annotations

import math

SIZE = 300
CELL = 100
EPS = 1e-7


def primitive(layer, points, *, kind="stroke", width=2.5, fill="none", stroke="#253746",
              role="motif", phase=0):
    return {"layer_id": layer, "kind": kind, "points": [[float(x), float(y)] for x, y in points],
            "stroke_width": width, "stroke": stroke, "fill": fill, "role": role, "phase": phase}


def regular(cx, cy, rx, ry, count, angle=0):
    return [(cx + rx*math.cos(angle + 2*math.pi*i/count),
             cy + ry*math.sin(angle + 2*math.pi*i/count)) for i in range(count)]


def circle(cx, cy, rx, ry=None, start=0, sweep=2*math.pi, steps=72):
    ry = rx if ry is None else ry
    return [(cx + rx*math.cos(start+sweep*i/steps),
             cy + ry*math.sin(start+sweep*i/steps)) for i in range(steps+1)]


def polygon(layer, points, *, fill="none", width=2.5, stroke="#253746", role="motif"):
    result = []
    if fill != "none":
        result.append(primitive(layer, points, kind="fill", fill=fill, width=0, role=role))
    result.append(primitive(layer, list(points)+[points[0]], width=width, stroke=stroke, role=role))
    return result


def _segment(a, b, box):
    """Liang–Barsky clipping; returns endpoints in the original direction."""
    x0, y0, x1, y1 = box
    dx, dy = b[0]-a[0], b[1]-a[1]
    p, q = (-dx, dx, -dy, dy), (a[0]-x0, x1-a[0], a[1]-y0, y1-a[1])
    lo, hi = 0.0, 1.0
    for pi, qi in zip(p, q):
        if abs(pi) < EPS:
            if qi < -EPS:
                return None
        else:
            t = qi/pi
            if pi < 0:
                lo = max(lo, t)
            else:
                hi = min(hi, t)
            if lo > hi + EPS:
                return None
    if hi-lo < EPS:
        return None
    return ([a[0]+lo*dx, a[1]+lo*dy], [a[0]+hi*dx, a[1]+hi*dy])


def _polygon_clip(points, box):
    x0, y0, x1, y1 = box
    result = [list(p) for p in points]
    boundaries = ((0, x0, 1), (0, x1, -1), (1, y0, 1), (1, y1, -1))
    for axis, value, sign in boundaries:
        previous = result
        result = []
        if not previous:
            break
        for a, b in zip(previous[-1:]+previous[:-1], previous):
            ai = sign*(a[axis]-value) >= -EPS
            bi = sign*(b[axis]-value) >= -EPS
            if ai != bi:
                t = (value-a[axis])/(b[axis]-a[axis])
                result.append([a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])])
            if bi:
                result.append(b)
    return result if len(result) >= 3 else []


def clip_primitive(item, box):
    if item["kind"] == "fill":
        points = _polygon_clip(item["points"], box)
        return [{**item, "points": points}] if points else []
    fragments = []
    current = []
    for a, b in zip(item["points"], item["points"][1:]):
        clipped = _segment(a, b, box)
        if clipped:
            if current and math.dist(current[-1], clipped[0]) < EPS:
                current.append(clipped[1])
            else:
                if len(current) >= 2:
                    fragments.append({**item, "points": current})
                current = [clipped[0], clipped[1]]
        elif current:
            fragments.append({**item, "points": current})
            current = []
    if len(current) >= 2:
        fragments.append({**item, "points": current})
    return fragments


def clip_pattern(master, box):
    return [part for item in master for part in clip_primitive(item, box)]


def missing_bounds(mode, index):
    if mode == "Cell Missing":
        return [100*(index % 3), 100*(index // 3),
                100*(index % 3+1), 100*(index // 3+1)]
    x, y = ((100, 100), (200, 100), (100, 200), (200, 200))[index]
    return [x-50, y-50, x+50, y+50]


def _canonical_points(item):
    pts = [tuple(round(v, 3) for v in p) for p in item["points"]]
    if item["kind"] == "fill":
        # A polygon's starting vertex and winding do not change its geometry.
        variants = [tuple(pts[i:]+pts[:i]) for i in range(len(pts))]
        backward = list(reversed(pts))
        variants += [tuple(backward[i:]+backward[:i]) for i in range(len(pts))]
        return min(variants)
    segments = [tuple(sorted((a, b))) for a, b in zip(pts, pts[1:]) if a != b]
    return tuple(sorted(segments))


def signature(piece):
    elements = []
    for item in piece:
        # Layer IDs describe the rule, but identical visible strokes on two
        # layers must still count as visually equivalent.
        style = (item["kind"], item["fill"], item["stroke_width"], item.get("stroke", "#253746"))
        if item["kind"] == "stroke":
            elements.extend((style, segment) for segment in _canonical_points(item))
        else:
            elements.append((style, _canonical_points(item)))
    return tuple(sorted(elements))


def _inside(point, polygon):
    """Point-in-polygon on the vector fill, with its edge counted as covered."""
    x,y=point
    inside=False
    points=polygon["points"]
    for a,b in zip(points,points[1:]+points[:1]):
        cross=(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0])
        if abs(cross)<EPS and min(a[0],b[0])-EPS <= x <= max(a[0],b[0])+EPS and \
                min(a[1],b[1])-EPS <= y <= max(a[1],b[1])+EPS:
            return True
        if (a[1]>y) != (b[1]>y):
            hit=a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if x<hit:
                inside=not inside
    return inside


def _crossing_parameter(a,b,c,d):
    ux,uy=b[0]-a[0],b[1]-a[1]
    vx,vy=d[0]-c[0],d[1]-c[1]
    determinant=ux*vy-uy*vx
    if abs(determinant)<EPS:
        return None
    wx,wy=c[0]-a[0],c[1]-a[1]
    t=(wx*vy-wy*vx)/determinant
    u=(wx*uy-wy*ux)/determinant
    return t if EPS<t<1-EPS and -EPS<=u<=1+EPS else None


def _visible_parts(a,b,later_fills):
    cuts=[0.0,1.0]
    for fill in later_fills:
        points=fill["points"]
        for c,d in zip(points,points[1:]+points[:1]):
            t=_crossing_parameter(a,b,c,d)
            if t is not None:
                cuts.append(t)
    cuts=sorted(set(round(t,9) for t in cuts))
    pieces=[]
    for lo,hi in zip(cuts,cuts[1:]):
        if hi-lo<EPS:
            continue
        midpoint=[a[j]+(lo+hi)/2*(b[j]-a[j]) for j in (0,1)]
        if any(_inside(midpoint,fill) for fill in later_fills):
            continue
        p=tuple(round(a[j]+lo*(b[j]-a[j]),3) for j in (0,1))
        q=tuple(round(a[j]+hi*(b[j]-a[j]),3) for j in (0,1))
        if p!=q:
            pieces.append(tuple(sorted((p,q))))
    return pieces


def visible_signature(piece, grayscale=False):
    """Canonical exposed vector edges after opaque later fills cover earlier art.

    This uses polygon intersections and containment, not rendered pixels.
    """
    elements=[]
    for index,item in enumerate(piece):
        later_fills=[other for other in piece[index+1:] if other["kind"] == "fill"]
        if item["kind"] == "fill":
            shade=("dark" if item["fill"].lower() != "#ffffff" else "light") if grayscale else item["fill"]
            style=("fill",shade)
            points=item["points"]
            segments=zip(points,points[1:]+points[:1])
        else:
            style=("stroke",item["stroke_width"],"ink" if grayscale else item.get("stroke","#253746"))
            segments=zip(item["points"],item["points"][1:])
        for a,b in segments:
            elements.extend((style,segment) for segment in _visible_parts(a,b,later_fills))
    return tuple(sorted(elements))


def boundary_connections(piece, box):
    """Record contour junctions and filled intervals on each edge of the cut."""
    x0, y0, x1, y1 = box
    entries = []
    for index,item in enumerate(piece):
        later_fills=[other for other in piece[index+1:] if other["kind"] == "fill"]
        if item["kind"] == "fill":
            points=item["points"]
            for a,b in zip(points,points[1:]+points[:1]):
                side=None
                if abs(a[0]-x0)<EPS and abs(b[0]-x0)<EPS: side="left"; start,end=a[1]-y0,b[1]-y0
                elif abs(a[0]-x1)<EPS and abs(b[0]-x1)<EPS: side="right"; start,end=a[1]-y0,b[1]-y0
                elif abs(a[1]-y0)<EPS and abs(b[1]-y0)<EPS: side="top"; start,end=a[0]-x0,b[0]-x0
                elif abs(a[1]-y1)<EPS and abs(b[1]-y1)<EPS: side="bottom"; start,end=a[0]-x0,b[0]-x0
                if side and abs(end-start)>EPS:
                    midpoint=[(a[0]+b[0])/2,(a[1]+b[1])/2]
                    inward={"left":(.01,0),"right":(-.01,0),
                            "top":(0,.01),"bottom":(0,-.01)}[side]
                    probe=[midpoint[0]+inward[0],midpoint[1]+inward[1]]
                    if any(_inside(probe,fill) for fill in later_fills):
                        continue
                    entries.append({"kind":"fill","side":side,"start":round(min(start,end),3),
                                    "end":round(max(start,end),3),"layer_id":item["layer_id"],
                                    "role":item["role"],"phase":item["phase"],"fill":item["fill"]})
            continue
        points = item["points"]
        for endpoint, neighbor in ((points[0], points[1]), (points[-1], points[-2])):
            probe=[endpoint[j]+.01*(neighbor[j]-endpoint[j]) for j in (0,1)]
            if any(_inside(probe,fill) for fill in later_fills):
                continue
            sides = []
            if abs(endpoint[0]-x0) < EPS: sides.append(("left", endpoint[1]-y0))
            if abs(endpoint[0]-x1) < EPS: sides.append(("right", endpoint[1]-y0))
            if abs(endpoint[1]-y0) < EPS: sides.append(("top", endpoint[0]-x0))
            if abs(endpoint[1]-y1) < EPS: sides.append(("bottom", endpoint[0]-x0))
            angle = math.degrees(math.atan2(neighbor[1]-endpoint[1], neighbor[0]-endpoint[0])) % 180
            for side, coordinate in sides:
                entries.append({"kind":"stroke","side": side, "coordinate": round(coordinate, 3),
                                "tangent": round(angle, 2), "layer_id": item["layer_id"],
                                "role": item["role"], "phase": item["phase"],
                                "stroke_width": item["stroke_width"]})
    return sorted(entries, key=lambda entry: (entry["side"],entry.get("coordinate",entry.get("start")),
                                               entry["layer_id"],entry.get("tangent",0)))
