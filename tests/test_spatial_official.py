"""Independent regression checks for exact spatial answers and SVG contracts."""

import json
import random
import unittest
from pathlib import Path
from xml.etree import ElementTree

from generators import generate_session
from generators.spatial.blocks_forming.solver import fit as fit_blocks
from generators.spatial.cube_counting.model import fill_behind, grow, views
from generators.spatial.cube_counting.validation import possible_counts
from generators.spatial.jigsaw_forming.model import make_board, rotate_board, rotate_piece
from generators.spatial.jigsaw_forming.solver import fit as fit_jigsaw
from generators.spatial.jigsaw_forming.solver import valid_square
from generators.spatial.perspective_viewing.model import build, cube, prism
from generators.spatial.perspective_viewing.projection import polygons, project, raycast_signature, signature
from generators.spatial.misc.geometry import STRUCTURE_PALETTES, choose_structure_palette, supported


CATALOG = json.loads((Path(__file__).resolve().parents[1] / "data/reasoning_types.json").read_text())
SPATIAL = next(item for item in CATALOG["types"] if item["id"] == "spatial")
NEW = SPATIAL["subtypes"][2:6]


class OfficialSpatialTests(unittest.TestCase):
    def test_structure_palettes_vary_by_item_and_keep_one_hue_per_figure(self):
        rng=random.Random(42)
        selected={choose_structure_palette(rng) for _ in range(80)}
        self.assertEqual(selected,set(STRUCTURE_PALETTES))
        for shades in STRUCTURE_PALETTES.values():
            self.assertEqual(set(shades),{"top","front","side"})
            self.assertEqual(len(set(shades.values())),3)

    def test_square_jigsaw_quarter_turns(self):
        for difficulty in ("Easy", "Average", "Challenge"):
            board=make_board(random.Random(17),difficulty)
            self.assertTrue(valid_square(board))
            loose=[rotate_piece(piece,(index+1)%4) for index,piece in enumerate(board["tiles"])]
            for turns in range(4):
                rotated=rotate_board(board,turns)
                self.assertTrue(valid_square(rotated))
                self.assertIsNotNone(fit_jigsaw(rotated,loose))

    def test_rear_fill_and_coordinate_count(self):
        source = {(0,0,0), (1,0,0), (1,1,0), (1,1,1)}
        solid = fill_behind(source)
        self.assertEqual(solid, {(x,y,z) for x in range(2) for y in range(2) for z in range(2)})
        self.assertEqual(len(solid), 8)
        for difficulty in ("Easy", "Average", "Challenge"):
            for seed in range(12):
                generated = grow(random.Random(seed), difficulty)
                self.assertIn((0,0,0), generated)
                self.assertTrue(all(x >= 0 and y >= 0 and z >= 0 for x,y,z in generated))

    def test_world_fixed_view_orientation_and_prism_projection(self):
        self.assertEqual(project((1,0,0), "Front"), (-1,0))
        self.assertEqual(project((1,0,0), "Top"), (-1,0))
        self.assertEqual(project((0,1,0), "Top"), (0,1))
        self.assertEqual(project((0,1,0), "Left"), (1,0))
        shapes = [cube(0,0,0), cube(1,0,0), prism(1,0,1,False,"x")]
        for view in ("Top", "Front", "Left"):
            self.assertEqual(signature(polygons(shapes,view)), raycast_signature(shapes,view))
        for difficulty in ("Easy", "Average", "Challenge"):
            for seed in range(12):
                shapes = build(random.Random(seed), difficulty)
                prism_shapes = [shape for shape in shapes if shape["kind"] == "triangular-prism"]
                if difficulty != "Easy":
                    self.assertEqual(len(prism_shapes), 1)
                    cube_top = max(shape["origin"][2] for shape in shapes if shape["kind"] == "cube")
                    self.assertEqual(prism_shapes[0]["origin"][2], cube_top + 1)
                for view in ("Top", "Front", "Left"):
                    self.assertEqual(signature(polygons(shapes,view)), raycast_signature(shapes,view))

    def test_catalog_replaces_temporary_spatial_entries(self):
        self.assertEqual([item["generator_key"] for item in SPATIAL["subtypes"]], [
            "spatial.dice_folding", "spatial.dice_unfolding", "spatial.cube_counting",
            "spatial.perspective_viewing", "spatial.blocks_forming", "spatial.jigsaw_forming",
            "spatial.pattern_finding"])

    def test_exact_answers_and_figure_data(self):
        for subtype in NEW:
            for difficulty in ("Easy", "Average", "Challenge"):
                for count in (2, 4, 6):
                    with self.subTest(subtype=subtype["id"], difficulty=difficulty, count=count):
                        for question in generate_session("spatial", subtype, difficulty, 3, count):
                            json.dumps(question)
                            self.assertEqual(len(question["choices"]), count)
                            self.assertIn(question["correct_answer_id"], [c["id"] for c in question["choices"]])
                            for figure in question["figures"] + [f for c in question["choices"] for f in c.get("figures", [])]:
                                self.assertIn("geometry", figure)
                                ElementTree.fromstring(figure["svg"])
                            meta = question["metadata"]
                            key = subtype["generator_key"]
                            if key == "spatial.cube_counting":
                                solid = set(map(tuple, meta["voxels"]))
                                self.assertTrue(supported(solid))
                                self.assertEqual(meta["answer_count"], len(solid))
                                self.assertEqual(sum(int(c["text"]) == len(solid) for c in question["choices"]), 1)
                                if meta["mode"] == "isometric":
                                    palette=meta["structure_palette"]
                                    self.assertIn(palette,STRUCTURE_PALETTES)
                                    self.assertEqual(question["figures"][0]["geometry"]["palette"],palette)
                                    self.assertEqual(question["figures"][0]["geometry"]["face_shades"],STRUCTURE_PALETTES[palette])
                                    self.assertEqual(fill_behind(solid), solid)
                                    faces = question["figures"][0]["geometry"]["visible_faces"]
                                    self.assertTrue(all(face["shade"] in STRUCTURE_PALETTES[palette].values()
                                                        for face in faces))
                                    self.assertEqual(len(faces), sum((x,y,z+1) not in solid for x,y,z in solid)
                                                     + sum((x,y+1,z) not in solid for x,y,z in solid)
                                                     + sum((x+1,y,z) not in solid for x,y,z in solid))
                                if meta["mode"] == "three-view":
                                    self.assertEqual(possible_counts(views(solid))[0], {len(solid)})
                            elif key == "spatial.perspective_viewing":
                                palette=meta["structure_palette"]
                                self.assertIn(palette,STRUCTURE_PALETTES)
                                self.assertEqual(question["figures"][0]["geometry"]["palette"],palette)
                                self.assertEqual(question["figures"][0]["geometry"]["face_shades"],STRUCTURE_PALETTES[palette])
                                target = frozenset(map(tuple, meta["projection_signature"]))
                                self.assertEqual(target, raycast_signature(meta["solids"], meta["requested_view"]))
                                arrows = question["figures"][0]["geometry"]["view_arrows"]
                                self.assertEqual([arrow["view"] for arrow in arrows if arrow["highlighted"]],
                                                 [meta["requested_view"]])
                                left,top,right,bottom=question["figures"][0]["geometry"]["object_bounds"]
                                by_view={arrow["view"]:arrow for arrow in arrows}
                                self.assertLess(by_view["Top"]["screen_tip"][1],top)
                                self.assertLess(by_view["Left"]["screen_tip"][0],left)
                                self.assertGreater(by_view["Left"]["screen_tip"][1],bottom)
                                self.assertGreater(by_view["Front"]["screen_tip"][0],right)
                                self.assertGreater(by_view["Front"]["screen_tip"][1],bottom)
                                self.assertTrue(all(len(arrow["screen_vertices"])==7 for arrow in arrows))
                                self.assertNotIn("<line",question["figures"][0]["svg"])
                                valid = [signature(polys) == target for polys in meta["choice_polygons"]]
                                self.assertEqual(valid.count(True), 1)
                                self.assertEqual(question["choices"][valid.index(True)]["id"], question["correct_answer_id"])
                                self.assertEqual(meta["choice_polygons"][valid.index(True)],
                                                 polygons(meta["solids"], meta["requested_view"]))
                            elif key == "spatial.blocks_forming":
                                palette=meta["structure_palette"]
                                self.assertIn(palette,STRUCTURE_PALETTES)
                                figures=question["figures"]+[f for choice in question["choices"] for f in choice["figures"]]
                                self.assertTrue(all(figure["geometry"]["palette"]==palette for figure in figures))
                                target = set(map(tuple, meta["target_voxels"]))
                                valid = [fit_blocks(target, option) is not None for option in meta["options"]]
                                self.assertEqual(valid.count(True), 1)
                                self.assertEqual(question["choices"][valid.index(True)]["id"], question["correct_answer_id"])
                                self.assertTrue(all(sum(map(len, option)) == len(target) for option in meta["options"]))
                            else:
                                size=meta["board_size"]
                                self.assertIn(size,(2,3))
                                self.assertEqual(len(meta["detached_pieces"]),size*size)
                                self.assertEqual(len(question["figures"]),size*size)
                                self.assertEqual(meta["aspect_ratio"],[1,1])
                                self.assertFalse(meta["allow_reflection"])
                                self.assertTrue(all(valid_square(option) for option in meta["options"]))
                                valid=[fit_jigsaw(option,meta["detached_pieces"]) is not None
                                       for option in meta["options"]]
                                self.assertEqual(valid.count(True), 1)
                                self.assertEqual(question["choices"][valid.index(True)]["id"], question["correct_answer_id"])
                                for choice in question["choices"]:
                                    figure=choice["figures"][0]
                                    _,_,width,height=map(float,ElementTree.fromstring(figure["svg"]).attrib["viewBox"].split())
                                    self.assertEqual(width,height)
                                    self.assertEqual(figure["geometry"]["aspect_ratio"],[1,1])


if __name__ == "__main__":
    unittest.main()
