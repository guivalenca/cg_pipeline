"""Public recipe contract for the task support gate."""

from universe.recipe_identity import launch_recipe


def test_task_triage_recipe_uses_flash_with_low_thinking():
    launch = launch_recipe("task-triage")

    assert launch["model"] == "deepseek/deepseek-v4-flash"
    assert launch["extra"]["thinking"] == {"type": "enabled"}
    assert launch["extra"]["reasoning_effort"] == "low"
