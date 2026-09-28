"""Regression checks for the rendered markings and exact dice answers."""

import random
import unittest
from xml.etree import ElementTree

from generators.spatial.dice_folding.generator import generate_question as folding_question
from generators.spatial.dice_unfolding.generator import generate_question as unfolding_question
from generators.spatial.misc.cube_figures import ABSTRACTS, SHAPES, THEMES, artwork, make_markings
from generators.spatial.misc.cube_model import Face, NORMALS, observation_matches, same_cube


def restore(snapshot):
    return {NORMALS[normal]: Face(face["face_id"], tuple(face["mark_up"]), face["mirrored"])
            for normal, face in snapshot.items()}


class SpatialDiceTests(unittest.TestCase):
    def test_all_artwork_renders_and_has_declared_rotation_symmetry(self):
        for kind, variants in (("shape", SHAPES), ("abstract", ABSTRACTS)):
            for variant, symmetry in variants.items():
                with self.subTest(kind=kind, variant=variant):
                    self.assertIn(symmetry, (1, 2, 4))
                    svg = artwork({"kind": kind, "value": variant, "color": "#91c9bd"})
                    ElementTree.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{svg}</svg>')
                    if kind == "abstract":
                        self.assertNotIn("<circle", svg)

    def test_markings_are_distinct_and_six_faces(self):
        for theme in THEMES:
            for seed in range(30):
                _, marks, symmetries = make_markings(random.Random(seed), "Average", theme)
                self.assertEqual(len(marks), 6)
                self.assertEqual(len({(mark["kind"], mark["value"]) for mark in marks.values()}), 6)
                self.assertEqual(set(marks), set(symmetries))
                if theme in ("Shapes/Polygons", "Abstract Structures"):
                    self.assertEqual(len({mark["color"] for mark in marks.values()}), 6)

    def test_generated_choices_have_one_correct_answer(self):
        for generator, key in ((folding_question, "spatial.dice_folding"),
                               (unfolding_question, "spatial.dice_unfolding")):
            for theme in (*THEMES, "Mixed"):
                for difficulty in ("Easy", "Average", "Challenge"):
                    for count in range(2, 7):
                        with self.subTest(key=key, theme=theme, difficulty=difficulty, count=count):
                            subtype = {"id": key.rsplit(".", 1)[-1], "generator_key": key}
                            for number in range(3):
                                question = generator("spatial", subtype, difficulty, count, number, theme)
                                meta = question["metadata"]
                                source = restore(meta["source_cube"])
                                views = [restore(view) for view in meta.get("question_views", [])]
                                valid = []
                                for option, choice in zip(meta["options"], question["choices"]):
                                    cube = restore(option["cube"])
                                    matches = same_cube(source, cube, meta["marking_symmetries"]) is not None
                                    self.assertEqual(option["valid"], matches)
                                    if views and not matches:
                                        self.assertFalse(observation_matches(views, cube, meta["marking_symmetries"]))
                                    valid.append(matches)
                                    for figure in choice["figures"]:
                                        ElementTree.fromstring(figure["svg"])
                                for figure in question["figures"]:
                                    ElementTree.fromstring(figure["svg"])
                                correct = [choice["id"] for choice, is_valid in zip(question["choices"], valid)
                                           if is_valid == (meta["mode"] == "can")]
                                self.assertEqual(correct, [question["correct_answer_id"]])


if __name__ == "__main__":
    unittest.main()
