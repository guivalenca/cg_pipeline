/* Sources — list of every source with its ingestion spine, plus a per-source
   detail view (?id=...). Hydrates from GET /api/sources and /api/sources/{id}. */

const $ = (selector, root = document) => root.querySelector(selector);

const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

/* Muted categorical palette (Companion group-palette style). Media type is
   data, so it never uses brand teal. */
const MEDIA_PALETTE = [
  { token: 'violet', accent: '#5b21b6', dark: '#a78bfa' },
  { token: 'wine', accent: '#8a3f5d', dark: '#f0a6bf' },
  { token: 'green', accent: '#047857', dark: '#34d399' },
  { token: 'blue', accent: '#075985', dark: '#38bdf8' },
  { token: 'amber', accent: '#b45309', dark: '#fbbf24' },
];

function mediaPalette(mediaType) {
  const key = String(mediaType ?? '').toLowerCase();
  if (!key) return { accent: '#64748b', dark: '#94a3b8' };
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  return MEDIA_PALETTE[hash % MEDIA_PALETTE.length];
}

function mediaStyle(mediaType) {
  const palette = mediaPalette(mediaType);
  return `--media-accent:${palette.accent};--media-accent-dark:${palette.dark}`;
}

/* Plain language: "acquired" = we hold extracted markdown for this source. */
const STATUS_LABEL = {
  unlinked: 'Unlinked',
  pending: 'Not acquired',
  ingested: 'Acquired',
  failed: 'Acquisition failed',
  'skipped by founder': 'Skipped',
};

/* Plain wording for every recorded acquisition gate, kept in step with
   universe/acquisition/gates.py — the taxonomy is defined there, not here. */
const GATE_DESCRIPTIONS = {
  auth_wall_detected: 'The source needs a signed-in account before it can be read.',
  bot_wall_detected: 'The source blocked the automated reader.',
  error_page_detected: 'The source returned an error page instead of its content.',
  http_status_4xx: 'The source rejected the request or could not be found.',
  http_status_5xx: 'The source service failed while we were fetching it.',
  missing_credentials: 'Firecrawl credentials are not configured.',
  unsupported_media_kind: 'This kind of source does not have a fetcher yet.',
  missing_concrete_scope: 'The book needs a chapter, page range, or unit to fetch.',
  manual_access_required: 'A person must open this source and provide the content.',
  empty_content: 'The fetch completed but returned no readable content.',
  fetch_failed: 'The source could not be fetched after the available attempts.',
};

const GATE_HINTS = {
  missing_credentials: 'Put the Firecrawl key in the .env file at the repo root as FIRECRAWL_API_KEY, then run acquisition again.',
  manual_access_required: 'Nothing automatic will fix this one — the content has to come from a person.',
};

const STAGE_STATUS_LABEL = {
  done: 'done',
  partial: 'partial',
  pending: 'pending',
  failed: 'failed',
};

/* Canonical pipeline order; stages the API returns that we do not know are
   appended after these, in API order. */
const STAGE_ORDER = [
  'passage-cuts',
  'passage-triage',
  'task-generation',
  'task-granularity',
  'task-revision',
  'task-triage',
  'task-substance',
  'kc-statement',
  'task-modality',
  'task-knowledge',
  'task-embedding',
  'kc-judge',
];

function orderStages(names) {
  const known = STAGE_ORDER.filter((name) => names.includes(name));
  const unknown = names.filter((name) => !STAGE_ORDER.includes(name));
  return [...known, ...unknown];
}

const state = {
  sources: [],
  corpusFilter: new URLSearchParams(window.location.search).get('corpus') || '',
  mediaFilter: '',
  attentionOnly: false,
};

function corpusKey(source) {
  return source.corpus?.id == null ? 'test' : source.corpus.id;
}

function setStatus(message) {
  const host = $('[data-status]');
  if (host) host.textContent = message;
}

