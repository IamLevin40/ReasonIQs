"""Official Which Does Not Belong? generator."""

from __future__ import annotations

import random

from .render import render_figure
from .rules import RULES, build
from .validation import validate

ATTRIBUTES = {
    "count": ("components",), "solid_count": ("fill",),
    "texture_count": ("texture",), "outer_parity": ("sides",),
    "side_relation": ("sides", "role"), "same_orientation": ("angle", "role"),
    "closed": ("shape",),
    "straight": ("shape",), "convex": ("shape",),
    "balanced_fill": ("fill",),
    "rotation_family": ("angle", "shape", "variant", "handedness"),
    "nested_depth": ("size", "role"),
    "unique_types": ("shape",), "clockwise_order": ("x", "y", "shape"),
    "grid_permutation": ("cell",), "grid_row_one_solid": ("cell", "fill"),
    "grid_three_pairs": ("cell", "role"), "grid_half_sides": ("cell", "role", "sides"),
    "grid_unique_sides": ("cell", "sides"),
}

TWO_CHOICE_EXCLUSIONS = frozenset({
    "three_objects", "one_solid", "two_striped", "grid_three_cells",
    "balanced_shading", "nested_three",
})


def eligible_rules(difficulty, choice_count):
    return [rule for rule in RULES if rule.difficulty == difficulty
            and (choice_count > 2 or rule.id not in TWO_CHOICE_EXCLUSIONS)]


def generate_question(type_id, subtype, difficulty, choice_count, number,
                      selected_theme="Mixed", rng=None, preferred_rule=None):
    if difficulty not in ("Easy", "Average", "Challenge"):
        raise ValueError("Unknown difficulty")
    if not 2 <= choice_count <= 6:
        raise ValueError("Which Does Not Belong? requires 2–6 choices")
    rng = rng or random.Random()
    pool = eligible_rules(difficulty, choice_count)
    first = rng.randrange(len(pool))
    candidates = pool[first:] + pool[:first]
    if preferred_rule is not None:
        preferred = next(rule for rule in pool if rule.id == preferred_rule)
        candidates = [preferred] + [rule for rule in candidates if rule.id != preferred_rule]
    for rule in candidates:
        for _ in range(8):
            try:
                majority, outlier, reference = build(rule, rng, choice_count)
            except ValueError:
                continue
            tagged = [(figure, False) for figure in majority] + [(outlier, True)]
            rng.shuffle(tagged)
            figures = [figure for figure, _ in tagged]
            outlier_index = next(i for i, (_, is_outlier) in enumerate(tagged) if is_outlier)
            if validate(rule, figures, outlier_index, reference):
                break
        else:
            continue
        break
    else:
        raise RuntimeError("Could not generate an unambiguous Which Does Not Belong? item")

    choices = [{"id": f"choice-{i+1}",
                "figures": [render_figure(figure, f"Option {chr(65+i)} geometric figure")]}
               for i, figure in enumerate(figures)]
    answer = choices[outlier_index]["id"]
    explanation = f"{rule.explanation} Option {chr(65+outlier_index)}: {rule.violation[0].lower()}{rule.violation[1:]}"
    metadata = {
        "generator_key": subtype["generator_key"], "rule_id": rule.id,
        "rule_family": rule.family, "active_predicates": list(rule.predicates),
        "relevant_figure_attributes": sorted({field for p in rule.predicates
                                               for field in ATTRIBUTES[p["op"]]}),
        "majority_class_explanation": rule.explanation,
        "outlier_violation": rule.violation,
        "difficulty_score": rule.complexity,
        "question_grid": figures[0]["grid"],
        "option_geometry": figures, "canonical_reference": reference,
        "outlier_index": outlier_index, "explanation": explanation,
        "validation": {"intended_failures": 1, "competing_outlier": False,
                       "grayscale_solvable": True},
    }
    return {"id": f"{subtype['id']}-{number}", "reasoning_type": type_id,
            "subtype": subtype["id"], "difficulty": difficulty,
            "text": "Which figure does not belong to the group?", "figures": [],
            "choices": choices, "correct_answer_id": answer,
            "explanation": explanation, "metadata": metadata}
