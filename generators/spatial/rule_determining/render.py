"""Neutral SVG projection of an already solved transformation graph."""
from __future__ import annotations

import html
import math

from generators.spatial.misc.geometry import svg_figure

INK = "#243747"
FILL = "#f5f8fa"
ACCENT = "#dfecff"  # Spatial soft accent; decorative only.


def _polygon(sides, radius=20, phase=-90):
    return " ".join(f"{radius*math.cos(math.radians(phase+i*360/sides)):.2f},"
                    f"{radius*math.sin(math.radians(phase+i*360/sides)):.2f}" for i in range(sides))


def _shape(shape, x, y):
    style = f'fill="{FILL}" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"'
    if shape == "circle": body = f'<circle r="20" {style}/>'
    elif shape in ("triangle", "square", "pentagon", "hexagon", "octagon"):
        sides = {"triangle": 3, "square": 4, "pentagon": 5, "hexagon": 6, "octagon": 8}[shape]
        body = f'<polygon points="{_polygon(sides, phase=-45 if shape == "square" else -90)}" {style}/>'
    elif shape == "diamond": body = f'<polygon points="0,-21 21,0 0,21 -21,0" {style}/>'
    elif shape == "star":
        points = " ".join(f"{(21 if i%2==0 else 9)*math.cos(math.radians(-90+i*36)):.2f},"
                          f"{(21 if i%2==0 else 9)*math.sin(math.radians(-90+i*36)):.2f}" for i in range(10))
        body = f'<polygon points="{points}" {style}/>'
    elif shape == "cross": body = f'<path d="M-6 -21 H6 V-6 H21 V6 H6 V21 H-6 V6 H-21 V-6 H-6 Z" {style}/>'
    elif shape == "trapezoid": body = f'<polygon points="-13,-18 13,-18 22,18 -22,18" {style}/>'
    elif shape == "parallelogram": body = f'<polygon points="-12,-19 22,-19 12,19 -22,19" {style}/>'
    elif shape == "semicircle": body = f'<path d="M-21 12 A21 21 0 0 1 21 12 Z" {style}/>'
    elif shape == "crescent": body = f'<path d="M8 -20 A21 21 0 1 0 8 20 A15 15 0 0 1 8 -20 Z" {style}/>'
    elif shape == "chevron": body = f'<path d="M-22 -13 L0 9 L22 -13 L22 -2 L0 20 L-22 -2 Z" {style}/>'
    else: raise ValueError(shape)
    return f'<g transform="translate({x:.1f} {y:.1f})">{body}</g>'


def render_section(graph, section):
    """Render only graph geometry; rule execution never occurs here."""
    nodes = [n for n in graph["nodes"] if n["section"] == section]
    lookup = {n["id"]: n for n in nodes}
    edges = [e for e in graph["edges"] if e["section"] == section]
    min_row = min(n["cell"][0] for n in nodes)
    max_row = max(n["cell"][0] for n in nodes)
    max_col = max(n["cell"][1] for n in nodes)
    cw, ch = graph["grid"]["cell_width"], graph["grid"]["cell_height"]
    width, height = (max_col+1)*cw+56, (max_row-min_row+1)*ch+28
    def center(node):
        row, col = node["cell"]
        return 28+(col+.5)*cw, 14+(row-min_row+.5)*ch
    parts = []
    if section == "demonstration":
        for link in graph.get("reuse_links", []):
            a, b = lookup[link["from"]], lookup[link["to"]]
            ax, ay = center(a); bx, by = center(b)
            lane = ax + 54
            parts.append(f'<path d="M{ax+19:.1f} {ay+22:.1f} H{lane:.1f} '
                         f'V{by-22:.1f} H{bx+19:.1f}" '
                         f'fill="none" stroke="#93afcc" stroke-width="2" '
                         f'stroke-dasharray="5 5"/>')
    for edge in edges:
        a, b = lookup[edge["from"]], lookup[edge["to"]]
        ax, ay = center(a); bx, by = center(b)
        if ay == by:
            direction = 1 if bx > ax else -1
            start = ax + direction*(51 if a["kind"] == "box" else 24)
            end = bx - direction*(54 if b["kind"] == "box" else 27)
            parts.append(f'<path d="M{start:.1f} {ay:.1f} H{end:.1f}" fill="none" stroke="{INK}" stroke-width="2.2"/>')
            parts.append(f'<polygon points="{end:.1f},{ay:.1f} {end-direction*9:.1f},{ay-5:.1f} {end-direction*9:.1f},{ay+5:.1f}" fill="{INK}"/>')
        else:
            start = ay + (26 if a["kind"] == "box" else 24)
            end = by - (30 if b["kind"] == "box" else 27)
            parts.append(f'<path d="M{ax:.1f} {start:.1f} V{end:.1f}" fill="none" stroke="{INK}" stroke-width="2.2"/>')
            parts.append(f'<polygon points="{bx:.1f},{end:.1f} {bx-5:.1f},{end-9:.1f} {bx+5:.1f},{end-9:.1f}" fill="{INK}"/>')
    for node in nodes:
        x, y = center(node)
        if node["kind"] == "operator":
            parts.append(_shape(node["shape"], x, y))
        else:
            label = html.escape(node["value"])
            font = min(19, 92/max(1, len(label)))
            parts.append(f'<rect x="{x-50:.1f}" y="{y-26:.1f}" width="100" height="52" rx="9" '
                         f'fill="{ACCENT if section == "query" else "#ffffff"}" stroke="{INK}" stroke-width="2"/>')
            parts.append(f'<text x="{x:.1f}" y="{y+1:.1f}" text-anchor="middle" dominant-baseline="middle" '
                         f'font-family="Arial,sans-serif" font-weight="700" font-size="{font:.1f}" fill="{INK}">{label}</text>')
    alt = ("Connected transformations with repeated shapes linked vertically" if section == "demonstration"
           else "New input followed by a directed chain of known shapes and an unknown output")
    return svg_figure("".join(parts), width, height, alt,
                      {"section": section, "grid": graph["grid"],
                       "node_ids": [n["id"] for n in nodes], "edge_count": len(edges)},
                      "Examples" if section == "demonstration" else "Find the output")


def render_graph(graph):
    """Compatibility helper returning the demonstration projection."""
    return render_section(graph, "demonstration")
