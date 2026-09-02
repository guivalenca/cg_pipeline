const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value) => String(value ?? '').replace(/[&<>"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
}[char]));

const state = {
  index: [],
  detail: null,
  subject: 'all',
  manualSource: null,
};
const view = $('[data-view]');
const heading = $('[data-heading]');
const status = $('[data-status]');
const uploadDialog = $('[data-upload-dialog]');
const uploadForm = $('[data-upload-form]');
const manualDialog = $('[data-manual-dialog]');
const markdownDialog = $('[data-markdown-dialog]');

function announce(message, isError = false) {
  status.textContent = message || '';
  status.classList.toggle('error', isError);
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const type = response.headers.get('content-type') || '';
  const body = type.includes('json') ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = body?.detail;
    const message = typeof detail === 'string' ? detail : detail?.message;
    throw new Error(message || `Falha HTTP ${response.status}`);
  }
  return body;
}

function currentSyllabusId() {
  return new URL(window.location.href).searchParams.get('syllabus');
}

function setSyllabusInUrl(syllabusId) {
  const url = new URL(window.location.href);
  if (syllabusId) url.searchParams.set('syllabus', syllabusId);
  else url.searchParams.delete('syllabus');
  history.pushState({}, '', url);
}

function renderIndex() {
  document.title = 'Syllabi · CG Pipeline';
  heading.innerHTML = `<div><p>Syllabi</p><h1>Source Publication</h1></div><button class="primary" data-new-syllabus>Adicionar syllabus</button>`;
  if (!state.index.length) {
    view.innerHTML = '<p class="empty">Nenhum syllabus registrado.</p>';
    view.ariaBusy = 'false';
    return;
  }
  view.innerHTML = `<div class="syllabus-list">${state.index.map((item) => `
    <a class="syllabus-card" href="/syllabi?syllabus=${encodeURIComponent(item.id)}" data-open-syllabus="${esc(item.id)}">
      <div><h2>${esc(item.title)}</h2><p>${esc(item.institution?.name || 'Instituição não informada')}</p>
        <div class="pills">${(item.lesson_subjects || []).map((subject) => `<span class="pill">${esc(subject.code)} · ${esc(subject.display_name)}</span>`).join('')}</div>
      </div>
      <div><strong>${Number(item.latest?.lesson_count || 0)} aulas</strong><p>${Number(item.latest?.source_count || 0)} fontes</p></div>
    </a>`).join('')}</div>`;
  view.ariaBusy = 'false';
}

function usageMarkup(usage) {
  const openrouter = usage?.openrouter;
  const firecrawl = usage?.firecrawl;
  if (!openrouter && !firecrawl) return 'Sem uso pago registrado';
  return [
    openrouter ? `OpenRouter: US$ ${Number(openrouter.cost_usd || 0).toFixed(4)} · ${Number(openrouter.calls || 0)} chamadas` : '',
    firecrawl ? `Firecrawl: ${Number(firecrawl.extractions || 0)} extrações` : '',
  ].filter(Boolean).join(' · ');
}

function sourceStatus(source) {
  const pipeline = source.pipeline?.status || 'idle';
  const labels = {
    idle: 'Não iniciada', queued: 'Na fila', extracting: 'Adquirindo', images: 'Analisando imagens',
    cleaning: 'Limpando', attention: 'Precisa de atenção', failed: 'Falhou', ready: 'Publicada',
  };
  return labels[pipeline] || pipeline;
}