function setTitle(suffix) {
  document.title = suffix ? `${suffix} · Sources · Concept Universe` : 'Sources · Concept Universe';
}

async function fetchJSON(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body?.detail || `Request failed (${response.status}).`);
  }
  return response.json();
}

function statusPill(sourceStatus) {
  const key = STATUS_LABEL[sourceStatus] ? sourceStatus : 'unlinked';
  const token = key.replace(/\s+/g, '-');
  return `<span class="sources-status sources-status--${esc(token)}">${esc(STATUS_LABEL[key])}</span>`;
}

function needsAttention(source) {
  if (source.source_status === 'failed' || source.source_status === 'pending') return true;
  return Object.values(source.stages || {}).some((stage) => stage.status === 'failed');
}

/* List view --------------------------------------------------------------- */

function stageStripTemplate(stages) {
  const names = orderStages(Object.keys(stages || {}));
  if (!names.length) {
    return '<span class="sources-stage-strip" aria-label="No pipeline stages yet"></span>';
  }
  const cells = names.map((name) => {
    const stage = stages[name];
    const status = STAGE_STATUS_LABEL[stage.status] ? stage.status : 'pending';
    const superseded = stage.generation && stage.generation !== 'current';
    const title = `${name} — ${STAGE_STATUS_LABEL[status]}${superseded ? ' (superseded generation — re-run to refresh)' : ''}`;
    return `<span class="sources-stage-strip__cell sources-stage-strip__cell--${esc(status)}${superseded ? ' sources-stage-strip__cell--superseded' : ''}" title="${esc(title)}"></span>`;
  }).join('');
  return `<span class="sources-stage-strip" role="img" aria-label="Pipeline: ${esc(names.map((name) => `${name} ${stages[name].status}`).join(', '))}">${cells}</span>`;
}

function rosterRowTemplate(source) {
  return `
    <button type="button" class="sources-roster__row" style="${mediaStyle(source.media_type)}" data-source-row="${esc(source.id)}">
      <span class="sources-source">
        <span class="sources-source__title">${esc(source.title || 'Untitled source')}</span>
        <span class="sources-source__url">${esc(source.url || '')}</span>
      </span>
      <span class="sources-media">${esc(source.media_type || 'unknown')}</span>
      ${statusPill(source.source_status)}
      ${stageStripTemplate(source.stages)}
    </button>
  `;
}

function visibleSources() {
  return state.sources.filter((source) => {
    if (state.corpusFilter && corpusKey(source) !== state.corpusFilter) return false;
    if (state.mediaFilter && String(source.media_type || '') !== state.mediaFilter) return false;
    if (state.attentionOnly && !needsAttention(source)) return false;
    return true;
  });
}

function renderCorpusTabs() {
  const host = $('[data-corpus-tabs]');
  if (!host) return;
  const corpora = new Map();
  for (const source of state.sources) {
    const key = corpusKey(source);
    if (!corpora.has(key)) {
      corpora.set(key, {
        label: key === 'test' ? 'Test corpus' : (source.corpus?.title || key),
        count: 0,
      });
    }
    corpora.get(key).count += 1;
  }
  if (state.corpusFilter && !corpora.has(state.corpusFilter)) state.corpusFilter = '';
  const tab = (key, label, count) => `
    <button type="button" role="tab" class="sources-corpus-tab${state.corpusFilter === key ? ' is-active' : ''}"
      aria-selected="${state.corpusFilter === key}" data-corpus-tab="${esc(key)}">
      ${esc(label)}<span class="sources-corpus-tab__count">${esc(String(count))}</span>
    </button>`;
  host.innerHTML = tab('', 'All', state.sources.length)
    + [...corpora.entries()].map(([key, entry]) => tab(key, entry.label, entry.count)).join('');
  host.querySelectorAll('[data-corpus-tab]').forEach((button) => {
    button.addEventListener('click', () => {
      state.corpusFilter = button.dataset.corpusTab;
      const url = new URL(window.location.href);
      if (state.corpusFilter) url.searchParams.set('corpus', state.corpusFilter);
      else url.searchParams.delete('corpus');
      window.history.replaceState(null, '', url);
      renderCorpusTabs();
      renderRoster();
    });
  });
}

