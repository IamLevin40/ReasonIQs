"""Projection constraint search over all supported column heights."""

from __future__ import annotations

from generators.spatial.cube_counting.model import views
from generators.spatial.misc.geometry import supported


def possible_counts(observed, stop_after=2):
    """Enumerate feasible supported solids and stop after count ambiguity appears."""
    top = sorted(observed["Top"])
    if not top:
        return set(), 0
    front_height = {x: max(z for xx, z in observed["Front"] if xx == x) + 1 for x, _ in top}
    left_height = {y: max(z for yy, z in observed["Left"] if yy == y) + 1 for _, y in top}
    heights = {}
    counts = set()
    solutions = 0

    def search(index):
        nonlocal solutions
        if len(counts) >= stop_after:
            return
        if index == len(top):
            solid = {(x, y, z) for (x, y), h in heights.items() for z in range(h)}
            if supported(solid) and views(solid) == observed:
                counts.add(len(solid))
                solutions += 1
            return
        x, y = top[index]
        for height in range(1, min(front_height[x], left_height[y]) + 1):
            heights[(x, y)] = height
            search(index + 1)
            if len(counts) >= stop_after:
                break
        heights.pop((x, y), None)

    search(0)
    return counts, solutions


def validate_choices(choices, true_count):
    values = [int(choice["text"]) for choice in choices]
    return len(values) == len(set(values)) and values.count(true_count) == 1 and min(values) > 0
