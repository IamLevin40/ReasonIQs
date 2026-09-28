"""Procedural Dice Folding questions with full-cube answer validation."""

from __future__ import annotations

import random

from generators.spatial.misc.cube_figures import cube_figure, make_markings, net_figure
from generators.spatial.misc.cube_model import (
    NORMALS, OPPOSITES, ROTATIONS, X, Y, Z, Face, Cube, cube_snapshot, net_faces,
    random_net, relocate_face, rotate_cube, same_cube, source_cube, turn_up,
)


def visible_signature(cube: Cube, symmetric: dict[str, int]) -> tuple:
    result = []
    for normal in (Y, Z, X):
        face = cube[normal]
        equivalent = tuple(turn_up(face.mark_up, normal, t)
                           for t in range(0, 4, 4 // symmetric[face.identity]))
        result.append((face.identity, min(equivalent), face.mirrored))
    return tuple(result)


def altered_cube(base: Cube, rng: random.Random, symmetric: dict[str, int], markings: dict[str, dict]) -> tuple[Cube, str] | None:
    normal_a, normal_b = rng.sample((Y, Z, X), 2)
    mutation = rng.choice(("opposites", "face swap", "mark rotation", "mark mirror"))
    changed = dict(base)
    if mutation == "opposites":
        opposite = tuple(-v for v in normal_a)
        changed[normal_b] = relocate_face(base[opposite], opposite, normal_b)
        changed[opposite] = relocate_face(base[normal_b], normal_b, opposite)
        reason = "Opposite faces are shown meeting along an edge."
    elif mutation == "face swap":
        changed[normal_a] = relocate_face(base[normal_b], normal_b, normal_a)
        changed[normal_b] = relocate_face(base[normal_a], normal_a, normal_b)
        reason = "Two faces exchange positions, reversing their required order around the corner."
    elif mutation == "mark rotation":
        face = changed[normal_a]
        if symmetric[face.identity] == 4:
            return None
        changed[normal_a] = Face(face.identity, turn_up(face.mark_up, normal_a, 1))
        reason = "A directional face marking has the wrong rotation for this fold."
    else:
        face = changed[normal_a]
        if symmetric[face.identity] != 1 or not markings[face.identity].get("mirrorable", False):
            return None
        changed[normal_a] = Face(face.identity, face.mark_up, True)
        reason = "A face marking is mirrored, which no rigid cube rotation can produce."
    return changed, reason


def generate_question(type_id: str, subtype: dict, difficulty: str, choice_count: int, number: int,
                      selected_theme: str = "Mixed") -> dict:
    rng = random.Random()
    for _ in range(100):
        source = source_cube(rng, difficulty)
        cells = random_net(rng, difficulty)
        theme, markings, symmetries = make_markings(rng, difficulty, selected_theme)
        cannot = (rng.random() < (0.67 if difficulty == "Challenge" else 0.5))
        desired_valid = 1 if not cannot else choice_count - 1
        options = []
        seen = set()
        attempts = 0
        while len(options) < choice_count and attempts < 500:
            attempts += 1
            valid = sum(option["valid"] for option in options) < desired_valid
            base_rotation = rng.randrange(24)
            base = rotate_cube(source, ROTATIONS[base_rotation])
            if valid:
                candidate, violation = base, None
            else:
                altered = altered_cube(base, rng, symmetries, markings)
                if altered is None:
                    continue
                candidate, violation = altered
            proof = same_cube(source, candidate, symmetries)
            if (proof is not None) != valid:
                continue
            signature = visible_signature(candidate, symmetries)
            if signature in seen:
                continue
            seen.add(signature)
            options.append({"cube": candidate, "valid": valid, "violation": violation,
                            "rotation": proof[0] if proof else None})
        if len(options) == choice_count:
            break
    else:
        raise RuntimeError("Could not create distinct validated folding choices")

    rng.shuffle(options)
    correct = next(i for i, option in enumerate(options) if option["valid"] != cannot)
    prompt = "Which cube cannot be made from the net?" if cannot else "Which cube can be made from the net?"
    choices = []
    for index, option in enumerate(options):
        letter = chr(65 + index)
        choices.append({"id": f"choice-{index + 1}", "figures": [cube_figure(
            option["cube"], markings, f"Folded cube option {letter}")]})
    return {
        "id": f"{subtype['id']}-{number}", "reasoning_type": type_id,
        "subtype": subtype["id"], "difficulty": difficulty, "text": prompt,
        "figures": [net_figure(cells, net_faces(cells, source), markings, "Six-face cube net")],
        "choices": choices, "correct_answer_id": choices[correct]["id"],
        "explanation": (f"Option {chr(65 + correct)} is the only "
                        f"{'impossible' if cannot else 'possible'} cube. "
                        f"{options[correct]['violation'] or 'Its complete face arrangement and marking directions match a rigid rotation of the net.'}"),
        "metadata": {
            "generator_key": subtype["generator_key"], "theme": theme, "mode": "cannot" if cannot else "can",
            "net_cells": cells, "source_cube": cube_snapshot(source),
            "markings": markings, "marking_symmetries": symmetries,
            "opposite_face_pairs": OPPOSITES,
            "adjacent_face_pairs": [(a, b) for a in NORMALS for b in NORMALS
                                    if a < b and (a, b) not in OPPOSITES and (b, a) not in OPPOSITES],
            "options": [{"valid": option["valid"], "legal_rotation": option["rotation"],
                         "violation": option["violation"], "cube": cube_snapshot(option["cube"]),
                         "visible_faces": [option["cube"][normal].identity for normal in (Y, Z, X)]}
                        for option in options],
        },
    }
