import copy
from pathlib import Path

import pytest
from openpyxl import Workbook

import universe.syllabus_reconciliation as reconciliation_module
from universe.syllabus import (
    LEGACY_COLUMNS,
    curate_syllabus,
    get_syllabus_workbook,
    get_syllabus_version,
    import_workbook,
    parse_workbook,
    update_source_review,
)
from universe.syllabus_reconciliation import (
    _projection_from_decisions,
    _validated_identity_decisions,
    apply_reconciliation,
    build_plan,
    create_reconciliation,
    get_reconciliation,
)


def _workbook(
    path: Path,
    *,
    description: str = "Descrição original",
    url: str = "https://example.com/original",
    lesson_title: str = "Aula de arquitetura",
    lesson_description: str = "Descrição da aula",
    lesson_date: str = "11/08/2026",
    axis: str = "SI",
) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All"
    sheet.append(LEGACY_COLUMNS)
    lesson = {
        "Week": 1,
        "Sort": 1,
        "Type": "Class",
        "Title": lesson_title,
        "Date": lesson_date,
        "Axis": axis,
        "Description": lesson_description,
    }
    source = {
        "Week": 1,
        "Sort": 2,
        "Type": "Self-study",
        "Title": "Material principal",
        "Date": "11/08/2026",
        "Parent class": lesson_title,
        "Axis": axis,
        "Description": description,
        "URL": url,
    }
    sheet.append([lesson.get(column) for column in LEGACY_COLUMNS])
    sheet.append([source.get(column) for column in LEGACY_COLUMNS])
    workbook.save(path)
    workbook.close()
    return path


def _manual_projection(detail: dict, *, url: str) -> list[dict]:
    lesson = detail["lessons"][0]
    source = lesson["sources"][0]
    return [
        {
            "id": lesson["id"],
            "week": lesson["week"],
            "kind": lesson["kind"],
            "title": lesson["title"],
            "subject": lesson["subject"],
            "date": str(lesson["date"]),
            "description": lesson["description"],
            "hidden": lesson["hidden"],
            "sources": [
                {
                    "reference_id": source["reference_id"],
                    "title": source["title"],
                    "description": source["description"],
                    "url": url,
                    "media_type": source["media_type"],
                    "resource_code": source["resource_code"],
                    "scope_kind": source["scope_kind"],
                    "scope_value": source["scope_value"],
                    "hidden": True,
                }
            ],
        }
    ]


def test_related_workbook_infers_one_unambiguous_orphan_source_parent(tmp_path: Path):
    path = tmp_path / "orphan-with-institutional-metadata.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All"
    sheet.append(LEGACY_COLUMNS)
    source = {
        "Week": 1,
        "Sort": 1,
        "Type": "Self-study",
        "Title": "Fonte órfã",
        "Professor": "Professora Única",
        "Axis": "COM",
        "URL": "https://example.com/orphan",
    }
    lesson = {
        "Week": 1,
        "Sort": 8,
        "Type": "Class",
        "Title": "Aula inferida",
        "Date": "11/08/2026",
        "Professor": "Professora Única",
        "Axis": "COM",
    }
    sheet.append([source.get(column) for column in LEGACY_COLUMNS])
    sheet.append([lesson.get(column) for column in LEGACY_COLUMNS])
    workbook.save(path)
    workbook.close()

    parsed = parse_workbook(path)

    assert parsed["lessons"][0]["title"] == "Aula inferida"
    assert [item["title"] for item in parsed["lessons"][0]["source_references"]] == [
        "Fonte órfã"
    ]


def test_source_reordering_uses_incoming_order_without_creating_a_decision():
    def source(title: str, seq: int) -> dict:
        return {
            "seq": seq,
            "title": title,
            "description": f"Descrição {title}",
            "url": f"https://example.com/{title.casefold()}",
            "media_type": "article",
            "hidden": False,
        }

    def projection(sources: list[dict]) -> dict:
        return {
            "lessons": [
                {
                    "id": "lesson-current",
                    "week": 1,
                    "seq": 1,
                    "kind": "Class",
                    "title": "Aula",
                    "subject": "SI",
                    "date": "2026-08-11",
                    "description": "Descrição",
                    "hidden": False,
                    "sources": sources,
                }
            ]
        }

    baseline = projection([source("A", 1), source("B", 2)])
    current = projection([source("A", 1), source("B", 2)])
    incoming = projection([source("B", 1), source("A", 2)])

    plan = build_plan(baseline, current, incoming)

    assert plan["summary"]["action_count"] == 0
    assert [item["current"]["title"] for item in plan["lessons"][0]["sources"]] == [
        "B",
        "A",
    ]


