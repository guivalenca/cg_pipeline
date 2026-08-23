UPDATE syllabus_lesson
SET subject = CASE lower(btrim(subject))
    WHEN 'computação' THEN 'COM'
    WHEN 'computacao' THEN 'COM'
    WHEN 'liderança' THEN 'LID'
    WHEN 'lideranca' THEN 'LID'
    WHEN 'negócios' THEN 'NEG'
    WHEN 'negocios' THEN 'NEG'
    WHEN 'user experience' THEN 'UEX'
END
WHERE lower(btrim(subject)) IN (
    'computação', 'computacao',
    'liderança', 'lideranca',
    'negócios', 'negocios',
    'user experience'
);

UPDATE syllabus_lesson
SET kind = CASE lower(btrim(kind))
    WHEN 'avaliação / pesquisa' THEN 'Evaluation'
    WHEN 'avaliacao / pesquisa' THEN 'Evaluation'
    WHEN 'desenvolvimento projeto' THEN 'Deliverable'
    WHEN 'encontro de instrução' THEN 'Class'
    WHEN 'encontro de instrucao' THEN 'Class'
    WHEN 'encontro de orientação' THEN 'Orientation'
    WHEN 'encontro de orientacao' THEN 'Orientation'
END
WHERE lower(btrim(kind)) IN (
    'avaliação / pesquisa', 'avaliacao / pesquisa',
    'desenvolvimento projeto',
    'encontro de instrução', 'encontro de instrucao',
    'encontro de orientação', 'encontro de orientacao'
);
