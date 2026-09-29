"""Construct complete cell-centered scenes before choosing the outlier."""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations, permutations
import math

from .model import appearance_signature, cell_part, scene
from .variation import select_options


GLYPHS = (
    ("circle", 0), ("ellipse", 0), ("polygon", 3), ("polygon", 4),
    ("polygon", 5), ("polygon", 6), ("star", 0), ("cross", 0),
    ("chevron", 0), ("arrow", 0), ("kite", 0), ("shield", 0),
    ("semicircle", 0), ("crescent", 0),
)
STRAIGHT = (GLYPHS[2], GLYPHS[3], GLYPHS[4], GLYPHS[5], GLYPHS[6],
            GLYPHS[7], GLYPHS[8], GLYPHS[9], GLYPHS[10], GLYPHS[11])
DIRECTIONAL = (GLYPHS[8], GLYPHS[9], GLYPHS[10], GLYPHS[11])
TRIPLES = ((0, 6, 3), (1, 7, 4), (12, 10, 5), (13, 9, 2),
           (0, 11, 8), (1, 6, 4), (12, 7, 5), (13, 10, 3))
PERIPHERAL = (0, 1, 2, 3, 5, 6, 7, 8)


def _symbol(grid_size, cell, glyph, size, **kwargs):
    shape, sides = glyph
    return cell_part(shape, grid_size, cell, size, sides=sides, **kwargs)


def _move(component, grid_size, cell):
    from .model import GRID_CENTERS

    component["cell"] = cell
    component["x"], component["y"] = GRID_CENTERS[grid_size][cell]


