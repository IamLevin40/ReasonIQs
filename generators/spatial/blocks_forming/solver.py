"""Exact non-overlapping polycube tiling solver."""

from __future__ import annotations

from .rotations import orientations


def fit(target, pieces):
    target = frozenset(map(tuple, target))
    pieces = [frozenset(map(tuple, piece)) for piece in pieces]
    if sum(map(len, pieces)) != len(target) or not target or any(not piece for piece in pieces):
        return None
    placements = []
    for piece in pieces:
        found = set()
        for orientation in orientations(piece):
            anchor = next(iter(orientation))
            for cell in target:
                offset = tuple(cell[i] - anchor[i] for i in range(3))
                placed = frozenset(tuple(p[i] + offset[i] for i in range(3)) for p in orientation)
                if placed <= target:
                    found.add(placed)
        if not found:
            return None
        placements.append(sorted(found, key=lambda p: sorted(p)))
    by_cell = [{cell: [p for p in options if cell in p] for cell in target} for options in placements]

    def search(remaining, unused, solution):
        if not remaining:
            return solution if not unused else None
        best = None
        for cell in remaining:
            candidates = [(index, placement) for index in unused
                          for placement in by_cell[index][cell] if placement <= remaining]
            if not candidates:
                return None
            if best is None or len(candidates) < len(best):
                best = candidates
        for index, placement in best:
            result = search(remaining-placement, unused-{index}, {**solution, index: placement})
            if result is not None:
                return result
        return None

    return search(target, set(range(len(pieces))), {})
