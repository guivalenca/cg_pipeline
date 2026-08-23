ALTER TABLE syllabus_lesson
    ADD COLUMN subjects TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];

UPDATE syllabus_lesson AS lesson
SET subjects = (
    SELECT coalesce(array_agg(topic ORDER BY ordinal), ARRAY[]::TEXT[]) AS subjects
    FROM (
        SELECT nullif(
            btrim(regexp_replace(part, '^\s*,\s*', '')),
            ''
        ) AS topic,
        ordinal
        FROM regexp_split_to_table(
            coalesce(lesson.fields->>'Assuntos', ''),
            E'[\r\n]+'
        ) WITH ORDINALITY AS split(part, ordinal)
    ) normalized
    WHERE topic IS NOT NULL
)
WHERE lesson.fields ? 'Assuntos';
