const $ = (selector, root = document) => root.querySelector(selector);

const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

const state = {
  syllabi: [],
  detail: null,
  loading: true,
  error: null,
  selectedVersionId: null,
  filters: { query: '', subject: '', mediaType: '', validation: '', complexity: '', showHidden: false },
  collapsedLessonIds: new Set(),
  expandedLessonIds: new Set(),
  reviewBusyReferenceIds: new Set(),
  editor: { active: false, busy: false, dirty: false, lessons: null, targetLessonId: null, note: '' },
  versionDialog: { mode: 'history', trigger: null, error: null },
  upload: {
    mode: 'new', syllabusId: null, busy: false,
    identityStatus: 'idle', proposedGraphId: '', proposalToken: 0,
  },
  catalog: { institutions: [], graphIds: [], loaded: false, loading: false, error: null },
  reconciliation: null,
  reconciliationCleanup: null,
  manualUpload: { sourceId: null, title: '', kind: null, items: [], busy: false },
  markdownSourceId: null,
  lessonBuild: {
    lessonId: null,
    offer: null,
    build: null,
    subjectGraph: null,
    pollingTimer: null,
    trigger: null,
    busy: false,
  },
  selectedReferences: new Map(),
  pollingTimer: null,
};

const viewHost = $('[data-view]');
const headingHost = $('[data-heading]');
const uploadDialog = $('[data-upload-dialog]');
const uploadForm = $('[data-upload-form]');
const versionDialog = $('[data-version-dialog]');
const versionForm = $('[data-version-form]');
const markdownDialog = $('[data-markdown-dialog]');
const manualDialog = $('[data-manual-dialog]');
const manualForm = $('[data-manual-form]');
const lessonBuildDialog = $('[data-lesson-build-dialog]');

const ICON = {
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>',
  back: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>',
  external: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>',
  document: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h6"/></svg>',
  queue: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3" cy="6" r="1"/><circle cx="3" cy="12" r="1"/><circle cx="3" cy="18" r="1"/></svg>',
  eye: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>',
  upload: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 16V4m0 0L7 9m5-5 5 5M5 15v4h14v-4"/></svg>',
  check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>',
  edit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/></svg>',
};

function announce(message) {
  $('[data-status]').textContent = message || '';
}

function intakeDropNote(summary) {
  const dropped = summary || {};
  if (!dropped.total_count) return '';
  const parts = [
    `${dropped.orientation_count || 0} orientações`,
    `${dropped.orientation_self_study_count || 0} autoestudos ligados a orientações`,
  ];
  if (dropped.no_parent_count) parts.push(`${dropped.no_parent_count} autoestudos sem aula anterior na semana`);
  return ` O intake descartou ${parts.slice(0, -1).join(', ')} e ${parts[parts.length - 1]}.`;
}

const INTAKE_NOTE_KEY = 'syllabus-intake-note:';

function storeIntakeNote(syllabusId, message) {
  try {
    window.sessionStorage.setItem(`${INTAKE_NOTE_KEY}${syllabusId}`, message);
  } catch {
    // Storage may be unavailable; the note was already announced on this page.
  }
}

function announceStoredIntakeNote(syllabusId) {
  let message = null;
  try {
    message = window.sessionStorage.getItem(`${INTAKE_NOTE_KEY}${syllabusId}`);
    window.sessionStorage.removeItem(`${INTAKE_NOTE_KEY}${syllabusId}`);
  } catch {
    return;
  }
  if (message) announce(message);
}

function fmtDate(value, withTime = false) {
  if (!value) return 'Data não informada';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('pt-BR', withTime
    ? { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
}

function fmtUsd(value) {
  return `US$ ${new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(Number(value || 0))}`;
}

function fmtInteger(value) {
  return new Intl.NumberFormat('pt-BR').format(Number(value || 0));
}

function safeUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url : null;
  } catch {
    return null;
  }
}

function safeAssetUrl(value) {
  const path = String(value || '');
  return /^\/api\/source-assets\/[A-Za-z0-9][A-Za-z0-9._:-]*$/.test(path) ? path : null;
}

function mediaLabel(source) {
  const kind = String(source.media_type || source.type || '').toLowerCase();
  if (kind.includes('video')) return 'Vídeo';
  if (kind.includes('book') || kind.includes('livro')) return 'Livro';
  if (kind.includes('pdf')) return 'PDF';
  if (kind.includes('article') || kind.includes('artigo')) return 'Artigo';
  return source.media_type || source.type || 'Material';
}

function mediaKey(source) {
  const kind = String(source.media_type || source.type || '').toLowerCase();
  if (kind.includes('video') || kind.includes('vídeo')) return 'video';
  if (kind.includes('book') || kind.includes('livro')) return 'book';
  if (kind.includes('article') || kind.includes('artigo')) return 'article';
  return kind;
}

function acquisitionCapability(source) {
  if (source.acquisition_capability && typeof source.acquisition_capability === 'object') {
    return source.acquisition_capability;
  }
  // Conservative fallback for a cached/older API response: only the Adapter
  // that exists today may expose an enabled queue action.
  const kind = String(source.media_type || source.type || '').toLowerCase();
  if (kind === 'article' || kind === 'artigo') {
    return { supported: true, adapter: 'firecrawl', label: 'Firecrawl' };
  }
  if (kind === 'video' || kind === 'vídeo') {
    return { supported: true, adapter: 'youtube', label: 'YouTube' };
  }
  if (kind === 'book' || kind === 'livro') {
    return {
      supported: true,
      adapter: 'browserbase-book',
      label: 'Browserbase + reconstrução ordenada',
    };
  }
  return {
    supported: false,
    adapter: null,
    label: 'Adapter indisponível',
    reason: `O adapter de ${mediaLabel(source).toLowerCase()} ainda não está disponível. Esta fonte não pode ser enfileirada por enquanto.`,
  };
}

function isScopeLessBook(source) {
  const kind = String(source.media_type || source.type || '').toLowerCase();
  const resourceCode = String(source.resource_code || '').trim();
  const scope = source.scope && typeof source.scope === 'object' ? source.scope : null;
  const scopeKind = String(scope?.kind || source.scope_kind || '').trim();
  const scopeValue = String(scope?.value || source.scope_value || '').trim();
  return kind === 'book'
    && !source.source_id
    && !source.id
    && Boolean(resourceCode)
    && !(scopeKind && scopeValue);
}

function sourceStatus(source) {
  if (!source.source_id && !source.id) {
    return isScopeLessBook(source)
      ? { key: 'attention', label: 'Informe o escopo' }
      : { key: 'attention', label: 'Fonte incompleta' };
  }
  const videoStage = String(source.video_progress?.stage || '').toLowerCase();
  const videoStages = {
    queued: { key: 'queued', label: 'Na fila' },
    visual_understanding: { key: 'running', label: 'Compreendendo o vídeo' },
    frame_extraction: { key: 'running', label: 'Extraindo quadros' },
    speech_and_frames: { key: 'running', label: 'Lendo fala e extraindo quadros' },
    frame_analysis: { key: 'running', label: 'Analisando quadros' },
    evidence_composition: { key: 'running', label: 'Compondo fonte' },
    canonical_cleanup: { key: 'running', label: 'Selecionando passagens' },
    ready: { key: 'ready', label: 'Fonte pronta' },
    attention: { key: 'failed', label: 'Precisa de atenção' },
  };
  if (videoStages[videoStage]) return videoStages[videoStage];
  const pipeline = String(source.pipeline?.status || '').toLowerCase();
  const pipelineStates = {
    queued: { key: 'queued', label: 'Na fila' },
    extracting: { key: 'running', label: 'Extraindo fonte' },
    images: { key: 'running', label: 'Analisando imagens' },
    cleaning: { key: 'running', label: 'Limpando Markdown' },
    failed: { key: 'failed', label: 'Precisa de atenção' },
    attention: { key: 'failed', label: 'Evidência incompleta' },
    ready: { key: 'ready', label: 'Markdown limpo' },
  };
  if (pipelineStates[pipeline]) return pipelineStates[pipeline];
  const job = source.job || source.acquisition || {};
  const raw = String(job.status || source.acquisition_status || source.source_status || '').toLowerCase();
  if (['queued', 'pending'].includes(raw)) return { key: 'queued', label: 'Na fila' };
  if (['running', 'processing', 'started'].includes(raw)) return { key: 'running', label: 'Extraindo' };
  if (['failed', 'error', 'needs_attention'].includes(raw)) return { key: 'failed', label: 'Precisa de atenção' };
  if (source.has_markdown || source.markdown?.available || ['done', 'succeeded', 'ready', 'ingested'].includes(raw)) {
    return { key: 'ready', label: 'Markdown pronto' };
  }
  if (!acquisitionCapability(source).supported) {
    return { key: 'unavailable', label: 'Adapter indisponível' };
  }
  return { key: 'idle', label: 'Não solicitada' };
}

function scopeLabel(source) {
  const scope = source.scope || (
    source.scope_kind && source.scope_value
      ? { kind: source.scope_kind, value: source.scope_value }
      : null
  );
  if (!scope || typeof scope !== 'object') return null;
  const names = {
    pages: 'Páginas', chapters: 'Capítulos', units: 'Unidades', exercises: 'Exercícios',
  };
  return `${names[scope.kind] || scope.kind} ${scope.value}`;
}

function parentInferenceLabel(source) {
  const inference = String(source.parent_inference || '').trim();
  if (!inference) return null;
  const labels = {
    inferred_from_activity_order: 'Pai inferido pela ordem da atividade',
    inferred_from_display_order: 'Pai inferido pela ordem exibida',
    curated_explicit_parent: 'Pai definido na curadoria',
  };
  return labels[inference] || `Vínculo do pai: ${inference}`;
}

function versionsOf(detail) {
  return [...(detail?.versions || [])].sort((a, b) => Number(b.seq || 0) - Number(a.seq || 0));
}

function currentVersion(detail) {
  return detail?.version || versionsOf(detail).find((version) => version.id === state.selectedVersionId)
    || versionsOf(detail)[0] || null;
}

function sourceCount(detail) {
  return (detail?.lessons || []).reduce((count, lesson) => count + (lesson.sources || []).length, 0);
}

function displayDetail() {
  if (!state.detail || !state.editor.active) return state.detail;
  return { ...state.detail, lessons: state.editor.lessons || [] };
}

function latestVersion(detail = state.detail) {
  return versionsOf(detail)[0] || null;
}

function isLatestVersion(detail = state.detail) {
  return currentVersion(detail)?.id === latestVersion(detail)?.id;
}

function renderError(message, action = 'Tentar novamente') {
  return `<div class="syl-empty syl-empty--error" role="alert">
    <strong>Não foi possível carregar esta página.</strong>
    <span>${esc(message)}</span>
    <button class="button" type="button" data-retry>${esc(action)}</button>
  </div>`;
}

function listHeading() {
  headingHost.innerHTML = `<div>
      <p class="syl-eyebrow">Biblioteca curricular</p>
      <h1>Syllabi</h1>
      <p class="admin-page__intro">Planilhas organizadas em aulas e fontes, com cada versão preservada.</p>
    </div>
    <button class="button button--primary syl-button-with-icon" type="button" data-new-syllabus>${ICON.plus}Adicionar syllabus</button>`;
}

function syllabusCard(syllabus) {
  const latest = syllabus.latest || versionsOf(syllabus)[0] || {};
  const lessonCount = latest.lesson_count ?? syllabus.lesson_count ?? 0;
  const sources = latest.source_count ?? syllabus.source_count ?? 0;
  return `<a class="syl-syllabus-card" href="/syllabi?id=${encodeURIComponent(syllabus.id)}">
    <div class="syl-syllabus-card__body">
      <span class="syl-syllabus-card__icon">${ICON.document}</span>
      <div>
        <h2>${esc(syllabus.title || syllabus.name)}</h2>
        <p>Versão ${esc(latest.seq ?? '—')} · ${esc(fmtDate(latest.created_at))}</p>
      </div>
    </div>
    <div class="syl-syllabus-card__facts">
      <span><strong>${esc(lessonCount)}</strong> aulas</span>
      <span><strong>${esc(sources)}</strong> fontes</span>
      <span class="syl-syllabus-card__arrow">${ICON.arrow}</span>
    </div>
  </a>`;
}

function renderList() {
  document.title = 'Syllabi · CG Pipeline';
  renderShellUsage();
  listHeading();
  viewHost.setAttribute('aria-busy', String(state.loading));
  if (state.loading) {
    viewHost.innerHTML = '<div class="syl-loading"><span></span>Carregando syllabi…</div>';
    return;
  }
  if (state.error) {
    viewHost.innerHTML = renderError(state.error);
    return;
  }
  if (!state.syllabi.length) {
    viewHost.innerHTML = `<div class="syl-empty">
      <span class="syl-empty__icon">${ICON.document}</span>
      <strong>Nenhum syllabus adicionado</strong>
      <span>Dê um nome ao primeiro syllabus e envie sua planilha XLSX.</span>
      <button class="button button--primary" type="button" data-new-syllabus>Adicionar syllabus</button>
    </div>`;
    return;
  }
  viewHost.innerHTML = `<div class="syl-list-heading">
      <span>${state.syllabi.length} ${state.syllabi.length === 1 ? 'syllabus' : 'syllabi'}</span>
    </div>
    <section class="syl-syllabus-list" aria-label="Syllabi cadastrados">
      ${state.syllabi.map(syllabusCard).join('')}
    </section>`;
}

