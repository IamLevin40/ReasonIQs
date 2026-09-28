"""Black and white SVG rendering from structured pattern cell states."""

from __future__ import annotations

import math
from collections import Counter

from generators.spatial.misc.geometry import svg_figure

INK = "#20313d"
GRID_COORDS = (-26, 0, 26)
PATH_POINTS = tuple((x, y) for y in GRID_COORDS for x in GRID_COORDS)
DOT_POINTS = ((-44, -44), (44, -44), (44, 44), (-44, 44),
              (0, -44), (44, 0), (0, 44), (-44, 0))
COUNT_ANCHORS = {
    1: (4,), 2: (3, 5), 3: (1, 4, 7), 4: (0, 2, 6, 8),
    5: (0, 2, 4, 6, 8), 6: (0, 1, 2, 6, 7, 8),
}
PAIRED_COUNT_ANCHORS = {1: (1,), 2: (0, 2), 3: (0, 1, 2)}


def polygon(n: int, radius: float = 16, phase: float = -90) -> str:
    return " ".join(f"{radius*math.cos(math.radians(phase+360*i/n)):.2f},"
                    f"{radius*math.sin(math.radians(phase+360*i/n)):.2f}" for i in range(n))


def shape_markup(shape: str, fill: str, border: str) -> str:
    stroke = f'stroke="{INK}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"'
    dash = ' stroke-dasharray="1 6"' if border == "segmented" else ""
    if shape in ("triangle", "square", "pentagon", "hexagon", "heptagon", "octagon"):
        n = {"triangle": 3, "square": 4, "pentagon": 5, "hexagon": 6,
             "heptagon": 7, "octagon": 8}[shape]
        body = f'<polygon points="{polygon(n, phase=-45 if n == 4 else -90)}" fill="{fill}" {stroke}{dash}/>'
    elif shape in ("circle", "dot"):
        radius = 15 if shape == "circle" else 9
        body = f'<circle r="{radius}" fill="{fill}" {stroke}{dash}/>'
    elif shape == "ellipse":
        body = f'<ellipse rx="17" ry="11" fill="{fill}" {stroke}{dash}/>'
    elif shape == "diamond":
        body = f'<polygon points="0,-17 16,0 0,17 -16,0" fill="{fill}" {stroke}{dash}/>'
    elif shape == "star":
        points = []
        for i in range(10):
            angle = math.radians(-90 + i * 36)
            radius = 17 if i % 2 == 0 else 8
            points.append(f"{radius*math.cos(angle):.2f},{radius*math.sin(angle):.2f}")
        body = f'<polygon points="{" ".join(points)}" fill="{fill}" {stroke}{dash}/>'
    elif shape == "arrow":
        body = f'<path d="M0 -19 L16 -2 L7 -2 L7 17 L-7 17 L-7 -2 L-16 -2 Z" fill="{fill}" {stroke}{dash}/>'
    elif shape == "chevron":
        body = f'<path d="M-17 -10 L0 8 L17 -10 L17 1 L0 18 L-17 1 Z" fill="{fill}" {stroke}{dash}/>'
    elif shape == "cross":
        body = f'<path d="M-5 -17 H5 V-5 H17 V5 H5 V17 H-5 V5 H-17 V-5 H-5 Z" fill="{fill}" {stroke}{dash}/>'
    elif shape == "crescent":
        body = f'<path d="M7 -17 A18 18 0 1 0 7 17 A14 14 0 0 1 7 -17 Z" fill="{fill}" {stroke}{dash}/>'
    elif shape == "semicircle":
        body = f'<path d="M-17 9 A17 17 0 0 1 17 9 Z" fill="{fill}" {stroke}{dash}/>'
    elif shape == "line":
        body = f'<line x1="-16" y1="-12" x2="16" y2="12" {stroke}{dash}/>'
    else:
        raise ValueError(shape)
    if border == "double" and shape != "line":
        body += f'<g transform="scale(.78)">{shape_markup(shape, "none", "smooth")}</g>'
    return body


def _object(obj: dict, fill_override: str | None = None, paired: bool = False,
            focus: bool = False) -> str:
    fill = {"outline": "#fff", "solid": INK, "hatched": "url(#pf-hatch)",
            "dotted": "url(#pf-dots)"}[fill_override or obj["fill"]]
    if fill_override is None and obj["texture"] == "hatch":
        fill = "url(#pf-hatch)"
    elif fill_override is None and obj["texture"] == "dots":
        fill = "url(#pf-dots)"
    count = obj["count"]
    if count == 1:
        anchors = (obj["position"],)
    elif paired and obj["layer"] == "primary" and count <= 3:
        anchors = PAIRED_COUNT_ANCHORS[count]
    else:
        anchors = COUNT_ANCHORS[count]
    size = obj["scale"] * (1.1 if focus else 0.55)
    rotate = obj["rotation"] + {"up": 0, "right": 90, "down": 180, "left": 270}[obj["orientation"]]
    reflection = {"none": "", "vertical": "scale(-1 1)",
                  "horizontal": "scale(1 -1)",
                  "diagonal": "matrix(0 1 1 0 0 0)"}[obj["mirror"]]
    pieces = []
    for anchor in anchors:
        x, y = PATH_POINTS[anchor]
        body = shape_markup(obj["shape"], fill, obj["border"])
        for level in range(obj["nesting"]):
            body += f'<g transform="scale({.62-level*.19:.2f})">{shape_markup(obj["shape"], "none", "smooth")}</g>'
        for i in range(obj["internal_lines"]):
            line_y = -7 + 5*i
            mark_ink = "#fff" if (fill_override or obj["fill"]) == "solid" and obj["texture"] == "plain" else INK
            body += f'<line x1="-8" y1="{line_y}" x2="8" y2="{line_y}" stroke="{mark_ink}" stroke-width="1.7"/>'
        if obj["containment"] == "inside":
            body += f'<circle cx="0" cy="0" r="3" fill="#fff" stroke="{INK}" stroke-width="1.3"/>'
        if obj["containment"] == "outside":
            body += f'<circle cx="15" cy="-10" r="4" fill="#fff" stroke="{INK}" stroke-width="1.5"/>'
        elif obj["containment"] == "around":
            body += f'<circle r="18" fill="none" stroke="{INK}" stroke-width="1.5"/>'
        symmetry_marks = {"vertical": ((-18,-16),(18,-16)),
                          "horizontal": ((-18,-16),(-18,16)),
                          "diagonal": ((-18,-16),(18,16))}
        for mx, my in symmetry_marks.get(obj["symmetry"], ()):
            body += f'<circle cx="{mx}" cy="{my}" r="2.5" fill="{INK}"/>'
        pieces.append(f'<g transform="translate({x:.2f} {y:.2f}) rotate({rotate}) scale({size:.3f}) {reflection}">{body}</g>')
    return "".join(pieces)


