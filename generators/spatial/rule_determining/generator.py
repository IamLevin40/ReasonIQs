"""Rule-first directed graph generation, evidence audit, and distractors."""
from __future__ import annotations

import random

from .rules import BY_ID, RULES, Rule, meaning_id
from .render import render_section

SHAPES = ("circle", "triangle", "square", "diamond", "pentagon", "hexagon",
          "octagon", "star", "cross", "trapezoid", "parallelogram",
          "semicircle", "crescent", "chevron")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def _try(rule: Rule, value: str) -> str | None:
    try:
        return rule.apply(value)
    except ValueError:
        return None


def _source(rng, rule=None):
    if rule and rule.op == "positions_to_letters":
        return "".join(f"{rng.randrange(1, 27):02d}" for _ in range(rng.randint(2, 3)))
    if rule and rule.op == "letters_to_positions":
        return "".join(rng.choices(ALPHABET, k=rng.randint(2, 4)))
    length = rng.randint(4, 6)
    chars = [rng.choice(ALPHABET + ("0123456789" if rng.random() < .55 else "")) for _ in range(length)]
    if rule and ("A" in str(rule.args) or rule.op == "remove_duplicates"):
        chars[rng.randrange(length)] = "A"
        if rng.random() < .5: chars[rng.randrange(length)] = "A"
    if rule and rule.op == "map_symbols":
        chars[1] = rng.choice([old for old, _ in rule.args[0]])
        if rng.random() < .5: chars[-1] = rule.args[0][-1][0]
    if rule and rule.op in ("insert_between_selected",):
        chars[1:3] = list("AB")
    if rule and rule.op == "remove_duplicates":
        chars[-1] = chars[0]
    if rule and rule.op == "shift_letters":
        chars[0] = rng.choice("YZ") if rule.args[0] > 0 else "A"
    if rule and rule.op == "shift_digits":
        chars[-1] = "9" if rule.args[0] > 0 else "0"
    if rule and rule.op in ("remove_matching", "retain_matching", "add_derived"):
        chars[0], chars[1], chars[2] = "A", "B", "3"
    return "".join(chars)


def _evidence(rule, rng):
    """Add witnesses until no different registered transformation fits them."""
    viable = {candidate.id for candidate in RULES}
    pairs = []
    for _ in range(110):
        source = _source(rng, rule)
        result = _try(rule, source)
        if result is None or any(a == source for a, _ in pairs): continue
        next_viable = {name for name in viable if _try(BY_ID[name], source) == result}
        if len(pairs) >= 2 and len(next_viable) == len(viable) and source[0] in {a[0] for a, _ in pairs}: continue
        pairs.append((source, result))
        viable = next_viable
        wrap_seen = (rule.op not in ("shift_letters", "shift_digits") or
                     any(("Z" in before or (rule.args[0] > 1 and "Y" in before)) if rule.op == "shift_letters" and rule.args[0] > 0 else
                         ("A" in before) if rule.op == "shift_letters" else
                         ("9" in before) if rule.args[0] > 0 else ("0" in before)
                         for before, _ in pairs))
        if len(pairs) >= 2 and len({a[0] for a, _ in pairs}) >= 2 and wrap_seen and all(meaning_id(name) == meaning_id(rule.id) for name in viable):
            return pairs
        if len(pairs) >= 7: break
    return None


def _query(rng, difficulty):
    target_unique, steps, tier = {"Easy": (2, 2, 0), "Average": (3, 4, 1),
                                  "Challenge": (4, 6, 2)}[difficulty]
    # A rule can recur, but every selected rule must be demonstrated.
    preferred = rng.choice([r for r in RULES if r.level == tier]) if tier and rng.random() < .55 else None
    source = _source(rng, preferred)
    current = source
    path = []
    states = [source]
    for index in range(steps):
        pool = [r for r in RULES if r.level <= tier and (r in path or len(set(path)) < target_unique)]
        if len(set(path)) < target_unique and steps-index <= target_unique-len(set(path)):
            pool = [r for r in pool if r not in path]
        rng.shuffle(pool)
        if index == 0 and preferred in pool:
            pool.remove(preferred); pool.insert(0, preferred)
        for rule in pool:
            result = _try(rule, current)
            if result and result != source and result not in states and len(result) <= 9:
                path.append(rule); states.append(result); current = result
                break
        else:
            return None
    if len(set(path)) != target_unique: return None
    return path, states


