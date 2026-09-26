"""SVG figures for the normalized ReasonIQs figure contract."""

from __future__ import annotations

import html
import random

from generators.spatial.misc.cube_model import Basis, Cube, Face, IDS, NORMALS, ROOT, X, Y, Z, fold_net, quarter_turns

THEMES = ("Shapes/Polygons", "Dice Dots", "Characters", "Abstract Structures")
ORDER = tuple(NORMALS)
COLORS = ("#e7a8a8", "#91c9bd", "#afbbe7", "#e5c184", "#c9abdb", "#9fc5df")


def make_markings(rng: random.Random, difficulty: str, selected_theme: str = "Mixed") -> tuple[str, dict[str, dict], dict[str, int]]:
    if selected_theme != "Mixed" and selected_theme not in THEMES:
        raise ValueError("Unknown cube marking theme")
    theme = rng.choice(THEMES) if selected_theme == "Mixed" else selected_theme
    marks = {}
    symmetries = {}
    glyphs = rng.sample("B F G J K L P R 4 7 9 ↗ →".split(), 6)
    for index, identity in enumerate(ORDER):
        if theme == "Dice Dots":
            marks[identity] = {"kind": "dots", "value": index + 1, "color": "#243747"}
            symmetries[identity] = {1: 4, 2: 2, 3: 2, 4: 4, 5: 4, 6: 2}[index + 1]
        elif theme == "Characters":
            marks[identity] = {"kind": "character", "value": glyphs[index], "color": "#243747"}
            symmetries[identity] = 1
        elif theme == "Shapes/Polygons":
            vertices = 3 + index
            marks[identity] = {"kind": "polygon", "value": vertices, "color": rng.choice(COLORS)}
            symmetries[identity] = {3: 1, 4: 4, 5: 1, 6: 2, 7: 1, 8: 4}[vertices]
        else:
            marks[identity] = {"kind": "abstract", "value": index, "color": rng.choice(COLORS)}
            symmetries[identity] = 1
    return theme, marks, symmetries


def artwork(mark: dict) -> str:
    kind, value = mark["kind"], mark["value"]
    dark, color = "#263b49", mark["color"]
    if kind == "dots":
        locations = {
            1: [(50, 50)], 2: [(28, 28), (72, 72)],
            3: [(28, 28), (50, 50), (72, 72)],
            4: [(28, 28), (72, 28), (28, 72), (72, 72)],
            5: [(28, 28), (72, 28), (50, 50), (28, 72), (72, 72)],
            6: [(28, 25), (72, 25), (28, 50), (72, 50), (28, 75), (72, 75)],
        }[value]
        return "".join(f'<circle cx="{x}" cy="{y}" r="7.3" fill="{dark}"/>' for x, y in locations)
    if kind == "character":
        return (f'<text x="50" y="52" text-anchor="middle" dominant-baseline="middle" '
                f'font-family="Arial" font-size="58" font-weight="700" fill="{dark}">{html.escape(value)}</text>')
    if kind == "polygon":
        import math
        vertices = value
        points = []
        for i in range(vertices):
            angle = -math.pi / 2 + i * 2 * math.pi / vertices
            points.append(f"{50 + 30 * math.cos(angle):.1f},{50 + 30 * math.sin(angle):.1f}")
        return f'<polygon points="{" ".join(points)}" fill="{color}" stroke="{dark}" stroke-width="4"/>'
    # Each abstract composition has a distinct count and an asymmetric dark anchor.
    count = value + 1
    strokes = "".join(f'<line x1="{20 + i * 9}" y1="36" x2="{32 + i * 9}" y2="67" stroke="{dark}" stroke-width="3"/>'
                      for i in range(count))
    return (f'<rect x="17" y="23" width="66" height="56" rx="7" fill="{color}" stroke="{dark}" stroke-width="3"/>'
            f'{strokes}<circle cx="29" cy="27" r="5" fill="{dark}"/>')


def marking_svg(face: Face, basis: Basis, marks: dict[str, dict]) -> str:
    degrees = quarter_turns(face.mark_up, basis) * 90
    mirror = "translate(100 0) scale(-1 1) " if face.mirrored else ""
    return f'<g transform="rotate({degrees} 50 50) {mirror}">{artwork(marks[face.identity])}</g>'


def net_figure(cells, faces: dict[tuple[int, int], Face], marks: dict[str, dict], alt: str) -> dict:
    folded = fold_net(cells)
    if folded is None:
        raise ValueError("Cannot render an invalid cube net")
    unit, margin = 96, 12
    width = (max(x for x, _ in cells) + 1) * unit + 2 * margin
    height = (max(y for _, y in cells) + 1) * unit + 2 * margin
    body = [f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
    for x, y in sorted(cells, key=lambda p: (p[1], p[0])):
        tx, ty = margin + unit * x, margin + unit * y
        body.append(f'<g transform="translate({tx} {ty}) scale(.96)">'
                    '<rect width="100" height="100" fill="#ffffff" stroke="#263b49" stroke-width="2.3"/>'
                    f'{marking_svg(faces[(x, y)], folded[(x, y)], marks)}</g>')
    return {"kind": "svg", "svg": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{"".join(body)}</svg>', "alt": alt}


DISPLAY = {
    Y: (Basis(Y, (0, 0, -1), X), ((120, 17), (218, 68), (22, 68), (120, 119))),
    Z: (Basis(Z, Y, X), ((22, 68), (120, 119), (22, 181), (120, 232))),
    X: (Basis(X, Y, (0, 0, -1)), ((120, 119), (218, 68), (120, 232), (218, 181))),
}


def cube_figure(cube: Cube, marks: dict[str, dict], alt: str) -> dict:
    body = ['<rect width="240" height="250" fill="#ffffff"/>']
    shades = {Y: "#f2f5f5", Z: "#ffffff", X: "#e7eeee"}
    for normal in (Y, Z, X):
        basis, (tl, tr, bl, br) = DISPLAY[normal]
        points = " ".join(f"{x},{y}" for x, y in (tl, tr, br, bl))
        body.append(f'<polygon points="{points}" fill="{shades[normal]}" stroke="#263b49" stroke-width="3" stroke-linejoin="round"/>')
        a, b = (tr[0] - tl[0]) / 100, (tr[1] - tl[1]) / 100
        c, d = (bl[0] - tl[0]) / 100, (bl[1] - tl[1]) / 100
        body.append(f'<g transform="matrix({a} {b} {c} {d} {tl[0]} {tl[1]})">'
                    f'{marking_svg(cube[normal], basis, marks)}</g>')
    return {"kind": "svg", "svg": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 250">{"".join(body)}</svg>', "alt": alt}
