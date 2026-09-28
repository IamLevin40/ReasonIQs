"""Procedural Dice Unfolding using the folding subtype's exact cube model."""

from __future__ import annotations

import random

from generators.spatial.misc.cube_figures import cube_figure, make_markings, net_figure
from generators.spatial.misc.cube_model import (
    Face, NORMALS, OPPOSITES, ROTATIONS, X, Y, Z, Cube, cube_snapshot, fold_net,
    net_cube, net_faces, observation_matches, random_net, rotate_cube,
    same_cube, source_cube, turn_up,
)


def question_views(source: Cube, difficulty: str, rng: random.Random) -> tuple[list[Cube], list[int]]:
    first = rng.randrange(24)
    views = [rotate_cube(source, ROTATIONS[first])]
    indexes = [first]
    if difficulty == "Easy" or (difficulty == "Average" and rng.random() < 0.5):
        return views, indexes
    first_visible = {views[0][normal].identity for normal in (X, Y, Z)}
    candidates = []
    for index, rotation in enumerate(ROTATIONS):
        if index == first:
            continue
        view = rotate_cube(source, rotation)
        union = first_visible | {view[normal].identity for normal in (X, Y, Z)}
        if len(union) >= (5 if difficulty == "Challenge" else 4):
            candidates.append((index, view, len(union)))
    if difficulty == "Challenge":
        maximum = max(candidate[2] for candidate in candidates)
        candidates = [candidate for candidate in candidates if candidate[2] == maximum]
    second, view, _ = rng.choice(candidates)
    return [views[0], view], [first, second]


def altered_net_cube(source: Cube, visible_ids: set[str], rng: random.Random,
                     symmetric: dict[str, int], markings: dict[str, dict]) -> tuple[Cube, str] | None:
    changed = dict(source)
    visible_normals = [normal for normal, face in source.items() if face.identity in visible_ids]
    operation = rng.choice(("swap", "swap", "rotation", "mirror", "opposites"))
    if operation == "rotation":
        candidates = [n for n in visible_normals if symmetric[source[n].identity] < 4]
        if not candidates:
            return None
        normal = rng.choice(candidates)
        face = changed[normal]
        changed[normal] = Face(face.identity, turn_up(face.mark_up, normal, 1))
        return changed, "An observed marking is rotated inconsistently with the cube view."
    if operation == "mirror":
        candidates = [n for n in visible_normals if symmetric[source[n].identity] == 1
                      and markings[source[n].identity].get("mirrorable", False)]
        if not candidates:
            return None
        normal = rng.choice(candidates)
        face = changed[normal]
        changed[normal] = Face(face.identity, face.mark_up, True)
        return changed, "An observed asymmetric marking is mirrored."
    if operation == "opposites":
        a = rng.choice(visible_normals)
        b = tuple(-v for v in a)
        c = rng.choice([n for n in visible_normals if n != a])
        # Bring the face opposite a into a visibly adjacent position.
        changed[b] = Face(source[c].identity, source[b].mark_up)
        changed[c] = Face(source[b].identity, source[c].mark_up)
        return changed, "Faces that should be opposite are made adjacent."
    a, b = rng.sample(visible_normals, 2)
    changed[a] = Face(source[b].identity, source[a].mark_up)
    changed[b] = Face(source[a].identity, source[b].mark_up)
    return changed, "Two observed faces are placed in the wrong order around a corner."


def net_signature(cells, cube: Cube) -> tuple:
    folded = fold_net(cells)
    return (tuple(cells), tuple((cell, cube[folded[cell].normal].identity,
                                 cube[folded[cell].normal].mark_up,
                                 cube[folded[cell].normal].mirrored) for cell in sorted(cells)))


def generate_question(type_id: str, subtype: dict, difficulty: str, choice_count: int, number: int,
                      selected_theme: str = "Mixed") -> dict:
    rng = random.Random()
    for _ in range(100):
        source = source_cube(rng, difficulty)
        theme, markings, symmetries = make_markings(rng, difficulty, selected_theme)
        views, view_rotations = question_views(source, difficulty, rng)
        visible_ids = {view[n].identity for view in views for n in (X, Y, Z)}
        cannot = rng.random() < (0.7 if difficulty == "Challenge" else 0.5)
        desired_valid = choice_count - 1 if cannot else 1
        options = []
        seen = set()
        seen_layouts = set()
        attempts = 0
        while len(options) < choice_count and attempts < 600:
            attempts += 1
            valid = sum(option["valid"] for option in options) < desired_valid
            cells = random_net(rng, difficulty)
            if valid:
                candidate, violation = source, None
            else:
                altered = altered_net_cube(source, visible_ids, rng, symmetries, markings)
                if altered is None:
                    continue
                candidate, violation = altered
            faces = net_faces(cells, candidate)
            folded_candidate = net_cube(cells, faces)
            proof = same_cube(source, folded_candidate, symmetries)
            if (proof is not None) != valid:
                continue
            if not valid and observation_matches(views, folded_candidate, symmetries):
                continue
            signature = net_signature(cells, candidate)
            if signature in seen or tuple(cells) in seen_layouts:
                continue
            seen.add(signature)
            seen_layouts.add(tuple(cells))
            options.append({"cells": cells, "faces": faces, "cube": folded_candidate,
                            "valid": valid, "violation": violation,
                            "rotation": proof[0] if proof else None})
        if len(options) == choice_count:
            break
    else:
        raise RuntimeError("Could not create distinct validated unfolding choices")

    rng.shuffle(options)
    correct = next(i for i, option in enumerate(options) if option["valid"] != cannot)
    prompt = "Which net cannot form the cube shown?" if cannot else "Which net can form the cube shown?"
    figures = [cube_figure(view, markings, f"Cube view {index + 1} of {len(views)}")
               for index, view in enumerate(views)]
    choices = []
    for index, option in enumerate(options):
        letter = chr(65 + index)
        choices.append({"id": f"choice-{index + 1}", "figures": [net_figure(
            option["cells"], option["faces"], markings, f"Six-face net option {letter}")]})
    return {
        "id": f"{subtype['id']}-{number}", "reasoning_type": type_id,
        "subtype": subtype["id"], "difficulty": difficulty, "text": prompt,
        "figures": figures, "choices": choices,
        "correct_answer_id": choices[correct]["id"],
        "explanation": (f"Option {chr(65 + correct)} is the only "
                        f"{'impossible' if cannot else 'possible'} net. "
                        f"{options[correct]['violation'] or 'Folding all six squares preserves the observed faces and their marking directions.'}"),
        "metadata": {
            "generator_key": subtype["generator_key"], "theme": theme,
            "mode": "cannot" if cannot else "can", "question_view_rotations": view_rotations,
            "observed_face_ids": sorted(visible_ids), "opposite_face_pairs": OPPOSITES,
            "source_cube": cube_snapshot(source), "question_views": [cube_snapshot(view) for view in views],
            "markings": markings, "marking_symmetries": symmetries,
            "adjacent_face_pairs": [(a, b) for a in NORMALS for b in NORMALS
                                    if a < b and (a, b) not in OPPOSITES and (b, a) not in OPPOSITES],
            "options": [{"valid": option["valid"], "legal_rotation": option["rotation"],
                         "violation": option["violation"], "net_cells": option["cells"],
                         "cube": cube_snapshot(option["cube"]),
                         "face_ids_by_cell": {f"{x},{y}": option["faces"][(x, y)].identity
                                              for x, y in option["cells"]}}
                        for option in options],
        },
    }
