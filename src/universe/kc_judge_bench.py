"""Bench runner for the directional mastery judge (ADR 0011).

    python -m universe.kc_judge_bench \\
        --prompt prompts/kc-judge/v002-surmise-pair.md \\
        --tool prompts/kc-judge/tool-v002.json \\
        --model deepseek/deepseek-v4-pro \\
        --out reports/judge-v002-r0130.json

Reads a corpus JSON from reports/, calls a model via ModelClient, and writes
a run JSON back to reports/. No database, no ledger.
"""

import argparse
import json
import math
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from universe.model_client import DEFAULT_MAX_TOKENS, ModelClient, ModelError

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
FIELD = re.compile(r"\{\{(\w+)\}\}")
DEFAULT_WORKERS = 16
DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_EXTRA = {
    "tool_choice": "auto",
    "reasoning_effort": "low",
    # Routing decision 2026-08-01 (docs/pipeline-defaults.md): no low-bit
    # quantization, fastest acceptable provider. Allowlist because OpenRouter
    # has no quantization denylist; "unknown" admits undeclared providers.
    "provider": {
        "sort": "throughput",
        "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
    },
}


def load_prompt_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"no prompt at {p}")
    return p.read_text()


def render_template(template: str, fields: dict[str, str]) -> str:
    missing = []

    def fill(match):
        key = match.group(1)
        if key not in fields:
            missing.append(key)
            return match.group(0)
        return fields[key]

    rendered = FIELD.sub(fill, template)
    if missing:
        raise SystemExit(f"missing template fields: {', '.join(sorted(set(missing)))}")
    if FIELD.search(rendered):
        raise SystemExit(f"unrendered template placeholders remain")
    return rendered


def load_tool(path: str) -> dict:
    tool = json.loads(Path(path).read_text())
    missing = [key for key in ("name", "description", "parameters") if key not in tool]
    if missing:
        raise SystemExit(f"{path} lacks {', '.join(missing)}")
    return {
        "tools": [{"type": "function", "function": tool}],
        "tool_choice": {"type": "function", "function": {"name": tool["name"]}},
        "parallel_tool_calls": False,
    }


def bm25_score(query_tokens, doc_tokens, all_docs, k1=1.2, b=0.75):
    n = len(all_docs)
    avg_len = sum(len(d) for d in all_docs) / n if n > 0 else 0
    doc_len = len(doc_tokens)
    score = 0.0
    unique_q = set(query_tokens)
    for t in unique_q:
        if t not in doc_tokens:
            continue
        tf = doc_tokens.count(t)
        df = sum(1 for d in all_docs if t in d)
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_len / avg_len))
    return score


def generate_pairs(corpus, floor=0.70, cap=6, lexical_k=5, legacy_knn=0, dense_min=None):
    items = corpus["items"]
    sims = corpus["sims"]
    n = len(items)
    pairs_by_key = {}
    pair_generators = defaultdict(set)
    axis_filtered = defaultdict(int)

    def compatible(i, j):
        return items[i]["modality"] == items[j]["modality"] and items[i]["knowledge"] == items[j]["knowledge"]

    def add_pair(i, j, gen):
        if not compatible(i, j):
            axis_filtered[gen] += 1
            return
        if i > j:
            i, j = j, i
        key = f"{i}|{j}"
        if key not in pairs_by_key:
            pairs_by_key[key] = {"sim": round(sims[i][j], 4)}
        pair_generators[key].add(gen)

    statements = [item["statement"] for item in items]
    statement_tokens = [
        re.findall(r"[a-z0-9_]+", s.lower()) for s in statements
    ]

    for i in range(n):
        neighbors = [(j, sims[i][j]) for j in range(n) if i != j and sims[i][j] >= floor]
        neighbors.sort(key=lambda x: x[1], reverse=True)
        for j, _ in neighbors[:cap]:
            add_pair(i, j, "semantic")

    for i in range(n):
        scores = []
        for j in range(n):
            if i == j:
                scores.append((-1, j))
            else:
                score = bm25_score(statement_tokens[i], statement_tokens[j], statement_tokens)
                scores.append((score, j))
        scores.sort(reverse=True)
        for _, j in scores[:lexical_k]:
            if j != i:
                add_pair(i, j, "lexical")

    if legacy_knn > 0:
        for i in range(n):
            neighbors = [(j, sims[i][j]) for j in range(n) if i != j]
            neighbors.sort(key=lambda x: x[1], reverse=True)
            for j, _ in neighbors[:legacy_knn]:
                add_pair(i, j, "legacy")

    if dense_min is not None:
        for i in range(n):
            for j in range(i + 1, n):
                if sims[i][j] >= dense_min:
                    add_pair(i, j, "dense")

    for key in pairs_by_key:
        pairs_by_key[key]["generators"] = sorted(list(pair_generators[key]))

    return pairs_by_key, axis_filtered

