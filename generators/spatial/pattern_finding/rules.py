"""Declarative attribute rules and structured cell construction.

Linear and Matrix use a single reading order. Mixed permits independent row
and column rules. Every mutable value is evaluated from a rule.
"""

from __future__ import annotations

from copy import deepcopy
import math


DOMAINS = {
    "shape": ("triangle", "square", "pentagon", "hexagon", "diamond", "star", "arrow", "chevron", "crescent", "cross", "ellipse", "semicircle", "circle", "line"),
    "sides": (3, 4, 5, 6, 7, 8),
    "position": (0, 1, 2, 3, 5, 6, 7, 8),
    "rotation": (0, 45, 90, 135, 180, 225, 270, 315),
    "fill": ("outline", "solid", "hatched", "dotted"),
    "count": (1, 2, 3, 4, 5, 6),
    "texture": ("plain", "hatch", "dots"),
    "border": ("smooth", "segmented", "double"),
    "internal_lines": (0, 1, 2, 3),
    "mirror": ("none", "vertical", "horizontal", "diagonal"),
    "nesting": (0, 1, 2),
    "containment": ("inside", "outside", "around"),
    "foreground": ("outer", "inner"),
    "orientation": ("up", "right", "down", "left"),
    "symmetry": ("vertical", "horizontal", "diagonal"),
}

BASE_OBJECT = {
    "shape": "arrow", "sides": 3, "position": 4, "rotation": 0,
    "fill": "outline", "size": 1.0, "scale": 1.0, "count": 1, "texture": "plain",
    "border": "smooth", "internal_lines": 0, "mirror": "none",
    "nesting": 0, "containment": "none", "foreground": "outer",
    "orientation": "up", "symmetry": "none", "layer": "primary",
}


def coordinates(index: int, layout: str) -> tuple[int, int, int]:
    if layout == "Linear":
        return 0, index, index
    return index // 3, index % 3, index


def rule_index(rule: dict, index: int, layout: str) -> int:
    row, col, serial = coordinates(index, layout)
    if layout in ("Linear", "Matrix"):
        return rule["origin"] + serial * rule["linear_step"]
    return rule["origin"] + row * rule["row_step"] + col * rule["col_step"]


def value(rule: dict, index: int, layout: str):
    sequence = rule["values"]
    raw = rule_index(rule, index, layout)
    if rule.get("wrap", True):
        return sequence[raw % len(sequence)]
    if not 0 <= raw < len(sequence):
        raise ValueError("Progression exceeds its bounded domain")
    return sequence[raw]


def object_at(rules: list[dict], index: int, layout: str, layer: str) -> dict:
    obj = deepcopy(BASE_OBJECT)
    obj["layer"] = layer
    if layer == "inner":
        obj.update(shape="chevron", size=0.90, position=7, fill="solid", foreground="inner")
    base_rule = next((rule for rule in rules if rule["layer"] == layer and "base_shape" in rule), None)
    if base_rule:
        obj["shape"] = base_rule["base_shape"]
    if any(rule["layer"] == layer and rule.get("attribute") == "sides" for rule in rules):
        obj["shape"] = "polygon"
    elif any(rule["layer"] == layer and rule.get("attribute") == "mirror" for rule in rules) and not any(
            rule["layer"] == layer and rule.get("attribute") == "shape" for rule in rules):
        mirror_rule = next(rule for rule in rules if rule["layer"] == layer and rule["attribute"] == "mirror")
        obj["shape"] = "crescent" if "vertical" in mirror_rule["values"] else "arrow"
    for rule in rules:
        if rule["layer"] == layer:
            obj[rule["attribute"]] = value(rule, index, layout)
    obj["scale"] = obj["size"]
    if obj["shape"] == "polygon":
        obj["shape"] = {3: "triangle", 4: "square", 5: "pentagon", 6: "hexagon", 7: "heptagon", 8: "octagon"}[obj["sides"]]
    return obj


