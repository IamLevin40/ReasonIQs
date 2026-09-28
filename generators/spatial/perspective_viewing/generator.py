"""Normalized world-fixed Perspective Viewing questions."""

from __future__ import annotations

import random

from generators.spatial.misc.geometry import choose_structure_palette

from .distractors import options
from .model import build
from .projection import raycast_signature, signature
from .render import source_figure, view_figure


def generate_question(type_id, subtype, difficulty, choice_count, number, selected_theme="Mixed"):
    rng=random.Random()
    palette=choose_structure_palette(rng)
    for _ in range(150):
        shapes=build(rng,difficulty)
        requested=rng.choice(("Top","Front","Left"))
        try:
            candidates,correct_signature=options(rng,shapes,requested,choice_count)
        except RuntimeError:
            continue
        volume_signature=raycast_signature(shapes,requested)
        if correct_signature != volume_signature:
            continue
        matches=[signature(candidate)==correct_signature for candidate in candidates]
        if sum(matches)==1:
            break
    else:
        raise RuntimeError("Could not generate distinct orthographic views")
    choices=[{"id":f"choice-{i+1}","figures":[view_figure(candidate)]}
             for i,candidate in enumerate(candidates)]
    correct=matches.index(True)
    return {"id":f"{subtype['id']}-{number}","reasoning_type":type_id,
            "subtype":subtype["id"],"difficulty":difficulty,
            "text":f"Which option shows the {requested.lower()} view of the object?",
            "figures":[source_figure(shapes,requested,palette)],"choices":choices,
            "correct_answer_id":choices[correct]["id"],
            "explanation":f"Looking from the fixed {requested.lower()} direction gives this outline.",
            "metadata":{"generator_key":subtype["generator_key"],"requested_view":requested,
                        "structure_palette":palette,
                        "solids":shapes,"choice_polygons":candidates,
                        "projection_signature":sorted(correct_signature),
                        "volume_projection_signature":sorted(volume_signature),
                        "screen_axes":{"Top":"right=-x, down=+y",
                                       "Front":"right=-x, down=-z",
                                       "Left":"right=+y, down=-z"},
                        "view_axes":{"Front":"+y","Left":"+x","Top":"+z"}}}
