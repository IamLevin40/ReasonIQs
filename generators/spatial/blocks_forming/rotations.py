"""The 24 proper cube rotations; reflections are deliberately excluded."""

from __future__ import annotations

from itertools import permutations, product

from generators.spatial.misc.geometry import normalize


def parity(order):
    return (-1) ** sum(order[i] > order[j] for i in range(3) for j in range(i+1, 3))


ROTATIONS = [(axes, signs) for axes in permutations(range(3)) for signs in product((-1, 1), repeat=3)
             if parity(axes) * signs[0] * signs[1] * signs[2] == 1]


def orientations(piece):
    return set(normalize(tuple(signs[i] * cell[axes[i]] for i in range(3)) for cell in piece)
               for axes, signs in ROTATIONS)
