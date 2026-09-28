"""Three-dimensional solids with explicit vertices and planar faces."""

from __future__ import annotations

from generators.spatial.cube_counting.model import grow


def cube(x, y, z):
    v = [(x+a,y+b,z+c) for a,b,c in ((0,0,0),(1,0,0),(1,1,0),(0,1,0),
                                      (0,0,1),(1,0,1),(1,1,1),(0,1,1))]
    faces = [(0,1,2,3), (4,5,6,7), (0,1,5,4), (1,2,6,5),
             (2,3,7,6), (3,0,4,7)]
    return {"kind":"cube", "origin":[x,y,z], "vertices":v, "faces":faces}


def prism(x, y, z, high_at_positive_x=True, axis="x"):
    """Unit triangular prism: triangle on axis/z, extruded along the other axis."""
    if high_at_positive_x:
        triangle = ((0,0),(1,0),(1,1))
    else:
        triangle = ((0,0),(1,0),(0,1))
    if axis == "x":
        v = [(x+a,y+b,z+c) for b in (0,1) for a,c in triangle]
    elif axis == "y":
        v = [(x+b,y+a,z+c) for b in (0,1) for a,c in triangle]
    else:
        raise ValueError("Prism axis must be x or y")
    faces = [(0,2,1), (3,4,5), (0,1,4,3), (1,2,5,4), (2,0,3,5)]
    return {"kind":"triangular-prism", "origin":[x,y,z],
            "vertices":v, "faces":faces, "high_at_positive_x":high_at_positive_x,
            "slope_axis":axis}


def build(rng, difficulty):
    voxels = grow(rng, difficulty)
    shapes = [cube(*cell) for cell in sorted(voxels)]
    if difficulty != "Easy":
        # A cap above a tallest cube is wholly outside the cube volume.
        top = max(z for _, _, z in voxels)
        tallest = [cell for cell in sorted(voxels) if cell[2] == top]
        max_x = max(x for x, _, _ in voxels)
        max_y = max(y for _, y, _ in voxels)
        boundary = [cell for cell in tallest if cell[0] in (0, max_x) or cell[1] in (0, max_y)]
        x, y, z = rng.choice(boundary or tallest)
        axes = ("x", "y") if difficulty == "Challenge" else ("x",)
        axis = rng.choice(axes)
        high_positive = (x == max_x) if axis == "x" else (y == max_y)
        shapes.append(prism(x, y, z + 1, high_positive, axis))
    return shapes
