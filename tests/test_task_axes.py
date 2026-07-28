"""Pure consolidation of repeated task-axis judgments."""

import pytest

from universe.task_axes import derive_axes


def items(task_id, *verdicts):
    return [
        {
            "task_id": task_id,
            "result": {"verdict": verdict, "reason": "Because."},
        }
        for verdict in verdicts
    ]


def derive(modalities, knowledges):
    return derive_axes(
        [
            item
            for task_id, verdicts in modalities.items()
            for item in items(task_id, *verdicts)
        ],
        [
            item
            for task_id, verdicts in knowledges.items()
            for item in items(task_id, *verdicts)
        ],
    )


def test_unanimous_verdicts_have_no_split():
    assert derive(
        {"t01": ("explain",) * 3},
        {"t01": ("concept",) * 3},
    ) == [
        {
            "task_id": "t01",
            "modality": {
                "verdict": "explain",
                "split": False,
                "votes": ["explain", "explain", "explain"],
            },
            "knowledge": {
                "verdict": "concept",
                "split": False,
                "votes": ["concept", "concept", "concept"],
            },
            "grain_class": "concept-explain",
        }
    ]


def test_two_to_one_split_keeps_the_majority_and_sets_split():
    result = derive(
        {"t01": ("do", "explain", "do")},
        {"t01": ("procedure", "procedure", "concept")},
    )[0]

    assert result["modality"] == {
        "verdict": "do",
        "split": True,
        "votes": ["do", "explain", "do"],
    }
    assert result["knowledge"] == {
        "verdict": "procedure",
        "split": True,
        "votes": ["procedure", "procedure", "concept"],
    }


@pytest.mark.parametrize(
    ("knowledge", "modality", "grain_class"),
    [
        ("concept", "explain", "concept-explain"),
        ("concept", "do", "concept-apply"),
        ("procedure", "do", "procedure-do"),
        ("procedure", "explain", "procedure-explain"),
    ],
)
def test_composite_grain_classes(knowledge, modality, grain_class):
    result = derive(
        {"t01": (modality,) * 3},
        {"t01": (knowledge,) * 3},
    )[0]

    assert result["grain_class"] == grain_class


def test_three_way_split_raises_and_names_the_task():
    with pytest.raises(SystemExit, match=r"three-way split.*t01"):
        derive(
            {"t01": ("do", "explain", "unsure")},
            {"t01": ("concept",) * 3},
        )


@pytest.mark.parametrize(
    ("modalities", "knowledges"),
    [
        ({"t01": ("unsure", "unsure", "do")}, {"t01": ("concept",) * 3}),
        ({"t01": ("do",) * 3}, {"t01": ("unsure", "unsure", "procedure")}),
    ],
)
def test_unsure_majority_raises_and_names_the_task(modalities, knowledges):
    with pytest.raises(SystemExit, match=r"unsure majority.*t01"):
        derive(modalities, knowledges)


def test_missing_usable_verdict_raises_and_names_every_silent_task():
    modality_items = items("t01", "do", "do", "do") + [
        *items("t02", "explain", "explain"),
        {"task_id": "t02", "result": "unparseable"},
    ]
    knowledge_items = (
        items("t01", "concept", "concept", "concept")
        + items("t02", "procedure", "procedure", "procedure")
    )

    with pytest.raises(SystemExit, match=r"silence is not a verdict.*t02"):
        derive_axes(modality_items, knowledge_items)


def test_fact_verdict_from_retired_module_raises():
    with pytest.raises(
        SystemExit,
        match=(
            "Fact verdict encountered from retired task-fact module; "
            "cannot mix retired-class runs into derivation"
        ),
    ):
        derive(
            {"t01": ("do",) * 3},
            {"t01": ("fact",) * 3},
        )