def test_subject_changes_are_first_class_reconciliation_decisions():
    def projection(subjects: list[str]) -> dict:
        return {
            "lessons": [
                {
                    "id": "lesson-current",
                    "week": 1,
                    "seq": 1,
                    "kind": "Class",
                    "title": "Aula de arquitetura",
                    "subject": "SI",
                    "subjects": subjects,
                    "date": "2026-08-11",
                    "description": "Descrição",
                    "hidden": False,
                    "sources": [],
                }
            ]
        }

    baseline = projection(["Arquitetura de nuvem"])
    current = projection(["Arquitetura de nuvem"])
    incoming = projection(["Arquitetura de nuvem", "Serverless"])

    plan = build_plan(baseline, current, incoming)

    assert plan["summary"]["action_count"] == 1
    lesson = plan["lessons"][0]
    assert lesson["status"] == "changed"
    assert lesson["incoming"]["subjects"] == ["Arquitetura de nuvem", "Serverless"]


def _identity_projection(
    *,
    lesson_id: str | None = "lesson-stable",
    title: str = "Arquitetura de Computação em Nuvem",
    description: str = "Apresenta os principais serviços usados por uma aplicação na nuvem.",
    subject: str = "COM",
    date: str = "2026-08-11",
    seq: int = 1,
    sources: list[dict] | None = None,
) -> dict:
    return {
        "lessons": [
            {
                "id": lesson_id,
                "incoming_key": "incoming-0001" if lesson_id is None else None,
                "week": 1,
                "seq": seq,
                "kind": "Class",
                "title": title,
                "subject": subject,
                "subjects": ["Arquitetura de nuvem"],
                "date": date,
                "description": description,
                "hidden": False,
                "sources": sources or [],
            }
        ]
    }


def test_date_and_self_study_changes_do_not_disqualify_lesson_identity():
    baseline = _identity_projection(
        sources=[
            {
                "seq": 1,
                "title": "Leitura original",
                "url": "https://example.com/original",
                "media_type": "article",
            }
        ]
    )
    current = copy.deepcopy(baseline)
    incoming = _identity_projection(
        lesson_id=None,
        date="2026-08-18",
        sources=[
            {
                "seq": 1,
                "title": "Leitura substituta",
                "url": "https://example.com/substituta",
                "media_type": "article",
            }
        ],
    )

    plan = build_plan(baseline, current, incoming)

    assert plan["lessons"][0]["identity"] == {
        "state": "carried",
        "lesson_id": "lesson-stable",
        "reason": "exact_text",
    }
    assert plan["summary"]["identity_action_count"] == 0


def test_small_title_and_description_edits_carry_identity_automatically():
    baseline = _identity_projection()
    current = copy.deepcopy(baseline)
    incoming = _identity_projection(
        lesson_id=None,
        title="Arquitetura da Computação em Nuvem",
        description="Apresenta os principais serviços usados por uma aplicação em nuvem.",
    )

    plan = build_plan(baseline, current, incoming)

    assert plan["lessons"][0]["identity"]["state"] == "carried"
    assert plan["lessons"][0]["identity"]["reason"] == "small_text_edit"


def test_plan_scoped_similarity_cache_preserves_the_reconciliation_plan(
    monkeypatch,
):
    baseline = _identity_projection()
    current = copy.deepcopy(baseline)
    incoming = _identity_projection(
        lesson_id=None,
        title="Arquitetura da Computação em Nuvem",
        description="Apresenta os principais serviços usados por uma aplicação em nuvem.",
    )
    cached = build_plan(baseline, current, incoming)

    monkeypatch.setattr(
        reconciliation_module,
        "_plan_similarity",
        lambda: reconciliation_module._similarity,
    )
    uncached = build_plan(baseline, current, incoming)

    assert cached == uncached


