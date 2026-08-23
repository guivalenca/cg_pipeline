// Structure — the founder's organizational tree: institutions -> courses and
// groups, each group listing the syllabi assigned to it. Everything on this
// page is created manually through the forms below; nothing is ever derived
// from a file name, and a syllabus only joins a group when the founder
// assigns it on the Syllabi page.

const $ = (selector, root = document) => root.querySelector(selector);

const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
}[char]));

const state = {
  institutions: [],
  loadError: null,
};

const viewHost = $('[data-view]');

function announce(message) {
  $('[data-status]').textContent = message;
}

/* ---------- markup ---------- */

function institutionFormMarkup() {
  return `<form class="panel org-create" data-add-institution novalidate>
    <div class="org-create__head">
      <h2>New institution</h2>
      <p>The slug is the institution's permanent id: lowercase letters, digits and hyphens, starting with a letter — for example <code>inteli</code>.</p>
    </div>
    <div class="org-form">
      <input class="field org-form__slug" type="text" name="slug" placeholder="slug" autocomplete="off" spellcheck="false" aria-label="Institution slug">
      <input class="field org-form__name" type="text" name="name" placeholder="Institution name" autocomplete="off" aria-label="Institution name">
      <button class="button button--primary" type="submit">Create institution</button>
    </div>
    <p class="org-form__error" role="alert" data-error hidden></p>
  </form>`;
}

function courseListMarkup(institution) {
  const courses = institution.courses || [];
  if (!courses.length) {
    return '<p class="org-none">No courses yet.</p>';
  }
  return `<ul class="org-courses">${courses.map((course) => (
    `<li><span class="org-courses__name">${esc(course.name)}</span><code class="org-id">${esc(course.id)}</code></li>`
  )).join('')}</ul>`;
}

function lessonSubjectListMarkup(institution) {
  const subjects = institution.lesson_subjects || [];
  if (!subjects.length) {
    return '<p class="org-none">No Lesson Subjects yet.</p>';
  }
  return `<ul class="org-subjects">${subjects.map((subject) => (
    `<li>
      <form class="org-subject" data-rename-subject data-subject="${esc(subject.id)}" novalidate>
        <code class="org-subject__code">${esc(subject.code)}</code>
        <input class="field" type="text" name="display_name" value="${esc(subject.display_name)}" autocomplete="off" aria-label="Display name for ${esc(subject.code)}">
        <button class="button button--quiet" type="submit">Save name</button>
        <p class="org-form__error" role="alert" data-error hidden></p>
      </form>
    </li>`
  )).join('')}</ul>`;
}

function syllabusRowMarkup(entry) {
  return `<li>
    <a class="org-syllabus" href="/syllabi?id=${encodeURIComponent(entry.id)}">
      <span class="org-syllabus__title">${esc(entry.title)}</span>
      <span class="org-syllabus__counts">${entry.item_count} ${entry.item_count === 1 ? 'item' : 'items'} · ${entry.source_count} ${entry.source_count === 1 ? 'source' : 'sources'}</span>
    </a>
  </li>`;
}

function groupMarkup(institution, group) {
  const course = (institution.courses || []).find((entry) => entry.id === group.course_id);
  const courseTag = course
    ? `<span class="org-group__course" title="Course this group teaches">${esc(course.name)}</span>`
    : '';
  const syllabi = group.syllabi || [];
  const syllabiMarkup = syllabi.length
    ? `<ul class="org-group__syllabi">${syllabi.map(syllabusRowMarkup).join('')}</ul>`
    : '<p class="org-none">No syllabus assigned yet — assign one from its page under Syllabi.</p>';
  return `<div class="org-group">
    <div class="org-group__head">
      <span class="org-group__name">${esc(group.name)}</span>
      ${courseTag}
    </div>
    ${syllabiMarkup}
  </div>`;
}

function courseFormMarkup(institution) {
  return `<form class="org-form" data-add-course data-institution="${esc(institution.id)}" novalidate>
    <input class="field" type="text" name="name" placeholder="New course name" autocomplete="off" aria-label="New course name for ${esc(institution.name)}">
    <button class="button" type="submit">Add course</button>
    <p class="org-form__error" role="alert" data-error hidden></p>
  </form>`;
}

function lessonSubjectFormMarkup(institution) {
  return `<form class="org-form" data-add-subject data-institution="${esc(institution.id)}" novalidate>
    <input class="field org-form__code" type="text" name="code" placeholder="Code, e.g. COM" autocomplete="off" spellcheck="false" aria-label="New Lesson Subject code for ${esc(institution.name)}">
    <input class="field" type="text" name="display_name" placeholder="Display name" autocomplete="off" aria-label="New Lesson Subject name for ${esc(institution.name)}">
    <button class="button" type="submit">Add subject</button>
    <p class="org-form__error" role="alert" data-error hidden></p>
  </form>`;
}

function groupFormMarkup(institution) {
  const options = (institution.courses || []).map((course) => (
    `<option value="${esc(course.id)}">${esc(course.name)}</option>`
  )).join('');
  return `<form class="org-form" data-add-group data-institution="${esc(institution.id)}" novalidate>
    <input class="field" type="text" name="name" placeholder="New group name" autocomplete="off" aria-label="New group name for ${esc(institution.name)}">
    <select class="field org-form__course" name="course_id" aria-label="Course for the new group (optional)">
      <option value="">No course</option>
      ${options}
    </select>
    <button class="button" type="submit">Add group</button>
    <p class="org-form__error" role="alert" data-error hidden></p>
  </form>`;
}

