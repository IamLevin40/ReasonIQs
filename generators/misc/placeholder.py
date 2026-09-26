"""Temporary, deterministic questions following the future generator contract."""


def sample_figure(shape: str, label: str) -> dict:
    """Small local SVG examples exercise the visual contract until real generators arrive."""
    forms = {
        "circle": '<circle cx="120" cy="70" r="37" fill="#9bdcca" stroke="#254b51" stroke-width="5"/>',
        "square": '<rect x="83" y="33" width="74" height="74" rx="7" fill="#ffd187" stroke="#254b51" stroke-width="5"/>',
        "triangle": '<polygon points="120,28 164,107 76,107" fill="#b5c6eb" stroke="#254b51" stroke-width="5"/>',
    }
    return {
        "kind": "svg",
        "svg": f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 140"><rect width="240" height="140" fill="#ffffff"/>{forms[shape]}</svg>',
        "alt": label,
    }


def generate_placeholder_session(type_id: str, subtype: dict, difficulty: str, item_count: int, choice_count: int) -> list[dict]:
    questions = []
    for index in range(item_count):
        number = index + 1
        choices = [
            {"id": f"choice-{option + 1}", "text": f"Placeholder choice {option + 1}"}
            for option in range(choice_count)
        ]
        if index == 0:
            for option, choice in enumerate(choices):
                choice.pop("text")
                choice["figures"] = [sample_figure(("circle", "square", "triangle")[option % 3], f"Prototype {('circle', 'square', 'triangle')[option % 3]} option")]
        elif index == 2:
            choices[0]["figures"] = [sample_figure("triangle", "Prototype triangle beside choice text")]
        question_figures = (
            [sample_figure("circle", "First prototype diagram"), sample_figure("square", "Second prototype diagram")]
            if index == 0 else [sample_figure("triangle", "Prototype triangle question diagram")]
            if index == 1 else []
        )
        questions.append({
            "id": f"{subtype['id']}-{number}",
            "reasoning_type": type_id,
            "subtype": subtype["id"],
            "difficulty": difficulty,
            "text": "" if index == 1 else f"Placeholder {subtype['title']} question {number}. Select one of the temporary choices below.",
            "figures": question_figures,
            "choices": choices,
            "correct_answer_id": choices[index % choice_count]["id"],
            "explanation": "This is a temporary placeholder. A procedural explanation will appear here in a later version.",
            "metadata": {"placeholder": True, "generator_key": subtype["generator_key"], "sequence": number},
        })
    return questions
