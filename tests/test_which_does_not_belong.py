"""Classification, ambiguity, SVG and API regression checks."""

import json
import math
import random
import unittest
from copy import deepcopy
from xml.etree import ElementTree

from app import app, load_catalog
from generators import generate_session
from generators.spatial.which_does_not_belong.model import (GRID_CENTERS, appearance_signature,
    centered_on_grid, equivalent_by_rotation, reflect, rotate_degrees)
from generators.spatial.which_does_not_belong.rules import RULES, build, matches
from generators.spatial.which_does_not_belong.render import MOTIFS
from generators.spatial.which_does_not_belong.validation import validate


SUBTYPE = next(x for t in load_catalog()["types"] if t["id"] == "spatial"
               for x in t["subtypes"] if x["id"] == "which-does-not-belong")


class WhichDoesNotBelongTests(unittest.TestCase):
    def test_every_rule_has_a_valid_item_with_four_and_six_choices(self):
        for rule in RULES:
            for count in (4, 6):
                with self.subTest(rule=rule.id, count=count):
                    majority, outlier, reference = build(rule, random.Random(9), count)
                    figures = majority + [outlier]
                    self.assertTrue(validate(rule, figures, count-1, reference))
                    self.assertEqual(len({appearance_signature(f) for f in figures}), count)
                    self.assertEqual([matches(rule, f, reference) for f in figures],
                                     [True]*(count-1)+[False])

    def test_reflection_is_not_a_rotation(self):
        rule = next(rule for rule in RULES if rule.id == "rotation_not_reflection")
        majority, outlier, reference = build(rule, random.Random(1), 6)
        self.assertTrue(all(equivalent_by_rotation(f, reference) for f in majority))
        self.assertFalse(equivalent_by_rotation(outlier, reference))
        self.assertTrue(equivalent_by_rotation(outlier, reflect(reference)))
        self.assertTrue(equivalent_by_rotation(rotate_degrees(reference, 45), reference))

    def test_border_change_cannot_disguise_a_duplicate(self):
        rule = next(rule for rule in RULES if rule.id == "rotation_not_reflection")
        majority, outlier, reference = build(rule, random.Random(2), 4)
        duplicate = deepcopy(majority[0])
        duplicate["components"][0]["boundary"] = "dashed"
        self.assertFalse(validate(rule, [majority[0], duplicate, majority[2], outlier], 3, reference))

    def test_randomized_variants_are_structurally_distinct(self):
        for name in ("one_solid", "matching_directions", "nested_three", "rotation_not_reflection", "clockwise_order"):
            rule = next(rule for rule in RULES if rule.id == name)
            layouts = set()
            for seed in range(5):
                majority, outlier, _ = build(rule, random.Random(seed), 6)
                layouts.add(tuple(appearance_signature(f) for f in majority + [outlier]))
            self.assertEqual(len(layouts), 5, name)

    def test_competing_outlier_is_rejected(self):
        rule = next(rule for rule in RULES if rule.id == "balanced_shading")
        majority, outlier, reference = build(rule, random.Random(1), 4)
        majority[1]["components"][0]["shape"] = "arc"
        self.assertFalse(validate(rule, majority+[outlier], 3, reference))

    def test_session_contract_and_api(self):
        for difficulty in ("Easy", "Average", "Challenge"):
            for count in (2, 4, 6):
                questions = generate_session("spatial", SUBTYPE, difficulty, 5, count)
                self.assertEqual(len(questions), 5)
                for q in questions:
                    with self.subTest(difficulty=difficulty, count=count, rule=q["metadata"]["rule_id"]):
                        self.assertEqual(q["text"], "Which figure does not belong to the group?")
                        self.assertEqual(len(q["choices"]), count)
                        self.assertEqual(q["figures"], [])
                        meta = q["metadata"]
                        rule = next(r for r in RULES if r.id == meta["rule_id"])
                        figures = meta["option_geometry"]
                        self.assertTrue(validate(rule, figures, meta["outlier_index"], meta["canonical_reference"]))
                        self.assertEqual(q["correct_answer_id"], q["choices"][meta["outlier_index"]]["id"])
                        for choice in q["choices"]:
                            figure = choice["figures"][0]
                            ElementTree.fromstring(figure["svg"])
                            self.assertTrue(figure["geometry"]["grayscale_solvable"])
                            self.assertEqual(figure["geometry"]["frame"],
                                             {"x": 4, "y": 4, "size": 104, "radius": 10})
                            root = ElementTree.fromstring(figure["svg"])
                            self.assertTrue(any(element.attrib.get("rx") == "10"
                                                for element in root.iter()))
                        json.dumps(q)
        response = app.test_client().post("/api/practice", json={
            "type_id": "spatial", "subtype_id": SUBTYPE["id"], "item_count": 5,
            "choice_count": 6, "timer_enabled": False, "seconds_per_item": 60,
            "difficulty": "Challenge"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json["placeholder"])

    def test_short_sessions_spread_rule_families(self):
        for difficulty in ("Easy", "Average", "Challenge"):
            for count in (2, 6):
                questions = generate_session("spatial", SUBTYPE, difficulty, 5, count)
                ids = [q["metadata"]["rule_id"] for q in questions]
                self.assertGreaterEqual(len(set(ids)), 2 if count == 2 else 4)

    def test_grid_choices_are_centered_and_share_question_layout(self):
        for rule in RULES:
            for count in (3, 6):
                with self.subTest(rule=rule.id, count=count):
                    majority, outlier, reference = build(rule, random.Random(13), count)
                    figures = majority + [outlier]
                    self.assertTrue(validate(rule, figures, count - 1, reference))
                    for figure in figures:
                        self.assertTrue(centered_on_grid(figure))
                        self.assertEqual(figure["grid"], reference["grid"])
                        self.assertEqual(len(figure["grid"]["centers"]), rule.grid_size ** 2)
                        for component in figure["components"]:
                            self.assertEqual((component["x"], component["y"]),
                                             GRID_CENTERS[rule.grid_size][component["cell"]])
                    shifted = deepcopy(figures[0])
                    shifted["components"][0]["x"] += 1
                    self.assertFalse(centered_on_grid(shifted))

    def test_sessions_cover_grid_sizes_when_available(self):
        for difficulty in ("Easy", "Average", "Challenge"):
            questions = generate_session("spatial", SUBTYPE, difficulty, 6, 6)
            self.assertEqual({q["metadata"]["question_grid"]["size"] for q in questions},
                             {1, 2, 3})

    def test_grid_seed_stress_and_shape_variety(self):
        for rule in (r for r in RULES if r.grid_size > 1):
            scenes = set()
            shapes = set()
            for seed in range(12):
                with self.subTest(rule=rule.id, seed=seed):
                    majority, outlier, reference = build(rule, random.Random(seed), 4)
                    figures = majority + [outlier]
                    self.assertTrue(validate(rule, figures, 3, reference))
                    self.assertEqual(len({appearance_signature(f) for f in figures}), 4)
                    scenes.add(tuple(appearance_signature(f) for f in figures))
                    shapes.update(p["shape"] for f in figures for p in f["components"])
            self.assertGreaterEqual(len(scenes), 8, rule.id)
            if rule.builder in ("count_three", "count_three_grid", "one_solid", "two_striped",
                                "balanced", "permutation", "row_fill"):
                self.assertGreaterEqual(len(shapes), 5, rule.id)

    def test_property_figures_use_multiple_shape_families(self):
        for name in ("three_objects", "one_solid", "two_striped", "balanced_shading"):
            rule = next(rule for rule in RULES if rule.id == name)
            glyphs = set()
            for seed in range(5):
                majority, outlier, reference = build(rule, random.Random(seed), 6)
                self.assertTrue(validate(rule, majority + [outlier], 5, reference))
                glyphs.update((part["shape"], part["sides"])
                              for figure in majority + [outlier] for part in figure["components"])
            self.assertGreaterEqual(len(glyphs), 6, name)

    def test_removed_ambiguous_rule_families_stay_removed(self):
        forbidden = {"opposite_positions", "axis_symmetry", "rotational_symmetry",
                     "contact", "line_intersection", "containment", "quadrant_balance",
                     "equal_spacing", "grid_center", "grid_opposite", "grid_adjacent",
                     "grid_cross", "grid_opposite_marks", "grid_checker_fill"}
        self.assertFalse(forbidden & {predicate["op"] for rule in RULES
                                      for predicate in rule.predicates})

    def test_grid_binding_is_mandatory_for_every_component(self):
        for rule in RULES:
            majority, outlier, reference = build(rule, random.Random(6), 4)
            figures = majority + [outlier]
            for figure in figures:
                self.assertTrue(centered_on_grid(figure), rule.id)
                for component in figure["components"]:
                    self.assertIn("cell", component)
                    self.assertEqual((component["x"], component["y"]),
                                     GRID_CENTERS[rule.grid_size][component["cell"]])
            missing = deepcopy(figures[0])
            del missing["components"][0]["cell"]
            self.assertFalse(centered_on_grid(missing), rule.id)
            self.assertFalse(validate(rule, [missing] + figures[1:], 3, reference), rule.id)

    def test_rotation_and_clockwise_structures_vary(self):
        reflection = next(rule for rule in RULES if rule.id == "rotation_not_reflection")
        clockwise = next(rule for rule in RULES if rule.id == "clockwise_order")
        motifs, triples = set(), set()
        for seed in range(16):
            majority, outlier, reference = build(reflection, random.Random(seed), 6)
            self.assertTrue(validate(reflection, majority + [outlier], 5, reference))
            motifs.add(reference["components"][0]["variant"])
            majority, outlier, reference = build(clockwise, random.Random(seed), 6)
            self.assertTrue(validate(clockwise, majority + [outlier], 5, reference))
            triples.add(tuple(sorted((p["shape"], p["sides"]) for p in reference["components"])))
        self.assertGreaterEqual(len(motifs), 5)
        self.assertGreaterEqual(len(triples), 5)

    def test_every_rendered_motif_is_chiral_and_distinct(self):
        signatures = set()
        for points in MOTIFS:
            rotations = []
            for degrees in range(0, 360, 45):
                radians = math.radians(degrees)
                rotated = {(round(x * math.cos(radians) - y * math.sin(radians), 5),
                            round(x * math.sin(radians) + y * math.cos(radians), 5))
                           for x, y in points}
                rotations.append(rotated)
            mirror = {(round(-x, 5), round(y, 5)) for x, y in points}
            self.assertNotIn(mirror, rotations)
            signature = min(tuple(sorted(rotation)) for rotation in rotations)
            self.assertNotIn(signature, signatures)
            signatures.add(signature)


if __name__ == "__main__":
    unittest.main()
