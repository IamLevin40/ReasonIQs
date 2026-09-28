"""Build a supported target, then partition it into connected blocks."""

from __future__ import annotations

from generators.spatial.misc.geometry import connected, normalize

PIECES = {"Easy": 2, "Average": 3, "Challenge": 4}


def partition(rng, target, difficulty):
    count = PIECES[difficulty]
    if len(target) < count * 2:
        return None
    seeds = rng.sample(sorted(target), count)
    regions = [{seed} for seed in seeds]
    remaining = set(target)-set(seeds)
    while remaining:
        options = []
        for index, region in enumerate(regions):
            for x, y, z in region:
                for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                    cell = (x+dx, y+dy, z+dz)
                    if cell in remaining:
                        options.append((index, cell))
        if not options:
            return None
        # Favor small regions so the answer cannot be inferred from one large piece.
        options.sort(key=lambda item: (len(regions[item[0]]), rng.random()))
        index, cell = options[0]
        regions[index].add(cell)
        remaining.remove(cell)
    if any(len(region) < 2 or not connected(region) for region in regions):
        return None
    return [normalize(region) for region in regions], regions
