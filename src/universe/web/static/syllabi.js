// Syllabi — list de syllabi + upload de planilha (list view) e módulo por
// semana com diff entre versões (detail view, /syllabi?id=...).
// O upload apenas registra uma versão e mostra o que mudou: nenhum estágio
// do pipeline é disparado a partir desta página.

const $ = (selector, root = document) => root.querySelector(selector);

const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

const state = {
  syllabi: [],
  listError: null,
  uploading: false,
  uploadResult: null,
  uploadError: null,
  detail: null,
  detailError: null,
  // Grupo do syllabus (estrutura organizacional): lista de grupos existentes,
  // atribuição atual e o estado do controle "atribuir a um grupo".
  org: { groups: [], assigned: null, error: null },
  groupControl: { selecting: false, saving: false, error: null, value: '' },
  selectedVersionId: null,
  diffDismissed: false,
  expanded: new Set(),
  editing: null, // { itemId, field, value, error, saving }
  historyOpen: new Set(), // "itemId field"
};

const viewHost = $('[data-view]');
const headingHost = $('[data-heading]');

function announce(message) {
  $('[data-status]').textContent = message;
}

function fmtDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function fmtDateShort(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' }).format(date);
}

function weekLabel(week) {
  const number = Number(week);
  return Number.isFinite(number) ? String(number).padStart(2, '0') : esc(week);
}

