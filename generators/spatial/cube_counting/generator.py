"""Normalized Cube Counting questions."""

from __future__ import annotations

import random

from generators.spatial.misc.geometry import choose_structure_palette

from .distractors import counts
from .model import fill_behind, grow, views
from .render import question_figures
from .validation import possible_counts, validate_choices


def generate_question(type_id, subtype, difficulty, choice_count, number, selected_theme="Mixed"):
    rng = random.Random()
    mode = rng.choice(("isometric", "three-view"))
    palette = choose_structure_palette(rng) if mode == "isometric" else None
    for attempt in range(350):
        scaffold = grow(rng, difficulty)
        voxels = fill_behind(scaffold) if mode == "isometric" else scaffold
        observed = views(voxels)
        if mode == "three-view":
            feasible, solutions = possible_counts(observed)
            if feasible != {len(voxels)} or (solutions > 1 and attempt < 250):
                continue
        else:
            solutions = None
        values = counts(rng, voxels, choice_count, difficulty)
        choices = [{"id": f"choice-{i+1}", "text": str(value), "figures": []}
                   for i, value in enumerate(values)]
        if validate_choices(choices, len(voxels)):
            break
    else:
        raise RuntimeError("Could not generate uniquely countable cube structure")
    return {
        "id": f"{subtype['id']}-{number}", "reasoning_type": type_id,
        "subtype": subtype["id"], "difficulty": difficulty,
        "text": ("How many unit cubes make up this solid pile? Cubes behind visible faces are filled."
                 if mode == "isometric" else "How many unit cubes make up this structure?"),
        "figures": question_figures(voxels, mode, palette), "choices": choices,
        "correct_answer_id": next(c["id"] for c in choices if int(c["text"]) == len(voxels)),
        "explanation": f"The structure contains {len(voxels)} occupied unit-cube positions.",
        "metadata": {"generator_key": subtype["generator_key"], "mode": mode,
                     "structure_palette": palette,
                     "voxels": sorted(voxels), "growth_scaffold": sorted(scaffold),
                     "rear_filled": mode == "isometric",
                     "projections": {k: sorted(v) for k, v in observed.items()},
                     "feasible_arrangements_checked": solutions, "answer_count": len(voxels),
                     "option_counts": values},
    }
