-- A Lesson keeps one id across immutable Syllabus Versions. The version id
-- selects an occurrence; the Lesson id selects its stable curricular identity.

ALTER TABLE syllabus_lesson_review
    ADD COLUMN version_id TEXT;

UPDATE syllabus_lesson_review review
SET version_id = lesson.version_id
FROM syllabus_lesson lesson
WHERE lesson.id = review.lesson_id;

ALTER TABLE syllabus_lesson_review
    ALTER COLUMN version_id SET NOT NULL,
    DROP CONSTRAINT syllabus_lesson_review_lesson_id_fkey,
    DROP CONSTRAINT syllabus_lesson_review_pkey;

ALTER TABLE syllabus_lesson
    DROP CONSTRAINT syllabus_lesson_pkey,
    ADD PRIMARY KEY (version_id, id);

CREATE INDEX syllabus_lesson_identity_idx
    ON syllabus_lesson (id, version_id);

ALTER TABLE syllabus_lesson_review
    ADD PRIMARY KEY (version_id, lesson_id),
    ADD FOREIGN KEY (version_id, lesson_id)
        REFERENCES syllabus_lesson (version_id, id);

CREATE OR REPLACE VIEW syllabus_item AS
SELECT legacy.id, legacy.version_id, legacy.week, legacy.seq, legacy.kind,
       legacy.title, legacy.description, legacy.parent_title, legacy.url,
       legacy.source_id, legacy.fields, legacy.created_at
FROM syllabus_item_legacy legacy
UNION ALL
SELECT lesson.id, lesson.version_id, lesson.week, lesson.seq, lesson.kind,
       lesson.title, lesson.description, NULL::text AS parent_title,
       NULL::text AS url, NULL::text AS source_id, lesson.fields,
       lesson.created_at
FROM syllabus_lesson lesson
UNION ALL
SELECT reference.id, reference.version_id, lesson.week, reference.seq,
       'Autoestudo'::text, reference.title, reference.description,
       lesson.title, reference.url, reference.source_id, reference.fields,
       reference.created_at
FROM syllabus_source_reference reference
JOIN syllabus_lesson lesson
  ON lesson.version_id = reference.version_id
 AND lesson.id = reference.lesson_id;
