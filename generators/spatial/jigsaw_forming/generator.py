"""Normalized square-picture Jigsaw Forming questions."""

from __future__ import annotations

import random

from .distractors import candidates
from .model import make_board, rotate_piece
from .render import choice_figure, detached_figures
from .solver import fit


def generate_question(type_id, subtype, difficulty, choice_count, number, selected_theme="Mixed"):
    rng=random.Random()
    for _ in range(100):
        target=make_board(rng,difficulty)
        detached=[rotate_piece(piece,rng.randrange(4)) for piece in target["tiles"]]
        rng.shuffle(detached)
        try:
            options,reasons=candidates(rng,target,detached,choice_count)
        except RuntimeError:
            continue
        verdicts=[fit(option,detached) for option in options]
        if sum(result is not None for result in verdicts)==1:
            break
    else:
        raise RuntimeError("Could not generate a uniquely formable square jigsaw")
    choices=[{"id":f"choice-{index+1}","figures":[choice_figure(option)]}
             for index,option in enumerate(options)]
    correct=next(index for index,result in enumerate(verdicts) if result is not None)
    return {
        "id":f"{subtype['id']}-{number}","reasoning_type":type_id,
        "subtype":subtype["id"],"difficulty":difficulty,
        "text":"Which completed square can be assembled from these jigsaw pieces? Rotate pieces by quarter turns; do not flip them.",
        "figures":detached_figures(detached),"choices":choices,
        "correct_answer_id":choices[correct]["id"],
        "explanation":"The tabs and notches interlock while the lines and polygons match these pieces exactly.",
        "metadata":{"generator_key":subtype["generator_key"],
                    "target_board":target,"detached_pieces":detached,
                    "options":options,"choice_mutations":reasons,
                    "solution":{str(slot):placement for slot,placement in verdicts[correct].items()},
                    "board_size":target["size"],"aspect_ratio":[1,1],
                    "allow_reflection":False,"allowed_rotations_degrees":[0,90,180,270]},
    }
