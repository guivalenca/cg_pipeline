import './shell.js?v=2';

const $ = (selector, root = document) => root.querySelector(selector);
const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

const ATTENTION_LABELS = {
  coverage_gap: 'Coverage gap',
  acquisition_failed: 'Acquisition failed',
  missing_credentials: 'Firecrawl key missing',
  manual_access_required: 'Needs a person',
  missing_concrete_scope: 'Book scope needed',
  unsupported_media_kind: 'No fetcher yet',
};

/* One extra sentence where the note alone does not say what to do. */
const ATTENTION_HINTS = {
  missing_credentials: 'Put the Firecrawl key in the .env file at the repo root as FIRECRAWL_API_KEY, then run acquisition again.',
};

function corpusNote(corpus) {
  if (corpus.kind === 'test') {
    return 'The markdown archive the pipeline was built and benched on. Not part of any course — its numbers never mix with a real syllabus.';
  }
  if (corpus.extracted === 0 && corpus.failed === 0) {
    return 'Listed from the syllabus; nothing acquired yet. Acquisition is the next phase.';
  }
  return `${corpus.extracted} of ${corpus.sources} sources have extracted material.`;
}

function figure(label, value, tone = '') {
  return `<div class="corpus-figure${tone ? ` corpus-figure--${tone}` : ''}">
    <span class="overview-label">${esc(label)}</span>
    <span class="overview-value">${esc(value)}</span>
  </div>`;
}

function corpusGroupLine(corpus) {
  if (corpus.kind !== 'syllabus') return '';
  const text = corpus.group
    ? `Group ${corpus.group.group_name} — ${corpus.group.institution_name}`
    : 'Not assigned to a group yet.';
  return `<p class="corpus-card__group">${esc(text)}</p>`;
}

function corpusCard(corpus) {
  const kindLabel = corpus.kind === 'test' ? 'Test material' : 'Syllabus';
  const links = corpus.kind === 'test'
    ? `<a class="overview-panel__more" href="/sources?corpus=test">View sources</a>`
    : `<a class="overview-panel__more" href="/syllabi">View syllabus</a>
       <a class="overview-panel__more" href="/sources?corpus=${encodeURIComponent(corpus.id)}">View sources</a>`;
  return `<article class="panel corpus-card corpus-card--${esc(corpus.kind)}">
    <div class="corpus-card__head">
      <span class="corpus-card__kind">${esc(kindLabel)}</span>
      <h2>${esc(corpus.title)}</h2>
      ${corpusGroupLine(corpus)}
    </div>
    <div class="corpus-card__figures">
      ${figure('Sources', corpus.sources)}
      ${figure('Acquired', corpus.extracted, corpus.extracted ? 'good' : '')}
      ${figure('Not acquired', corpus.not_acquired, corpus.not_acquired ? 'wait' : '')}
      ${figure('Failed', corpus.failed, corpus.failed ? 'bad' : '')}
      ${figure('Tasks', corpus.tasks)}
      ${figure('KCs in universe', corpus.kcs)}
    </div>
    <p class="corpus-card__note">${esc(corpusNote(corpus))}</p>
    <div class="corpus-card__links">${links}</div>
  </article>`;
}

function universeMarkup(universe) {
  if (!universe?.grouping_id) {
    return '<p class="overview-empty">No grouping computed yet.</p>';
  }
  return `<div class="universe-strip">
    <div class="corpus-figure">
      <span class="overview-label">Same-knowledge pairs</span>
      <span class="overview-value">${esc(universe.mutual_pairs)}</span>
    </div>
    <div class="corpus-figure">
      <span class="overview-label">Composite KCs</span>
      <span class="overview-value">${esc(universe.composites)}</span>
    </div>
    <p class="universe-strip__note">Latest grouping <code>${esc(universe.grouping_id)}</code> —
      knowledge components judged the same are merged; everything else stays separate on purpose.</p>
  </div>`;
}

async function postJSON(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.detail || `Request failed (${response.status}).`);
  return payload;
}

/* Inline decisions. Both write one founder fact and nothing else: a book scope
   the fetcher can use, or a skip that takes the source off this list. */
function attentionActions(item, index) {
  if (!item.source_id) return '';
  const scopeId = `attention-scope-${index}`;
  const wantsScope = item.kind === 'missing_concrete_scope';
  return `
    <div class="attention-item__actions" data-actions>
      ${wantsScope ? '<button type="button" class="attention-action" data-scope-open>Provide book scope</button>' : ''}
      <button type="button" class="attention-action attention-action--quiet" data-skip-open>Skip this source</button>
    </div>
    ${wantsScope ? `<form class="attention-form" data-scope-form hidden>
      <label class="attention-form__label" for="${scopeId}">Which chapters, pages, or units should be fetched?</label>
      <div class="attention-form__row">
        <input class="attention-form__input" id="${scopeId}" data-scope-input type="text"
          placeholder="chapter 3, pages 40–58" autocomplete="off">
        <button type="submit" class="attention-action">Save scope</button>
        <button type="button" class="attention-action attention-action--quiet" data-scope-cancel>Cancel</button>
      </div>
    </form>` : ''}
    <div class="attention-confirm" data-skip-confirm hidden>
      <p class="attention-confirm__text">Skip it? The source stays in the syllabus, marked skipped, and stops asking for a decision.</p>
      <button type="button" class="attention-action" data-skip-yes>Skip it</button>
      <button type="button" class="attention-action attention-action--quiet" data-skip-cancel>Keep it</button>
    </div>
    <p class="attention-feedback" data-feedback hidden></p>`;
}

