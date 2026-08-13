"""Static HTML for reading a run back: one run, or two side by side.

Self-contained pages, no assets, no scripts. They are regenerable from the
database, so `reports/` is not tracked.
"""

import json
from html import escape

STYLE = """
:root {
  color-scheme: light dark;
  --bg: #fbfbfa; --panel: #ffffff; --ink: #1c1c1a; --muted: #6b6b66;
  --line: #e2e2dd; --accent: #7a2f2f; --accent-bg: #fbf0ef;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16161a; --panel: #1d1d22; --ink: #e6e6e2; --muted: #94948d;
    --line: #2e2e35; --accent: #e08a80; --accent-bg: #2a1d1d;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 2.5rem 1.5rem 6rem; background: var(--bg); color: var(--ink);
  font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 62rem; margin: 0 auto; }
main.wide { max-width: 92rem; }
h1 { font-size: 1.35rem; font-weight: 600; margin: 0 0 .25rem; letter-spacing: -.01em; }
h2 { font-size: 1rem; font-weight: 600; margin: 0 0 .1rem; }
.sub { color: var(--muted); margin: 0 0 1.75rem; }
.stamp { display: grid; grid-template-columns: max-content 1fr; gap: .3rem 1.25rem;
  border: 1px solid var(--line); background: var(--panel); border-radius: 6px;
  padding: 1rem 1.25rem; margin-bottom: 2.5rem; font-size: 13.5px; }
.stamp dt { color: var(--muted); }
.stamp dd { margin: 0; font-variant-numeric: tabular-nums; }
.mono, pre, code { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
section.item { border-top: 1px solid var(--line); padding-top: 1.5rem; margin-top: 2rem; }
.meta { color: var(--muted); font-size: 12.5px; margin: 0 0 .9rem; }
pre { background: var(--panel); border: 1px solid var(--line); border-radius: 6px;
  padding: 1rem 1.15rem; overflow-x: auto; white-space: pre-wrap; word-break: break-word;
  font-size: 13px; line-height: 1.5; margin: 0; }
pre.error { border-color: var(--accent); background: var(--accent-bg); color: var(--accent); }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }
.cols h3 { font-size: 12.5px; font-weight: 600; color: var(--muted); margin: 0 0 .4rem;
  text-transform: uppercase; letter-spacing: .06em; }
.note { border: 1px solid var(--line); background: var(--panel); border-radius: 6px;
  padding: .9rem 1.15rem; font-size: 13px; color: var(--muted); margin-top: 2.5rem; }
@media (max-width: 780px) { .cols { grid-template-columns: 1fr; } }
"""

USAGE_ORDER = ["prompt_tokens", "completion_tokens", "total_tokens", "cost", "total_cost"]


def aggregate_usage(items: list[dict]) -> dict:
    """Sum the authoritative provider usage reported across items.

    One level of nesting is flattened by inner key, because OpenRouter
    reports cache and reasoning counts inside prompt_tokens_details and
    completion_tokens_details instead of at the top level. Newer run items
    contain an attempt ledger; when present, that ledger replaces the legacy
    top-level final-attempt usage so retries and their cost are counted once.
    """
    totals: dict[str, float] = {}

    def add(key: str, value) -> None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            totals[key] = totals.get(key, 0) + value

    def add_usage(usage: dict) -> None:
        for key, value in usage.items():
            if isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    add(inner_key, inner_value)
            else:
                add(key, value)

    for item in items:
        usage = item.get("usage") or {}
        attempts = usage.get("attempts")
        if isinstance(attempts, list):
            for attempt in attempts:
                if (
                    isinstance(attempt, dict)
                    and isinstance(attempt.get("usage"), dict)
                ):
                    add_usage(attempt["usage"])
        else:
            add_usage(usage)
    return {key: round(value, 6) if isinstance(value, float) else value
            for key, value in sorted(totals.items(), key=_usage_rank)}


def _usage_rank(pair: tuple[str, float]) -> tuple[int, str]:
    key = pair[0]
    return (USAGE_ORDER.index(key) if key in USAGE_ORDER else len(USAGE_ORDER), key)


def format_usage(usage: dict) -> str:
    """Token counts exact and grouped; costs and other floats short."""
    return ", ".join(
        f"{key} {value:,}" if isinstance(value, int) else f"{key} {value:g}"
        for key, value in usage.items()
    )