def _example_chains(rules, path, states, rng):
    """Find worked paths that use more than one shape without exposing the answer."""
    chains = []
    positions = {rule.id: index for index, rule in enumerate(rules)}
    for start in range(len(path) - 1):
        segment = path[start:start + 2]
        if positions[segment[0].id] >= positions[segment[1].id]: continue
        original = states[start]
        for _ in range(180):
            chars = list(original)
            at = rng.randrange(len(chars))
            chars[at] = rng.choice("0123456789" if chars[at].isdigit() else ALPHABET)
            source = "".join(chars)
            if source == original: continue
            values = [source]
            for rule in segment:
                value = _try(rule, values[-1])
                if value is None: break
                values.append(value)
            if len(values) == 3 and values[-1] not in states:
                chains.append((segment, values))
                break
    return chains


def _graph(rules, evidence, path, states, shapes, chains):
    nodes, edges, demonstrations = [], [], []
    def node(kind, value, row, col, section, shape=None):
        item = {"id": f"n{len(nodes)}", "kind": kind, "value": value,
                "cell": [row, col], "section": section}
        if shape: item["shape"] = shape
        nodes.append(item)
        return item["id"]
    def edge(a, b, section):
        edges.append({"from": a, "to": b, "section": section, "directed": True})
    row = 0
    shape_nodes = {rule.id: [] for rule in rules}
    rule_positions = {rule.id: index for index, rule in enumerate(rules)}
    for segment, values in chains:
        first_col = rule_positions[segment[0].id] * 2
        ids = [node("box", values[0], row, first_col, "demonstration")]
        for index, rule in enumerate(segment):
            rule_col = rule_positions[rule.id] * 2
            operator = node("operator", rule.id, row, rule_col + 1,
                            "demonstration", shapes[rule.id])
            output = node("box", values[index + 1], row, rule_col + 2,
                          "demonstration")
            edge(ids[-1], operator, "demonstration")
            edge(operator, output, "demonstration")
            shape_nodes[rule.id].append(operator)
            demonstrations.append({"rule_id": rule.id, "shape": shapes[rule.id],
                                   "input": values[index], "output": values[index + 1],
                                   "node_ids": [ids[-1], operator, output],
                                   "trace": values[index:index + 2]})
            ids.append(output)
        row += 1
    base_row = row + 1
    for rule_index, rule in enumerate(rules):
        for witness_index, (before, after) in enumerate(evidence[rule.id]):
            witness_row = base_row + witness_index * 3
            column = rule_index * 2 + 1
            a = node("box", before, witness_row, column, "demonstration")
            o = node("operator", rule.id, witness_row + 1, column,
                     "demonstration", shapes[rule.id])
            b = node("box", after, witness_row + 2, column, "demonstration")
            edge(a, o, "demonstration"); edge(o, b, "demonstration")
            shape_nodes[rule.id].append(o)
            demonstrations.append({"rule_id": rule.id, "shape": shapes[rule.id],
                                   "input": before, "output": after, "node_ids": [a, o, b],
                                   "trace": [before, after]})
    row = base_row + 3 * max(len(evidence[rule.id]) for rule in rules)
    query_row = row + 2
    query_nodes = [node("box", states[0], query_row, 0, "query")]
    turn = (len(path)+1)//2 if len(path) > 2 else len(path)
    for i, rule in enumerate(path):
        if i < turn:
            cell_row, cell_col = query_row, 2*i+2
        else:
            cell_row, cell_col = query_row+2, 2*(len(path)-i)
        current = node("operator", rule.id, cell_row, cell_col, "query", shapes[rule.id])
        edge(query_nodes[-1], current, "query"); query_nodes.append(current)
    answer = node("box", "?", query_row+2 if turn < len(path) else query_row,
                  0 if turn < len(path) else 2*len(path)+2, "query")
    edge(query_nodes[-1], answer, "query"); query_nodes.append(answer)
    size = max(query_row + (3 if turn < len(path) else 1),
               2 * len(rules) + 1, 2 * len(path) + 3, 9)
    return {"grid": {"rows": size, "columns": size, "cell_width": 112, "cell_height": 72},
            "nodes": nodes, "edges": edges, "demonstrations": demonstrations,
            "reuse_links": [{"from": a, "to": b, "rule_id": rule_id}
                            for rule_id, ids in shape_nodes.items()
                            for a, b in zip(ids, ids[1:])],
            "query": {"node_ids": query_nodes, "operator_ids": [r.id for r in path],
                      "input": states[0], "intermediate_states": states[1:-1],
                      "correct_output": states[-1], "trace": states}}