function attentionMarkup(items) {
  if (!items?.length) {
    return '<p class="overview-empty">Nothing needs a decision.</p>';
  }
  return items.map((item, index) => {
    const hint = ATTENTION_HINTS[item.kind];
    return `<article class="attention-item"${item.source_id ? ` data-source="${esc(item.source_id)}"` : ''}>
      <span class="attention-badge attention-badge--${esc(item.kind)}">${esc(ATTENTION_LABELS[item.kind] || String(item.kind ?? '').replaceAll('_', ' '))}</span>
      <div class="attention-item__body"><strong>${esc(item.title)}</strong>${item.note ? `<span>${esc(item.note)}</span>` : ''}${hint ? `<span class="attention-item__hint">${esc(hint)}</span>` : ''}</div>
      ${item.source_id ? `<a class="attention-link" href="/sources?id=${encodeURIComponent(item.source_id)}">Open source</a>` : ''}
      ${attentionActions(item, index)}
    </article>`;
  }).join('');
}

function wireAttentionItem(article) {
  const sourceId = article.dataset.source;
  if (!sourceId) return;
  const actions = $('[data-actions]', article);
  const scopeForm = $('[data-scope-form]', article);
  const skipConfirm = $('[data-skip-confirm]', article);
  const feedback = $('[data-feedback]', article);

  const show = (element) => {
    actions.hidden = element !== actions;
    if (scopeForm) scopeForm.hidden = element !== scopeForm;
    skipConfirm.hidden = element !== skipConfirm;
  };
  const say = (message, tone) => {
    feedback.textContent = message;
    feedback.hidden = !message;
    feedback.classList.toggle('attention-feedback--error', tone === 'error');
  };

  $('[data-scope-open]', article)?.addEventListener('click', () => {
    say('');
    show(scopeForm);
    $('[data-scope-input]', article)?.focus();
  });
  $('[data-scope-cancel]', article)?.addEventListener('click', () => show(actions));
  scopeForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = $('[data-scope-input]', article);
    const value = input.value.trim();
    if (!value) {
      say('Write the chapters or pages first.', 'error');
      input.focus();
      return;
    }
    try {
      await postJSON(`/api/sources/${encodeURIComponent(sourceId)}/scope-override`, { value });
      show(actions);
      // The failed attempt is still on the ledger, so the item stays here until
      // acquisition is run again — say so instead of pretending it cleared.
      say(`Scope recorded: ${value}. Open the source and run acquisition again to use it.`);
    } catch (error) {
      say(`Could not save the scope: ${error.message}`, 'error');
    }
  });

  $('[data-skip-open]', article)?.addEventListener('click', () => {
    say('');
    show(skipConfirm);
  });
  $('[data-skip-cancel]', article)?.addEventListener('click', () => show(actions));
  $('[data-skip-yes]', article)?.addEventListener('click', async () => {
    try {
      await postJSON(`/api/sources/${encodeURIComponent(sourceId)}/skip`, {});
      await loadOverview();
    } catch (error) {
      show(actions);
      say(`Could not skip this source: ${error.message}`, 'error');
    }
  });
}

async function loadOverview() {
  const status = $('[data-status]');
  try {
    const response = await fetch('/api/overview', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`overview_load_failed_${response.status}`);
    const overview = await response.json();
    $('[data-corpora]').innerHTML = (overview.corpora || []).map(corpusCard).join('')
      || '<p class="overview-empty">No material yet. Upload a syllabus to begin.</p>';
    $('[data-universe]').innerHTML = universeMarkup(overview.universe);
    const attentionHost = $('[data-attention]');
    attentionHost.innerHTML = attentionMarkup(overview.attention);
    attentionHost.querySelectorAll('[data-source]').forEach(wireAttentionItem);
    $('[data-ledger]').textContent = overview.ledger
      ? `Permanent ledger: ${overview.ledger.runs} model runs and ${overview.ledger.verdicts} judge verdicts recorded — full history under Runs.`
      : '';
    status.textContent = '';
    status.classList.remove('overview-status--error');
  } catch {
    status.textContent = 'Could not load the overview. Is the API running? Reload to try again.';
    status.classList.add('overview-status--error');
  }
}

loadOverview();
