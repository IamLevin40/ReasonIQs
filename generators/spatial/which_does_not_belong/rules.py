"""Cell-centered, machine-readable odd-one-out classifications."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .model import equivalent_by_rotation


@dataclass(frozen=True)
class Rule:
    id: str
    family: str
    difficulty: str
    complexity: int
    explanation: str
    violation: str
    predicates: tuple[dict, ...]
    builder: str
    grid_size: int = 1


def _parts(figure, role=None):
    return [p for p in figure["components"] if role is None or p["role"] == role]


def _symbol(part):
    return part["shape"], part["sides"], part.get("variant", 0)


def _clockwise(figure):
    parts = _parts(figure)
    if len(parts) != 3 or any(p["x"] == p["y"] == 0 for p in parts):
        return None
    ordered = sorted(parts, key=lambda p: math.atan2(p["y"], p["x"]))
    return tuple(_symbol(p) for p in ordered)


def evaluate(predicate, figure, reference=None):
    """Read semantic geometry; renderer output never determines an answer."""
    op = predicate["op"]
    parts = _parts(figure)
    if op.startswith("grid_") and figure["grid"]["size"] != predicate["size"]:
        raise ValueError("Predicate grid mismatch")
    if op == "count":
        return len(parts) == predicate["value"]
    if op == "solid_count":
        return sum(p["fill"] == "solid" for p in parts) == predicate["value"]
    if op == "texture_count":
        return sum(p["texture"] == predicate["texture"] for p in parts) == predicate["value"]
    if op == "outer_parity":
        outer = _parts(figure, "outer")
        return len(outer) == 1 and outer[0]["shape"] == "polygon" and outer[0]["sides"] % 2 == 0
    if op == "side_relation":
        outer, inner = _parts(figure, "outer"), _parts(figure, "inner")
        return (len(outer) == len(inner) == 1 and
                outer[0]["sides"] == inner[0]["sides"] * predicate["multiplier"] + predicate["offset"])
    if op == "same_orientation":
        first, second = _parts(figure, "first"), _parts(figure, "second")
        return len(first) == len(second) == 1 and first[0]["angle"] == second[0]["angle"]
    if op == "closed":
        return all(p["shape"] not in ("arc", "line") for p in parts)
    if op == "straight":
        return all(p["shape"] in ("polygon", "concave", "star", "cross", "arrow",
                                   "chevron", "kite", "shield", "motif", "line") for p in parts)
    if op == "convex":
        return all(p["shape"] == "polygon" for p in parts)
    if op == "unique_types":
        return len({_symbol(p) for p in parts}) == len(parts)
    if op == "balanced_fill":
        return sum(p["fill"] == "solid" for p in parts) * 2 == len(parts)
    if op == "rotation_family":
        return equivalent_by_rotation(figure, reference)
    if op == "clockwise_order":
        actual, target = _clockwise(figure), _clockwise(reference)
        return (actual is not None and target is not None and
                any(actual == target[i:] + target[:i] for i in range(3)))
    if op == "nested_depth":
        rings = sorted((p["size"] for p in _parts(figure, "ring")), reverse=True)
        return len(rings) == predicate["value"] and all(a > b for a, b in zip(rings, rings[1:]))
    if op == "grid_permutation":
        cells = [p["cell"] for p in parts]
        return (len(parts) == 3 and len(set(cells)) == 3 and
                {cell // 3 for cell in cells} == {0, 1, 2} and
                {cell % 3 for cell in cells} == {0, 1, 2})
    if op == "grid_row_one_solid":
        return (len(parts) == 4 and {p["cell"] for p in parts} == {0, 1, 2, 3} and
                all(sum(p["fill"] == "solid" for p in parts if p["cell"] // 2 == row) == 1
                    for row in (0, 1)))
    if op == "grid_three_pairs":
        cells = {p["cell"] for p in parts}
        return (len(parts) == 6 and len(cells) == 3 and all(
            sorted(p["role"] for p in parts if p["cell"] == cell) == ["inner", "outer"]
            for cell in cells))
    if op == "grid_half_sides":
        cells = {p["cell"] for p in parts}
        return bool(cells) and all(
            len(outer := [p for p in parts if p["cell"] == cell and p["role"] == "outer"]) == 1 and
            len(inner := [p for p in parts if p["cell"] == cell and p["role"] == "inner"]) == 1 and
            outer[0]["sides"] == 2 * inner[0]["sides"] for cell in cells)
    if op == "grid_unique_sides":
        return len(parts) == 3 and all(p["shape"] == "polygon" for p in parts) and len(
            {p["sides"] for p in parts}) == 3
    raise ValueError(f"Unknown predicate: {op}")


def matches(rule, figure, reference=None):
    return figure["grid"]["size"] == rule.grid_size and all(
        evaluate(predicate, figure, reference) for predicate in rule.predicates)


RULES = (
    Rule("three_objects", "Property Exception", "Easy", 1,
         "The other figures each contain three symbols.", "A fourth symbol was added.",
         ({"op": "count", "value": 3},), "count_three", 2),
    Rule("even_outer_sides", "Quantity and Geometry", "Easy", 1,
         "The other polygons have an even number of sides.", "The polygon has an odd number of sides.",
         ({"op": "outer_parity"},), "even_sides", 1),
    Rule("one_solid", "Property Exception", "Easy", 1,
         "Exactly one symbol is solid in every other figure.", "A second symbol was filled.",
         ({"op": "solid_count", "value": 1},), "one_solid", 2),
    Rule("two_striped", "Property Exception", "Easy", 1,
         "Exactly two symbols are striped in every other figure.", "One stripe texture was removed.",
         ({"op": "texture_count", "texture": "striped", "value": 2},), "two_striped", 2),
    Rule("closed_contours", "Topology and Connectivity", "Easy", 1,
         "The other outlines are closed.", "The outline was opened.",
         ({"op": "closed"},), "closed", 1),
    Rule("straight_boundaries", "Quantity and Geometry", "Easy", 1,
         "The other figures use straight boundaries.", "A curved boundary was introduced.",
         ({"op": "straight"},), "straight", 1),
    Rule("grid_three_cells", "Property Exception", "Easy", 1,
         "The other figures each contain three symbols.", "A fourth symbol was added.",
         ({"op": "count", "value": 3},), "count_three_grid", 3),
    Rule("convex_outline", "Quantity and Geometry", "Average", 2,
         "The other outlines are convex.", "One corner was pushed inward.",
         ({"op": "convex"},), "convex", 1),
    Rule("matching_directions", "Relational Composition", "Average", 2,
         "The two symbols face the same way in every other figure.", "One symbol was turned.",
         ({"op": "same_orientation"},), "directions", 2),
    Rule("half_sides", "Relational Composition", "Average", 2,
         "The inner polygon has half the outer polygon's sides in every other figure.",
         "A side was added to the inner polygon.",
         ({"op": "side_relation", "multiplier": 2, "offset": 0},), "half_sides", 1),
    Rule("unique_shapes", "Property Exception", "Average", 2,
         "Every symbol has a different shape in the other figures.", "One shape was repeated.",
         ({"op": "unique_types"},), "unique", 2),
    Rule("grid_one_per_row_column", "Relational Composition", "Average", 2,
         "The other figures have one symbol in each row and column.",
         "A symbol moved into an occupied column.",
         ({"op": "grid_permutation", "size": 3},), "permutation", 3),
    Rule("grid_row_fill", "Relational Composition", "Average", 2,
         "Each row has one solid symbol in the other figures.",
         "Both solid symbols ended up in one row.",
         ({"op": "grid_row_one_solid", "size": 2},), "row_fill", 2),
    Rule("one_less_side", "Relational Composition", "Challenge", 3,
         "The inner polygon has one fewer side than the outer polygon in every other figure.",
         "The inner polygon gained a side.",
         ({"op": "side_relation", "multiplier": 1, "offset": 1},), "one_less", 1),
    Rule("balanced_shading", "Relational Composition", "Challenge", 3,
         "The other figures have equal numbers of solid and unshaded symbols.",
         "One unshaded symbol was filled.",
         ({"op": "balanced_fill"},), "balanced", 2),
    Rule("rotation_not_reflection", "Transformation Family", "Challenge", 4,
         "The other structures are rotations of the same shape; this one is its mirror image.",
         "The structure was reflected instead of rotated.",
         ({"op": "rotation_family"},), "reflection", 1),
    Rule("clockwise_order", "Transformation Family", "Challenge", 4,
         "The three different symbols appear in the same clockwise order in the other figures.",
         "Two symbols exchanged positions, reversing their order.",
         ({"op": "clockwise_order"},), "clockwise", 3),
    Rule("nested_three", "Topology and Connectivity", "Challenge", 3,
         "The other figures have three nested outlines.", "An enclosing outline was removed.",
         ({"op": "nested_depth", "value": 3},), "nested", 1),
    Rule("grid_three_nested_ratios", "Compound Classification", "Challenge", 4,
         "Three cells each hold an inner polygon with half as many sides as its outer polygon.",
         "One inner polygon gained a side.",
         ({"op": "grid_three_pairs", "size": 2}, {"op": "grid_half_sides", "size": 2}),
         "pairs", 2),
    Rule("grid_three_unique_sides", "Compound Classification", "Challenge", 4,
         "Each row and column has one polygon, and all three side counts differ.",
         "One polygon gained a side, repeating another side count.",
         ({"op": "grid_permutation", "size": 3}, {"op": "grid_unique_sides", "size": 3}),
         "unique_sides", 3),
)


def build(rule, rng, choice_count):
    from .grid_rules import build_grid

    return build_grid(rule, rng, choice_count)
