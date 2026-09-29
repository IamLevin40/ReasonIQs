"""Neutral, fixed-scale SVG renderer for structured odd-one-out scenes."""

from __future__ import annotations

import math

from generators.spatial.misc.geometry import svg_figure

INK = "#20313d"
DEFS = ('<defs><pattern id="wdb-stripe" width="6" height="6" patternUnits="userSpaceOnUse">'
        f'<path d="M-1 1 L1 -1 M0 6 L6 0 M5 7 L7 5" stroke="{INK}" stroke-width="1.2"/>'
        '</pattern><pattern id="wdb-dot" width="7" height="7" patternUnits="userSpaceOnUse">'
        f'<circle cx="3.5" cy="3.5" r="1.2" fill="{INK}"/></pattern></defs>')

MOTIFS = (
    ((-1, -1), (-.35, -1), (-.35, .25), (1, .25), (1, .9), (-1, .9)),
    ((-.9, -1), (-.2, -1), (-.2, -.35), (.45, -.35), (.45, .3), (1, .3), (1, .95), (-.9, .95)),
    ((-1, -1), (.8, -1), (.8, -.35), (-.25, -.35), (-.25, .2), (.45, .2), (.45, .95), (-1, .95)),
    ((-.95, -1), (-.3, -1), (-.3, -.15), (.95, -.15), (.95, .5), (.25, .5), (.25, .95), (-.95, .95)),
    ((-1, -.9), (-.35, -.9), (-.35, -.2), (.35, -.2), (.35, -.9), (1, -.9), (1, .45), (.1, .45), (.1, 1), (-1, 1)),
    ((-.95, -1), (.4, -1), (.4, -.3), (1, -.3), (1, .35), (.15, .35), (.15, 1), (-.5, 1), (-.5, .3), (-.95, .3)),
    ((-1, -.95), (-.3, -.95), (-.3, -.2), (.3, -.2), (.3, -.95), (1, -.95), (1, .2), (.35, .2), (.35, 1), (-1, 1)),
    ((-.9, -1), (.85, -1), (.85, -.3), (.2, -.3), (.2, .25), (1, .25), (1, .9), (-.9, .9)),
    ((-.8, -1), (.15, -1), (-.25, -.2), (.9, -.2), (-.25, 1), (-.05, .2), (-.9, .2)),
    ((-1, -.8), (-.25, -1), (.95, -.15), (.5, .35), (-.15, -.1), (-.35, .95), (-1, .75)),
    ((-.95, -1), (-.2, -1), (-.2, -.35), (.95, -.85), (.95, .05), (-.2, .45), (-.2, 1), (-.95, 1)),
    ((-1, -.95), (-.2, -.95), (.15, -.4), (1, -.4), (1, .2), (.4, .2), (.75, .95), (-.1, .95), (-.55, .2), (-1, .2)),
)


def _points(n, size, phase=-90):
    return " ".join(f"{size * math.cos(math.radians(phase + i * 360 / n)):.2f},"
                    f"{size * math.sin(math.radians(phase + i * 360 / n)):.2f}" for i in range(n))


def _path(component):
    shape, size = component["shape"], component["size"]
    if shape == "motif":
        points = MOTIFS[component["variant"] % len(MOTIFS)]
        return '<polygon points="' + ' '.join(
            f'{x * size:.2f},{y * size:.2f}' for x, y in points) + '"'
    if shape == "polygon":
        return f'<polygon points="{_points(component["sides"], size)}"'
    if shape == "concave":
        s = size
        return f'<polygon points="{-s},{-s} {s},{-s} {s},{s} 0,{s*.22:.2f} {-s},{s}"'
    if shape == "star":
        points = []
        for i in range(10):
            radius = size if i % 2 == 0 else size * .46
            angle = math.radians(-90 + i * 36)
            points.append(f"{radius*math.cos(angle):.2f},{radius*math.sin(angle):.2f}")
        return f'<polygon points="{" ".join(points)}"'
    if shape == "circle" or shape == "dot":
        return f'<circle r="{size}"'
    if shape == "ellipse":
        return f'<ellipse rx="{size}" ry="{size*.64:.2f}"'
    if shape == "line":
        return f'<line x1="{-size}" y1="0" x2="{size}" y2="0"'
    if shape == "arc":
        return f'<path d="M{-size} 0 A{size} {size} 0 1 1 {size} 0"'
    if shape == "arrow":
        s = size / 20
        return f'<path d="M0 {-20*s} L{16*s} {-2*s} L{7*s} {-2*s} L{7*s} {18*s} L{-7*s} {18*s} L{-7*s} {-2*s} L{-16*s} {-2*s} Z"'
    if shape == "chevron":
        s = size
        return f'<path d="M{-s} {-s*.6:.2f} L0 {s*.55:.2f} L{s} {-s*.6:.2f} L{s} 0 L0 {s} L{-s} 0 Z"'
    if shape == "cross":
        s = size
        return f'<path d="M{-s*.28:.2f} {-s} H{s*.28:.2f} V{-s*.28:.2f} H{s} V{s*.28:.2f} H{s*.28:.2f} V{s} H{-s*.28:.2f} V{s*.28:.2f} H{-s} V{-s*.28:.2f} H{-s*.28:.2f} Z"'
    if shape == "kite":
        s = size
        return f'<polygon points="0,{-s} {s*.78:.2f},{-s*.12:.2f} 0,{s} {-s*.58:.2f},{-s*.12:.2f}"'
    if shape == "shield":
        s = size
        return (f'<polygon points="{-s},{-s*.75:.2f} {s},{-s*.75:.2f} '
                f'{s*.82:.2f},{s*.24:.2f} 0,{s} {-s*.82:.2f},{s*.24:.2f}"')
    if shape == "semicircle":
        return f'<path d="M{-size} 0 A{size} {size} 0 0 1 {size} 0 Z"'
    if shape == "crescent":
        s = size
        return (f'<path d="M{s*.25:.2f} {-s} A{s} {s} 0 1 0 {s*.25:.2f} {s} '
                f'A{s*.7:.2f} {s*.7:.2f} 0 0 1 {s*.25:.2f} {-s} Z"')
    raise ValueError(f"Unknown shape: {shape}")


def render_figure(figure, alt):
    body = [DEFS, f'<rect x="4" y="4" width="104" height="104" rx="10" '
            f'fill="#fff" stroke="{INK}" stroke-width="1.8"/>']
    for p in figure["components"]:
        fill = (INK if p["fill"] == "solid" else "url(#wdb-stripe)" if p["texture"] == "striped"
                else "url(#wdb-dot)" if p["texture"] == "dotted" else "#fff")
        if p["shape"] in ("line", "arc"):
            fill = "none"
        dash = ' stroke-dasharray="5 4"' if p["boundary"] == "dashed" else ""
        body.append(f'<g transform="translate({56+p["x"]} {56+p["y"]}) rotate({p["angle"]}) '
                    f'scale({p.get("handedness", 1)} 1)">'
                    f'{_path(p)} fill="{fill}" stroke="{INK}" stroke-width="{figure["stroke_width"]}"'
                    f' stroke-linejoin="round" stroke-linecap="round"{dash}/></g>')
    return svg_figure("".join(body), 112, 112, alt,
                      {"components": figure["components"], "stroke_width": figure["stroke_width"],
                       "grid": figure["grid"],
                       "canvas": figure["canvas"], "frame": {"x": 4, "y": 4, "size": 104, "radius": 10},
                       "grayscale_solvable": True})
