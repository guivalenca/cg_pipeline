"""Shared parsing for task-axis verdicts that require a nonblank reason."""

from __future__ import annotations

import json
from collections.abc import Set


def parse_reasoned_verdict(item: dict, verdicts: Set[str]) -> dict | str:
    """Return one normalized verdict or the observable failure category."""
    if item["error"]:
        return "error"
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(parsed, dict) or parsed.get("verdict") not in verdicts:
        return "unparseable"
    reason = parsed.get("reason")
    if not isinstance(reason, str) or not (reason := reason.strip()):
        return "unparseable"
    return {"verdict": parsed["verdict"], "reason": reason}
