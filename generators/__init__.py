"""Dispatch normalized ReasonIQs questions to procedural generators."""

from generators.misc.placeholder import generate_placeholder_session


def generate_session(type_id: str, subtype: dict, difficulty: str, item_count: int, choice_count: int,
                     theme: str = "Mixed") -> list[dict]:
    key = subtype["generator_key"]
    if key == "spatial.dice_folding":
        from generators.spatial.dice_folding.generator import generate_question
    elif key == "spatial.dice_unfolding":
        from generators.spatial.dice_unfolding.generator import generate_question
    elif key == "spatial.cube_counting":
        from generators.spatial.cube_counting.generator import generate_question
    elif key == "spatial.perspective_viewing":
        from generators.spatial.perspective_viewing.generator import generate_question
    elif key == "spatial.blocks_forming":
        from generators.spatial.blocks_forming.generator import generate_question
    elif key == "spatial.jigsaw_forming":
        from generators.spatial.jigsaw_forming.generator import generate_question
    else:
        return generate_placeholder_session(type_id, subtype, difficulty, item_count, choice_count)
    return [generate_question(type_id, subtype, difficulty, choice_count, index + 1, theme) for index in range(item_count)]