function sourceMarkup(source, lessonId) {
  const capability = source.acquisition_capability || {};
  const canAcquire = Boolean(source.source_id && capability.supported);
  return `<article class="source" data-reference-id="${esc(source.reference_id)}" data-lesson-id="${esc(lessonId)}">
    <div class="source__top"><div><h3>${esc(source.title || 'Fonte sem título')}</h3>
      <p>${esc(source.media_type || 'fonte')} · ${esc(sourceStatus(source))}${source.hidden ? ' · oculta' : ''}</p></div>
      ${source.url ? `<a href="${esc(source.url)}" target="_blank" rel="noreferrer">Abrir original</a>` : ''}
    </div>
    ${source.description ? `<p>${esc(source.description)}</p>` : ''}
    <div class="source__review">
      <label><input type="checkbox" data-review-validated ${source.review?.validated ? 'checked' : ''}> Source Publication validada</label>
      <label>Complexidade <select data-review-complexity><option value="">Não definida</option><option value="simple" ${source.review?.complexity === 'simple' ? 'selected' : ''}>Simples</option><option value="complex" ${source.review?.complexity === 'complex' ? 'selected' : ''}>Complexa</option></select></label>
    </div>
    <div class="source__actions">
      <button class="primary" data-acquire="${esc(source.source_id || '')}" ${canAcquire ? '' : 'disabled'}>Adquirir, limpar e publicar</button>
      <button data-manual="${esc(source.source_id || '')}">Usar PDF ou imagens</button>
      ${source.has_markdown ? `<button data-markdown="${esc(source.source_id)}" data-title="${esc(source.title)}">Ver publicação</button>` : ''}
      <button data-hide-source>${source.hidden ? 'Mostrar' : 'Ocultar'}</button>
      <button data-replace-source>Substituir</button>
      <button data-remove-source>Remover</button>
    </div>
  </article>`;
}

function renderDetail() {
  const detail = state.detail;
  document.title = `${detail.title} · Syllabi · CG Pipeline`;
  heading.innerHTML = `<div><button data-back>← Todos</button><h1>${esc(detail.title)}</h1></div><div class="toolbar"><button data-reupload>Reenviar XLSX</button><a href="/api/syllabi/${encodeURIComponent(detail.id)}/versions/${encodeURIComponent(detail.version.id)}/workbook"><button>Baixar XLSX</button></a></div>`;
  const subjects = detail.lesson_subjects || [];
  const lessons = (detail.lessons || []).filter((lesson) => state.subject === 'all' || lesson.subject === state.subject);
  view.innerHTML = `<section class="summary">
      <div class="summary__top"><div><strong>${esc(detail.institution?.name || 'Instituição não informada')}</strong><p>Versão ${Number(detail.version?.seq || 0)} · ${Number(detail.lessons?.length || 0)} aulas</p></div>
      <label>Lesson Subject <select data-subject-filter><option value="all">Todas</option>${subjects.map((subject) => `<option value="${esc(subject.code)}" ${state.subject === subject.code ? 'selected' : ''}>${esc(subject.code)} · ${esc(subject.display_name)}</option>`).join('')}</select></label></div>
      <ul class="identities">${(detail.export_identities || []).map((identity) => `<li><strong>${esc(identity.lesson_subject_code)}</strong><code>${esc(identity.graph_id)}</code><span>${esc(identity.display_name)}</span></li>`).join('')}</ul>
      <div class="usage">${esc(usageMarkup(detail.usage))}</div>
    </section>
    <div class="lessons">${lessons.map((lesson) => `<article class="lesson" data-lesson-id="${esc(lesson.id)}">
      <header><div><small>${esc(lesson.lesson_subject?.code || lesson.subject || '')} · semana ${esc(lesson.week || '—')}</small><h2>${esc(lesson.title)}</h2></div><span>${Number(lesson.sources?.length || 0)} fontes</span></header>
      <div class="lesson__body">${(lesson.sources || []).map((source) => sourceMarkup(source, lesson.id)).join('') || '<p class="empty">Sem autoestudos nesta aula.</p>'}</div>
    </article>`).join('') || '<p class="empty">Nenhuma aula neste filtro.</p>'}</div>`;
  view.ariaBusy = 'false';
}

async function loadIndex() {
  view.ariaBusy = 'true';
  state.index = (await request('/api/syllabi')).syllabi || [];
  renderIndex();
}

async function loadDetail(syllabusId, versionId = null) {
  view.ariaBusy = 'true';
  const query = versionId ? `?version_id=${encodeURIComponent(versionId)}` : '';
  state.detail = await request(`/api/syllabi/${encodeURIComponent(syllabusId)}${query}`);
  state.subject = 'all';
  renderDetail();
}

async function loadRoute() {
  const syllabusId = currentSyllabusId();
  if (syllabusId) await loadDetail(syllabusId);
  else await loadIndex();
}

