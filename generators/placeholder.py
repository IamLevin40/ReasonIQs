"""Temporary, deterministic questions following the future generator contract."""


def generate_placeholder_session(type_id: str, subtype: dict, difficulty: str, item_count: int, choice_count: int) -> list[dict]:
    questions = []
    for index in range(item_count):
        number = index + 1
        choices = [
            {"id": f"choice-{option + 1}", "text": f"Placeholder choice {option + 1}"}
            for option in range(choice_count)
        ]
        questions.append({
            "id": f"{subtype['id']}-{number}",
            "reasoning_type": type_id,
            "subtype": subtype["id"],
            "difficulty": difficulty,
            "prompt": f"Placeholder {subtype['title']} question {number}. Select one of the temporary choices below.",
            "visual": None,
            "diagram_data": None,
            "choices": choices,
            "correct_answer_id": choices[index % choice_count]["id"],
            "explanation": "This is a temporary placeholder. A procedural explanation will appear here in a later version.",
            "metadata": {"placeholder": True, "generator_key": subtype["generator_key"], "sequence": number},
        })
    return questions
