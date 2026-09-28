"""Plausible wrong answers produced by specific rule application errors."""

from __future__ import annotations

from copy import deepcopy

from .rules import DOMAINS, choice_group, signature


POLYGON_NAMES = {3: "triangle", 4: "square", 5: "pentagon", 6: "hexagon",
                 7: "heptagon", 8: "octagon"}


def _change(state: dict, rule: dict, new_value) -> dict:
    result = deepcopy(state)
    layer = rule["layer"]
    if layer == "components":
        result["components"] = sorted(new_value)
        return result
    obj = next(item for item in result["objects"] if item["layer"] == layer)
    obj[rule["attribute"]] = new_value
    if rule["attribute"] == "sides":
        obj["shape"] = POLYGON_NAMES[new_value]
    return result


def _observed(state: dict, rule: dict):
    if rule["layer"] == "components":
        return state["components"]
    return next(obj[rule["attribute"]] for obj in state["objects"]
                if obj["layer"] == rule["layer"])


def generate(rules: list[dict], states: list[dict], target: int,
             choice_count: int, rng, layout: str = "Linear") -> tuple[list[dict], list[str]]:
    correct = states[target]
    seen = {signature(correct)}
    seen_groups = {choice_group(correct)}
    candidates: list[tuple[dict, str]] = []

    def offer(state, error):
        key = signature(state)
        group = choice_group(state)
        if key not in seen and group not in seen_groups:
            seen.add(key)
            seen_groups.add(group)
            candidates.append((state, error))

    neighbor = states[target-1] if target else states[1]
    offer(deepcopy(neighbor), "repeat neighboring cell")
    if layout != "Linear" and target >= 3:
        error = ("copy cell above instead of applying the column rule" if layout == "Mixed" else
                 "repeat the figure from the preceding row")
        offer(deepcopy(states[target-3]), error)
    for rule in rules:
        if rule["layer"] == "components":
            band = target // 3 if rule["direction"] == "rows" else target % 3
            indices = ((3*band, 3*band+1) if rule["direction"] == "rows" else (band, 3+band))
            a = set(states[indices[0]]["components"])
            b = set(states[indices[1]]["components"])
            mistaken = ((a | b, "use union"), (a & b, "use intersection"),
                        (a ^ b, "use XOR"), (a - b, "subtract components"),
                        (a, "copy first source"), (b, "copy second source"))
            offer(_change(correct, rule, list(a)+list(b)), "components: add without cancelling shared components")
            for value, error in mistaken:
                offer(_change(correct, rule, value), f"components: {error}")
            for element in range(8):
                changed = set(correct["components"])
                changed.symmetric_difference_update({element})
                offer(_change(correct, rule, changed), "components: fail to add or cancel a dot")
            continue
        right = _observed(correct, rule)
        values = list(dict.fromkeys(rule["values"]))
        ordered = sorted(values, key=lambda v: abs(values.index(v)-values.index(right)))
        for wrong in ordered:
            if wrong == right:
                continue
            if wrong == _observed(neighbor, rule):
                error = "repeat preceding attribute"
            elif values.index(wrong) < values.index(right):
                error = "move backward or stop early"
            else:
                error = "move one or more steps too far"
            offer(_change(correct, rule, wrong), f"{rule['attribute']}: {error}")
        # A symmetric mistake can use a value outside a short two/three-value
        # cycle while retaining the same attribute and symbol vocabulary.
        for wrong in (() if rule["attribute"] == "shape" else DOMAINS[rule["attribute"]]):
            if wrong != right:
                offer(_change(correct, rule, wrong),
                      f"{rule['attribute']}: apply the right rule with the wrong magnitude")

    if len(candidates) < choice_count-1:
        # Paired errors remain connected to the two active transformations.
        for first in rules:
            if first["layer"] == "components":
                continue
            for second in rules:
                if first is second or second["layer"] == "components":
                    continue
                a = next(v for v in DOMAINS[first["attribute"]] if v != _observed(correct, first))
                b = next(v for v in DOMAINS[second["attribute"]] if v != _observed(correct, second))
                offer(_change(_change(correct, first, a), second, b), "apply two rules incorrectly")
    if len(candidates) < choice_count-1:
        raise ValueError("Not enough rule based distractors")
    # Give each active rule a representative wrong answer before filling the
    # remaining slots with other close mistakes.
    chosen = []
    used = set()
    for rule in rules:
        prefix = rule["attribute"] + ":"
        for index, candidate in enumerate(candidates):
            if index not in used and candidate[1].startswith(prefix):
                chosen.append(candidate)
                used.add(index)
                break
        if len(chosen) >= choice_count-1:
            break
    for index, candidate in enumerate(candidates):
        if len(chosen) >= choice_count-1:
            break
        if index not in used:
            chosen.append(candidate)
            used.add(index)
    options = [(deepcopy(correct), "correct derivation"), *chosen]
    rng.shuffle(options)
    return [state for state, _ in options], [error for _, error in options]
