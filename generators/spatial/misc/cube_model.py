"""Exact cube-net geometry and oriented face identities shared by both subtypes."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import product
import random

Vec = tuple[int, int, int]
Point = tuple[int, int]
X: Vec = (1, 0, 0)
Y: Vec = (0, 1, 0)
Z: Vec = (0, 0, 1)
NORMALS = {"R": X, "L": (-1, 0, 0), "U": Y, "D": (0, -1, 0), "F": Z, "B": (0, 0, -1)}
IDS = {value: key for key, value in NORMALS.items()}
OPPOSITES = (("U", "D"), ("F", "B"), ("L", "R"))
STEPS = {(1, 0): "east", (-1, 0): "west", (0, -1): "north", (0, 1): "south"}


def neg(a: Vec) -> Vec:
    return (-a[0], -a[1], -a[2])


def cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


@dataclass(frozen=True)
class Basis:
    normal: Vec
    up: Vec
    right: Vec

    def across(self, direction: str) -> "Basis":
        n, u, r = self.normal, self.up, self.right
        if direction == "east":
            return Basis(r, u, neg(n))
        if direction == "west":
            return Basis(neg(r), u, n)
        if direction == "north":
            return Basis(u, neg(n), r)
        return Basis(neg(u), n, r)


ROOT = Basis(Z, Y, X)


def normalize(cells: set[Point] | tuple[Point, ...]) -> tuple[Point, ...]:
    x0 = min(x for x, _ in cells)
    y0 = min(y for _, y in cells)
    return tuple(sorted((x - x0, y - y0) for x, y in cells))


def planar_transform(cells, quarter_turns: int = 0, reflect: bool = False) -> tuple[Point, ...]:
    result = []
    for x, y in cells:
        if reflect:
            x = -x
        for _ in range(quarter_turns % 4):
            x, y = -y, x
        result.append((x, y))
    return normalize(result)


def canonical(cells) -> tuple[Point, ...]:
    return min(planar_transform(cells, turns, flip) for turns, flip in product(range(4), (False, True)))


def fold_net(cells, root: Basis = ROOT) -> dict[Point, Basis] | None:
    """Traverse shared edges in 3D; reject disconnected, overlapping or contradictory nets."""
    squares = set(cells)
    if len(squares) != 6:
        return None
    first = min(squares)
    placed = {first: root}
    queue = deque([first])
    while queue:
        x, y = queue.popleft()
        for (dx, dy), direction in STEPS.items():
            neighbor = (x + dx, y + dy)
            if neighbor not in squares:
                continue
            expected = placed[(x, y)].across(direction)
            if neighbor in placed:
                if placed[neighbor] != expected:
                    return None
            else:
                placed[neighbor] = expected
                queue.append(neighbor)
    if len(placed) != 6 or {basis.normal for basis in placed.values()} != set(NORMALS.values()):
        return None
    return placed


def all_cube_nets() -> tuple[tuple[Point, ...], ...]:
    """Enumerate free hexominoes and keep the complete family of eleven cube nets."""
    shapes = {((0, 0),)}
    for _ in range(5):
        expanded = set()
        for shape in shapes:
            occupied = set(shape)
            for x, y in shape:
                for dx, dy in STEPS:
                    point = (x + dx, y + dy)
                    if point not in occupied:
                        expanded.add(canonical(occupied | {point}))
        shapes = expanded
    nets = tuple(sorted(shape for shape in shapes if fold_net(shape) is not None))
    if len(nets) != 11:
        raise AssertionError(f"Expected eleven cube-net topologies, found {len(nets)}")
    return nets


NETS = all_cube_nets()


def random_net(rng: random.Random, difficulty: str = "Average") -> tuple[Point, ...]:
    pool = NETS
    if difficulty == "Easy":
        pool = tuple(net for net in NETS if max(x for x, _ in net) - min(x for x, _ in net) <= 3)
    elif difficulty == "Challenge":
        pool = tuple(net for net in NETS if max(x for x, _ in net) - min(x for x, _ in net) >= 3)
    return planar_transform(rng.choice(pool), rng.randrange(4), rng.choice((False, True)))


def rotations() -> tuple[tuple[Vec, Vec, Vec], ...]:
    result = []
    for ex, ey in product(NORMALS.values(), repeat=2):
        ez = cross(ex, ey)
        if ez in NORMALS.values():
            result.append((ex, ey, ez))
    return tuple(result)


ROTATIONS = rotations()


def rotate(v: Vec, rotation: tuple[Vec, Vec, Vec]) -> Vec:
    return tuple(sum(v[i] * rotation[i][j] for i in range(3)) for j in range(3))  # type: ignore[return-value]


def turn_up(up: Vec, normal: Vec, turns: int) -> Vec:
    for _ in range(turns % 4):
        up = cross(up, normal)
    return up


def quarter_turns(up: Vec, basis: Basis) -> int:
    for turns in range(4):
        if turn_up(basis.up, basis.normal, turns) == up:
            return turns
    raise ValueError("Marking direction is outside its face plane")


def canonical_basis(normal: Vec) -> Basis:
    for rotation in ROTATIONS:
        if rotate(Z, rotation) == normal:
            return Basis(normal, rotate(Y, rotation), rotate(X, rotation))
    raise ValueError(normal)


def relocate_face(face: "Face", old_normal: Vec, new_normal: Vec) -> "Face":
    """Move a marking to another face plane without inventing a tilt."""
    turns = quarter_turns(face.mark_up, canonical_basis(old_normal))
    basis = canonical_basis(new_normal)
    return Face(face.identity, turn_up(basis.up, new_normal, turns), face.mirrored)


@dataclass(frozen=True)
class Face:
    identity: str
    mark_up: Vec
    mirrored: bool = False


Cube = dict[Vec, Face]


def source_cube(rng: random.Random, difficulty: str) -> Cube:
    cube = {}
    for identity, normal in NORMALS.items():
        basis = canonical_basis(normal)
        turns = rng.randrange(4) if difficulty != "Easy" else rng.randrange(2)
        cube[normal] = Face(identity, turn_up(basis.up, normal, turns))
    return cube


def rotate_cube(cube: Cube, rotation: tuple[Vec, Vec, Vec]) -> Cube:
    return {rotate(normal, rotation): Face(face.identity, rotate(face.mark_up, rotation), face.mirrored)
            for normal, face in cube.items()}


def same_cube(source: Cube, candidate: Cube, symmetric: dict[str, int] | None = None) -> tuple[int, Cube] | None:
    """Return a proving rigid rotation, comparing all faces and mark directions."""
    symmetric = symmetric or {}
    for index, rotation in enumerate(ROTATIONS):
        turned = rotate_cube(source, rotation)
        if all(
            candidate[n].identity == turned[n].identity
            and candidate[n].mirrored == turned[n].mirrored
            and any(candidate[n].mark_up == turn_up(turned[n].mark_up, n, t)
                    for t in range(0, 4, 4 // symmetric.get(turned[n].identity, 1)))
            for n in NORMALS.values()
        ):
            return index, turned
    return None


def net_cube(cells, faces_by_cell: dict[Point, Face]) -> Cube | None:
    folded = fold_net(cells)
    if folded is None or set(faces_by_cell) != set(cells):
        return None
    return {basis.normal: faces_by_cell[cell] for cell, basis in folded.items()}


def net_faces(cells, cube: Cube) -> dict[Point, Face]:
    folded = fold_net(cells)
    if folded is None:
        raise ValueError("Invalid cube net")
    return {cell: cube[basis.normal] for cell, basis in folded.items()}


def observation_matches(question_views: list[Cube], candidate: Cube, symmetric: dict[str, int] | None = None) -> bool:
    """Each shown three-face view must be possible from one candidate cube."""
    symmetric = symmetric or {}
    visible = (X, Y, Z)
    for view in question_views:
        if not any(all(
            rotated[n].identity == view[n].identity
            and rotated[n].mirrored == view[n].mirrored
            and any(rotated[n].mark_up == turn_up(view[n].mark_up, n, t)
                    for t in range(0, 4, 4 // symmetric.get(view[n].identity, 1)))
            for n in visible
        ) for rotated in (rotate_cube(candidate, rotation) for rotation in ROTATIONS)):
            return False
    return True


def cube_snapshot(cube: Cube) -> dict[str, dict]:
    return {IDS[normal]: {"face_id": face.identity, "mark_up": face.mark_up,
                          "mirrored": face.mirrored} for normal, face in cube.items()}
