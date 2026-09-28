"""Infer hidden values from visible cells and reject ambiguous rule evidence."""

from __future__ import annotations

from .render import cell_markup, puzzle_focus
from .rules import choice_group, coordinates, signature


def _observed(state: dict, rule: dict):
    return next(obj[rule["attribute"]] for obj in state["objects"] if obj["layer"] == rule["layer"])


def infer_attribute(rule: dict, visible: list[dict | None], target: int, layout: str) -> set:
    """Fit origins and strides afresh; do not read the generator's chosen origin."""
    sequence = rule["values"]
    possible = set()
    strides = range(-2, 3)
    for origin in range(len(sequence)):
        for row_step in (strides if layout == "Mixed" else (0,)):
            for col_step in (strides if layout == "Mixed" else (0,)):
                for linear_step in (strides if layout in ("Linear", "Matrix") else (0,)):
                    def predicted(index):
                        row, col, serial = coordinates(index, layout)
                        raw = origin + row*row_step + col*col_step + serial*linear_step
                        if not rule.get("wrap", True) and not 0 <= raw < len(sequence):
                            return None
                        return sequence[raw % len(sequence)]
                    if all(state is None or _observed(state, rule) == predicted(i)
                           for i, state in enumerate(visible)):
                        possible.add(predicted(target))
    return possible


def _set_operation(a: list, b: list, operation: str) -> tuple:
    left, right = set(a), set(b)
    if operation == "addition":
        return tuple(sorted(a+b))
    if operation == "symmetry_completion":
        mirror = {0: 1, 1: 0, 2: 3, 3: 2, 4: 4, 5: 7, 6: 6, 7: 5}
        combined = left | right
        return tuple(sorted(combined | {mirror[item] for item in combined}))
    if operation == "balance":
        return tuple(sorted({0, 1, 2, 3} - (left | right)))
    return tuple(sorted({"union": left | right, "intersection": left & right,
                         "xor": left ^ right, "subtraction": left - right}[operation]))


def infer_set_operation(visible: list[dict | None], target: int, direction: str) -> tuple[set[str], set[tuple]]:
    def idx(band, place):
        return 3*band+place if direction == "rows" else 3*place+band
    valid = set()
    for operation in ("union", "intersection", "xor", "subtraction", "addition",
                      "symmetry_completion", "balance"):
        if all(visible[idx(band, 2)] is None or
               _set_operation(visible[idx(band, 0)]["components"],
                              visible[idx(band, 1)]["components"], operation)
               == tuple(visible[idx(band, 2)]["components"]) for band in range(3)):
            valid.add(operation)
    band = target // 3 if direction == "rows" else target % 3
    a, b = visible[idx(band, 0)]["components"], visible[idx(band, 1)]["components"]
    return valid, {_set_operation(a, b, operation) for operation in valid}


def validate(rules: list[dict], states: list[dict], target: int, layout: str,
             choices: list[dict] | None = None) -> bool:
    visible = [None if i == target else state for i, state in enumerate(states)]
    for rule in rules:
        if rule["layer"] == "components":
            if layout == "Linear" or (target % 3 != 2 if rule["direction"] == "rows" else target // 3 != 2):
                return False
            operations, values = infer_set_operation(visible, target, rule["direction"])
            if len(operations) != 1 or values != {tuple(states[target]["components"])}:
                return False
        elif infer_attribute(rule, visible, target, layout) != {
                _observed(states[target], rule)}:
            return False
    if choices is not None:
        expected = signature(states[target])
        if sum(signature(choice) == expected for choice in choices) != 1:
            return False
        if len({signature(choice) for choice in choices}) != len(choices):
            return False
        if len({choice_group(choice) for choice in choices}) != len(choices):
            return False
        focus_mode = puzzle_focus(states, choices)
        if len({cell_markup(choice, 0, 0, 104, focus_mode=focus_mode) for choice in choices}) != len(choices):
            return False
    return True
