"""Command adapter invoked by the existing Lesson Build worker."""

from __future__ import annotations

import sys

from universe import lesson_creation, pipeline_lease
from universe.db import connect


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        raise SystemExit("usage: universe.lesson_creation_stage SOURCE_ID ARTIFACT_ID CONTENT_HASH")
    supervisor = pipeline_lease.current_supervisor(required=True)
    if supervisor is None or supervisor.lease is None:
        raise pipeline_lease.LeaseLost("Lesson creation stage requires an active lease")
    prefix = "lesson-build-work:"
    if not supervisor.lease.scope_key.startswith(prefix):
        raise pipeline_lease.LeaseLost("Lesson creation stage lease has the wrong scope")
    work_id = supervisor.lease.scope_key[len(prefix) :]
    with connect() as conn:
        lesson_creation.run_stage(
            conn,
            work_id=work_id,
            stage=supervisor.lease.stage,
        )


if __name__ == "__main__":
    main()
