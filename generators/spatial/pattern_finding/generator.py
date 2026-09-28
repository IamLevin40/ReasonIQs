"""Official Pattern Finding generator.

Rule selection precedes cell construction. One cell is hidden only after the
entire sequence or matrix exists; distractors come last.
"""

from __future__ import annotations

import random
from copy import deepcopy

from .distractors import generate as generate_distractors
from .render import choice_figure, puzzle_figure, puzzle_focus
from .rules import DOMAINS, cell_at, choice_group, describe, signature
from .validation import validate


EASY_ATTRIBUTES = ("sides", "count", "position", "rotation")
SECONDARY_ATTRIBUTES = ("fill", "shape", "mirror", "border",
                        "texture", "internal_lines", "orientation", "nesting",
                        "containment", "symmetry")

POSITION_NAMES = ("top left", "top center", "top right", "middle left",
                  "center", "middle right", "bottom left", "bottom center", "bottom right")
DOT_NAMES = ("top left", "top right", "bottom right", "bottom left",
             "top edge", "right edge", "bottom edge", "left edge")
POLYGON_NAMES = {3: "triangle", 4: "square", 5: "pentagon", 6: "hexagon",
                 7: "heptagon", 8: "octagon"}


def rule_is_visible(rule: dict, states: list[dict]) -> bool:
    """Every value of an active attribute must yield a distinct visible figure."""
    if rule["layer"] == "components":
        return True
    for state in states:
        seen = set()
        for value in dict.fromkeys(rule["values"]):
            variant = deepcopy(state)
            obj = next(item for item in variant["objects"] if item["layer"] == rule["layer"])
            obj[rule["attribute"]] = value
            if rule["attribute"] == "sides":
                obj["shape"] = POLYGON_NAMES[value]
            seen.add(choice_group(variant))
        if len(seen) != len(set(rule["values"])):
            return False
    return True


def _derived_value(state: dict, rule: dict):
    if rule["layer"] == "components":
        return state["components"]
    obj = next(item for item in state["objects"] if item["layer"] == rule["layer"])
    return obj[rule["attribute"]]


def _value_words(rule: dict, value) -> str:
    attr = rule["attribute"]
    if attr == "components":
        return "dots at " + ", ".join(DOT_NAMES[i] for i in value) if value else "no dots"
    if attr == "position":
        return POSITION_NAMES[value]
    if attr == "rotation":
        return f"{value}°"
    if attr == "sides":
        return f"a {value}-sided polygon"
    if attr == "count":
        return f"{value} figure{'s' if value != 1 else ''}"
    return str(value).replace("_", " ")