def test_large_description_edit_requires_identity_review():
    baseline = _identity_projection()
    current = copy.deepcopy(baseline)
    incoming = _identity_projection(
        lesson_id=None,
        description="Negociação, precificação e canais de venda para um novo produto.",
    )

    plan = build_plan(baseline, current, incoming)

    lesson = plan["lessons"][0]
    assert lesson["identity"]["state"] == "review"
    assert lesson["identity"]["reason"] == "large_description_edit"
    assert lesson["identity"]["candidates"][0]["lesson_id"] == "lesson-stable"
    assert plan["summary"]["identity_action_count"] == 1


def test_lesson_subject_change_never_carries_identity_automatically():
    baseline = _identity_projection()
    current = copy.deepcopy(baseline)
    incoming = _identity_projection(lesson_id=None, subject="NEG")

    plan = build_plan(baseline, current, incoming)

    assert plan["lessons"][0]["identity"]["state"] == "review"
    assert plan["lessons"][0]["identity"]["reason"] == "subject_changed"


def test_equal_candidates_require_review_instead_of_a_greedy_identity_match():
    first = _identity_projection()["lessons"][0]
    second = {**copy.deepcopy(first), "id": "lesson-other", "seq": 2}
    baseline = {"lessons": [first, second]}
    current = copy.deepcopy(baseline)
    incoming_lesson = {
        **copy.deepcopy(first),
        "id": None,
        "incoming_key": "incoming-0001",
        "seq": 3,
    }

    plan = build_plan(baseline, current, {"lessons": [incoming_lesson]})

    incoming_plan = next(
        lesson for lesson in plan["lessons"] if lesson.get("incoming_key")
    )
    assert incoming_plan["identity"]["state"] == "review"
    assert incoming_plan["identity"]["reason"] == "ambiguous_match"
    assert {
        candidate["lesson_id"]
        for candidate in incoming_plan["identity"]["candidates"]
    } == {"lesson-stable", "lesson-other"}


def test_non_primary_identity_candidate_can_keep_content():
    first = _identity_projection()["lessons"][0]
    second = {**copy.deepcopy(first), "id": "lesson-other", "seq": 2}
    incoming_lesson = {
        **copy.deepcopy(first),
        "id": None,
        "incoming_key": "incoming-0001",
        "seq": 3,
    }
    plan = build_plan(
        {"lessons": [first, second]},
        {"lessons": copy.deepcopy([first, second])},
        {"lessons": [incoming_lesson]},
    )
    review = next(
        lesson for lesson in plan["lessons"] if lesson.get("incoming_key")
    )
    identity_decisions = _validated_identity_decisions(
        plan,
        {
            review["item_id"]: {
                "choice": "same",
                "lesson_id": "lesson-stable",
            }
        },
    )
    removed = next(lesson for lesson in plan["lessons"] if not lesson.get("incoming_key"))

    projection = _projection_from_decisions(
        plan,
        {removed["item_id"]: "keep"},
        {},
        identity_decisions,
    )

    assert [lesson["id"] for lesson in projection] == [
        "lesson-other",
        "lesson-stable",
    ]
    accepted = next(
        lesson for lesson in projection if lesson.get("_incoming_key")
    )
    assert accepted["id"] == "lesson-stable"


def test_unchanged_ambiguous_lesson_can_keep_its_current_identity():
    lesson = {
        "item_id": "lesson-0001",
        "kind": "lesson",
        "status": "unchanged",
        "current": {"id": "lesson-current", "title": "Aula", "sources": []},
        "incoming": {"title": "Aula", "sources": []},
        "identity": {
            "state": "review",
            "lesson_id": None,
            "reason": "ambiguous_match",
            "candidates": [{"lesson_id": "lesson-current"}],
        },
        "sources": [],
    }
    plan = {"lessons": [lesson]}

    identities = _validated_identity_decisions(
        plan,
        {lesson["item_id"]: {"choice": "keep"}},
        {},
    )
    projection = _projection_from_decisions(plan, {}, {}, identities)

    assert identities == {lesson["item_id"]: {"choice": "keep"}}
    assert projection[0]["id"] == "lesson-current"


