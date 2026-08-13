"""The task-modality parser; no model, no transport."""

import pytest

from universe.task_modality import DEFAULT_WORKERS, modality_of


def test_task_modality_is_serial_to_avoid_provider_rate_limit_bursts():
    assert DEFAULT_WORKERS == 1


def test_an_errored_item_is_an_error():
    assert modality_of({"error": "HTTP 502", "response": None}) == "error"


@pytest.mark.parametrize(
    "response",
    [
        "prose, not a tool call",
        "[]",
        '{"verdict": "important", "reason": "Not a modality verdict."}',
        '{"verdict": "do"}',
        '{"verdict": "explain", "reason": ""}',
        '{"verdict": "unsure", "reason": "  "}',
    ],
)
def test_an_invalid_response_is_unparseable(response):
    assert modality_of({"error": None, "response": response}) == "unparseable"


@pytest.mark.parametrize("verdict", ["do", "explain", "unsure"])
def test_every_verdict_carries_a_stripped_reason(verdict):
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