def make_rule(rng, attribute: str, layout: str, layer: str = "primary",
              direction: str = "rows", difficulty: str = "Average") -> dict:
    """Construct one reusable scalar rule with independently set axis strides."""
    domain = list(DOMAINS[attribute])
    family = "cycle"
    if attribute == "position":
        family = "movement"
        if difficulty == "Easy":
            domain = [0, 1, 2, 5, 8, 7, 6, 3]
        else:
            paths = (
                [0, 1, 2, 5, 8, 7, 6, 3],  # perimeter
                [0, 2, 8, 6],              # corners clockwise
                [1, 5, 7, 3],              # edge middles clockwise
                [0, 8, 2, 6],              # outer diagonal endpoints
                [0, 3, 6],                 # vertical
                [0, 1, 2],                 # horizontal
                [2, 5, 8],                 # right edge
                [6, 7, 8],                 # bottom edge
            )
            domain = rng.choice(paths[:3] if layout == "Matrix" else paths)
        if layer == "inner" and layout == "Mixed":
            domain = [6, 7, 8]
        elif layer == "primary" and layout == "Mixed":
            domain = [0, 1, 2]
    elif attribute == "rotation":
        family = "rotation"
    elif attribute == "mirror":
        family = "reflection"
        domain = ["none", rng.choice(("vertical", "horizontal", "diagonal"))]
    elif attribute == "shape":
        # At higher difficulty, an A-B-C permutation can combine with an
        # independent row or column change in another attribute.
        domain = rng.sample(domain[:12], 4 if layout == "Matrix" else 3 if difficulty != "Easy" else 2)
        family = "distribution" if layout != "Linear" else "alternation"
    elif attribute in ("fill", "texture", "border", "containment", "foreground", "symmetry"):
        family = "alternation" if len(domain) == 2 else "distribution"
        if attribute == "foreground":
            family = "foreground_background"
    elif attribute in ("sides", "count", "internal_lines", "nesting"):
        family = "progression"
    elif attribute == "orientation":
        family = "rotation"
    if layout == "Mixed" and len(domain) > 3 and attribute not in ("position", "rotation"):
        start = rng.randrange(len(domain)-2)
        domain = domain[start:start+3]
    if attribute == "fill":
        domain = ["outline", "solid"]
        family = "alternation"
    if attribute == "position" and layout == "Mixed" and difficulty == "Easy":
        domain = domain[:4]
    step = rng.choice((-1, 1))
    if attribute in ("position", "rotation") and difficulty == "Challenge" and layout != "Matrix":
        step = rng.choice((-2, -1, 1, 2))
    if attribute == "rotation" and layout == "Linear" and difficulty == "Easy":
        step = rng.choice((-2, 2))  # quarter turns
    wrap = True
    origin = rng.randrange(len(domain))
    if layout == "Linear" and attribute in ("sides", "count"):
        domain = list(DOMAINS[attribute])
        step = rng.choice((-1, 1))
        origin = len(domain)-1 if step < 0 else 0
        wrap = False
    if attribute == "count" and layout != "Matrix" and difficulty != "Easy" and rng.random() < .28:
        domain = [1, 2, 3, 2]
        step = rng.choice((-1, 1))
        origin = 0 if step > 0 else 2
        wrap = True
        family = "add_remove"
    if layout == "Mixed" and attribute in ("sides", "count", "internal_lines", "nesting"):
        if family == "alternation":
            wrap = True
        elif family != "add_remove":
            step = rng.choice((-1, 1))
            origin = len(domain)-1 if step < 0 else 0
            wrap = direction == "both"
    if difficulty == "Challenge" and layout != "Matrix" and attribute in ("sides", "count") and rng.random() < .3:
        domain = list(DOMAINS[attribute])
        step = rng.choice((-2, 2))
        origin = len(domain)-1 if step < 0 else 0
        wrap = layout == "Linear" or direction == "both"
        family = "progression" if not wrap else "cycle"
    if layout == "Mixed" and attribute == "count":
        if family != "add_remove":
            domain = [1, 2, 3]
            step = 1 if step > 0 else -1
            origin = 0 if step > 0 else 2
        wrap = True
    row_step = step if direction in ("columns", "both") else 0
    col_step = step if direction in ("rows", "both") else 0
    if layout == "Mixed" and direction == "both" and difficulty == "Challenge" and len(domain) > 2 and rng.random() < .6:
        row_step = rng.choice([candidate for candidate in (-2, -1, 1, 2)
                               if candidate != col_step])
    if layout == "Matrix":
        row_step = col_step = 0
        wrap = True
    if attribute in ("rotation", "orientation"):
        base_shape = rng.choice(("arrow", "chevron", "semicircle", "crescent"))
    else:
        base_shape = rng.choice(("triangle", "square", "pentagon", "hexagon",
                                 "diamond", "star", "arrow", "chevron", "cross",
                                 "ellipse", "semicircle", "circle"))
    return {"layer": layer, "attribute": attribute, "family": family,
            "base_shape": base_shape,
            "values": domain, "origin": origin, "linear_step": step if layout in ("Linear", "Matrix") else 0,
            "row_step": row_step, "col_step": col_step, "wrap": wrap,
            "direction": "serial" if layout == "Matrix" else "linear" if layout == "Linear" else direction,
            "parameter": {"step": step, "row_step": row_step, "col_step": col_step,
                          "path": domain if attribute == "position" else None}}


def _set_rule(rng) -> dict:
    left, right = [], []
    operation = rng.choice(("union", "intersection", "xor", "subtraction",
                            "addition", "symmetry_completion", "balance"))
    for _ in range(3):
        if operation == "balance":
            a, b, c, _missing = rng.sample(range(4), 4)
            left.append(sorted((a, b)))
            right.append([c])
        else:
            common, a, b, c = rng.sample(range(8), 4)
            left.append(sorted((common, a, b)))
            right.append(sorted((common, c)))
    direction = rng.choice(("rows", "columns"))
    return {"layer": "components", "attribute": "components",
            "family": "set_operation", "direction": direction,
            "operation": operation,
            "left": left, "right": right,
            "parameter": {"source_cells": [0, 1], "result_cell": 2}}