function kindClass(kind) {
  const plain = String(kind || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  if (plain === 'autoestudo') return 'autoestudo';
  if (plain.includes('instrucao')) return 'instrucao';
  if (plain.includes('orientacao')) return 'orientacao';
  if (plain.includes('projeto')) return 'projeto';
  if (plain.includes('avaliacao')) return 'avaliacao';
  return 'outro';
}

/* Ícones em linha, currentColor, stroke 2 — mesmo contrato de iconografia
   do design system do Companion (sem emoji no chrome). */
const ICON = {
  book: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
  video: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4.5" width="20" height="15" rx="2.5"/><path d="m10 9 5 3-5 3z"/></svg>',
  article: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h8"/></svg>',
  link: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/></svg>',
  chevron: '<svg class="syl-item__chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>',
  chevronRight: '<svg class="syl-card__chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>',
  external: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6"/><path d="M10 14 21 3"/></svg>',
  back: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>',
  upload: '<svg class="syl-drop__icon" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>',
  pencil: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/></svg>',
};

function mediaIcon(mediaType) {
  const plain = String(mediaType || '').toLowerCase();
  if (plain.includes('book') || plain.includes('livro')) return { icon: ICON.book, label: 'Livro' };
  if (plain.includes('video') || plain.includes('vídeo')) return { icon: ICON.video, label: 'Vídeo' };
  if (plain.includes('article') || plain.includes('artigo') || plain.includes('texto')) return { icon: ICON.article, label: 'Artigo' };
  return { icon: ICON.link, label: mediaType ? String(mediaType) : 'Material' };
}

const SOURCE_STATUS = {
  ingested: { label: 'Ingerida', cls: 'ingested', title: 'Fonte capturada e com artefato pronto.' },
  pending: { label: 'Pendente', cls: 'pending', title: 'Fonte vinculada, ainda sem captura concluída.' },
  failed: { label: 'Falhou', cls: 'failed', title: 'Todas as capturas desta fonte falharam.' },
  unlinked: { label: 'Sem fonte', cls: 'unlinked', title: 'Nenhuma fonte vinculada a este item.' },
  // Decisão do founder, não um problema: marcador discreto, sem alarme.
  'skipped by founder': {
    label: 'Pulada',
    cls: 'skipped',
    title: 'Você marcou esta fonte como pulada — ela continua no plano, mas nada será capturado.',
  },
};

function statusPill(status) {
  const meta = SOURCE_STATUS[status] || { label: status || '—', cls: 'pending', title: '' };
  return `<span class="syl-pill syl-pill--${meta.cls}" title="${esc(meta.title)}">${esc(meta.label)}</span>`;
}

function attentionFlags(list) {
  return (list || []).map((flag) => {
    if (flag === 'book_scope_missing') {
      return '<span class="syl-flag" title="Livro sem recorte: o founder precisa indicar capítulos ou páginas antes da ingestão.">scope?</span>';
    }
    return `<span class="syl-flag" title="${esc(flag)}">${esc(String(flag).replaceAll('_', ' '))}</span>`;
  }).join('');
}

/* ---------- diff markup (shared: upload result + detail banner) ---------- */

function diffGroup(label, cls, items) {
  const entries = items || [];
  if (!entries.length) {
    return `<div class="syl-diff__group--empty"><span class="syl-diff__count syl-diff__count--${cls}">0</span>${label}</div>`;
  }
  const list = entries.map((item) => (
    `<li><span class="syl-diff__week">Semana ${weekLabel(item.week)}</span>${esc(item.title)}</li>`
  )).join('');
  return `<details class="syl-diff__group"><summary><span class="syl-diff__count syl-diff__count--${cls}">${entries.length}</span>${label}</summary><ul>${list}</ul></details>`;
}

function diffMarkup(diff) {
  if (!diff) return '';
  return `<div class="syl-diff">
    ${diffGroup('Itens adicionados', 'added', diff.added)}
    ${diffGroup('Itens removidos', 'removed', diff.removed)}
    ${diffGroup('Itens alterados', 'changed', diff.changed)}
  </div>`;
}

/* ---------- list view ---------- */

function uploadResultMarkup() {
  if (state.uploadError) {
    return `<div class="syl-upload-result syl-upload-result--error" role="alert">${esc(state.uploadError)}</div>`;
  }
  const result = state.uploadResult;
  if (!result) return '';
  if (result.unchanged) {
    return `<div class="syl-upload-result">
      <div class="syl-upload-result__head">
        <span class="syl-result-badge syl-result-badge--unchanged">Planilha inalterada</span>
        <a class="syl-upload-result__open" href="/syllabi?id=${encodeURIComponent(result.syllabus_id)}">Abrir syllabus</a>
      </div>
      <p class="syl-upload-result__note">O conteúdo é idêntico à versão atual — nenhuma versão foi criada.</p>
    </div>`;
  }
  return `<div class="syl-upload-result">
    <div class="syl-upload-result__head">
      <span class="syl-result-badge syl-result-badge--new">Nova versão registrada</span>
      <a class="syl-upload-result__open" href="/syllabi?id=${encodeURIComponent(result.syllabus_id)}">Abrir syllabus</a>
    </div>
    <p class="syl-upload-result__note">A versão foi registrada e comparada com a anterior. Nada foi executado — ingestão e demais estágios continuam sob seu comando.</p>
    ${diffMarkup(result.diff)}
  </div>`;
}

function uploadPanelMarkup() {
  const busy = state.uploading;
  const dropBody = busy
    ? `<div class="syl-progress"><span class="syl-progress__track"><span class="syl-progress__bar"></span></span>Enviando e comparando a planilha…</div>`
    : `${ICON.upload}
      <p><strong>Arraste a planilha .xlsx aqui</strong> ou selecione o arquivo no computador.</p>
      <label class="button syl-drop__pick">Escolher arquivo
        <input class="sr-only" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" data-file>
      </label>`;
  return `<section class="panel syl-upload" aria-labelledby="syl-upload-title">
    <div class="syl-upload__head">
      <h2 id="syl-upload-title">Enviar planilha</h2>
      <p>O envio registra uma nova versão do syllabus e mostra o que mudou em relação à anterior. Nenhum processamento é disparado a partir daqui.</p>
    </div>
    <div class="syl-drop${busy ? ' is-busy' : ''}" data-drop${busy ? ' aria-busy="true"' : ''}>${dropBody}</div>
    ${uploadResultMarkup()}
  </section>`;
}

function syllabusCard(syllabus) {
  const versions = [...(syllabus.versions || [])].sort((a, b) => (b.seq || 0) - (a.seq || 0));
  const latest = versions[0];
  const count = versions.length;
  return `<a class="panel syl-card" href="/syllabi?id=${encodeURIComponent(syllabus.id)}">
    <div class="syl-card__main">
      <h2>${esc(syllabus.title)}</h2>
      <p class="syl-card__meta">${count} ${count === 1 ? 'versão' : 'versões'} · última em ${esc(fmtDateShort(latest?.created_at))}</p>
    </div>
    <dl class="syl-card__facts">
      <div><dt>Itens</dt><dd>${latest?.item_count ?? '—'}</dd></div>
      <div><dt>Fontes</dt><dd>${latest?.source_count ?? '—'}</dd></div>
    </dl>
    ${ICON.chevronRight}
  </a>`;
}

function renderList() {
  document.title = 'Syllabi · Concept Universe';
  headingHost.innerHTML = `<div>
    <h1>Syllabi</h1>
    <p class="admin-page__intro">Cada planilha enviada vira uma versão registrada do módulo. O envio apenas registra e compara — nada é executado.</p>
  </div>`;
  let listMarkup;
  if (state.listError) {
    listMarkup = `<div class="syl-error">Não foi possível carregar os syllabi: ${esc(state.listError)}
      <button class="button" type="button" data-retry>Tentar de novo</button></div>`;
  } else if (!state.syllabi.length) {
    listMarkup = '<div class="syl-empty">Nenhum syllabus registrado ainda.<br>Envie a primeira planilha .xlsx acima para começar.</div>';
  } else {
    listMarkup = `<p class="syl-list__label">Syllabi registrados</p>
      <div class="syl-list">${state.syllabi.map(syllabusCard).join('')}</div>`;
  }
  viewHost.setAttribute('aria-busy', 'false');
  viewHost.innerHTML = `${uploadPanelMarkup()}${listMarkup}`;
}

async function loadList({ silent = false } = {}) {
  try {
    const response = await fetch('/api/syllabi', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`o servidor respondeu ${response.status}`);
    const payload = await response.json();
    state.syllabi = payload.syllabi || [];
    state.listError = null;
  } catch (error) {
    state.listError = error.message;
    if (!silent) announce('Falha ao carregar os syllabi.');
  }
  renderList();
}

async function uploadFile(file) {
  if (!file || state.uploading) return;
  state.uploadResult = null;
  state.uploadError = null;
  if (!/\.xlsx$/i.test(file.name)) {
    state.uploadError = `“${file.name}” não é uma planilha .xlsx. Apenas workbooks .xlsx são aceitos.`;
    announce('Arquivo recusado: apenas .xlsx.');
    renderList();
    return;
  }
  state.uploading = true;
  announce(`Enviando ${file.name}…`);
  renderList();
  try {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch('/api/syllabi/upload', { method: 'POST', body: form });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(typeof body?.detail === 'string' && body.detail
        ? body.detail : `o servidor respondeu ${response.status}`);
    }
    state.uploadResult = body;
    announce(body.unchanged
      ? 'Planilha inalterada — nenhuma versão criada.'
      : 'Nova versão registrada. Nada foi executado.');
    state.uploading = false;
    await loadList({ silent: true });
    return;
  } catch (error) {
    state.uploadError = `Não foi possível processar a planilha: ${error.message}`;
    announce('Falha no envio da planilha.');
  }
  state.uploading = false;
  renderList();
}

