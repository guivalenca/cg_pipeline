"""Post-run analysis for judge bench runs and legacy judge runs.

    python -m universe.kc_judge_report \\
        --runs reports/judge-v002-pro.json reports/judge-v002-flash.json \\
        --data reports/grouping-data.json \\
        --out reports/kc-judge-bench-v002.md

Reads new-format judge runs (kind: judge-run, verdicts with v in
clear_yes/likely/unlikely/clear_no), optionally legacy runs (v in sim/nao),
and the corpus. Generates a markdown report with per-run stats, agreement
analysis, generator audits, floor yield curves, and direction asymmetry.
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict


def collapse_verdict(v):
    """Map verdict to yes/no."""
    if v in ("clear_yes", "likely", "sim"):
        return "yes"
    elif v in ("unlikely", "clear_no", "nao"):
        return "no"
    return None


def load_run(path):
    """Load a judge run (new or legacy format)."""
    try:
        data = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return None
    return data


def load_corpus(path):
    """Load corpus with items and similarity matrix."""
    corpus = json.loads(Path(path).read_text())
    return corpus


def get_edge_level(ab_v, ba_v):
    """Map verdicts to edge weight level."""
    weight = 0
    if ab_v == "clear_yes" or ab_v == "sim":
        weight += 2
    elif ab_v in ("likely", "unlikely"):
        weight += 1
    if ba_v == "clear_yes" or ba_v == "sim":
        weight += 2
    elif ba_v in ("likely", "unlikely"):
        weight += 1
    return weight


def classify_edge(ab_collapse, ba_collapse):
    """Classify edge as dupla/simples/nada."""
    yes_count = sum(1 for v in [ab_collapse, ba_collapse] if v == "yes")
    if yes_count == 2:
        return "dupla"
    elif yes_count == 1:
        return "simples"
    else:
        return "nada"


def analyze_run(run, corpus, is_legacy=False):
    """Analyze a single run."""
    if not run:
        return None

    verdicts = run.get("verdicts", {})
    pairs = run.get("pairs", {})
    sims = corpus["sims"]
    items = corpus["items"]

    stats = {
        "pairs_judged": len(verdicts),
        "dupla": 0,
        "simples": 0,
        "nada": 0,
        "level_distribution": defaultdict(int),
        "weak_doubles": 0,
        "usage": run.get("usage", {}),
        "pairs_by_generator": defaultdict(int),
        "judged_by_generator": defaultdict(int),
        "duplas_by_generator": defaultdict(int),
        "simples_by_generator": defaultdict(int),
        "sim_bands": defaultdict(lambda: {"pairs": 0, "duplas": 0, "simples": 0, "nada": 0}),
        "asymmetry_count": 0,
    }

    for key, verdict_data in verdicts.items():
        i, j = map(int, key.split("|"))
        ab_v = verdict_data.get("ab", {}).get("v")
        ba_v = verdict_data.get("ba", {}).get("v")

        ab_collapse = collapse_verdict(ab_v)
        ba_collapse = collapse_verdict(ba_v)

        edge = classify_edge(ab_collapse, ba_collapse)
        stats[edge] += 1

        stats["level_distribution"][ab_v] += 1
        stats["level_distribution"][ba_v] += 1
        if edge == "dupla" and "likely" in (ab_v, ba_v):
            stats["weak_doubles"] += 1

        if ab_collapse != ba_collapse:
            stats["asymmetry_count"] += 1

        pair_meta = pairs.get(key, {})
        sim = pair_meta.get("sim")
        if sim is None and i < len(sims) and j < len(sims[i]):
            sim = round(sims[i][j], 4)

        if sim is not None:
            if sim < 0.70:
                band = "<0.70"
            elif sim < 0.72:
                band = "0.70-0.72"
            elif sim < 0.75:
                band = "0.72-0.75"
            elif sim < 0.78:
                band = "0.75-0.78"
            elif sim < 0.82:
                band = "0.78-0.82"
            else:
                band = ">=0.82"
            stats["sim_bands"][band]["pairs"] += 1
            if edge == "dupla":
                stats["sim_bands"][band]["duplas"] += 1
            elif edge == "simples":
                stats["sim_bands"][band]["simples"] += 1
            else:
                stats["sim_bands"][band]["nada"] += 1

        if is_legacy:
            stats["pairs_by_generator"]["?"] += 1
            stats["judged_by_generator"]["?"] += 1
            if edge == "dupla":
                stats["duplas_by_generator"]["?"] += 1
            elif edge == "simples":
                stats["simples_by_generator"]["?"] += 1
        else:
            gens = pair_meta.get("generators", [])
            if not gens:
                gens = ["?"]
            for gen in gens:
                stats["pairs_by_generator"][gen] += 1
                stats["judged_by_generator"][gen] += 1
                if edge == "dupla":
                    stats["duplas_by_generator"][gen] += 1
                elif edge == "simples":
                    stats["simples_by_generator"][gen] += 1

    return stats


def format_usage(usage_dict):
    """Format usage stats."""
    calls = usage_dict.get("calls", 0)
    tokens = usage_dict.get("prompt_tokens", 0) + usage_dict.get("completion_tokens", 0)
    cost = usage_dict.get("cost_usd", 0)
    return f"{calls} calls, {tokens} tokens, ${cost:.4f}"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="universe.kc_judge_report", description=__doc__)
    parser.add_argument("--runs", nargs="*", default=[], help="new-format run files")
    parser.add_argument("--legacy", help="legacy run file")
    parser.add_argument("--data", required=True, help="corpus file")
    parser.add_argument("--out", required=True, help="output markdown file")
    args = parser.parse_args(argv)

    corpus = load_corpus(args.data)

    runs_data = []
    for run_path in args.runs:
        run = load_run(run_path)
        if run:
            runs_data.append({"path": run_path, "data": run, "is_legacy": False})
        else:
            print(f"Warning: run not found: {run_path}", file=sys.stderr)

    legacy_data = None
    if args.legacy:
        legacy = load_run(args.legacy)
        if legacy:
            legacy_data = {"path": args.legacy, "data": legacy, "is_legacy": True}
        else:
            print(f"Warning: legacy run not found: {args.legacy}", file=sys.stderr)

    md = []
    md.append("# Judge Bench Report\n")

    md.append("## Per-Run Summary\n")
    run_stats = {}
    for i, run_info in enumerate(runs_data):
        stats = analyze_run(run_info["data"], corpus)
        run_stats[i] = stats
        name = Path(run_info["path"]).stem
        md.append(f"### {name}\n")
        md.append(f"- Pairs judged: {stats['pairs_judged']}\n")
        md.append(f"- Duplas: {stats['dupla']} | Simples: {stats['simples']} | Nada: {stats['nada']}\n")
        md.append(f"- Weak doubles (a likely direction): {stats['weak_doubles']}\n")
        md.append(f"- Usage: {format_usage(stats['usage'])}\n")

        total_directional = stats['pairs_judged'] * 2
        level_dist = []
        for level in ("clear_yes", "likely", "unlikely", "clear_no", "sim", "nao"):
            count = stats["level_distribution"].get(level, 0)
            if not count:
                continue
            pct = (count / total_directional * 100) if total_directional > 0 else 0
            level_dist.append(f"{level}: {count} ({pct:.1f}%)")
        md.append(f"- Level distribution (per directional call): {', '.join(level_dist)}\n")
        md.append("\n")

    if legacy_data:
        stats = analyze_run(legacy_data["data"], corpus, is_legacy=True)
        run_stats["legacy"] = stats
        md.append(f"### Legacy (opus5-judge-r0130)\n")
        md.append(f"- Pairs judged: {stats['pairs_judged']}\n")
        md.append(f"- Duplas: {stats['dupla']} | Simples: {stats['simples']} | Nada: {stats['nada']}\n")
        md.append(f"- Weak doubles (a likely direction): {stats['weak_doubles']}\n")
        md.append(f"- Usage: {format_usage(stats['usage'])}\n")

        total_directional = stats['pairs_judged'] * 2
        level_dist = []
        for level in ("clear_yes", "likely", "unlikely", "clear_no", "sim", "nao"):
            count = stats["level_distribution"].get(level, 0)
            if not count:
                continue
            pct = (count / total_directional * 100) if total_directional > 0 else 0
            level_dist.append(f"{level}: {count} ({pct:.1f}%)")
        md.append(f"- Level distribution (per directional call): {', '.join(level_dist)}\n")
        md.append("\n")

    if len(runs_data) >= 2:
        md.append("## A/B Agreement (First Two Runs)\n")
        run1_verdicts = runs_data[0]["data"].get("verdicts", {})
        run2_verdicts = runs_data[1]["data"].get("verdicts", {})
        common_keys = set(run1_verdicts.keys()) & set(run2_verdicts.keys())
        md.append(f"Common pairs: {len(common_keys)}\n")

        if common_keys:
            agree_count = 0
            agree_exact_count = 0
            for key in common_keys:
                v1 = run1_verdicts[key]
                v2 = run2_verdicts[key]
                c1_ab = collapse_verdict(v1["ab"]["v"])
                c1_ba = collapse_verdict(v1["ba"]["v"])
                c2_ab = collapse_verdict(v2["ab"]["v"])
                c2_ba = collapse_verdict(v2["ba"]["v"])
                if c1_ab == c2_ab and c1_ba == c2_ba:
                    agree_count += 2
                    if v1["ab"]["v"] == v2["ab"]["v"] and v1["ba"]["v"] == v2["ba"]["v"]:
                        agree_exact_count += 2
                elif c1_ab == c2_ab or c1_ba == c2_ba:
                    if c1_ab == c2_ab:
                        agree_count += 1
                    if c1_ba == c2_ba:
                        agree_count += 1

            total_dir = len(common_keys) * 2
            md.append(f"- Collapsed agreement: {agree_count}/{total_dir} ({agree_count/total_dir*100:.1f}%)\n")
            md.append(f"- Exact level agreement: {agree_exact_count}/{total_dir}\n")
        md.append("\n")
    elif len(runs_data) < 2 and (runs_data or legacy_data):
        md.append("## A/B Comparison\n")
        md.append("Skipped: fewer than 2 new runs to compare.\n")
        md.append("\n")

    if len(runs_data) > 0 and legacy_data:
        md.append("## New vs Legacy Agreement\n")
        run_verdicts = runs_data[0]["data"].get("verdicts", {})
        legacy_verdicts = legacy_data["data"].get("verdicts", {})
        common_keys = set(run_verdicts.keys()) & set(legacy_verdicts.keys())
        md.append(f"Common pairs (first new run vs legacy): {len(common_keys)}\n")
        if common_keys:
            agree_count = 0
            total_dir = len(common_keys) * 2
            for key in common_keys:
                v1 = run_verdicts[key]
                v2 = legacy_verdicts[key]
                c1_ab = collapse_verdict(v1["ab"]["v"])
                c1_ba = collapse_verdict(v1["ba"]["v"])
                c2_ab = collapse_verdict(v2["ab"]["v"])
                c2_ba = collapse_verdict(v2["ba"]["v"])
                if c1_ab == c2_ab:
                    agree_count += 1
                if c1_ba == c2_ba:
                    agree_count += 1

            md.append(f"- Collapsed agreement: {agree_count}/{total_dir} ({agree_count/total_dir*100:.1f}%)\n")
        md.append("\n")

    for i, run_info in enumerate(runs_data):
        run = run_info["data"]
        stats = run_stats[i]
        pairs = run.get("pairs", {})

        md.append(f"## Generator Audit: {Path(run_info['path']).stem}\n")
        generators = sorted(set().union(*[set(pairs.get(k, {}).get("generators", [])) for k in pairs]))
        if not generators:
            generators = ["?"]

        md.append("| Generator | Pairs Proposed | Judged | Duplas | Simples | Hit Rate |\n")
        md.append("|-----------|----------------|--------|--------|---------|----------|\n")
        for gen in generators:
            proposed = stats["pairs_by_generator"].get(gen, 0)
            judged = stats["judged_by_generator"].get(gen, 0)
            duplas = stats["duplas_by_generator"].get(gen, 0)
            simples = stats["simples_by_generator"].get(gen, 0)
            hit_rate = (duplas + simples) / judged if judged > 0 else 0
            md.append(f"| {gen} | {proposed} | {judged} | {duplas} | {simples} | {hit_rate:.2%} |\n")
        md.append("\n")

    if legacy_data:
        stats = run_stats["legacy"]
        md.append("## Generator Audit: Legacy (opus5-judge-r0130)\n")
        md.append("| Generator | Pairs Proposed | Judged | Duplas | Simples | Hit Rate |\n")
        md.append("|-----------|----------------|--------|--------|---------|----------|\n")
        gen = "?"
        proposed = stats["pairs_by_generator"].get(gen, 0)
        judged = stats["judged_by_generator"].get(gen, 0)
        duplas = stats["duplas_by_generator"].get(gen, 0)
        simples = stats["simples_by_generator"].get(gen, 0)
        hit_rate = (duplas + simples) / judged if judged > 0 else 0
        md.append(f"| {gen} | {proposed} | {judged} | {duplas} | {simples} | {hit_rate:.2%} |\n")
        md.append("\n")

    for i, run_info in enumerate(runs_data):
        stats = run_stats[i]
        md.append(f"## Floor Yield Curve: {Path(run_info['path']).stem}\n")
        md.append("| Sim Band | Pairs | Duplas | Simples | Nada |\n")
        md.append("|----------|-------|--------|---------|------|\n")
        for band in ["<0.70", "0.70-0.72", "0.72-0.75", "0.75-0.78", "0.78-0.82", ">=0.82"]:
            band_data = stats["sim_bands"].get(band, {"pairs": 0, "duplas": 0, "simples": 0, "nada": 0})
            md.append(f"| {band} | {band_data['pairs']} | {band_data['duplas']} | {band_data['simples']} | {band_data['nada']} |\n")
        md.append("\n")

    if legacy_data:
        stats = run_stats["legacy"]
        md.append("## Floor Yield Curve: Legacy (opus5-judge-r0130)\n")
        md.append("| Sim Band | Pairs | Duplas | Simples | Nada |\n")
        md.append("|----------|-------|--------|---------|------|\n")
        for band in ["<0.70", "0.70-0.72", "0.72-0.75", "0.75-0.78", "0.78-0.82", ">=0.82"]:
            band_data = stats["sim_bands"].get(band, {"pairs": 0, "duplas": 0, "simples": 0, "nada": 0})
            md.append(f"| {band} | {band_data['pairs']} | {band_data['duplas']} | {band_data['simples']} | {band_data['nada']} |\n")
        md.append("\n")

    md.append("## Direction Asymmetry\n")
    for i, run_info in enumerate(runs_data):
        stats = run_stats[i]
        md.append(f"### {Path(run_info['path']).stem}\n")
        md.append(f"Pairs with exactly one yes direction: {stats['asymmetry_count']}\n")
        md.append("\n")

    if legacy_data:
        stats = run_stats["legacy"]
        md.append(f"### Legacy (opus5-judge-r0130)\n")
        md.append(f"Pairs with exactly one yes direction: {stats['asymmetry_count']}\n")
        md.append("\n")

    report_text = "".join(md)
    Path(args.out).write_text(report_text)
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
