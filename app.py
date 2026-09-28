"""ReasonIQs application and structured practice API."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from generators import generate_session
from generators.spatial.misc.cube_figures import THEMES

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "reasoning_types.json"
app = Flask(__name__)


def load_catalog() -> dict:
    """Read the editable catalog on request, so development edits need no restart."""
    with DATA_FILE.open(encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("types"), list):
        raise ValueError("Reasoning catalog has an invalid structure")
    type_ids = set()
    subtype_ids = set()
    for reasoning_type in catalog["types"]:
        if not isinstance(reasoning_type, dict) or not all(
            isinstance(reasoning_type.get(key), str) and reasoning_type[key]
            for key in ("id", "title", "subtitle", "icon", "accent")
        ) or not isinstance(reasoning_type.get("active"), bool) or not isinstance(reasoning_type.get("subtypes"), list):
            raise ValueError("Reasoning catalog has an invalid type")
        if reasoning_type["id"] in type_ids:
            raise ValueError("Reasoning catalog has duplicate type IDs")
        type_ids.add(reasoning_type["id"])
        for subtype in reasoning_type["subtypes"]:
            if not isinstance(subtype, dict) or not all(
                isinstance(subtype.get(key), str) and subtype[key]
                for key in ("id", "parent_id", "title", "subtitle", "description", "icon", "generator_key")
            ) or not isinstance(subtype.get("active"), bool) or not isinstance(subtype.get("difficulties"), list):
                raise ValueError("Reasoning catalog has an invalid subtype")
            if subtype["id"] in subtype_ids or subtype["parent_id"] != reasoning_type["id"]:
                raise ValueError("Reasoning catalog has inconsistent subtype IDs")
            if any(level not in ("Easy", "Average", "Challenge") for level in subtype["difficulties"]):
                raise ValueError("Reasoning catalog has an invalid difficulty")
            subtype_ids.add(subtype["id"])
    return catalog


def error_response(message: str, status: int):
    return jsonify({"error": message}), status


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/reasoning")
def reasoning_catalog():
    try:
        return jsonify(load_catalog())
    except (OSError, ValueError, json.JSONDecodeError):
        app.logger.exception("Unable to load reasoning catalog")
        return error_response("Reasoning areas could not be loaded. Please retry.", 503)


@app.post("/api/practice")
def create_practice():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("Please provide valid practice settings.", 400)

    try:
        catalog = load_catalog()
    except (OSError, ValueError, json.JSONDecodeError):
        app.logger.exception("Unable to load reasoning catalog")
        return error_response("Practice areas are temporarily unavailable. Please retry.", 503)

    type_id = payload.get("type_id")
    subtype_id = payload.get("subtype_id")
    reasoning_type = next((item for item in catalog["types"] if item.get("id") == type_id and item.get("active")), None)
    subtype = next((item for item in reasoning_type.get("subtypes", []) if item.get("id") == subtype_id and item.get("active")), None) if reasoning_type else None
    if not subtype:
        return error_response("Select an available reasoning subtype.", 400)

    item_count = payload.get("item_count")
    choice_count = payload.get("choice_count")
    timer_enabled = payload.get("timer_enabled")
    seconds_per_item = payload.get("seconds_per_item")
    difficulty = payload.get("difficulty")
    theme = payload.get("theme", "Mixed")
    puzzle_type = payload.get("puzzle_type", "Mixed")
    if not isinstance(item_count, int) or isinstance(item_count, bool) or not 5 <= item_count <= 50:
        return error_response("Choose between 5 and 50 items.", 400)
    if not isinstance(choice_count, int) or isinstance(choice_count, bool) or not 2 <= choice_count <= 6:
        return error_response("Choose between 2 and 6 answer choices.", 400)
    if not isinstance(timer_enabled, bool):
        return error_response("Choose whether to use an item timer.", 400)
    if not isinstance(seconds_per_item, int) or isinstance(seconds_per_item, bool) or not 10 <= seconds_per_item <= 300:
        return error_response("Choose a timer duration between 10 and 300 seconds.", 400)
    if difficulty not in ("Easy", "Average", "Challenge") or difficulty not in subtype.get("difficulties", []):
        return error_response("Choose an available difficulty.", 400)
    if subtype["generator_key"] in ("spatial.dice_folding", "spatial.dice_unfolding") and theme not in ("Mixed", *THEMES):
        return error_response("Choose an available cube marking theme.", 400)
    if subtype["generator_key"] == "spatial.pattern_finding" and puzzle_type not in ("Linear", "Matrix", "Mixed"):
        return error_response("Choose an available puzzle type.", 400)

    questions = generate_session(type_id, subtype, difficulty, item_count, choice_count, theme, puzzle_type)
    return jsonify({"questions": questions, "placeholder": all(question["metadata"].get("placeholder", False) for question in questions)})


if __name__ == "__main__":
    app.run(debug=True)
