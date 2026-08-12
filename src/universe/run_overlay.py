"""Shared newest-usable overlay semantics for append-only model runs."""

from __future__ import annotations

from collections.abc import Callable


def fold_newest_usable(
    rows: list[tuple],
    usable: Callable[[dict], object | None],
) -> tuple[dict, set, tuple]:
    """Choose the newest parseable answer per unit, falling through failures."""
    answers: dict[str, dict] = {}
    attempted: set[str] = set()
    newest = (None, None, None)
    for unit_id, item_id, response, error, run_id, model, prompt_ref in rows:
        if newest[0] is None:
            newest = (run_id, model, prompt_ref)
        attempted.add(unit_id)
        if unit_id in answers:
            continue
        parsed = usable({"response": response, "error": error})
        if parsed is not None:
            answers[unit_id] = {
                "answer": parsed,
                "item_id": item_id,
                "run_id": run_id,
            }
    return answers, attempted, newest
