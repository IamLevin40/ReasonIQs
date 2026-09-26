import unittest
from pathlib import Path

from app import app, load_catalog


class ReasonIQsApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_catalog_relationships_and_assets(self):
        catalog = load_catalog()
        self.assertEqual({item["id"] for item in catalog["types"]}, {"mechanical", "spatial", "verbal"})
        all_ids = set()
        for reasoning_type in catalog["types"]:
            self.assertGreaterEqual(len(reasoning_type["subtypes"]), 6)
            self.assertTrue((Path(__file__).resolve().parents[1] / reasoning_type["icon"].lstrip("/")).is_file())
            for subtype in reasoning_type["subtypes"]:
                self.assertNotIn(subtype["id"], all_ids)
                all_ids.add(subtype["id"])
                self.assertEqual(subtype["parent_id"], reasoning_type["id"])
                self.assertEqual(subtype["difficulties"], ["Easy", "Average", "Challenge"])
                self.assertTrue((Path(__file__).resolve().parents[1] / subtype["icon"].lstrip("/")).is_file())

    def test_practice_respects_item_and_choice_counts(self):
        for domain in load_catalog()["types"]:
            for choice_count in (2, 4, 6):
                response = self.client.post("/api/practice", json={
                    "type_id": domain["id"], "subtype_id": domain["subtypes"][0]["id"],
                    "difficulty": "Challenge", "item_count": 5, "choice_count": choice_count,
                    "timer_enabled": True, "seconds_per_item": 10,
                })
                self.assertEqual(response.status_code, 200)
                questions = response.json["questions"]
                self.assertEqual(len(questions), 5)
                self.assertTrue(all(len(question["choices"]) == choice_count for question in questions))
                self.assertTrue(all(question["correct_answer_id"] in {choice["id"] for choice in question["choices"]} for question in questions))

    def test_rejects_invalid_settings(self):
        valid = {
            "type_id": "mechanical", "subtype_id": "gears-rotation",
            "difficulty": "Average", "item_count": 5, "choice_count": 4,
            "timer_enabled": False, "seconds_per_item": 45,
        }
        for field, value in [
            ("item_count", 4), ("item_count", True), ("choice_count", 7),
            ("seconds_per_item", 9), ("difficulty", "Expert"),
            ("subtype_id", "missing"), ("timer_enabled", "yes"),
        ]:
            response = self.client.post("/api/practice", json={**valid, field: value})
            self.assertEqual(response.status_code, 400, (field, value))
            self.assertIn("error", response.json)

    def test_placeholder_session_exercises_content_formats(self):
        response = self.client.post("/api/practice", json={
            "type_id": "mechanical", "subtype_id": "gears-rotation",
            "difficulty": "Average", "item_count": 5, "choice_count": 4,
            "timer_enabled": False, "seconds_per_item": 45,
        })
        questions = response.json["questions"]
        self.assertEqual(len(questions[0]["figures"]), 2)
        self.assertTrue(questions[0]["text"])
        self.assertFalse(questions[0]["choices"][0].get("text"))
        self.assertEqual(questions[0]["choices"][0]["figures"][0]["kind"], "svg")
        self.assertFalse(questions[1]["text"])
        self.assertEqual(len(questions[1]["figures"]), 1)
        self.assertTrue(questions[2]["choices"][0]["text"])
        self.assertEqual(len(questions[2]["choices"][0]["figures"]), 1)
        self.assertFalse(questions[3]["figures"])


if __name__ == "__main__":
    unittest.main()