async function openUpload({ forVersion = false } = {}) {
  uploadForm.reset();
  uploadForm.dataset.syllabusId = forVersion ? state.detail.id : '';
  $('[data-upload-eyebrow]').textContent = forVersion ? 'Nova versão' : 'Novo syllabus';
  $('[data-upload-title]').textContent = forVersion ? state.detail.title : 'Adicionar syllabus';
  uploadForm.elements.name.value = forVersion ? state.detail.title : '';
  uploadForm.elements.name.readOnly = forVersion;
  $('[data-institution-field]').hidden = forVersion;
  uploadForm.elements.institution_id.required = !forVersion;
  $('[data-upload-error]').textContent = '';
  if (!forVersion) {
    try {
      const namespace = await request('/api/companion/graph-namespace');
      uploadForm.elements.institution_id.innerHTML = '<option value="">Escolha uma instituição</option>'
        + (namespace.institutions || []).map((item) => `<option value="${esc(item.slug)}">${esc(item.name)}</option>`).join('');
      uploadForm.elements.institution_id.disabled = false;
    } catch (error) {
      $('[data-upload-error]').textContent = error.message;
    }
  }
  uploadDialog.showModal();
}

async function submitUpload(event) {
  event.preventDefault();
  const formData = new FormData(uploadForm);
  const syllabusId = uploadForm.dataset.syllabusId;
  try {
    if (syllabusId) {
      formData.delete('name');
      formData.delete('institution_id');
      const reconciliation = await request(`/api/syllabi/${encodeURIComponent(syllabusId)}/reconciliations`, { method: 'POST', body: formData });
      uploadDialog.close();
      const { mountSyllabusReconciliation } = await import('/static/syllabus_reconciliation.js?v=10');
      mountSyllabusReconciliation({
        headingHost: heading,
        viewHost: view,
        reconciliation,
        announce,
        onCancel: renderDetail,
        onApplied: async () => { announce('Nova versão publicada.'); await loadDetail(syllabusId); },
      });
      return;
    }
    const result = await request('/api/syllabi/upload', { method: 'POST', body: formData });
    uploadDialog.close();
    setSyllabusInUrl(result.syllabus_id);
    announce(result.dropped_summary?.total ? `${result.dropped_summary.total} linha(s) não curricular(es) foram ignoradas.` : 'Syllabus importado.');
    await loadDetail(result.syllabus_id);
  } catch (error) {
    $('[data-upload-error]').textContent = error.message;
  }
}

function findSourceElement(target) {
  const card = target.closest('[data-reference-id]');
  const lesson = state.detail.lessons.find((item) => String(item.id) === String(card?.dataset.lessonId));
  const source = lesson?.sources.find((item) => String(item.reference_id) === String(card?.dataset.referenceId));
  return { card, lesson, source };
}

