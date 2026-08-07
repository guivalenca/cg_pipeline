import './shell.js?v=2';

const $ = (selector, root = document) => root.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

// Pipeline order, so the stage groups read as the pipeline reads.
const STAGE_ORDER = [
  'passage-cuts', 'passage-triage', 'task-generation', 'task-granularity',
  'task-revision', 'task-triage', 'task-substance', 'kc-statement',
  'task-modality', 'task-knowledge', 'task-embedding', 'kc-judge',
];

const GENERATION_LABELS = {
  current: 'in use today',
  superseded: 'older setup — superseded',
  retired: 'stage retired',
};

// Open/closed choices persist across visits; stages the founder has not
// touched default to open only when they have a run from today.
const OPEN_STATE_KEY = 'runs.stage-open';

function loadOpenState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(OPEN_STATE_KEY));
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function saveOpenState(openState) {
  try {
    localStorage.setItem(OPEN_STATE_KEY, JSON.stringify(openState));
  } catch {
    // Private-mode storage failures just lose persistence, not the page.
  }
}

const state = {
  runs: [],
  stageDefaults: {},
  retiredStages: [],
  stage: '',
  openStages: loadOpenState(),
};

const STATUS_CLASSES = {
  done: 'done', ok: 'done', succeeded: 'done', success: 'done', completed: 'done',
  running: 'running', in_progress: 'running', started: 'running',
  failed: 'failed', error: 'failed',
  pending: 'pending', queued: 'pending',
};

function statusClass(status) {
  return STATUS_CLASSES[String(status ?? '').toLowerCase()] || 'pending';
}

function formatDateTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function startedAtValue(run) {
  const time = new Date(run.started_at ?? 0).getTime();
  return Number.isNaN(time) ? 0 : time;
}

function runRow(run) {
  const errors = Number(run.errors ?? 0);
  const generation = run.generation || 'current';
  return `<div class="runs-ledger__row runs-ledger__row--${esc(generation)}">
    <span class="runs-cell--mono" title="${esc(run.id)}">${esc(run.id)}</span>
    <span class="runs-cell--model">${esc(run.model)}</span>
    <span class="runs-cell--mono" title="${esc(run.prompt_ref)}">${esc(run.prompt_ref ?? '—')}</span>
    <span class="run-generation run-generation--${esc(generation)}">${esc(GENERATION_LABELS[generation] || generation)}</span>
    <span class="run-status run-status--${esc(statusClass(run.status))}">${esc(run.status)}</span>
    <span class="runs-cell--count">${esc(run.items ?? '—')}</span>
    <span class="runs-cell--errors${errors > 0 ? ' has-errors' : ''}">${esc(run.errors ?? '—')}</span>
    <span class="runs-cell--time">${esc(formatDateTime(run.started_at))}</span>
  </div>`;
}

function stageIndex(stage) {
  const index = STAGE_ORDER.indexOf(stage);
  return index === -1 ? STAGE_ORDER.length : index;
}

function stageGroups() {
  const groups = new Map();
  for (const run of state.runs) {
    if (state.stage && run.stage !== state.stage) continue;
    if (!groups.has(run.stage)) groups.set(run.stage, []);
    groups.get(run.stage).push(run);
  }
  return [...groups.entries()].sort((a, b) => (
    stageIndex(a[0]) - stageIndex(b[0]) || a[0].localeCompare(b[0])
  ));
}

function stageDefaultLine(stage) {
  if (state.retiredStages.includes(stage)) {
    return 'This stage no longer exists in the pipeline — its runs are kept as history.';
  }
  const preset = state.stageDefaults[stage];
  if (!preset) return '';
  return `Current default: <code>${esc(preset.model)}</code> with prompt <code>${esc(preset.prompt_ref)}</code>.`;
}

function isToday(value) {
  const date = new Date(value ?? NaN);
  const now = new Date();
  return date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate();
}

