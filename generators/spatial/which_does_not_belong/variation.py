"""Select visibly distinct options from rule-preserving cell scenes."""

from __future__ import annotations

from .model import appearance_distance


def select_options(rule, candidates, rng, choice_count, reference):
    """Return a unique option set only after the independent ambiguity audit."""
    from .validation import validate

    if len(candidates) < choice_count:
        raise ValueError(f"Insufficient distinct {rule.id} candidates")
    proposals = []
    for _ in range(220):
        chosen = rng.sample(candidates, choice_count)
        majority = [good for good, _ in chosen[:-1]]
        outlier = chosen[-1][1]
        figures = majority + [outlier]
        separation = min(appearance_distance(a, b) for i, a in enumerate(figures)
                         for b in figures[i+1:])
        proposals.append((separation, majority, outlier))
    proposals.sort(key=lambda item: item[0], reverse=True)
    for _, majority, outlier in proposals:
        if validate(rule, majority + [outlier], choice_count - 1, reference):
            return majority, outlier, reference
    raise ValueError(f"Could not assemble an unambiguous {rule.id} option set")