def _distractors(path, states, count, rng):
    result = states[-1]
    proposals = []
    def add(value, error):
        if value and value != result and len(value) <= 12 and value not in [x for x, _ in proposals]:
            proposals.append((value, error))
    for i in range(1, len(states)-1): add(states[i], "stopped_after_step_"+str(i))
    for skipped in range(len(path)):
        current = states[0]
        for i, rule in enumerate(path):
            if i != skipped: current = _try(rule, current)
            if current is None: break
        add(current, "skipped_step_"+str(skipped+1))
    for i in range(len(path)-1):
        order = path[:]; order[i], order[i+1] = order[i+1], order[i]
        current = states[0]
        for rule in order:
            current = _try(rule, current) if current else None
        add(current, "swapped_steps_"+str(i+1)+"_"+str(i+2))
    for i in range(1, len(path)):
        if path[i] == path[i-1]:
            current = states[0]
            for j, rule in enumerate(path):
                if j != i: current = _try(rule, current) if current else None
            add(current, "repeated_operator_once")
    # Local misconception variants, continued through the remainder of the path.
    for i, rule in enumerate(path):
        alternatives = []
        if rule.op in ("remove_at", "duplicate_at", "replace_at"):
            old = rule.args[0]
            for where in ("first", "last", 1, 2):
                if where != old: alternatives.append(Rule("misread", rule.op, (where,)+rule.args[1:]))
        if rule.op == "insert_at":
            for where in ("first", "last", 1, "center"):
                if where != rule.args[0]: alternatives.append(Rule("misread", rule.op, (where, rule.args[1])))
        if rule.op == "rotate":
            alternatives += [Rule("misread", "reverse"), Rule("misread", "rotate", ("right" if rule.args[0]=="left" else "left", rule.args[1]))]
        if rule.op == "remove_neighbor":
            alternatives.append(Rule("misread", "remove_occurrence", (rule.args[0], "first")))
        if rule.op == "shift_letters":
            alternatives.append(Rule("misread", "shift_letters", (-rule.args[0], rule.args[1])))
        if rule.op == "shift_digits":
            alternatives.append(Rule("misread", "shift_digits", (-rule.args[0],)))
        if rule.op in ("remove_matching", "retain_matching"):
            alternatives.append(Rule("misread", "retain_matching" if rule.op == "remove_matching" else "remove_matching", rule.args))
        for alternative in alternatives:
            current = _try(alternative, states[i])
            for following in path[i+1:]:
                current = _try(following, current) if current else None
            add(current, f"misapplied_{rule.id}_at_step_{i+1}")
        if rule.op in ("shift_letters", "shift_digits"):
            # A learner may leave the boundary character unchanged instead of
            # applying the specified alphabet/digit wrap.
            source, shifted = states[i], states[i+1]
            offset = rule.args[0]
            boundary = ("Z" if offset == 1 else "YZ") if rule.op == "shift_letters" and offset > 0 else (
                "A" if rule.op == "shift_letters" else "9" if offset > 0 else "0")
            current = "".join(before if before in boundary else after for before, after in zip(source, shifted))
            for following in path[i+1:]:
                current = _try(following, current) if current else None
            add(current, f"ignored_wrap_at_step_{i+1}")
    rng.shuffle(proposals)
    return proposals[:count-1] if len(proposals) >= count-1 else None