def call_model_for_pair(client, prompt_template, item_a, item_b, ab):
    fields = {
        "a_statement": item_a["statement"],
        "a_task": item_a["body"],
        "a_answer": item_a["answer"],
        "b_statement": item_b["statement"],
        "b_task": item_b["body"],
        "b_answer": item_b["answer"],
    }
    rendered = render_template(prompt_template, fields)
    backoff = [1, 4, 16]
    for attempt in range(3):
        try:
            text, usage, duration_ms = client.complete(rendered)
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"unparseable JSON: {text[:200]}"
            if not isinstance(parsed, dict):
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"parsed result not a dict"
            verdict = parsed.get("verdict")
            reason = parsed.get("reason")
            if verdict not in ("clear_yes", "likely", "unlikely", "clear_no"):
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"invalid verdict: {verdict}"
            if not isinstance(reason, str) or not reason.strip():
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"missing or empty reason"
            return {"v": verdict, "reason": reason.strip(), "usage": usage, "duration_ms": duration_ms}, None
        except ModelError as e:
            if attempt < 2:
                time.sleep(backoff[attempt])
            else:
                return None, f"ModelError: {str(e)}"
    return None, "exhausted retries"

def call_model_for_pair_both(client, prompt_template, item_a, item_b):
    fields = {
        "a_statement": item_a["statement"],
        "a_task": item_a["body"],
        "a_answer": item_a["answer"],
        "b_statement": item_b["statement"],
        "b_task": item_b["body"],
        "b_answer": item_b["answer"],
    }
    rendered = render_template(prompt_template, fields)
    backoff = [1, 4, 16]
    for attempt in range(3):
        try:
            text, usage, duration_ms = client.complete(rendered)
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"unparseable JSON: {text[:200]}"
            if not isinstance(parsed, dict):
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"parsed result not a dict"
            verdict_a_to_b = parsed.get("verdict_a_to_b")
            reason_a_to_b = parsed.get("reason_a_to_b")
            verdict_b_to_a = parsed.get("verdict_b_to_a")
            reason_b_to_a = parsed.get("reason_b_to_a")
            if verdict_a_to_b not in ("clear_yes", "likely", "unlikely", "clear_no") or verdict_b_to_a not in ("clear_yes", "likely", "unlikely", "clear_no"):
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"invalid verdicts: {verdict_a_to_b}, {verdict_b_to_a}"
            if not isinstance(reason_a_to_b, str) or not reason_a_to_b.strip() or not isinstance(reason_b_to_a, str) or not reason_b_to_a.strip():
                if attempt < 2:
                    time.sleep(backoff[attempt])
                    continue
                return None, f"missing or empty reason"
            return {
                "ab": {"v": verdict_a_to_b, "reason": reason_a_to_b, "usage": usage, "duration_ms": duration_ms},
                "ba": {"v": verdict_b_to_a, "reason": reason_b_to_a},
            }, None
        except ModelError as e:
            if attempt < 2:
                time.sleep(backoff[attempt])
            else:
                return None, f"ModelError: {str(e)}"
    return None, "exhausted retries"


def load_progress(progress_path):
    verdicts = {}
    if not progress_path.exists():
        return verdicts
    with open(progress_path) as f:
        for line in f:
            line = line.rstrip('\n')
            if not line:
                continue
            try:
                obj = json.loads(line)
                key = obj.get("key")
                if key and "ab" in obj and "ba" in obj:
                    verdicts[key] = {"ab": obj["ab"], "ba": obj["ba"]}
            except json.JSONDecodeError:
                pass
    return verdicts