function renderRoster() {
  const host = $('[data-roster]');
  if (!host) return;
  const sources = visibleSources();

  const summary = $('[data-filter-summary]');
  if (summary) {
    summary.textContent = sources.length === state.sources.length
      ? ''
      : `${sources.length} of ${state.sources.length} sources`;
  }

  if (!state.sources.length) {
    host.innerHTML = '<p class="sources-empty">No sources yet — upload a syllabus and its linked materials will appear here.</p>';
    return;
  }
  if (!sources.length) {
    host.innerHTML = '<p class="sources-empty">No sources match the current filters.</p>';
    return;
  }

  host.innerHTML = `
    <div class="sources-roster">
      <div class="sources-roster__header" aria-hidden="true">
        <span>Source</span>
        <span>Media</span>
        <span>Status</span>
        <span>Pipeline</span>
      </div>
      ${sources.map(rosterRowTemplate).join('')}
    </div>
  `;

  host.querySelectorAll('[data-source-row]').forEach((row) => {
    row.addEventListener('click', () => {
      window.location.href = `/sources?id=${encodeURIComponent(row.dataset.sourceRow)}`;
    });
  });
}

function renderMediaFilter() {
  const select = $('[data-media-filter]');
  if (!select) return;
  const types = [...new Set(state.sources.map((source) => String(source.media_type || '')).filter(Boolean))].sort();
  select.innerHTML = '<option value="">All media types</option>'
    + types.map((type) => `<option value="${esc(type)}">${esc(type)}</option>`).join('');
  select.value = state.mediaFilter;
}

async function bootList() {
  const roster = $('[data-roster]');
  setStatus('Loading sources…');
  if (roster) roster.innerHTML = '<p class="sources-empty">Loading sources…</p>';
  try {
    const payload = await fetchJSON('/api/sources');
    state.sources = payload.sources || [];
    const count = $('[data-title-count]');
    if (count) count.textContent = String(state.sources.length);
    renderCorpusTabs();
    renderMediaFilter();
    renderRoster();
    setStatus(`${state.sources.length} source${state.sources.length === 1 ? '' : 's'} loaded.`);
  } catch (error) {
    if (roster) roster.innerHTML = `<p class="sources-error">Could not load sources: ${esc(error.message)}</p>`;
    setStatus('Failed to load sources.');
  }

  $('[data-media-filter]')?.addEventListener('change', (event) => {
    state.mediaFilter = event.target.value;
    renderRoster();
  });
  $('[data-attention-filter]')?.addEventListener('change', (event) => {
    state.attentionOnly = event.target.checked;
    renderRoster();
  });
}

/* Detail view ------------------------------------------------------------- */

function panelTemplate({ title, count, body, full = false }) {
  return `
    <section class="sources-panel${full ? ' sources-panel--full' : ''}">
      <header class="sources-panel__heading">
        <h2>${esc(title)}</h2>
        <span class="sources-panel__count">${esc(String(count))}</span>
      </header>
      ${body}
    </section>
  `;
}