def validate(graph, operator_dictionary, options):
    """Audit geometry, every witness, executable trace, identifiability, and choices."""
    nodes = {n["id"]: n for n in graph["nodes"]}
    size = graph["grid"]["rows"]
    if len(nodes) != len(graph["nodes"]) or graph["grid"]["columns"] != size:
        return False
    if len({tuple(n["cell"]) for n in nodes.values()}) != len(nodes): return False
    if any(not all(0 <= v < size for v in n["cell"]) for n in nodes.values()): return False
    for edge in graph["edges"]:
        if edge["from"] not in nodes or edge["to"] not in nodes or not edge["directed"]: return False
        a, b = nodes[edge["from"]], nodes[edge["to"]]
        if a["section"] != b["section"] or a["section"] != edge["section"]: return False
        ar, ac = a["cell"]; br, bc = b["cell"]
        if ar != br and ac != bc: return False
        if any(n["id"] not in (a["id"], b["id"]) and
               ((ar == br == n["cell"][0] and min(ac, bc) < n["cell"][1] < max(ac, bc)) or
                (ac == bc == n["cell"][1] and min(ar, br) < n["cell"][0] < max(ar, br)))
               for n in nodes.values()): return False
    demo_ids = {n["id"] for n in nodes.values() if n["section"] == "demonstration"}
    neighbors = {node_id: set() for node_id in demo_ids}
    for edge in graph["edges"]:
        if edge["section"] == "demonstration":
            neighbors[edge["from"]].add(edge["to"])
            neighbors[edge["to"]].add(edge["from"])
    for link in graph.get("reuse_links", []):
        a, b = nodes.get(link["from"]), nodes.get(link["to"])
        if (not a or not b or a["id"] not in demo_ids or b["id"] not in demo_ids or
                a["kind"] != "operator" or b["kind"] != "operator" or
                a["value"] != b["value"] or a["value"] != link["rule_id"] or
                a["cell"][1] != b["cell"][1]): return False
        neighbors[a["id"]].add(b["id"])
        neighbors[b["id"]].add(a["id"])
    seen, pending = set(), [next(iter(demo_ids))]
    while pending:
        current = pending.pop()
        if current in seen: continue
        seen.add(current)
        pending.extend(neighbors[current] - seen)
    if seen != demo_ids: return False
    used = set(graph["query"]["operator_ids"])
    if not used <= set(operator_dictionary): return False
    if graph.get("operator_dictionary") != operator_dictionary: return False
    if len({entry["shape"] for entry in operator_dictionary.values()}) != len(operator_dictionary): return False
    if any(n["shape"] != operator_dictionary[n["value"]]["shape"] for n in nodes.values()
           if n["kind"] == "operator"): return False
    actual_edges = {(e["from"], e["to"]) for e in graph["edges"]}
    query_nodes = graph["query"]["node_ids"]
    if any((a, b) not in actual_edges for a, b in zip(query_nodes, query_nodes[1:])): return False
    for rule_id in used:
        witnesses = [d for d in graph["demonstrations"] if d["rule_id"] == rule_id]
        if len(witnesses) < 2: return False
        rule = BY_ID[rule_id]
        if any(_try(rule, d["input"]) != d["output"] or
               [nodes[n]["value"] for n in d["node_ids"]] != [d["input"], rule_id, d["output"]] or
               (d["node_ids"][0], d["node_ids"][1]) not in actual_edges or
               (d["node_ids"][1], d["node_ids"][2]) not in actual_edges
               for d in witnesses): return False
        if any(meaning_id(candidate.id) != meaning_id(rule_id) and all(_try(candidate, d["input"]) == d["output"] for d in witnesses)
               for candidate in RULES): return False
    current = graph["query"]["input"]
    trace = [current]
    for rule_id in graph["query"]["operator_ids"]:
        current = _try(BY_ID[rule_id], current)
        if current is None: return False
        trace.append(current)
    if trace != graph["query"]["trace"] or trace[-1] != graph["query"]["correct_output"]: return False
    return len(options) == len(set(options)) and options.count(current) == 1


