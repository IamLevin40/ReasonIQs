"""Plausible numerical miscounts, checked against the authoritative voxel set."""

from __future__ import annotations


def counts(rng, voxels, choice_count, difficulty):
    answer = len(voxels)
    top = {(x, y) for x, y, _ in voxels}
    hidden_bases = sum(1 for x, y, z in voxels if z == 0 and (x, y, 1) in voxels)
    offsets = [len(top), answer-hidden_bases, answer-2, answer-1, answer+1,
               answer+2, answer+3, answer-3, answer+4, answer-4]
    if difficulty == "Challenge":
        offsets = [answer-1, answer+1, answer-2, answer+2, *offsets]
    unique = [answer]
    for value in offsets:
        if 1 <= value <= answer+5 and value not in unique:
            unique.append(value)
    if len(unique) < choice_count:
        unique.extend(value for value in range(1, answer+6) if value not in unique)
    wrong = unique[1:choice_count]
    rng.shuffle(wrong)
    result = [answer, *wrong]
    rng.shuffle(result)
    return result
