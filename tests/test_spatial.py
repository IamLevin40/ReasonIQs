"""Geometry and generated-answer checks for both dice subtypes."""

import unittest
from xml.etree import ElementTree

from generators.spatial.misc.cube_model import (
    NETS, NORMALS, ROTATIONS, Face, fold_net, observation_matches,
    planar_transform, same_cube,
)
from generators.spatial.dice_folding.generator import generate_question as folding_question
from generators.spatial.dice_unfolding.generator import generate_question as unfolding_question
from generators.spatial.misc.cube_figures import THEMES, artwork, make_markings
from app import app


def restore(snapshot):
    return {NORMALS[normal]: Face(face["face_id"], tuple(face["mark_up"]), face["mirrored"])
            for normal, face in snapshot.items()}


class CubeGeometryTests(unittest.TestCase):
    def test_shape_and_character_artwork_stays_pure(self):
        import math
        import random

        _, polygons, symmetries = make_markings(random.Random(5), "Challenge", "Shapes/Polygons")
        self.assertEqual(sorted(mark["value"] for mark in polygons.values()), [3, 4, 5, 6, 7, 8])
        for identity, mark in polygons.items():
            art = ElementTree.fromstring(f"<svg>{artwork(mark)}</svg>")
            self.assertEqual([element.tag for element in art], ["polygon"])
            points = [tuple(map(float, point.split(","))) for point in art[0].attrib["points"].split()]
            self.assertEqual(len(points), mark["value"])
            radii = [math.hypot(x - 50, y - 50) for x, y in points]
            self.assertLess(max(radii) - min(radii), 0.12)
            self.assertEqual(symmetries[identity], math.gcd(mark["value"], 4))
        _, characters, _ = make_markings(random.Random(5), "Challenge", "Characters")
        for mark in characters.values():
            art = ElementTree.fromstring(f"<svg>{artwork(mark)}</svg>")
            self.assertEqual([element.tag for element in art], ["text"])

    def test_all_eleven_nets_and_planar_symmetries_fold(self):
        self.assertEqual(len(NETS), 11)
        self.assertEqual(len(ROTATIONS), 24)
        for net in NETS:
            for turns in range(4):
                for reflected in (False, True):
                    folded = fold_net(planar_transform(net, turns, reflected))
                    self.assertIsNotNone(folded)
                    self.assertEqual({basis.normal for basis in folded.values()}, set(NORMALS.values()))
        self.assertIsNone(fold_net(((0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1))))
        self.assertIsNone(fold_net(((0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (9, 9))))

    def test_generated_options_are_independently_validated(self):
        configs = (("Easy", 2), ("Average", 4), ("Challenge", 6))
        for generator, subtype_id in ((folding_question, "dice-folding"),
                                      (unfolding_question, "dice-unfolding")):
            subtype = {"id": subtype_id, "generator_key": f"spatial.{subtype_id.replace('-', '_')}"}
            for difficulty, count in configs:
                for number in range(12):
                    question = generator("spatial", subtype, difficulty, count, number + 1)
                    metadata = question["metadata"]
                    source = restore(metadata["source_cube"])
                    symmetries = metadata["marking_symmetries"]
                    self.assertEqual(len(question["choices"]), count)
                    self.assertEqual(len(metadata["options"]), count)
                    self.assertEqual(sum(option["valid"] for option in metadata["options"]),
                                     count - 1 if metadata["mode"] == "cannot" else 1)
                    expected = next(i for i, option in enumerate(metadata["options"])
                                    if option["valid"] == (metadata["mode"] == "can"))
                    self.assertEqual(question["correct_answer_id"], question["choices"][expected]["id"])
                    for figure in question["figures"] + [choice["figures"][0] for choice in question["choices"]]:
                        self.assertEqual(figure["kind"], "svg")
                        ElementTree.fromstring(figure["svg"])
                    views = [restore(view) for view in metadata.get("question_views", [])]
                    if subtype_id == "dice-unfolding":
                        self.assertEqual(len(question["figures"]), len(views))
                        self.assertEqual(len(metadata["observed_face_ids"]),
                                         len({view[n].identity for view in views for n in
                                              (NORMALS["R"], NORMALS["U"], NORMALS["F"])}))
                    for option in metadata["options"]:
                        candidate = restore(option["cube"])
                        proof = same_cube(source, candidate, symmetries)
                        self.assertEqual(proof is not None, option["valid"])
                        self.assertEqual(proof[0] if proof else None, option["legal_rotation"])
                        if not option["valid"]:
                            self.assertTrue(option["violation"])
                        if subtype_id == "dice-unfolding":
                            self.assertIsNotNone(fold_net(option["net_cells"]))
                            self.assertEqual(len(option["face_ids_by_cell"]), 6)
                            self.assertEqual(set(option["face_ids_by_cell"].values()), set(NORMALS))
                            self.assertEqual(observation_matches(views, candidate, symmetries), option["valid"])

    def test_theme_selection_through_api(self):
        client = app.test_client()
        settings = {"type_id": "spatial", "subtype_id": "dice-folding", "difficulty": "Easy",
                    "item_count": 5, "choice_count": 2, "timer_enabled": False,
                    "seconds_per_item": 45}
        for subtype in ("dice-folding", "dice-unfolding"):
            for theme in THEMES:
                response = client.post("/api/practice", json={**settings, "subtype_id": subtype, "theme": theme})
                self.assertEqual(response.status_code, 200)
                self.assertEqual({question["metadata"]["theme"] for question in response.json["questions"]}, {theme})
        self.assertEqual(client.post("/api/practice", json={**settings, "theme": "Color only"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
