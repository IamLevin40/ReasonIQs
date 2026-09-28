"""Figure specifications derived solely from voxels."""

from generators.spatial.cube_counting.model import views
from generators.spatial.misc.geometry import grid_figure, isometric


def question_figures(voxels, mode, palette=None):
    if mode == "isometric":
        return [isometric(voxels, "Isometric cube structure", palette=palette)]
    observed = views(voxels)
    return [grid_figure(observed[label], f"{label} orthographic view", label)
            for label in ("Top", "Front", "Left")]