async function loadList() {
  state.loading = true;
  state.error = null;
  renderList();
  try {
    const response = await fetch('/api/syllabi', { headers: { Accept: 'application/json' } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    state.syllabi = body.syllabi || [];
  } catch (error) {
    state.error = error.message;
  } finally {
    state.loading = false;
    renderList();
  }
}

function detailHeading() {
  const detail = displayDetail();
  const version = currentVersion(detail);
  const editing = state.editor.active;
  headingHost.innerHTML = `<div>
      <a class="syl-back" href="/syllabi">${ICON.back}Syllabi</a>
      <p class="syl-eyebrow">Syllabus</p>
      <h1>${esc(detail.title || detail.name)}</h1>
      <p class="admin-page__intro">${sourceCount(detail)} fontes em ${(detail.lessons || []).length} aulas</p>
    </div>
    <div class="syl-heading-controls">
      <div class="workspace__actions">
      ${version?.id ? `<a class="button" href="/api/syllabi/${encodeURIComponent(detail.id)}/versions/${encodeURIComponent(version.id)}/workbook">Baixar XLSX</a>` : ''}
      ${editing
        ? `<button class="button button--quiet" type="button" data-cancel-edit${state.editor.busy ? ' disabled' : ''}>Cancelar</button>
          <button class="button button--primary syl-mobile-save" type="button" data-save-syllabus${state.editor.busy ? ' disabled' : ''}>${state.editor.busy ? 'Salvando…' : 'Salvar nova versão'}</button>`
        : `<button class="button" type="button" data-edit-syllabus${isLatestVersion(detail) ? '' : ' disabled title="Abra a versão mais recente para editar"'}>Editar syllabus</button>
          <button class="button" type="button" data-new-version>Enviar nova versão</button>`}
      </div>
      <div class="syl-version-row">
        <button class="button syl-version-button" type="button" data-open-versions aria-haspopup="dialog"${editing ? ' disabled title="Finalize a edição para trocar de versão"' : ''}>
          <span>Versão ${esc(version?.seq ?? '—')}</span>
          <small>${esc(fmtDate(version?.created_at))}</small>
          ${ICON.arrow}
        </button>
      </div>
    </div>`;
}

function lessonSubjectFilter(lesson) {
  const subject = String(lesson?.subject || '').trim();
  if (subject) return { value: subject, label: subject };
  const kind = String(lesson?.kind || '').trim().toLocaleLowerCase('pt-BR');
  return {
    orientation: { value: 'orientation', label: 'Orientação' },
    'orientação': { value: 'orientation', label: 'Orientação' },
    deliverable: { value: 'deliverable', label: 'Artefatos' },
    artifact: { value: 'deliverable', label: 'Artefatos' },
    artefato: { value: 'deliverable', label: 'Artefatos' },
    evaluation: { value: 'evaluation', label: 'Avaliações' },
    'avaliação': { value: 'evaluation', label: 'Avaliações' },
  }[kind] || null;
}

function lessonSubjects(value) {
  const values = Array.isArray(value) ? value : String(value || '').split(/\r?\n/);
  return [...new Set(values.map((subject) => String(subject || '').trim()).filter(Boolean))];
}

function filterMarkup(detail) {
  const subjects = [...new Map((detail.lessons || [])
    .map(lessonSubjectFilter)
    .filter(Boolean)
    .map((subject) => [subject.value, subject])).values()]
    .sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'));
  const hiddenCount = (detail.lessons || []).reduce(
    (count, lesson) => count + Number(Boolean(lesson.hidden))
      + (lesson.sources || []).filter((source) => source.hidden).length, 0,
  );
  return `<section class="syl-toolbar" aria-label="Filtros do syllabus">
    <label class="syl-search">${ICON.search}<span class="sr-only">Buscar</span>
      <input type="search" placeholder="Buscar aula ou fonte" value="${esc(state.filters.query)}" data-filter-query>
    </label>
    ${subjects.length > 1 ? `<label class="syl-filter"><span class="sr-only">Matéria</span>
      <select data-filter-subject>
        <option value="">Todas as matérias</option>
        ${subjects.map((subject) => `<option value="${esc(subject.value)}"${subject.value === state.filters.subject ? ' selected' : ''}>${esc(subject.label)}</option>`).join('')}
      </select>
    </label>` : ''}
    <label class="syl-filter syl-filter--compact"><span class="sr-only">Tipo de fonte</span>
      <select data-filter-media>
        <option value="">Todos os tipos</option>
        <option value="article"${state.filters.mediaType === 'article' ? ' selected' : ''}>Artigos</option>
        <option value="video"${state.filters.mediaType === 'video' ? ' selected' : ''}>Vídeos</option>
        <option value="book"${state.filters.mediaType === 'book' ? ' selected' : ''}>Livros</option>
      </select>
    </label>
    <label class="syl-filter syl-filter--compact"><span class="sr-only">Validação</span>
      <select data-filter-validation>
        <option value="">Todas</option>
        <option value="pending"${state.filters.validation === 'pending' ? ' selected' : ''}>Pendentes</option>
        <option value="validated"${state.filters.validation === 'validated' ? ' selected' : ''}>Validadas</option>
      </select>
    </label>
    <label class="syl-filter syl-filter--compact"><span class="sr-only">Complexidade</span>
      <select data-filter-complexity>
        <option value="">Qualquer complexidade</option>
        <option value="simple"${state.filters.complexity === 'simple' ? ' selected' : ''}>Simples</option>
        <option value="complex"${state.filters.complexity === 'complex' ? ' selected' : ''}>Complexas</option>
        <option value="untagged"${state.filters.complexity === 'untagged' ? ' selected' : ''}>Sem tag</option>
      </select>
    </label>
    <label class="syl-hidden-toggle">
      <input type="checkbox" data-show-hidden${state.filters.showHidden ? ' checked' : ''}>
      <span>Mostrar ocultas${hiddenCount ? ` (${hiddenCount})` : ''}</span>
    </label>
    ${state.editor.active ? `<span class="syl-editing-stamp">${state.editor.targetLessonId ? 'Editando uma aula' : 'Editando syllabus'} · salvar cria uma nova versão</span>` : ''}
    <span class="syl-version-stamp">v${esc(currentVersion(detail)?.seq ?? '—')} · registrada em ${esc(fmtDate(currentVersion(detail)?.created_at, true))}</span>
  </section>`;
}

function usageMarkup(detail) {
  const usage = detail.usage || {};
  const openrouter = usage.openrouter || {};
  const firecrawl = usage.firecrawl || {};
  const firecrawlOutcome = [
    Number(firecrawl.succeeded || 0) ? `${fmtInteger(firecrawl.succeeded)} ${Number(firecrawl.succeeded) === 1 ? 'concluída' : 'concluídas'}` : null,
    Number(firecrawl.failed || 0) ? `${fmtInteger(firecrawl.failed)} ${Number(firecrawl.failed) === 1 ? 'falhou' : 'falharam'}` : null,
  ].filter(Boolean).join(' · ');
  const firecrawlExtractions = Number(firecrawl.extractions || 0);
  const firecrawlAttempts = Number(firecrawl.attempts || 0);
  return `<section class="syl-shell-usage" aria-label="Consumo das fontes desta versão">
    ${state.editor.active ? `<button class="button button--primary syl-shell-save" type="button" data-save-syllabus${state.editor.busy ? ' disabled' : ''}>${state.editor.busy ? 'Salvando…' : 'Salvar nova versão'}</button>` : ''}
    <div class="syl-usage-item" title="${esc(`${fmtInteger(openrouter.calls)} chamadas · ${fmtInteger(openrouter.total_tokens)} tokens`)}">
      <span>OpenRouter</span>
      <strong>${esc(fmtUsd(openrouter.cost_usd))}</strong>
      <small>${esc(fmtInteger(openrouter.calls))} chamadas · ${esc(fmtInteger(openrouter.total_tokens))} tokens</small>
    </div>
    <div class="syl-usage-item" title="${esc(`${fmtInteger(firecrawlAttempts)} ${firecrawlAttempts === 1 ? 'tentativa' : 'tentativas'}${firecrawlOutcome ? ` · ${firecrawlOutcome}` : ''}`)}">
      <span>Firecrawl</span>
      <strong>${esc(fmtInteger(firecrawlExtractions))} ${firecrawlExtractions === 1 ? 'extração' : 'extrações'}</strong>
      <small>${esc(fmtInteger(firecrawlAttempts))} ${firecrawlAttempts === 1 ? 'tentativa' : 'tentativas'}${firecrawlOutcome ? ` · ${esc(firecrawlOutcome)}` : ''}</small>
    </div>
  </section>`;
}

function renderShellUsage(detail = null) {
  const host = document.querySelector('[data-admin-shell-context]');
  if (host) host.innerHTML = detail ? usageMarkup(detail) : '';
}

function sourceMatches(source, query) {
  if (!query) return true;
  return [source.title, source.description, source.url, source.media_type, source.resource_code, scopeLabel(source)]
    .filter(Boolean).join(' ').toLocaleLowerCase('pt-BR').includes(query);
}

function filteredLessons(detail) {
  const query = state.filters.query.trim().toLocaleLowerCase('pt-BR');
  return (detail.lessons || []).flatMap((lesson, lessonIndex) => {
    if (lesson.hidden && !state.filters.showHidden) return [];
    if (state.filters.subject && lessonSubjectFilter(lesson)?.value !== state.filters.subject) return [];
    const lessonMatches = [lesson.title, lesson.subject, lesson.description]
      .filter(Boolean).join(' ').toLocaleLowerCase('pt-BR').includes(query);
    const allSources = lesson.sources || [];
    const visible = allSources
      .map((source, sourceIndex) => ({ ...source, __sourceIndex: sourceIndex }))
      .filter((source) => state.filters.showHidden || !source.hidden);
    const sources = (lessonMatches ? visible : visible.filter((source) => sourceMatches(source, query)))
      .filter((source) => {
        const review = source.review || {};
        if (state.filters.mediaType && mediaKey(source) !== state.filters.mediaType) return false;
        if (state.filters.validation === 'validated' && !review.validated) return false;
        if (state.filters.validation === 'pending' && review.validated) return false;
        if (state.filters.complexity === 'untagged' && review.complexity) return false;
        if (['simple', 'complex'].includes(state.filters.complexity)
          && review.complexity !== state.filters.complexity) return false;
        return true;
      });
    const sourceFilterActive = Boolean(
      state.filters.mediaType || state.filters.validation || state.filters.complexity
    );
    if (sourceFilterActive && !sources.length) return [];
    if (!query || lessonMatches || sources.length) {
      return [{ ...lesson, __lessonIndex: lessonIndex, __allSources: allSources, sources }];
    }
    return [];
  });
}

function sourceStatusMarkup(source) {
  const status = sourceStatus(source);
  const images = source.image_branch || {};
  const isVideo = String(source.media_type || source.type || '').toLowerCase().includes('video');
  const visualNoun = isVideo ? 'quadro' : 'imagem';
  const visualNounPlural = isVideo ? 'quadros' : 'imagens';
  const analyzedAdjective = isVideo ? 'analisados' : 'analisadas';
  let imageLabel = null;
  let imageState = String(images.state || 'none');
  if (images.active) {
    const completed = Number(images.useful || 0) + Number(images.not_important || 0)
      + Number(images.filtered || 0) + Number(images.failed || 0);
    imageLabel = `${completed}/${Number(images.total || 0)} ${visualNounPlural} ${analyzedAdjective}`;
    imageState = 'processing';
  } else if (Number(images.failed || 0)) {
    imageLabel = `${Number(images.useful || 0)} úteis · ${Number(images.failed)} com atenção`;
    imageState = 'attention';
  } else if (Number(images.total || 0)) {
    imageLabel = `${Number(images.useful || 0)} ${Number(images.useful || 0) === 1 ? `${visualNoun} útil` : `${visualNounPlural} úteis`}`;
    imageState = 'ready';
  }
  return `${source.hidden ? '<span class="syl-hidden-state">Ocultada</span>' : ''}
    <span class="syl-source-state syl-source-state--${status.key}"><i></i>${esc(status.label)}</span>
    ${source.markdown?.is_previous_version ? '<span class="syl-markdown-state">Último Markdown válido preservado</span>' : ''}
    ${imageLabel ? `<span class="syl-image-state syl-image-state--${esc(imageState)}">${esc(imageLabel)}</span>` : ''}`;
}

function hasSourcePublication(source) {
  const status = sourceStatus(source);
  return Boolean(
    source.source_publication
    || source.publication
    || source.publication_id
    || source.has_markdown
    || source.markdown?.available
    || status.key === 'ready'
  );
}

function hasCurrentSourcePublication(source) {
  return hasSourcePublication(source) && !source.markdown?.is_previous_version;
}

function sourceActions(source) {
  const status = sourceStatus(source);
  const busy = ['queued', 'running'].includes(status.key);
  const markdownReady = hasSourcePublication(source);
  const sourceId = source.source_id || source.id;
  const capability = acquisitionCapability(source);
  const unavailableLabel = `Adapter de ${mediaLabel(source).toLowerCase()} indisponível`;
  const isVideo = String(source.media_type || source.type || '').toLowerCase().includes('video');
  const preflight = source.video_preflight || null;
  const needsPreflight = isVideo && (!preflight || preflight.status === 'failed');
  const needsAuthorization = isVideo && preflight?.route === 'approval_required';
  const canSetBookScope = isLatestVersion()
    && isScopeLessBook(source)
    && Boolean(source.reference_id);
  return `<div class="syl-source__actions">
    ${markdownReady ? `<button class="button syl-action-button" type="button" data-markdown-source="${esc(sourceId)}" data-markdown-title="${esc(source.title)}">${ICON.eye}Visualizar</button>` : ''}
    ${source.source_id ? `<button class="button syl-action-button syl-manual-button" type="button" data-manual-source="${esc(source.source_id)}" data-manual-title="${esc(source.title || 'Fonte sem título')}"${busy ? ' disabled' : ''}>${ICON.upload}Upload de PDF ou Imagem</button>` : ''}
    ${canSetBookScope ? `<button class="button syl-action-button" type="button" data-edit-book-scope="${esc(source.reference_id)}" aria-label="Informar escopo de ${esc(source.title || 'livro sem título')}">${ICON.edit}Informar escopo</button>` : ''}
    ${needsPreflight
      ? `<button class="button syl-queue-button" type="button" data-video-preflight="${esc(sourceId || '')}"${busy || !sourceId ? ' disabled' : ''}>${ICON.queue}${preflight ? 'Atualizar dados do vídeo' : 'Verificar vídeo'}</button>`
      : (needsAuthorization
        ? `<button class="button syl-queue-button" type="button" data-authorize-video="${esc(sourceId || '')}"${busy || !sourceId ? ' disabled' : ''}>${ICON.queue}Processar vídeo longo</button>`
        : (capability.supported
      ? `<button class="button syl-queue-button" type="button" data-queue-source="${esc(sourceId || '')}"${busy || !sourceId ? ' disabled' : ''}>
          ${ICON.queue}${!sourceId ? 'Complete a fonte' : (busy ? `${esc(status.label)}…` : (markdownReady ? 'Reprocessar fonte' : (isVideo ? 'Processar vídeo' : 'Extrair Markdown')))}
        </button>`
      : (markdownReady
        ? ''
        : `<button class="button syl-queue-button" type="button" disabled title="${esc(capability.reason || unavailableLabel)}">${ICON.queue}${unavailableLabel}</button>`)))}
  </div>`;
}

function videoReadinessMarkup(source) {
  const kind = String(source.media_type || source.type || '').toLowerCase();
  if (!kind.includes('video')) return '';
  const preflight = source.video_preflight;
  if (!preflight) return '<div class="syl-video-readiness">Metadados do vídeo ainda não verificados.</div>';
  if (preflight.status === 'failed') {
    return '<div class="syl-video-readiness syl-video-readiness--attention">Metadados indisponíveis · Tente verificar novamente</div>';
  }
  const seconds = Number(preflight.duration_seconds);
  const duration = Number.isFinite(seconds) ? `${Math.max(1, Math.round(seconds / 60))} min` : null;
  if (preflight.route === 'uploaded_caption') {
    return `<div class="syl-video-readiness">Vídeo verificado${duration ? ` · ${duration}` : ''} · Legendas do autor · Quadros serão analisados</div>`;
  }
  if (preflight.route === 'visual_only') {
    return `<div class="syl-video-readiness">Vídeo verificado${duration ? ` · ${duration}` : ''} · Conteúdo visual será compreendido</div>`;
  }
  if (preflight.route === 'automatic_stt') {
    return `<div class="syl-video-readiness">Vídeo verificado${duration ? ` · ${duration}` : ''} · Fala será transcrita · Quadros serão analisados</div>`;
  }
  if (!duration) {
    return '<div class="syl-video-readiness syl-video-readiness--attention">Duração desconhecida · Confirme antes de processar o vídeo</div>';
  }
  return `<div class="syl-video-readiness syl-video-readiness--attention">Vídeo longo · ${duration} · Confirmação necessária para analisar os quadros</div>`;
}

function sourceEditorMarkup(source, lessonIndex, sourceIndex) {
  const kind = String(source.media_type || 'article').toLowerCase();
  return `<article class="syl-source syl-source--editor${source.hidden ? ' is-hidden-source' : ''}" data-editor-source="${lessonIndex}:${sourceIndex}">
    <div class="syl-editor-source__heading">
      <span class="syl-media syl-media--${esc(kind)}">${esc(mediaLabel(source))}</span>
      ${source.hidden ? '<span class="syl-hidden-state">Ocultada</span>' : ''}
      ${source.__new ? '<span class="syl-new-state">Nova fonte</span>' : ''}
      <div class="syl-editor-controls">
        <button class="button button--quiet" type="button" data-move-source-up="${lessonIndex}:${sourceIndex}"${sourceIndex === 0 ? ' disabled' : ''} aria-label="Mover fonte para cima">↑</button>
        <button class="button button--quiet" type="button" data-move-source-down="${lessonIndex}:${sourceIndex}"${sourceIndex >= (state.editor.lessons?.[lessonIndex]?.sources?.length || 0) - 1 ? ' disabled' : ''} aria-label="Mover fonte para baixo">↓</button>
        <button class="button button--quiet" type="button" data-toggle-source-hidden="${lessonIndex}:${sourceIndex}">${source.hidden ? 'Desocultar' : 'Ocultar'}</button>
        <button class="button button--danger-quiet" type="button" data-remove-source="${lessonIndex}:${sourceIndex}">Remover</button>
      </div>
    </div>
    <div class="syl-editor-grid">
      <label class="syl-form-field syl-editor-field--wide"><span>Nome da fonte</span>
        <input class="field" type="text" value="${esc(source.title || '')}" data-source-field="title" data-lesson-index="${lessonIndex}" data-source-index="${sourceIndex}" required>
      </label>
      <label class="syl-form-field"><span>Tipo</span>
        <select class="field" data-source-field="media_type" data-lesson-index="${lessonIndex}" data-source-index="${sourceIndex}">
          ${[['article', 'Artigo'], ['video', 'Vídeo'], ['book', 'Livro']].map(([value, label]) => `<option value="${value}"${kind === value ? ' selected' : ''}>${label}</option>`).join('')}
        </select>
      </label>
      <label class="syl-form-field syl-editor-field--full"><span>Descrição</span>
        <textarea class="field" rows="3" maxlength="4000" data-source-field="description" data-lesson-index="${lessonIndex}" data-source-index="${sourceIndex}">${esc(source.description || '')}</textarea>
      </label>
      <label class="syl-form-field syl-editor-field--full"><span>Link</span>
        <input class="field" type="url" value="${esc(source.url || '')}" placeholder="https://…" data-source-field="url" data-lesson-index="${lessonIndex}" data-source-index="${sourceIndex}">
      </label>
      ${kind === 'book' ? `<label class="syl-form-field"><span>Código do recurso / ISBN</span>
          <input class="field" type="text" value="${esc(source.resource_code || '')}" data-source-field="resource_code" data-lesson-index="${lessonIndex}" data-source-index="${sourceIndex}">
        </label>
        <label class="syl-form-field"><span>Tipo de escopo</span>
          <select class="field" data-source-field="scope_kind" data-lesson-index="${lessonIndex}" data-source-index="${sourceIndex}">
            <option value="">Sem escopo</option>
            ${[['pages', 'Páginas'], ['chapters', 'Capítulos'], ['units', 'Unidades'], ['exercises', 'Exercícios']].map(([value, label]) => `<option value="${value}"${source.scope_kind === value ? ' selected' : ''}>${label}</option>`).join('')}
          </select>
        </label>
        <label class="syl-form-field syl-editor-field--full"><span>Escopo concreto</span>
          <input class="field" type="text" value="${esc(source.scope_value || '')}" placeholder="Ex.: 27-55" data-source-field="scope_value" data-lesson-index="${lessonIndex}" data-source-index="${sourceIndex}">
        </label>` : ''}
    </div>
  </article>`;
}

function lessonSelectionKey(lessonId) {
  const versionId = currentVersion(state.detail)?.id || state.selectedVersionId || '';
  return `${versionId}:${lessonId || ''}`;
}

function eligibleLessonReferenceIds(lessonId) {
  const lesson = lessonById(lessonId);
  return (lesson?.sources || [])
    .filter((source) => (
      !source.hidden
      && source.reference_id
      && source.review?.validated
      && hasCurrentSourcePublication(source)
    ))
    .map((source) => String(source.reference_id));
}

function selectedReferencesForLesson(lessonId) {
  const key = lessonSelectionKey(lessonId);
  if (!state.selectedReferences.has(key)) {
    state.selectedReferences.set(key, new Set(eligibleLessonReferenceIds(lessonId)));
  }
  return state.selectedReferences.get(key);
}

function sourceBuildSelectionMarkup(source, lessonId) {
  const referenceId = String(source.reference_id || '');
  if (!referenceId) return '';
  const eligible = !source.hidden && Boolean(source.review?.validated) && hasCurrentSourcePublication(source);
  const selected = selectedReferencesForLesson(lessonId).has(referenceId);
  const reason = !source.review?.validated
    ? 'Valide o autoestudo antes de incluí-lo'
    : (!hasCurrentSourcePublication(source) ? 'Extraia o Markdown atual antes de incluí-lo' : '');
  return `<label class="syl-build-source-choice${eligible ? '' : ' is-disabled'}"${reason ? ` title="${esc(reason)}"` : ''}>
    <input type="checkbox" data-build-source data-lesson-id="${esc(lessonId || '')}" data-reference-id="${esc(referenceId)}"${selected ? ' checked' : ''}${eligible ? '' : ' disabled'}>
    <span>Usar no Lesson Build</span>
  </label>`;
}

function sourceReviewMarkup(source, lessonId) {
  const review = source.review || {};
  const complexity = review.complexity || null;
  const validated = Boolean(review.validated);
  const referenceId = source.reference_id || '';
  const busy = state.reviewBusyReferenceIds.has(referenceId);
  return `<div class="syl-source__review-actions" aria-label="Organização do autoestudo">
    <button class="syl-source-tag syl-source-tag--simple${complexity === 'simple' ? ' is-active' : ''}" type="button" data-set-source-complexity="simple" data-reference-id="${esc(referenceId)}" aria-pressed="${complexity === 'simple'}"${busy ? ' disabled' : ''}>Simples</button>
    <button class="syl-source-tag syl-source-tag--complex${complexity === 'complex' ? ' is-active' : ''}" type="button" data-set-source-complexity="complex" data-reference-id="${esc(referenceId)}" aria-pressed="${complexity === 'complex'}"${busy ? ' disabled' : ''}>Complexa</button>
    <button class="syl-source-validated${validated ? ' is-active' : ''}" type="button" data-toggle-source-validated data-reference-id="${esc(referenceId)}" aria-pressed="${validated}"${busy ? ' disabled' : ''}>${validated ? '✓ ' : ''}Validada</button>
    ${sourceBuildSelectionMarkup(source, lessonId)}
  </div>`;
}

function sourceMarkup(source, lessonId) {
  const original = safeUrl(source.url);
  const status = sourceStatus(source);
  const sourceId = source.source_id || source.id || '';
  if (source.review?.validated) {
    const markdownReady = hasSourcePublication(source);
    const referenceId = source.reference_id || '';
    const busy = state.reviewBusyReferenceIds.has(referenceId);
    return `<article class="syl-source syl-source--validated${source.hidden ? ' is-hidden-source' : ''}" data-source-id="${esc(sourceId)}" data-reference-id="${esc(referenceId)}" data-source-status="${status.key}">
      <h3>${esc(source.title || 'Fonte sem título')}</h3>
      <div class="syl-source__actions">
        ${markdownReady ? `<button class="button syl-action-button" type="button" data-markdown-source="${esc(sourceId)}" data-markdown-title="${esc(source.title)}">${ICON.eye}Visualizar</button>` : ''}
        ${sourceBuildSelectionMarkup(source, lessonId)}
        <button class="button syl-action-button" type="button" data-toggle-source-validated data-reference-id="${esc(referenceId)}" aria-pressed="true"${busy ? ' disabled' : ''}>${ICON.check}Desvalidar</button>
      </div>
    </article>`;
  }
  const missingInput = !source.source_id && !source.id
    ? (isScopeLessBook(source)
      ? 'Este livro ainda não tem um escopo concreto. Informe páginas ou capítulos antes de extrair.'
      : 'Esta referência ainda não possui identidade suficiente para ser extraída.')
    : null;
  const failure = source.job?.error || source.acquisition?.error || source.failure_note || source.error || missingInput;
  const capability = acquisitionCapability(source);
  const markdownReady = source.has_markdown || source.markdown?.available || status.key === 'ready';
  // Once a manual PDF/image path produced Markdown, the missing native adapter
  // is no longer an actionable problem for this source. Keep the fallback
  // upload action visible, but do not contradict the successful outcome.
  const adapterNotice = !markdownReady && !capability.supported ? capability.reason : null;
  const meta = [scopeLabel(source), parentInferenceLabel(source)].filter(Boolean);
  const bookCode = source.resource_code ? String(source.resource_code) : '';
  return `<article class="syl-source${source.hidden ? ' is-hidden-source' : ''}" data-source-id="${esc(sourceId)}" data-reference-id="${esc(source.reference_id || '')}" data-source-status="${status.key}">
    <div class="syl-source__main">
      <div class="syl-source__topline">
        <span class="syl-media syl-media--${esc(String(source.media_type || 'material').toLowerCase())}">${esc(mediaLabel(source))}</span>
        <span class="syl-source__states">${sourceStatusMarkup(source)}</span>
        ${source.reference_id ? sourceReviewMarkup(source, lessonId) : ''}
      </div>
      <h3>${esc(source.title || 'Fonte sem título')}</h3>
      ${source.description ? `<p class="syl-source__description">${esc(source.description)}</p>` : ''}
      ${videoReadinessMarkup(source)}
      <div class="syl-source__footer">
        ${original ? `<a class="syl-original-link" href="${esc(original.href)}" target="_blank" rel="noopener noreferrer" title="${esc(original.href)}">${esc(original.href)}${ICON.external}</a>` : '<span class="syl-no-link">Sem link público</span>'}
        ${bookCode ? `<button class="syl-source__meta syl-copy-code" type="button" data-copy-book-code="${esc(bookCode)}" aria-label="Copiar código do livro ${esc(bookCode)}" title="Copiar código do livro"><span>Código</span><code>${esc(bookCode)}</code><span class="syl-copy-code__action" aria-hidden="true">Copiar</span></button>` : ''}
        ${meta.map((entry) => `<span class="syl-source__meta">${esc(entry)}</span>`).join('')}
      </div>
      ${failure ? `<div class="syl-source__failure"><strong>A extração precisa de atenção.</strong><span>${esc(failure)}</span></div>` : ''}
      ${adapterNotice ? `<div class="syl-source__adapter-notice"><strong>Extração indisponível nesta versão.</strong><span>${esc(adapterNotice)}</span></div>` : ''}
    </div>
    ${sourceActions(source)}
  </article>`;
}

function lessonValidationProgress(lesson) {
  const allSources = lesson.__allSources || lesson.sources || [];
  const activeSources = allSources.filter((source) => !source.hidden);
  return {
    total: activeSources.length,
    validated: activeSources.filter((source) => Boolean(source.review?.validated)).length,
  };
}

function lessonIsValidated(lesson) {
  const progress = lessonValidationProgress(lesson);
  return progress.total > 0 && progress.validated === progress.total;
}

function lessonIsCollapsed(lesson) {
  const lessonId = lesson.id || '';
  return state.collapsedLessonIds.has(lessonId)
    || !state.expandedLessonIds.has(lessonId);
}

function lessonHasActiveWork(lesson) {
  const buildStatus = String(lesson.lesson_build?.latest_build?.status || '').toLowerCase();
  if (['queued', 'running'].includes(buildStatus)) return true;
  return (lesson.__allSources || lesson.sources || []).some((source) => {
    const status = sourceStatus(source).key;
    return status === 'queued' || status === 'running' || Boolean(source.image_branch?.active);
  });
}

function lessonBuildMarkup(lesson) {
  const eligible = eligibleLessonReferenceIds(lesson.id);
  const selected = selectedReferencesForLesson(lesson.id);
  const selectedCount = eligible.filter((referenceId) => selected.has(referenceId)).length;
  const build = lesson.lesson_build?.latest_build || null;
  const status = String(build?.status || '').toLowerCase();
  const statusCopy = build
    ? ({ queued: 'na fila', running: 'em execução', succeeded: 'concluído', failed: 'precisa de atenção' }[status] || status)
    : 'ainda não iniciado';
  return `<footer class="syl-lesson-build-footer">
    <div class="syl-lesson-build-copy">
      <strong>Lesson Build</strong>
      <span>${selectedCount}/${eligible.length} Source Publication${eligible.length === 1 ? '' : 's'} selecionada${selectedCount === 1 ? '' : 's'} · ${esc(statusCopy)}</span>
    </div>
    <button class="button syl-lesson-build" type="button" data-open-lesson-build="${esc(lesson.id || '')}">${['queued', 'running'].includes(status) ? 'Acompanhar' : 'Abrir Lesson Build'}</button>
  </footer>`;
}

function lessonMarkup(lesson, index) {
  const sources = lesson.sources || [];
  const subjects = lessonSubjects(lesson.subjects);
  const when = lesson.date ? fmtDate(lesson.date) : (lesson.week ? `Semana ${lesson.week}` : 'Data não informada');
  const lessonIndex = Number.isInteger(lesson.__lessonIndex) ? lesson.__lessonIndex : index;
  const editingThisLesson = state.editor.active
    && (!state.editor.targetLessonId || state.editor.targetLessonId === lesson.id);
  if (editingThisLesson) {
    const originalSourceCount = state.editor.lessons?.[lessonIndex]?.sources?.length || 0;
    const editorSubject = lessonSubjectFilter(lesson)?.label || '';
    return `<section class="syl-lesson syl-lesson--editor${lesson.hidden ? ' is-hidden-lesson' : ''}" data-subject="${esc(editorSubject.toUpperCase())}">
      <header class="syl-lesson__header syl-lesson__header--editor">
        <div class="syl-lesson__index" aria-hidden="true">${String(lessonIndex + 1).padStart(2, '0')}</div>
        <div class="syl-editor-lesson-fields">
          <div class="syl-editor-grid">
            <label class="syl-form-field syl-editor-field--wide"><span>Nome da aula</span>
              <input class="field" type="text" value="${esc(lesson.title || '')}" data-lesson-field="title" data-lesson-index="${lessonIndex}" required>
            </label>
            <label class="syl-form-field"><span>Matéria</span>
              <input class="field" type="text" value="${esc(lesson.subject || '')}" data-lesson-field="subject" data-lesson-index="${lessonIndex}">
            </label>
            <label class="syl-form-field"><span>Data</span>
              <input class="field" type="date" value="${esc(lesson.date || '')}" data-lesson-field="date" data-lesson-index="${lessonIndex}">
            </label>
            <label class="syl-form-field"><span>Semana</span>
              <input class="field" type="number" min="1" max="1000" value="${esc(lesson.week || '')}" data-lesson-field="week" data-lesson-index="${lessonIndex}">
            </label>
            <label class="syl-form-field syl-editor-field--full"><span>Descrição da aula</span>
              <textarea class="field" rows="3" maxlength="4000" data-lesson-field="description" data-lesson-index="${lessonIndex}">${esc(lesson.description || '')}</textarea>
            </label>
            <label class="syl-form-field syl-editor-field--full"><span>Assuntos, um por linha</span>
              <textarea class="field" rows="3" maxlength="20000" data-lesson-field="subjects" data-lesson-index="${lessonIndex}">${esc(subjects.join('\n'))}</textarea>
            </label>
          </div>
        </div>
        <div class="syl-editor-lesson-actions">
          <span>${originalSourceCount} ${originalSourceCount === 1 ? 'fonte' : 'fontes'}</span>
          ${lesson.hidden ? '<span class="syl-hidden-state">Aula ocultada</span>' : ''}
          <button class="button button--quiet" type="button" data-toggle-lesson-hidden="${lessonIndex}">${lesson.hidden ? 'Desocultar aula' : 'Ocultar aula'}</button>
          <button class="button button--quiet" type="button" data-move-lesson-up="${lessonIndex}"${lessonIndex === 0 ? ' disabled' : ''}>↑ Aula</button>
          <button class="button button--quiet" type="button" data-move-lesson-down="${lessonIndex}"${lessonIndex >= (state.editor.lessons?.length || 0) - 1 ? ' disabled' : ''}>↓ Aula</button>
        </div>
      </header>
      <div class="syl-lesson__sources">
        ${sources.map((source) => sourceEditorMarkup(source, lessonIndex, source.__sourceIndex)).join('')}
        <div class="syl-add-source"><button class="button" type="button" data-add-source="${lessonIndex}">${ICON.plus}Adicionar fonte a esta aula</button></div>
      </div>
    </section>`;
  }
  const validated = lessonIsValidated(lesson);
  const progress = lessonValidationProgress(lesson);
  const collapsed = lessonIsCollapsed(lesson);
  const activeWork = lessonHasActiveWork(lesson);
  const subject = lessonSubjectFilter(lesson)?.label || '';
  return `<section class="syl-lesson${lesson.hidden ? ' is-hidden-lesson' : ''}${validated ? ' is-validated' : ''}${collapsed ? ' is-collapsed' : ''}" data-lesson-id="${esc(lesson.id || '')}" data-subject="${esc(subject.toUpperCase())}">
    <header class="syl-lesson__header${collapsed ? ' syl-lesson__header--collapsed' : ''}">
      <button class="syl-lesson__header-toggle" type="button" data-toggle-lesson-expanded data-lesson-id="${esc(lesson.id || '')}" aria-expanded="${!collapsed}" aria-label="${collapsed ? 'Expandir' : 'Recolher'} aula ${esc(lesson.title || 'sem título')}"></button>
      <div class="syl-lesson__index" aria-hidden="true">${String(index + 1).padStart(2, '0')}</div>
      <div class="syl-lesson__identity">
        <div class="syl-lesson__meta">${collapsed
          ? `<time${lesson.date ? ` datetime="${esc(lesson.date)}"` : ''}>${esc(when)}</time>
            ${subject ? `<span>${esc(subject)}</span>` : ''}`
          : `<time${lesson.date ? ` datetime="${esc(lesson.date)}"` : ''}>${esc(when)}</time>
            ${subject ? `<span>${esc(subject)}</span>` : ''}
            ${lesson.hidden ? '<span class="syl-hidden-state">Ocultada</span>' : ''}`}
        </div>
        <h2>${esc(lesson.title || 'Aula sem título')}</h2>
        ${!collapsed && lesson.description ? `<p>${esc(lesson.description)}</p>` : ''}
        ${!collapsed && subjects.length ? `<ul class="syl-lesson__subjects" aria-label="Assuntos">${subjects.map((item) => `<li>${esc(item)}</li>`).join('')}</ul>` : ''}
      </div>
      <div class="syl-lesson__side">
        <div class="syl-lesson__source-tools">
          ${activeWork ? '<span class="syl-lesson__spinner" role="status" aria-label="Processando aula" title="Processando"></span>' : ''}
          <span class="syl-lesson__source-count">${sources.length} ${sources.length === 1 ? 'fonte' : 'fontes'}</span>
          ${isLatestVersion() && (!state.editor.active || state.editor.targetLessonId) ? `<button class="syl-lesson-edit" type="button" data-edit-lesson="${esc(lesson.id || '')}" aria-label="Editar somente esta aula">${ICON.edit}</button>` : ''}
        </div>
        ${collapsed ? `<span class="syl-lesson__validation-progress">${progress.validated}/${progress.total} autoestudos validados</span>` : ''}
        ${!collapsed && validated ? '<span class="syl-lesson-complete">✓ Autoestudos validados</span>' : ''}
      </div>
    </header>
    <div class="syl-lesson__sources">
      ${sources.length ? sources.map((source) => sourceMarkup(source, lesson.id)).join('') : '<p class="syl-lesson__empty">Nenhuma fonte registrada nesta aula.</p>'}
    </div>
    ${lessonBuildMarkup(lesson)}
  </section>`;
}

function hasActiveJobs(detail) {
  return (detail?.lessons || []).some((lesson) => (
    ['queued', 'running'].includes(String(lesson.lesson_build?.latest_build?.status || '').toLowerCase())
    || (lesson.sources || []).some((source) => {
      const status = sourceStatus(source).key;
      return status === 'queued' || status === 'running' || Boolean(source.image_branch?.active);
    })
  ));
}

function schedulePolling() {
  window.clearTimeout(state.pollingTimer);
  state.pollingTimer = null;
  if (state.editor.active) return;
  if (!hasActiveJobs(state.detail)) return;
  state.pollingTimer = window.setTimeout(() => loadDetail({ silent: true }), 2000);
}

function renderDetail() {
  viewHost.setAttribute('aria-busy', String(state.loading));
  if (state.loading && !state.detail) {
    headingHost.innerHTML = '';
    viewHost.innerHTML = '<div class="syl-loading"><span></span>Carregando syllabus…</div>';
    return;
  }
  if (state.error) {
    headingHost.innerHTML = `<div><a class="syl-back" href="/syllabi">${ICON.back}Syllabi</a><h1>Syllabus</h1></div>`;
    viewHost.innerHTML = renderError(state.error);
    return;
  }
  const detail = displayDetail();
  if (!detail) return;
  document.title = `${detail.title || detail.name} · Syllabi · CG Pipeline`;
  detailHeading();
  renderShellUsage(detail);
  const lessons = filteredLessons(detail);
  viewHost.innerHTML = `${filterMarkup(detail)}
    <div class="syl-lessons">
      ${lessons.length ? lessons.map(lessonMarkup).join('') : `<div class="syl-empty"><strong>Nenhuma aula encontrada</strong><span>Ajuste os filtros para voltar a visualizar o syllabus.</span></div>`}
    </div>`;
  autosizeEditorTextareas();
  schedulePolling();
}

function autosizeEditorTextarea(textarea) {
  if (!(textarea instanceof HTMLTextAreaElement)) return;
  const borderHeight = textarea.offsetHeight - textarea.clientHeight;
  textarea.style.height = 'auto';
  textarea.style.height = `${textarea.scrollHeight + borderHeight}px`;
}

function autosizeEditorTextareas() {
  viewHost.querySelectorAll('.syl-lesson--editor textarea.field')
    .forEach(autosizeEditorTextarea);
}

const initialSearch = new URLSearchParams(window.location.search);
const routeId = initialSearch.get('id');
const initialReconciliationId = initialSearch.get('reconciliation');
const initialVersionId = initialSearch.get('version_id');
if (initialVersionId) state.selectedVersionId = initialVersionId;

async function loadDetail({ versionId = state.selectedVersionId, silent = false } = {}) {
  if (!routeId) return;
  if (!silent) {
    state.loading = true;
    state.error = null;
    renderDetail();
  }
  const query = versionId ? `?version_id=${encodeURIComponent(versionId)}` : '';
  try {
    const response = await fetch(`/api/syllabi/${encodeURIComponent(routeId)}${query}`, { headers: { Accept: 'application/json' } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    state.detail = body;
    state.selectedVersionId = body.version?.id || versionId || body.latest_version_id || null;
    state.error = null;
  } catch (error) {
    if (!silent) state.error = error.message;
    else announce(`Não foi possível atualizar o progresso: ${error.message}`);
  } finally {
    state.loading = false;
    renderDetail();
  }
}

function cloneLessons(lessons) {
  if (typeof structuredClone === 'function') return structuredClone(lessons || []);
  return JSON.parse(JSON.stringify(lessons || []));
}

function startEditing(targetLessonId = null) {
  if (!state.detail || !isLatestVersion() || state.editor.busy) return;
  if (targetLessonId && !(state.detail.lessons || []).some((lesson) => lesson.id === targetLessonId)) return;
  if (state.editor.active) {
    if (!targetLessonId || !state.editor.targetLessonId) return;
    state.editor.targetLessonId = targetLessonId;
    announce('Alterações mantidas. Agora editando somente a aula selecionada.');
    renderDetail();
    return;
  }
  state.editor = {
    active: true,
    busy: false,
    dirty: false,
    lessons: cloneLessons(state.detail.lessons),
    targetLessonId,
    note: '',
  };
  state.filters = { query: '', subject: '', mediaType: '', validation: '', complexity: '', showHidden: false };
  announce(targetLessonId
    ? 'Editando somente esta aula. Salvar criará uma nova versão do syllabus.'
    : 'Modo de edição aberto. Nenhuma mudança foi salva ainda.');
  renderDetail();
}

function cancelEditing() {
  if (!state.editor.active || state.editor.busy) return;
  if (state.editor.dirty && !window.confirm('Descartar as mudanças ainda não salvas?')) return;
  state.editor = { active: false, busy: false, dirty: false, lessons: null, targetLessonId: null, note: '' };
  state.filters = { ...state.filters, showHidden: false };
  announce('Edição cancelada. A versão atual não foi alterada.');
  renderDetail();
}

function markEditorDirty() {
  if (state.editor.active) state.editor.dirty = true;
}

function versionDialogTrigger() {
  return state.versionDialog.mode === 'save'
    ? $('[data-save-syllabus]')
    : $('[data-open-versions]');
}

function renderVersionDialog() {
  const detail = displayDetail();
  const current = currentVersion(detail);
  const versions = versionsOf(detail);
  const saving = state.versionDialog.mode === 'save';
  const note = String(state.editor.note || '');
  $('[data-version-eyebrow]').textContent = saving ? 'Checkpoint editorial' : 'Histórico do syllabus';
  $('[data-version-title]').textContent = saving ? 'Registrar nova versão' : 'Versões do syllabus';
  $('[data-version-body]').innerHTML = saving
    ? `<section class="syl-version-save-summary">
        <span>Próxima versão</span>
        <strong>Versão ${Number(latestVersion(detail)?.seq || 0) + 1}</strong>
        <p>As alterações serão preservadas como uma nova edição. A versão ${esc(current?.seq ?? '—')} continuará disponível no histórico.</p>
      </section>
      <label class="syl-form-field syl-version-reason">
        <span>Razão da nova versão</span>
        <textarea class="field" maxlength="500" rows="3" data-version-note required placeholder="Resuma o que mudou e por quê.">${esc(note)}</textarea>
        <small><span>Este comentário ajuda a entender a evolução do syllabus.</span><b data-version-note-count>${[...note].length}/500</b></small>
      </label>
      <p class="syl-form-error" role="alert" data-version-error>${esc(state.versionDialog.error || '')}</p>`
    : `<p class="syl-version-dialog__intro">Cada edição permanece acessível com o comentário registrado no momento da mudança.</p>
      <ol class="syl-version-list">
        ${versions.map((entry, index) => {
          const selected = entry.id === current?.id;
          const entryNote = String(entry.note || '').trim();
          return `<li class="syl-version-card${selected ? ' is-current' : ''}">
            <div class="syl-version-card__marker" aria-hidden="true"></div>
            <div class="syl-version-card__content">
              <div class="syl-version-card__heading">
                <div><strong>Versão ${esc(entry.seq)}</strong><span>${esc(fmtDate(entry.created_at, true))}</span></div>
                <div class="syl-version-card__badges">${index === 0 ? '<span>Mais recente</span>' : ''}${selected ? '<span class="is-open">Versão aberta</span>' : ''}</div>
              </div>
              <p>${entryNote ? esc(entryNote) : '<em>Nenhum comentário registrado.</em>'}</p>
              ${selected ? '' : `<button class="button button--quiet" type="button" data-select-version="${esc(entry.id)}">Abrir versão ${esc(entry.seq)}</button>`}
            </div>
          </li>`;
        }).join('')}
      </ol>`;
  $('[data-version-footer]').innerHTML = saving
    ? `<button class="button button--quiet" type="button" data-version-close${state.editor.busy ? ' disabled' : ''}>Voltar</button>
       <button class="button button--primary" type="submit" data-confirm-version${state.editor.busy || !note.trim() ? ' disabled' : ''}>${state.editor.busy ? 'Criando…' : 'Criar versão'}</button>`
    : '<button class="button" type="button" data-version-close>Fechar</button>';
}

function openVersionDialog(mode, trigger = document.activeElement) {
  if (!state.detail || (mode === 'save' && (!state.editor.active || state.editor.busy))) return;
  state.versionDialog = { mode, trigger, error: null };
  renderVersionDialog();
  if (!versionDialog.open) versionDialog.showModal();
  window.setTimeout(() => {
    (mode === 'save' ? $('[data-version-note]') : $('[data-version-close]', versionDialog))?.focus();
  }, 0);
}

function closeVersionDialog() {
  if (state.editor.busy) return;
  if (versionDialog.open) versionDialog.close();
  const trigger = state.versionDialog.trigger;
  state.versionDialog = { mode: 'history', trigger: null, error: null };
  (trigger?.isConnected ? trigger : versionDialogTrigger())?.focus();
}

async function selectVersion(versionId) {
  if (!versionId || versionId === state.selectedVersionId) return;
  state.selectedVersionId = versionId;
  state.filters = { query: '', subject: '', mediaType: '', validation: '', complexity: '', showHidden: false };
  if (versionDialog.open) versionDialog.close();
  await loadDetail({ versionId });
  $('[data-open-versions]')?.focus();
}

function editorPosition(value) {
  const [lessonIndex, sourceIndex] = String(value || '').split(':').map(Number);
  if (!Number.isInteger(lessonIndex) || !Number.isInteger(sourceIndex)) return null;
  const lesson = state.editor.lessons?.[lessonIndex];
  const source = lesson?.sources?.[sourceIndex];
  return lesson && source ? { lessonIndex, sourceIndex, lesson, source } : null;
}

function moveArrayItem(items, index, offset) {
  const next = index + offset;
  if (!Array.isArray(items) || index < 0 || next < 0 || next >= items.length) return false;
  [items[index], items[next]] = [items[next], items[index]];
  return true;
}

function addEditorSource(lessonIndex) {
  const lesson = state.editor.lessons?.[lessonIndex];
  if (!lesson) return;
  lesson.sources ||= [];
  lesson.sources.push({
    reference_id: null,
    source_id: null,
    title: '',
    description: '',
    url: '',
    media_type: 'article',
    resource_code: '',
    scope_kind: '',
    scope_value: '',
    hidden: false,
    __new: true,
  });
  markEditorDirty();
  renderDetail();
  window.setTimeout(() => {
    const index = lesson.sources.length - 1;
    document.querySelector(`[data-source-field="title"][data-lesson-index="${lessonIndex}"][data-source-index="${index}"]`)?.focus();
  }, 0);
}

function removeEditorSource(position) {
  const found = editorPosition(position);
  if (!found) return;
  found.lesson.sources.splice(found.sourceIndex, 1);
  markEditorDirty();
  renderDetail();
}

function toggleEditorSourceHidden(position) {
  const found = editorPosition(position);
  if (!found) return;
  found.source.hidden = !found.source.hidden;
  if (found.source.hidden) state.filters.showHidden = true;
  markEditorDirty();
  renderDetail();
}

function toggleEditorLessonHidden(index) {
  const lesson = state.editor.lessons?.[Number(index)];
  if (!lesson) return;
  lesson.hidden = !lesson.hidden;
  if (lesson.hidden) state.filters.showHidden = true;
  markEditorDirty();
  renderDetail();
}

function moveEditorSource(position, offset) {
  const found = editorPosition(position);
  if (!found || !moveArrayItem(found.lesson.sources, found.sourceIndex, offset)) return;
  markEditorDirty();
  renderDetail();
}

function moveEditorLesson(index, offset) {
  if (!moveArrayItem(state.editor.lessons, Number(index), offset)) return;
  markEditorDirty();
  renderDetail();
}

function sourceByReferenceId(referenceId) {
  for (const lesson of state.detail?.lessons || []) {
    const source = (lesson.sources || []).find((candidate) => candidate.reference_id === referenceId);
    if (source) return { lesson, source };
  }
  return null;
}

function editBookScope(referenceId) {
  const found = sourceByReferenceId(referenceId);
  if (!found) return;
  const lessonIndex = (state.detail?.lessons || []).indexOf(found.lesson);
  const sourceIndex = (found.lesson.sources || []).indexOf(found.source);
  if (lessonIndex < 0 || sourceIndex < 0) return;
  startEditing(found.lesson.id);
  const scopeKind = viewHost.querySelector(
    `[data-source-field="scope_kind"][data-lesson-index="${lessonIndex}"][data-source-index="${sourceIndex}"]`
  );
  if (!scopeKind) return;
  scopeKind.closest('[data-editor-source]')?.scrollIntoView({ block: 'center' });
  scopeKind.focus();
  announce('Informe as páginas ou capítulos deste livro. Salvar criará uma nova versão do syllabus.');
}

async function updateSourceReview(referenceId, changes) {
  const found = sourceByReferenceId(referenceId);
  if (!found || state.reviewBusyReferenceIds.has(referenceId)) return;
  state.reviewBusyReferenceIds.add(referenceId);
  renderDetail();
  try {
    const response = await fetch(
      `/api/syllabi/${encodeURIComponent(routeId)}/sources/${encodeURIComponent(referenceId)}/review`,
      {
        method: 'PATCH',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify(changes),
      },
    );
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    found.source.review = body.review;
    if ('validated' in changes) {
      state.expandedLessonIds.delete(found.lesson.id);
      const selected = selectedReferencesForLesson(found.lesson.id);
      if (body.review?.validated && hasCurrentSourcePublication(found.source)) selected.add(String(referenceId));
      else selected.delete(String(referenceId));
      // Validation and a current Source Publication jointly control Lesson
      // Build eligibility, so refresh the server projection before rendering.
      await loadDetail({ versionId: state.selectedVersionId, silent: true });
    }
    announce('Organização do autoestudo atualizada.');
  } catch (error) {
    announce(`Não foi possível atualizar o autoestudo: ${error.message}`);
  } finally {
    state.reviewBusyReferenceIds.delete(referenceId);
    renderDetail();
  }
}

async function copyBookCode(code) {
  const value = String(code || '').trim();
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    announce(`Código do livro copiado: ${value}`);
  } catch (_error) {
    announce('Não foi possível copiar o código do livro. Selecione o código e tente novamente.');
  }
}

function toggleLessonExpanded(lessonId) {
  const lesson = (state.detail?.lessons || []).find((entry) => entry.id === lessonId);
  if (!lesson) return;
  if (lessonIsCollapsed(lesson)) {
    state.collapsedLessonIds.delete(lessonId);
    state.expandedLessonIds.add(lessonId);
  } else {
    state.collapsedLessonIds.add(lessonId);
    state.expandedLessonIds.delete(lessonId);
  }
  renderDetail();
}

function updateEditorField(target) {
  if (!state.editor.active) return false;
  const lessonIndex = Number(target.dataset.lessonIndex);
  const lesson = state.editor.lessons?.[lessonIndex];
  if (!lesson) return false;
  if (target.dataset.lessonField) {
    const field = target.dataset.lessonField;
    lesson[field] = field === 'week' ? (target.value ? Number(target.value) : null) : target.value;
    markEditorDirty();
    return field;
  }
  if (target.dataset.sourceField) {
    const source = lesson.sources?.[Number(target.dataset.sourceIndex)];
    if (!source) return false;
    const field = target.dataset.sourceField;
    source[field] = target.value;
    if (field === 'scope_kind' && !target.value) source.scope_value = '';
    markEditorDirty();
    return field;
  }
  return false;
}

function editorPayload() {
  return (state.editor.lessons || []).map((lesson) => ({
    id: lesson.id || null,
    hidden: Boolean(lesson.hidden),
    week: lesson.week ?? null,
    kind: lesson.kind || 'Class',
    title: String(lesson.title || '').trim(),
    subject: String(lesson.subject || '').trim() || null,
    subjects: lessonSubjects(lesson.subjects),
    date: lesson.date || null,
    description: String(lesson.description || '').trim() || null,
    sources: (lesson.sources || []).map((source) => ({
      reference_id: source.reference_id || null,
      title: String(source.title || '').trim(),
      description: String(source.description || '').trim() || null,
      url: String(source.url || '').trim() || null,
      media_type: source.media_type || 'article',
      resource_code: String(source.resource_code || '').trim() || null,
      scope_kind: source.scope_kind || null,
      scope_value: String(source.scope_value || '').trim() || null,
      hidden: Boolean(source.hidden),
    })),
  }));
}

async function saveEditor() {
  if (!state.editor.active || state.editor.busy || !state.detail) return;
  const lessons = editorPayload();
  const note = String(state.editor.note || '').trim();
  if (!note) {
    state.versionDialog.error = 'Informe a razão da nova versão antes de salvar.';
    renderVersionDialog();
    $('[data-version-note]')?.focus();
    return;
  }
  const missingLesson = lessons.findIndex((lesson) => !lesson.title);
  if (missingLesson >= 0) {
    announce(`Dê um nome à aula ${missingLesson + 1} antes de salvar.`);
    return;
  }
  for (let lessonIndex = 0; lessonIndex < lessons.length; lessonIndex += 1) {
    const missingSource = lessons[lessonIndex].sources.findIndex((source) => !source.title);
    if (missingSource >= 0) {
      announce(`Dê um nome à fonte ${missingSource + 1} da aula ${lessonIndex + 1} antes de salvar.`);
      return;
    }
  }
  state.editor.busy = true;
  renderDetail();
  renderVersionDialog();
  announce('Compilando a nova versão e o XLSX…');
  try {
    const response = await fetch(`/api/syllabi/${encodeURIComponent(routeId)}/curate`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        base_version_id: currentVersion(state.detail)?.id,
        note,
        lessons,
      }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    if (versionDialog.open) versionDialog.close();
    state.editor = { active: false, busy: false, dirty: false, lessons: null, targetLessonId: null, note: '' };
    state.versionDialog = { mode: 'history', trigger: null, error: null };
    state.filters = { query: '', subject: '', mediaType: '', validation: '', complexity: '', showHidden: false };
    state.selectedVersionId = body.version_id;
    announce(body.unchanged
      ? 'Nenhuma mudança foi detectada; a versão atual foi mantida.'
      : `Versão ${body.seq} salva. O novo XLSX já pode ser baixado.`);
    await loadDetail({ versionId: body.version_id, silent: true });
    $('[data-open-versions]')?.focus();
  } catch (error) {
    state.editor.busy = false;
    state.versionDialog.error = error.message;
    renderDetail();
    renderVersionDialog();
    announce(`Não foi possível salvar a nova versão: ${error.message}`);
  }
}

function reconciliationUrl(reconciliationId = null) {
  const url = new URL(window.location.href);
  url.searchParams.delete('prototype');
  if (reconciliationId) url.searchParams.set('reconciliation', reconciliationId);
  else url.searchParams.delete('reconciliation');
  window.history.replaceState({}, '', url);
}

function closeReconciliation({ reload = false } = {}) {
  state.reconciliationCleanup?.();
  state.reconciliationCleanup = null;
  state.reconciliation = null;
  reconciliationUrl();
  if (reload) loadDetail({ versionId: state.selectedVersionId });
  else renderDetail();
}

async function applyReconciliation(payload) {
  const reconciliation = state.reconciliation;
  if (!reconciliation) throw new Error('A comparação não está mais disponível.');
  const response = await fetch(
    `/api/syllabi/${encodeURIComponent(routeId)}/reconciliations/${encodeURIComponent(reconciliation.id)}/apply`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  );
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
  state.reconciliationCleanup?.();
  state.reconciliationCleanup = null;
  state.reconciliation = null;
  state.selectedVersionId = body.version_id || state.selectedVersionId;
  reconciliationUrl();
  announce(body.unchanged
    ? 'Comparação concluída; a versão atual já representa suas escolhas.'
    : `Versão ${body.seq} criada a partir das escolhas revisadas.`);
  await loadDetail({ versionId: state.selectedVersionId, silent: true });
  return body;
}

async function showReconciliation(reconciliation) {
  state.reconciliationCleanup?.();
  state.reconciliation = reconciliation;
  reconciliationUrl(reconciliation.id);
  const { mountSyllabusReconciliation } = await import('/static/syllabus_reconciliation.js?v=10');
  state.reconciliationCleanup = mountSyllabusReconciliation({
    headingHost,
    viewHost,
    reconciliation,
    announce,
    onCancel: () => closeReconciliation(),
    onApplied: applyReconciliation,
  });
}

async function loadReconciliation(reconciliationId) {
  state.loading = true;
  viewHost.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(
      `/api/syllabi/${encodeURIComponent(routeId)}/reconciliations/${encodeURIComponent(reconciliationId)}`,
      { headers: { Accept: 'application/json' } },
    );
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    await showReconciliation(body);
  } catch (error) {
    reconciliationUrl();
    state.error = error.message;
    viewHost.innerHTML = renderError(error.message);
  } finally {
    state.loading = false;
    viewHost.setAttribute('aria-busy', 'false');
  }
}

function renderUploadCatalog() {
  const select = uploadForm.elements.institution_id;
  const error = $('[data-catalog-error]');
  if (state.catalog.error) {
    select.innerHTML = '<option value="">Não foi possível carregar</option>';
    select.disabled = true;
    error.textContent = `Não foi possível carregar o cadastro: ${state.catalog.error}`;
    return;
  }
  const institutions = state.catalog.institutions;
  if (!institutions.length) {
    select.innerHTML = '<option value="">Nenhuma instituição cadastrada</option>';
    select.disabled = true;
    error.textContent = 'O Companion não retornou nenhuma instituição.';
    return;
  }
  select.innerHTML = `<option value="">Selecione a instituição</option>${institutions.map((institution) => (
    `<option value="${esc(institution.slug)}">${esc(institution.name)}</option>`
  )).join('')}`;
  select.disabled = false;
  error.textContent = '';
}

async function loadUploadCatalog() {
  if (state.catalog.loaded) {
    renderUploadCatalog();
    scheduleGraphProposal();
    return;
  }
  if (state.catalog.loading) return;
  state.catalog.loading = true;
  const select = uploadForm.elements.institution_id;
  select.innerHTML = '<option value="">Carregando instituições…</option>';
  select.disabled = true;
  try {
    const response = await fetch('/api/companion/graph-namespace', { headers: { Accept: 'application/json' } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    state.catalog.institutions = body.institutions || [];
    state.catalog.graphIds = body.graph_ids || [];
    state.catalog.error = null;
    state.catalog.loaded = true;
  } catch (error) {
    state.catalog.error = error.message;
  } finally {
    state.catalog.loading = false;
    if (state.upload.mode === 'new' && uploadDialog.open) {
      renderUploadCatalog();
      scheduleGraphProposal();
    }
  }
}

let graphProposalTimer = null;

function hideIdentityConflicts() {
  $('[data-graph-conflict]').hidden = true;
  $('[data-syllabus-conflict]').hidden = true;
}

function renderUploadSubmitState() {
  const submit = $('[data-upload-submit]');
  const isVersion = state.upload.mode === 'version';
  submit.disabled = state.upload.busy || (!isVersion && state.upload.identityStatus !== 'derived');
  if (state.upload.busy) {
    submit.textContent = isVersion ? 'Comparando…' : 'Registrando…';
  } else {
    submit.textContent = isVersion ? 'Comparar planilha' : 'Adicionar syllabus';
  }
}

function setGraphIdentityStatus(statusName, message = '') {
  state.upload.identityStatus = statusName;
  const status = $('[data-graph-id-status]');
  status.hidden = !message;
  status.textContent = message;
  status.dataset.state = statusName;
  renderUploadSubmitState();
}

function resetGraphIdentity() {
  if (graphProposalTimer) window.clearTimeout(graphProposalTimer);
  graphProposalTimer = null;
  state.upload.proposalToken += 1;
  state.upload.proposedGraphId = '';
  $('[data-graph-preview]').hidden = true;
  $('[data-graph-display-name]').textContent = '';
  $('[data-proposed-graph-id]').textContent = '';
  hideIdentityConflicts();
  setGraphIdentityStatus('idle');
}

function showGraphConflict(detail) {
  $('[data-syllabus-conflict]').hidden = true;
  const conflict = $('[data-graph-conflict]');
  const graphId = String(detail?.graph_id || '').trim();
  if (graphId) {
    state.upload.proposedGraphId = graphId;
    $('[data-proposed-graph-id]').textContent = graphId;
    $('[data-graph-preview]').hidden = false;
  }
  setGraphIdentityStatus('conflict');
  conflict.hidden = false;
  conflict.scrollIntoView({ block: 'nearest' });
}

function showSyllabusConflict(detail) {
  $('[data-graph-conflict]').hidden = true;
  const conflict = $('[data-syllabus-conflict]');
  const syllabusId = String(detail?.syllabus_id || detail?.id || '').trim();
  const ownerTitle = String(detail?.title || '').trim();
  $('[data-syllabus-conflict-copy]').textContent = detail?.identity_collision
    ? `Este nome usa a mesma identidade do syllabus${ownerTitle ? ` “${ownerTitle}”` : ' existente'}. Abra-o para adicionar uma versão ou escolha outro nome.`
    : 'Este nome já existe. Você está adicionando uma versão a esse syllabus.';
  $('[data-open-existing]').href = `/syllabi?id=${encodeURIComponent(syllabusId)}`;
  setGraphIdentityStatus('conflict');
  conflict.hidden = false;
  conflict.scrollIntoView({ block: 'nearest' });
}

async function refreshGraphProposal() {
  if (state.upload.mode !== 'new' || !uploadDialog.open) return;
  const name = String(uploadForm.elements.name.value || '').trim();
  const institutionId = String(uploadForm.elements.institution_id.value || '').trim();
  const preview = $('[data-graph-preview]');
  hideIdentityConflicts();
  if (!name || !institutionId) {
    state.upload.proposedGraphId = '';
    preview.hidden = true;
    setGraphIdentityStatus('idle');
    return;
  }
  const token = ++state.upload.proposalToken;
  try {
    const query = new URLSearchParams({ institution_id: institutionId, name });
    const response = await fetch(`/api/syllabi/graph-id-proposal?${query}`, {
      headers: { Accept: 'application/json' },
    });
    const body = await response.json().catch(() => ({}));
    if (token !== state.upload.proposalToken) return;
    if (!response.ok && response.status === 422) {
      preview.hidden = false;
      $('[data-graph-display-name]').textContent = name;
      $('[data-proposed-graph-id]').textContent = 'Continue digitando…';
      setGraphIdentityStatus('error', 'Continue digitando para gerar um modelo válido.');
      return;
    }
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    state.upload.proposedGraphId = String(body.graph_id_template || '');
    $('[data-graph-display-name]').textContent = body.display_name || name;
    $('[data-proposed-graph-id]').textContent = state.upload.proposedGraphId;
    preview.hidden = false;
    if (body.existing_syllabus) {
      showSyllabusConflict({
        ...body.existing_syllabus,
        syllabus_id: body.existing_syllabus.id,
        title: body.existing_syllabus.title,
      });
      return;
    }
    // Before parsing the workbook this is a per-Subject template, not a
    // concrete Graph ID. A normalized syllabus-id owner is an identity
    // collision; concrete namespace conflicts are checked during import.
    if (body.syllabus_id_owner) {
      showSyllabusConflict({
        ...body.syllabus_id_owner,
        syllabus_id: body.syllabus_id_owner.id,
        identity_collision: true,
      });
      return;
    }
    setGraphIdentityStatus(
      'derived',
      'Modelo derivado. Os Graph IDs concretos serão verificados no envio.',
    );
  } catch (error) {
    if (token !== state.upload.proposalToken) return;
    preview.hidden = false;
    $('[data-graph-display-name]').textContent = name;
    $('[data-proposed-graph-id]').textContent = 'Não foi possível calcular';
    setGraphIdentityStatus('error', 'Não foi possível derivar o modelo.');
    $('[data-upload-error]').textContent = `Não foi possível gerar o modelo de Graph ID: ${error.message}`;
  }
}

function scheduleGraphProposal({ resetManual = false } = {}) {
  if (resetManual) {
    const name = String(uploadForm.elements.name.value || '').trim();
    const institutionId = String(uploadForm.elements.institution_id.value || '').trim();
    state.upload.proposalToken += 1;
    state.upload.proposedGraphId = '';
    $('[data-graph-preview]').hidden = !name || !institutionId;
    $('[data-graph-display-name]').textContent = name;
    $('[data-proposed-graph-id]').textContent = name && institutionId ? 'Calculando…' : '';
    hideIdentityConflicts();
    setGraphIdentityStatus(
      name && institutionId ? 'calculating' : 'idle',
      name && institutionId ? 'Derivando o modelo de Graph ID…' : '',
    );
  }
  if (graphProposalTimer) window.clearTimeout(graphProposalTimer);
  graphProposalTimer = window.setTimeout(refreshGraphProposal, 120);
}

function openUpload(mode) {
  state.upload = {
    mode,
    syllabusId: mode === 'version' ? routeId : null,
    busy: false,
    identityStatus: 'idle',
    proposedGraphId: '',
    proposalToken: state.upload.proposalToken + 1,
  };
  uploadForm.reset();
  resetGraphIdentity();
  $('[data-upload-error]').textContent = '';
  $('[data-file-name]').textContent = 'Escolher arquivo .xlsx';
  const nameField = $('[data-name-field]');
  const syllabusFields = $('[data-syllabus-fields]');
  const nameInput = uploadForm.elements.name;
  const isVersion = mode === 'version';
  $('[data-new-upload-mode]').hidden = isVersion;
  $('[data-version-upload-mode]').hidden = !isVersion;
  nameField.hidden = isVersion;
  syllabusFields.hidden = isVersion;
  syllabusFields.disabled = isVersion;
  nameInput.required = !isVersion;
  nameInput.disabled = isVersion;
  nameInput.value = isVersion ? (state.detail?.title || state.detail?.name || '') : '';
  uploadForm.elements.institution_id.required = !isVersion;
  if (isVersion) {
    $('[data-version-syllabus-name]').textContent = state.detail?.title || 'Syllabus';
    $('[data-version-institution]').textContent = state.detail?.institution?.name || 'Não definida';
    const graphIds = (state.detail?.export_identities || [])
      .map((identity) => String(identity.graph_id || '').trim())
      .filter(Boolean);
    $('[data-version-graph-id]').textContent = graphIds.join(' · ') || 'Não definido';
  }
  $('[data-upload-eyebrow]').textContent = isVersion ? 'Nova versão' : 'Novo syllabus';
  $('[data-upload-title]').textContent = isVersion ? `Atualizar ${state.detail?.title || 'syllabus'}` : 'Adicionar syllabus';
  renderUploadSubmitState();
  uploadDialog.showModal();
  if (!isVersion) loadUploadCatalog();
  window.setTimeout(() => (isVersion ? $('[data-upload-file]') : nameInput).focus(), 0);
}

function closeUpload() {
  if (state.upload.busy) return;
  uploadDialog.close();
}

async function submitUpload(event) {
  event.preventDefault();
  if (state.upload.busy) return;
  const data = new FormData(uploadForm);
  const file = data.get('file');
  const name = String(data.get('name') || '').trim();
  for (const fieldName of ['name', 'institution_id']) {
    if (data.has(fieldName)) data.set(fieldName, String(data.get(fieldName) || '').trim());
  }
  if (!file?.name || !/\.xlsx$/i.test(file.name)) {
    $('[data-upload-error]').textContent = 'Escolha uma planilha .xlsx válida.';
    return;
  }
  if (state.upload.mode === 'new' && !name) {
    $('[data-upload-error]').textContent = 'Dê um nome ao syllabus.';
    return;
  }
  if (state.upload.mode === 'new' && !data.get('institution_id')) {
    $('[data-upload-error]').textContent = 'Selecione uma instituição cadastrada.';
    return;
  }
  if (state.upload.mode === 'new' && state.upload.identityStatus !== 'derived') {
    scheduleGraphProposal({ resetManual: true });
    return;
  }
  if (state.upload.syllabusId) data.set('syllabus_id', state.upload.syllabusId);
  state.upload.busy = true;
  renderUploadSubmitState();
  $('[data-upload-error]').textContent = '';
  try {
    const endpoint = state.upload.mode === 'version'
      ? `/api/syllabi/${encodeURIComponent(routeId)}/reconciliations`
      : '/api/syllabi/upload';
    const response = await fetch(endpoint, { method: 'POST', body: data });
    const body = await response.json().catch(() => ({}));
    if (!response.ok && body.detail?.code === 'graph_id_conflict') {
      showGraphConflict(body.detail);
      return;
    }
    if (!response.ok && body.detail?.code === 'syllabus_already_exists') {
      showSyllabusConflict({
        ...body.detail,
        title: name,
      });
      return;
    }
    if (!response.ok) {
      const detail = typeof body.detail === 'string' ? body.detail : body.detail?.message;
      throw new Error(detail || `o servidor respondeu ${response.status}`);
    }
    uploadDialog.close();
    const droppedNote = intakeDropNote(body.dropped_summary || body.incoming?.dropped_summary);
    if (state.upload.mode === 'new') {
      const message = body.unchanged
        ? `A planilha é igual à versão atual.${droppedNote}`
        : `Syllabus adicionado. Nenhuma fonte foi processada automaticamente.${droppedNote}`;
      announce(message);
      // The page navigates away right now; the destination announces the note.
      storeIntakeNote(body.syllabus_id, message);
      window.location.assign(`/syllabi?id=${encodeURIComponent(body.syllabus_id)}`);
    } else {
      announce(`Planilha comparada. Revise as mudanças antes de criar a nova versão.${droppedNote}`);
      await showReconciliation(body);
    }
  } catch (error) {
    $('[data-upload-error]').textContent = `Não foi possível registrar a planilha: ${error.message}`;
  } finally {
    state.upload.busy = false;
    renderUploadSubmitState();
  }
}

function replaceSourceState(sourceId, payload) {
  for (const lesson of state.detail?.lessons || []) {
    const source = (lesson.sources || []).find((entry) => (entry.source_id || entry.id) === sourceId);
    if (!source) continue;
    source.job = payload.job || payload;
    const jobStatus = String(source.job?.status || '').toLowerCase();
    if (['queued', 'running'].includes(jobStatus)) {
      source.pipeline = { status: jobStatus === 'queued' ? 'queued' : 'extracting' };
      if (String(source.media_type || source.type || '').toLowerCase().includes('video')) {
        source.video_progress = {
          stage: jobStatus,
          speech: source.video_progress?.speech || null,
        };
      }
      delete source.image_branch;
      source.has_markdown = false;
      delete source.markdown;
    }
    if (payload.has_markdown !== undefined) source.has_markdown = payload.has_markdown;
    if (payload.markdown) source.markdown = payload.markdown;
    return;
  }
}

async function queueSource(sourceId) {
  if (!sourceId) return;
  const sourceNode = document.querySelector(`[data-source-id="${CSS.escape(sourceId)}"]`);
  const button = sourceNode?.querySelector('[data-queue-source]');
  if (button) button.disabled = true;
  announce('Adicionando a fonte à fila…');
  try {
    const response = await fetch(`/api/sources/${encodeURIComponent(sourceId)}/queue`, {
      method: 'POST', headers: { Accept: 'application/json' },
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    replaceSourceState(sourceId, body);
    announce('Fonte adicionada à fila. Você pode continuar usando o syllabus.');
    renderDetail();
  } catch (error) {
    announce(`Não foi possível enfileirar a fonte: ${error.message}`);
    if (button) button.disabled = false;
  }
}

function sourceById(sourceId) {
  for (const lesson of state.detail?.lessons || []) {
    const source = (lesson.sources || []).find(
      (entry) => (entry.source_id || entry.id) === sourceId,
    );
    if (source) return source;
  }
  return null;
}

async function preflightVideo(sourceId) {
  if (!sourceId) return;
  announce('Verificando o vídeo…');
  try {
    const response = await fetch(
      `/api/sources/${encodeURIComponent(sourceId)}/video-preflight`,
      { method: 'POST', headers: { Accept: 'application/json' } },
    );
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    const source = sourceById(sourceId);
    if (source) source.video_preflight = body.video_preflight;
    announce('Vídeo verificado.');
    renderDetail();
  } catch (error) {
    announce(`Não foi possível verificar o vídeo: ${error.message}`);
  }
}

async function authorizeVideo(sourceId) {
  if (!sourceId) return;
  announce('Confirmando e adicionando o vídeo à fila…');
  try {
    const response = await fetch(
      `/api/sources/${encodeURIComponent(sourceId)}/authorize-transcription`,
      { method: 'POST', headers: { Accept: 'application/json' } },
    );
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    replaceSourceState(sourceId, body);
    announce('Vídeo confirmado e adicionado à fila.');
    renderDetail();
  } catch (error) {
    announce(`Não foi possível confirmar o processamento: ${error.message}`);
  }
}

function humanFileSize(bytes) {
  const value = Number(bytes || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(value < 10 * 1024 ? 1 : 0)} KB`;
  return `${(value / (1024 * 1024)).toFixed(value < 10 * 1024 * 1024 ? 1 : 0)} MB`;
}

function classifyManualFile(file) {
  const type = String(file?.type || '').toLowerCase();
  const name = String(file?.name || '').toLowerCase();
  if (type === 'application/pdf' || (!type && name.endsWith('.pdf'))) return 'pdf';
  if (['image/png', 'image/jpeg', 'image/webp'].includes(type)) return 'image';
  if (!type && /\.(png|jpe?g|webp)$/.test(name)) return 'image';
  return null;
}

function revokeManualItems(items = state.manualUpload.items) {
  for (const item of items) {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
  }
}

function clearManualItems() {
  revokeManualItems();
  state.manualUpload.items = [];
  const input = $('[data-manual-files]');
  if (input) input.value = '';
}

function manualItem(file) {
  const isImage = classifyManualFile(file) === 'image';
  return {
    file,
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    previewUrl: isImage ? URL.createObjectURL(file) : null,
  };
}

function renderManualUpload() {
  const manual = state.manualUpload;
  const isPdf = manual.kind === 'pdf';
  const isImages = manual.kind === 'images';
  document.querySelectorAll('[data-manual-kind]').forEach((button) => {
    const active = button.dataset.manualKind === manual.kind;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-pressed', String(active));
    button.disabled = manual.busy;
  });

  const picker = $('[data-manual-picker]');
  const input = $('[data-manual-files]');
  picker.hidden = !manual.kind;
  if (manual.kind) {
    input.accept = isPdf ? 'application/pdf,.pdf' : 'image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp';
    input.multiple = isImages;
    $('[data-manual-picker-title]').textContent = isPdf
      ? (manual.items.length ? 'Trocar PDF' : 'Escolher PDF')
      : (manual.items.length ? 'Adicionar screenshots' : 'Escolher screenshots');
    $('[data-manual-picker-help]').textContent = isPdf
      ? 'PDF · um arquivo'
      : 'PNG, JPEG ou WebP · até 50 imagens';
  }

  const selection = $('[data-manual-selection]');
  selection.hidden = manual.items.length === 0;
  $('[data-manual-count]').textContent = isImages
    ? `${manual.items.length} ${manual.items.length === 1 ? 'imagem selecionada' : 'imagens selecionadas'}`
    : 'PDF selecionado';
  $('[data-manual-order-help]').textContent = isImages && manual.items.length > 1
    ? 'A ordem abaixo será a ordem do Markdown.'
    : '';
  $('[data-manual-file-list]').innerHTML = manual.items.map((item, index) => {
    const file = item.file;
    const image = item.previewUrl
      ? `<img src="${esc(item.previewUrl)}" alt="Prévia de ${esc(file.name)}">`
      : `<span class="syl-manual-file__pdf" aria-hidden="true">PDF</span>`;
    return `<li class="syl-manual-file" data-manual-item="${esc(item.id)}">
      <span class="syl-manual-file__preview">${image}</span>
      <span class="syl-manual-file__identity">
        ${isImages ? `<small>Imagem ${index + 1} de ${manual.items.length}</small>` : ''}
        <strong title="${esc(file.name)}">${esc(file.name)}</strong>
        <span>${esc(file.type || (isPdf ? 'application/pdf' : 'imagem'))} · ${esc(humanFileSize(file.size))}<span data-manual-dimensions></span></span>
      </span>
      <span class="syl-manual-file__controls">
        ${isImages ? `<button class="syl-file-order" type="button" data-manual-up="${index}" aria-label="Mover ${esc(file.name)} para cima"${index === 0 || manual.busy ? ' disabled' : ''}>↑</button>
          <button class="syl-file-order" type="button" data-manual-down="${index}" aria-label="Mover ${esc(file.name)} para baixo"${index === manual.items.length - 1 || manual.busy ? ' disabled' : ''}>↓</button>` : ''}
        <button class="syl-file-remove" type="button" data-manual-remove="${index}" aria-label="Remover ${esc(file.name)}"${manual.busy ? ' disabled' : ''}>Remover</button>
      </span>
    </li>`;
  }).join('');
  document.querySelectorAll('[data-manual-item]').forEach((node) => {
    const image = node.querySelector('img');
    const dimensions = node.querySelector('[data-manual-dimensions]');
    if (!image || !dimensions) return;
    const showDimensions = () => {
      if (image.naturalWidth && image.naturalHeight) {
        dimensions.textContent = ` · ${image.naturalWidth} × ${image.naturalHeight} px`;
      }
    };
    if (image.complete) showDimensions();
    else image.addEventListener('load', showDimensions, { once: true });
  });

  const valid = (isPdf && manual.items.length === 1)
    || (isImages && manual.items.length >= 1 && manual.items.length <= 50);
  $('[data-manual-submit]').disabled = !valid || manual.busy;
  $('[data-manual-submit]').textContent = manual.busy ? 'Enviando…' : 'Processar e criar Markdown';
  input.disabled = manual.busy;
}

function chooseManualKind(kind) {
  if (!['pdf', 'images'].includes(kind) || state.manualUpload.busy) return;
  if (state.manualUpload.kind && state.manualUpload.kind !== kind && state.manualUpload.items.length) {
    clearManualItems();
    $('[data-manual-error]').textContent = 'A seleção anterior foi removida: PDF e imagens não podem ser misturados.';
  } else {
    $('[data-manual-error]').textContent = '';
  }
  state.manualUpload.kind = kind;
  renderManualUpload();
  window.setTimeout(() => $('[data-manual-files]')?.focus(), 0);
}

function addManualFiles(fileList) {
  const manual = state.manualUpload;
  const files = [...(fileList || [])];
  if (!manual.kind || !files.length || manual.busy) return;
  $('[data-manual-error]').textContent = '';

  if (manual.kind === 'pdf') {
    if (files.length !== 1 || classifyManualFile(files[0]) !== 'pdf') {
      $('[data-manual-error]').textContent = 'Escolha exatamente um arquivo PDF.';
      return;
    }
    clearManualItems();
    manual.items = [manualItem(files[0])];
  } else {
    if (files.some((file) => classifyManualFile(file) !== 'image')) {
      $('[data-manual-error]').textContent = 'Use somente imagens PNG, JPEG ou WebP. PDF e imagens não podem ser misturados.';
      return;
    }
    if (manual.items.length + files.length > 50) {
      $('[data-manual-error]').textContent = `O limite é de 50 imagens. Remova ${manual.items.length + files.length - 50} antes de continuar.`;
      return;
    }
    manual.items.push(...files.map(manualItem));
  }
  $('[data-manual-files]').value = '';
  renderManualUpload();
}

function moveManualItem(index, offset) {
  const items = state.manualUpload.items;
  const next = index + offset;
  if (state.manualUpload.busy || index < 0 || next < 0 || next >= items.length) return;
  const movedId = items[index].id;
  [items[index], items[next]] = [items[next], items[index]];
  renderManualUpload();
  window.setTimeout(() => {
    const item = document.querySelector(`[data-manual-item="${CSS.escape(movedId)}"]`);
    const preferred = offset < 0 ? '[data-manual-up]:not(:disabled)' : '[data-manual-down]:not(:disabled)';
    (item?.querySelector(preferred)
      || item?.querySelector('[data-manual-up]:not(:disabled), [data-manual-down]:not(:disabled)')
      || item?.querySelector('[data-manual-remove]'))?.focus();
  }, 0);
}

function removeManualItem(index) {
  if (state.manualUpload.busy || index < 0 || index >= state.manualUpload.items.length) return;
  const [removed] = state.manualUpload.items.splice(index, 1);
  const focusId = state.manualUpload.items[index]?.id || state.manualUpload.items[index - 1]?.id || null;
  revokeManualItems([removed]);
  renderManualUpload();
  window.setTimeout(() => {
    if (focusId) {
      document.querySelector(`[data-manual-item="${CSS.escape(focusId)}"] [data-manual-remove]`)?.focus();
    } else {
      $('[data-manual-files]')?.focus();
    }
  }, 0);
}

function openManualUpload(sourceId, title) {
  if (!sourceId) return;
  clearManualItems();
  state.manualUpload = { sourceId, title: title || 'Fonte', kind: null, items: [], busy: false };
  $('[data-manual-title]').textContent = title || 'Usar PDF ou imagens';
  $('[data-manual-error]').textContent = '';
  renderManualUpload();
  manualDialog.showModal();
  window.setTimeout(() => $('[data-manual-kind="pdf"]')?.focus(), 0);
}

function closeManualUpload(force = false) {
  if (state.manualUpload.busy && !force) return;
  clearManualItems();
  state.manualUpload = { sourceId: null, title: '', kind: null, items: [], busy: false };
  manualDialog.close();
}

async function submitManualUpload(event) {
  event.preventDefault();
  const manual = state.manualUpload;
  if (!manual.sourceId || manual.busy) return;
  const isValid = (manual.kind === 'pdf' && manual.items.length === 1)
    || (manual.kind === 'images' && manual.items.length >= 1 && manual.items.length <= 50);
  if (!isValid) {
    $('[data-manual-error]').textContent = 'Escolha um PDF ou de 1 a 50 imagens para continuar.';
    return;
  }

  manual.busy = true;
  $('[data-manual-error]').textContent = '';
  renderManualUpload();
  const sourceId = manual.sourceId;
  const data = new FormData();
  data.append('kind', manual.kind);
  // Appending in the visible array order is the upload contract for screenshots.
  manual.items.forEach((item) => data.append('files', item.file, item.file.name));
  try {
    const response = await fetch(`/api/sources/${encodeURIComponent(sourceId)}/manual-upload`, {
      method: 'POST', body: data, headers: { Accept: 'application/json' },
    });
    const body = await response.json().catch(() => ({}));
    if (response.status !== 202) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    replaceSourceState(sourceId, body);
    closeManualUpload(true);
    announce('Arquivo recebido e adicionado à fila. O processamento termina em Markdown, sem iniciar um Lesson Build automaticamente.');
    renderDetail();
  } catch (error) {
    manual.busy = false;
    $('[data-manual-error]').textContent = `Não foi possível enviar o material: ${error.message}`;
    renderManualUpload();
  }
}

function originalImageLink(image) {
  if (image.asset_kind === 'video_frame') {
    const metadata = image.asset_metadata && typeof image.asset_metadata === 'object'
      ? image.asset_metadata : {};
    const videoId = String(metadata.video_id || '').trim();
    const seconds = Math.max(0, Math.floor(Number(metadata.timestamp_ms || 0) / 1000));
    if (/^[A-Za-z0-9_-]{6,}$/.test(videoId)) {
      return `<a href="https://www.youtube.com/watch?v=${esc(videoId)}&t=${seconds}s" target="_blank" rel="noopener noreferrer">Abrir vídeo neste ponto${ICON.external}</a>`;
    }
  }
  const original = safeUrl(image.original_url);
  return original
    ? `<a href="${esc(original.href)}" target="_blank" rel="noopener noreferrer">Abrir imagem original${ICON.external}</a>`
    : '';
}

function renderImageSidecar(payload) {
  const images = Array.isArray(payload.images) ? payload.images : [];
  if (!images.length) return '';
  const branch = payload.image_branch || {};
  const videoFrames = images.some((image) => image.asset_kind === 'video_frame');
  const singular = videoFrames ? 'quadro' : 'imagem';
  const plural = videoFrames ? 'quadros' : 'imagens';
  const useful = images.filter((image) => image.status === 'useful' && safeAssetUrl(image.asset_url));
  const attention = images.filter((image) => image.status === 'failed');
  const active = images.filter((image) => ['queued', 'running', 'downloaded'].includes(image.status));
  const filtered = Number(branch.filtered || 0);
  const notImportant = Number(branch.not_important || 0);
  const usefulMarkup = useful.map((image) => {
    const assetUrl = safeAssetUrl(image.asset_url);
    const analysis = image.analysis && typeof image.analysis === 'object' ? image.analysis : {};
    const description = String(analysis.description || '').trim();
    const visibleText = String(analysis.ocr || analysis.visible_text || '').trim();
    const limitations = String(analysis.limitations || '').trim();
    const alt = String(
      image.alt_text
      || description
      || `${videoFrames ? 'Quadro' : 'Imagem'} ${image.ordinal || ''}`,
    ).trim();
    const timestampMs = Number(image.asset_metadata?.timestamp_ms);
    const timestamp = Number.isFinite(timestampMs)
      ? new Date(Math.max(0, timestampMs)).toISOString().slice(14, 19)
      : null;
    return `<article class="syl-image-card">
      <img src="${esc(assetUrl)}" alt="${esc(alt)}" loading="lazy">
      <div class="syl-image-card__body">
        <div class="syl-image-card__top"><strong>${videoFrames ? 'Quadro útil' : 'Imagem útil'}${timestamp ? ` · ${esc(timestamp)}` : ` ${esc(image.ordinal || '')}`}</strong>${originalImageLink(image)}</div>
        ${description ? `<p>${esc(description)}</p>` : '<p>Descrição visual não disponível.</p>'}
        ${visibleText ? `<details><summary>Texto visível transcrito</summary><pre>${esc(visibleText)}</pre></details>` : ''}
        ${limitations ? `<p class="syl-image-card__limitation"><strong>Limitação:</strong> ${esc(limitations)}</p>` : ''}
      </div>
    </article>`;
  }).join('');
  const preservedLabel = videoFrames ? 'Quadro preservado' : 'Imagem preservada';
  const attentionMarkup = attention.map((image) => {
    const assetUrl = safeAssetUrl(image.asset_url);
    const alt = String(
      image.alt_text || `${videoFrames ? 'Quadro' : 'Imagem'} ${image.ordinal || ''}`,
    ).trim();
    return `<li>
      ${assetUrl ? `<img src="${esc(assetUrl)}" alt="${esc(alt)}" loading="lazy">` : ''}
      <div><strong>${assetUrl ? preservedLabel : (videoFrames ? 'Quadro' : 'Imagem')} ${esc(image.ordinal || '')}</strong><span>${esc(image.error || image.failure_code || `O ${singular} precisa de atenção.`)}</span></div>
      ${originalImageLink(image)}
    </li>`;
  }).join('');
  return `<section class="syl-image-sidecar" aria-labelledby="source-images-title">
    <header>
      <div><p class="syl-eyebrow">${videoFrames ? 'Quadros do vídeo' : 'Imagens da fonte'}</p><h2 id="source-images-title">Evidências visuais</h2></div>
      <span>${esc(Number(branch.useful || 0))} úteis · ${esc(Number(branch.total || images.length))} candidatas</span>
    </header>
    ${active.length ? `<p class="syl-image-sidecar__progress">${active.length} ${active.length === 1 ? `${singular} ainda está sendo preparado` : `${plural} ainda estão sendo preparados`}. O Markdown final só será publicado depois da análise visual e da limpeza.</p>` : ''}
    ${usefulMarkup ? `<div class="syl-image-grid">${usefulMarkup}</div>` : ''}
    ${attentionMarkup ? `<div class="syl-image-attention"><strong>${attention.length} ${attention.length === 1 ? `${singular} precisa` : `${plural} precisam`} de atenção</strong><ul>${attentionMarkup}</ul></div>` : ''}
    ${filtered ? `<p class="syl-image-sidecar__note">${filtered} ${filtered === 1 ? 'candidata permanece com uma classificação legada' : 'candidatas permanecem com classificações legadas'} e pode ser reavaliada pelo fluxo visual atual.</p>` : ''}
    ${notImportant ? `<p class="syl-image-sidecar__note">${notImportant} ${notImportant === 1 ? 'candidata foi classificada como irrelevante e foi omitida' : 'candidatas foram classificadas como irrelevantes e foram omitidas'} do Markdown; o resultado permanece no ledger.</p>` : ''}
  </section>`;
}

async function openMarkdown(sourceId, title) {
  if (!sourceId) return;
  state.markdownSourceId = sourceId;
  $('[data-markdown-heading]').textContent = title || 'Fonte';
  $('[data-markdown-meta]').innerHTML = '';
  $('[data-markdown-body]').innerHTML = '<div class="syl-loading"><span></span>Carregando Markdown…</div>';
  markdownDialog.showModal();
  try {
    const response = await fetch(`/api/sources/${encodeURIComponent(sourceId)}/markdown`, { headers: { Accept: 'application/json' } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || `o servidor respondeu ${response.status}`);
    if (state.markdownSourceId !== sourceId) return;
    $('[data-markdown-meta]').innerHTML = `${body.is_previous_version ? '<span>Última versão válida</span>' : ''}<span>${esc(body.tool || 'Ferramenta não informada')}</span><span>${esc(fmtDate(body.created_at, true))}</span>`;
    const renderedMarkdown = body.html || '<p>O artefato não contém conteúdo renderizável.</p>';
    $('[data-markdown-body]').innerHTML = renderedMarkdown + renderImageSidecar(body);
  } catch (error) {
    $('[data-markdown-body]').innerHTML = renderError(error.message, 'Fechar');
  }
}

function lessonById(lessonId) {
  return (state.detail?.lessons || []).find((lesson) => String(lesson.id) === String(lessonId)) || null;
}

function buildFromResponse(body) {
  if (!body || typeof body !== 'object') return null;
  return body.build && typeof body.build === 'object' ? body.build : body;
}

function lessonBuildApiPath(lessonId) {
  const versionId = currentVersion(state.detail)?.id || state.selectedVersionId;
  if (!routeId || !versionId || !lessonId) return null;
  return `/api/syllabi/${encodeURIComponent(routeId)}/versions/${encodeURIComponent(versionId)}/lessons/${encodeURIComponent(lessonId)}`;
}

function lessonBuildRequestKey() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function lessonBuildError(body, status) {
  const detail = body?.detail;
  return detail?.message || (typeof detail === 'string' ? detail : `o servidor respondeu ${status}`);
}

async function lessonBuildRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { Accept: 'application/json', ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(lessonBuildError(body, response.status));
  return body;
}

function buildStatusLabel(value) {
  return ({
    queued: 'Na fila',
    running: 'Em execução',
    succeeded: 'Concluído',
    failed: 'Falhou',
  })[String(value || '').toLowerCase()] || value || 'Não iniciado';
}

function graphRevisionMarkup(subjectGraph, acceptedRevision = null) {
  const graphId = subjectGraph?.graph_id;
  const currentRevision = subjectGraph?.current_revision;
  const revisions = subjectGraph?.revisions || [];
  if (!graphId || !currentRevision) return '';
  const graphPath = `/api/graphs/${encodeURIComponent(graphId)}`;
  const acceptedPath = acceptedRevision?.id
    ? `/api/graph-revisions/${encodeURIComponent(acceptedRevision.id)}`
    : null;
  return `<section class="syl-graph-revision">
    <div class="syl-graph-revision__heading">
      <strong>Graph Revision atual · ${Number(currentRevision.number)}</strong>
      <code>${esc(graphId)}</code>
    </div>
    <div class="syl-build-actions">
      <a class="button" href="${graphPath}/graph.json" target="_blank" rel="noopener noreferrer">Ver graph.json</a>
      <a class="button" href="${graphPath}/graph.json?download=true">Baixar graph.json</a>
      <button class="button" type="button" data-companion-package="${graphPath}/companion-package.zip">Baixar pacote Companion</button>
      ${acceptedPath ? `<a class="button" href="${acceptedPath}/graph.json" target="_blank" rel="noopener noreferrer">Ver revisão aceita</a>
        <a class="button" href="${acceptedPath}/graph.json?download=true">Baixar revisão aceita</a>
        <button class="button" type="button" data-companion-package="${acceptedPath}/companion-package.zip">Baixar pacote aceito</button>` : ''}
    </div>
    ${revisions.length > 1 ? `<details class="syl-build-history"><summary>Histórico de revisões</summary><ol>${revisions.map((revision) => {
      const revisionPath = `/api/graph-revisions/${encodeURIComponent(revision.id)}`;
      return `<li><span>Revisão ${Number(revision.number)}${revision.is_current ? ' · atual' : ''}</span><span><a href="${revisionPath}/graph.json" target="_blank" rel="noopener noreferrer">ver</a> · <a href="${revisionPath}/graph.json?download=true">baixar</a> · <button type="button" data-companion-package="${revisionPath}/companion-package.zip">pacote</button></span></li>`;
    }).join('')}</ol></details>` : ''}
  </section>`;
}

async function downloadCompanionPackage(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const isJson = (response.headers.get('content-type') || '').includes('json');
    const body = isJson ? await response.json().catch(() => ({})) : {};
    throw new Error(lessonBuildError(body, response.status));
  }
  const disposition = response.headers.get('content-disposition') || '';
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || 'companion-package.zip';
  const blobUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(blobUrl);
  announce('Pacote Companion validado e baixado.');
}

function updateLessonBuildProjection(build) {
  const lesson = lessonById(state.lessonBuild.lessonId);
  if (!lesson) return;
  lesson.lesson_build = { ...(lesson.lesson_build || {}), latest_build: build };
}

function scheduleLessonBuildPolling() {
  window.clearTimeout(state.lessonBuild.pollingTimer);
  state.lessonBuild.pollingTimer = null;
  const status = String(state.lessonBuild.build?.status || '').toLowerCase();
  if (!lessonBuildDialog.open || !['queued', 'running'].includes(status)) return;
  state.lessonBuild.pollingTimer = window.setTimeout(() => {
    refreshLessonBuild().catch((error) => {
      $('[data-lesson-build-error]').textContent = error.message;
      scheduleLessonBuildPolling();
    });
  }, 2000);
}

function renderLessonBuild() {
  const lessonId = state.lessonBuild.lessonId;
  const lesson = lessonById(lessonId);
  const build = state.lessonBuild.build;
  const body = $('[data-lesson-build-body]');
  const error = $('[data-lesson-build-error]');
  const start = $('[data-lesson-build-start]');
  $('[data-lesson-build-heading]').textContent = lesson?.title || 'Lesson Build';
  error.textContent = '';

  if (!build) {
    const selected = selectedReferencesForLesson(lessonId);
    const eligible = eligibleLessonReferenceIds(lessonId);
    const count = eligible.filter((referenceId) => selected.has(referenceId)).length;
    body.innerHTML = `<section class="syl-build-offer">
      <p>Serão fixadas <strong>${count} Source Publication${count === 1 ? '' : 's'}</strong> validada${count === 1 ? '' : 's'} para esta aula.</p>
      <p>As escolhas acima só passam a valer quando o build é iniciado. O manifesto preserva as publicações exatas usadas nesta tentativa.</p>
      ${count ? '' : '<p class="syl-form-error" role="alert">Selecione pelo menos uma Source Publication validada.</p>'}
    </section>${graphRevisionMarkup(state.lessonBuild.subjectGraph)}`;
    start.hidden = false;
    start.disabled = state.lessonBuild.busy || count === 0;
    start.textContent = state.lessonBuild.busy ? 'Iniciando…' : 'Iniciar Lesson Build';
    return;
  }

  const status = String(build.status || '').toLowerCase();
  const completed = new Set((build.checkpoints || [])
    .filter((checkpoint) => checkpoint.is_stage_result)
    .map((checkpoint) => checkpoint.stage));
  const families = [...new Set((build.checkpoints || []).map((checkpoint) => checkpoint.family).filter(Boolean))];
  const reviewLabel = build.review?.decision === 'accepted'
    ? 'Aceito'
    : (build.review?.decision === 'rejected' ? 'Rejeitado' : 'Aguardando revisão');
  let actions = '';
  if (status === 'failed') {
    actions = `<div class="syl-build-actions">
      <button class="button button--primary" type="button" data-lesson-build-resume>Retomar do checkpoint</button>
      <button class="button" type="button" data-lesson-build-regenerate>Regenerar desde o início</button>
    </div>`;
  } else if (status === 'succeeded' && !build.review) {
    actions = `<div class="syl-build-actions syl-build-review-actions">
      <button class="button button--primary" type="button" data-lesson-build-accept>Aceitar Lesson</button>
      <button class="button" type="button" data-lesson-build-reject>Rejeitar Lesson</button>
      <button class="button" type="button" data-lesson-build-regenerate>Regenerar desde o início</button>
    </div>`;
  } else if (status === 'succeeded') {
    actions = '<div class="syl-build-actions"><button class="button" type="button" data-lesson-build-regenerate>Regenerar desde o início</button></div>';
  }

  body.innerHTML = `<section class="syl-build-summary">
    <div class="syl-build-summary__heading" role="status" aria-live="polite">
      <span class="syl-build-status is-${esc(status || 'queued')}">${esc(buildStatusLabel(status))}</span>
      <code>${esc(build.id)}</code>
    </div>
    ${build.failure_message ? `<p class="syl-build-failure">${esc(build.failure_message)}</p>` : ''}
    ${status === 'succeeded' ? `<p class="syl-build-review-state">${esc(reviewLabel)}</p>` : ''}
    <ol class="syl-build-stages">${(build.stages || []).map((stage) => `<li class="${completed.has(stage.name) ? 'is-done' : ''}">${completed.has(stage.name) ? '✓' : '○'} ${esc(stage.label)}</li>`).join('')}</ol>
    <details class="syl-build-manifest"><summary>Manifesto congelado</summary><pre>${esc(JSON.stringify(build.manifest || {}, null, 2))}</pre></details>
    ${families.length ? `<section class="syl-build-artifacts"><h3>Artefatos brutos</h3>${families.map((family) => `<div><strong>${esc(String(family).replaceAll('_', ' '))}</strong><ul>${(build.checkpoints || []).filter((checkpoint) => checkpoint.family === family).map((checkpoint) => `<li><a href="/api/lesson-builds/${encodeURIComponent(build.id)}/checkpoints/${encodeURIComponent(checkpoint.id)}" target="_blank" rel="noopener noreferrer">${esc(checkpoint.path)}</a></li>`).join('')}</ul></div>`).join('')}</section>` : ''}
    <p class="syl-build-usage">OpenRouter: ${Number(build.usage?.calls || 0)} chamadas · ${esc(fmtUsd(build.usage?.cost_usd || 0))}</p>
    ${(build.attempts || []).length ? `<details class="syl-build-attempts"><summary>Tentativas</summary><ul>${build.attempts.map((attempt) => `<li>${esc(attempt.stage)} · ${esc(attempt.requested_model || 'modelo desconhecido')} · ${esc(attempt.provider || 'provider desconhecido')} · ${esc(attempt.outcome)}</li>`).join('')}</ul></details>` : ''}
    ${graphRevisionMarkup(build.subject_graph || state.lessonBuild.subjectGraph, build.graph_revision)}
    ${actions}
  </section>`;
  start.hidden = true;
  scheduleLessonBuildPolling();
}

async function openLessonBuild(lessonId, trigger = null) {
  const path = lessonBuildApiPath(lessonId);
  if (!path) return;
  window.clearTimeout(state.lessonBuild.pollingTimer);
  state.lessonBuild = {
    lessonId,
    offer: null,
    build: null,
    subjectGraph: null,
    pollingTimer: null,
    trigger: trigger || document.activeElement,
    busy: true,
  };
  $('[data-lesson-build-heading]').textContent = lessonById(lessonId)?.title || 'Lesson Build';
  $('[data-lesson-build-body]').innerHTML = '<div class="syl-loading"><span></span>Carregando Lesson Build…</div>';
  $('[data-lesson-build-error]').textContent = '';
  $('[data-lesson-build-start]').hidden = true;
  if (!lessonBuildDialog.open) lessonBuildDialog.showModal();
  try {
    const offer = await lessonBuildRequest(`${path}/lesson-build`);
    if (String(state.lessonBuild.lessonId) !== String(lessonId) || !lessonBuildDialog.open) return;
    state.lessonBuild.offer = offer;
    state.lessonBuild.build = buildFromResponse(offer.latest_build);
    state.lessonBuild.subjectGraph = offer.subject_graph || state.lessonBuild.build?.subject_graph || null;
    state.lessonBuild.busy = false;
    renderLessonBuild();
  } catch (error) {
    if (String(state.lessonBuild.lessonId) !== String(lessonId)) return;
    state.lessonBuild.busy = false;
    $('[data-lesson-build-body]').innerHTML = '<div class="syl-build-empty"><strong>Não foi possível abrir o Lesson Build.</strong></div>';
    $('[data-lesson-build-error]').textContent = error.message;
  }
}

async function startLessonBuild() {
  const lessonId = state.lessonBuild.lessonId;
  const path = lessonBuildApiPath(lessonId);
  if (!path || state.lessonBuild.busy) return;
  const eligible = new Set(eligibleLessonReferenceIds(lessonId));
  const selected = [...selectedReferencesForLesson(lessonId)].filter((referenceId) => eligible.has(referenceId));
  if (!selected.length) throw new Error('Selecione pelo menos uma Source Publication validada.');
  state.lessonBuild.busy = true;
  renderLessonBuild();
  try {
    const body = await lessonBuildRequest(`${path}/lesson-builds`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request_key: lessonBuildRequestKey(), reference_ids: selected }),
    });
    state.lessonBuild.build = buildFromResponse(body);
    state.lessonBuild.subjectGraph = state.lessonBuild.build?.subject_graph || state.lessonBuild.subjectGraph;
    state.lessonBuild.busy = false;
    updateLessonBuildProjection(state.lessonBuild.build);
    renderDetail();
    renderLessonBuild();
    announce('Lesson Build colocado na fila.');
  } catch (error) {
    state.lessonBuild.busy = false;
    renderLessonBuild();
    throw error;
  }
}

async function refreshLessonBuild() {
  const buildId = state.lessonBuild.build?.id;
  if (!buildId || !lessonBuildDialog.open) return;
  const body = await lessonBuildRequest(`/api/lesson-builds/${encodeURIComponent(buildId)}`);
  if (!lessonBuildDialog.open || String(state.lessonBuild.build?.id || '') !== String(buildId)) return;
  state.lessonBuild.build = buildFromResponse(body);
  state.lessonBuild.subjectGraph = state.lessonBuild.build?.subject_graph || state.lessonBuild.subjectGraph;
  updateLessonBuildProjection(state.lessonBuild.build);
  renderDetail();
  renderLessonBuild();
}

async function mutateLessonBuild(action, payload = null) {
  const buildId = state.lessonBuild.build?.id;
  if (!buildId || state.lessonBuild.busy) return;
  state.lessonBuild.busy = true;
  const options = { method: 'POST' };
  if (payload) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(payload);
  }
  try {
    const body = await lessonBuildRequest(`/api/lesson-builds/${encodeURIComponent(buildId)}/${action}`, options);
    const nextBuild = buildFromResponse(body);
    if (['resume', 'regenerate'].includes(action) && nextBuild?.id) state.lessonBuild.build = nextBuild;
    else await refreshLessonBuild();
    state.lessonBuild.busy = false;
    updateLessonBuildProjection(state.lessonBuild.build);
    renderDetail();
    renderLessonBuild();
  } catch (error) {
    state.lessonBuild.busy = false;
    throw error;
  }
}

function closeLessonBuild() {
  const trigger = state.lessonBuild.trigger;
  window.clearTimeout(state.lessonBuild.pollingTimer);
  if (lessonBuildDialog.open) lessonBuildDialog.close();
  state.lessonBuild = {
    lessonId: null,
    offer: null,
    build: null,
    subjectGraph: null,
    pollingTimer: null,
    trigger: null,
    busy: false,
  };
  if (trigger?.isConnected) trigger.focus();
}

document.querySelector('main').addEventListener('click', (event) => {
  if (event.target.closest('[data-new-syllabus]')) { openUpload('new'); return; }
  if (event.target.closest('[data-new-version]')) { openUpload('version'); return; }
  const versions = event.target.closest('[data-open-versions]');
  if (versions) { openVersionDialog('history', versions); return; }
  if (event.target.closest('[data-edit-syllabus]')) { startEditing(); return; }
  const editLesson = event.target.closest('[data-edit-lesson]');
  if (editLesson) { startEditing(editLesson.dataset.editLesson); return; }
  if (event.target.closest('[data-cancel-edit]')) { cancelEditing(); return; }
  const saveSyllabus = event.target.closest('[data-save-syllabus]');
  if (saveSyllabus) { openVersionDialog('save', saveSyllabus); return; }
  const addSource = event.target.closest('[data-add-source]');
  if (addSource) { addEditorSource(Number(addSource.dataset.addSource)); return; }
  const removeSource = event.target.closest('[data-remove-source]');
  if (removeSource) { removeEditorSource(removeSource.dataset.removeSource); return; }
  const hideSource = event.target.closest('[data-toggle-source-hidden]');
  if (hideSource) { toggleEditorSourceHidden(hideSource.dataset.toggleSourceHidden); return; }
  const hideLesson = event.target.closest('[data-toggle-lesson-hidden]');
  if (hideLesson) { toggleEditorLessonHidden(hideLesson.dataset.toggleLessonHidden); return; }
  const sourceUp = event.target.closest('[data-move-source-up]');
  if (sourceUp) { moveEditorSource(sourceUp.dataset.moveSourceUp, -1); return; }
  const sourceDown = event.target.closest('[data-move-source-down]');
  if (sourceDown) { moveEditorSource(sourceDown.dataset.moveSourceDown, 1); return; }
  const lessonUp = event.target.closest('[data-move-lesson-up]');
  if (lessonUp) { moveEditorLesson(Number(lessonUp.dataset.moveLessonUp), -1); return; }
  const lessonDown = event.target.closest('[data-move-lesson-down]');
  if (lessonDown) { moveEditorLesson(Number(lessonDown.dataset.moveLessonDown), 1); return; }
  const complexity = event.target.closest('[data-set-source-complexity]');
  if (complexity) {
    const found = sourceByReferenceId(complexity.dataset.referenceId);
    const selected = complexity.dataset.setSourceComplexity;
    updateSourceReview(complexity.dataset.referenceId, {
      complexity: found?.source?.review?.complexity === selected ? null : selected,
    });
    return;
  }
  const validated = event.target.closest('[data-toggle-source-validated]');
  if (validated) {
    const found = sourceByReferenceId(validated.dataset.referenceId);
    updateSourceReview(validated.dataset.referenceId, {
      validated: !Boolean(found?.source?.review?.validated),
    });
    return;
  }
  const build = event.target.closest('[data-open-lesson-build]');
  if (build) { openLessonBuild(build.dataset.openLessonBuild, build); return; }
  const expanded = event.target.closest('[data-toggle-lesson-expanded]');
  if (expanded) { toggleLessonExpanded(expanded.dataset.lessonId); return; }
  const copyCode = event.target.closest('[data-copy-book-code]');
  if (copyCode) { copyBookCode(copyCode.dataset.copyBookCode); return; }
  const bookScope = event.target.closest('[data-edit-book-scope]');
  if (bookScope) { editBookScope(bookScope.dataset.editBookScope); return; }
  const queue = event.target.closest('[data-queue-source]');
  if (queue) { queueSource(queue.dataset.queueSource); return; }
  const videoPreflight = event.target.closest('[data-video-preflight]');
  if (videoPreflight) { preflightVideo(videoPreflight.dataset.videoPreflight); return; }
  const authorize = event.target.closest('[data-authorize-video]');
  if (authorize) { authorizeVideo(authorize.dataset.authorizeVideo); return; }
  const manual = event.target.closest('[data-manual-source]');
  if (manual) { openManualUpload(manual.dataset.manualSource, manual.dataset.manualTitle); return; }
  const markdown = event.target.closest('[data-markdown-source]');
  if (markdown) { openMarkdown(markdown.dataset.markdownSource, markdown.dataset.markdownTitle); return; }
  if (event.target.closest('[data-retry]')) {
    if (routeId) loadDetail({ versionId: state.selectedVersionId }); else loadList();
  }
});

document.querySelector('[data-admin-shell]')?.addEventListener('click', (event) => {
  const saveSyllabus = event.target.closest('[data-save-syllabus]');
  if (saveSyllabus) openVersionDialog('save', saveSyllabus);
});

document.querySelector('main').addEventListener('input', (event) => {
  if (updateEditorField(event.target)) {
    autosizeEditorTextarea(event.target);
    return;
  }
  if (event.target.matches('[data-filter-query]')) {
    state.filters.query = event.target.value;
    renderDetail();
    $('[data-filter-query]')?.focus();
  }
});

document.querySelector('main').addEventListener('change', (event) => {
  const editedField = updateEditorField(event.target);
  if (editedField === 'media_type') {
    renderDetail();
  } else if (editedField) {
    return;
  } else if (event.target.matches('[data-build-source]')) {
    const lessonId = event.target.dataset.lessonId;
    const referenceId = String(event.target.dataset.referenceId || '');
    const selected = selectedReferencesForLesson(lessonId);
    if (event.target.checked) selected.add(referenceId);
    else selected.delete(referenceId);
    renderDetail();
  } else if (event.target.matches('[data-filter-subject]')) {
    state.filters.subject = event.target.value;
    renderDetail();
  } else if (event.target.matches('[data-filter-media]')) {
    state.filters.mediaType = event.target.value;
    renderDetail();
  } else if (event.target.matches('[data-filter-validation]')) {
    state.filters.validation = event.target.value;
    renderDetail();
  } else if (event.target.matches('[data-filter-complexity]')) {
    state.filters.complexity = event.target.value;
    renderDetail();
  } else if (event.target.matches('[data-show-hidden]')) {
    state.filters.showHidden = event.target.checked;
    renderDetail();
  }
});

uploadForm.addEventListener('submit', submitUpload);
uploadForm.elements.name.addEventListener('input', () => {
  $('[data-upload-error]').textContent = '';
  scheduleGraphProposal({ resetManual: true });
});
uploadForm.elements.institution_id.addEventListener('change', () => {
  $('[data-upload-error]').textContent = '';
  scheduleGraphProposal({ resetManual: true });
});
uploadDialog.addEventListener('click', (event) => {
  if (event.target.closest('[data-dialog-close]')) closeUpload();
  else if (event.target === uploadDialog) closeUpload();
});
$('[data-upload-file]').addEventListener('change', (event) => {
  $('[data-file-name]').textContent = event.target.files?.[0]?.name || 'Escolher arquivo .xlsx';
});

versionForm.addEventListener('submit', (event) => {
  event.preventDefault();
  saveEditor();
});
versionDialog.addEventListener('input', (event) => {
  if (!event.target.matches('[data-version-note]')) return;
  state.editor.note = event.target.value;
  const count = $('[data-version-note-count]', versionDialog);
  if (count) count.textContent = `${[...state.editor.note].length}/500`;
  const confirm = $('[data-confirm-version]', versionDialog);
  if (confirm) confirm.disabled = state.editor.busy || !state.editor.note.trim();
  const error = $('[data-version-error]', versionDialog);
  if (error) error.textContent = '';
});
versionDialog.addEventListener('click', (event) => {
  const selected = event.target.closest('[data-select-version]');
  if (selected) { selectVersion(selected.dataset.selectVersion); return; }
  if (event.target.closest('[data-version-close]') || event.target === versionDialog) closeVersionDialog();
});
versionDialog.addEventListener('cancel', (event) => {
  event.preventDefault();
  closeVersionDialog();
});

markdownDialog.addEventListener('click', (event) => {
  if (event.target.closest('[data-markdown-close]') || event.target === markdownDialog || event.target.closest('[data-retry]')) {
    state.markdownSourceId = null;
    markdownDialog.close();
  }
});

lessonBuildDialog.addEventListener('click', async (event) => {
  if (event.target.closest('[data-lesson-build-close]') || event.target === lessonBuildDialog) {
    closeLessonBuild();
    return;
  }
  try {
    const packageButton = event.target.closest('[data-companion-package]');
    if (packageButton) {
      await downloadCompanionPackage(packageButton.dataset.companionPackage);
      return;
    }
    if (event.target.closest('[data-lesson-build-start]')) {
      await startLessonBuild();
      return;
    }
    if (event.target.closest('[data-lesson-build-resume]')) {
      await mutateLessonBuild('resume');
      announce('Lesson Build retomado do checkpoint.');
      return;
    }
    if (event.target.closest('[data-lesson-build-accept]')) {
      await mutateLessonBuild('accept', { actor: 'founder' });
      announce('Lesson aceita e nova Graph Revision criada.');
      return;
    }
    if (event.target.closest('[data-lesson-build-reject]')) {
      await mutateLessonBuild('reject', { actor: 'founder' });
      announce('Lesson rejeitada; o grafo aceito não mudou.');
      return;
    }
    if (event.target.closest('[data-lesson-build-regenerate]')) {
      await mutateLessonBuild('regenerate', { request_key: lessonBuildRequestKey() });
      announce('Nova tentativa de Lesson Build colocada na fila.');
    }
  } catch (error) {
    $('[data-lesson-build-error]').textContent = error.message;
  }
});
lessonBuildDialog.addEventListener('cancel', (event) => {
  event.preventDefault();
  closeLessonBuild();
});

manualForm.addEventListener('submit', submitManualUpload);
manualDialog.addEventListener('click', (event) => {
  const kind = event.target.closest('[data-manual-kind]');
  if (kind) { chooseManualKind(kind.dataset.manualKind); return; }
  const up = event.target.closest('[data-manual-up]');
  if (up) { moveManualItem(Number(up.dataset.manualUp), -1); return; }
  const down = event.target.closest('[data-manual-down]');
  if (down) { moveManualItem(Number(down.dataset.manualDown), 1); return; }
  const remove = event.target.closest('[data-manual-remove]');
  if (remove) { removeManualItem(Number(remove.dataset.manualRemove)); return; }
  if (event.target.closest('[data-manual-close]') || event.target === manualDialog) closeManualUpload();
});
manualDialog.addEventListener('cancel', (event) => {
  event.preventDefault();
  closeManualUpload();
});
$('[data-manual-files]').addEventListener('change', (event) => addManualFiles(event.target.files));

window.addEventListener('beforeunload', (event) => {
  window.clearTimeout(state.pollingTimer);
  window.clearTimeout(state.lessonBuild.pollingTimer);
  revokeManualItems();
  if (state.editor.active && state.editor.dirty) {
    event.preventDefault();
    event.returnValue = '';
  }
});

if (routeId && initialReconciliationId) {
  loadReconciliation(initialReconciliationId);
} else if (routeId) {
  announceStoredIntakeNote(routeId);
  loadDetail();
} else {
  loadList();
}
