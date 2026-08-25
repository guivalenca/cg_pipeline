"""Stable graph identity generated from an Institution and Syllabus name."""

from __future__ import annotations

import hashlib
import re
import unicodedata


GRAPH_ID = re.compile(r"^[a-z][a-z0-9_.-]{1,127}$")
INSTITUTION_SLUG = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


class GraphIdConflict(ValueError):
    """A proposed graph id is already occupied in Concept or Companion."""

    def __init__(self, graph_id: str) -> None:
        self.graph_id = graph_id
        super().__init__(f"O identificador {graph_id!r} já está em uso.")


def slug_component(value: str) -> str:
    """Normalize human text for one stable lowercase identity component."""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip("-")


def graph_id_for(institution_slug: str, syllabus_name: str) -> str:
    """Generate a deterministic Companion graph id, bounded to 128 chars."""
    institution_slug = str(institution_slug or "").strip()
    if INSTITUTION_SLUG.fullmatch(institution_slug) is None:
        raise ValueError("A instituição não tem um slug compatível com o Companion.")
    name_slug = slug_component(str(syllabus_name or "").strip())
    if not name_slug:
        raise ValueError("O nome do syllabus não produz um identificador válido.")
    prefix = f"graph-{institution_slug}-"
    candidate = prefix + name_slug
    if len(candidate) > 128:
        suffix = "-" + hashlib.sha256(candidate.encode()).hexdigest()[:8]
        name_slug = name_slug[: 128 - len(prefix) - len(suffix)].rstrip("-")
        candidate = prefix + name_slug + suffix
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
