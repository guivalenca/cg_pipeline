const ICONS = {
  check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>',
  edit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/></svg>',
  external: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>',
  inherited: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7h-9M14 4l-3 3 3 3M4 17h9M10 14l3 3-3 3"/></svg>',
  lesson: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v14H4zM8 9h8M8 13h5"/></svg>',
  source: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16h16V8zM14 2v6h6M8 13h8M8 17h6"/></svg>',
  warning: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 2 21h20L12 3Z"/><path d="M12 9v5M12 18h.01"/></svg>',
};

const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

const fmtDate = (value) => {
  if (!value) return 'Data não informada';
  const parts = String(value).slice(0, 10).split('-');
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return String(value);
};

const safeUrl = (value) => {
  try {
    const url = new URL(String(value || ''));
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
};

const valueOf = (item, side) => item?.[side] || null;
const titleOf = (item) => valueOf(item, 'incoming')?.title || valueOf(item, 'current')?.title || 'Item sem título';
const lessonModel = (lesson) => valueOf(lesson, 'incoming') || valueOf(lesson, 'current') || {};

const FIELD_DEFS = {
  lesson: [
    ['title', 'Título', 'text'],
    ['subject', 'Matéria', 'text'],
    ['subjects', 'Assuntos', 'subjects'],
    ['date', 'Data', 'date'],
    ['week', 'Semana', 'number'],
    ['kind', 'Tipo', 'text'],
    ['description', 'Descrição', 'textarea'],
  ],
  source: [
    ['title', 'Título', 'text'],
    ['description', 'Descrição', 'textarea'],
    ['url', 'Link', 'url'],
    ['media_type', 'Tipo', 'media'],
    ['resource_code', 'Código do recurso', 'text'],
    ['scope_kind', 'Tipo de escopo', 'text'],
    ['scope_value', 'Escopo', 'text'],
  ],
};

function statusLabel(status) {
  return { changed: 'Alterado', added: 'Adicionado', removed: 'Removido', unchanged: 'Sem mudanças' }[status] || status;
}

function extractionLabel(item) {
  const extraction = item.extraction || {};
  const pipeline = String(extraction.pipeline?.status || '').toLowerCase();
  if (pipeline === 'ready' || extraction.has_markdown) return ['Markdown limpo', 'ready'];
  if (pipeline === 'failed' || pipeline === 'attention') return ['Precisa de atenção', 'attention'];
  if (['queued', 'extracting', 'images', 'cleaning'].includes(pipeline)) return ['Processando', 'attention'];
  if (valueOf(item, 'current')?.source_id) return ['Não extraído', 'idle'];
  return null;
}

function settingsLabel(item) {
  const current = valueOf(item, 'current') || {};
  const review = current.review || {};
  const settings = [];
  if (current.hidden) settings.push('Oculto');
  if (review.validated) settings.push('Validado');
  if (review.complexity === 'simple') settings.push('Simples');
  if (review.complexity === 'complex') settings.push('Complexo');
  return settings;
}

function fieldChanged(item, key) {
  const current = valueOf(item, 'current')?.[key] ?? null;
  const incoming = valueOf(item, 'incoming')?.[key] ?? null;
  const comparable = (value) => Array.isArray(value) ? JSON.stringify(value) : String(value ?? '');
  return comparable(current) !== comparable(incoming);
}

function summaryFor(item) {
  if (item.status === 'added') return item.kind === 'lesson' ? 'Nova aula incluída na planilha.' : 'Novo autoestudo incluído na aula.';
  if (item.status === 'removed') return item.kind === 'lesson' ? 'A aula não existe mais na nova planilha.' : 'O autoestudo não existe mais na nova planilha.';
  if (item.status === 'unchanged') {
    const settings = settingsLabel(item);
    return settings.length ? `Sem mudanças; ${settings.join(', ').toLowerCase()} preservado.` : 'Sem mudanças na planilha.';
  }
  const labels = FIELD_DEFS[item.kind].filter(([key]) => fieldChanged(item, key)).map(([, label]) => label.toLowerCase());
  return labels.length ? `${labels.join(', ')} ${labels.length === 1 ? 'mudou' : 'mudaram'} neste item.` : 'O item foi alterado.';
}

function ensureStyles() {
  if (document.querySelector('[data-reconciliation-style]')) return;
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = '/static/syllabus_reconciliation.css?v=6';
  link.dataset.reconciliationStyle = 'true';
  document.head.appendChild(link);
}

export function mountSyllabusReconciliation({ headingHost, viewHost, reconciliation, onCancel, onApplied, announce }) {
  ensureStyles();
  const lessons = reconciliation.lessons || [];
  const reviewLessons = lessons.filter((lesson) => lesson.status !== 'unchanged' || lesson.identity?.state === 'review' || lesson.sources.some((source) => source.status !== 'unchanged'));
  const allItems = lessons.flatMap((lesson) => [lesson, ...lesson.sources]);
  const actionableItems = allItems.filter((item) => item.status !== 'unchanged' || item.identity?.state === 'review');
  const contentActionableItems = allItems.filter((item) => item.status !== 'unchanged');
  const identityActionableItems = lessons.filter((lesson) => lesson.identity?.state === 'review');
  const state = {
    active: true,
    selectedLessonId: reviewLessons[0]?.item_id || null,
    selectedItemId: reviewLessons[0]?.item_id || null,
    decisions: {},
    identityDecisions: {},
    draftIdentityDecisions: {},
    identityCandidates: {},
    drafts: {},
    manualExpanded: new Set(),
    busy: false,
    error: null,
  };

  const selectedLesson = () => lessons.find((lesson) => lesson.item_id === state.selectedLessonId) || reviewLessons[0] || lessons[0];
  const selectedItem = () => allItems.find((item) => item.item_id === state.selectedItemId) || selectedLesson();

  function identityCandidatesFor(item) {
    const candidates = item.identity?.candidates || [];
    if (candidates.length) return candidates;
    const current = valueOf(item, 'current');
    const lessonId = item.identity?.lesson_id || current?.id;
    return lessonId ? [{ ...current, lesson_id: lessonId }] : [];
  }

  function selectedIdentityCandidate(item) {
    const candidates = identityCandidatesFor(item);
    const candidateId = state.identityCandidates[item.item_id]
      || state.identityDecisions[item.item_id]?.lesson_id
      || candidates[0]?.lesson_id;
    const candidate = candidates.find((option) => option.lesson_id === candidateId) || candidates[0] || null;
    if (candidate?.lesson_id) state.identityCandidates[item.item_id] = candidate.lesson_id;
    return candidate;
  }

  function keptIdentityOwner(lessonId, ownerItemId) {
    return lessons.find((item) => (
      item.item_id !== ownerItemId
      && valueOf(item, 'current')?.id === lessonId
      && (
        state.decisions[item.item_id] === 'keep'
        || state.identityDecisions[item.item_id]?.choice === 'keep'
      )
    ))?.item_id || null;
  }

  function needsIdentityDecision(item) {
    return item.kind === 'lesson'
      && (item.identity?.state === 'review' || state.decisions[item.item_id] === 'custom');
  }

  function itemIsPending(item) {
    const contentPending = item.status !== 'unchanged' && !state.decisions[item.item_id];
    const identityPending = needsIdentityDecision(item) && !state.identityDecisions[item.item_id];
    return contentPending || identityPending;
  }

  const pendingCount = () => actionableItems.filter(itemIsPending).length;
  const willCreateVersion = () => contentActionableItems.some((item) => {
    const decision = state.decisions[item.item_id];
    return decision === 'transition';
  }) || identityActionableItems.some((item) => {
    if (item.status !== 'unchanged') return false;
    const decision = state.identityDecisions[item.item_id];
    if (decision?.choice === 'new') return true;
    if (decision?.choice !== 'same') return false;
    return decision.lesson_id !== valueOf(item, 'current')?.id;
  });

  function versionEffect() {
    if (pendingCount()) return 'pending';
    if (Object.values(state.decisions).includes('custom')) return 'unknown';
    return willCreateVersion() ? 'create' : 'keep';
  }

  function versionEffectLabel({ long = false } = {}) {
    const current = reconciliation.current_version?.seq;
    const next = reconciliation.next_version_seq;
    const prefix = long ? 'Versão ' : 'v';
    if (versionEffect() === 'pending') return `${prefix}${esc(current)} → resultado pendente`;
    if (versionEffect() === 'keep') return `${prefix}${esc(current)} será mantida`;
    if (versionEffect() === 'create') return `${prefix}${esc(current)} → ${long ? 'prévia da versão ' : 'v'}${esc(next)}`;
    return `${prefix}${esc(current)} → resultado definido ao concluir`;
  }

  function renderHeading() {
    headingHost.innerHTML = `<div>
      <button class="syl-back recon-cancel-link" type="button" data-recon-cancel>← Voltar ao syllabus</button>
      <p class="syl-eyebrow">Revisão da nova planilha</p>
      <h1>Atualizar ${esc(reconciliation.syllabus_title || 'syllabus')}</h1>
      <p>Escolha somente o destino das mudanças reais; ajustes locais continuam preservados.</p>
    </div>
    <div class="recon-heading-meta"><span>Arquivo analisado</span><strong>${esc(reconciliation.file_name)}</strong><small>${versionEffectLabel()}</small></div>`;
  }

  function renderSummary() {
    const summary = reconciliation.summary || {};
    const pending = pendingCount();
    return `<section class="recon-summary" aria-label="Resumo da comparação">
      <div><span>${versionEffectLabel({ long: true })}</span><strong>${pending} ${pending === 1 ? 'item pendente' : 'itens pendentes'}</strong><p>Itens com conteúdo 1:1 não exigem decisão de conteúdo. Ocultação, validação, complexidade e edições manuais continuam aplicadas.</p></div>
      <dl><div><dt>${esc(summary.automatic_identity_count || 0)}</dt><dd>IDs reconhecidos</dd></div><div><dt>${esc(summary.unchanged_source_count || 0)}</dt><dd>fontes sem mudança</dd></div><div><dt>${esc(summary.inherited_settings || 0)}</dt><dd>ajustes preservados</dd></div><div><dt>${esc(actionableItems.length)}</dt><dd>decisões necessárias</dd></div></dl>
    </section>`;
  }

  function lessonCounts(lesson) {
    return [lesson, ...lesson.sources].reduce((counts, item) => {
      counts[item.status] = (counts[item.status] || 0) + 1;
      return counts;
    }, {});
  }

  function renderExtraction(item) {
    const label = extractionLabel(item);
    return label ? `<span class="recon-extraction recon-extraction--${label[1]}">${esc(label[0])}</span>` : '';
  }

  function renderRailSubtask(item) {
    const decision = state.decisions[item.item_id];
    const identityDecision = state.identityDecisions[item.item_id];
    const settings = settingsLabel(item);
    let decisionLabel = statusLabel(item.status);
    if (itemIsPending(item) && item.identity?.state === 'review') decisionLabel = 'Decisão pendente';
    else if (decision === 'custom') {
      decisionLabel = identityDecision?.choice === 'same'
        ? 'Versão manual · relacionada'
        : identityDecision?.choice === 'new'
          ? 'Versão manual · nova aula'
          : 'Versão manual';
    } else if (identityDecision?.choice === 'keep' || decision === 'keep') decisionLabel = 'Manter';
    else if (identityDecision?.choice === 'same') decisionLabel = 'Relacionada + transicionar';
    else if (identityDecision?.choice === 'new') decisionLabel = 'Nova aula + transicionar';
    else if (decision === 'transition') decisionLabel = 'Transicionar';
    return `<button type="button" data-recon-item="${esc(item.item_id)}" class="recon-lesson-subtask recon-lesson-subtask--${esc(item.status)} ${item.item_id === state.selectedItemId ? 'is-active' : ''}">
      <span class="recon-lesson-subtask__line"></span>
      <span class="recon-lesson-subtask__body"><small>${item.kind === 'lesson' ? 'Dados da aula' : 'Autoestudo'}${settings.length ? ` · ${esc(settings.join(' · '))}` : ''}</small><strong>${esc(item.kind === 'lesson' ? 'Dados da aula' : titleOf(item))}</strong><em>${esc(summaryFor(item))}</em></span>
      <span class="recon-lesson-subtask__meta">${renderExtraction(item)}<span class="recon-change-state recon-change-state--${esc(item.status)}">${!itemIsPending(item) && (decision || identityDecision) ? ICONS.check : ''}${esc(decisionLabel)}</span></span>
    </button>`;
  }

  function renderLessonRail(lesson) {
    const counts = lessonCounts(lesson);
    const lessonItems = [lesson, ...lesson.sources];
    const total = lessonItems.filter((item) => item.status !== 'unchanged' || item.identity?.state === 'review').length;
    const resolved = lessonItems.filter((item) => (
      item.status !== 'unchanged' || item.identity?.state === 'review'
    ) && !itemIsPending(item)).length;
    const active = lesson.item_id === state.selectedLessonId;
    const model = lessonModel(lesson);
    const changes = [];
    if (counts.changed) changes.push(`${counts.changed} alterado${counts.changed === 1 ? '' : 's'}`);
    if (counts.added) changes.push(`${counts.added} novo${counts.added === 1 ? '' : 's'}`);
    if (counts.removed) changes.push(`${counts.removed} removido${counts.removed === 1 ? '' : 's'}`);
    return `<section class="recon-lesson-tree ${active ? 'is-active' : ''}">
      <button type="button" data-recon-lesson="${esc(lesson.item_id)}" class="recon-lesson-parent">
        <span class="recon-lesson-rail__body"><small><span>${esc(model.subject || 'Sem matéria')}</span><time datetime="${esc(model.date || '')}">${esc(fmtDate(model.date))}</time></small><strong>${esc(model.title || 'Aula sem título')}</strong><em>${esc(changes.join(' · ') || 'Sem mudanças')}</em></span>
        <span class="recon-lesson-rail__progress ${resolved === total ? 'is-complete' : ''}">${resolved}/${total}</span>
      </button>
      ${active ? `<div class="recon-lesson-subtasks">${[lesson, ...lesson.sources].map(renderRailSubtask).join('')}</div>` : ''}
    </section>`;
  }

  function renderFieldValue(item, key, label, kind, side) {
    const value = valueOf(item, side)?.[key];
    const printable = value === null || value === undefined || value === ''
      ? '—'
      : kind === 'date'
        ? fmtDate(value)
        : kind === 'subjects'
          ? (Array.isArray(value) ? value.join('\n') : value)
          : value;
    const href = kind === 'url' ? safeUrl(value) : null;
    const content = href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(printable)}${ICONS.external}</a>` : `<p>${esc(printable)}</p>`;
    return `<div class="recon-field${fieldChanged(item, key) ? ' is-changed' : ''}"><small>${esc(label)}${fieldChanged(item, key) ? '<span>Mudou</span>' : ''}</small>${content}</div>`;
  }

  function renderComparison(item) {
    const version = reconciliation.current_version || {};
    const fields = FIELD_DEFS[item.kind];
    return `<section class="recon-comparison" aria-label="Comparação lado a lado">
      <article><header><span>Versão atual</span><strong>v${esc(version.seq)} · ${esc(fmtDate(version.created_at))}</strong></header><div>${fields.map(([key, label, kind]) => renderFieldValue(item, key, label, kind, 'current')).join('')}</div></article>
      <article><header><span>Nova planilha</span><strong>${esc(reconciliation.file_name)}</strong></header><div>${fields.map(([key, label, kind]) => renderFieldValue(item, key, label, kind, 'incoming')).join('')}</div></article>
    </section>`;
  }

  function renderDeletedWarning(item) {
    if (item.status !== 'removed') return '';
    const preserved = item.kind === 'source' && valueOf(item, 'current')?.source_id && extractionLabel(item)?.[1] === 'ready';
    return `<aside class="recon-deleted-warning">${ICONS.warning}<div><strong>Removido da nova planilha</strong><span>${item.kind === 'lesson' ? 'Esta aula não existe na nova versão.' : 'Este autoestudo não existe mais nesta aula.'}${preserved ? ' O Markdown já extraído continuará preservado no Universe.' : ''}</span></div></aside>`;
  }

  function renderChoices(item) {
    if (item.kind === 'lesson' && item.identity?.state === 'review') {
      const identityDecision = state.identityDecisions[item.item_id];
      const contentDecision = state.decisions[item.item_id];
      const candidate = selectedIdentityCandidate(item);
      const relatedAvailable = Boolean(candidate && !keptIdentityOwner(candidate.lesson_id, item.item_id));
      const relatedSelected = relatedAvailable && contentDecision !== 'custom' && identityDecision?.choice === 'same';
      const keepSelected = identityDecision?.choice === 'keep';
      const newSelected = contentDecision !== 'custom' && identityDecision?.choice === 'new';
      return `<section class="recon-choices recon-choices--lesson" data-recon-lesson-actions><div><small>O que deve entrar no syllabus?</small><h3>Escolha uma ação completa</h3></div><div role="group" aria-label="Destino da aula">
        <button type="button" aria-label="É a aula selecionada + transicionar" data-recon-lesson-action="related-transition" class="${relatedSelected ? 'is-selected' : ''}" aria-pressed="${relatedSelected}" ${relatedAvailable ? '' : 'disabled'}>${relatedSelected ? ICONS.check : ''}<span><strong>É a aula selecionada + transicionar</strong><small>${relatedAvailable ? 'Mantém o ID da aula relacionada e aceita as mudanças.' : 'Esta aula já foi mantida por outra entrada.'}</small></span></button>
        <button type="button" aria-label="Manter" data-recon-lesson-action="keep" class="${keepSelected ? 'is-selected' : ''}" aria-pressed="${keepSelected}">${keepSelected ? ICONS.check : ''}<span><strong>Manter</strong><small>Continua exatamente como está hoje, sem aplicar esta mudança.</small></span></button>
        <button type="button" aria-label="É uma aula nova + transicionar" data-recon-lesson-action="new-transition" class="${newSelected ? 'is-selected' : ''}" aria-pressed="${newSelected}">${newSelected ? ICONS.check : ''}<span><strong>É uma aula nova + transicionar</strong><small>Aceita as mudanças e cria um novo ID.</small></span></button>
      </div></section>`;
    }
    if (item.status === 'unchanged') return `<p class="recon-unchanged-note">${ICONS.inherited}<span><strong>Nenhuma decisão de conteúdo necessária</strong>Este item é 1:1 e seus ajustes locais continuam aplicados.</span></p>`;
    const decision = state.decisions[item.item_id];
    const transitionCopy = item.status === 'removed' ? 'Aceita a remoção indicada pela planilha.' : item.status === 'added' ? 'Inclui o novo item no syllabus.' : 'Aceita todas as mudanças deste item.';
    return `<section class="recon-choices"><div><small>O que deve entrar na nova versão?</small><h3>Escolha o destino deste item</h3></div><div>
      <button type="button" data-recon-choice="keep" class="${decision === 'keep' ? 'is-selected' : ''}" aria-pressed="${decision === 'keep'}">${decision === 'keep' ? ICONS.check : ''}<span><strong>Manter</strong><small>Continua exatamente como está hoje.</small></span></button>
      <button type="button" data-recon-choice="transition" class="${decision === 'transition' ? 'is-selected' : ''}" aria-pressed="${decision === 'transition'}">${decision === 'transition' ? ICONS.check : ''}<span><strong>Transicionar</strong><small>${esc(transitionCopy)}</small></span></button>
    </div></section>`;
  }

  function identityReason(identity) {
    return {
      exact_text: 'Título, descrição e matéria coincidem com a versão anterior.',
      small_text_edit: 'As mudanças de título e descrição ficaram dentro do limite automático.',
      subject_changed: 'A matéria mudou. O sistema não mantém o ID sem sua decisão.',
      kind_changed: 'O tipo da aula mudou. O sistema não mantém o ID sem sua decisão.',
      ambiguous_match: 'A correspondência não é segura o suficiente para manter o ID automaticamente.',
      large_title_edit: 'O título mudou além do limite automático.',
      large_description_edit: 'A descrição mudou além do limite automático.',
      no_confident_match: 'Não há uma correspondência segura. Escolha uma aula anterior ou crie um novo ID.',
      no_predecessor: 'Nenhuma aula anterior corresponde a esta entrada.',
    }[identity?.reason] || 'A identidade desta aula precisa de confirmação.';
  }

  function identityCandidateLabel(candidate, { includeTitle = true } = {}) {
    const details = [
      candidate.subject || 'Sem matéria',
      candidate.kind || 'Aula',
      candidate.week ? `semana ${candidate.week}` : null,
      candidate.date ? fmtDate(candidate.date) : null,
      candidate.seq ? `ordem ${candidate.seq}` : null,
      candidate.lesson_id ? `ID …${String(candidate.lesson_id).slice(-6)}` : null,
    ].filter(Boolean);
    return `${includeTitle ? `${candidate.title || 'Aula sem título'} · ` : ''}${details.join(' · ')}`;
  }

  function renderIdentity(item) {
    if (item.kind !== 'lesson') return '';
    const identity = item.identity || {};
    if (identity.state === 'removed') return '';
    if (identity.state === 'carried') {
      return `<aside class="recon-identity recon-identity--automatic">${ICONS.inherited}<div><small>Identidade da aula</small><strong>ID mantido automaticamente</strong><span>${esc(identityReason(identity))}</span></div></aside>`;
    }
    if (identity.state === 'new') {
      return `<aside class="recon-identity recon-identity--new">${ICONS.lesson}<div><small>Identidade da aula</small><strong>Nova aula</strong><span>${esc(identityReason(identity))}</span></div></aside>`;
    }
    const candidates = identityCandidatesFor(item);
    const candidate = selectedIdentityCandidate(item) || {};
    const selectedElsewhere = new Set(Object.entries(state.identityDecisions)
      .filter(([itemId]) => itemId !== item.item_id)
      .map(([itemId, value]) => {
        if (value?.choice === 'same') return value.lesson_id;
        const owner = allItems.find((option) => option.item_id === itemId);
        return value?.choice === 'keep' ? valueOf(owner, 'current')?.id : null;
      })
      .filter(Boolean));
    lessons.forEach((option) => {
      if (option.item_id === item.item_id || state.decisions[option.item_id] !== 'keep') return;
      const keptId = valueOf(option, 'current')?.id;
      if (keptId) selectedElsewhere.add(keptId);
    });
    const candidateControl = candidates.length > 1
      ? `<label class="recon-identity-picker"><span>Qual aula atual está relacionada?</span><select data-recon-identity-candidate aria-label="Aula relacionada">${candidates.map((option) => `<option value="${esc(option.lesson_id)}"${option.lesson_id === candidate.lesson_id ? ' selected' : ''}${selectedElsewhere.has(option.lesson_id) ? ' disabled' : ''}>${esc(identityCandidateLabel(option))}</option>`).join('')}</select></label>`
      : `<div class="recon-identity-candidate"><span>Aula relacionada</span><strong>${esc(candidate.title || 'Aula sem título')}</strong><small>${esc(identityCandidateLabel(candidate, { includeTitle: false }))}</small></div>`;
    return `<section class="recon-identity-review">
      <header>${identity.reason === 'subject_changed' ? ICONS.warning : ICONS.lesson}<div><small>Identidade da aula</small><h3>Como esta entrada se relaciona com o syllabus atual?</h3><p>${esc(identityReason(identity))}</p></div></header>
      ${candidateControl}
    </section>`;
  }

  function renderManualField(item, key, label, kind) {
    const value = state.drafts[item.item_id]?.[key] || '';
    if (kind === 'textarea' || kind === 'subjects') {
      const printable = kind === 'subjects' && Array.isArray(value) ? value.join('\n') : value;
      return `<label class="recon-manual-field recon-manual-field--wide"><span>${esc(label)}</span><textarea rows="4" data-recon-draft="${esc(key)}">${esc(printable)}</textarea></label>`;
    }
    if (kind === 'media') return `<label class="recon-manual-field"><span>${esc(label)}</span><select data-recon-draft="${esc(key)}"><option value="">Escolha</option>${['article', 'video', 'book'].map((choice) => `<option value="${choice}"${value === choice ? ' selected' : ''}>${choice === 'article' ? 'Artigo' : choice === 'video' ? 'Vídeo' : 'Livro'}</option>`).join('')}</select></label>`;
    return `<label class="recon-manual-field"><span>${esc(label)}</span><input type="${kind === 'number' ? 'number' : kind === 'date' ? 'date' : 'text'}" value="${esc(value)}" data-recon-draft="${esc(key)}"></label>`;
  }

  function manualIsReady(item) {
    if (!String(state.drafts[item.item_id]?.title || '').trim()) return false;
    if (item.kind !== 'lesson') return true;
    const identity = state.draftIdentityDecisions[item.item_id];
    if (identity?.choice === 'new') return true;
    return identity?.choice === 'same'
      && !keptIdentityOwner(identity.lesson_id, item.item_id);
  }

  function renderManualIdentity(item) {
    if (item.kind !== 'lesson') return '';
    const decision = state.draftIdentityDecisions[item.item_id];
    const candidate = selectedIdentityCandidate(item);
    const relatedAvailable = Boolean(candidate && !keptIdentityOwner(candidate.lesson_id, item.item_id));
    const relatedSelected = relatedAvailable && decision?.choice === 'same';
    const newSelected = decision?.choice === 'new';
    return `<section class="recon-manual-identity"><header><small>Identidade da versão montada</small><h4>Esta versão continua qual aula?</h4><p>Escolha a relação antes de usar a versão manual.</p></header>
      ${candidate ? `<div class="recon-identity-candidate"><span>Aula relacionada</span><strong>${esc(candidate.title || 'Aula sem título')}</strong><small>${esc(identityCandidateLabel(candidate, { includeTitle: false }))}</small></div>` : ''}
      <div class="recon-identity-choices" role="group" aria-label="Identidade da versão montada">
        ${candidate ? `<button type="button" aria-label="É a aula relacionada" data-recon-manual-identity="same" class="${relatedSelected ? 'is-selected' : ''}" aria-pressed="${relatedSelected}" ${relatedAvailable ? '' : 'disabled'}>${relatedSelected ? ICONS.check : ''}<span><strong>É a aula relacionada</strong><small>${relatedAvailable ? 'Mantém o ID dessa aula.' : 'Esta aula já foi mantida por outra entrada.'}</small></span></button>` : ''}
        <button type="button" aria-label="É uma aula nova" data-recon-manual-identity="new" class="${newSelected ? 'is-selected' : ''}" aria-pressed="${newSelected}">${newSelected ? ICONS.check : ''}<span><strong>É uma aula nova</strong><small>Cria um novo ID para a versão montada.</small></span></button>
      </div>
    </section>`;
  }

  function renderManual(item) {
    if (item.status === 'unchanged') return '';
    const expanded = state.manualExpanded.has(item.item_id);
    return `<section class="recon-manual-shell">
      <button type="button" data-recon-manual-toggle aria-expanded="${expanded}">${ICONS.edit}<span><strong>Montar uma versão manual</strong><small>Use quando Manter ou Transicionar não forem suficientes.</small></span><b>${expanded ? 'Fechar' : 'Abrir'}</b></button>
      ${expanded ? `<form data-recon-manual-form="${esc(item.item_id)}"><p>Monte o item em branco. O título é obrigatório.</p><div>${FIELD_DEFS[item.kind].map(([key, label, kind]) => renderManualField(item, key, label, kind)).join('')}</div>${renderManualIdentity(item)}<footer><button type="submit" ${manualIsReady(item) ? '' : 'disabled'}>${ICONS.check}Usar versão montada</button></footer></form>` : ''}
    </section>`;
  }

  function renderSelectedItem(item) {
    const index = actionableItems.findIndex((candidate) => candidate.item_id === item.item_id);
    return `<section class="recon-item-detail">
      <header><div class="recon-item-detail__type"><span>${item.kind === 'lesson' ? ICONS.lesson : ICONS.source}</span><small>${item.kind === 'lesson' ? 'Dados da aula' : 'Autoestudo'}</small>${renderExtraction(item)}</div></header>
      <div class="recon-item-detail__heading"><h2>${esc(item.kind === 'lesson' ? 'Dados da aula' : titleOf(item))}</h2><span class="recon-change-state recon-change-state--${esc(item.status)}">${esc(statusLabel(item.status))}</span></div>
      <p>${esc(summaryFor(item))}</p>${renderIdentity(item)}${renderDeletedWarning(item)}${renderComparison(item)}${renderChoices(item)}${renderManual(item)}
      <footer><button type="button" data-recon-step="-1">← Anterior</button><span>${index >= 0 ? `${index + 1} de ${actionableItems.length} itens com decisão` : 'Item sem mudanças'}</span><button type="button" data-recon-step="1">Próximo →</button></footer>
    </section>`;
  }

  function renderActionBar() {
    const pending = pendingCount();
    const effect = versionEffect();
    const status = state.error
      ? esc(state.error)
      : pending
        ? `Resolva ${pending} ${pending === 1 ? 'item' : 'itens'} para continuar`
        : effect === 'create'
          ? 'Todas as mudanças têm um destino'
          : effect === 'keep'
            ? 'Nenhuma mudança será aplicada'
            : 'O resultado será calculado a partir da versão montada';
    const buttonLabel = state.busy
      ? (effect === 'create' ? 'Criando versão…' : 'Concluindo…')
      : pending
        ? 'Concluir revisão'
        : (effect === 'create'
          ? `Criar versão ${esc(reconciliation.next_version_seq)}`
          : effect === 'keep'
            ? 'Concluir sem criar versão'
            : 'Concluir revisão');
    return `<footer class="recon-action-bar"><div><small>${versionEffectLabel()}</small><strong>${status}</strong></div><button type="button" data-recon-apply ${pending || state.busy ? 'disabled' : ''}>${ICONS.check}${buttonLabel}</button></footer>`;
  }

  function render() {
    if (!state.active) return;
    renderHeading();
    const lesson = selectedLesson();
    if (!lesson) {
      viewHost.innerHTML = '<div class="syl-empty"><strong>Nenhuma mudança encontrada.</strong><span>A planilha pode ser aceita sem decisões.</span></div>' + renderActionBar();
      return;
    }
    const item = selectedItem();
    const model = lessonModel(lesson);
    viewHost.className = 'syl-view recon-production';
    viewHost.setAttribute('aria-busy', 'false');
    viewHost.innerHTML = `${renderSummary()}<div class="recon-workspace">
      <aside class="recon-lesson-rail"><header><span>Aulas com mudanças</span><h2>${reviewLessons.length} ${reviewLessons.length === 1 ? 'aula para revisar' : 'aulas para revisar'}</h2><p>Abra uma aula e percorra seus dados e autoestudos.</p></header><nav aria-label="Aulas com mudanças">${reviewLessons.map(renderLessonRail).join('')}</nav><footer>${ICONS.inherited}<div><strong>${esc(reconciliation.summary?.unchanged_lesson_count || 0)} aulas com conteúdo 1:1</strong><span>${esc(reconciliation.summary?.inherited_settings || 0)} ajustes locais reaplicados</span></div></footer></aside>
      <main class="recon-main"><header class="recon-class-heading"><div><small>${esc(model.subject || 'Sem matéria')} · Aula</small><h2>${esc(model.title || 'Aula sem título')}</h2><p>${esc(fmtDate(model.date))}</p></div><span>${lesson.sources.length} ${lesson.sources.length === 1 ? 'autoestudo' : 'autoestudos'}</span></header>${renderSelectedItem(item)}</main>
    </div>${renderActionBar()}`;
  }

  function chooseLesson(itemId) {
    const lesson = lessons.find((candidate) => candidate.item_id === itemId);
    if (!lesson) return;
    state.selectedLessonId = itemId;
    state.selectedItemId = [lesson, ...lesson.sources].find((item) => item.status !== 'unchanged')?.item_id || itemId;
    render();
  }

  function chooseItem(itemId) {
    const item = allItems.find((candidate) => candidate.item_id === itemId);
    if (!item) return;
    const lesson = lessons.find((candidate) => candidate.item_id === itemId || candidate.sources.some((source) => source.item_id === itemId));
    state.selectedLessonId = lesson?.item_id || state.selectedLessonId;
    state.selectedItemId = itemId;
    render();
  }

  function moveItem(direction) {
    let index = actionableItems.findIndex((item) => item.item_id === selectedItem()?.item_id);
    if (index < 0) index = direction > 0 ? -1 : 0;
    const next = actionableItems[(index + direction + actionableItems.length) % actionableItems.length];
    if (next) chooseItem(next.item_id);
  }

  function applyDecision(decision) {
    const item = selectedItem();
    if (!item || item.status === 'unchanged' || item.identity?.state === 'review' || state.busy) return;
    state.decisions[item.item_id] = decision;
    if (item.kind === 'lesson' && item.identity?.state !== 'review') {
      delete state.identityDecisions[item.item_id];
      if (decision === 'keep') {
        const currentId = valueOf(item, 'current')?.id;
        if (currentId) clearDuplicateIdentity(currentId, item.item_id);
      }
    }
    state.error = null;
    render();
  }

  function applyReviewedLessonAction(action) {
    const item = selectedItem();
    if (!item || item.kind !== 'lesson' || item.identity?.state !== 'review' || state.busy) return;
    if (item.status !== 'unchanged') {
      state.decisions[item.item_id] = action === 'keep' ? 'keep' : 'transition';
    }
    if (action === 'keep') {
      const currentId = valueOf(item, 'current')?.id;
      if (currentId) clearDuplicateIdentity(currentId, item.item_id);
      state.identityDecisions[item.item_id] = { choice: 'keep' };
    } else if (action === 'related-transition') {
      const candidate = selectedIdentityCandidate(item);
      if (!candidate?.lesson_id || keptIdentityOwner(candidate.lesson_id, item.item_id)) return;
      clearDuplicateIdentity(candidate.lesson_id, item.item_id);
      state.identityDecisions[item.item_id] = {
        choice: 'same',
        lesson_id: candidate.lesson_id,
      };
    } else if (action === 'new-transition') {
      state.identityDecisions[item.item_id] = { choice: 'new' };
    } else return;
    state.error = null;
    render();
    restoreIdentityFocus(item.item_id, 'data-recon-lesson-action', action);
  }

  function clearDuplicateIdentity(lessonId, ownerItemId) {
    Object.entries(state.identityDecisions).forEach(([itemId, decision]) => {
      if (itemId !== ownerItemId && decision?.choice === 'same' && decision.lesson_id === lessonId) {
        delete state.identityDecisions[itemId];
      }
    });
    Object.entries(state.draftIdentityDecisions).forEach(([itemId, decision]) => {
      if (itemId !== ownerItemId && decision?.choice === 'same' && decision.lesson_id === lessonId) {
        delete state.draftIdentityDecisions[itemId];
      }
    });
  }

  function restoreIdentityFocus(itemId, control, value) {
    const controls = [...viewHost.querySelectorAll(`[${control}]`)];
    const target = controls.find((element) => {
      const item = element.closest('.recon-item-detail');
      return selectedItem()?.item_id === itemId && item && (!value || element.getAttribute(control) === value);
    });
    target?.focus();
  }

  async function applyAll() {
    if (pendingCount() || state.busy) return;
    state.busy = true;
    state.error = null;
    render();
    try {
      const result = await onApplied({ decisions: state.decisions, drafts: state.drafts, identity_decisions: state.identityDecisions });
      state.active = false;
      return result;
    } catch (error) {
      state.busy = false;
      state.error = error.message;
      announce?.(`Não foi possível criar a nova versão: ${error.message}`);
      render();
    }
  }

  function handleClick(event) {
    if (!state.active) return;
    if (event.target.closest('[data-recon-cancel]')) { state.active = false; onCancel(); return; }
    const lesson = event.target.closest('[data-recon-lesson]');
    if (lesson) { chooseLesson(lesson.dataset.reconLesson); return; }
    const item = event.target.closest('[data-recon-item]');
    if (item) { chooseItem(item.dataset.reconItem); return; }
    const step = event.target.closest('[data-recon-step]');
    if (step) { moveItem(Number(step.dataset.reconStep)); return; }
    const lessonAction = event.target.closest('[data-recon-lesson-action]');
    if (lessonAction) { applyReviewedLessonAction(lessonAction.dataset.reconLessonAction); return; }
    const choice = event.target.closest('[data-recon-choice]');
    if (choice) { applyDecision(choice.dataset.reconChoice); return; }
    const manualIdentity = event.target.closest('[data-recon-manual-identity]');
    if (manualIdentity) {
      const item = selectedItem();
      if (item?.kind === 'lesson') {
        const choice = manualIdentity.dataset.reconManualIdentity;
        if (choice === 'same') {
          const lessonId = selectedIdentityCandidate(item)?.lesson_id;
          if (!lessonId || keptIdentityOwner(lessonId, item.item_id)) return;
          state.draftIdentityDecisions[item.item_id] = { choice: 'same', lesson_id: lessonId };
        } else {
          state.draftIdentityDecisions[item.item_id] = { choice: 'new' };
        }
        state.error = null;
        render();
        restoreIdentityFocus(item.item_id, 'data-recon-manual-identity', choice);
      }
      return;
    }
    if (event.target.closest('[data-recon-manual-toggle]')) {
      const id = selectedItem().item_id;
      if (state.manualExpanded.has(id)) state.manualExpanded.delete(id); else state.manualExpanded.add(id);
      render(); return;
    }
    if (event.target.closest('[data-recon-apply]')) applyAll();
  }

  function handleInput(event) {
    const identityCandidate = event.target.closest('[data-recon-identity-candidate]');
    if (identityCandidate) {
      const item = selectedItem();
      if (!item || item.identity?.state !== 'review') return;
      state.identityCandidates[item.item_id] = identityCandidate.value;
      if (state.identityDecisions[item.item_id]?.choice === 'same') {
        clearDuplicateIdentity(identityCandidate.value, item.item_id);
        state.identityDecisions[item.item_id] = {
          choice: 'same',
          lesson_id: identityCandidate.value,
        };
      }
      if (state.draftIdentityDecisions[item.item_id]?.choice === 'same') {
        state.draftIdentityDecisions[item.item_id] = {
          choice: 'same',
          lesson_id: identityCandidate.value,
        };
      }
      render();
      restoreIdentityFocus(item.item_id, 'data-recon-identity-candidate');
      return;
    }
    const input = event.target.closest('[data-recon-draft]');
    if (!input) return;
    const form = input.closest('[data-recon-manual-form]');
    const itemId = form.dataset.reconManualForm;
    state.drafts[itemId] ||= {};
    state.drafts[itemId][input.dataset.reconDraft] = input.value;
    const item = allItems.find((candidate) => candidate.item_id === itemId);
    form.querySelector('button[type="submit"]').disabled = !item || !manualIsReady(item);
  }

  function handleSubmit(event) {
    const form = event.target.closest('[data-recon-manual-form]');
    if (!form) return;
    event.preventDefault();
    const itemId = form.dataset.reconManualForm;
    const item = allItems.find((candidate) => candidate.item_id === itemId);
    if (!item || !manualIsReady(item)) return;
    if (item.kind === 'lesson') {
      const identityDecision = state.draftIdentityDecisions[itemId];
      if (identityDecision.choice === 'same') {
        clearDuplicateIdentity(identityDecision.lesson_id, itemId);
      }
      state.identityDecisions[itemId] = { ...identityDecision };
    }
    state.decisions[itemId] = 'custom';
    render();
    restoreIdentityFocus(itemId, 'data-recon-manual-toggle');
  }

  function handleKeys(event) {
    if (!state.active || state.busy) return;
    const tag = event.target.tagName?.toLowerCase();
    if (['input', 'textarea', 'select', 'button'].includes(tag) || event.target.isContentEditable) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); moveItem(-1); }
    else if (event.key === 'ArrowRight') { event.preventDefault(); moveItem(1); }
    else if (event.key.toLowerCase() === 'm') {
      event.preventDefault();
      if (selectedItem()?.identity?.state === 'review') applyReviewedLessonAction('keep');
      else applyDecision('keep');
    }
    else if (event.key.toLowerCase() === 't') { event.preventDefault(); applyDecision('transition'); }
  }

  viewHost.addEventListener('click', handleClick);
  viewHost.addEventListener('input', handleInput);
  viewHost.addEventListener('submit', handleSubmit);
  headingHost.addEventListener('click', handleClick);
  window.addEventListener('keydown', handleKeys);
  render();

  return () => {
    state.active = false;
    viewHost.removeEventListener('click', handleClick);
    viewHost.removeEventListener('input', handleInput);
    viewHost.removeEventListener('submit', handleSubmit);
    headingHost.removeEventListener('click', handleClick);
    window.removeEventListener('keydown', handleKeys);
  };
}