def set_components(rule: dict, index: int, layout: str) -> list[int]:
    """Evaluate a set operation across each matrix row or column."""
    row, col, _ = coordinates(index, layout)
    band = row if rule["direction"] == "rows" else col
    place = col if rule["direction"] == "rows" else row
    a = set(rule["left"][band])
    b = set(rule["right"][band])
    if place == 0:
        return sorted(a)
    if place == 1:
        return sorted(b)
    operation = rule["operation"]
    if operation == "addition":
        return sorted(rule["left"][band] + rule["right"][band])
    if operation == "union":
        return sorted(a | b)
    if operation == "intersection":
        return sorted(a & b)
    if operation == "xor":
        return sorted(a ^ b)
    if operation == "subtraction":
        return sorted(a - b)
    if operation == "symmetry_completion":
        reflection = {0: 1, 1: 0, 2: 3, 3: 2, 4: 4, 5: 7, 6: 6, 7: 5}
        combined = a | b
        return sorted(combined | {reflection[item] for item in combined})
    if operation == "balance":
        return sorted({0, 1, 2, 3} - (a | b))
    raise ValueError(operation)


def cell_at(rules: list[dict], index: int, layout: str) -> dict:
    layers = sorted({rule["layer"] for rule in rules if rule["layer"] != "components"} | {"primary"},
                    key=lambda name: (name != "primary", name))
    state = {"objects": [object_at(rules, index, layout, layer) for layer in layers],
             "components": [], "background": "white",
             "foreground_mode": any(rule.get("attribute") == "foreground" for rule in rules)}
    if len(state["objects"]) > 1:
        primary = state["objects"][0]
        if not any(rule.get("layer") == "primary" and rule.get("attribute") == "position" for rule in rules):
            primary["position"] = 1
    for rule in rules:
        if rule["layer"] == "components":
            state["components"] = set_components(rule, index, layout)
    return state


def signature(state: dict) -> tuple:
    """Canonical visible state, ignoring attributes masked by the SVG artwork."""
    visible_state = deepcopy(state)
    if visible_state.get("foreground_mode"):
        front = next((obj["foreground"] for obj in visible_state["objects"]
                      if obj["layer"] == "primary"), "outer")
        for obj in visible_state["objects"]:
            obj["fill"] = "solid" if (obj["layer"] == "primary") == (front == "outer") else "outline"
            obj["texture"] = "plain"
    def visible_object(obj):
        result = dict(obj)
        result.pop("sides", None)  # the rendered shape already encodes polygon sides
        result.pop("size", None)   # only scale controls rendered size
        if result["texture"] != "plain":
            result["fill"] = result["texture"]
        angle = result.pop("rotation") + {"up": 0, "right": 90,
                                          "down": 180, "left": 270}[result.pop("orientation")]
        polygon_sides = {"triangle": 3, "square": 4, "pentagon": 5,
                         "hexagon": 6, "heptagon": 7, "octagon": 8}
        if (not result["internal_lines"] and
                result["symmetry"] == "none" and result["containment"] == "none" and
                result["texture"] == "plain" and result["fill"] not in ("hatched", "dotted")):
            shape = result["shape"]
            if shape in polygon_sides:
                n = polygon_sides[shape]
                phase = -45 if shape == "square" else -90
                points = [(math.cos(math.radians(phase+360*i/n)),
                           math.sin(math.radians(phase+360*i/n))) for i in range(n)]
            elif shape == "arrow":
                points = [(0,-19),(16,-2),(7,-2),(7,17),(-7,17),(-7,-2),(-16,-2)]
            elif shape == "chevron":
                points = [(-17,-10),(0,8),(17,-10),(17,1),(0,18),(-17,1)]
            elif shape == "diamond":
                points = [(0,-17),(16,0),(0,17),(-16,0)]
            elif shape == "cross":
                points = [(-5,-17),(5,-17),(5,-5),(17,-5),(17,5),(5,5),
                          (5,17),(-5,17),(-5,5),(-17,5),(-17,-5),(-5,-5)]
            elif shape == "line":
                points = [(-16,-12),(16,12)]
            elif shape == "semicircle":
                points = [(-17+34*i/16, 9-17*math.sin(math.pi*i/16))
                          for i in range(17)]
            elif shape == "crescent":
                points = [(7,-17),(-4,-17),(-11,-11),(-14,0),(-11,11),(-4,17),
                          (7,17),(0,11),(-3,0),(0,-11)]
            elif shape in ("circle", "dot", "ellipse", "star"):
                n = 10 if shape == "star" else 16
                points = []
                for i in range(n):
                    direction = math.radians(-90+360*i/n)
                    radius = (1 if i % 2 == 0 else 8/17) if shape == "star" else 1
                    ry = 11/17 if shape == "ellipse" else 1
                    points.append((radius*math.cos(direction), radius*ry*math.sin(direction)))
            else:
                points = None
            vertices = []
            for x, y in points or ():
                if result["mirror"] == "vertical":
                    x = -x
                elif result["mirror"] == "horizontal":
                    y = -y
                elif result["mirror"] == "diagonal":
                    x, y = y, x
                turn = math.radians(angle)
                vertices.append((round(x*math.cos(turn)-y*math.sin(turn), 5),
                                 round(x*math.sin(turn)+y*math.cos(turn), 5)))
            if points is not None:
                result.pop("mirror")
                result["outline_vertices"] = tuple(sorted(vertices))
                if result["count"] > 1:
                    result.pop("position")  # count is placed at fixed grid anchors
                return tuple(sorted(result.items()))
        symmetry_period = {"triangle": 120, "square": 90, "pentagon": 72,
                           "hexagon": 60, "heptagon": 360/7, "octagon": 45,
                           "circle": 1, "dot": 1, "star": 72, "cross": 90,
                           "ellipse": 180, "diamond": 180, "line": 180}
        if (result["internal_lines"] or result["symmetry"] != "none" or
                result["containment"] != "none" or result["texture"] == "hatch"):
            period = 360
        else:
            period = symmetry_period.get(result["shape"], 360)
        result["angle"] = round(angle % period, 6)
        if result["count"] > 1:
            result.pop("position")
        return tuple(sorted(result.items()))
    return (tuple(visible_object(obj) for obj in visible_state["objects"]),
            tuple(visible_state["components"]), visible_state["background"], visible_state.get("foreground_mode", False))