def test_related_identity_cannot_displace_a_lesson_explicitly_kept():
    def review_lesson(item_id: str, current_id: str) -> dict:
        return {
            "item_id": item_id,
            "kind": "lesson",
            "status": "changed",
            "current": {"id": current_id, "title": item_id, "sources": []},
            "incoming": {"title": f"{item_id} nova", "sources": []},
            "identity": {
                "state": "review",
                "lesson_id": None,
                "reason": "ambiguous_match",
                "candidates": [{"lesson_id": "lesson-a"}],
            },
            "sources": [],
        }

    kept = review_lesson("lesson-0001", "lesson-a")
    related = review_lesson("lesson-0002", "lesson-b")
    plan = {"lessons": [kept, related]}

    with pytest.raises(ValueError, match="duas aulas diferentes"):
        _validated_identity_decisions(
            plan,
            {
                kept["item_id"]: {"choice": "keep"},
                related["item_id"]: {
                    "choice": "same",
                    "lesson_id": "lesson-a",
                },
            },
            {
                kept["item_id"]: "keep",
                related["item_id"]: "transition",
            },
        )


def test_fully_rewritten_and_moved_lesson_still_requires_identity_review():
    baseline = _identity_projection()
    current = copy.deepcopy(baseline)
    incoming = _identity_projection(
        lesson_id=None,
        title="Cerimônia de encerramento",
        description="Pesquisa qualitativa com usuários e síntese de entrevistas.",
    )
    incoming["lessons"][0].update({"week": 9, "seq": 9})

    plan = build_plan(baseline, current, incoming)

    incoming_plan = next(
        lesson for lesson in plan["lessons"] if lesson.get("incoming_key")
    )
    assert incoming_plan["identity"]["state"] == "review"
    assert incoming_plan["identity"]["reason"] == "no_confident_match"
    assert [
        candidate["lesson_id"]
        for candidate in incoming_plan["identity"]["candidates"]
    ] == ["lesson-stable"]


def test_related_added_lesson_claims_the_selected_removed_lesson_id():
    removed = {
        "item_id": "lesson-removed",
        "kind": "lesson",
        "status": "removed",
        "current": {"id": "lesson-stable", "title": "Aula antiga", "sources": []},
        "incoming": None,
        "identity": {
            "state": "removed",
            "lesson_id": "lesson-stable",
            "reason": "removed",
        },
        "sources": [],
    }
    added = {
        "item_id": "lesson-added",
        "kind": "lesson",
        "status": "added",
        "current": None,
        "incoming": {"id": None, "title": "Aula reescrita", "sources": []},
        "identity": {
            "state": "review",
            "lesson_id": None,
            "reason": "no_confident_match",
            "candidates": [{"lesson_id": "lesson-stable"}],
        },
        "sources": [],
    }
    plan = {"lessons": [removed, added]}
    identities = _validated_identity_decisions(
        plan,
        {
            added["item_id"]: {
                "choice": "same",
                "lesson_id": "lesson-stable",
            }
        },
        {removed["item_id"]: "transition", added["item_id"]: "transition"},
    )

    projection = _projection_from_decisions(
        plan,
        {removed["item_id"]: "transition", added["item_id"]: "transition"},
        {},
        identities,
    )

    assert [lesson["id"] for lesson in projection] == ["lesson-stable"]

    with pytest.raises(ValueError, match="duas aulas diferentes"):
        _validated_identity_decisions(
            plan,
            {
                added["item_id"]: {
                    "choice": "same",
                    "lesson_id": "lesson-stable",
                }
            },
            {removed["item_id"]: "keep", added["item_id"]: "transition"},
        )


def test_identical_institutional_workbook_preserves_manual_overlay_without_review(
    db, tmp_path: Path
):
    original = _workbook(tmp_path / "recon-original.xlsx")
    imported = import_workbook(
        db, original, "Reconciliação 1", require_syllabus_metadata=False
    )
    initial = get_syllabus_version(db, imported["syllabus_id"])
    curated = curate_syllabus(
        db,
        imported["syllabus_id"],
        imported["version_id"],
        _manual_projection(initial, url="https://example.com/manual"),
        note="Preserva a curadoria manual.",
    )
    current = get_syllabus_version(db, imported["syllabus_id"])
    reference_id = current["lessons"][0]["sources"][0]["reference_id"]
    update_source_review(
        db,
        imported["syllabus_id"],
        reference_id,
        {"validated": True, "complexity": "complex"},
    )

    preview = create_reconciliation(db, imported["syllabus_id"], original)

    assert preview["base_version_id"] == curated["version_id"]
    assert preview["summary"]["action_count"] == 0
    source = preview["lessons"][0]["sources"][0]
    assert source["status"] == "unchanged"
    assert source["incoming"]["url"] == "https://example.com/manual"
    assert source["incoming"]["hidden"] is True
    assert source["incoming"]["review"] == {
        "validated": True,
        "complexity": "complex",
    }

    result = apply_reconciliation(
        db, imported["syllabus_id"], preview["id"], {}, {}
    )
    assert result["unchanged"] is True
    assert result["version_id"] == curated["version_id"]
    recorded = get_reconciliation(db, imported["syllabus_id"], preview["id"])
    assert recorded["status"] == "applied"


