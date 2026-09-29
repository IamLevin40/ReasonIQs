"""Rule semantics, identifiability, graph, and figure regression checks."""
import json
import random
import unittest
from copy import deepcopy
from xml.etree import ElementTree

from generators.spatial.rule_determining.generator import generate_question, validate
from generators.spatial.rule_determining.rules import Rule

SUBTYPE = {"id": "rule-determining", "generator_key": "spatial.rule_determining"}


class RuleDeterminingTests(unittest.TestCase):
    def test_parameterized_rule_families_and_preconditions(self):
        cases = [
            ("remove_at", ("first",), "LKPO", "KPO"),
            ("remove_neighbor", ("A", "after"), "XAB", "XA"),
            ("remove_matching", ("odd_digit",), "A123", "A2"),
            ("remove_duplicates", (), "ABACA", "ABC"),
            ("insert_at", ("center", "E"), "ABCD", "ABECD"),
            ("insert_neighbor", ("A", "before", "E"), "BAC", "BEAC"),
            ("insert_between_all", ("E",), "ABC", "AEBEC"),
            ("insert_between_selected", ("A", "B", "E"), "ABCD", "AEBCD"),
            ("duplicate_at", (1,), "ABC", "ABBC"),
            ("replace_symbol", ("A", "E", "all"), "ABAA", "EBEE"),
            ("swap_adjacent", (), "ABCDE", "BADCE"),
            ("move", (1, "back"), "ABCD", "ACDB"),
            ("rotate", ("left", 2), "ABCDE", "CDEAB"),
            ("reverse_half", ("second",), "ABCD", "ABDC"),
            ("exchange_halves", (), "ABCD", "CDAB"),
            ("odd_even", (), "ABCDE", "ACEBD"),
            ("shift_letters", (2, None), "YZ", "AB"),
            ("shift_digits", (1,), "89", "90"),
            ("letters_to_positions", (), "AZ", "0126"),
            ("positions_to_letters", (), "0126", "AZ"),
            ("add_derived", ("back", "vowel"), "BEA", "BEA2"),
            ("retain_matching", ("digit",), "A12B", "12"),
            ("repeat_substring", (0, 2), "ABC", "ABCAB"),
        ]
        for operation, args, source, expected in cases:
            with self.subTest(operation=operation):
                self.assertEqual(Rule("test", operation, args).apply(source), expected)
        with self.assertRaises(ValueError):
            Rule("test", "remove_neighbor", ("Z", "after")).apply("ABC")
        with self.assertRaises(ValueError):
            Rule("test", "remove_at", ("first",)).apply("A")

    def test_generated_questions_are_executable_identifiable_and_renderable(self):
        for difficulty in ("Easy", "Average", "Challenge"):
            for count in (2, 4, 6):
                for seed in range(20):
                    with self.subTest(difficulty=difficulty, count=count, seed=seed):
                        question = generate_question("spatial", SUBTYPE, difficulty, count, seed+1,
                                                     rng=random.Random(seed))
                        json.dumps(question)
                        meta = question["metadata"]
                        graph = meta["transformation_graph"]
                        values = [choice["text"] for choice in question["choices"]]
                        self.assertTrue(validate(graph, meta["operator_dictionary"], values))
                        self.assertEqual(len(values), count)
                        self.assertEqual(values.count(meta["correct_output"]), 1)
                        self.assertEqual(len(meta["query_path"]), {"Easy": 2, "Average": 4, "Challenge": 6}[difficulty])
                        self.assertEqual(len(set(meta["query_path"])), {"Easy": 2, "Average": 3, "Challenge": 4}[difficulty])
                        self.assertEqual(len(question["figures"]), 2)
                        for figure in question["figures"]:
                            ElementTree.fromstring(figure["svg"])
                            self.assertIn("geometry", figure)
                        nodes = {n["id"]: n for n in graph["nodes"]}
                        demonstrations = graph["demonstrations"]
                        self.assertTrue(any(
                            first["node_ids"][2] == second["node_ids"][0]
                            for first in demonstrations for second in demonstrations))
                        self.assertTrue(graph["reuse_links"])
                        for link in graph["reuse_links"]:
                            self.assertEqual(nodes[link["from"]]["value"],
                                             nodes[link["to"]]["value"])
                            self.assertEqual(nodes[link["from"]]["cell"][1],
                                             nodes[link["to"]]["cell"][1])
                        for edge in graph["edges"]:
                            a, b = nodes[edge["from"]], nodes[edge["to"]]
                            self.assertTrue(a["cell"][0] == b["cell"][0] or a["cell"][1] == b["cell"][1])
                            self.assertTrue(edge["directed"])
                        for rule_id, formal in meta["operator_dictionary"].items():
                            witnesses = [d["input"] for d in graph["demonstrations"] if d["rule_id"] == rule_id]
                            if formal["operation"] == "shift_digits":
                                self.assertTrue(any(("9" if formal["parameters"][0] > 0 else "0") in s for s in witnesses))
                            if formal["operation"] == "shift_letters" and formal["parameters"][1] is None:
                                boundary = "YZ" if formal["parameters"][0] > 0 else "A"
                                self.assertTrue(any(any(c in s for c in boundary) for s in witnesses))

    def test_validator_rejects_corrupt_demonstration(self):
        question = generate_question("spatial", SUBTYPE, "Easy", 4, 1, rng=random.Random(7))
        meta = question["metadata"]
        graph = deepcopy(meta["transformation_graph"])
        graph["demonstrations"][0]["output"] = "WRONG"
        self.assertFalse(validate(graph, meta["operator_dictionary"],
                                  [choice["text"] for choice in question["choices"]]))


if __name__ == "__main__":
    unittest.main()