function formatWhen(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function snapshotsBody(snapshots) {
  if (!snapshots.length) {
    return '<p class="sources-empty">No snapshots yet — acquisition has not run.</p>';
  }
  return `
    <div class="sources-fact-list">
      ${snapshots.map((snapshot) => `
        <div class="sources-fact-row">
          <span class="sources-fact-row__primary"><span class="sources-status sources-status--${snapshot.status === 'ok' ? 'ingested' : 'failed'}">${esc(snapshot.status === 'ok' ? 'OK' : 'Failed')}</span></span>
          <span class="sources-fact-row__meta">${esc(formatWhen(snapshot.captured_at))}</span>
          ${snapshot.failure_note ? `<p class="sources-fact-row__note">${esc(snapshot.failure_note)}</p>` : ''}
        </div>
      `).join('')}
    </div>
  `;
}

function artifactsBody(artifacts) {
  if (!artifacts.length) {
    return '<p class="sources-empty">No artifacts yet — nothing has been extracted from this source.</p>';
  }
  return `
    <div class="sources-fact-list">
      ${artifacts.map((artifact) => `
        <div class="sources-fact-row">
          <span class="sources-fact-row__primary">${esc(artifact.kind || 'artifact')}</span>
          <span class="sources-fact-row__meta">${esc(artifact.tool || '—')} · ${esc(formatChars(artifact.chars))}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function formatChars(chars) {
  if (chars == null) return '—';
  const value = Number(chars);
  if (!Number.isFinite(value)) return String(chars);
  if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k chars`;
  return `${value} chars`;
}

function stagesBody(stages) {
  if (!stages.length) {
    return '<p class="sources-empty">No stage activity yet — the pipeline has not touched this source.</p>';
  }
  const byName = new Map(stages.map((stage) => [stage.stage, stage]));
  const names = orderStages([...byName.keys()]);
  return `
    <ul class="sources-stage-list">
      ${names.map((name) => {
        const stage = byName.get(name);
        const status = STAGE_STATUS_LABEL[stage.status] ? stage.status : 'pending';
        const counts = stage.total != null ? `${stage.done ?? 0}/${stage.total}` : '';
        const superseded = stage.generation && stage.generation !== 'current';
        const run = stage.run_id
          ? `<span class="sources-stage-list__run">${esc(stage.run_id)}${superseded ? ' <em class="sources-stage-list__superseded">superseded — re-run to refresh</em>' : ''}</span>`
          : '<span class="sources-stage-list__run" aria-hidden="true"></span>';
        return `
          <li>
            <span class="sources-stage-strip__cell sources-stage-strip__cell--${esc(status)}" title="${esc(STAGE_STATUS_LABEL[status])}"></span>
            <span class="sources-stage-list__name">${esc(name)}</span>
            <span class="sources-stage-list__counts">${esc(counts)}</span>
            ${run}
          </li>
        `;
      }).join('')}
    </ul>
  `;
}

function taskTemplate(task, index) {
  const body = String(task.body ?? '');
  const truncatable = body.length > 180;
  return `
    <li class="sources-task">
      <p class="sources-task__statement">${esc(task.statement || task.body || 'Untitled task')}</p>
      ${body ? `
        <p class="sources-task__body" id="task-body-${index}" data-truncated="${truncatable}">${esc(body)}</p>
        ${truncatable ? `<button type="button" class="sources-task__expand" data-expand="task-body-${index}" aria-expanded="false" aria-controls="task-body-${index}">Show full task</button>` : ''}
      ` : ''}
      <span class="sources-task__meta">
        ${task.modality ? `<span class="sources-task__badge">${esc(task.modality)}</span>` : ''}
        ${task.knowledge ? `<span class="sources-task__badge">${esc(task.knowledge)}</span>` : ''}
        ${task.group_id ? `<a class="sources-task__group" href="/universe" title="Committed knowledge component">${esc(task.group_id)}</a>` : ''}
      </span>
    </li>
  `;
}

function tasksBody(tasks) {
  if (!tasks.length) {
    return '<p class="sources-empty">No surviving tasks yet — task generation and triage have not produced anything for this source.</p>';
  }
  return `<ul class="sources-task-list">${tasks.map(taskTemplate).join('')}</ul>`;
}

/* Pipeline actions — what would run next for this source, and the button
   that fires it. Hydrates from GET /api/sources/{id}/next-step. */

async function postJSON(url, payload) {
  const init = { method: 'POST', headers: { Accept: 'application/json' } };
  if (payload !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(payload);
  }
  const response = await fetch(url, init);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status}).`);
  return body;
}

function pipelineActionsBody(payload) {
  const running = payload.running;
  const step = payload.next || {};
  if (running) {
    const label = DESCRIPTIONS_FALLBACK(step, running.stage);
    return `
      <p class="sources-pipeline__now">Running now: ${esc(label)}.</p>
      <p class="sources-pipeline__hint">Progress lands in the stage list below as answers come back.</p>
      <button type="button" class="sources-pipeline__button sources-pipeline__button--quiet" data-step-refresh>Refresh</button>
    `;
  }
  if (!step.stage) {
    return '<p class="sources-pipeline__done">Every stage is complete for this source.</p>';
  }
  const retry = step.stage_status === 'failed' || step.stage_status === 'partial'
    ? ' (the last attempt did not finish — running again picks it up)'
    : '';
  const model = step.model ? ` — ${esc(step.model)}` : '';
  if (!step.runnable) {
    return `
      <p class="sources-pipeline__next sources-pipeline__next--blocked">Next: ${esc(step.description)}${model}</p>
      <p class="sources-pipeline__reason">Not runnable from here yet — ${esc(step.reason || 'no reason recorded')}.</p>
    `;
  }
  const spend = step.spends_model_calls
    ? `This will spend model calls${step.model ? ` on ${esc(step.model)}` : ''}.`
    : 'This runs locally and spends no model calls.';
  return `
    <p class="sources-pipeline__next">Next: ${esc(step.description)}${model}${esc(retry)}</p>
    <div class="sources-pipeline__actions" data-step-arm>
      <button type="button" class="sources-pipeline__button" data-step-run>Run this step</button>
    </div>
    <div class="sources-pipeline__actions" data-step-confirm hidden>
      <span class="sources-pipeline__spend">${spend}</span>
      <button type="button" class="sources-pipeline__button" data-step-confirm-run>Run it</button>
      <button type="button" class="sources-pipeline__button sources-pipeline__button--quiet" data-step-cancel>Cancel</button>
    </div>
    <p class="sources-pipeline__error" data-step-error hidden></p>
  `;
}

function DESCRIPTIONS_FALLBACK(step, stage) {
  if (step.stage === stage && step.description) return step.description;
  return stage || 'the current step';
}

async function loadPipelineActions(id) {
  const host = $('[data-pipeline-actions]');
  if (!host) return;
  host.innerHTML = '<p class="sources-empty">Checking what runs next…</p>';
  let payload;
  try {
    payload = await fetchJSON(`/api/sources/${encodeURIComponent(id)}/next-step`);
  } catch (error) {
    host.innerHTML = `<p class="sources-error">Could not work out the next step: ${esc(error.message)}</p>`;
    return;
  }
  host.innerHTML = pipelineActionsBody(payload);

  $('[data-step-refresh]', host)?.addEventListener('click', () => bootDetail(id));
  $('[data-step-run]', host)?.addEventListener('click', () => {
    $('[data-step-arm]', host).hidden = true;
    $('[data-step-confirm]', host).hidden = false;
  });
  $('[data-step-cancel]', host)?.addEventListener('click', () => {
    $('[data-step-arm]', host).hidden = false;
    $('[data-step-confirm]', host).hidden = true;
  });
  $('[data-step-confirm-run]', host)?.addEventListener('click', async () => {
    const errorHost = $('[data-step-error]', host);
    errorHost.hidden = true;
    try {
      await postJSON(`/api/sources/${encodeURIComponent(id)}/run-next-step`);
      await loadPipelineActions(id);
    } catch (error) {
      errorHost.textContent = error.message;
      errorHost.hidden = false;
    }
  });
}

/* Acquisition — why this source still has no material, in plain words. Shown
   only while nothing has been acquired; launching stays with the Run button
   under Pipeline actions. */

function latestAttempt(snapshots) {
  // The API returns snapshots oldest first, so the newest attempt is last.
  return snapshots.length ? snapshots[snapshots.length - 1] : null;
}

/* Failure notes carry the bare gate code today; older backfilled snapshots
   wrote "failed_gate: <code>" and sometimes listed several codes. Read the
   first gate we have wording for, and keep the raw note for the panel. */
function gateCode(failureNote) {
  const text = String(failureNote ?? '').trim();
  if (!text || GATE_DESCRIPTIONS[text]) return text || null;
  const listed = text.split(':').pop().split(',').map((part) => part.trim()).filter(Boolean);
  return listed.find((part) => GATE_DESCRIPTIONS[part]) || text;
}

function acquisitionPanel(source) {
  const snapshots = source.snapshots || [];
  if (snapshots.some((snapshot) => snapshot.status === 'ok')) return '';
  const latest = latestAttempt(snapshots);
  const code = latest && latest.status !== 'ok' ? gateCode(latest.failure_note) : null;
  const scopeOverride = typeof source.scope_override === 'string' && source.scope_override.trim()
    ? source.scope_override.trim()
    : null;

  const parts = [];
  if (source.source_status === 'skipped by founder') {
    parts.push('<p class="sources-acq__state">You skipped this source. It stays in the syllabus and nothing will be acquired for it.</p>');
  }
  if (!latest) {
    parts.push('<p class="sources-acq__state">Acquisition has never been attempted for this source.</p>');
  } else {
    const when = formatWhen(latest.created_at || latest.captured_at);
    parts.push(`<p class="sources-acq__state">The last attempt failed on ${esc(when)}.</p>`);
    parts.push(`<p class="sources-acq__reason">${esc(GATE_DESCRIPTIONS[code] || 'The source could not be acquired, and no reason was recorded.')}</p>`);
    if (GATE_HINTS[code]) {
      parts.push(`<p class="sources-acq__hint">${esc(GATE_HINTS[code])}</p>`);
    }
    const rawNote = String(latest.failure_note ?? '').trim();
    if (rawNote && rawNote !== code) {
      parts.push(`<p class="sources-acq__hint">Recorded on the snapshot: <code>${esc(rawNote)}</code></p>`);
    }
  }

  if (scopeOverride) {
    parts.push(`<p class="sources-acq__scope">Book scope you set: <strong>${esc(scopeOverride)}</strong></p>`);
  } else if (code === 'missing_concrete_scope') {
    parts.push(`
      <form class="sources-acq__form" data-scope-form>
        <label class="sources-acq__label" for="acq-scope">Which chapters, pages, or units should be fetched?</label>
        <div class="sources-acq__row">
          <input class="sources-acq__input" id="acq-scope" data-scope-input type="text"
            placeholder="chapter 3, pages 40–58" autocomplete="off">
          <button type="submit" class="sources-pipeline__button">Save scope</button>
        </div>
      </form>
      <p class="sources-acq__feedback" data-scope-feedback hidden></p>`);
  }

  // Re-running only helps where the blocker can change. A source that needs a
  // person, or a media kind with no fetcher, will fail exactly the same way.
  const retryPointless = code === 'manual_access_required' || code === 'unsupported_media_kind';
  if (latest && !retryPointless && source.source_status !== 'skipped by founder') {
    parts.push('<p class="sources-acq__hint">The Run button under Pipeline actions below starts another attempt.</p>');
  }

  return `
    <section class="sources-panel sources-panel--full sources-acq">
      <header class="sources-panel__heading">
        <h2>Acquisition</h2>
      </header>
      ${parts.join('')}
    </section>
  `;
}

function wireAcquisitionPanel(id, host) {
  const form = $('[data-scope-form]', host);
  if (!form) return;
  const feedback = $('[data-scope-feedback]', host);
  const say = (message, tone) => {
    feedback.textContent = message;
    feedback.hidden = !message;
    feedback.classList.toggle('sources-acq__feedback--error', tone === 'error');
  };
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = $('[data-scope-input]', host);
    const value = input.value.trim();
    if (!value) {
      say('Write the chapters or pages first.', 'error');
      input.focus();
      return;
    }
    try {
      await postJSON(`/api/sources/${encodeURIComponent(id)}/scope-override`, { value });
      say(`Scope recorded: ${value}. Run acquisition again to use it.`);
    } catch (error) {
      say(`Could not save the scope: ${error.message}`, 'error');
    }
  });
}

