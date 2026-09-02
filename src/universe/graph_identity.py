"""Stable graph identity for one curriculum Subject."""

from __future__ import annotations

import hashlib
import re
import unicodedata


GRAPH_ID = re.compile(r"^[a-z][a-z0-9_.-]{1,127}$")
INSTITUTION_SLUG = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
GRAPH_ID_CONFLICT_MESSAGE = (
    "Este ID de Subject já está em uso no Companion. Revise a instituição, "
    "o currículo ou o código do Subject."
)


class GraphIdConflict(ValueError):
    """A proposed graph id is already occupied in Concept or Companion."""

    def __init__(self, graph_id: str) -> None:
        self.graph_id = graph_id
        super().__init__(GRAPH_ID_CONFLICT_MESSAGE)


def slug_component(value: str) -> str:
    """Normalize human text for one stable lowercase identity component."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip("-")


def subject_graph_id_for(
    institution_slug: str,
    curriculum_name: str,
    lesson_subject_code: str,
) -> str:
    """Generate one stable graph id from its full institutional identity."""
    institution_slug = str(institution_slug or "").strip()
    if INSTITUTION_SLUG.fullmatch(institution_slug) is None:
        raise ValueError("A instituição não tem um slug compatível com o Companion.")
    curriculum_slug = slug_component(str(curriculum_name or "").strip())
    if not curriculum_slug:
        raise ValueError("O currículo não produz um identificador válido.")
    subject_slug = slug_component(str(lesson_subject_code or "").strip())
    if not subject_slug:
        raise ValueError("O código do Subject não produz um identificador válido.")

    prefix = f"graph-{institution_slug}-"
    suffix = f"-{subject_slug}"
    candidate = prefix + curriculum_slug + suffix
    if len(candidate) > 128:
        digest = "-" + hashlib.sha256(candidate.encode()).hexdigest()[:8]
        curriculum_slug = curriculum_slug[
            : 128 - len(prefix) - len(digest) - len(suffix)
        ].rstrip("-")
        candidate = prefix + curriculum_slug + digest + suffix
    return candidate


def validate_graph_id(value: str) -> str:
    graph_id = str(value or "").strip()
    if GRAPH_ID.fullmatch(graph_id) is None:
        raise ValueError(
            "O graph ID deve começar com letra minúscula, ter de 2 a 128 "
            "caracteres e usar apenas letras minúsculas, números, ponto, "
            "hífen ou sublinhado."
        )
    return graph_id