async function saveProjection(note) {
  const result = await request(`/api/syllabi/${encodeURIComponent(state.detail.id)}/curate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ base_version_id: state.detail.version.id, lessons: state.detail.lessons, note }),
  });
  announce(result.unchanged ? 'Nenhuma mudança para salvar.' : 'Nova versão de curadoria publicada.');
  await loadDetail(state.detail.id);
}

async function patchReview(card, source) {
  const validated = $('[data-review-validated]', card).checked;
  const complexity = $('[data-review-complexity]', card).value || null;
  await request(`/api/syllabi/${encodeURIComponent(state.detail.id)}/sources/${encodeURIComponent(source.reference_id)}/review`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ validated, complexity }),
  });
  source.review = { validated, complexity };
  announce(validated ? 'Source Publication validada.' : 'Validação removida.');
}

async function acquire(sourceId) {
  await request(`/api/sources/${encodeURIComponent(sourceId)}/queue`, { method: 'POST' });
  announce('Aquisição, limpeza e publicação colocadas na fila.');
  await loadDetail(state.detail.id);
}

function openManual(sourceId, title) {
  state.manualSource = sourceId;
  $('[data-manual-title]').textContent = title || 'Usar PDF ou imagens';
  $('[data-manual-error]').textContent = '';
  $('[data-manual-form]').reset();
  manualDialog.showModal();
}

async function submitManual(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const kind = data.get('kind');
  const input = $('[data-manual-files]');
  input.multiple = kind === 'images';
  data.delete('files');
  [...input.files].forEach((file) => data.append('files', file));
  try {
    await request(`/api/sources/${encodeURIComponent(state.manualSource)}/manual-upload`, { method: 'POST', body: data });
    manualDialog.close();
    announce('Material preservado e colocado na fila.');
    await loadDetail(state.detail.id);
  } catch (error) {
    $('[data-manual-error]').textContent = error.message;
  }
}

async function openMarkdown(sourceId, title) {
  try {
    const publication = await request(`/api/sources/${encodeURIComponent(sourceId)}/markdown`);
    $('[data-markdown-heading]').textContent = title || 'Fonte';
    $('[data-markdown-body]').innerHTML = publication.html;
    markdownDialog.showModal();
  } catch (error) { announce(error.message, true); }
}

document.addEventListener('click', async (event) => {
  const open = event.target.closest('[data-open-syllabus]');
  if (open) { event.preventDefault(); setSyllabusInUrl(open.dataset.openSyllabus); await loadDetail(open.dataset.openSyllabus); return; }
  if (event.target.closest('[data-new-syllabus]')) { await openUpload(); return; }
  if (event.target.closest('[data-back]')) { setSyllabusInUrl(null); state.detail = null; await loadIndex(); return; }
  if (event.target.closest('[data-reupload]')) { await openUpload({ forVersion: true }); return; }
  const { card, lesson, source } = findSourceElement(event.target);
  if (!source) return;
  try {
    if (event.target.closest('[data-acquire]')) await acquire(source.source_id);
    else if (event.target.closest('[data-manual]')) openManual(source.source_id, source.title);
    else if (event.target.closest('[data-markdown]')) await openMarkdown(source.source_id, source.title);
    else if (event.target.closest('[data-hide-source]')) { source.hidden = !source.hidden; await saveProjection(source.hidden ? 'Fonte ocultada' : 'Fonte restaurada'); }
    else if (event.target.closest('[data-remove-source]')) { lesson.sources = lesson.sources.filter((item) => item !== source); await saveProjection('Fonte removida'); }
    else if (event.target.closest('[data-replace-source]')) {
      const url = window.prompt('URL da fonte substituta', source.url || '');
      if (!url) return;
      const title = window.prompt('Título da fonte substituta', source.title || '') || source.title;
      const replacement = { ...source, id: null, reference_id: null, source_id: null, title, url, hidden: false };
      lesson.sources.splice(lesson.sources.indexOf(source), 1, replacement);
      await saveProjection('Fonte substituída');
    }
  } catch (error) { announce(error.message, true); }
});

view.addEventListener('change', async (event) => {
  if (event.target.matches('[data-subject-filter]')) { state.subject = event.target.value; renderDetail(); return; }
  if (event.target.matches('[data-review-validated], [data-review-complexity]')) {
    const { card, source } = findSourceElement(event.target);
    try { await patchReview(card, source); } catch (error) { announce(error.message, true); }
  }
});

uploadForm.addEventListener('submit', submitUpload);
manualDialog.addEventListener('change', (event) => {
  if (!event.target.matches('input[name="kind"]')) return;
  const input = $('[data-manual-files]');
  input.value = '';
  input.multiple = event.target.value === 'images';
  input.accept = event.target.value === 'images' ? 'image/png,image/jpeg' : 'application/pdf';
});
$('[data-manual-form]').addEventListener('submit', submitManual);
$$('[data-upload-close]').forEach((button) => button.addEventListener('click', () => uploadDialog.close()));
$$('[data-manual-close]').forEach((button) => button.addEventListener('click', () => manualDialog.close()));
$$('[data-markdown-close]').forEach((button) => button.addEventListener('click', () => markdownDialog.close()));
window.addEventListener('popstate', () => loadRoute().catch((error) => announce(error.message, true)));
loadRoute().catch((error) => { view.ariaBusy = 'false'; view.innerHTML = `<p class="empty">${esc(error.message)}</p>`; });
