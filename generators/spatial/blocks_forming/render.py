"""Target and separated candidate polycube figure specifications."""

from generators.spatial.misc.geometry import isometric


def target_figure(target, palette):
    return isometric(target, "Assembled target structure", palette=palette)


def piece_figures(pieces, palette):
    return [isometric(piece, f"Block {i+1} of {len(pieces)}", f"Block {i+1}", palette=palette)
            for i, piece in enumerate(pieces)]
