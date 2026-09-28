"""SVG figures for the normalized ReasonIQs figure contract."""

from __future__ import annotations

import html
import math
import random

from generators.spatial.misc.cube_model import Basis, Cube, Face, NORMALS, X, Y, Z, fold_net, quarter_turns

THEMES = ("Shapes/Polygons", "Dice Dots", "Characters", "Abstract Structures")
ORDER = tuple(NORMALS)
COLORS = ("#e7a8a8", "#91c9bd", "#afbbe7", "#e5c184", "#c9abdb", "#9fc5df")
SHAPES = {"triangle": 1, "square": 4, "pentagon": 1, "hexagon": 2,
          "circle": 4, "star": 1, "rectangle": 2, "parallelogram": 2,
          "trapezoid": 1, "diamond": 2, "donut": 4, "cross": 4,
          "arrow": 1, "chevron": 1, "semicircle": 1, "heart": 1, "octagon": 4}
ABSTRACTS = {"corner_pair": 2, "corner_triangle": 1, "cross_stitches": 4,
             "horizontal_lines": 2, "vertical_lines": 2, "diagonal_lines": 2,
             "solid": 4, "offset_bars": 1, "nested_angles": 1,
             "stepped_blocks": 1, "rays": 1, "zigzag": 1}


def make_markings(rng: random.Random, difficulty: str, selected_theme: str = "Mixed") -> tuple[str, dict[str, dict], dict[str, int]]:
    if selected_theme != "Mixed" and selected_theme not in THEMES:
        raise ValueError("Unknown cube marking theme")
    theme = rng.choice(THEMES) if selected_theme == "Mixed" else selected_theme
    marks = {}
    symmetries = {}
    glyphs = rng.sample("B F G J K L P R 4 7 9".split(), 6)
    shapes = rng.sample(tuple(SHAPES), 6)
    abstracts = rng.sample(tuple(ABSTRACTS), 6)
    colors = rng.sample(COLORS, 6)
    for index, identity in enumerate(ORDER):
        if theme == "Dice Dots":
            marks[identity] = {"kind": "dots", "value": index + 1, "color": "#243747"}
            symmetries[identity] = {1: 4, 2: 2, 3: 2, 4: 4, 5: 4, 6: 2}[index + 1]
        elif theme == "Characters":
            marks[identity] = {"kind": "character", "value": glyphs[index], "color": "#243747", "mirrorable": True}
            symmetries[identity] = 1
        elif theme == "Shapes/Polygons":
            shape = shapes[index]
            marks[identity] = {"kind": "shape", "value": shape, "color": colors[index], "mirrorable": False}
            symmetries[identity] = SHAPES[shape]
        else:
            pattern = abstracts[index]
            marks[identity] = {"kind": "abstract", "value": pattern, "color": colors[index], "mirrorable": False}
            symmetries[identity] = ABSTRACTS[pattern]
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
    if kind == "shape":
        if value in ("circle", "donut"):
            outer = f'<circle cx="50" cy="50" r="30" fill="{color}" stroke="{dark}" stroke-width="4"/>'
            return outer if value == "circle" else outer + f'<circle cx="50" cy="50" r="13" fill="#ffffff" stroke="{dark}" stroke-width="3"/>'
        if value == "rectangle":
            return f'<rect x="19" y="32" width="62" height="36" fill="{color}" stroke="{dark}" stroke-width="4"/>'
        if value == "cross":
            return f'<path d="M39 18H61V39H82V61H61V82H39V61H18V39H39Z" fill="{color}" stroke="{dark}" stroke-width="4" stroke-linejoin="round"/>'
        if value == "semicircle":
            return f'<path d="M20 68A30 30 0 0 1 80 68Z" fill="{color}" stroke="{dark}" stroke-width="4"/>'
        if value == "heart":
            return f'<path d="M50 80L22 52C8 37 23 17 39 26L50 35L61 26C77 17 92 37 78 52Z" fill="{color}" stroke="{dark}" stroke-width="4"/>'
        if value == "star":
            points = []
            for i in range(10):
                angle = -math.pi / 2 + i * math.pi / 5
                radius = 33 if i % 2 == 0 else 15
                points.append(f"{50 + radius * math.cos(angle):.1f},{50 + radius * math.sin(angle):.1f}")
        elif value in ("triangle", "square", "pentagon", "hexagon", "octagon"):
            vertices = {"triangle": 3, "square": 4, "pentagon": 5, "hexagon": 6, "octagon": 8}[value]
            points = []
            for i in range(vertices):
                angle = -math.pi / 2 + i * 2 * math.pi / vertices
                points.append(f"{50 + 30 * math.cos(angle):.1f},{50 + 30 * math.sin(angle):.1f}")
        else:
            coordinates = {
                "parallelogram": ((28, 25), (78, 25), (72, 75), (22, 75)),
                "trapezoid": ((36, 24), (64, 24), (82, 76), (18, 76)),
                "diamond": ((50, 16), (80, 50), (50, 84), (20, 50)),
                "arrow": ((18, 38), (54, 38), (54, 24), (84, 50), (54, 76), (54, 62), (18, 62)),
                "chevron": ((18, 28), (42, 28), (72, 50), (42, 72), (18, 72), (48, 50)),
            }[value]
            points = [f"{x},{y}" for x, y in coordinates]
        return f'<polygon points="{" ".join(points)}" fill="{color}" stroke="{dark}" stroke-width="4" stroke-linejoin="round"/>'
    if kind != "abstract":
        raise ValueError(f"Unknown marking kind: {kind}")
    if value == "solid":
        return f'<rect x="3" y="3" width="94" height="94" fill="{color}"/>'
    if value == "corner_pair":
        return (f'<rect x="11" y="11" width="26" height="26" fill="{color}" stroke="{dark}" stroke-width="3"/>'
                f'<rect x="63" y="63" width="26" height="26" fill="{color}" stroke="{dark}" stroke-width="3"/>')
    if value == "corner_triangle":
        return f'<polygon points="10,10 47,10 10,47" fill="{color}" stroke="{dark}" stroke-width="3"/>'
    if value == "cross_stitches":
        return ''.join(f'<path d="M{x-7} {y-7}L{x+7} {y+7}M{x+7} {y-7}L{x-7} {y+7}" stroke="{dark}" stroke-width="4" stroke-linecap="round"/>'
                       for x in (27, 50, 73) for y in (27, 50, 73))
    if value in ("horizontal_lines", "vertical_lines", "diagonal_lines"):
        if value == "horizontal_lines":
            segments = ((13, y, 87, y) for y in (22, 36, 50, 64, 78))
        elif value == "vertical_lines":
            segments = ((x, 13, x, 87) for x in (22, 36, 50, 64, 78))
        else:
            segments = ((14, 42, 42, 14), (14, 70, 70, 14), (14, 86, 86, 14),
                        (30, 86, 86, 30), (58, 86, 86, 58))
        return ''.join(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="8" stroke-linecap="round"/>'
                       for x1, y1, x2, y2 in segments)
    paths = {
        "offset_bars": '<rect x="15" y="19" width="48" height="13"/><rect x="37" y="44" width="48" height="13"/><rect x="15" y="69" width="48" height="13"/>',
        "nested_angles": '<path d="M18 76V22H76M32 76V36H76M46 76V50H76"/>',
        "stepped_blocks": '<path d="M15 80V60H35V40H55V20H85V80Z"/>',
        "rays": '<path d="M16 74L77 16M35 84L84 35M16 49L49 16"/>',
        "zigzag": '<path d="M13 34L31 66L50 34L69 66L87 34"/>',
    }
    if value in ("offset_bars", "stepped_blocks"):
        return f'<g fill="{color}" stroke="{dark}" stroke-width="3">{paths[value]}</g>'
    return f'<g fill="none" stroke="{color}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round">{paths[value]}</g>'


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
