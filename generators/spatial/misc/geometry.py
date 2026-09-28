"""Exact grid geometry and SVG projections shared by spatial generators.

World coordinates: x points left in the isometric drawing, y points right,
and z points up. Front looks along -y; Left looks along -x.
"""

from __future__ import annotations

from collections import deque

INK = "#243747"

# Each palette is one hue with three brightness levels. Dark outlines carry
# the geometry, so no item depends on recognizing a particular color.
STRUCTURE_PALETTES = {
    "teal": {"top": "#d2eee8", "front": "#a9d9cf", "side": "#81c2b5"},
    "blue": {"top": "#d7e9f8", "front": "#a9cee9", "side": "#7eafd2"},
    "lavender": {"top": "#e6e0f6", "front": "#c7baeb", "side": "#a89ad7"},
    "amber": {"top": "#f8e8cc", "front": "#efd09e", "side": "#ddb977"},
    "coral": {"top": "#f7e0dc", "front": "#eeb9af", "side": "#da988e"},
    "sage": {"top": "#e1efd7", "front": "#bcdbad", "side": "#9ec78d"},
}


def choose_structure_palette(rng):
    return rng.choice(tuple(STRUCTURE_PALETTES))


def connected(cells, dimensions=3):
    cells = set(cells)
    if not cells:
        return False
    seen = {next(iter(cells))}
    queue = deque(seen)
    while queue:
        cell = queue.popleft()
        for axis in range(dimensions):
            for step in (-1, 1):
                other = list(cell)
                other[axis] += step
                other = tuple(other)
                if other in cells and other not in seen:
                    seen.add(other)
                    queue.append(other)
    return seen == cells


def normalize(cells):
    cells = set(map(tuple, cells))
    if not cells:
        return frozenset()
    origin = tuple(min(cell[i] for cell in cells) for i in range(len(next(iter(cells)))))
    return frozenset(tuple(v - origin[i] for i, v in enumerate(cell)) for cell in cells)


def supported(voxels):
    voxels = set(voxels)
    return connected(voxels) and all(z == 0 or (x, y, z - 1) in voxels for x, y, z in voxels)


def svg_figure(body, width, height, alt, geometry, caption=None):
    figure = {
        "kind": "svg", "alt": alt, "geometry": geometry,
        "svg": (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.2f} {height:.2f}">'
                f'<rect width="100%" height="100%" fill="#ffffff"/>{body}</svg>'),
    }
    if caption:
        figure["caption"] = caption
    return figure


def _polygon(points, fill, stroke=INK, width=2):
    vertices = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (f'<polygon points="{vertices}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linejoin="round"/>')


def isometric(voxels, alt="Cube structure", caption=None, palette="teal"):
    """Paint exposed faces back to front from authoritative unit voxels."""
    voxels = set(map(tuple, voxels))
    if not voxels:
        raise ValueError("Empty voxel figure")
    shades = STRUCTURE_PALETTES[palette]
    # An orthographic axonometric basis. All unit edges have fixed lengths.
    def project(point):
        x, y, z = point
        return ((y - x) * 31, (x + y) * 18 - z * 36)

    templates = (
        ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)), shades["top"]),
        ((0, 1, 0), ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)), shades["front"]),
        ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)), shades["side"]),
    )
    faces = []
    for x, y, z in voxels:
        for normal, corners, shade in templates:
            if (x + normal[0], y + normal[1], z + normal[2]) in voxels:
                continue
            world = [tuple(c[i] + (x, y, z)[i] for i in range(3)) for c in corners]
            faces.append((x + y + z, world, shade))
    faces.sort(key=lambda face: face[0])
    projected = [[project(point) for point in world] for _, world, _ in faces]
    minx = min(p[0] for face in projected for p in face)
    miny = min(p[1] for face in projected for p in face)
    maxx = max(p[0] for face in projected for p in face)
    maxy = max(p[1] for face in projected for p in face)
    body = "".join(_polygon([(px - minx + 14, py - miny + 14) for px, py in points], face[2])
                   for face, points in zip(faces, projected))
    geometry = {"type": "voxel-isometric", "voxels": sorted(voxels),
                "palette": palette, "face_shades": shades,
                "projection": {"x": [-31, 18], "y": [31, 18], "z": [0, -36]},
                "visible_faces": [{"vertices": face[1], "shade": face[2]} for face in faces]}
    return svg_figure(body, maxx - minx + 28, maxy - miny + 28, alt, geometry, caption)


def grid_figure(cells, alt, caption=None, unit=28, shade="#eef3f5"):
    cells = set(map(tuple, cells))
    if not cells:
        raise ValueError("Empty grid figure")
    minx, miny = min(x for x, _ in cells), min(y for _, y in cells)
    shifted = {(x - minx, y - miny) for x, y in cells}
    width = (max(x for x, _ in shifted) + 1) * unit + 20
    height = (max(y for _, y in shifted) + 1) * unit + 20
    body = []
    for x, y in sorted(shifted):
        body.append(f'<rect x="{10+x*unit}" y="{10+y*unit}" width="{unit}" height="{unit}" '
                    f'fill="{shade}" stroke="{INK}" stroke-width="1.6"/>')
    return svg_figure("".join(body), width, height, alt,
                      {"type": "grid-cells", "cells": sorted(cells), "unit": unit}, caption)


def polygon_cells_figure(cells, alt, caption=None, unit=30):
    """Render a polyomino as one filled region with exact boundary edges."""
    cells = set(map(tuple, cells))
    if not cells:
        raise ValueError("Empty polygon figure")
    minx, miny = min(x for x, _ in cells), min(y for _, y in cells)
    shifted = {(x - minx, y - miny) for x, y in cells}
    edges = []
    for x, y in shifted:
        for dx, dy, endpoints in (
            (0, -1, ((x, y), (x+1, y))), (1, 0, ((x+1, y), (x+1, y+1))),
            (0, 1, ((x, y+1), (x+1, y+1))), (-1, 0, ((x, y), (x, y+1))),
        ):
            if (x+dx, y+dy) not in shifted:
                edges.append(endpoints)
    body = "".join(f'<rect x="{10+x*unit}" y="{10+y*unit}" width="{unit}" height="{unit}" fill="#eef3f5"/>'
                   for x, y in sorted(shifted))
    body += "".join(f'<line x1="{10+a[0]*unit}" y1="{10+a[1]*unit}" x2="{10+b[0]*unit}" y2="{10+b[1]*unit}" '
                    f'stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>' for a, b in edges)
    return svg_figure(body, (max(x for x, _ in shifted)+1)*unit+20,
                      (max(y for _, y in shifted)+1)*unit+20, alt,
                      {"type": "grid-polygon", "cells": sorted(cells),
                       "polygons": [[[x,y],[x+1,y],[x+1,y+1],[x,y+1]] for x,y in sorted(cells)],
                       "boundary_edges": edges}, caption)