/* ---------- detail view ---------- */

function sortedVersions(detail) {
  return [...(detail.versions || [])].sort((a, b) => (b.seq || 0) - (a.seq || 0));
}

function selectedVersion(detail) {
  const versions = sortedVersions(detail);
  return versions.find((version) => version.id === state.selectedVersionId) || versions[0] || null;
}

function versionMetaMarkup(detail) {
  const version = selectedVersion(detail);
  if (!version) return '';
  const parts = [
    `v${version.seq ?? '—'}`,
    version.origin ? esc(version.origin) : null,
    version.file_name ? esc(version.file_name) : null,
    esc(fmtDate(version.created_at)),
    `${version.item_count ?? '—'} itens`,
    `${version.source_count ?? '—'} fontes`,
  ].filter(Boolean);
  const isLatest = version.id === detail.latest?.version_id;
  const note = isLatest ? '' : '<span class="syl-version-note">A visualização por semana abaixo mostra sempre a versão mais recente.</span>';
  return `${parts.join(' · ')}${note}`;
}

function detailHeadingMarkup(detail) {
  const versions = sortedVersions(detail);
  const options = versions.map((version) => {
    const selected = version.id === selectedVersion(detail)?.id ? ' selected' : '';
    const label = [`v${version.seq ?? '—'}`, version.file_name || version.origin || '', fmtDateShort(version.created_at)]
      .filter(Boolean).join(' · ');
    return `<option value="${esc(version.id)}"${selected}>${esc(label)}</option>`;
  }).join('');
  return `<div>
    <a class="syl-back" href="/syllabi">${ICON.back}Syllabi</a>
    <h1>${esc(detail.title)}</h1>
    <p class="syl-version-meta" data-version-meta>${versionMetaMarkup(detail)}</p>
    ${groupLineMarkup()}
  </div>
  <div class="workspace__actions">
    <label class="syl-version-picker">
      <span>Versão</span>
      <select class="field" data-version-select aria-label="Selecionar versão do syllabus">${options}</select>
    </label>
  </div>`;
}

/* ---------- group assignment ----------
   O grupo é a autoridade de conteúdo (herdado do Companion). A atribuição é
   sempre uma escolha manual do founder: a lista vem de /api/org e nada é
   sugerido a partir de nomes de arquivo. */

