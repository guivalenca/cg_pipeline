"""Ordered creation stages available to the per-Lesson build worker.

DEV-76 deliberately ships an empty registry. Later slices add Stage plans here
without changing the durable build, work, claim, lease, or worker interfaces.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StagePlan:
    name: str
    module: str


_STAGES: tuple[StagePlan, ...] = ()


def registered_stages() -> tuple[StagePlan, ...]:
    """Return the immutable ordered registry used by Lesson workers."""
    return _STAGES


def next_stage(*, completed: tuple[str, ...]) -> StagePlan | None:
    """Return the first registered stage not present in ``completed``."""
    done = set(completed)
    return next((stage for stage in _STAGES if stage.name not in done), None)
