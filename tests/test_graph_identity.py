import pytest

from universe.graph_identity import subject_graph_id_for, validate_graph_id


def test_graph_id_is_generated_from_institution_curriculum_and_lesson_subject():
    assert subject_graph_id_for(
        "inteli", "Sistemas de Informação · Módulo 7", "COM"
    ) == (
        "graph-inteli-sistemas-de-informacao-modulo-7-com"
    )


def test_long_graph_id_is_deterministically_bounded():
    first = subject_graph_id_for("inteli", "Nome muito longo " * 30, "MTF")
    second = subject_graph_id_for("inteli", "Nome muito longo " * 30, "MTF")

    assert first == second
    assert len(first) <= 128
    assert validate_graph_id(first) == first


@pytest.mark.parametrize("value", ["", "Bad ID", "1graph", "a" * 129])
def test_graph_id_validator_uses_the_companion_shape(value):
    with pytest.raises(ValueError, match="graph ID"):
        validate_graph_id(value)
