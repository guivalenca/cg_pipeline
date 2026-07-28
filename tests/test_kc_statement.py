"""The kc-statement parser; no model, no transport."""

import pytest

from universe.kc_statement import statement_of


def test_an_errored_item_is_an_error():
    assert statement_of({"error": "HTTP 502", "response": None}) == "error"


@pytest.mark.parametrize(
    "response",
    [
        "prose, not a tool call",
        "[]",
        '{"verdict": "important"}',
    ],
)
def test_a_nonobject_or_bad_verdict_is_unparseable(response):
    assert statement_of({"error": None, "response": response}) == "unparseable"


@pytest.mark.parametrize(
    "response",
    [
        '{"verdict": "stated"}',
        '{"verdict": "stated", "statement": ""}',
        '{"verdict": "stated", "statement": "  "}',
        '{"verdict": "stated", "statement": 42}',
    ],
)
def test_stated_without_a_nonblank_statement_is_unparseable(response):
    assert statement_of({"error": None, "response": response}) == "unparseable"


def test_a_stated_item_carries_its_statement():
    item = {
        "error": None,
        "response": '{"verdict": "stated", "statement": "The learner can explain stopwords."}',
    }
    assert statement_of(item) == {
        "verdict": "stated",
        "statement": "The learner can explain stopwords.",
    }


def test_an_unsure_item_needs_no_reason():
    item = {"error": None, "response": '{"verdict": "unsure"}'}
    assert statement_of(item) == {"verdict": "unsure"}


def test_an_unsure_item_carries_a_nonblank_reason():
    item = {
        "error": None,
        "response": '{"verdict": "unsure", "reason": "The expected skill is ambiguous."}',
    }
    assert statement_of(item) == {
        "verdict": "unsure",
        "reason": "The expected skill is ambiguous.",
    }


def test_delivered_statement_and_reason_are_stripped():
    stated = {
        "error": None,
        "response": '{"verdict": "stated", "statement": "  The learner can compare methods.  "}',
    }
    unsure = {
        "error": None,
        "response": '{"verdict": "unsure", "reason": "  It asks two things.  "}',
    }
    assert statement_of(stated)["statement"] == "The learner can compare methods."
    assert statement_of(unsure)["reason"] == "It asks two things."


def test_a_blank_unsure_reason_is_omitted():
    item = {
        "error": None,
        "response": '{"verdict": "unsure", "reason": "  "}',
    }
    assert statement_of(item) == {"verdict": "unsure"}
