"""Same-volume candidate block sets with altered topology."""

from __future__ import annotations

from generators.spatial.misc.geometry import connected, normalize
from .solver import fit


def mutate_piece(rng, piece):
    piece = set(piece)
    for _ in range(90):
        removed = rng.choice(sorted(piece))
        base = piece-{removed}
        if not connected(base):
            continue
        neighbors = set()
        for x, y, z in base:
            for dx, dy, dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
                neighbors.add((x+dx,y+dy,z+dz))
        alternatives = sorted(neighbors-piece)
        if alternatives:
            return normalize(base|{rng.choice(alternatives)})
    return None


def candidate_sets(rng, target, correct, count):
    options = [correct]
    seen = {tuple(sorted(tuple(sorted(piece)) for piece in correct))}
    attempts = 0
    while len(options) < count and attempts < 1500:
        attempts += 1
        source = rng.choice(options if rng.random() < .35 else [correct])
        candidate = list(source)
        index = rng.randrange(len(candidate))
        replacement = mutate_piece(rng, candidate[index])
        if replacement is None:
            continue
        candidate[index] = replacement
        key = tuple(sorted(tuple(sorted(piece)) for piece in candidate))
        if key in seen or fit(target, candidate) is not None:
            continue
        seen.add(key)
        options.append(candidate)
    if len(options) != count:
        raise RuntimeError("Could not generate enough non-fitting block sets")
    rng.shuffle(options)
    return options