def _stamp(run: dict, items: list[dict]) -> dict[str, str]:
    finished = run["finished_at"]
    duration = (finished - run["started_at"]).total_seconds() if finished else None
    usage = aggregate_usage(items)
    failed = sum(1 for item in items if item["error"])
    return {
        "run": run["id"],
        "stage": run["stage"],
        "model": run["model"],
        "prompt": f"{run['prompt_ref']}  sha {run['prompt_sha'][:12]}",
        "params": json.dumps(run["params"], sort_keys=True),
        "status": run["status"],
        "items": f"{len(items) - failed} ok, {failed} failed",
        "started": run["started_at"].strftime("%Y-%m-%d %H:%M:%S %Z").strip(),
        "wall clock": f"{duration:.1f}s" if duration is not None else "unfinished",
        "model time": f"{sum(i['duration_ms'] or 0 for i in items) / 1000:.1f}s",
        "usage": format_usage(usage) or "none reported",
    }


def _stamp_html(stamp: dict[str, str]) -> str:
    rows = "".join(
        f"<dt>{escape(key)}</dt><dd class='mono'>{escape(str(value))}</dd>"
        for key, value in stamp.items()
    )
    return f"<dl class='stamp'>{rows}</dl>"


def _page(title: str, body: str, wide: bool = False) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{escape(title)}</title><style>{STYLE}</style></head>"
        f"<body><main class='{'wide' if wide else ''}'>{body}</main></body></html>"
    )


def _response_html(item: dict) -> str:
    if item["error"]:
        return f"<pre class='error'>{escape(item['error'])}</pre>"
    return f"<pre>{escape(item['response'] or '')}</pre>"


def _item_meta(item: dict) -> str:
    bits = [item["artifact_id"]]
    if item["duration_ms"] is not None:
        bits.append(f"{item['duration_ms'] / 1000:.1f}s")
    if item["usage"]:
        bits.append(format_usage(aggregate_usage([item])))
    return escape("  ·  ".join(bits))


def render_run(run: dict, items: list[dict]) -> str:
    sections = "".join(
        "<section class='item'>"
        f"<h2>{escape(item['source_title'] or item['source_id'])}</h2>"
        f"<p class='meta mono'>{escape(item['source_id'])}<br>{_item_meta(item)}</p>"
        f"{_response_html(item)}</section>"
        for item in items
    )
    body = (
        f"<h1>{escape(run['id'])} &middot; {escape(run['prompt_ref'])}</h1>"
        f"<p class='sub'>{escape(run['model'])} over {len(items)} artifact(s)</p>"
        f"{_stamp_html(_stamp(run, items))}{sections}"
    )
    return _page(f"{run['id']} {run['prompt_ref']}", body)


def render_comparison(run_a: dict, items_a: list[dict], run_b: dict, items_b: list[dict]) -> str:
    by_artifact_a = {item["artifact_id"]: item for item in items_a}
    by_artifact_b = {item["artifact_id"]: item for item in items_b}
    shared = [key for key in by_artifact_a if key in by_artifact_b]

    sections = ""
    for artifact_id in shared:
        left, right = by_artifact_a[artifact_id], by_artifact_b[artifact_id]
        sections += (
            "<section class='item'>"
            f"<h2>{escape(left['source_title'] or left['source_id'])}</h2>"
            f"<p class='meta mono'>{escape(left['source_id'])}</p>"
            "<div class='cols'>"
            f"<div><h3>{escape(run_a['id'])} &middot; {escape(run_a['prompt_ref'])}</h3>"
            f"<p class='meta mono'>{_item_meta(left)}</p>{_response_html(left)}</div>"
            f"<div><h3>{escape(run_b['id'])} &middot; {escape(run_b['prompt_ref'])}</h3>"
            f"<p class='meta mono'>{_item_meta(right)}</p>{_response_html(right)}</div>"
            "</div></section>"
        )

    only_a = [key for key in by_artifact_a if key not in by_artifact_b]
    only_b = [key for key in by_artifact_b if key not in by_artifact_a]
    parts = []
    if only_a:
        parts.append(f"only in {escape(run_a['id'])}: {escape(', '.join(only_a))}")
    if only_b:
        parts.append(f"only in {escape(run_b['id'])}: {escape(', '.join(only_b))}")
    note = (
        "<div class='note'><strong>Not compared.</strong><br>" + "<br>".join(parts) + "</div>"
        if parts
        else ""
    )

    body = (
        f"<h1>{escape(run_a['id'])} vs {escape(run_b['id'])}</h1>"
        f"<p class='sub'>{len(shared)} artifact(s) in both runs</p>"
        "<div class='cols'>"
        f"<div>{_stamp_html(_stamp(run_a, items_a))}</div>"
        f"<div>{_stamp_html(_stamp(run_b, items_b))}</div>"
        f"</div>{sections}{note}"
    )
    return _page(f"{run_a['id']} vs {run_b['id']}", body, wide=True)