def _candidate(kind, serial, theme):
    glyph = GLYPHS[serial % len(GLYPHS)]
    if kind in ("count_three", "count_three_grid"):
        size = 2 if kind == "count_three" else 3
        layouts = tuple(combinations(range(size * size), 3))
        cells = layouts[serial // len(GLYPHS) % len(layouts)]
        empty = next(cell for cell in range(size * size) if cell not in cells)
        good = scene(*(_symbol(size, cell, glyph, 14 if size == 2 else 8)
                       for cell in cells), grid_size=size)
        bad = deepcopy(good)
        bad["components"].append(_symbol(size, empty, glyph, 14 if size == 2 else 8))
    elif kind == "even_sides":
        sides = (4, 6, 8)[serial % 3]
        angle = (serial // 3 % 8) * 7
        good = scene(cell_part("polygon", 1, 0, 31, sides=sides, angle=angle, role="outer"))
        bad = deepcopy(good)
        bad["components"][0]["sides"] += 1
    elif kind in ("one_solid", "two_striped", "balanced", "row_fill"):
        if kind == "one_solid":
            cells = tuple(combinations(range(4), 3))[serial // len(GLYPHS) % 4]
            solid = {cells[serial // 4 % 3]}
            striped = set()
        elif kind == "row_fill":
            cells = tuple(range(4))
            solid = {serial // 3 % 2, 2 + serial // 5 % 2}
            striped = set()
        else:
            cells = tuple(range(4))
            selected = tuple(combinations(cells, 2))[serial // len(GLYPHS) % 6]
            solid = set(selected) if kind == "balanced" else set()
            striped = set(selected) if kind == "two_striped" else set()
        good = scene(*(_symbol(2, cell, glyph, 14,
                               fill="solid" if cell in solid else "outline",
                               texture="striped" if cell in striped else "plain")
                       for cell in cells), grid_size=2)
        bad = deepcopy(good)
        if kind == "two_striped":
            next(p for p in bad["components"] if p["cell"] in striped)["texture"] = "plain"
        elif kind == "row_fill":
            top_solid = next(p for p in bad["components"] if p["cell"] < 2 and p["fill"] == "solid")
            bottom_outline = next(p for p in bad["components"] if p["cell"] >= 2 and p["fill"] == "outline")
            top_solid["fill"] = "outline"
            bottom_outline["fill"] = "solid"
        else:
            next(p for p in bad["components"] if p["fill"] == "outline")["fill"] = "solid"
    elif kind == "closed":
        good = scene(_symbol(1, 0, glyph, 29))
        bad = scene(cell_part("arc", 1, 0, 29, angle=serial // 14 % 4 * 90))
    elif kind == "straight":
        good = scene(_symbol(1, 0, STRAIGHT[serial % len(STRAIGHT)], 29))
        bad = scene(_symbol(1, 0, (GLYPHS[0], GLYPHS[1], GLYPHS[12], GLYPHS[13])[
            serial // len(STRAIGHT) % 4], 29))
    elif kind == "convex":
        sides = 3 + serial % 6
        good = scene(cell_part("polygon", 1, 0, 30, sides=sides,
                               angle=serial // 6 % 6 * 10))
        bad = scene(cell_part("concave", 1, 0, 30, angle=serial // 6 % 6 * 10))
    elif kind == "directions":
        cells = tuple(combinations(range(4), 2))[serial // 4 % 6]
        arrow = DIRECTIONAL[serial % len(DIRECTIONAL)]
        angle = (serial // 24 % 4) * 90
        good = scene(_symbol(2, cells[0], arrow, 15, angle=angle, role="first"),
                     _symbol(2, cells[1], arrow, 15, angle=angle, role="second"), grid_size=2)
        bad = deepcopy(good)
        bad["components"][1]["angle"] = (angle + 90) % 360
    elif kind in ("half_sides", "one_less"):
        outer_sides = (6, 8)[serial % 2] if kind == "half_sides" else 4 + serial % 5
        inner_sides = outer_sides // 2 if kind == "half_sides" else outer_sides - 1
        angle = serial // 5 % 8 * 9
        good = scene(cell_part("polygon", 1, 0, 33, sides=outer_sides, role="outer", angle=angle),
                     cell_part("polygon", 1, 0, 12, sides=inner_sides, role="inner",
                               angle=angle + 12))
        bad = deepcopy(good)
        bad["components"][1]["sides"] += 1
    elif kind == "unique":
        cells = tuple(combinations(range(4), 3))[serial // 8 % 4]
        triple = TRIPLES[serial % len(TRIPLES)]
        good = scene(*(_symbol(2, cell, GLYPHS[index], 14)
                       for cell, index in zip(cells, triple)), grid_size=2)
        bad = deepcopy(good)
        bad["components"][2]["shape"] = bad["components"][0]["shape"]
        bad["components"][2]["sides"] = bad["components"][0]["sides"]
    elif kind in ("permutation", "unique_sides"):
        columns = tuple(permutations(range(3)))[serial // 3 % 6]
        if kind == "permutation":
            shapes = tuple(GLYPHS[index] for index in TRIPLES[serial // 18 % len(TRIPLES)])
        else:
            start = (3, 4, 5)[serial // 18 % 3]
            shapes = tuple(("polygon", start + row) for row in range(3))
        good = scene(*(_symbol(3, row * 3 + columns[row], shapes[row], 8)
                       for row in range(3)), grid_size=3)
        bad = deepcopy(good)
        if kind == "permutation":
            row = serial // 18 % 3
            _move(bad["components"][row], 3, row * 3 + (columns[row] + 1) % 3)
        else:
            bad["components"][serial // 54 % 2]["sides"] += 1
    elif kind == "reflection":
        good = scene(cell_part("motif", 1, 0, 29, angle=serial % 8 * 45,
                               fill="solid", variant=theme))
        bad = deepcopy(good)
        bad["components"][0]["handedness"] = -1
    elif kind == "clockwise":
        from .model import GRID_CENTERS

        cells = theme["cells"][serial % len(theme["cells"])]
        ordered = sorted(cells, key=lambda cell: math.atan2(
            GRID_CENTERS[3][cell][1], GRID_CENTERS[3][cell][0]))
        good = scene(*(_symbol(3, cell, glyph, 8)
                       for cell, glyph in zip(ordered, theme["glyphs"])), grid_size=3)
        bad = deepcopy(good)
        for field in ("shape", "sides"):
            bad["components"][0][field], bad["components"][1][field] = (
                bad["components"][1][field], bad["components"][0][field])
    elif kind == "nested":
        shape, sides = (GLYPHS[0], GLYPHS[1], GLYPHS[3], GLYPHS[4], GLYPHS[5])[
            serial % 5]
        medium = (20, 23, 26)[serial // 5 % 3]
        small = (9, 12, 15)[serial // 15 % 3]
        good = scene(*(cell_part(shape, 1, 0, radius, sides=sides, role="ring")
                       for radius in (34, medium, small)))
        bad = deepcopy(good)
        bad["components"].pop()
    elif kind == "pairs":
        occupied = tuple(combinations(range(4), 3))[serial % 4]
        parts = []
        for index, cell in enumerate(occupied):
            inner_sides = (3, 4)[(serial // 4 + index) % 2]
            parts.extend((cell_part("polygon", 2, cell, 16, sides=inner_sides * 2, role="outer"),
                          cell_part("polygon", 2, cell, 7, sides=inner_sides, role="inner")))
        good = scene(*parts, grid_size=2)
        bad = deepcopy(good)
        bad["components"][2 * (serial // 16 % 3) + 1]["sides"] += 1
    else:
        raise ValueError(kind)
    return good, bad


def _clockwise_cells():
    from .model import GRID_CENTERS

    result = []
    for cells in combinations(PERIPHERAL, 3):
        (ax, ay), (bx, by), (cx, cy) = (GRID_CENTERS[3][cell] for cell in cells)
        area2 = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))
        if area2 >= 900:
            result.append(cells)
    return tuple(result)


def build_grid(rule, rng, choice_count):
    from .rules import matches

    theme = None
    if rule.builder == "reflection":
        from .render import MOTIFS

        theme = rng.randrange(len(MOTIFS))
    elif rule.builder == "clockwise":
        theme = {"cells": _clockwise_cells(),
                 "glyphs": tuple(GLYPHS[index] for index in rng.choice(TRIPLES))}
    serials = list(range(8 if rule.builder == "reflection" else 240))
    rng.shuffle(serials)
    candidates = []
    seen = set()
    reference = None
    for serial in serials:
        good, bad = _candidate(rule.builder, serial, theme)
        if reference is None:
            reference = good
        key = appearance_signature(good)
        if key in seen or not matches(rule, good, reference) or matches(rule, bad, reference):
            continue
        seen.add(key)
        candidates.append((good, bad))
    if not candidates:
        raise ValueError(f"No {rule.id} candidates")
    return select_options(rule, candidates, rng, choice_count, reference)
