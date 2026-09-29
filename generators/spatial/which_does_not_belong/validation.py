"""Independent item audit, including competing simple classifications."""

from __future__ import annotations

from collections import Counter

from .model import (appearance_signature, centered_on_grid, equivalent_by_rotation,
                    reflected_rotation_signature, rotation_signature)
from .rules import RULES, Rule, evaluate, matches


def _try(predicate, figure, reference):
    try:
        return evaluate(predicate, figure, reference)
    except (IndexError, KeyError, StopIteration, TypeError, ValueError):
        return None


def features(figure):
    parts = figure["components"]
    x0 = min(p["x"] - p["size"] for p in parts)
    x1 = max(p["x"] + p["size"] for p in parts)
    y0 = min(p["y"] - p["size"] for p in parts)
    y1 = max(p["y"] + p["size"] for p in parts)
    return {
        "component_count": len(parts),
        "solid_count": sum(p["fill"] == "solid" for p in parts),
        "striped_count": sum(p["texture"] == "striped" for p in parts),
        "dotted_count": sum(p["texture"] == "dotted" for p in parts),
        "dashed_count": sum(p["boundary"] == "dashed" for p in parts),
        "outline_count": sum(p["fill"] == "outline" for p in parts),
        "bbox_orientation": (x1-x0 > y1-y0+2) - (y1-y0 > x1-x0+2),
        "bbox_span_bucket": round(max(x1-x0, y1-y0) / 8),
        "whitespace_bucket": round((112-(x1-x0))*(112-(y1-y0)) / 800),
        "stroke_width": figure["stroke_width"],
        "canvas": tuple(figure["canvas"]),
    }


def validate(rule: Rule, figures, outlier_index, reference):
    """A question passes only with one intended failure and no rival outlier."""
    if len(figures) < 2 or not 0 <= outlier_index < len(figures):
        return False
    if not all(centered_on_grid(figure) and figure["grid"] == reference["grid"]
               for figure in figures):
        return False
    if len({appearance_signature(figure) for figure in figures}) != len(figures):
        return False
    expected = [i != outlier_index for i in range(len(figures))]
    if [matches(rule, figure, reference) for figure in figures] != expected:
        return False
    if rule.id == "rotation_not_reflection":
        if any(not equivalent_by_rotation(figure, reference) for i, figure in enumerate(figures) if i != outlier_index):
            return False
        if rotation_signature(figures[outlier_index]) != reflected_rotation_signature(reference):
            return False
        if equivalent_by_rotation(figures[outlier_index], reference):
            return False

    # Evaluate every registered predicate that is no more complex than the
    # intended rule. A different singleton answer is unacceptable.
    for other in RULES:
        if other.complexity > rule.complexity:
            continue
        for predicate in other.predicates:
            results = [_try(predicate, figure, reference) for figure in figures]
            if None in results:
                continue
            if results.count(False) == 1 and results[outlier_index] is not False:
                return False
            if len(figures) > 2 and results.count(True) == 1 and results[outlier_index] is not True:
                return False
            if 1 < results.count(False) < len(figures) and results.count(True) > results.count(False):
                return False

    # Presentation properties cannot uniquely designate a different choice.
    feature_sets = [features(figure) for figure in figures]
    for name in feature_sets[0]:
        values = [item[name] for item in feature_sets]
        counts = Counter(values)
        if len(counts) > 1 and any(counts[value] == 1 and i != outlier_index
                                   for i, value in enumerate(values)):
            return False
        if name in ("stroke_width", "canvas") and len(counts) != 1:
            return False
    return True