def _swap_rules(rng, difficulty: str) -> list[dict]:
    pair = []
    for layer, origin in (("primary", 0), ("inner", 1)):
        rule = make_rule(rng, "position", "Mixed", layer=layer,
                         direction="rows", difficulty=difficulty)
        rule.update(family="swap", values=[3, 5], origin=origin,
                    row_step=0, col_step=1, wrap=True,
                    parameter={"positions": ["left", "right"], "paired_layer":
                               "inner" if layer == "primary" else "primary"})
        pair.append(rule)
    return pair


def select_rules(rng, layout: str, difficulty: str) -> list[dict]:
    primary = rng.choice(("position", "rotation") if layout == "Matrix" and difficulty == "Easy"
                         else EASY_ATTRIBUTES)
    if layout == "Linear":
        rules = [make_rule(rng, primary, layout, difficulty=difficulty)]
        if difficulty != "Easy":
            second = rng.choice([a for a in ("fill", "shape", "mirror", "orientation")
                                 if a != primary
                                 and not (primary == "sides" and a in ("mirror", "orientation"))
                                 and not (primary in ("sides", "rotation") and a == "shape")
                                 and not (primary == "rotation" and a in ("orientation", "mirror"))])
            rules.append(make_rule(rng, second, layout, difficulty=difficulty))
        if difficulty == "Challenge":
            third = rng.choice([a for a in ("position", "rotation", "count", "sides", "fill", "orientation")
                                if a not in {rule["attribute"] for rule in rules}
                                and not ({a, second} == {"fill", "texture"})
                                and not ({a, second} == {"rotation", "orientation"})
                                and not ({a, second} in ({"mirror", "sides"}, {"mirror", "rotation"}))
                                and not ({a, second} in ({"shape", "sides"}, {"shape", "rotation"}))
                                and not ({a, primary} == {"position", "count"})
                                and not ({a, primary} == {"sides", "rotation"})])
            rules.append(make_rule(rng, third, layout, difficulty=difficulty))
        return rules
    if layout == "Matrix":
        rules = [make_rule(rng, primary, layout, difficulty=difficulty)]
        if difficulty != "Easy":
            second = rng.choice([a for a in ("fill", "shape", "orientation", "position", "count") if a != primary
                                 and not (primary == "sides" and a in ("orientation", "shape", "mirror"))
                                 and not (primary == "rotation" and a in ("shape", "orientation", "mirror"))
                                 and {primary, a} != {"position", "count"}])
            rules.append(make_rule(rng, second, layout, difficulty=difficulty))
        if difficulty == "Challenge":
            third = rng.choice([a for a in ("position", "rotation", "sides", "count", "fill", "orientation")
                                if a not in {rule["attribute"] for rule in rules}
                                and not ({a, primary} == {"position", "count"})
                                and not ({a, primary} == {"sides", "rotation"})
                                and not ({a, second} == {"rotation", "orientation"})
                                and not ({a, second} == {"fill", "texture"})
                                and not ({a, second} in ({"shape", "sides"}, {"shape", "rotation"},
                                                         {"mirror", "sides"}, {"mirror", "rotation"}))])
            rules.append(make_rule(rng, third, layout, difficulty=difficulty))
        return rules
    # Mixed: two visible regions, coupled swaps, or a logical dot layer.
    if rng.random() < .24:
        rules = _swap_rules(rng, difficulty)
        if difficulty != "Easy":
            rules.append(make_rule(rng, rng.choice(("fill", "rotation", "border")),
                                   layout, direction="columns", difficulty=difficulty))
        if difficulty == "Challenge":
            rules.append(make_rule(rng, rng.choice(("fill", "shape", "mirror")),
                                   layout, layer="inner", direction="columns", difficulty=difficulty))
        return rules
    if rng.random() < .16:
        rules = [make_rule(rng, "foreground", layout, direction="rows", difficulty=difficulty),
                 make_rule(rng, "rotation", layout, layer="inner",
                           direction="columns", difficulty=difficulty)]
        if difficulty == "Challenge":
            rules.append(make_rule(rng, rng.choice(("position", "border")),
                                   layout, direction="both", difficulty=difficulty))
        return rules
    rules = [make_rule(rng, primary, layout, direction="rows", difficulty=difficulty)]
    inner = rng.choice(tuple(a for a in ("rotation", "position", "fill", "shape", "orientation")
                             if not (primary == "position" and a == "position")))
    rules.append(make_rule(rng, inner, layout, layer="inner", direction="columns", difficulty=difficulty))
    if difficulty == "Challenge" or (difficulty == "Average" and rng.random() < .45):
        rules.append(_set_rule(rng))
    elif difficulty != "Easy":
        candidates = ("border", "fill") if primary in ("sides", "rotation") else ("mirror", "border", "fill")
        rules.append(make_rule(rng, rng.choice(candidates),
                               layout, direction="both", difficulty=difficulty))
    return rules


