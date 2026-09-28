"""Normalized exact-fit Blocks Forming questions."""

from __future__ import annotations

import random

from generators.spatial.cube_counting.model import grow
from generators.spatial.misc.geometry import choose_structure_palette
from .distractors import candidate_sets
from .model import partition
from .render import piece_figures, target_figure
from .rotations import orientations
from .solver import fit


def generate_question(type_id, subtype, difficulty, choice_count, number, selected_theme="Mixed"):
    rng = random.Random()
    palette = choose_structure_palette(rng)
    for _ in range(100):
        scaffold = grow(rng, difficulty)
        result = partition(rng, scaffold, difficulty)
        if result is None:
            continue
        pieces, original_regions = result
        # The displayed local blocks receive independent proper rotations.
        pieces = [rng.choice(sorted(orientations(piece), key=lambda o: sorted(o))) for piece in pieces]
        # Their saved placements, rather than the scaffold, define the final solid.
        target = set().union(*original_regions)
        solution = fit(target, pieces)
        if solution is None:
            continue
        try:
            options = candidate_sets(rng, target, pieces, choice_count)
        except RuntimeError:
            continue
        verdicts = [fit(target, option) for option in options]
        if sum(v is not None for v in verdicts) == 1:
            break
    else:
        raise RuntimeError("Could not generate validated block assembly")
    choices = [{"id": f"choice-{i+1}", "figures": piece_figures(option, palette)}
               for i, option in enumerate(options)]
    correct = next(i for i, proof in enumerate(verdicts) if proof is not None)
    return {
        "id": f"{subtype['id']}-{number}", "reasoning_type": type_id,
        "subtype": subtype["id"], "difficulty": difficulty,
        "text": "Which set of blocks can be rotated and assembled to make the target?",
        "figures": [target_figure(target, palette)], "choices": choices,
        "correct_answer_id": choices[correct]["id"],
        "explanation": "These blocks exactly fill the target with no gaps or overlaps.",
        "metadata": {"generator_key": subtype["generator_key"], "target_voxels": sorted(target),
                     "structure_palette": palette,
                     "original_partition": [sorted(region) for region in original_regions],
                     "options": [[sorted(piece) for piece in option] for option in options],
                     "solution": {str(i): sorted(cells) for i, cells in verdicts[correct].items()},
                     "allow_reflection": False},
    }
