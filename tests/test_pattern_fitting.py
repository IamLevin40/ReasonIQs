"""Continuous-pattern clipping, uniqueness, and API integration checks."""

import json
import random
import unittest
from xml.etree import ElementTree

from app import app
from generators import generate_session
from generators.spatial.pattern_fitting.distractors import _transform
from generators.spatial.pattern_fitting.generator import generate_question
from generators.spatial.pattern_fitting.geometry import (
    boundary_connections, circle, clip_pattern, missing_bounds, primitive, signature,
    visible_signature,
)
from generators.spatial.pattern_fitting.rules import DARK, LIGHT, SHAPES, _motif, _motifs, build_master
from generators.spatial.pattern_fitting.validation import validate


SUBTYPE={"id":"pattern-fitting","generator_key":"spatial.pattern_fitting"}


class PatternFittingTests(unittest.TestCase):
    def test_both_holes_clip_a_complete_master_across_boundaries(self):
        master=[primitive("line",[(0,125),(300,125)],role="stripe",phase=5),
                primitive("arc",circle(100,100,65),role="closure")]
        for mode,index in (("Cell Missing",3),("Four-Cell Junction Missing",0)):
            box=missing_bounds(mode,index)
            piece=clip_pattern(master,box)
            self.assertTrue(piece)
            self.assertGreaterEqual(len(boundary_connections(piece,box)),2)
            self.assertEqual(signature(piece),signature(clip_pattern(master,box)))
        self.assertEqual(missing_bounds("Four-Cell Junction Missing",0),[50,50,150,150])

    def test_symmetry_equivalent_choice_is_rejected(self):
        box=[50,50,150,150]
        master=[primitive("circle",circle(100,100,65),role="closure")]
        correct=clip_pattern(master,box)
        rotated=_transform(correct,box,"rotate_90")
        self.assertEqual(signature(correct),signature(rotated))
        self.assertFalse(validate(master,box,[(correct,"exact clipped piece"),(rotated,"rotate_90")],0))

    def test_rule_layers_and_exact_unique_piece_at_all_difficulties(self):
        families=set()
        for difficulty in ("Easy","Average","Challenge"):
            for mode in ("Cell Missing","Four-Cell Junction Missing"):
                for seed in range(4):
                    rng=random.Random(seed+100)
                    q=generate_question("spatial",SUBTYPE,difficulty,6,seed+1,mode,rng)
                    json.dumps(q)
                    meta=q["metadata"]
                    families.update(rule["family"] for rule in meta["active_rule_layers"])
                    self.assertEqual(meta["missing_region"]["mode"],mode)
                    self.assertEqual(len(meta["active_rule_layers"]),
                                     meta["difficulty_score"])
                    self.assertIn(len(meta["active_rule_layers"]),
                                  {"Easy":(1,),"Average":(2,3),"Challenge":(3,4)}[difficulty])
                    box=meta["missing_region"]["bounds"]
                    master=meta["complete_master_pattern"]
                    expected=signature(clip_pattern(master,box))
                    pieces=[choice["figures"][0]["geometry"]["primitives"] for choice in q["choices"]]
                    signatures=[signature(piece) for piece in pieces]
                    self.assertEqual(signatures.count(expected),1)
                    self.assertEqual(len(set(signatures)),6)
                    self.assertEqual(len({visible_signature(piece,grayscale=True)
                                          for piece in pieces}),6)
                    correct=next(i for i,choice in enumerate(q["choices"])
                                 if choice["id"] == q["correct_answer_id"])
                    self.assertTrue(validate(master,box,list(zip(pieces,[""]*6)),correct))
                    self.assertEqual(pieces[correct],meta["correct_clipped_geometry"])
                    self.assertEqual(len(meta["distractor_mutation_type"]),5)
                    self.assertGreaterEqual(len(meta["boundary_connections"]),2)
                    for figure in q["figures"]+[choice["figures"][0] for choice in q["choices"]]:
                        self.assertEqual(figure["kind"],"svg")
                        ElementTree.fromstring(figure["svg"])
        self.assertGreaterEqual(len(families),6)

    def test_mixed_session_and_practice_api(self):
        questions=generate_session("spatial",SUBTYPE,"Average",6,4,puzzle_type="Mixed")
        self.assertEqual([q["metadata"]["missing_region"]["mode"] for q in questions],
                         ["Cell Missing","Four-Cell Junction Missing"]*3)
        payload={"type_id":"spatial","subtype_id":"pattern-fitting","item_count":5,
                 "choice_count":4,"timer_enabled":False,"seconds_per_item":60,
                 "difficulty":"Easy","puzzle_type":"Four-Cell Junction Missing"}
        response=app.test_client().post("/api/practice",json=payload)
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.json["placeholder"])
        self.assertEqual({q["metadata"]["missing_region"]["mode"]
                          for q in response.json["questions"]},{"Four-Cell Junction Missing"})
        payload["puzzle_type"]="Invalid"
        self.assertEqual(app.test_client().post("/api/practice",json=payload).status_code,400)

    def test_master_is_built_independently_of_hole(self):
        a,rules=build_master(random.Random(17),"Challenge")
        self.assertGreaterEqual(len(rules),3)
        self.assertTrue(all("layer_id" in item and "points" in item for item in a))
        cell=clip_pattern(a,missing_bounds("Cell Missing",4))
        junction=clip_pattern(a,missing_bounds("Four-Cell Junction Missing",0))
        self.assertNotEqual(signature(cell),signature(junction))

    def test_foreground_motifs_are_opaque_aligned_and_binary_shaded(self):
        for shape in SHAPES:
            art=_motif("motif",shape,150,150,54,0,False)
            self.assertTrue(any(item["kind"] == "fill" and item["fill"] == LIGHT
                                for item in art),shape)
        for seed in range(70):
            art,rule=_motifs(random.Random(seed),"motif")
            radius=rule["radius"]
            centers=[(x,y) for x,y,_ in rule["placements"]]
            for i,a in enumerate(centers):
                for b in centers[i+1:]:
                    self.assertGreaterEqual(sum((a[j]-b[j])**2 for j in (0,1))**.5,
                                            2*radius+8)
            fills=[item["fill"] for item in art if item["kind"] == "fill"]
            self.assertTrue(fills)
            self.assertLessEqual(set(fills),{LIGHT,DARK})

    def test_hidden_background_lines_do_not_create_visible_difference(self):
        box=[0,0,100,100]
        foreground=_motif("motif","circle",50,50,35,0,False)
        a=clip_pattern([primitive("lines",[(20,50),(80,50)]),*foreground],box)
        b=clip_pattern([primitive("lines",[(30,50),(70,50)]),*foreground],box)
        self.assertNotEqual(signature(a),signature(b))
        self.assertEqual(visible_signature(a,grayscale=True),
                         visible_signature(b,grayscale=True))


if __name__ == "__main__":
    unittest.main()
