"""Tool-call extraction, the blocks body, and the cut checks: all pure."""

import json

import pytest

from universe import cuts
from universe.model_client import ModelError, extract_text


def tool_response(*arguments: str) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "report_cuts", "arguments": args}}
                        for args in arguments
                    ],
                }
            }
        ]
    }


def test_a_tool_call_yields_its_raw_arguments():
    assert extract_text(tool_response('{"cuts": [4, 9]}')) == '{"cuts": [4, 9]}'


def test_more_than_one_tool_call_is_an_error():
    with pytest.raises(ModelError, match="expected one tool call, got 2"):
        extract_text(tool_response('{"cuts": [2]}', '{"cuts": [3]}'))


def test_a_tool_call_without_arguments_is_an_error():
    with pytest.raises(ModelError, match="without arguments"):
        extract_text(tool_response(""))


def test_plain_text_responses_still_come_through():
    assert extract_text({"choices": [{"message": {"content": "hi"}}]}) == "hi"


def test_prose_when_a_tool_was_declared_is_an_error():
    body = {"choices": [{"message": {"content": "The cuts are 4 and 9."}}]}
    with pytest.raises(ModelError, match="prose instead of the declared tool call"):
        extract_text(body, require_tool=True)


def test_cuts_parse_and_reject_non_integers():
    assert cuts.parse_cuts('{"cuts": [3, 7]}') == [3, 7]
    with pytest.raises(ValueError):
        cuts.parse_cuts('{"cuts": ["3"]}')
    with pytest.raises(json.JSONDecodeError):
        cuts.parse_cuts("not json")


def test_every_contract_deviation_is_named():
    seqs = list(range(1, 11))
    assert cuts.check_cuts([4, 9], seqs) == []
    assert cuts.check_cuts([9, 4], seqs) == ["not ascending"]
    assert cuts.check_cuts([4, 4], seqs) == ["duplicates"]
    assert cuts.check_cuts([1, 4], seqs) == ["includes the first block (1)"]
    assert cuts.check_cuts([4, 40], seqs) == ["outside the block range: [40]"]


def test_repair_keeps_the_nearest_valid_reading():
    seqs = list(range(1, 11))
    assert cuts.repair_cuts([9, 4, 4, 1, 40], seqs) == [4, 9]
    assert cuts.repair_cuts([2], []) == []


def test_cuts_become_covering_ranges():
    seqs = list(range(1, 11))
    assert cuts.passage_ranges([4, 9], seqs) == [(1, 3), (4, 8), (9, 10)]
    assert cuts.passage_ranges([], seqs) == [(1, 10)]
    assert cuts.passage_ranges([], []) == []