function groupSelectMarkup() {
  const control = state.groupControl;
  const assigned = state.org.assigned;
  const options = state.org.groups.map((group) => {
    const selected = group.id === control.value ? ' selected' : '';
    return `<option value="${esc(group.id)}"${selected}>${esc(group.institution_name)} / ${esc(group.name)}</option>`;
  }).join('');
  const cancel = assigned
    ? `<button class="button button--quiet" type="button" data-group-cancel${control.saving ? ' disabled' : ''}>Cancelar</button>`
    : '';
  return `<div class="syl-group__form">
    <select class="field syl-group__select" data-group-select aria-label="Grupo do syllabus"${control.saving ? ' disabled' : ''}>
      <option value="">Escolher grupo…</option>
      ${options}
    </select>
    <button class="button button--primary" type="button" data-group-save${control.saving ? ' disabled' : ''}>${control.saving ? 'Salvando…' : 'Salvar'}</button>
    ${cancel}
    ${control.error ? `<p class="syl-group__error" role="alert">${esc(control.error)}</p>` : ''}
  </div>`;
}

function groupLineMarkup() {
  if (state.org.error) {
    return `<p class="syl-group syl-group--muted">Não foi possível carregar os grupos: ${esc(state.org.error)}</p>`;
  }
  const assigned = state.org.assigned;
  if (assigned && !state.groupControl.selecting) {
    return `<p class="syl-group">
      <span class="syl-group__label">Grupo:</span>
      <strong>${esc(assigned.institution_name)} / ${esc(assigned.group_name)}</strong>
      <button class="syl-group__change" type="button" data-group-change>Alterar</button>
    </p>`;
  }
  if (!state.org.groups.length) {
    return `<p class="syl-group syl-group--muted">Sem grupo — <a href="/structure">crie um grupo em Structure</a> para poder atribuir este syllabus.</p>`;
  }
  return `<div class="syl-group">
    <span class="syl-group__label">${state.org.assigned ? 'Grupo:' : 'Atribuir a um grupo:'}</span>
    ${groupSelectMarkup()}
  </div>`;
}

function flattenGroups(institutions) {
  const groups = [];
  for (const institution of institutions || []) {
    for (const group of institution.groups || []) {
      groups.push({
        id: group.id,
        name: group.name,
        institution_id: institution.id,
        institution_name: institution.name,
      });
    }
  }
  return groups;
}

function assignedGroupOf(institutions, syllabusId) {
  for (const institution of institutions || []) {
    for (const group of institution.groups || []) {
      if ((group.syllabi || []).some((entry) => entry.id === syllabusId)) {
        return {
          group_id: group.id,
          group_name: group.name,
          institution_id: institution.id,
          institution_name: institution.name,
        };
      }
    }
  }
  return null;
}

async function loadOrg(syllabusId) {
  try {
    const response = await fetch('/api/org', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`o servidor respondeu ${response.status}`);
    const payload = await response.json();
    state.org.groups = flattenGroups(payload.institutions);
    state.org.assigned = assignedGroupOf(payload.institutions, syllabusId);
    state.org.error = null;
  } catch (error) {
    state.org = { groups: [], assigned: null, error: error.message };
  }
}

async function saveGroup() {
  const control = state.groupControl;
  if (control.saving || !state.detail) return;
  control.value = $('[data-group-select]')?.value || '';
  if (!control.value) {
    control.error = 'Escolha um grupo antes de salvar.';
    renderDetail();
    return;
  }
  control.saving = true;
  control.error = null;
  renderDetail();
  try {
    const response = await fetch(`/api/syllabi/${encodeURIComponent(state.detail.id)}/assign-group`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ group_id: control.value }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(typeof body?.detail === 'string' && body.detail
        ? body.detail : `o servidor respondeu ${response.status}`);
    }
    state.org.assigned = {
      group_id: body.group_id,
      group_name: body.group_name,
      institution_id: body.institution_id,
      institution_name: body.institution_name,
    };
    state.groupControl = { selecting: false, saving: false, error: null, value: '' };
    announce(`Syllabus atribuído ao grupo ${body.group_name} (${body.institution_name}).`);
  } catch (error) {
    control.saving = false;
    control.error = `Não foi possível salvar: ${error.message}`;
  }
  renderDetail();
}

function startGroupChange() {
  state.groupControl = {
    selecting: true,
    saving: false,
    error: null,
    value: state.org.assigned?.group_id || '',
  };
  renderDetail();
}

