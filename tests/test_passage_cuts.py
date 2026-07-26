"""Tool-call extraction, the blocks body, and the cut checks: all pure."""

import json
from pathlib import Path

import pytest

from universe import passage_report
from universe.harness import load_tool
from universe.model_client import ModelError, extract_text

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


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


def test_the_versioned_tool_file_loads_as_a_forcing_payload():
    payload = load_tool(str(PROMPTS_DIR / "passage-cuts" / "tool-v001.json"))
    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "report_cuts"
    assert payload["tool_choice"] == {"type": "function", "function": {"name": "report_cuts"}}
    assert "cuts" in payload["tools"][0]["function"]["parameters"]["properties"]


def test_the_prompt_file_has_the_placeholder_inside_source_tags():
    text = (PROMPTS_DIR / "passage-cuts" / "v001.md").read_text()
    assert "<source>\n{{body}}\n</source>" in text
    assert "report_cuts" in text


def test_cuts_parse_and_reject_non_integers():
    assert passage_report.parse_cuts('{"cuts": [3, 7]}') == [3, 7]
    with pytest.raises(ValueError):
        passage_report.parse_cuts('{"cuts": ["3"]}')
    with pytest.raises(json.JSONDecodeError):
        passage_report.parse_cuts("not json")


def test_every_contract_deviation_is_named():
    seqs = list(range(1, 11))
    assert passage_report.check_cuts([4, 9], seqs) == []
    assert passage_report.check_cuts([9, 4], seqs) == ["not ascending"]
    assert passage_report.check_cuts([4, 4], seqs) == ["duplicates"]
    assert passage_report.check_cuts([1, 4], seqs) == ["includes the first block (1)"]
    assert passage_report.check_cuts([4, 40], seqs) == ["outside the block range: [40]"]


def test_repair_keeps_the_nearest_valid_reading():
    seqs = list(range(1, 11))
    assert passage_report.repair_cuts([9, 4, 4, 1, 40], seqs) == [4, 9]
    assert passage_report.repair_cuts([2], []) == []


def test_cuts_become_covering_ranges():
    seqs = list(range(1, 11))
    assert passage_report.passage_ranges([4, 9], seqs) == [(1, 3), (4, 8), (9, 10)]
    assert passage_report.passage_ranges([], seqs) == [(1, 10)]
    assert passage_report.passage_ranges([], []) == []
