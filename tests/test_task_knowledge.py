"""The observable task-knowledge verdict contract; no model or transport."""

from universe.task_knowledge import knowledge_of


def test_knowledge_verdicts_are_normalized_and_invalid_answers_fail_closed():
    assert knowledge_of({"error": "HTTP 502", "response": None}) == "error"
    for response in (
        "prose, not a tool call",
        "[]",
        '{"verdict": "skill", "reason": "Not a knowledge verdict."}',
        '{"verdict": "fact"}',
        '{"verdict": "concept", "reason": ""}',
        '{"verdict": "procedure", "reason": "  "}',
    ):
        assert knowledge_of({"error": None, "response": response}) == "unparseable"
    for verdict in ("fact", "concept", "procedure", "unsure"):
        item = {
            "error": None,
            "response": (
                f'{{"verdict": "{verdict}",'
                ' "reason": "  The requested response determines the knowledge kind.  "}'
            ),
        }
        assert knowledge_of(item) == {
            "verdict": verdict,
            "reason": "The requested response determines the knowledge kind.",
        }
