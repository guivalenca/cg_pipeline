"""Run one planned pipeline command under child-owned lease supervision.

This is the production subprocess boundary used by ``kc_pipeline.advance``.
It invokes the target module in the same Python process, so every runner sees
one authoritative lease supervisor through ``pipeline_lease``. Selected model
producers publish their deterministic rows before the lease is released.
"""

from __future__ import annotations

import importlib
import sys

from universe import pipeline_lease
from universe.db import connect


def execute_module(module_name: str, argv: list[str]) -> None:
    """Invoke a universe CLI's ``main(argv)`` without another subprocess."""
    if not module_name.startswith("universe."):
        raise SystemExit("pipeline worker only executes universe modules")
    module = importlib.import_module(module_name)
    main = getattr(module, "main", None)
    if not callable(main):
        raise SystemExit(f"{module_name} has no callable main")
    main(argv)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        raise SystemExit("usage: universe.pipeline_worker STAGE MODULE [--] [ARGS...]")
    stage, module_name, *target_argv = args
    if target_argv[:1] == ["--"]:
        target_argv = target_argv[1:]

    with connect() as conn:
        with pipeline_lease.supervise(conn, stage=stage) as supervisor:
            supervisor.verify()
            execute_module(module_name, target_argv)
            supervisor.verify()


if __name__ == "__main__":
    main()