function cancelGroupChange() {
  if (state.groupControl.saving) return;
  state.groupControl = { selecting: false, saving: false, error: null, value: '' };
  renderDetail();
}

function diffBannerMarkup(detail) {
  if (!detail.diff || state.diffDismissed) return '';
  const versions = sortedVersions(detail);
  const previous = versions.find((version) => version.id === detail.diff.vs_version_id);
  const versus = previous ? `em relação à v${previous.seq}` : 'em relação à versão anterior';
  return `<section class="syl-banner" aria-label="Mudanças desta versão">
    <div class="syl-banner__head">
      <div><strong>O que mudou nesta versão</strong><span>Diferenças ${esc(versus)}. Só o registro mudou — nada foi executado.</span></div>
      <button class="button button--quiet" type="button" data-dismiss-diff>Dispensar</button>
    </div>
    ${diffMarkup(detail.diff)}
  </section>`;
}

function topicsOf(item) {
  const raw = item.assuntos ?? item.topics ?? null;
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.filter(Boolean).map(String);
  return String(raw).split(/[;,]/).map((part) => part.trim()).filter(Boolean);
}

function safeUrl(url) {
  if (!url) return null;
  try {
    const parsed = new URL(url, window.location.origin);
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed : null;
  } catch {
    return null;
  }
}

/* ---------- inline editing (curation) ----------
   Uma correção nunca sobrescreve o fato importado da planilha: o POST
   registra um evento de curadoria e devolve o item efetivo (planilha +
   edições por cima), que substitui o item na tela sem recarregar a página. */

const FIELD_LABEL = { title: 'Título', url: 'URL', description: 'Descrição' };

function historyKey(itemId, field) {
  return `${itemId} ${field}`;
}

function isEditing(itemId, field) {
  return Boolean(state.editing && state.editing.itemId === itemId && state.editing.field === field);
}

function findItem(itemId) {
  for (const week of state.detail?.latest?.weeks || []) {
    const match = (week.items || []).find((item) => item.id === itemId);
    if (match) return match;
  }
  return null;
}

function pencilButton(item, field) {
  const label = `Editar ${FIELD_LABEL[field].toLowerCase()} de “${esc(item.title)}”`;
  return `<button class="syl-edit__pencil" type="button" data-edit-start data-edit-item="${esc(item.id)}" data-edit-field="${field}" title="Editar ${FIELD_LABEL[field].toLowerCase()}" aria-label="${label}">${ICON.pencil}</button>`;
}

function editedMarker(item, field) {
  if (!item.edited?.[field]) return '';
  const open = state.historyOpen.has(historyKey(item.id, field));
  return `<button class="syl-edit__marker${open ? ' is-open' : ''}" type="button" data-edit-marker data-edit-item="${esc(item.id)}" data-edit-field="${field}" aria-expanded="${open}" title="Campo editado — clique para ver o histórico e o valor original da planilha">editado</button>`;
}

function historyMarkup(item, field) {
  if (!state.historyOpen.has(historyKey(item.id, field))) return '';
  const edits = (item.edits || []).filter((edit) => edit.field === field);
  if (!edits.length) return '';
  const original = edits[edits.length - 1]; // mais antigo: o "old" é o valor da planilha
  const rows = edits.map((edit) => `<li>
      <span class="syl-history__at">${esc(fmtDate(edit.at))}</span>
      <span class="syl-history__change"><s>${edit.old ? esc(edit.old) : '—'}</s> <span class="syl-history__arrow" aria-hidden="true">→</span> ${esc(edit.new)}</span>
      ${edit.note ? `<span class="syl-history__note">${esc(edit.note)}</span>` : ''}
    </li>`).join('');
  return `<div class="syl-history">
    <p class="syl-history__original"><span>Original da planilha</span>${original.old ? esc(original.old) : '<span class="muted">vazio</span>'}</p>
    <ul>${rows}</ul>
  </div>`;
}

function editFormMarkup(item, field) {
  const editing = state.editing;
  const control = field === 'description'
    ? `<textarea class="field syl-edit__input" rows="3" data-edit-input aria-label="Nova descrição">${esc(editing.value)}</textarea>`
    : `<input class="field syl-edit__input" type="text" value="${esc(editing.value)}" data-edit-input aria-label="Novo valor de ${FIELD_LABEL[field].toLowerCase()}">`;
  return `<div class="syl-edit__form">
    ${control}
    <div class="syl-edit__actions">
      <button class="button button--primary" type="button" data-edit-save${editing.saving ? ' disabled' : ''}>${editing.saving ? 'Salvando…' : 'Salvar'}</button>
      <button class="button button--quiet" type="button" data-edit-cancel${editing.saving ? ' disabled' : ''}>Cancelar</button>
      <span class="syl-edit__hint">O valor da planilha fica preservado no histórico.</span>
    </div>
    ${editing.error ? `<p class="syl-edit__error" role="alert">${esc(editing.error)}</p>` : ''}
  </div>`;
}

