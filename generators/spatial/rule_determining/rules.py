"""Pure, parameterized string transformations.

Positions are zero based internally. Undefined and invisible applications raise
ValueError, so the generator never silently changes a rule's meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
import string

LETTERS = string.ascii_uppercase
DIGITS = string.digits
VOWELS = frozenset("AEIOU")


@dataclass(frozen=True)
class Rule:
    id: str
    op: str
    args: tuple = ()
    level: int = 0

    def data(self):
        data = {"id": self.id, "operation": self.op, "parameters": list(self.args),
                "difficulty_tier": self.level, "position_indexing": "zero_based"}
        if self.op == "shift_letters": data["wrap_rule"] = "Alphabet positions wrap modulo 26: Z to A and A to Z"
        if self.op == "shift_digits": data["wrap_rule"] = "Each digit wraps modulo 10: 9 to 0 and 0 to 9"
        if self.op in ("remove_neighbor", "insert_neighbor", "duplicate_symbol"):
            data["anchor_occurrence"] = "first"
        if self.op in ("letters_to_positions", "positions_to_letters"):
            data["position_format"] = "fixed_width_two_digits_per_letter"
        return data

    def apply(self, value: str) -> str:
        if not value or len(value) > 12 or any(c not in LETTERS + DIGITS for c in value):
            raise ValueError("Input must be a short uppercase alphanumeric string")
        out = transform(self.op, self.args, value)
        if not out or out == value or len(out) > 12 or any(c not in LETTERS + DIGITS for c in out):
            raise ValueError("Undefined, invisible, or unreadable transformation")
        return out


def _index(s: str, target):
    if target == "first": return 0
    if target == "last": return len(s) - 1
    if target == "middle":
        if len(s) % 2 != 1: raise ValueError("No single middle character")
        return len(s) // 2
    if isinstance(target, int) and 0 <= target < len(s): return target
    raise ValueError("Position unavailable")


def _condition(c: str, kind: str) -> bool:
    conditions = {"letter": c.isalpha(), "digit": c.isdigit(),
            "vowel": c in VOWELS, "consonant": c.isalpha() and c not in VOWELS,
            "odd_digit": c.isdigit() and int(c) % 2 == 1,
            "even_digit": c.isdigit() and int(c) % 2 == 0}
    if kind not in conditions: raise ValueError("Unknown character condition")
    return conditions[kind]


def transform(op: str, args: tuple, s: str) -> str:
    """Apply a named operation; raise ValueError for missing anchors/positions."""
    if op == "remove_at":
        i = _index(s, args[0]); return s[:i] + s[i+1:]
    if op == "remove_occurrence":
        anchor, which = args
        if anchor not in s: raise ValueError("Missing character")
        if which == "all": return s.replace(anchor, "")
        i = s.index(anchor) if which == "first" else s.rindex(anchor)
        return s[:i] + s[i+1:]
    if op == "remove_neighbor":
        anchor, side = args
        if anchor not in s: raise ValueError("Missing anchor")
        i = s.index(anchor) + (-1 if side == "before" else 1)
        if not 0 <= i < len(s): raise ValueError("Missing neighbor")
        return s[:i] + s[i+1:]
    if op == "remove_matching":
        return "".join(c for c in s if not _condition(c, args[0]))
    if op == "remove_duplicates":
        return "".join(c for i, c in enumerate(s) if c not in s[:i])
    if op == "insert_at":
        where, c = args
        i = 0 if where == "first" else len(s) if where == "last" else len(s)//2 if where == "center" else where
        if not 0 <= i <= len(s): raise ValueError("Position unavailable")
        return s[:i] + c + s[i:]
    if op == "insert_neighbor":
        anchor, side, c = args
        if anchor not in s: raise ValueError("Missing anchor")
        i = s.index(anchor) + (side == "after")
        return s[:i] + c + s[i:]
    if op == "insert_between_all":
        if len(s) < 2: raise ValueError("Too short")
        return args[0].join(s)
    if op == "insert_between_selected":
        left, right, c = args
        i = s.find(left + right)
        if i < 0: raise ValueError("Missing adjacent pair")
        return s[:i+1] + c + s[i+1:]
    if op == "duplicate_at":
        i = _index(s, args[0]); return s[:i+1] + s[i] + s[i+1:]
    if op == "duplicate_symbol":
        c = args[0]
        if c not in s: raise ValueError("Missing character")
        i = s.index(c); return s[:i+1] + c + s[i+1:]
    if op == "replace_at":
        i = _index(s, args[0]); return s[:i] + args[1] + s[i+1:]
    if op == "replace_symbol":
        old, new, which = args
        if old not in s: raise ValueError("Missing character")
        return s.replace(old, new) if which == "all" else s.replace(old, new, 1)
    if op == "map_symbols":
        mapping = dict(args[0]); return "".join(mapping.get(c, c) for c in s)
    if op == "reverse": return s[::-1]
    if op == "swap_ends": return s[-1] + s[1:-1] + s[0] if len(s) >= 2 else s
    if op == "swap_positions":
        i, j = args
        if max(i, j) >= len(s) or min(i, j) < 0: raise ValueError("Position unavailable")
        chars = list(s); chars[i], chars[j] = chars[j], chars[i]; return "".join(chars)
    if op == "swap_adjacent":
        return "".join(s[i:i+2][::-1] for i in range(0, len(s), 2))
    if op == "move":
        where, to = args; i = _index(s, where)
        remainder = s[:i] + s[i+1:]
        return (s[i] + remainder) if to == "front" else (remainder + s[i])
    if op == "rotate":
        side, k = args; k %= len(s)
        return s[k:] + s[:k] if side == "left" else s[-k:] + s[:-k]
    if op == "reverse_half":
        if len(s) % 2: raise ValueError("Halves must be equal")
        mid = len(s)//2
        return s[:mid][::-1] + s[mid:] if args[0] == "first" else s[:mid] + s[mid:][::-1]
    if op == "exchange_halves":
        if len(s) % 2: raise ValueError("Halves must be equal")
        mid = len(s)//2; return s[mid:] + s[:mid]
    if op == "odd_even": return s[::2] + s[1::2]
    if op == "shift_letters":
        offset, selected = args
        if not any(c.isalpha() and (selected is None or c == selected) for c in s):
            raise ValueError("No matching letter")
        return "".join(LETTERS[(LETTERS.index(c)+offset)%26] if c.isalpha() and (selected is None or c == selected) else c for c in s)
    if op == "shift_digits":
        offset = args[0]
        if not any(c.isdigit() for c in s): raise ValueError("No digits")
        return "".join(str((int(c)+offset)%10) if c.isdigit() else c for c in s)
    if op == "letters_to_positions":
        if not s.isalpha(): raise ValueError("Letters only")
        return "".join(f"{LETTERS.index(c)+1:02d}" for c in s)
    if op == "positions_to_letters":
        if not s.isdigit() or len(s)%2: raise ValueError("Two-digit positions only")
        pairs = [int(s[i:i+2]) for i in range(0, len(s), 2)]
        if not all(1 <= n <= 26 for n in pairs): raise ValueError("Invalid alphabet position")
        return "".join(LETTERS[n-1] for n in pairs)
    if op == "add_derived":
        side, kind = args
        count = len(s) if kind == "length" else sum(_condition(c, kind) for c in s)
        return str(count) + s if side == "front" else s + str(count)
    if op == "retain_matching": return "".join(c for c in s if _condition(c, args[0]))
    if op == "repeat_substring":
        start, length = args
        if start < 0 or start+length > len(s): raise ValueError("Substring unavailable")
        return s + s[start:start+length]
    raise ValueError(f"Unknown operation: {op}")


def _r(op, *args, level=0, name=None):
    label = name or op + ("_" + "_".join(map(str, args)) if args else "")
    return Rule(label, op, args, level)


# Registered concrete rules form the inference vocabulary. The engine above
# also accepts other valid parameters without requiring a fixed question bank.
RULES = [
    _r("remove_at", "first", name="remove_first"), _r("remove_at", "last", name="remove_last"),
    _r("remove_at", 1, name="remove_second", level=1), _r("remove_at", "middle", name="remove_middle", level=1),
    _r("remove_occurrence", "A", "first", name="remove_first_A", level=1),
    _r("remove_occurrence", "A", "last", name="remove_last_A", level=1),
    _r("remove_occurrence", "A", "all", name="remove_all_A", level=1),
    _r("remove_neighbor", "A", "before", name="remove_before_A", level=2),
    _r("remove_neighbor", "A", "after", name="remove_after_A", level=2),
    *[_r("remove_matching", kind, name="remove_"+kind, level=2) for kind in
      ("letter", "digit", "vowel", "consonant", "odd_digit", "even_digit")],
    _r("remove_duplicates", level=2),
    *[_r("insert_at", where, "E", name="insert_E_"+str(where), level=0 if where in ("first", "last") else 1)
      for where in ("first", "last", 1, "center")],
    _r("insert_neighbor", "A", "before", "E", name="insert_E_before_A", level=1),
    _r("insert_neighbor", "A", "after", "E", name="insert_E_after_A", level=1),
    _r("insert_between_all", "E", name="insert_E_between_all", level=2),
    _r("insert_between_selected", "A", "B", "E", name="insert_E_between_AB", level=2),
    *[_r("duplicate_at", where, name="duplicate_"+str(where), level=1) for where in ("first", "last", 1)],
    _r("duplicate_symbol", "A", name="duplicate_A", level=1),
    *[_r("replace_at", where, "E", name="replace_"+str(where)+"_with_E", level=1) for where in ("first", "last", 1)],
    _r("replace_symbol", "A", "E", "all", name="replace_all_A_with_E", level=1),
    _r("replace_symbol", "A", "E", "first", name="replace_first_A_with_E", level=2),
    _r("map_symbols", (("A", "E"), ("B", "F")), name="map_AE_BF", level=2),
    _r("map_symbols", (("1", "7"), ("2", "8")), name="map_1to7_2to8", level=2),
    _r("reverse"), _r("swap_ends", level=1), _r("swap_positions", 1, 3, level=2),
    _r("swap_adjacent", level=2),
    _r("move", "first", "back", name="move_first_back", level=1),
    _r("move", "last", "front", name="move_last_front", level=1),
    _r("move", 1, "front", name="move_second_front", level=2),
    _r("move", 1, "back", name="move_second_back", level=2),
    _r("rotate", "left", 2, name="rotate_left_2", level=2),
    _r("rotate", "right", 2, name="rotate_right_2", level=2),
    _r("reverse_half", "first", level=2), _r("reverse_half", "second", level=2),
    _r("exchange_halves", level=2), _r("odd_even", level=2),
    _r("shift_letters", 1, None, name="shift_letters_plus_1", level=2),
    _r("shift_letters", -1, None, name="shift_letters_minus_1", level=2),
    _r("shift_letters", 2, None, name="shift_letters_plus_2", level=2),
    _r("shift_letters", 1, "A", name="shift_A_plus_1", level=2),
    _r("shift_digits", 1, name="shift_digits_plus_1", level=2),
    _r("shift_digits", -1, name="shift_digits_minus_1", level=2),
    _r("letters_to_positions", level=2), _r("positions_to_letters", level=2),
    *[_r("add_derived", side, kind, name="add_"+kind+"_"+side, level=2)
      for side in ("front", "back") for kind in ("length", "letter", "digit", "vowel")],
    *[_r("retain_matching", kind, name="retain_"+kind, level=2) for kind in
      ("letter", "digit", "vowel", "consonant", "odd_digit", "even_digit")],
    _r("repeat_substring", 0, 2, name="repeat_first_two", level=2),
]
BY_ID = {rule.id: rule for rule in RULES}

# These pairs are identical functions over uppercase alphanumeric strings.
# No demonstration can distinguish two names for the same transformation.
EQUIVALENT_IDS = {"retain_digit": "remove_letter", "retain_letter": "remove_digit"}


def meaning_id(rule_id: str) -> str:
    return EQUIVALENT_IDS.get(rule_id, rule_id)
