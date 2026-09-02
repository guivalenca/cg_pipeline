from universe import org


def test_syllabus_groups_returns_only_assigned_group_and_institution_labels(db):
    db.execute(
        "INSERT INTO institution (id, name) VALUES"
        " ('org-inteli', 'Inteli'), ('org-other', 'Outra instituição')"
    )
    db.execute(
        "INSERT INTO study_group (id, institution_id, name) VALUES"
        " ('org-cc07', 'org-inteli', 'CC07'),"
        " ('org-other-group', 'org-other', 'Outro grupo')"
    )
    db.execute(
        "INSERT INTO syllabus (id, title, institution_id, group_id) VALUES"
        " ('org-assigned', 'Syllabus atribuído', 'org-inteli', 'org-cc07'),"
        " ('org-unassigned', 'Syllabus sem grupo', 'org-inteli', NULL)"
    )

    assert org.syllabus_groups(db) == {
        "org-assigned": {
            "group_id": "org-cc07",
            "group_name": "CC07",
            "institution_id": "org-inteli",
            "institution_name": "Inteli",
        }
    }
