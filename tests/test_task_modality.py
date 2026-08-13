"""The observable task-modality verdict contract; no model or transport."""

from universe.task_modality import modality_of


def test_modality_verdicts_are_normalized_and_invalid_answers_fail_closed():
    assert modality_of({"error": "HTTP 502", "response": None}) == "error"
    for response in (
        "prose, not a tool call",
        "[]",
        '{"verdict": "important", "reason": "Not a modality verdict."}',
        '{"verdict": "do"}',
        '{"verdict": "explain", "reason": ""}',
        '{"verdict": "unsure", "reason": "  "}',
    ):
        assert modality_of({"error": None, "response": response}) == "unparseable"
    for verdict in ("do", "explain", "unsure"):
        item = {
            "error": None,
            "response": (
                f'{{"verdict": "{verdict}",'
                ' "reason": "  The requested action determines the modality.  "}'
            ),
        }
        assert modality_of(item) == {
            "verdict": verdict,
            "reason": "The requested action determines the modality.",
        }