function institutionMarkup(institution) {
  const groups = institution.groups || [];
  const groupsMarkup = groups.length
    ? `<div class="org-groups">${groups.map((group) => groupMarkup(institution, group)).join('')}</div>`
    : '<p class="org-none">No groups yet. A group is what a syllabus is assigned to.</p>';
  return `<article class="panel org-institution">
    <header class="org-institution__head">
      <h2>${esc(institution.name)}</h2>
      <code class="org-id">${esc(institution.id)}</code>
    </header>
    <div class="org-columns">
      <section class="org-section" aria-label="Lesson Subjects of ${esc(institution.name)}">
        <p class="org-section__label">Lesson Subjects</p>
        ${lessonSubjectListMarkup(institution)}
        ${lessonSubjectFormMarkup(institution)}
      </section>
      <section class="org-section" aria-label="Courses of ${esc(institution.name)}">
        <p class="org-section__label">Courses</p>
        ${courseListMarkup(institution)}
        ${courseFormMarkup(institution)}
      </section>
      <section class="org-section" aria-label="Groups of ${esc(institution.name)}">
        <p class="org-section__label">Groups</p>
        ${groupsMarkup}
        ${groupFormMarkup(institution)}
      </section>
    </div>
  </article>`;
}

function render() {
  viewHost.setAttribute('aria-busy', 'false');
  if (state.loadError) {
    viewHost.innerHTML = `<div class="org-error">Could not load the structure: ${esc(state.loadError)}
      <button class="button" type="button" data-retry>Try again</button></div>`;
    return;
  }
  const tree = state.institutions.length
    ? state.institutions.map(institutionMarkup).join('')
    : '<div class="org-empty">Content belongs to a group: create an institution, add its groups, then assign each syllabus to its group — you create all of this manually.</div>';
  viewHost.innerHTML = `${institutionFormMarkup()}${tree}`;
}

/* ---------- data ---------- */

async function loadTree() {
  try {
    const response = await fetch('/api/org', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`the server responded ${response.status}`);
    const payload = await response.json();
    state.institutions = payload.institutions || [];
    state.loadError = null;
  } catch (error) {
    state.loadError = error.message;
    announce('Could not load the structure.');
  }
  render();
}

async function post(url, payload, method = 'POST') {
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(typeof body?.detail === 'string' && body.detail
      ? body.detail : `the server responded ${response.status}`);
  }
  return body;
}

/* ---------- forms ----------
   On failure the tree is left untouched so typed values survive: only the
   form's own error line is updated. On success the whole tree reloads. */

function showFormError(form, message) {
  const error = form.querySelector('[data-error]');
  if (!error) return;
  error.textContent = message || '';
  error.hidden = !message;
}

function setFormBusy(form, busy) {
  form.querySelectorAll('button, input, select').forEach((element) => {
    element.disabled = busy;
  });
}

async function submitForm(form, buildRequest, successMessage) {
  showFormError(form, '');
  const request = buildRequest(form);
  if (typeof request === 'string') {
    showFormError(form, request);
    return;
  }
  setFormBusy(form, true);
  try {
    const created = await post(request.url, request.payload, request.method);
    announce(successMessage(created));
    await loadTree();
  } catch (error) {
    setFormBusy(form, false);
    showFormError(form, error.message);
  }
}

function institutionRequest(form) {
  const slug = form.elements.slug.value.trim();
  const name = form.elements.name.value.trim();
  if (!slug || !name) return 'Fill in both the slug and the name.';
  return { url: '/api/org/institutions', payload: { slug, name } };
}

function courseRequest(form) {
  const name = form.elements.name.value.trim();
  if (!name) return 'Give the course a name.';
  return {
    url: '/api/org/courses',
    payload: { institution_id: form.dataset.institution, name },
  };
}

function lessonSubjectRequest(form) {
  const code = form.elements.code.value.trim();
  const displayName = form.elements.display_name.value.trim();
  if (!code || !displayName) return 'Fill in both the code and the display name.';
  return {
    url: '/api/org/lesson-subjects',
    payload: {
      institution_id: form.dataset.institution,
      code,
      display_name: displayName,
    },
  };
}

function renameLessonSubjectRequest(form) {
  const displayName = form.elements.display_name.value.trim();
  if (!displayName) return 'Give the Lesson Subject a display name.';
  return {
    url: `/api/org/lesson-subjects/${encodeURIComponent(form.dataset.subject)}`,
    method: 'PATCH',
    payload: { display_name: displayName },
  };
}

function groupRequest(form) {
  const name = form.elements.name.value.trim();
  if (!name) return 'Give the group a name.';
  return {
    url: '/api/org/groups',
    payload: {
      institution_id: form.dataset.institution,
      name,
      course_id: form.elements.course_id.value || null,
    },
  };
}

/* ---------- events ---------- */

document.querySelector('main').addEventListener('submit', (event) => {
  const form = event.target;
  event.preventDefault();
  if (form.matches('[data-add-institution]')) {
    submitForm(form, institutionRequest, (created) => `Institution “${created.name}” created.`);
  } else if (form.matches('[data-add-subject]')) {
    submitForm(form, lessonSubjectRequest, (created) => `Lesson Subject “${created.display_name}” created.`);
  } else if (form.matches('[data-rename-subject]')) {
    submitForm(form, renameLessonSubjectRequest, (updated) => `Lesson Subject ${updated.code} renamed.`);
  } else if (form.matches('[data-add-course]')) {
    submitForm(form, courseRequest, (created) => `Course “${created.name}” created.`);
  } else if (form.matches('[data-add-group]')) {
    submitForm(form, groupRequest, (created) => `Group “${created.name}” created.`);
  }
});

document.querySelector('main').addEventListener('click', (event) => {
  if (event.target.closest('[data-retry]')) {
    viewHost.setAttribute('aria-busy', 'true');
    loadTree();
  }
});

loadTree();