function stageDefaultOpen(runs) {
  return runs.some((run) => isToday(run.started_at));
}

function stageIsOpen(stage, runs) {
  if (stage in state.openStages) return Boolean(state.openStages[stage]);
  return stageDefaultOpen(runs);
}

function stageSection([stage, runs]) {
  const currentCount = runs.filter((run) => run.generation === 'current').length;
  return `<details class="runs-stage" data-stage="${esc(stage)}" data-default-open="${stageDefaultOpen(runs) ? '1' : ''}"${stageIsOpen(stage, runs) ? ' open' : ''}>
    <summary class="runs-stage__head" aria-label="${esc(stage)} runs">
      <h2>${esc(stage)}</h2>
      <span class="runs-stage__count">${runs.length} run${runs.length === 1 ? '' : 's'}${currentCount ? ` · ${currentCount} in use today` : ''}</span>
      <p class="runs-stage__default">${stageDefaultLine(stage)}</p>
    </summary>
    <div class="runs-ledger">
      <div class="runs-ledger__header" aria-hidden="true">
        <span>Run</span><span>Model</span><span>Prompt</span>
        <span>Generation</span><span>Status</span><span>Items</span><span>Errors</span><span>Started</span>
      </div>
      ${runs.map(runRow).join('')}
    </div>
  </details>`;
}

function renderRuns() {
  const host = $('[data-runs]');
  const groups = stageGroups();
  const visible = groups.reduce((total, [, runs]) => total + runs.length, 0);
  $('[data-title-count]').textContent = state.runs.length
    ? `${visible} of ${state.runs.length}` : '';
  if (!state.runs.length) {
    host.innerHTML = '<p class="runs-empty">No runs yet. Runs appear here as pipeline stages execute.</p>';
    return;
  }
  if (!groups.length) {
    host.innerHTML = '<p class="runs-empty">No runs for this stage.</p>';
    return;
  }
  host.innerHTML = groups.map(stageSection).join('');
}

function renderStageFilter() {
  const select = $('[data-stage-filter]');
  const stages = [...new Set(state.runs.map((run) => run.stage).filter(Boolean))]
    .sort((a, b) => stageIndex(a) - stageIndex(b) || a.localeCompare(b));
  select.innerHTML = '<option value="">All stages</option>' + stages.map((stage) => (
    `<option value="${esc(stage)}">${esc(stage)}</option>`
  )).join('');
  select.value = stages.includes(state.stage) ? state.stage : '';
}

async function loadRuns() {
  const status = $('[data-status]');
  try {
    const response = await fetch('/api/runs', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`runs_load_failed_${response.status}`);
    const payload = await response.json();
    state.runs = [...(payload.runs || [])].sort((a, b) => startedAtValue(b) - startedAtValue(a));
    state.stageDefaults = payload.stage_defaults || {};
    state.retiredStages = payload.retired_stages || [];
    renderStageFilter();
    renderRuns();
    status.textContent = '';
    status.classList.remove('runs-status--error');
  } catch {
    status.textContent = 'Could not load runs. Is the API running? Reload to try again.';
    status.classList.add('runs-status--error');
  }
}

$('[data-stage-filter]').addEventListener('change', (event) => {
  state.stage = event.currentTarget.value;
  renderRuns();
});

// `toggle` does not bubble; capture catches it from every stage <details>.
// Browsers also queue a toggle when innerHTML parses `open`, so a state that
// matches the render-time default clears the override instead of storing it —
// only genuine departures from the default are remembered.
$('[data-runs]').addEventListener('toggle', (event) => {
  const details = event.target.closest('details[data-stage]');
  if (!details) return;
  const defaultOpen = details.dataset.defaultOpen === '1';
  if (details.open === defaultOpen) {
    delete state.openStages[details.dataset.stage];
  } else {
    state.openStages[details.dataset.stage] = details.open;
  }
  saveOpenState(state.openStages);
}, true);

loadRuns();