function editableFact(item, field, valueMarkup) {
  if (isEditing(item.id, field)) {
    return `<div class="syl-fact syl-fact--wide"><dt>${FIELD_LABEL[field]}</dt><dd class="syl-fact__value">${editFormMarkup(item, field)}</dd></div>`;
  }
  const wide = state.historyOpen.has(historyKey(item.id, field));
  return `<div class="syl-fact${wide ? ' syl-fact--wide' : ''}">
    <dt>${FIELD_LABEL[field]}</dt>
    <dd class="syl-fact__value">${valueMarkup}${pencilButton(item, field)}${editedMarker(item, field)}</dd>
    ${historyMarkup(item, field)}
  </div>`;
}

function focusEditInput() {
  const input = $('[data-edit-input]');
  if (!input) return;
  input.focus();
  const end = input.value.length;
  try { input.setSelectionRange(end, end); } catch { /* inputs sem seleção */ }
}

function startEdit(itemId, field) {
  if (state.editing?.saving) return;
  const item = findItem(itemId);
  if (!item || !(field in FIELD_LABEL)) return;
  state.editing = { itemId, field, value: item[field] || '', error: null, saving: false };
  renderDetail();
  focusEditInput();
}

function cancelEdit() {
  if (!state.editing || state.editing.saving) return;
  state.editing = null;
  renderDetail();
}

function toggleHistory(itemId, field) {
  const key = historyKey(itemId, field);
  if (state.historyOpen.has(key)) state.historyOpen.delete(key);
  else state.historyOpen.add(key);
  renderDetail();
}

function applyEffectiveItem(effective) {
  for (const week of state.detail?.latest?.weeks || []) {
    const items = week.items || [];
    const index = items.findIndex((item) => item.id === effective.id);
    if (index !== -1) {
      const { week: _week, ...fields } = effective;
      items[index] = { ...items[index], ...fields };
      return;
    }
  }
}

