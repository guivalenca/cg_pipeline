"""The refinement prompt asks one judgment and the tool only locates elements."""

from pathlib import Path

from universe.harness import load_prompt, load_tool


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts" / "passage-refine"


def test_refine_prompt_is_the_approved_simple_question():
    prompt = load_prompt("passage-refine", "v002", require_body=False)
    assert prompt.template == (
        "You will read a passage split into numbered elements.\n\n"
        "Use the report_element_removals tool to report which elements should be "
        "removed in order to improve passage quality and retain relevant teachable "
        "content.\n\n"
        "<passage>\n{{passage}}\n</passage>\n"
    )


def test_refine_tool_reports_only_element_numbers_and_allows_no_removal():
    payload = load_tool(str(PROMPTS_DIR / "tool-v002.json"))
    function = payload["tools"][0]["function"]
    assert function["name"] == "report_element_removals"
    properties = function["parameters"]["properties"]
    assert set(properties) == {"drop_elements"}
    drop_elements = properties["drop_elements"]
    assert drop_elements["items"] == {"type": "integer", "minimum": 1}
    assert "minItems" not in drop_elements

