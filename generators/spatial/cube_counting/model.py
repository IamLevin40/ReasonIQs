"""Grow supported, connected structures on an integer lattice."""

from __future__ import annotations

from generators.spatial.misc.geometry import supported

SIZES = {"Easy": (3, 3, 2, 5, 8), "Average": (4, 3, 3, 8, 13),
         "Challenge": (4, 4, 4, 12, 20)}


def grow(rng, difficulty):
    width, depth, limit, low, high = SIZES[difficulty]
    target = rng.randint(low, high)
    voxels = {(0, 0, 0)}
    while len(voxels) < target:
        candidates = set()
        for x, y, z in voxels:
            # The rear origin is fixed. Ground expansion moves toward the
            # positive-x/positive-y camera, never backward behind the start.
            for dx, dy in ((1, 0), (0, 1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < depth and (nx, ny, 0) not in voxels:
                    candidates.add((nx, ny, 0))
            if z + 1 < limit and (x, y, z + 1) not in voxels:
                candidates.add((x, y, z + 1))
        if not candidates:
            break
        # Height growth makes towers; ground growth makes branches and bridges.
        choices = sorted(candidates)
        weights = [3 if p[2] == 0 else (2 if difficulty != "Easy" else 1) for p in choices]
        voxels.add(rng.choices(choices, weights)[0])
    if not supported(voxels):
        raise AssertionError("Voxel growth lost support")
    return voxels


def fill_behind(voxels):
    """Complete every rear x/y column implied by the camera-facing pile.

    The camera is in the positive x/y/z octant. A cube at (x,y,z) therefore
    implies a solid block of occupied rear coordinates from the origin through
    (x,y) at that level. Ground support is included at every filled position.
    """
    source = set(map(tuple, voxels))
    if (0, 0, 0) not in source:
        raise ValueError("The pile must start at the rear origin")
    solid = {(back_x, back_y, level)
             for x, y, z in source
             for back_x in range(x + 1)
             for back_y in range(y + 1)
             for level in range(z + 1)}
    if not supported(solid):
        raise AssertionError("Rear fill lost connectivity or support")
    return solid


def views(voxels):
    top = {(x, y) for x, y, _ in voxels}
    front = {(x, z) for x, _, z in voxels}
    left = {(y, z) for _, y, z in voxels}
    return {"Top": top, "Front": front, "Left": left}
