#!/usr/bin/env python3
"""Prepare a Markdown Source Body for line-grounded extraction."""

from __future__ import annotations

import argparse
from pathlib import Path


def strip_frontmatter(text: str) -> str:
    """Remove one leading YAML frontmatter block and leading blank lines."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                lines = lines[index + 1 :]
                break
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)


def numbered_lines(body: str) -> list[str]:
    return [f"[L{index:03d}] {line}" for index, line in enumerate(body.splitlines(), 1)]


def prepare_source(path: Path) -> tuple[list[str], list[str]]:
    body_lines = strip_frontmatter(path.read_text(encoding="utf-8")).splitlines()
    numbered = [f"[L{index:03d}] {line}" for index, line in enumerate(body_lines, 1)]
    return body_lines, numbered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    _, lines = prepare_source(args.source)
    rendered = "\n".join(lines) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