async function saveEdit() {
  const editing = state.editing;
  if (!editing || editing.saving) return;
  const input = $('[data-edit-input]');
  if (input) editing.value = input.value;
  const value = editing.value.trim();
  if (!value) {
    editing.error = 'O campo não pode ficar vazio.';
    renderDetail();
    focusEditInput();
    return;
  }
  const item = findItem(editing.itemId);
  if (item && value === String(item[editing.field] ?? '').trim()) {
    state.editing = null;
    renderDetail();
    announce('Nada mudou — nenhuma edição foi registrada.');
    return;
  }
  editing.saving = true;
  editing.error = null;
  renderDetail();
  try {
    const response = await fetch(`/api/syllabi/items/${encodeURIComponent(editing.itemId)}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ field: editing.field, value }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(typeof body?.detail === 'string' && body.detail
        ? body.detail : `o servidor respondeu ${response.status}`);
    }
    applyEffectiveItem(body);
    if (state.editing === editing) state.editing = null;
    announce(`${FIELD_LABEL[editing.field]} atualizado. O valor da planilha segue no histórico.`);
    renderDetail();
  } catch (error) {
    if (state.editing !== editing) {
      announce('Não foi possível salvar a edição.');
      renderDetail();
      return;
    }
    editing.saving = false;
    editing.error = `Não foi possível salvar: ${error.message}`;
    renderDetail();
    focusEditInput();
  }
}

function autoestudoDetailMarkup(item) {
  const url = safeUrl(item.url);
  const urlValue = url
    ? `<a href="${esc(url.href)}" target="_blank" rel="noopener noreferrer">${esc(url.hostname)}${ICON.external}</a>`
    : (item.url ? `<span>${esc(item.url)}</span>` : '<span class="muted">Sem URL</span>');
  const descValue = item.description
    ? `<span class="syl-fact__text">${esc(item.description)}</span>`
    : '<span class="muted">Sem descrição</span>';
  const parentFact = item.parent_title
    ? `<div><dt>Aula</dt><dd>${esc(item.parent_title)}</dd></div>` : '';
  const sourceFact = item.source_id
    ? `<div><dt>Fonte</dt><dd><a href="/sources?id=${encodeURIComponent(item.source_id)}">${esc(item.source_id)}</a></dd></div>`
    : '<div><dt>Fonte</dt><dd class="muted">Sem fonte vinculada</dd></div>';
  const topics = topicsOf(item);
  const topicsMarkup = topics.length
    ? `<div class="syl-topics"><span>Assuntos</span><div class="syl-chips">${topics.map((topic) => `<span class="syl-chip">${esc(topic)}</span>`).join('')}</div></div>`
    : '';
  return `<dl class="syl-item__facts">
      ${editableFact(item, 'title', `<span>${esc(item.title)}</span>`)}
      ${editableFact(item, 'url', urlValue)}
      ${editableFact(item, 'description', descValue)}
      ${parentFact}${sourceFact}
    </dl>
    ${topicsMarkup}`;
}

function itemMarkup(item) {
  const cls = kindClass(item.kind);
  const kindBadge = `<span class="syl-kind syl-kind--${cls}">${esc(item.kind)}</span>`;
  const duration = item.duration
    ? `<span class="syl-item__duration">${esc(item.duration)}</span>` : '';
  if (cls !== 'autoestudo') {
    if (isEditing(item.id, 'title')) {
      return `<div class="syl-item syl-item--quiet syl-item--${cls}">
        <div class="syl-item__row syl-item__row--editing">
          ${kindBadge}
          ${editFormMarkup(item, 'title')}
        </div>
      </div>`;
    }
    const history = historyMarkup(item, 'title');
    return `<div class="syl-item syl-item--quiet syl-item--${cls}">
      <div class="syl-item__row">
        ${kindBadge}
        <span class="syl-item__title">${esc(item.title)}</span>
        <span class="syl-item__side">${duration}${editedMarker(item, 'title')}${pencilButton(item, 'title')}</span>
      </div>
      ${history ? `<div class="syl-item__history">${history}</div>` : ''}
    </div>`;
  }
  const media = mediaIcon(item.media_type);
  const open = state.expanded.has(item.id);
  const detailId = `syl-item-detail-${esc(item.id)}`;
  const editedAny = item.edited && Object.values(item.edited).some(Boolean);
  const editedDot = editedAny
    ? '<span class="syl-edit__dot" title="Este item tem edições — expanda para ver o histórico">editado</span>' : '';
  return `<div class="syl-item syl-item--autoestudo${open ? ' is-open' : ''}" data-item="${esc(item.id)}">
    <button class="syl-item__row" type="button" data-toggle-item="${esc(item.id)}" aria-expanded="${open}" aria-controls="${detailId}">
      ${kindBadge}
      <span class="syl-item__title"><span class="syl-item__media" title="${esc(media.label)}">${media.icon}</span>${esc(item.title)}</span>
      <span class="syl-item__side">${duration}${editedDot}${attentionFlags(item.attention)}${statusPill(item.source_status)}${ICON.chevron}</span>
    </button>
    <div class="syl-item__detail" id="${detailId}"${open ? '' : ' hidden'}>${autoestudoDetailMarkup(item)}</div>
  </div>`;
}

function weekMarkup(week) {
  const items = [...(week.items || [])].sort((a, b) => (a.seq || 0) - (b.seq || 0));
  return `<section class="syl-week">
    <h2 class="syl-week__title">Semana ${weekLabel(week.week)}<span class="syl-week__count">${items.length} ${items.length === 1 ? 'item' : 'itens'}</span></h2>
    <div class="syl-week__items">${items.map(itemMarkup).join('')}</div>
  </section>`;
}

function renderDetail() {
  const detail = state.detail;
  if (state.detailError) {
    headingHost.innerHTML = `<div><a class="syl-back" href="/syllabi">${ICON.back}Syllabi</a><h1>Syllabus</h1></div>`;
    viewHost.setAttribute('aria-busy', 'false');
    viewHost.innerHTML = `<div class="syl-error">Não foi possível carregar o syllabus: ${esc(state.detailError)}
      <button class="button" type="button" data-retry>Tentar de novo</button></div>`;
    return;
  }
  if (!detail) return;
  document.title = `${detail.title} · Syllabi · Concept Universe`;
  headingHost.innerHTML = detailHeadingMarkup(detail);
  const weeks = detail.latest?.weeks || [];
  const module = weeks.length
    ? `<div class="syl-module">${weeks.map(weekMarkup).join('')}</div>`
    : '<div class="syl-empty">Esta versão ainda não tem itens registrados por semana.</div>';
  viewHost.setAttribute('aria-busy', 'false');
  viewHost.innerHTML = `${diffBannerMarkup(detail)}${module}`;
}

async function loadDetail(id) {
  const [detailResult] = await Promise.all([
    (async () => {
      const response = await fetch(`/api/syllabi/${encodeURIComponent(id)}`, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`o servidor respondeu ${response.status}`);
      return response.json();
    })().then((detail) => ({ detail }), (error) => ({ error })),
    loadOrg(id),
  ]);
  if (detailResult.error) {
    state.detail = null;
    state.detailError = detailResult.error.message;
    announce('Falha ao carregar o syllabus.');
  } else {
    state.detail = detailResult.detail;
    state.detailError = null;
    state.selectedVersionId = state.detail.latest?.version_id || null;
  }
  state.editing = null;
  state.groupControl = { selecting: false, saving: false, error: null, value: '' };
  renderDetail();
}

function toggleItem(button) {
  const id = button.dataset.toggleItem;
  const container = button.closest('[data-item]');
  const detail = container?.querySelector('.syl-item__detail');
  if (!container || !detail) return;
  const open = state.expanded.has(id);
  if (open) state.expanded.delete(id); else state.expanded.add(id);
  container.classList.toggle('is-open', !open);
  button.setAttribute('aria-expanded', String(!open));
  detail.hidden = open;
}

/* ---------- events ---------- */

const routeId = new URLSearchParams(window.location.search).get('id');

document.querySelector('main').addEventListener('click', (event) => {
  const editStart = event.target.closest('[data-edit-start]');
  if (editStart) { startEdit(editStart.dataset.editItem, editStart.dataset.editField); return; }
  if (event.target.closest('[data-edit-save]')) { saveEdit(); return; }
  if (event.target.closest('[data-edit-cancel]')) { cancelEdit(); return; }
  const marker = event.target.closest('[data-edit-marker]');
  if (marker) { toggleHistory(marker.dataset.editItem, marker.dataset.editField); return; }
  if (event.target.closest('[data-group-save]')) { saveGroup(); return; }
  if (event.target.closest('[data-group-change]')) { startGroupChange(); return; }
  if (event.target.closest('[data-group-cancel]')) { cancelGroupChange(); return; }
  const toggle = event.target.closest('[data-toggle-item]');
  if (toggle) { toggleItem(toggle); return; }
  const dismiss = event.target.closest('[data-dismiss-diff]');
  if (dismiss) {
    state.diffDismissed = true;
    renderDetail();
    return;
  }
  const retry = event.target.closest('[data-retry]');
  if (retry) {
    viewHost.setAttribute('aria-busy', 'true');
    if (routeId) loadDetail(routeId); else loadList();
  }
});

document.querySelector('main').addEventListener('change', (event) => {
  if (event.target.matches('[data-file]')) {
    const file = event.target.files?.[0];
    event.target.value = '';
    uploadFile(file);
    return;
  }
  if (event.target.matches('[data-group-select]')) {
    state.groupControl.value = event.target.value;
    if (state.groupControl.error) {
      state.groupControl.error = null;
      renderDetail();
    }
    return;
  }
  if (event.target.matches('[data-version-select]')) {
    state.selectedVersionId = event.target.value;
    const meta = $('[data-version-meta]');
    if (meta && state.detail) meta.innerHTML = versionMetaMarkup(state.detail);
  }
});

document.querySelector('main').addEventListener('keydown', (event) => {
  if (!event.target.matches('[data-edit-input]')) return;
  if (event.key === 'Enter' && event.target.tagName !== 'TEXTAREA') {
    event.preventDefault();
    saveEdit();
  } else if (event.key === 'Escape') {
    cancelEdit();
  }
});

document.querySelector('main').addEventListener('dragover', (event) => {
  const zone = event.target.closest('[data-drop]');
  if (!zone || state.uploading) return;
  event.preventDefault();
  zone.classList.add('is-drag');
});

document.querySelector('main').addEventListener('dragleave', (event) => {
  const zone = event.target.closest('[data-drop]');
  if (zone && !zone.contains(event.relatedTarget)) zone.classList.remove('is-drag');
});

document.querySelector('main').addEventListener('drop', (event) => {
  const zone = event.target.closest('[data-drop]');
  if (!zone) return;
  event.preventDefault();
  zone.classList.remove('is-drag');
  if (state.uploading) return;
  uploadFile(event.dataTransfer?.files?.[0]);
});

if (routeId) loadDetail(routeId); else loadList();
