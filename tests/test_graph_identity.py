import pytest

from universe.graph_identity import graph_id_for, validate_graph_id


def test_graph_id_is_generated_from_companion_institution_and_syllabus_name():
    assert graph_id_for("inteli", "Sistemas de Informação · Módulo 7") == (
        "graph-inteli-sistemas-de-informacao-modulo-7"
    )


def test_long_graph_id_is_deterministically_bounded():
    first = graph_id_for("inteli", "Nome muito longo " * 30)
    second = graph_id_for("inteli", "Nome muito longo " * 30)

    assert first == second
    assert len(first) == 128
    assert validate_graph_id(first) == first


@pytest.mark.parametrize("value", ["", "Bad ID", "1graph", "a" * 129])
def test_graph_id_validator_uses_the_companion_shape(value):
    with pytest.raises(ValueError, match="graph ID"):
        validate_graph_id(value)