function detailTemplate(source) {
  const snapshots = source.snapshots || [];
  const artifacts = source.artifacts || [];
  const stages = source.stages || [];
  const tasks = source.tasks || [];
  const rawIdentity = source.identity;
  const identity = typeof rawIdentity === 'string'
    ? rawIdentity
    : String(rawIdentity?.url || rawIdentity?.canonical_url || '');
  const isLink = /^https?:\/\//i.test(identity);
  return `
    <a class="sources-detail-back" href="/sources">&larr; All sources</a>
    <header class="sources-detail-header" style="${mediaStyle(source.media_type)}">
      <h1>${esc(source.title || 'Untitled source')}</h1>
      <div class="sources-detail-header__meta">
        <span class="sources-media">${esc(source.media_type || 'unknown')}</span>
        ${statusPill(source.source_status)}
        ${identity ? (isLink
          ? `<a class="sources-detail-header__link" href="${esc(identity)}" target="_blank" rel="noopener">${esc(identity)}</a>`
          : `<span class="sources-detail-header__link">${esc(identity)}</span>`) : ''}
      </div>
    </header>
    ${acquisitionPanel(source)}
    <section class="sources-panel sources-panel--full sources-pipeline">
      <header class="sources-panel__heading">
        <h2>Pipeline actions</h2>
      </header>
      <div data-pipeline-actions></div>
    </section>
    <div class="sources-detail-grid">
      ${panelTemplate({ title: 'Snapshots', count: snapshots.length, body: snapshotsBody(snapshots) })}
      ${panelTemplate({ title: 'Artifacts', count: artifacts.length, body: artifactsBody(artifacts) })}
      ${panelTemplate({ title: 'Stage progress', count: stages.length, body: stagesBody(stages), full: true })}
      ${panelTemplate({ title: 'Tasks', count: tasks.length, body: tasksBody(tasks), full: true })}
    </div>
  `;
}