def choice_group(state: dict) -> tuple:
    """Group options that differ only in small markings or outline details."""
    simplified = deepcopy(state)
    for obj in simplified["objects"]:
        if obj["texture"] != "plain" or obj["fill"] in ("hatched", "dotted"):
            obj["fill"] = "outline"
        obj.update(border="smooth", internal_lines=0, nesting=0,
                   containment="none", symmetry="none", texture="plain")
    return signature(simplified)


def describe(rule: dict) -> str:
    if rule["layer"] == "components":
        band = "row" if rule["direction"] == "rows" else "column"
        action = {"addition": "combined components, retaining repeated dots",
                  "symmetry_completion": "the vertical mirror completion of the first two dot sets",
                  "balance": "the corner dots needed to complete a set of four"}.get(
                      rule["operation"], f"{rule['operation']} of the first two dot sets")
        return f"In each {band}, the third cell shows the {action}"
    if rule["family"] == "swap":
        return "the two figures swap left and right positions in each row"
    if rule["family"] == "foreground_background":
        return "the filled foreground alternates between the two figures"
    attr = rule["attribute"].replace("_", " ")
    if rule["direction"] == "both" and rule["row_step"] != rule["col_step"]:
        return (f"the {rule['layer']} {attr} advances {rule['col_step']:+d} across rows "
                f"and {rule['row_step']:+d} down columns")
    if rule["family"] == "progression":
        step = (rule["linear_step"] if rule["direction"] in ("linear", "serial") else
                rule["col_step"] or rule["row_step"])
        action = "increases" if step > 0 else "decreases"
        return f"the {rule['layer']} {attr} {action} by a fixed step"
    if rule["family"] == "alternation":
        return f"the {rule['layer']} {attr} alternates"
    if rule["family"] == "add_remove":
        return f"the number of {rule['layer']} figures repeatedly grows and shrinks"
    if rule["family"] == "distribution":
        direction = "in reading order" if rule["direction"] == "serial" else "once per row or column"
        return f"the {rule['layer']} {attr} cycles through each value {direction}"
    if rule["family"] == "movement":
        return f"the {rule['layer']} figure moves along a fixed path"
    if rule["family"] == "rotation":
        return f"the {rule['layer']} figure rotates by a fixed angle"
    if rule["family"] == "reflection":
        return f"the {rule['layer']} figure alternates between reflected and unreflected"
    return f"the {rule['layer']} {attr} follows a repeating cycle"
