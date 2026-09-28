"""Controlled wrong views, reversals, rotations, and added/omitted regions."""

from __future__ import annotations

from .projection import polygons, signature, transform


def options(rng, shapes, target_view, count):
    correct = polygons(shapes, target_view)
    candidates = [correct]
    for other in (view for view in ("Top","Front","Left") if view != target_view):
        candidates.append(polygons(shapes, other))
    for operation in ("mirror", "rotate", "flip"):
        candidates.append(transform(correct, operation))
    # Occupancy errors are full unit projected polygons, not image edits.
    vertices = [p for poly in correct for p in poly["vertices"]]
    left, right = min(x for x,_ in vertices), max(x for x,_ in vertices)
    low, high = min(y for _,y in vertices), max(y for _,y in vertices)
    for x,y in ((left-1,low),(right,low),(left,high-1),(right-1,high)):
        extra = {"vertices": ((x,y),(x+1,y),(x+1,y+1),(x,y+1)),
                 "world_vertices": [], "depth": 999, "solid_kind": "added-region"}
        candidates.append([*correct, extra])
    for i in range(len(correct)-1,-1,-1):
        if correct[i]["solid_kind"] == "triangular-prism":
            candidates.append(correct[:i]+correct[i+1:])
            break
    seen = set()
    distinct = []
    for candidate in candidates:
        key = signature(candidate)
        if key and key not in seen:
            seen.add(key)
            distinct.append(candidate)
    if len(distinct) < count:
        raise RuntimeError("Insufficient distinct perspective options")
    wrong = distinct[1:]
    rng.shuffle(wrong)
    result = [distinct[0], *wrong[:count-1]]
    rng.shuffle(result)
    return result, signature(correct)