def generate_question(type_id, subtype, difficulty, choice_count, number, selected_theme="Mixed"):
    if selected_theme not in ("Linear", "Matrix", "Mixed"):
        raise ValueError("Unknown Pattern Finding puzzle type")
    rng = random.Random()
    layout = ("Linear", "Matrix")[(number-1) % 2] if selected_theme == "Mixed" else selected_theme
    for _ in range(240):
        rules = select_rules(rng, layout, difficulty)
        count = 6 if layout == "Linear" else 9
        states = [cell_at(rules, index, layout) for index in range(count)]
        if not all(rule_is_visible(rule, states) for rule in rules):
            continue
        if layout == "Matrix":
            visible = [signature(state) for state in states]
            rows = [tuple(visible[start:start+3]) for start in (0, 3, 6)]
            if len(set(rows)) != 3 or visible[2] == visible[3] or visible[5] == visible[6]:
                continue
        if any(signature(states[i]) == signature(states[j]) for i in range(count) for j in range(i+1, count)
               if layout == "Linear" and abs(i-j) == 1):
            continue
        logic = next((rule for rule in rules if rule["layer"] == "components"), None)
        targets = (list(range(count)) if not logic else
                   [2, 5, 8] if logic["direction"] == "rows" else [6, 7, 8])
        rng.shuffle(targets)
        for target in targets:
            if not validate(rules, states, target, layout):
                continue
            try:
                options, errors = generate_distractors(rules, states, target, choice_count, rng, layout)
            except ValueError:
                continue
            if validate(rules, states, target, layout, options):
                break
        else:
            continue
        break
    else:
        raise RuntimeError("Could not generate an unambiguous Pattern Finding item")

    correct_key = signature(states[target])
    focus_mode = puzzle_focus(states, options)
    choices = [{"id": f"choice-{i+1}", "figures": [choice_figure(state, f"Pattern option {i+1}", focus_mode)]}
               for i, state in enumerate(options)]
    correct = next(i for i, state in enumerate(options) if signature(state) == correct_key)
    derivation = [{"rule_index": i, "attribute": rule["attribute"],
                   "layer": rule["layer"], "value": _derived_value(states[target], rule),
                   "reason": describe(rule)} for i, rule in enumerate(rules)]
    explanations = list(dict.fromkeys(
        f"{step['reason']}, giving {_value_words(rules[step['rule_index']], step['value'])}"
        for step in derivation))
    explanation = "; ".join(explanations)
    explanation = explanation[0].upper() + explanation[1:] + "."
    row, col = (0, target) if layout == "Linear" else divmod(target, 3)
    metadata = {
        "generator_key": subtype["generator_key"], "layout_type": layout,
        "reading_order": list(range(count)),
        "missing_cell": {"index": target, "row": row, "column": col},
        "rule_direction": [rule["direction"] for rule in rules],
        "active_rules": rules,
        "mutable_attributes": sorted({rule["attribute"] for rule in rules}),
        "generated_cell_states": states,
        "correct_derivation": {"cell": states[target], "steps": derivation},
        "distractor_error_type": {choices[i]["id"]: error for i, error in enumerate(errors) if i != correct},
        "difficulty_score": len(rules) + (1 if any(r["layer"] == "components" for r in rules) else 0)
                            + (0.5 if layout == "Mixed" else 0),
        "center_focus": focus_mode,
        "explanation": explanation,
    }
    return {"id": f"{subtype['id']}-{number}", "reasoning_type": type_id,
            "subtype": subtype["id"], "difficulty": difficulty,
            "text": ("Which figure comes next in the sequence?" if layout == "Linear" else
                     "Which figure completes the sequence? Read left to right, then continue on the next row." if layout == "Matrix" else
                     "Which figure completes the pattern? Compare the rows and columns."),
            "figures": [puzzle_figure(states, target, layout, focus_mode)], "choices": choices,
            "correct_answer_id": choices[correct]["id"], "explanation": explanation,
            "metadata": metadata}
