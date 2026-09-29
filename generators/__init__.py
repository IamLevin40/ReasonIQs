"""Dispatch normalized ReasonIQs questions to procedural generators."""

import random

from generators.misc.placeholder import generate_placeholder_session


def generate_session(type_id: str, subtype: dict, difficulty: str, item_count: int, choice_count: int,
                     theme: str = "Mixed", puzzle_type: str = "Mixed") -> list[dict]:
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
    elif key == "spatial.pattern_finding":
        from generators.spatial.pattern_finding.generator import generate_question
    elif key == "spatial.which_does_not_belong":
        from generators.spatial.which_does_not_belong.generator import generate_question
    else:
        return generate_placeholder_session(type_id, subtype, difficulty, item_count, choice_count)
    if key == "spatial.pattern_finding":
        if puzzle_type not in ("Linear", "Matrix", "Mixed"):
            raise ValueError("Unknown Pattern Finding puzzle type")
        layouts = (["Linear", "Matrix"] * ((item_count + 1) // 2))[:item_count] if puzzle_type == "Mixed" else [puzzle_type] * item_count
        return [generate_question(type_id, subtype, difficulty, choice_count, index + 1, layout)
                for index, layout in enumerate(layouts)]
    if key == "spatial.which_does_not_belong":
        from generators.spatial.which_does_not_belong.generator import eligible_rules

        rng = random.Random()
        available = eligible_rules(difficulty, choice_count)
        by_grid = {size: [rule.id for rule in available if rule.grid_size == size]
                   for size in (1, 2, 3)}
        grid_sizes = [size for size, ids in by_grid.items() if ids]
        rng.shuffle(grid_sizes)
        if 1 in grid_sizes:
            grid_sizes.remove(1)
            grid_sizes.insert(0, 1)
        remaining = {size: [] for size in grid_sizes}
        questions = []
        for index in range(item_count):
            size = grid_sizes[index % len(grid_sizes)]
            if not remaining[size]:
                remaining[size] = by_grid[size][:]
                rng.shuffle(remaining[size])
            questions.append(generate_question(type_id, subtype, difficulty, choice_count,
                                               index + 1, rng=rng,
                                               preferred_rule=remaining[size].pop()))
        return questions
    return [generate_question(type_id, subtype, difficulty, choice_count, index + 1, theme) for index in range(item_count)]