async function bootDetail(id) {
  const host = $('[data-detail-view]');
  const list = $('[data-list-view]');
  if (list) list.hidden = true;
  if (host) {
    host.hidden = false;
    host.innerHTML = '<a class="sources-detail-back" href="/sources">&larr; All sources</a><p class="sources-empty">Loading source…</p>';
  }
  setStatus('Loading source…');
  try {
    const source = await fetchJSON(`/api/sources/${encodeURIComponent(id)}`);
    setTitle(source.title || id);
    if (host) host.innerHTML = detailTemplate(source);
    setStatus(`Source ${source.title || id} loaded.`);
    if (host) wireAcquisitionPanel(id, host);
    loadPipelineActions(id);

    host?.querySelectorAll('[data-expand]').forEach((button) => {
      button.addEventListener('click', () => {
        const target = document.getElementById(button.dataset.expand);
        if (!target) return;
        const expanded = target.dataset.truncated !== 'true';
        target.dataset.truncated = expanded ? 'true' : 'false';
        button.setAttribute('aria-expanded', String(!expanded));
        button.textContent = expanded ? 'Show full task' : 'Show less';
      });
    });
  } catch (error) {
    if (host) {
      host.innerHTML = `
        <a class="sources-detail-back" href="/sources">&larr; All sources</a>
        <p class="sources-error">Could not load this source: ${esc(error.message)}</p>
      `;
    }
    setStatus('Failed to load source.');
  }
}

/* Boot -------------------------------------------------------------------- */

const id = new URLSearchParams(window.location.search).get('id');
if (id) {
  bootDetail(id);
} else {
  bootList();
}