def generate_question(type_id, subtype, difficulty, choice_count, number, selected_theme="Mixed", rng=None):
    if difficulty not in ("Easy", "Average", "Challenge") or not 2 <= choice_count <= 6:
        raise ValueError("Unsupported Rule Determining settings")
    rng = rng or random.Random()
    for _ in range(400):
        selected = _query(rng, difficulty)
        if not selected: continue
        path, states = selected
        rules = list(dict.fromkeys(path))
        evidence = {rule.id: _evidence(rule, rng) for rule in rules}
        if any(pairs is None for pairs in evidence.values()): continue
        distractors = _distractors(path, states, choice_count, rng)
        if distractors is None: continue
        shapes = dict(zip((r.id for r in rules), rng.sample(SHAPES, len(rules))))
        graph = _graph(rules, evidence, path, states, shapes,
                       _example_chains(rules, path, states, rng))
        mapping = {rule.id: {**rule.data(), "shape": shapes[rule.id]} for rule in rules}
        graph["operator_dictionary"] = mapping
        tagged = [(states[-1], None)] + distractors
        rng.shuffle(tagged)
        if not validate(graph, mapping, [value for value, _ in tagged]): continue
        break
    else:
        raise RuntimeError("Could not generate an identifiable Rule Determining question")
    choices = [{"id": f"choice-{i+1}", "text": value} for i, (value, _) in enumerate(tagged)]
    correct = next(choice["id"] for choice, (value, _) in zip(choices, tagged) if value == states[-1])
    def rule_words(rule):
        words = rule.id.replace("_", " ")
        if rule.op == "shift_letters": words += " (A/Z wraparound)"
        if rule.op == "shift_digits": words += " (0/9 wraparound)"
        if rule.op in ("remove_neighbor", "insert_neighbor", "duplicate_symbol"):
            words += " (use the first matching anchor)"
        if rule.op in ("letters_to_positions", "positions_to_letters"):
            words += " (two digits per letter)"
        return words
    names = "; ".join(f"{shapes[r.id]}: {rule_words(r)}" for r in rules)
    explanation = f"{names}. Trace: {' → '.join(states)}."
    metadata = {"generator_key": subtype["generator_key"], "transformation_graph": graph,
                "operator_dictionary": mapping, "demonstration_traces": graph["demonstrations"],
                "query_path": graph["query"]["operator_ids"], "intermediate_states": states[1:-1],
                "correct_output": states[-1],
                "distractor_misconceptions": {choice["id"]: error for choice, (_, error) in zip(choices, tagged) if error},
                "difficulty_score": len(rules) + len(path),
                "validation": {"identifiable": True, "executable": True, "unique_answer": True}}
    return {"id": f"{subtype['id']}-{number}", "reasoning_type": type_id,
            "subtype": subtype["id"], "difficulty": difficulty,
            "text": "Infer what each shape does from the connected examples. Dashed lines link repeated shapes. Follow the arrows in the question diagram. What replaces ?",
            "figures": [render_section(graph, "demonstration"), render_section(graph, "query")], "choices": choices,
            "correct_answer_id": correct, "explanation": explanation, "metadata": metadata}
