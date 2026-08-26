/*
 * Adalove observer workbook exporter.
 *
 * Run this entire file in the Safari Web Inspector console while the intended
 * Adalove section is open. It reads only the signed-in observer session and
 * downloads one XLSX file. It never logs or writes the session token.
 */
(function installAdaloveObserverExporter() {
  'use strict';

  const API_BASE = 'https://apiv2.inteli.edu.br';
  const EXCELJS_URL = 'https://cdn.jsdelivr.net/npm/exceljs@4.4.0/dist/exceljs.min.js';
  const COGNITO_CLIENT_ID = '6v6iqlcv6hl5p3u628geho1cjp';
  const TYPE_CAPTIONS = {
    1: 'Encontro de orientação',
    2: 'Encontro de instrução',
    11: 'Autoestudo',
    21: 'Desenvolvimento projeto',
    31: 'Avaliação / pesquisa',
  };
  const TYPE_NAMES = {
    1: 'Orientation',
    2: 'Class',
    11: 'Self-study',
    21: 'Deliverable',
    31: 'Evaluation',
  };
  // Keep this aligned with PROJECT_SUBJECTS in
  // concept-universe/src/universe/syllabus.py and SUBJECT_THEMES in
  // companion/static/js/subject_theme.js until "Unify subject identities
  // under institutions" replaces the cross-repository copies.
  const AXIS_CAPTIONS = {
    COM: 'Computação',
    LID: 'Liderança',
    NEG: 'Negócios',
    UEX: 'User Experience',
    MTF: 'Matemática',
  };
  const ANCHOR_TYPES = new Set([1, 2]);
  const STATUS_KEY = 'adaloveObserverExportStatus';

  const DEFAULT_CONFIG = Object.freeze({
    concurrency: 8,
    detailRetries: 2,
    orderingSnapshots: 3,
    weeks: [],
    limit: null,
    includeDescriptionLinks: true,
  });

  const log = (...args) => console.log('[adalove-observer-export]', ...args);
  const warn = (...args) => console.warn('[adalove-observer-export]', ...args);
  const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
  const clean = value => String(value == null ? '' : value).replace(/\s+/g, ' ').trim();
  const asNumber = value => {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  };
  const yesNo = value => (value === true || value === 1 || value === '1' ? 'Sim' : 'Não');
  const uniq = values => [...new Set(values.filter(Boolean))];
  const safeFilename = value => clean(value || 'adalove').replace(/[\\/:*?"<>|]+/g, '-');
  const safeSheetName = value => clean(value || 'Sheet').replace(/[:\\/?*\[\]]/g, ' ').slice(0, 31);
  const weekNumber = caption => {
    const match = clean(caption).match(/(\d+)/);
    return match ? Number(match[1]) : 0;
  };
  const formatDate = value => {
    if (!value) return '';
    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) return `${match[3]}/${match[2]}/${match[1]}`;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('pt-BR');
  };
  const stripHtml = value => {
    if (!value) return '';
    const element = document.createElement('div');
    element.innerHTML = String(value);
    return clean(element.textContent || element.innerText || '');
  };
  const parseStoredValue = value => {
    if (!value) return '';
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  };
  const uuidFromStoredSection = value => {
    const parsed = parseStoredValue(value);
    if (typeof parsed === 'string') return parsed;
    return parsed?.sectionUuid || parsed?.section_uuid || parsed?.uuid || '';
  };
  const activityType = summary => asNumber(summary?.activityType ?? summary?.type);
  const activityUuid = summary => clean(
    summary?.activityUuid ?? summary?.activityUUID ?? summary?.activity_uuid ?? summary?.uuid,
  );
  const activityCaption = summary => stripHtml(summary?.activityCaption ?? summary?.caption ?? summary?.title);
  const folderCaption = summary => clean(summary?.folderCaption ?? summary?.folder?.caption);
  const folderUuid = summary => clean(summary?.folderUuid ?? summary?.folder?.uuid);
  const weekOrder = summary => asNumber(summary?.sort) || weekNumber(folderCaption(summary));
  const withinWeekOrder = summary => asNumber(summary?.activitySort ?? summary?.activity_sort ?? summary?.sort);
  const orderCompare = (left, right) => (
    weekOrder(left) - weekOrder(right)
    || withinWeekOrder(left) - withinWeekOrder(right)
    || activityUuid(left).localeCompare(activityUuid(right))
  );
  const orderSignature = summaries => summaries
    .slice()
    .sort(orderCompare)
    .map(summary => `${folderUuid(summary)}|${withinWeekOrder(summary)}|${activityUuid(summary)}`)
    .join('\n');
  const rawSignature = summaries => summaries.map(activityUuid).join('\n');

  const readAuth = () => {
    const authUser = localStorage.getItem(
      `CognitoIdentityServiceProvider.${COGNITO_CLIENT_ID}.LastAuthUser`,
    );
    const cognitoToken = authUser
      ? localStorage.getItem(
        `CognitoIdentityServiceProvider.${COGNITO_CLIENT_ID}.${authUser}.accessToken`,
      )
      : '';
    return {
      sectionUuid: uuidFromStoredSection(localStorage.getItem('@buzz:currentSection')),
      token: localStorage.getItem('@buzz:token') || cognitoToken || '',
      mfaToken: localStorage.getItem('@buzz:token-mfa') || '',
    };
  };
  const headersFromAuth = auth => ({
    Accept: 'application/json',
    Authorization: `Bearer ${auth.token}`,
    ...(auth.mfaToken ? { 'X-MFA-Token': `Bearer ${auth.mfaToken}` } : {}),
  });

  const fetchJson = async (url, headers, retries = 0) => {
    let lastError = null;
    for (let attempt = 0; attempt <= retries; attempt += 1) {
      try {
        const response = await fetch(url, { headers });
        const text = await response.text();
        let payload = null;
        try {
          payload = text ? JSON.parse(text) : null;
        } catch {
          payload = text;
        }
        if (!response.ok) {
          throw new Error(`HTTP ${response.status} for ${new URL(url).pathname}`);
        }
        return payload;
      } catch (error) {
        lastError = error;
        if (attempt < retries) await sleep(300 * (2 ** attempt));
      }
    }
    throw lastError;
  };

  const mapWithConcurrency = async (items, concurrency, worker, onProgress) => {
    const results = new Array(items.length);
    let cursor = 0;
    let completed = 0;
    async function runWorker() {
      while (cursor < items.length) {
        const index = cursor;
        cursor += 1;
        results[index] = await worker(items[index], index);
        completed += 1;
        onProgress?.(completed, items.length);
      }
    }
    const workers = Array.from(
      { length: Math.min(Math.max(1, concurrency), Math.max(1, items.length)) },
      runWorker,
    );
    await Promise.all(workers);
    return results;
  };

  const extractHtmlLinks = html => {
    if (!html) return [];
    const element = document.createElement('div');
    element.innerHTML = String(html);
    return [...element.querySelectorAll('a[href]')].map(anchor => ({
      url: clean(anchor.href),
      label: clean(anchor.textContent),
      source: 'description',
    }));
  };
  const extractTextLinks = html => {
    if (!html) return [];
    const element = document.createElement('div');
    element.innerHTML = String(html);
    const text = element.textContent || element.innerText || '';
    const matches = text.match(/https?:\/\/[^\s<>"']+/gi) || [];
    return matches.map(url => ({
      url: url.replace(/[.,;:!?]+$/, ''),
      label: '',
      source: 'description_text',
      path: 'description:text',
    }));
  };
  const looksLikeUrl = value => /^(https?:\/\/|www\.)/i.test(clean(value));
  const materialLabel = value => {
    if (!value || typeof value !== 'object') return '';
    const keys = ['caption', 'title', 'name', 'label', 'description', 'book', 'video'];
    for (const key of keys) {
      if (typeof value[key] === 'string' && clean(value[key])) return stripHtml(value[key]);
    }
    return '';
  };
  const collectMaterialLinks = (detail, includeDescriptionLinks) => {
    const records = [];
    const seenObjects = new WeakSet();
    const push = record => {
      const url = clean(record.url);
      if (!looksLikeUrl(url)) return;
      records.push({
        url: url.startsWith('www.') ? `https://${url}` : url,
        label: clean(record.label),
        source: clean(record.source),
        path: clean(record.path),
      });
    };
    if (detail?.basic_activity_url) {
      push({
        url: detail.basic_activity_url,
        label: detail.caption,
        source: 'basic_activity_url',
        path: 'basic_activity_url',
      });
    }
    const visit = (value, path = 'activityStudyMaterials', depth = 0) => {
      if (value == null || depth > 8) return;
      if (typeof value === 'string') {
        if (looksLikeUrl(value)) push({ url: value, source: 'study_material', path });
        return;
      }
      if (typeof value !== 'object') return;
      if (seenObjects.has(value)) return;
      seenObjects.add(value);
      if (Array.isArray(value)) {
        value.forEach((item, index) => visit(item, `${path}.${index}`, depth + 1));
        return;
      }
      const label = materialLabel(value);
      for (const [key, child] of Object.entries(value)) {
        const childPath = `${path}.${key}`;
        if (typeof child === 'string' && /url|link|href/i.test(key)) {
          push({ url: child, label, source: 'study_material', path: childPath });
        } else {
          visit(child, childPath, depth + 1);
        }
      }
    };
    visit(detail?.activityStudyMaterials || []);
    if (includeDescriptionLinks) {
      extractHtmlLinks(detail?.description).forEach(push);
      extractTextLinks(detail?.description).forEach(push);
    }
    const unique = new Map();
    for (const record of records) {
      const key = `${record.url}|${record.source}|${record.path}`;
      if (!unique.has(key)) unique.set(key, record);
    }
    return [...unique.values()];
  };
  const resourceCode = value => {
    const text = String(value || '');
    const urls = text.match(
      /https?:\/\/integrada\.minhabiblioteca\.com\.br[^\s<>"']*/gi,
    ) || [];
    for (const rawUrl of urls) {
      try {
        const parsed = new URL(rawUrl.replace(/[.,;:!?]+$/, ''));
        const route = decodeURIComponent(`${parsed.pathname}${parsed.hash}`);
        const match = route.match(/\/books\/([0-9Xx-]{10,25})/i);
        if (match) return match[1];
      } catch {
        // Keep looking: descriptions can contain malformed URLs next to a valid one.
      }
    }
    return '';
  };
  const isVideoUrl = url => /(?:youtube\.com|youtu\.be|vimeo\.com|wistia\.)/i.test(url || '');
  const detailSectionActivity = (detail, sectionUuid) => {
    const items = Array.isArray(detail?.sectionActivities) ? detail.sectionActivities : [];
    return items.find(item => clean(item?.section?.uuid) === sectionUuid) || items[0] || {};
  };
  const relatedSubjects = detail => (Array.isArray(detail?.subjects) ? detail.subjects : [])
    .map(subject => ({
      uuid: clean(subject?.uuid ?? subject?.subjectUuid),
      caption: stripHtml(subject?.subject ?? subject?.caption ?? subject?.name),
    }))
    .filter(subject => subject.caption);

  const normalizeActivity = (summary, detail, detailError, sectionUuid, config) => {
    const typeCode = activityType(summary) || asNumber(detail?.activityType?.uuid);
    const sectionActivity = detailSectionActivity(detail, sectionUuid);
    const summaryDateTime = clean(
      summary?.sectionActivityDateTime ?? summary?.date ?? summary?.section_activity_date_time,
    );
    const detailDateTime = clean(sectionActivity?.date);
    const subjects = relatedSubjects(detail);
    const materials = collectMaterialLinks(detail, config.includeDescriptionLinks);
    const professor = sectionActivity?.professor || {};
    const assistant = sectionActivity?.assistant || {};
    const firstUrl = clean(detail?.basic_activity_url) || materials[0]?.url || '';
    const extractedResourceCode = [
      firstUrl,
      ...materials.map(material => material.url),
      detail?.description,
      summary?.description,
    ].map(resourceCode).find(Boolean) || '';
    const inClassActivity = detail?.in_class_activity === true
      || detail?.in_class_activity === 1
      || detail?.in_class_activity === '1';
    const comparableSummaryDate = summaryDateTime ? new Date(summaryDateTime).getTime() : null;
    const comparableDetailDate = detailDateTime ? new Date(detailDateTime).getTime() : null;
    return {
      summary,
      detail,
      detail_error: detailError,
      section_uuid: sectionUuid,
      folder_uuid: folderUuid(summary) || clean(detail?.folder?.uuid),
      activity_uuid: activityUuid(summary) || clean(detail?.uuid),
      week: folderCaption(summary) || clean(detail?.folder?.caption),
      week_order: weekOrder(summary),
      activity_order: withinWeekOrder(summary),
      type_code: typeCode,
      type: TYPE_NAMES[typeCode] || clean(detail?.activityType?.caption) || `type_${typeCode}`,
      type_caption: clean(detail?.activityType?.caption) || TYPE_CAPTIONS[typeCode] || `Tipo ${typeCode}`,
      title: activityCaption(summary) || stripHtml(detail?.caption),
      description: stripHtml(detail?.description ?? summary?.description),
      summary_datetime: summaryDateTime,
      detail_datetime: detailDateTime,
      date: formatDate(detailDateTime || summaryDateTime),
      datetime_disagrees: comparableSummaryDate != null
        && comparableDetailDate != null
        && comparableSummaryDate !== comparableDetailDate,
      professor: clean(professor?.name ?? summary?.sectionInstructorName ?? summary?.professorName),
      professor_uuid: clean(professor?.uuid ?? summary?.sectionInstructorUuid),
      assistant: clean(
        assistant?.name
        ?? summary?.sectionAssistantInstructorName
        ?? summary?.assistantInstructorName,
      ),
      assistant_uuid: clean(
        assistant?.uuid
        ?? summary?.sectionAssistantInstructorUuId
        ?? summary?.sectionAssistantInstructorUuid,
      ),
      lesson_subject_code: clean(summary?.axisCaption),
      subjects,
      materials,
      primary_url: firstUrl,
      resource_code: extractedResourceCode,
      study_question: stripHtml(detail?.study_question),
      study_answer: stripHtml(detail?.study_answer),
      required: detail?.required ?? summary?.required ?? 0,
      grade_weight: detail?.grade_weight ?? summary?.gradeWeight ?? 0,
      duration_minutes: clean(detail?.duration),
      in_class_activity: inClassActivity,
      study_type: clean(detail?.study_type),
      exam: detail?.exam ?? 0,
      makeup_exam: detail?.makeup_exam ?? 0,
      has_makeup_exam_capability: detail?.has_makeup_exam ?? false,
      active: summary?.active ?? '',
      clipboard_uuid: clean(detail?.clipboard_uuid),
      ai_assessment_uuid: clean(detail?.ai_assessment_uuid),
      parent_activity_uuid: '',
      parent_title: '',
      parent_date: '',
      parent_inference: '',
    };
  };

  const inferSelfStudyParents = activities => {
    let currentWeek = null;
    let lastAnchor = null;
    for (const activity of activities) {
      if (activity.folder_uuid !== currentWeek) {
        currentWeek = activity.folder_uuid;
        lastAnchor = null;
      }
      if (ANCHOR_TYPES.has(activity.type_code)) {
        lastAnchor = activity;
        continue;
      }
      if (activity.type_code === 11 && lastAnchor) {
        activity.parent_activity_uuid = lastAnchor.activity_uuid;
        activity.parent_title = lastAnchor.title;
        activity.parent_date = lastAnchor.date;
        activity.parent_inference = 'inferred_from_activity_order';
      } else if (activity.type_code === 11) {
        activity.parent_inference = 'no_preceding_anchor_in_week';
      }
    }
  };

  const buildOrderAudit = activities => {
    const counts = new Map();
    for (const activity of activities) {
      const key = `${activity.folder_uuid}|${activity.activity_order}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    const missingByWeek = new Map();
    const byWeek = new Map();
    for (const activity of activities) {
      if (!byWeek.has(activity.folder_uuid)) byWeek.set(activity.folder_uuid, []);
      byWeek.get(activity.folder_uuid).push(activity.activity_order);
    }
    for (const [weekUuid, values] of byWeek) {
      const uniqueValues = [...new Set(values)].sort((a, b) => a - b);
      const missing = [];
      for (let value = uniqueValues[0]; value <= uniqueValues.at(-1); value += 1) {
        if (!uniqueValues.includes(value)) missing.push(value);
      }
      missingByWeek.set(weekUuid, missing.join(', '));
    }
    return activities.map((activity, index) => {
      const key = `${activity.folder_uuid}|${activity.activity_order}`;
      return {
        week: activity.week,
        week_order: activity.week_order,
        activity_order: activity.activity_order,
        order_key: `${activity.week_order}:${activity.activity_order}`,
        duplicate_order_key: counts.get(key) > 1 ? 'yes' : 'no',
        missing_orders_in_week: missingByWeek.get(activity.folder_uuid),
        activity_uuid: activity.activity_uuid,
        folder_uuid: activity.folder_uuid,
        type: activity.type,
        title: activity.title,
        datetime_disagrees: activity.datetime_disagrees ? 'yes' : 'no',
        parent_inference: activity.parent_inference,
        detail_error: activity.detail_error,
      };
    });
  };

  const loadExcelJs = async () => {
    if (window.ExcelJS) return;
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = EXCELJS_URL;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Failed to load ExcelJS from jsDelivr.'));
      document.head.appendChild(script);
    });
  };

  const HEADER_FILL = 'FF2E2640';
  const HEADER_FONT = 'FFFFFFFF';
  const ALT_ROW_FILL = 'FFF7F5FA';
  const BORDER_COLOR = 'FFE1DDE8';
  const styleSheet = (worksheet, columns) => {
    const header = worksheet.getRow(1);
    header.height = 28;
    header.eachCell(cell => {
      cell.font = { name: 'Calibri', bold: true, color: { argb: HEADER_FONT }, size: 11 };
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: HEADER_FILL } };
      cell.alignment = { vertical: 'middle', horizontal: 'left', wrapText: true };
      cell.border = { bottom: { style: 'medium', color: { argb: HEADER_FILL } } };
    });
    worksheet.eachRow((row, rowNumber) => {
      if (rowNumber === 1) return;
      row.height = 22;
      columns.forEach((column, index) => {
        const cell = row.getCell(index + 1);
        cell.font = { name: 'Calibri', size: 10 };
        cell.alignment = {
          vertical: 'top',
          horizontal: column.align || 'left',
          wrapText: column.wrap !== false,
        };
        cell.border = { bottom: { style: 'thin', color: { argb: BORDER_COLOR } } };
        if (rowNumber % 2 === 1) {
          cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: ALT_ROW_FILL } };
        }
        if (column.text) {
          if (cell.value != null) cell.value = String(cell.value);
          cell.numFmt = '@';
        }
        if (column.hyperlink && looksLikeUrl(cell.value)) {
          const url = cell.value;
          cell.value = { text: url, hyperlink: url };
          cell.font = { name: 'Calibri', size: 10, color: { argb: 'FF1A56DB' }, underline: 'single' };
        }
      });
    });
    worksheet.autoFilter = {
      from: { row: 1, column: 1 },
      to: { row: 1, column: columns.length },
    };
  };
  const addSheet = (workbook, name, columns, rows) => {
    const worksheet = workbook.addWorksheet(safeSheetName(name), {
      views: [{ state: 'frozen', ySplit: 1 }],
    });
    worksheet.columns = columns.map(column => ({
      header: column.header,
      key: column.key,
      width: column.width || 18,
      ...(column.text ? { style: { numFmt: '@' } } : {}),
    }));
    rows.forEach(row => worksheet.addRow(Object.fromEntries(
      Object.entries(row).map(([key, value]) => [key, value === '' ? null : value]),
    )));
    styleSheet(worksheet, columns);
    return worksheet;
  };

  const activitiesColumns = [
    { header: 'Activity order', key: 'activity_order', width: 13, align: 'center' },
    { header: 'Week', key: 'week_order', width: 9, align: 'center' },
    { header: 'Type', key: 'type', width: 14 },
    { header: 'Original label', key: 'type_caption', width: 23 },
    { header: 'Title', key: 'title', width: 46 },
    { header: 'Description', key: 'description', width: 70 },
    { header: 'Date', key: 'date', width: 12 },
    { header: 'Professor', key: 'professor', width: 28 },
    { header: 'Professor UUID', key: 'professor_uuid', width: 34 },
    { header: 'Assistant', key: 'assistant', width: 28 },
    { header: 'Assistant UUID', key: 'assistant_uuid', width: 34 },
    { header: 'Lesson Subject code', key: 'lesson_subject_code', width: 20 },
    { header: 'Related subjects', key: 'related_subjects', width: 48 },
    { header: 'Primary URL', key: 'primary_url', width: 48, hyperlink: true },
    { header: 'Resource code', key: 'resource_code', width: 22, text: true },
    { header: 'Study question', key: 'study_question', width: 55 },
    { header: 'Study answer / rubric', key: 'study_answer', width: 55 },
    { header: 'Required', key: 'required', width: 10 },
    { header: 'Grade weight', key: 'grade_weight', width: 13 },
    { header: 'Duration minutes', key: 'duration_minutes', width: 16 },
    { header: 'Self-study schedule', key: 'study_type', width: 20 },
    { header: 'Exam', key: 'exam', width: 9 },
    { header: 'Makeup exam', key: 'makeup_exam', width: 13 },
    { header: 'Parent activity UUID', key: 'parent_activity_uuid', width: 34, text: true },
    { header: 'Parent title', key: 'parent_title', width: 45 },
    { header: 'Parent date', key: 'parent_date', width: 12 },
    { header: 'Parent inference', key: 'parent_inference', width: 31 },
    { header: 'Activity UUID', key: 'activity_uuid', width: 34, text: true },
    { header: 'Folder UUID', key: 'folder_uuid', width: 34, text: true },
    { header: 'Section UUID', key: 'section_uuid', width: 34, text: true },
    { header: 'Active', key: 'active', width: 9 },
    { header: 'Detail error', key: 'detail_error', width: 35 },
  ];
  const type2Columns = [
    'Projeto',
    'Semana',
    'Ordem',
    'Atividade',
    'Tipo da atividade',
    'Descrição da atividade',
    'Questão do autoestudo',
    'Barema do autoestudo',
    'Atividade obrigatória',
    'Peso da atividade',
    'Eixo',
    'Assuntos',
    'URL',
    'Ponderada aplicada em sala',
    'Encontro pai',
    'Prova',
    'Prova substitutiva',
    'Material de estudo',
    'Material em vídeo',
    'Duração em minutos',
    'Atividade verificada',
  ].map(header => ({ header, key: header, width: Math.min(65, Math.max(12, header.length + 4)) }));

  const buildWorkbook = async (data, activities, audit, snapshots, detailErrors) => {
    await loadExcelJs();
    const workbook = new window.ExcelJS.Workbook();
    workbook.creator = 'Adalove Observer Exporter';
    workbook.created = new Date();
    const section = data.section || {};
    const projectCaption = clean(section.projectCaption);
    const activityRows = activities.map(activity => ({
      ...activity,
      related_subjects: activity.subjects.map(subject => subject.caption).join('; '),
      required: yesNo(activity.required),
      study_type: activity.study_type === 'class'
        ? 'In class'
        : (activity.study_type === 'weekly' ? 'Weekly' : activity.study_type),
      exam: yesNo(activity.exam),
      makeup_exam: yesNo(activity.makeup_exam),
    }));
    addSheet(workbook, 'Activities', activitiesColumns, activityRows);

    const subjectRows = activities.flatMap(activity => activity.subjects.map(subject => ({
      activity_uuid: activity.activity_uuid,
      week: activity.week_order,
      activity_order: activity.activity_order,
      activity_title: activity.title,
      lesson_subject_code: activity.lesson_subject_code,
      subject_uuid: subject.uuid,
      subject: subject.caption,
    })));
    addSheet(workbook, 'Subjects', [
      { header: 'Activity order', key: 'activity_order', width: 13 },
      { header: 'Week', key: 'week', width: 9 },
      { header: 'Activity UUID', key: 'activity_uuid', width: 34, text: true },
      { header: 'Activity title', key: 'activity_title', width: 48 },
      { header: 'Lesson Subject code', key: 'lesson_subject_code', width: 20 },
      { header: 'Subject UUID', key: 'subject_uuid', width: 34, text: true },
      { header: 'Related subject', key: 'subject', width: 50 },
    ], subjectRows);

    const materialRows = activities.flatMap(activity => activity.materials.map(material => ({
      activity_uuid: activity.activity_uuid,
      week: activity.week_order,
      activity_order: activity.activity_order,
      activity_title: activity.title,
      label: material.label,
      url: material.url,
      source: material.source,
      source_path: material.path,
      resource_code: resourceCode(material.url),
      video: yesNo(isVideoUrl(material.url)),
    })));
    addSheet(workbook, 'Materials', [
      { header: 'Activity order', key: 'activity_order', width: 13 },
      { header: 'Week', key: 'week', width: 9 },
      { header: 'Activity UUID', key: 'activity_uuid', width: 34, text: true },
      { header: 'Activity title', key: 'activity_title', width: 48 },
      { header: 'Label', key: 'label', width: 40 },
      { header: 'URL', key: 'url', width: 60, hyperlink: true },
      { header: 'Source', key: 'source', width: 20 },
      { header: 'Source path', key: 'source_path', width: 42 },
      { header: 'Resource code', key: 'resource_code', width: 22, text: true },
      { header: 'Video', key: 'video', width: 10 },
    ], materialRows);

    addSheet(workbook, 'Order audit', [
      { header: 'Activity order', key: 'activity_order', width: 13 },
      { header: 'Week', key: 'week_order', width: 9 },
      { header: 'Order key', key: 'order_key', width: 12 },
      { header: 'Duplicate order key', key: 'duplicate_order_key', width: 20 },
      { header: 'Missing orders in week', key: 'missing_orders_in_week', width: 23 },
      { header: 'Activity UUID', key: 'activity_uuid', width: 34, text: true },
      { header: 'Folder UUID', key: 'folder_uuid', width: 34, text: true },
      { header: 'Type', key: 'type', width: 14 },
      { header: 'Title', key: 'title', width: 50 },
      { header: 'Parent inference', key: 'parent_inference', width: 31 },
      { header: 'Detail error', key: 'detail_error', width: 35 },
    ], audit);

    const type2Rows = activities.map(activity => {
      const explicitStudyMaterials = activity.materials.filter(
        material => material.source === 'study_material',
      );
      const hasStudyMaterial = explicitStudyMaterials.some(material => !isVideoUrl(material.url));
      const hasVideoMaterial = explicitStudyMaterials.some(material => isVideoUrl(material.url));
      return {
        Projeto: projectCaption,
        Semana: activity.week,
        Ordem: String(activity.activity_order),
        Atividade: activity.title,
        'Tipo da atividade': activity.type_caption,
        'Descrição da atividade': activity.description,
        'Questão do autoestudo': activity.study_question,
        'Barema do autoestudo': activity.study_answer,
        'Atividade obrigatória': yesNo(activity.required),
        'Peso da atividade': activity.grade_weight,
        Eixo: AXIS_CAPTIONS[activity.lesson_subject_code] || activity.lesson_subject_code,
        Assuntos: activity.subjects.map(subject => subject.caption).join('; '),
        URL: activity.primary_url,
        'Ponderada aplicada em sala': yesNo(activity.in_class_activity),
        'Encontro pai': activity.parent_title,
        Prova: yesNo(activity.exam),
        'Prova substitutiva': yesNo(activity.makeup_exam),
        'Material de estudo': yesNo(hasStudyMaterial),
        'Material em vídeo': yesNo(hasVideoMaterial),
        'Duração em minutos': activity.duration_minutes,
        'Atividade verificada': 'Não',
      };
    });
    addSheet(workbook, 'Type 2 compatible', type2Columns, type2Rows);

    const duplicateOrderKeys = audit.filter(row => row.duplicate_order_key === 'yes').length;
    const datetimeDisagreements = activities.filter(activity => activity.datetime_disagrees).length;
    const unparentedSelfStudies = activities.filter(
      activity => activity.type_code === 11 && !activity.parent_activity_uuid,
    ).length;
    const readMeRows = [
      ['Exported at', new Date().toISOString()],
      ['Section', clean(section.sectionCaption)],
      ['Section UUID', clean(section.sectionUuid)],
      ['Project', projectCaption],
      ['Project UUID', clean(section.projectUuid)],
      ['Section last update', clean(section.sectionLastUpdate)],
      ['Section last sync', clean(section.sectionLastSync)],
      ['Activity count', activities.length],
      ['Detail fetch errors', detailErrors],
      ['Subject rows', subjectRows.length],
      ['Material rows', materialRows.length],
      ['Ordering snapshots', snapshots.length],
      ['Sorted order stable across snapshots', snapshots.sortedStable ? 'yes' : 'no'],
      ['Raw API order stable across snapshots', snapshots.rawStable ? 'yes' : 'no'],
      ['Duplicate (folder UUID, activity order) keys', duplicateOrderKeys],
      ['Summary/detail datetime disagreements', datetimeDisagreements],
      ['Self-studies without preceding anchor', unparentedSelfStudies],
      ['Ordering rule', 'week sort, then activity sort, then activity UUID only as a deterministic tie-break'],
      ['Ordering scope', 'Reliable for this exported snapshot; compare UUID + order key between exports to detect later edits.'],
      ['Parent rule', 'Only self-studies are linked to the preceding orientation/class in the same week. This is inferred from activity order; Adalove does not expose an explicit parent field to observers.'],
      ['Date rule', 'The exported Date uses the activity detail response. The list response differs by exactly three hours for all scheduled classes/orientations, consistent with a timezone serialization difference.'],
      ['Self-study schedule', 'Adalove exposes this only for self-studies. The exporter translates class to In class and weekly to Weekly. Non-self-study activities leave it blank.'],
      ['Week', 'Numeric Adalove week order. The human folder caption is intentionally omitted from the full-fidelity sheets.'],
      ['Resource code', 'Extracted from any Minha Biblioteca URL exposed as the primary URL, a study material, or inside the activity description. Stored as text so 13-digit codes are never rendered in scientific notation.'],
      ['Type 2 note', 'The compatibility sheet preserves the 21 legacy columns. Full-fidelity data lives in Activities, Subjects, Materials, and Order audit.'],
      ['Verification caveat', 'The observer detail response does not expose an activity-verification flag, so the Type 2 compatible value defaults to Não.'],
      ['Source endpoints', '/sections/{sectionUuid}/userdata (lbl) and /activities/{activityUuid}/section/{sectionUuid}'],
    ].map(([field, value]) => ({ field, value }));
    addSheet(workbook, 'Read me', [
      { header: 'Field', key: 'field', width: 42 },
      { header: 'Value / note', key: 'value', width: 115 },
    ], readMeRows);
    return { workbook, counts: { subjectRows: subjectRows.length, materialRows: materialRows.length } };
  };

  const run = async (overrides = {}) => {
    const config = { ...DEFAULT_CONFIG, ...overrides };
    const status = {
      state: 'running',
      startedAt: new Date().toISOString(),
      progress: null,
      outputFile: null,
      totals: null,
      error: null,
    };
    window[STATUS_KEY] = status;
    try {
      if (!location.hostname.endsWith('adalove.inteli.edu.br')) {
        throw new Error('Open the intended Adalove section before running this exporter.');
      }
      const auth = readAuth();
      if (!auth.token) throw new Error('No Adalove token found. Sign in and try again.');
      if (!auth.sectionUuid) throw new Error('No current Adalove section found. Open a section and try again.');
      const headers = headersFromAuth(auth);
      const userdataUrl = `${API_BASE}/sections/${encodeURIComponent(auth.sectionUuid)}/userdata`;
      log(`Fetching ${config.orderingSnapshots} section snapshots...`);
      const snapshots = await Promise.all(Array.from(
        { length: Math.max(1, config.orderingSnapshots) },
        () => fetchJson(userdataUrl, headers, config.detailRetries),
      ));
      const data = snapshots[0] || {};
      const summaryLists = snapshots.map(snapshot => (
        Array.isArray(snapshot?.lbl)
          ? snapshot.lbl
          : (Array.isArray(snapshot?.activities) ? snapshot.activities : [])
      ));
      if (!summaryLists[0].length) {
        throw new Error('The observer response contained no activities in lbl or activities.');
      }
      snapshots.sortedStable = summaryLists.every(
        list => orderSignature(list) === orderSignature(summaryLists[0]),
      );
      snapshots.rawStable = summaryLists.every(
        list => rawSignature(list) === rawSignature(summaryLists[0]),
      );
      const allowedWeeks = new Set(config.weeks.map(clean));
      let summaries = summaryLists[0]
        .filter(summary => !allowedWeeks.size || allowedWeeks.has(folderCaption(summary)))
        .slice()
        .sort(orderCompare);
      if (Number.isFinite(config.limit) && config.limit > 0) {
        summaries = summaries.slice(0, config.limit);
      }
      log('Fetching observer activity details...', { activities: summaries.length, concurrency: config.concurrency });
      const detailResults = await mapWithConcurrency(
        summaries,
        config.concurrency,
        async summary => {
          try {
            const uuid = activityUuid(summary);
            if (!uuid) throw new Error('Activity summary has no UUID.');
            const url = `${API_BASE}/activities/${encodeURIComponent(uuid)}/section/${encodeURIComponent(auth.sectionUuid)}`;
            return { detail: await fetchJson(url, headers, config.detailRetries), error: '' };
          } catch (error) {
            return { detail: null, error: clean(error?.message || error) };
          }
        },
        (completed, total) => {
          status.progress = { completed, total };
          if (completed === total || completed % 20 === 0) log(`Details ${completed}/${total}`);
        },
      );
      const activities = summaries.map((summary, index) => normalizeActivity(
        summary,
        detailResults[index].detail,
        detailResults[index].error,
        auth.sectionUuid,
        config,
      ));
      inferSelfStudyParents(activities);
      const audit = buildOrderAudit(activities);
      const detailErrors = detailResults.filter(result => result.error).length;
      const { workbook, counts } = await buildWorkbook(data, activities, audit, snapshots, detailErrors);
      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
      const section = data.section || {};
      const filename = safeFilename(
        `adalove_${section.sectionCaption || auth.sectionUuid}_${section.projectCaption || 'observer'}_${timestamp}.xlsx`,
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      setTimeout(() => {
        URL.revokeObjectURL(url);
        link.remove();
      }, 1500);
      status.state = 'done';
      status.finishedAt = new Date().toISOString();
      status.outputFile = filename;
      status.totals = {
        activities: activities.length,
        detailsFetched: activities.length - detailErrors,
        detailErrors,
        subjects: counts.subjectRows,
        materials: counts.materialRows,
        worksheets: workbook.worksheets.length,
        sortedOrderStable: snapshots.sortedStable,
        rawOrderStable: snapshots.rawStable,
        duplicateOrderKeys: audit.filter(row => row.duplicate_order_key === 'yes').length,
        datetimeDisagreements: activities.filter(activity => activity.datetime_disagrees).length,
      };
      window.adaloveObserverExportLastResult = {
        filename,
        totals: status.totals,
        activities,
        audit,
      };
      log('Downloaded', filename, status.totals);
      return window.adaloveObserverExportLastResult;
    } catch (error) {
      status.state = 'error';
      status.finishedAt = new Date().toISOString();
      status.error = clean(error?.stack || error?.message || error);
      console.error('[adalove-observer-export] Export failed:', error);
      throw error;
    }
  };

  window.adaloveObserverExporter = {
    run,
    defaults: DEFAULT_CONFIG,
    extractResourceCode: resourceCode,
    version: '1.2.0',
  };
  if (window[STATUS_KEY]?.state !== 'running') {
    run().catch(() => {});
  } else {
    warn('An observer export is already running.');
  }
}());
