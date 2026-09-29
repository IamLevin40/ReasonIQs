"""Small, explicit geometric scene model shared by rules and SVG rendering."""

from __future__ import annotations

from copy import deepcopy
import math


def part(shape="circle", x=0, y=0, size=12, *, sides=0, angle=0,
         fill="outline", texture="plain", boundary="solid", role="object",
         variant=0, handedness=1):
    return dict(shape=shape, sides=sides, x=x, y=y, size=size, angle=angle % 360,
                fill=fill, texture=texture, boundary=boundary, role=role,
                variant=variant, handedness=handedness)


GRID_CENTERS = {
    1: ((0, 0),),
    2: ((-24, -24), (24, -24), (-24, 24), (24, 24)),
    3: tuple((x, y) for y in (-31, 0, 31) for x in (-31, 0, 31)),
}


def scene(*components, grid_size=1):
    return {"components": list(components), "stroke_width": 2.6, "canvas": [112, 112],
            "grid": {"size": grid_size, "centers": [list(center) for center in GRID_CENTERS[grid_size]]}}


def cell_part(shape, grid_size, cell, size, **kwargs):
    x, y = GRID_CENTERS[grid_size][cell]
    component = part(shape, x, y, size, **kwargs)
    component["cell"] = cell
    return component


def centered_on_grid(figure):
    grid = figure.get("grid")
    if not isinstance(grid, dict) or grid.get("size") not in GRID_CENTERS:
        return False
    size = grid["size"]
    if grid.get("centers") != [list(center) for center in GRID_CENTERS[size]]:
        return False
    if not figure.get("components"):
        return False
    limit = {1: 40, 2: 17, 3: 11}[size]
    for component in figure["components"]:
        cell = component.get("cell")
        if isinstance(cell, bool) or not isinstance(cell, int) or not 0 <= cell < size * size:
            return False
        x, y = GRID_CENTERS[size][cell]
        if abs(component["x"] - x) > 1e-6 or abs(component["y"] - y) > 1e-6:
            return False
        if not 0 < component["size"] <= limit:
            return False
    for cell in range(size * size):
        occupants = [p for p in figure["components"] if p["cell"] == cell]
        if len(occupants) > 1:
            roles = [p["role"] for p in occupants]
            if not (sorted(roles) == ["inner", "outer"] or
                    all(role == "ring" for role in roles)):
                return False
    return True


def rotate(figure, turns):
    result = deepcopy(figure)
    for component in result["components"]:
        for _ in range(turns % 4):
            component["x"], component["y"] = -component["y"], component["x"]
        component["angle"] = (component["angle"] + 90 * turns) % 360
        if "cell" in component:
            component["cell"] = GRID_CENTERS[figure["grid"]["size"]].index(
                (component["x"], component["y"]))
    return result


def rotate_degrees(figure, degrees):
    """Rotate a scene rigidly; the 45-degree turns expand chiral option pools."""
    result = deepcopy(figure)
    radians = math.radians(degrees)
    cosine, sine = math.cos(radians), math.sin(radians)
    for component in result["components"]:
        x, y = component["x"], component["y"]
        component["x"] = round(x * cosine - y * sine, 8)
        component["y"] = round(x * sine + y * cosine, 8)
        component["angle"] = (component["angle"] + degrees) % 360
    return result


def reflect(figure):
    result = deepcopy(figure)
    for component in result["components"]:
        component["x"] = -component["x"]
        component["angle"] = (-component["angle"]) % 360
        component["handedness"] = -component.get("handedness", 1)
        if "cell" in component:
            component["cell"] = GRID_CENTERS[figure["grid"]["size"]].index(
                (component["x"], component["y"]))
    return result


def _key(figure):
    components = figure["components"]
    cx = sum(p["x"] for p in components) / len(components)
    cy = sum(p["y"] for p in components) / len(components)
    extent = max(max(abs(p["x"] - cx), abs(p["y"] - cy), p["size"]) for p in components)
    return tuple(sorted((p["shape"], p["sides"], p["role"], p["fill"], p["texture"],
                         p["boundary"], round((p["x"] - cx) / extent, 5),
                         round((p["y"] - cy) / extent, 5), round(p["size"] / extent, 5),
                         p["angle"] % 360, p.get("variant", 0),
                         p.get("handedness", 1)) for p in components))


def appearance_signature(figure):
    """Visible scene identity, ignoring component order and border-only changes."""
    periods = {"circle": 0, "dot": 0, "ellipse": 180, "line": 180,
               "cross": 90, "star": 72}
    result = []
    for p in figure["components"]:
        period = 360 / p["sides"] if p["shape"] == "polygon" else periods.get(p["shape"], 360)
        angle = 0 if period == 0 else round(p["angle"] % period, 4)
        result.append((p["shape"], p["sides"], round(p["x"], 3), round(p["y"], 3),
                       round(p["size"], 3), angle, p["fill"], p["texture"], p.get("cell"),
                       p.get("variant", 0), p.get("handedness", 1)))
    return tuple(sorted(result))


def appearance_distance(a, b):
    """Estimate visible separation while ignoring outline-only decoration."""
    left = sorted(a["components"], key=lambda p: (p["shape"], p["x"], p["y"]))
    right = sorted(b["components"], key=lambda p: (p["shape"], p["x"], p["y"]))
    score = 24 * abs(len(left) - len(right))
    for p, q in zip(left, right):
        score += 22 * (p["shape"] != q["shape"])
        score += 5 * abs(p["sides"] - q["sides"])
        score += math.hypot(p["x"] - q["x"], p["y"] - q["y"])
        score += 1.8 * abs(p["size"] - q["size"])
        score += 12 * (p["fill"] != q["fill"])
        score += 12 * (p["texture"] != q["texture"])
        score += 15 * (p.get("variant", 0) != q.get("variant", 0))
        score += 15 * (p.get("handedness", 1) != q.get("handedness", 1))
        if p["shape"] in ("arrow", "chevron", "arc", "concave", "motif"):
            delta = abs((p["angle"] - q["angle"]) % 360)
            score += min(delta, 360 - delta) / 4
    return score


def rotation_signature(figure):
    """Translation/scale normalized, rotation invariant, but reflection sensitive."""
    return min(_key(rotate_degrees(figure, degrees)) for degrees in range(0, 360, 45))


def reflected_rotation_signature(figure):
    return rotation_signature(reflect(figure))


def equivalent_by_rotation(a, b):
    return rotation_signature(a) == rotation_signature(b)