def test_transition_applies_only_changed_workbook_fields_over_manual_settings(
    db, tmp_path: Path
):
    original = _workbook(tmp_path / "recon-delta-original.xlsx")
    incoming = _workbook(
        tmp_path / "recon-delta-incoming.xlsx",
        description="Descrição institucional nova",
    )
    imported = import_workbook(
        db, original, "Reconciliação 2", require_syllabus_metadata=False
    )
    initial = get_syllabus_version(db, imported["syllabus_id"])
    curate_syllabus(
        db,
        imported["syllabus_id"],
        imported["version_id"],
        _manual_projection(initial, url="https://example.com/manual-preservado"),
        note="Preserva a fonte manual durante a reconciliação.",
    )
    current = get_syllabus_version(db, imported["syllabus_id"])
    reference_id = current["lessons"][0]["sources"][0]["reference_id"]
    update_source_review(
        db,
        imported["syllabus_id"],
        reference_id,
        {"validated": True, "complexity": "simple"},
    )

    preview = create_reconciliation(db, imported["syllabus_id"], incoming)
    actions = [
        item
        for lesson in preview["lessons"]
        for item in (lesson, *lesson["sources"])
        if item["status"] != "unchanged"
    ]
    assert [(item["kind"], item["status"]) for item in actions] == [
        ("source", "changed")
    ]
    changed = actions[0]
    assert changed["incoming"]["description"] == "Descrição institucional nova"
    assert changed["incoming"]["url"] == "https://example.com/manual-preservado"
    assert changed["incoming"]["hidden"] is True

    result = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {changed["item_id"]: "transition"},
        {},
    )
    assert result["unchanged"] is False
    latest = get_syllabus_version(db, imported["syllabus_id"])
    source = latest["lessons"][0]["sources"][0]
    assert source["description"] == "Descrição institucional nova"
    assert source["url"] == "https://example.com/manual-preservado"
    assert source["hidden"] is True
    assert source["review"] == {"validated": False, "complexity": "simple"}

    repeated = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {changed["item_id"]: "transition"},
        {},
    )
    assert repeated["already_applied"] is True
    assert repeated["version_id"] == result["version_id"]


def test_reconciliation_reuses_stable_lesson_id_and_keeps_versions_scoped(
    db, tmp_path: Path
):
    original = _workbook(tmp_path / "stable-original.xlsx")
    incoming = _workbook(
        tmp_path / "stable-incoming.xlsx",
        lesson_title="Aula de arquitetura.",
        lesson_description="Descrição da aula.",
        description="Descrição institucional atualizada",
    )
    imported = import_workbook(db, original, "Identidade estável automática", require_syllabus_metadata=False)
    before = get_syllabus_version(db, imported["syllabus_id"])
    stable_id = before["lessons"][0]["id"]

    preview = create_reconciliation(db, imported["syllabus_id"], incoming)

    lesson = preview["lessons"][0]
    assert lesson["identity"]["state"] == "carried"
    actions = {
        item["item_id"]: "transition"
        for item in (lesson, *lesson["sources"])
        if item["status"] != "unchanged"
    }
    applied = apply_reconciliation(
        db, imported["syllabus_id"], preview["id"], actions, {}
    )
    after = get_syllabus_version(db, imported["syllabus_id"], applied["version_id"])
    historical = get_syllabus_version(
        db, imported["syllabus_id"], imported["version_id"]
    )

    assert after["lessons"][0]["id"] == stable_id
    assert historical["lessons"][0]["id"] == stable_id
    assert historical["lessons"][0]["sources"][0]["description"] == "Descrição original"
    assert after["lessons"][0]["sources"][0]["description"] == "Descrição institucional atualizada"
    assert historical["lessons"][0]["sources"][0]["reference_id"] != after["lessons"][0]["sources"][0]["reference_id"]


