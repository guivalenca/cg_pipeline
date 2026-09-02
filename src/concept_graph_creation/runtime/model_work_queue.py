from __future__ import annotations

import concurrent.futures
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence, TypeVar, cast


WorkItem = TypeVar("WorkItem")
WorkResult = TypeVar("WorkResult")


class ModelWorkCancelled(RuntimeError):
    """Internal cooperative cancellation raised after terminal sibling failure."""


@dataclass(frozen=True)
class ModelWorkControl:
    """Cooperative stop signal shared by model work that is already running."""

    _stop_event: threading.Event

    @property
    def stop_requested(self) -> bool:
        return self._stop_event.is_set()

    def wait_for_stop(self, timeout: float) -> bool:
        """Wait up to ``timeout`` seconds, returning early when sibling work fails."""

        return self._stop_event.wait(timeout=max(0.0, timeout))

    def raise_if_stopped(self) -> None:
        if self.stop_requested:
            raise ModelWorkCancelled("model work stopped after terminal sibling failure")


@dataclass(frozen=True)
class ModelWorkActivity:
    """Safe coordinator snapshot for progress reporting.

    Work items are deliberately represented only by their input indexes. Callers may map those
    indexes to stage-safe identifiers without passing prompts or provider payloads downstream.
    """

    completed_count: int
    total_count: int
    active_item_indexes: tuple[int, ...]
    queued_count: int

    @property
    def active_count(self) -> int:
        return len(self.active_item_indexes)


def safe_model_work_activity(
    activity: ModelWorkActivity,
    *,
    item_type: str,
    item_ids: Sequence[str],
) -> dict[str, object]:
    """Map an activity snapshot to the stable, non-sensitive progress schema."""

    if len(item_ids) != activity.total_count:
        raise ValueError("item_ids must describe every queued work item")
    return {
        "current": activity.completed_count,
        "total": activity.total_count,
        "active_item_count": activity.active_count,
        "active_items": [
            {"item_type": item_type, "item_id": str(item_ids[index])}
            for index in activity.active_item_indexes
        ],
        "queued_item_count": activity.queued_count,
    }


def format_active_model_work(activity: dict[str, object], *, limit: int = 3) -> str:
    """Render a concise status from safe item identifiers only."""

    active_items = activity.get("active_items")
    if not isinstance(active_items, list) or not active_items:
        return ""
    labels: list[str] = []
    for item in active_items[: max(1, limit)]:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("item_type") or "Item")
        item_id = str(item.get("item_id") or "").strip()
        labels.append(f"{item_type} {item_id}".strip())
    active_count = int(activity.get("active_item_count") or len(active_items))
    hidden_count = max(0, active_count - len(labels))
    hidden_suffix = f" +{hidden_count}" if hidden_count else ""
    return f"em andamento ({active_count}): {', '.join(labels)}{hidden_suffix}"


def run_bounded_model_work(
    items: Iterable[WorkItem],
    *,
    worker: Callable[[WorkItem, ModelWorkControl], WorkResult],
    concurrency: int,
    on_result: Callable[[WorkResult, int, int], None] | None = None,
    on_activity: Callable[[ModelWorkActivity], None] | None = None,
) -> list[WorkResult]:
    """Run independent model work with bounded submission and fail-fast cancellation.

    At most ``concurrency`` items are submitted at once. After the first exception, items that
    have not started are cancelled, no later items are submitted, and already-running work is
    allowed to leave its HTTP call safely before the original exception is propagated.
    """

    work_items = list(items)
    if not work_items:
        return []

    worker_count = max(1, concurrency)
    stop_event = threading.Event()
    control = ModelWorkControl(stop_event)
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=worker_count)
    active: dict[concurrent.futures.Future[WorkResult], int] = {}
    results: list[WorkResult | None] = [None] * len(work_items)
    next_index = 0
    completed_count = 0
    terminal_error: BaseException | None = None

    def submit_available() -> None:
        nonlocal next_index
        while not control.stop_requested and next_index < len(work_items) and len(active) < worker_count:
            index = next_index
            next_index += 1
            active[executor.submit(worker, work_items[index], control)] = index

    def report_activity() -> None:
        if on_activity is None:
            return
        on_activity(
            ModelWorkActivity(
                completed_count=completed_count,
                total_count=len(work_items),
                active_item_indexes=tuple(sorted(active.values())),
                queued_count=len(work_items) - next_index,
            )
        )

    submit_available()
    try:
        report_activity()
        while active and terminal_error is None:
            completed, _ = concurrent.futures.wait(
                tuple(active),
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in completed:
                index = active.pop(future)
                try:
                    result = future.result()
                    results[index] = result
                    completed_count += 1
                    if on_result is not None:
                        on_result(result, completed_count, len(work_items))
                except BaseException as exc:
                    terminal_error = exc
                    stop_event.set()
                    break
            if terminal_error is None:
                submit_available()
            report_activity()
    finally:
        if terminal_error is not None:
            stop_event.set()
        for future in active:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)

    if terminal_error is not None:
        raise terminal_error
    return cast(list[WorkResult], results)