def center_only(state: dict) -> bool:
    return (not state["components"] and len(state["objects"]) == 1
            and state["objects"][0]["count"] == 1
            and state["objects"][0]["position"] == 4)


def puzzle_focus(states: list[dict], choices: list[dict] | None = None) -> bool:
    return all(center_only(state) for state in [*states, *(choices or [])])


DEFS = ('<defs><pattern id="pf-hatch" width="6" height="6" patternUnits="userSpaceOnUse">'
        f'<path d="M-1 1 L1 -1 M0 6 L6 0 M5 7 L7 5" stroke="{INK}" stroke-width="1.2"/>'
        '</pattern><pattern id="pf-dots" width="9" height="9" patternUnits="userSpaceOnUse">'
        f'<circle cx="4.5" cy="4.5" r="1.5" fill="{INK}"/></pattern></defs>')


def cell_markup(state: dict, x: float, y: float, unit: float, missing=False,
                focus_mode: bool | None = None) -> str:
    body = f'<rect x="{x:.2f}" y="{y:.2f}" width="{unit:.2f}" height="{unit:.2f}" rx="7" fill="#fff" stroke="{INK}" stroke-width="2"/>'
    cx, cy = x + unit/2, y + unit/2
    if missing:
        return body + (f'<g transform="translate({cx:.2f} {cy:.2f}) scale({unit/104:.3f})">'
                       f'<text x="0" y="13" text-anchor="middle" font-size="42" font-family="Arial,sans-serif" font-weight="700" fill="{INK}">?</text></g>')
    objects = sorted(state["objects"], key=lambda obj: (obj["foreground"] != obj["layer"], obj["layer"] == "inner"))
    paired = len(objects) > 1
    focus = center_only(state) if focus_mode is None else focus_mode
    front = next((obj["foreground"] for obj in objects if obj["layer"] == "primary"), "outer")
    def artwork(obj):
        if not state.get("foreground_mode"):
            return _object(obj, paired=paired, focus=focus)
        is_front = (obj["layer"] == "primary") == (front == "outer")
        return _object(obj, "solid" if is_front else "outline", paired=paired, focus=focus)
    inside = "".join(artwork(obj) for obj in objects)
    for index, amount in Counter(state["components"]).items():
        px, py = DOT_POINTS[index]
        inside += f'<circle cx="{px}" cy="{py}" r="3.3" fill="{INK}"/>'
        if amount > 1:
            inside += f'<circle cx="{px}" cy="{py}" r="6.4" fill="none" stroke="{INK}" stroke-width="1.4"/>'
    return body + f'<g transform="translate({cx:.2f} {cy:.2f}) scale({unit/104:.3f})">{inside}</g>'


def puzzle_figure(states: list[dict], missing: int, layout: str,
                  focus_mode: bool | None = None) -> dict:
    linear = layout == "Linear"
    count = len(states)
    unit = 92 if linear else 104
    gap = 8
    cols = count if linear else 3
    rows = 1 if linear else 3
    pad = 10
    width = 2*pad + cols*unit + (cols-1)*gap
    height = 2*pad + rows*unit + (rows-1)*gap
    body = [DEFS]
    for index, state in enumerate(states):
        row, col = (0, index) if linear else divmod(index, 3)
        body.append(cell_markup(state, pad+col*(unit+gap), pad+row*(unit+gap), unit,
                                index == missing, focus_mode))
    return svg_figure("".join(body), width, height,
                      f"{layout} pattern with cell {missing+1} missing",
                      {"type": "pattern-finding", "layout": layout,
                       "internal_grid": {"rows": 3, "columns": 3, "anchors": PATH_POINTS},
                       "cells": [None if i == missing else state for i, state in enumerate(states)],
                       "missing_cell": missing})


def choice_figure(state: dict, label: str, focus_mode: bool | None = None) -> dict:
    return svg_figure(DEFS + cell_markup(state, 10, 10, 104, focus_mode=focus_mode), 124, 124,
                      label, {"type": "pattern-choice", "cell": state,
                              "internal_grid": {"rows": 3, "columns": 3, "anchors": PATH_POINTS}})
