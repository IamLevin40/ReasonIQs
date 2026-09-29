"""Official Pattern Fitting question generator."""

from __future__ import annotations

import random

from .distractors import generate as generate_distractors
from .geometry import boundary_connections, clip_pattern, missing_bounds
from .render import choice_figure, puzzle_figure
from .rules import build_master
from .validation import validate, violation

MODES=("Cell Missing","Four-Cell Junction Missing")


def _mode(selected, number):
    if selected not in ("Mixed",*MODES):
        raise ValueError("Unknown Pattern Fitting missing-region mode")
    return MODES[(number-1)%2] if selected == "Mixed" else selected


def _holes(master, mode, rng):
    indices=range(9 if mode == "Cell Missing" else 4)
    candidates=[]
    for index in indices:
        box=missing_bounds(mode,index)
        piece=clip_pattern(master,box)
        connections=boundary_connections(piece,box)
        if len(connections) < 2 or not piece:
            continue
        # Prefer holes where several independent visible contours enter.
        layers=len({entry["layer_id"] for entry in connections})
        score=min(len(connections),18)+3*layers+rng.random()*2
        candidates.append((score,index,box,piece,connections))
    candidates.sort(reverse=True)
    return candidates[:5]


def _explain(rules, connections):
    layers={item["layer_id"] for item in connections}
    descriptions=[]
    for rule in rules:
        if rule["layer_id"] not in layers and len(rules)>1:
            continue
        family=rule["family"]
        if family in ("parallel","crossed","grid","progressive_stripes","diagonal_stripes","cross_hatch"):
            descriptions.append("continues the line spacing and direction across the cut")
        elif family in ("dots","square_dots","short_marks"):
            descriptions.append("preserves the mark spacing and phase")
        elif family in ("wave","zigzag","radial","concentric"):
            descriptions.append("rejoins the curved or radial paths at every boundary")
        elif family in ("checker","alternating_quadrants"):
            descriptions.append("keeps the alternating shading in place")
        elif family in ("rotating_junctions","repeating_cells","perimeter_repeat"):
            descriptions.append("completes the repeated motif and its quarter-turn order")
        elif family == "mirrored_neighbors":
            descriptions.append("restores the mirrored motif")
        else:
            descriptions.append("closes the larger geometric form")
    if not descriptions:
        descriptions=["joins every contour and texture at the missing boundary"]
    return "The piece " + ", and ".join(dict.fromkeys(descriptions)) + "."


def generate_question(type_id, subtype, difficulty, choice_count, number,
                      selected_theme="Mixed", rng=None):
    if difficulty not in ("Easy","Average","Challenge"):
        raise ValueError("Unknown difficulty")
    if not 2 <= choice_count <= 6:
        raise ValueError("Pattern Fitting supports 2 to 6 choices")
    rng=rng or random.Random()
    mode=_mode(selected_theme,number)
    for _attempt in range(100):
        master,rules=build_master(rng,difficulty)
        for _score,index,box,correct_piece,connections in _holes(master,mode,rng):
            try:
                options=generate_distractors(master,correct_piece,box,choice_count,rng)
            except ValueError:
                continue
            correct=next(i for i,(_,mutation) in enumerate(options)
                         if mutation == "exact clipped piece")
            if validate(master,box,options,correct):
                break
        else:
            continue
        break
    else:
        raise RuntimeError("Could not generate a unique Pattern Fitting item")

    explanation=_explain(rules,connections)
    choices=[]
    for i,(piece,mutation) in enumerate(options):
        choices.append({"id":f"choice-{i+1}",
                        "figures":[choice_figure(piece,box,f"Pattern piece option {i+1}")]})
    metadata={
        "generator_key":subtype["generator_key"], "layout_type":"3x3 continuous matrix",
        "missing_region":{"mode":mode,"index":index,"bounds":box},
        "active_rule_layers":rules,"complete_master_pattern":master,
        "boundary_connections":connections,"correct_clipped_geometry":correct_piece,
        "transformation_relationships":[rule.get("transforms",rule["family"]) for rule in rules],
        "distractor_mutation_type":{choices[i]["id"]:mutation for i,(_,mutation) in enumerate(options)
                                    if i != correct},
        "distractor_constraint_violation":{choices[i]["id"]:violation(master,box,piece)
                                           for i,(piece,_) in enumerate(options) if i != correct},
        "difficulty_score":len(rules),"explanation":explanation,
    }
    return {"id":f"{subtype['id']}-{number}","reasoning_type":type_id,
            "subtype":subtype["id"],"difficulty":difficulty,
            "text":"Which piece exactly restores the missing part of the continuous 3×3 pattern?",
            "figures":[puzzle_figure(master,box,mode)],"choices":choices,
            "correct_answer_id":choices[correct]["id"],"explanation":explanation,
            "metadata":metadata}