@pytest.mark.parametrize(
    ("identity_choice", "keeps_id"),
    [("same", True), ("new", False)],
)
def test_founder_resolves_large_lesson_change_as_same_or_new(
    db, tmp_path: Path, identity_choice: str, keeps_id: bool
):
    original = _workbook(tmp_path / f"review-{identity_choice}-original.xlsx")
    incoming = _workbook(
        tmp_path / f"review-{identity_choice}-incoming.xlsx",
        lesson_title="Estratégia comercial e canais de distribuição",
        lesson_description="Discute proposta de valor, precificação e canais de venda.",
    )
    imported = import_workbook(
        db, original, f"Identidade revisada {identity_choice}",
        require_syllabus_metadata=False,
    )
    before = get_syllabus_version(db, imported["syllabus_id"])
    old_id = before["lessons"][0]["id"]
    preview = create_reconciliation(db, imported["syllabus_id"], incoming)
    lesson = preview["lessons"][0]

    assert lesson["identity"]["state"] == "review"
    with pytest.raises(ValueError, match="identidades de aula sem decisão"):
        apply_reconciliation(
            db,
            imported["syllabus_id"],
            preview["id"],
            {lesson["item_id"]: "transition"},
            {},
        )

    applied = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {lesson["item_id"]: "transition"},
        {},
        {
            lesson["item_id"]: (
                {
                    "choice": "same",
                    "lesson_id": lesson["identity"]["candidates"][0]["lesson_id"],
                }
                if identity_choice == "same"
                else {"choice": "new"}
            )
        },
    )
    after = get_syllabus_version(db, imported["syllabus_id"], applied["version_id"])

    assert (after["lessons"][0]["id"] == old_id) is keeps_id
    recorded = get_reconciliation(db, imported["syllabus_id"], preview["id"])
    outcome = next(iter(recorded["decisions"]["identity_outcomes"].values()))
    assert outcome["outcome"] == f"founder_{identity_choice}"
    assert recorded["incoming"]["lessons"][0]["id"] is None
    assert recorded["decisions"]["accepted_incoming"]["lessons"][0]["id"] == after["lessons"][0]["id"]


def test_keeping_a_reviewed_lesson_is_an_explicit_noop(
    db, tmp_path: Path
):
    original = _workbook(tmp_path / "review-keep-original.xlsx")
    incoming = _workbook(
        tmp_path / "review-keep-incoming.xlsx",
        lesson_title="Estratégia comercial e canais de distribuição",
        lesson_description="Discute proposta de valor, precificação e canais de venda.",
    )
    imported = import_workbook(db, original, "Identidade revisada e mantida", require_syllabus_metadata=False)
    before = get_syllabus_version(db, imported["syllabus_id"])
    preview = create_reconciliation(db, imported["syllabus_id"], incoming)
    lesson = preview["lessons"][0]

    with pytest.raises(ValueError, match="aula mantida"):
        apply_reconciliation(
            db,
            imported["syllabus_id"],
            preview["id"],
            {lesson["item_id"]: "keep"},
            {},
            {lesson["item_id"]: {"choice": "new"}},
        )
    db.rollback()

    applied = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {lesson["item_id"]: "keep"},
        {},
        {lesson["item_id"]: {"choice": "keep"}},
    )

    assert applied["unchanged"] is True
    assert applied["version_id"] == before["version"]["id"]
    recorded = get_reconciliation(db, imported["syllabus_id"], preview["id"])
    outcome = next(iter(recorded["decisions"]["identity_outcomes"].values()))
    assert outcome["outcome"] == "founder_kept_current"
    assert outcome["lesson_id"] == before["lessons"][0]["id"]
    assert (
        recorded["decisions"]["accepted_incoming"]["lessons"][0]["id"]
        == before["lessons"][0]["id"]
    )


