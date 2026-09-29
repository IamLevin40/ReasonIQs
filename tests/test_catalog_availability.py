"""Availability rules for reasoning areas without practice topics."""

import unittest

from app import app, load_catalog


class CatalogAvailabilityTests(unittest.TestCase):
    def test_only_spatial_has_practice_topics(self):
        areas = {area["id"]: area for area in load_catalog()["types"]}
        self.assertEqual(areas["mechanical"]["subtypes"], [])
        self.assertEqual(areas["verbal"]["subtypes"], [])
        self.assertTrue(areas["spatial"]["subtypes"])

    def test_removed_topic_cannot_start_practice(self):
        response = app.test_client().post(
            "/api/practice",
            json={"type_id": "mechanical", "subtype_id": "gears-rotation"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("available", response.json["error"])


if __name__ == "__main__":
    unittest.main()
