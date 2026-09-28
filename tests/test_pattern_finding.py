"""Pattern Finding rule, inference, SVG, and API contract checks."""

import json
import random
import unittest
from copy import deepcopy
from xml.etree import ElementTree

from app import app
from generators import generate_session
from generators.spatial.pattern_finding.generator import generate_question, make_rule, rule_is_visible, select_rules
from generators.spatial.pattern_finding.render import PATH_POINTS, COUNT_ANCHORS, choice_figure, puzzle_figure, puzzle_focus, shape_markup
from generators.spatial.pattern_finding.rules import DOMAINS, cell_at, choice_group, signature
from generators.spatial.pattern_finding.validation import validate


SUBTYPE = {"id": "pattern-finding", "generator_key": "spatial.pattern_finding"}


class PatternFindingTests(unittest.TestCase):
    def test_rule_engine_reconstructs_every_hidden_position(self):
        for layout in ("Linear", "Matrix", "Mixed"):
            for difficulty in ("Easy", "Average", "Challenge"):
                for seed in range(24):
                    rng = random.Random(seed)
                    rules = select_rules(rng, layout, difficulty)
                    states = [cell_at(rules, i, layout) for i in range(6 if layout == "Linear" else 9)]
                    valid = [i for i in range(len(states)) if validate(rules, states, i, layout)]
                    self.assertTrue(valid, (layout, difficulty, seed, rules))
                    for index in valid:
                        self.assertEqual(states[index], cell_at(rules, index, layout))

    def test_generates_one_exact_answer_and_structured_svg(self):
        layouts = set()
        nonfinal = 0
        for difficulty in ("Easy", "Average", "Challenge"):
            for choice_count in (2, 4, 6):
                for number in range(1, 16):
                    q = generate_question("spatial", SUBTYPE, difficulty, choice_count, number)
                    json.dumps(q)
                    meta = q["metadata"]
                    layouts.add(meta["layout_type"])
                    target = meta["missing_cell"]["index"]
                    self.assertEqual(meta["reading_order"], list(range(len(meta["generated_cell_states"]))))
                    nonfinal += target != len(meta["generated_cell_states"])-1
                    self.assertFalse(meta.get("placeholder", False))
                    self.assertEqual(q["difficulty"], difficulty)
                    self.assertEqual(len(q["choices"]), choice_count)
                    self.assertEqual(len(meta["distractor_error_type"]), choice_count-1)
                    self.assertTrue(validate(meta["active_rules"], meta["generated_cell_states"],
                                             target, meta["layout_type"],
                                             [choice["figures"][0]["geometry"]["cell"]
                                              for choice in q["choices"]]))
                    self.assertIsNone(q["figures"][0]["geometry"]["cells"][target])
                    self.assertEqual(meta["correct_derivation"]["cell"],
                                     meta["generated_cell_states"][target])
                    for figure in q["figures"] + [choice["figures"][0] for choice in q["choices"]]:
                        self.assertEqual(figure["kind"], "svg")
                        ElementTree.fromstring(figure["svg"])
        self.assertEqual(layouts, {"Linear", "Matrix"})
        self.assertGreater(nonfinal, 50)

    def test_matrix_is_one_row_major_sequence_and_mixed_keeps_axes(self):
        rule = {"layer": "primary", "attribute": "rotation", "family": "rotation",
                "values": list(range(0, 270, 30)), "origin": 0,
                "linear_step": 1, "row_step": 3, "col_step": 5,
                "wrap": False, "direction": "serial"}
        self.assertEqual(rule["direction"], "serial")
        states = [cell_at([rule], i, "Matrix") for i in range(9)]
        self.assertEqual([state["objects"][0]["rotation"] for state in states],
                         [0, 30, 60, 90, 120, 150, 180, 210, 240])
        self.assertTrue(any(validate([rule], states, i, "Matrix") for i in range(9)))
        generated = make_rule(random.Random(5), "rotation", "Matrix")
        self.assertEqual((generated["direction"], generated["row_step"], generated["col_step"]),
                         ("serial", 0, 0))
        row_rule = make_rule(random.Random(7), "position", "Mixed", direction="rows")
        column_rule = make_rule(random.Random(8), "rotation", "Mixed", direction="columns")
        self.assertEqual(row_rule["row_step"], 0)
        self.assertEqual(column_rule["col_step"], 0)

    def test_matrix_rules_continue_across_row_boundaries(self):
        for difficulty in ("Easy", "Average", "Challenge"):
            for seed in range(60):
                rules = select_rules(random.Random(seed), "Matrix", difficulty)
                self.assertTrue(all(rule["direction"] == "serial" and
                                    (len(rule["values"]) >= 4 or rule["attribute"] == "fill")
                                    and abs(rule["linear_step"]) == 1 for rule in rules))
                states = [cell_at(rules, i, "Matrix") for i in range(9)]
                if difficulty == "Easy":
                    rows = [tuple(signature(state) for state in states[start:start+3])
                            for start in (0, 3, 6)]
                    self.assertEqual(len(set(rows)), 3)
                for rule in rules:
                    values = [next(obj[rule["attribute"]] for obj in state["objects"]
                                   if obj["layer"] == rule["layer"]) for state in states]
                    if difficulty == "Easy":
                        self.assertNotEqual(values[:3], values[3:6])
                        self.assertNotEqual(values[3:6], values[6:9])
                    for i in (2, 5):
                        expected = rule["values"][(rule["origin"] + (i+1)*rule["linear_step"]) % len(rule["values"])]
                        self.assertEqual(values[i+1], expected)

    def test_puzzle_type_setting_and_balanced_session(self):
        for selected in ("Linear", "Matrix"):
            questions = generate_session("spatial", SUBTYPE, "Average", 5, 4,
                                         puzzle_type=selected)
            self.assertEqual([q["metadata"]["layout_type"] for q in questions], [selected]*5)
        mixed = generate_session("spatial", SUBTYPE, "Easy", 8, 4,
                                 puzzle_type="Mixed")
        layouts = [q["metadata"]["layout_type"] for q in mixed]
        self.assertEqual(layouts, ["Linear", "Matrix"]*4)
        odd = generate_session("spatial", SUBTYPE, "Easy", 5, 4,
                               puzzle_type="Mixed")
        self.assertEqual([q["metadata"]["layout_type"] for q in odd],
                         ["Linear", "Matrix", "Linear", "Matrix", "Linear"])
        payload = {"type_id": "spatial", "subtype_id": "pattern-finding",
                   "item_count": 5, "choice_count": 4, "timer_enabled": False,
                   "seconds_per_item": 60, "difficulty": "Easy", "puzzle_type": "Matrix"}
        response = app.test_client().post("/api/practice", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({q["metadata"]["layout_type"] for q in response.json["questions"]}, {"Matrix"})
        payload["puzzle_type"] = "Invalid"
        self.assertEqual(app.test_client().post("/api/practice", json=payload).status_code, 400)
        payload["puzzle_type"] = "Balanced"
        self.assertEqual(app.test_client().post("/api/practice", json=payload).status_code, 400)

    def test_set_operations(self):
        for direction in ("rows", "columns"):
            for operation in ("union", "intersection", "xor", "subtraction", "addition",
                              "symmetry_completion", "balance"):
                rule = {"layer": "components", "attribute": "components", "family": "set_operation",
                        "direction": direction, "operation": operation,
                        "left": [[0, 1], [1, 2], [0, 3]] if operation == "balance" else
                        [[0, 1, 2], [1, 3, 5], [2, 4, 6]],
                        "right": [[2], [0], [1]] if operation == "balance" else
                        [[0, 3], [1, 6], [2, 7]]}
                states = [cell_at([rule], i, "Mixed") for i in range(9)]
                target = 5 if direction == "rows" else 7
                self.assertTrue(validate([rule], states, target, "Mixed"))

    def test_internal_positions_are_cell_centers(self):
        self.assertEqual(PATH_POINTS, tuple((x, y) for y in (-26, 0, 26) for x in (-26, 0, 26)))
        self.assertEqual(COUNT_ANCHORS[3], (1, 4, 7))
        state = cell_at([], 0, "Matrix")
        state["objects"][0]["position"] = 2
        svg = choice_figure(state, "top right")["svg"]
        self.assertEqual(choice_figure(state, "top right")["geometry"]["internal_grid"]["anchors"],
                         PATH_POINTS)
        self.assertIn('translate(26.00 -26.00)', svg)
        self.assertNotIn('M-13 -39 V39 M13 -39 V39', svg)
        paired = cell_at([make_rule(random.Random(3), "rotation", "Mixed", layer="inner")],
                         0, "Mixed")
        paired_svg = choice_figure(paired, "paired")["svg"]
        self.assertIn('translate(0.00 -26.00)', paired_svg)
        self.assertIn('translate(0.00 26.00)', paired_svg)

    def test_recognized_shapes_dots_and_center_focus(self):
        self.assertNotIn("irregular", DOMAINS["shape"])
        with self.assertRaises(ValueError):
            shape_markup("irregular", "#fff", "smooth")
        self.assertIn('stroke-dasharray="1 6"', shape_markup("line", "#fff", "segmented"))
        self.assertIn('stroke-dasharray="1 6"', shape_markup("pentagon", "#fff", "segmented"))
        center = cell_at([], 0, "Matrix")
        centered_svg = choice_figure(center, "center")["svg"]
        self.assertIn('scale(1.100)', centered_svg)
        off_center = deepcopy(center)
        off_center["objects"][0]["position"] = 2
        self.assertIn('scale(0.550)', choice_figure(off_center, "corner")["svg"])
        self.assertNotIn('stroke="#dce3e5"', centered_svg)
        self.assertTrue(puzzle_focus([center, deepcopy(center)]))
        self.assertFalse(puzzle_focus([center, off_center]))
        self.assertFalse(puzzle_focus([center], [center, off_center]))
        puzzle_svg = puzzle_figure([center, off_center], 1, "Linear",
                                   puzzle_focus([center, off_center]))["svg"]
        self.assertIn('scale(0.550)', puzzle_svg)
        self.assertNotIn('scale(1.100)', puzzle_svg)
        self.assertIn('scale(0.550)', choice_figure(center, "center", False)["svg"])

    def test_no_size_rules_and_visually_distinct_choice_groups(self):
        for layout in ("Linear", "Matrix"):
            for difficulty in ("Easy", "Average", "Challenge"):
                for seed in range(40):
                    rules = select_rules(random.Random(seed), layout, difficulty)
                    self.assertNotIn("size", {rule["attribute"] for rule in rules})
        state = cell_at([], 0, "Linear")
        mirrored = deepcopy(state)
        mirrored["objects"][0]["mirror"] = "vertical"
        self.assertEqual(signature(state), signature(mirrored))
        marked = deepcopy(state)
        marked["objects"][0]["border"] = "double"
        self.assertEqual(choice_group(state), choice_group(marked))
        shifted = deepcopy(state)
        shifted["objects"][0]["position"] = 2
        self.assertNotEqual(choice_group(state), choice_group(shifted))
        patterned = deepcopy(state)
        patterned["objects"][0]["texture"] = "dots"
        self.assertEqual(choice_group(state), choice_group(patterned))
        filled = deepcopy(state)
        filled["objects"][0]["fill"] = "solid"
        self.assertNotEqual(choice_group(state), choice_group(filled))
        circle = deepcopy(state)
        circle["objects"][0]["shape"] = "circle"
        rotation_rule = make_rule(random.Random(9), "rotation", "Linear")
        self.assertFalse(rule_is_visible(rotation_rule, [circle]))
        arrow = deepcopy(state)
        self.assertTrue(rule_is_visible(rotation_rule, [arrow]))
        semicircle = deepcopy(state)
        semicircle["objects"][0]["shape"] = "semicircle"
        reflected = deepcopy(semicircle)
        reflected["objects"][0]["mirror"] = "vertical"
        self.assertEqual(signature(semicircle), signature(reflected))

    def test_moving_figures_use_outer_grid_only(self):
        perimeter = (0, 1, 2, 5, 8, 7, 6, 3)
        self.assertNotIn(4, DOMAINS["position"])
        for layout in ("Linear", "Matrix", "Mixed"):
            for difficulty in ("Easy", "Average", "Challenge"):
                for seed in range(100):
                    rule = make_rule(random.Random(seed), "position", layout,
                                     difficulty=difficulty)
                    self.assertNotIn(4, rule["values"])
                    self.assertTrue(set(rule["values"]) <= set(perimeter))
                    if difficulty == "Easy" and layout != "Mixed":
                        self.assertEqual(tuple(rule["values"]), perimeter)

    def test_easy_and_average_use_varied_familiar_base_shapes(self):
        for difficulty in ("Easy", "Average"):
            shapes = {cell_at(select_rules(random.Random(seed), "Linear", difficulty), 0,
                              "Linear")["objects"][0]["shape"] for seed in range(60)}
            self.assertGreaterEqual(len(shapes), 7)
            self.assertTrue(shapes <= set(DOMAINS["shape"]) | {"heptagon", "octagon"})

    def test_practice_api_uses_official_generator(self):
        payload = {"type_id": "spatial", "subtype_id": "pattern-finding",
                   "item_count": 5, "choice_count": 6, "timer_enabled": False,
                   "seconds_per_item": 60, "difficulty": "Challenge"}
        response = app.test_client().post("/api/practice", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["placeholder"])
        self.assertEqual(len(response.json["questions"]), 5)

    def test_visible_equivalence_filters_symmetric_and_masked_choices(self):
        state = cell_at([], 0, "Linear")
        square = deepcopy(state)
        square["objects"][0]["shape"] = "square"
        turned = deepcopy(square)
        turned["objects"][0]["rotation"] = 90
        self.assertEqual(signature(square), signature(turned))
        reflected = deepcopy(square)
        reflected["objects"][0]["mirror"] = "vertical"
        self.assertEqual(signature(square), signature(reflected))
        arrow = deepcopy(state)
        arrow["objects"][0]["rotation"] = 90
        self.assertNotEqual(signature(state), signature(arrow))
        textured = deepcopy(state)
        textured["objects"][0]["texture"] = "hatch"
        alternate_fill = deepcopy(textured)
        alternate_fill["objects"][0]["fill"] = "solid"
        self.assertEqual(signature(textured), signature(alternate_fill))
        invisible_sides = deepcopy(state)
        invisible_sides["objects"][0]["sides"] = 8
        self.assertEqual(signature(state), signature(invisible_sides))
        self.assertFalse(validate([], [state, state], 0, "Linear", [state, invisible_sides]))


if __name__ == "__main__":
    unittest.main()