@pytest.mark.parametrize(
    ("identity_choice", "keeps_id"),
    [("same", True), ("new", False)],
)
def test_manual_lesson_version_requires_an_explicit_identity_choice(
    db, tmp_path: Path, identity_choice: str, keeps_id: bool
):
    original = _workbook(tmp_path / f"manual-identity-{identity_choice}-original.xlsx")
    incoming = _workbook(
        tmp_path / f"manual-identity-{identity_choice}-incoming.xlsx",
        lesson_title="Aula de arquitetura.",
        lesson_description="Descrição da aula.",
    )
    imported = import_workbook(
        db, original, f"Identidade da versão manual {identity_choice}",
        require_syllabus_metadata=False,
    )
    before = get_syllabus_version(db, imported["syllabus_id"])
    preview = create_reconciliation(db, imported["syllabus_id"], incoming)
    lesson = preview["lessons"][0]
    draft = {
        "title": "Aula de arquitetura montada",
        "kind": "Class",
        "subject": "SI",
        "description": "Versão montada pelo founder.",
    }

    with pytest.raises(ValueError, match="identidade.*sem decisão"):
        apply_reconciliation(
            db,
            imported["syllabus_id"],
            preview["id"],
            {lesson["item_id"]: "custom"},
            {lesson["item_id"]: draft},
            {},
        )

    applied = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {lesson["item_id"]: "custom"},
        {lesson["item_id"]: draft},
        {
            lesson["item_id"]: (
                {
                    "choice": "same",
                    "lesson_id": lesson["identity"]["lesson_id"],
                }
                if identity_choice == "same"
                else {"choice": "new"}
            )
        },
    )
    after = get_syllabus_version(db, imported["syllabus_id"], applied["version_id"])

    assert (after["lessons"][0]["id"] == before["lessons"][0]["id"]) is keeps_id


def test_type2_update_round_trips_after_new_identity_decision(
    db, tmp_path: Path, type2_workbook
):
    original = type2_workbook(tmp_path / "type2-original.xlsx")
    incoming = type2_workbook(
        tmp_path / "type2-incoming.xlsx",
        lesson_axis="Negócios",
    )
    imported = import_workbook(db, original, "GRAD CC07 estável", require_syllabus_metadata=False)
    before = get_syllabus_version(db, imported["syllabus_id"])
    preview = create_reconciliation(db, imported["syllabus_id"], incoming)
    lesson = preview["lessons"][0]

    assert lesson["identity"]["state"] == "review"
    assert lesson["identity"]["reason"] == "subject_changed"
    applied = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {lesson["item_id"]: "transition"},
        {},
        {lesson["item_id"]: {"choice": "new"}},
    )
    latest = get_syllabus_version(db, imported["syllabus_id"], applied["version_id"])

    assert latest["version"]["input_format"] == "projetos-21"
    assert latest["lessons"][0]["id"] != before["lessons"][0]["id"]
    assert latest["lessons"][0]["subject"] == "NEG"
    assert latest["lessons"][0]["subjects"] == [
        "Banco de dados relacional",
        "SQL Básico",
    ]
    exported = get_syllabus_workbook(db, applied["version_id"])
    round_trip = tmp_path / "type2-round-trip.xlsx"
    round_trip.write_bytes(exported["body"])
    parsed = parse_workbook(round_trip)
    assert parsed["format"] == "projetos-21"
    assert parsed["lessons"][0]["title"] == latest["lessons"][0]["title"]
    assert [
        source["title"] for source in parsed["lessons"][0]["source_references"]
    ] == ["Tutorial MySQL"]


def test_type2_update_accepts_realistic_long_lesson_descriptions(
    db, tmp_path: Path, type2_workbook
):
    original_description = "Infraestrutura, integração e observabilidade. " * 105
    incoming_description = original_description + "Revisão institucional pequena."
    original = type2_workbook(
        tmp_path / "type2-long-original.xlsx",
        lesson_description=original_description,
    )
    incoming = type2_workbook(
        tmp_path / "type2-long-incoming.xlsx",
        lesson_description=incoming_description,
    )
    imported = import_workbook(db, original, "GRAD CC07 descrição longa", require_syllabus_metadata=False)
    before = get_syllabus_version(db, imported["syllabus_id"])
    preview = create_reconciliation(db, imported["syllabus_id"], incoming)
    lesson = preview["lessons"][0]

    assert len(original_description) > 4000
    assert lesson["identity"]["state"] == "carried"
    result = apply_reconciliation(
        db,
        imported["syllabus_id"],
        preview["id"],
        {lesson["item_id"]: "transition"},
        {},
    )
    after = get_syllabus_version(db, imported["syllabus_id"], result["version_id"])

    assert after["lessons"][0]["id"] == before["lessons"][0]["id"]
    assert after["lessons"][0]["description"] == incoming_description