def main(argv=None):
    parser = argparse.ArgumentParser(prog="universe.kc_judge_bench", description=__doc__)
    parser.add_argument("--prompt", required=True, help="path to .md template")
    parser.add_argument("--tool", required=True, help="path to tool JSON")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--data", default="reports/grouping-data.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--floor", type=float, default=0.70)
    parser.add_argument("--cap", type=int, default=6)
    parser.add_argument("--lexical-k", type=int, default=5)
    parser.add_argument("--dense-min", type=float, default=None)
    parser.add_argument("--legacy-knn", type=int, default=0)
    parser.add_argument("--closure-rounds", type=int, default=5)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--extra", type=lambda s: json.loads(s) if s else {})
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    corpus_path = Path(args.data)
    if not corpus_path.exists():
        raise SystemExit(f"corpus not found: {corpus_path}")
    corpus = json.loads(corpus_path.read_text())

    prompt_text = load_prompt_text(args.prompt)
    tool_payload = load_tool(args.tool)
    tool_obj = tool_payload["tools"][0]["function"]
    pair_mode = "verdict_a_to_b" in tool_obj["parameters"]["properties"]

    base_pairs_by_key, axis_filtered = generate_pairs(
        corpus,
        floor=args.floor,
        cap=args.cap,
        lexical_k=args.lexical_k,
        legacy_knn=args.legacy_knn,
        dense_min=args.dense_min,
    )

    base_pair_count = len(base_pairs_by_key)
    gen_counts = defaultdict(int)
    for key, data in base_pairs_by_key.items():
        for gen in data["generators"]:
            gen_counts[gen] += 1

    print(f"semantic={gen_counts['semantic']} lexical={gen_counts['lexical']} " +
          f"legacy={gen_counts['legacy']} dense={gen_counts['dense']} union={base_pair_count} axis_filtered={sum(axis_filtered.values())}")
    print(f"calls={base_pair_count * (1 if pair_mode else 2)}")

    if args.dry_run:
        print(f"call mode: {'pair' if pair_mode else 'direction'}")
        if base_pairs_by_key:
            first_key = sorted(base_pairs_by_key.keys(), key=lambda k: base_pairs_by_key[k]["sim"], reverse=True)[0]
            i, j = map(int, first_key.split("|"))
            fields = {
                "a_statement": corpus["items"][i]["statement"],
                "a_task": corpus["items"][i]["body"],
                "a_answer": corpus["items"][i]["answer"],
                "b_statement": corpus["items"][j]["statement"],
                "b_task": corpus["items"][j]["body"],
                "b_answer": corpus["items"][j]["answer"],
            }
            rendered = render_template(prompt_text, fields)
            print("\nFirst pair rendered prompt:")
            print(rendered)
        sys.exit(0)

    pairs_by_key = dict(base_pairs_by_key)
    ordered_keys = sorted(pairs_by_key.keys(), key=lambda k: pairs_by_key[k]["sim"], reverse=True)

    if args.limit:
        limited_keys = ordered_keys[:args.limit]
        pairs_by_key = {k: pairs_by_key[k] for k in limited_keys}
        ordered_keys = limited_keys

    progress_path = Path(str(args.out) + ".progress.jsonl")
    if progress_path.exists() and not args.resume:
        raise SystemExit(f"progress sidecar exists at {progress_path}; pass --resume to continue or delete the file")

    verdicts = {}
    if args.resume and progress_path.exists():
        verdicts = load_progress(progress_path)
        print(f"Restored {len(verdicts)} pairs from {progress_path}", file=sys.stderr)

    extra = dict(tool_payload)
    extra.update(DEFAULT_EXTRA)
    if args.extra:
        extra.update(args.extra)

    client = ModelClient(args.model, extra=extra or None, max_tokens=DEFAULT_MAX_TOKENS)

    failed_calls = []
    progress_lock = threading.Lock()
    completed_count = [len(verdicts)]
    progress_fh = None if not progress_path else open(progress_path, "a")

    print(f"Starting with {len(ordered_keys)} base pairs ({args.workers} workers)", file=sys.stderr)

    def judge_pair(key):
        i, j = map(int, key.split("|"))
        item_a, item_b = corpus["items"][i], corpus["items"][j]
        results = {}
        if pair_mode:
            call_result, error = call_model_for_pair_both(client, prompt_text, item_a, item_b)
            if error:
                with progress_lock:
                    failed_calls.append((key, "pair", error))
                return None
            results = call_result
        else:
            for ab in [True, False]:
                a, b = (item_a, item_b) if ab else (item_b, item_a)
                call_result, error = call_model_for_pair(client, prompt_text, a, b, ab)
                if error:
                    with progress_lock:
                        failed_calls.append((key, "ab" if ab else "ba", error))
                    return None
                results["ab" if ab else "ba"] = call_result
        return (key, results)


    pairs_to_judge = [k for k in ordered_keys if k not in verdicts]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(judge_pair, key): key for key in pairs_to_judge}
        for future in as_completed(futures):
            result = future.result()
            if result:
                key, results = result
                verdicts[key] = results
                completed_count[0] += 1
                with progress_lock:
                    if progress_fh:
                        progress_fh.write(json.dumps({"key": key, "ab": results["ab"], "ba": results["ba"]}, ensure_ascii=False) + "\n")
                        progress_fh.flush()
                    if completed_count[0] % 20 == 0:
                        print(f"julgados {completed_count[0]}/{len(ordered_keys)} pares", file=sys.stderr)
            else:
                break

    if failed_calls:
        if progress_fh:
            progress_fh.close()
        print(f"Failed calls: {len(failed_calls)}", file=sys.stderr)
        for key, direction, error in failed_calls:
            print(f"  {key} {direction}: {error}", file=sys.stderr)
        sys.exit(1)

    closure_added_pairs = {}
    for round_num in range(args.closure_rounds):
        new_pairs = set()
        grain_by_idx = {i: item.get("grain") for i, item in enumerate(corpus["items"])}

        def is_double(key):
            if key not in verdicts:
                return False
            ab = verdicts[key].get("ab", {}).get("v")
            ba = verdicts[key].get("ba", {}).get("v")
            if not ab or not ba:
                return False
            return ab == "clear_yes" and ba == "clear_yes"

        for key in verdicts:
            if not is_double(key):
                continue
            i, j = map(int, key.split("|"))
            if grain_by_idx[i] != grain_by_idx[j]:
                continue

            for k in range(len(corpus["items"])):
                if k == i or k == j:
                    continue
                jk_key = f"{min(j, k)}|{max(j, k)}"
                kj_key = f"{min(k, j)}|{max(k, j)}"
                if is_double(jk_key) and grain_by_idx[j] == grain_by_idx[k]:
                    ik_key = f"{min(i, k)}|{max(i, k)}"
                    if ik_key not in pairs_by_key and ik_key not in verdicts:
                        new_pairs.add(ik_key)

        if not new_pairs:
            break

        for key2 in new_pairs:
            i, j = map(int, key2.split("|"))
            sim = corpus["sims"][i][j] if i < len(corpus["sims"]) and j < len(corpus["sims"][i]) else 0.0
            pairs_by_key[key2] = {
                "sim": round(sim, 4),
                "generators": ["closure"]
            }
            closure_added_pairs[key2] = True

        print(f"fechamento rodada {round_num + 1}: +{len(new_pairs)} pares", file=sys.stderr)

        new_ordered = sorted(new_pairs, key=lambda k: pairs_by_key[k]["sim"], reverse=True)
        new_pairs_to_judge = [k for k in new_ordered if k not in verdicts]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(judge_pair, key): key for key in new_pairs_to_judge}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    key, results = result
                    verdicts[key] = results
                    completed_count[0] += 1
                    with progress_lock:
                        if progress_fh:
                            progress_fh.write(json.dumps({"key": key, "ab": results["ab"], "ba": results["ba"]}, ensure_ascii=False) + "\n")
                            progress_fh.flush()
                        if completed_count[0] % 20 == 0:
                            print(f"julgados {completed_count[0]} pares", file=sys.stderr)
                else:
                    break

    if progress_fh:
        progress_fh.close()

    ordered_keys = sorted(pairs_by_key.keys(), key=lambda k: pairs_by_key[k]["sim"], reverse=True)
    ordered_keys_for_output = [k for k in ordered_keys if k not in closure_added_pairs]
    ordered_keys_for_output.extend(sorted(closure_added_pairs.keys(), key=lambda k: pairs_by_key[k]["sim"], reverse=True))

    params = {
        "workers": args.workers,
        "floor": args.floor,
        "cap": args.cap,
        "lexical_k": args.lexical_k,
        "dense_min": args.dense_min,
        "legacy_knn": args.legacy_knn,
        "closure_rounds": args.closure_rounds,
        "call_mode": "pair" if pair_mode else "direction",
        "axis_filtered": axis_filtered,
        "passages_from": corpus["run_id"],
        "convencao": "A->B = dominar A implica dominar B; ab = menor_indice -> maior_indice",
    }
    params.update(extra)

    total_usage = {
        "calls": len(verdicts) * (1 if pair_mode else 2),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cost_usd": 0.0,
    }
    for key in verdicts:
        for direction in ["ab", "ba"]:
            if direction in verdicts[key] and "usage" in verdicts[key][direction]:
                u = verdicts[key][direction]["usage"]
                total_usage["prompt_tokens"] += u.get("prompt_tokens", 0)
                total_usage["completion_tokens"] += u.get("completion_tokens", 0)
                if "cost" in u:
                    total_usage["cost_usd"] += u["cost"]

    output = {
        "kind": "judge-run",
        "judge": args.model,
        "variant": Path(args.prompt).stem,
        "corpus": {
            "file": corpus_path.name,
            "run_id": corpus["run_id"],
            "n_items": len(corpus["items"]),
        },
        "params": params,
        "prompt": {
            "user_template": prompt_text,
            "tool": tool_obj,
        },
        "order": ordered_keys_for_output,
        "pairs": pairs_by_key,
        "verdicts": verdicts,
        "usage": total_usage,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(output, ensure_ascii=False, indent=1))
    tmp_path.rename(out_path)

    if progress_path.exists():
        progress_path.unlink()


if __name__ == "__main__":
    main()
