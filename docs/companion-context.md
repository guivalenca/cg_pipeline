# The Companion

An adaptive AI tutoring platform that teaches students through personalized active sessions and tracks their understanding over time. This document is the canonical glossary for the domain — terms here override any near-synonyms found in code.

## Language

### Curriculum hierarchy

**Course**:
The degree program a Student is enrolled in. Course is identity and a **Placement Rule** dimension; it does not independently determine available content.
_Avoid_: program, degree, *graduação*.

**Curriculum**:
A named academic content collection that can be assigned independently from a Student's **Course**. It organizes Modules and their Subjects without making storage paths part of domain identity.
_Avoid_: course catalog, reference folder, content scope.

**Curriculum Release**:
An immutable published revision of a **Curriculum**. It fixes Module and Subject composition, exact **Concept Graph Revisions**, and associated teaching material.
_Avoid_: latest curriculum, mutable version, folder snapshot.

**Module**:
A fixed ~10-week phase within a **Curriculum Release**. A **Group Curriculum Assignment** chooses the current Module shared by Students in that Group.
_Avoid_: term, semester, phase.

**Subject**:
A teachable area within a **Module** (`computacao`, etc.). One Subject has exactly one **Concept Graph**. This is *disciplina* in PT-BR — **not** *aula*, and **not** the OOP sense of "class."
_Avoid_: class, discipline, *disciplina*, *matéria*, *aula*, topic.

**Session**:
A single tutoring execution between one authenticated User and the Companion. A Student Session carries that Student; an Admin Test Session instead carries `student_id=NULL`, uses the administrator's temporary **Admin Test Context**, and never mutates a Student Profile. A curricular Session is scoped to exactly one **Subject** and pins the exact Curriculum Release, Concept Graph Revision, and Concept Namespace used when it begins.
_Avoid_: chat, conversation, *aula*.

**Study Mode**:
The axis that determines **how a Session's concept set and path are composed** — `curricular` | `livre` | `revisao` (a `custom` value is parked for later — student pre-picks a segment). `curricular` (the default) runs one authored **Runtime Lesson** in order; `livre` lets the Student speak freely and is matched to the most fitting segment; `revisao` composes a review path from an exam's scope and the Student's **Concept Map** gaps. Orthogonal to **Lesson Mode** (which controls depth, not content selection). Defaults to `curricular`, so every pre-existing Session is `curricular` with no data migration. Student-facing umbrella label: "modo de estudo".

**Scope**: `curricular` is scoped to exactly **one Subject** (the invariant below). `livre` / `revisao` / `custom` span **all Subjects of the Student's current Module** — they may pull segments from any of that Module's **Concept Graphs**, so their session "lesson" is an ephemeral composite, not one authored **Runtime Lesson**. Future-module Subjects are out of scope.
_Avoid_: session mode (collides — retired, see Lesson Mode), session type, track, *modo de sessão*.

**Lesson Mode**:
The **depth** axis of a Session — `padrao` (Sessão Padrão) | `profundo` (Aprendizado Profundo). Selects the system prompt and how verbose the focus / lesson-context prompts are; it does **not** change which **Concepts** are taught. Orthogonal to **Study Mode**. Field: `session_spec.lesson_mode`; helpers in [app/services/runtime_graph.py](app/services/runtime_graph.py).
_Avoid_: session mode (the retired gloss — it collided with the broader notion of study type), depth setting.

### Cohorts and segmentation

**Cohort**:
A population of Students sharing a graduation year. Cohort is identity and a **Placement Rule** dimension, not curriculum authority; the **Group Curriculum Assignment** determines available content and current Module.
_Avoid_: class, generation, year (unqualified — use **Academic Year** for the derived 1–4 label), conflating with **Turma**.

**Academic Year**:
The derived 1–4 label of a **Cohort** (`year_number`). Student-facing as "1º ano", "2º ano". Distinct from `graduation_year` (the stored value) and from **Module** (the ~10-week phase within it).
_Avoid_: ano (in code), grade, level.

**Turma**:
A class section carried as Student placement metadata. It is not an independent source of curriculum authority; curricular differences belong to Groups and their Curriculum Assignments.
_Avoid_: class, section (in code use `turma_id`), cohort (that is the broader graduation-year group).

**Slice**:
The (**Module**, **Subject**) pair a Student is currently using. Module comes from the Student's Group Curriculum Assignment; Subject is an individual navigation choice that must exist in that Module's Curriculum Release.
_Avoid_: position, current pair, slice state, conflating with **Cohort** (`cohort_module` is where the cohort sits; the Slice is where the individual Student sits).

### Concepts and student state

**Source Fragment**:
An immutable, source-specific unit of knowledge preserving one idea explicitly expressed by a teaching source. It may faithfully paraphrase or condense its Evidence Span but cannot add a conclusion that requires outside knowledge or further derivation; every Fragment remains permanently available and enters at least one Concept Facet.
_Avoid_: source concept, merged concept, disposable extraction.

**Evidence Span**:
The exact contiguous lines in an immutable Source Revision that directly support a Source Fragment. A reviewer must be able to validate the complete Fragment from this span without additional domain reasoning.
_Avoid_: fragment, model rationale, inferred evidence.

**Concept Facet** (short form: **Facet**):
A simple rectifying grouping of Source Fragments that make essentially the same semantic contribution. A Facet is necessarily part of a Teachable Concept and is not independently selected for a Lesson or treated as a mastery unit.
_Avoid_: lesson selection, topic, independent concept, digest.

**Teachable Concept** (short form: **Concept**):
A granular, reusable, platform-owned unit of learning composed of one or more Concept Facets. Lessons select Concepts for teaching and assessment; a Concept exists independently of any single Source, Course, Module, Subject, or Institution.
_Avoid_: topic, item, source fragment, merged summary, subject (in the Companion, "Subject" is reserved for the curriculum level above this one).

**Composite Concept** (short form: **Composite**):
A greater learning idea composed of multiple Teachable Concepts. Evidence of mastery over its component Concepts contributes to an aggregate judgment of mastery over the Composite.
_Avoid_: facet, lesson concept, simple topic label.

**Concept Digest**:
An informational, versioned, source-backed teaching snapshot of a Teachable Concept, derived from its Facets and supporting Source Fragments. It is recomputable and is not part of the concept universe's relationship structure.
_Avoid_: canonical concept, merged concept, source of truth, graph node.

**Concept Graph**:
The curriculum for one **Subject** — an ordered list of Concepts plus dependency edges between them. It has stable logical identity independent from artifact storage and is read-only at runtime.
_Avoid_: syllabus, curriculum, plan, lesson plan.

**Concept Graph Revision**:
An immutable published revision of a **Concept Graph**, referenced by stable ID from a Curriculum Release and pinned by every Session that uses it.
_Avoid_: graph file, latest graph, path version.

**Concept Namespace**:
The stable identity prefix connecting Concepts in a **Concept Graph Revision** to Concept States in Student Concept Maps. It is explicit and never inferred from an artifact path.
_Avoid_: folder key, graph path, implicit namespace.

**Runtime Lesson**:
In `runtime_graph.v0` Concept Graphs, a student-facing lesson made of ordered teachable segments. Students select a Runtime Lesson, not individual Concepts; the runtime advances through opening, teaching focuses, synthesis, and then ends with the standard post-session evaluation.
_Avoid_: preset, concept selection, day preset.

**Intro Note**:
A pre-lesson preview of a **Runtime Lesson**, shipped as reference data (`intro_notes.json`) alongside the **Concept Graph**. Shown to the student before their first **Session** on that lesson. Student-facing label: "Prévia da aula".
_Avoid_: preview (unqualified), intro (unqualified), *prévia* (in code).

**Lesson Progression**:
The state machine that moves a `runtime_graph.v0` **Session** through its **Runtime Lesson**: which boundary tool the tutor may call per phase, how a model result is classified at a boundary (opening completion, focus transition, protocol recovery/violation), and the **Session State** mutations each transition performs (phase flips, pending-checkpoint lifecycle, segment advancement, hidden-context engineering). Owned by [app/services/lesson_progression.py](app/services/lesson_progression.py); the session service orchestrates LLM calls and persistence around it.
_Avoid_: v0 logic (unqualified), boundary handling, checkpoint engine.

**Concept Map**:
A Student's per-Concept state of knowledge across **Concept Graphs**, keyed by Concept Namespace plus Concept identity. It holds status, confidence, evidence, and the **Concept Evaluation Observation** produced by evaluation.
_Avoid_: progress, scoreboard, mastery map.

**Concept State**:
The value stored in the **Concept Map** for a single Concept: Confidence, Concept Status, evidence summary, and Concept Evaluation Observation. One Concept State per Concept per Student.
_Avoid_: score, entry, record.

**Concept Evaluation Observation**:
The evaluator's pedagogical observation about how a Student handled one Concept in a Session. It is distinct from evidence, the Student-facing Study Sheet, and the human-authored Internal Note.
_Avoid_: source notes, model notes, internal note.

**Confidence**:
A float in `[0.0, 1.0]` representing the model's best estimate, after the most recent **Session**, of how well the student understands a **Concept**. The numerical signal — fine-grained but noisy. Confidence is the source of truth for the assessed strength of a Concept.

**Concept Status**:
A coarse bucket — `unseen`, `weak`, `shaky`, `solid` — categorizing the student's grasp of a Concept. Stored as `concept_map[id].concept_status`. Derived by the system from **Confidence** using these bands: `0.00–0.30 → weak`, `0.31–0.75 → shaky`, `0.76–1.00 → solid`; `unseen` is the default before any assessment. The post-session LLM does not emit this field. Distinct from **Session Status**.
_Avoid_: level, grade, mastery, band.

**Session Status**:
The visible lifecycle of a **Session**: in progress, paused, evaluating, evaluated, evaluation failed, or discarded. A Session becomes evaluation-eligible after completing its first segment; leaving earlier pauses it while an explicit or final too-short exit discards it.
_Avoid_: state, phase (the eval pipeline has its own **Eval Phase** concept), conflating with **Concept Status**.

**Meaningful Session Event**:
A Session lifecycle change that repositions its single card in **Activity**: start, pause, resume, discard, Evaluation start, Evaluation completion, or terminal Evaluation failure. Turns, Segment progress, cost reconciliation, Study Sheet work, and inspection are not Meaningful Session Events.
_Avoid_: activity event, audit event, message event.

**Activity**:
The administrator's one-card-per-Session view ordered by each Session's latest **Meaningful Session Event**, with in-progress Sessions integrated in “Agora” and every other Session in the dated timeline.
_Avoid_: overview, dashboard feed, recent users.

**Session State**:
The canonical in-flight state of one active **Session** — the dict held in Redis while the Session runs (and snapshotted to `session_transcripts.model_state_json` for pause/resume). Carries the paired conversation histories (`model_facing_history`, the model-facing notebook including hidden context; and `student_facing_history`, the student-facing transcript), the turn counter, model pinning, and the `runtime_graph.v0` lesson fields (`session_phase`, `pending_checkpoint`, segment progress). Sessions persisted before the rename carry the legacy `history` / `full_history` keys; `normalize_legacy_history_keys` migrates them on load (via `load_session`, the production read path over the raw Redis fetch, and in shape healing) so old snapshots resume seamlessly. Owned by [app/services/session_state.py](app/services/session_state.py), which is the sole owner of Session memory mutation: construction, legacy-key normalization, shape healing on load, the invariant-carrying turn operations (record student message, record assistant message, rollback turn), and the hidden-context / strip / prune mutations the `runtime_graph.v0` **Lesson Progression** requests all live there — no other module appends, pops, removes, prunes, or strips the histories directly. Distinct from **Session Status** (the Postgres record lifecycle).
_Avoid_: session dict, state (unqualified), conflating with **Session Status**; `history` / `full_history` (the pre-rename key names — retained only as legacy-load aliases).

**Turn**:
One full tutoring exchange within an active **Session**: student input (or a checkpoint advance) goes in, the model call(s) run, and the tutor's reply lands on the **Session State**. A Turn includes the `runtime_graph.v0` boundary decision and its follow-up bridge/closing calls, the hidden-context begin/finish steps requested by **Lesson Progression**, the leaked-boundary guards, and the in-memory rollback when a model call fails. Owned by [app/services/turn.py](app/services/turn.py) (`run_student_turn`, `run_checkpoint_advance_turn`, `run_opening_turn`), the only caller of the model adapter's `call_model` on the session path; transient-failure retry lives inside the adapter's single wire, so a turn issues one call and lets a failure propagate to roll back. The session service is the I/O shell around it (locks, idempotency, Redis/Postgres persistence, HTTP errors, streaming plumbing). `turn_count` on the Session State counts recorded student turns.
_Avoid_: message exchange, round, interaction, conflating with the HTTP request that carries it.

### Evaluation pipeline

**Evaluation Job**:
A row in `evaluation_jobs` representing one post-**Session** evaluation pass — the LLM call that reads a transcript and writes back updates to the **Concept Map**. One Evaluation Job per Session that reaches the eval stage.
_Avoid_: eval, run (overloaded), task.

**Job Status**:
The outer lifecycle of an **Evaluation Job** — `queued | running | completed | failed | dead_lettered`. Stored as `evaluation_jobs.evaluation_job_status`. Coarse, used by the worker scheduler. A non-terminal worker failure requeues the job (`queued`, `completed_at` cleared) and leaves the stream message unACKed for reclaim; `failed` is reserved for terminal failures. `dead_lettered` means the worker exhausted retries and ACKed the message out of the live stream — Postgres (`evaluation_job_status` + `error_code`/`error_detail`) is the source of truth for dead-lettered jobs; there is no separate dead-letter stream. Job Status constrains **Eval Phase**: `queued -> queued`, `running -> sending | analyzing | scoring | saving`, `completed -> done`, `failed -> failed`, `dead_lettered -> failed`.
_Avoid_: state. Always qualify as "Evaluation Job Status" or use `evaluation_job_status` in code.

**Eval Phase**:
The fine-grained, UI-facing progress state of an **Evaluation Job** — `queued | sending | analyzing | scoring | saving | done | failed`. Drives the student-visible progress indicator (Enviando → Analisando → Pontuando → Salvando). Stored on `evaluation_jobs.eval_phase`. It is partially redundant with **Evaluation Job Status**, not orthogonal to it. Distinct from the prompt analysis section and prompt scoring section below.
_Avoid_: status, stage, step.

**Model Preset**:
A named model configuration in the catalog (`model_adapter.PRESETS`) — model + thinking mode + effort level. Selection only, never wiring: presets can only combine what the registry entry's capabilities allow. Pipeline defaults are preset names in env-overridable settings (`SESSION_PRESET`, `EVAL_PRESET` in [app/config.py](app/config.py)); the notes pipeline keeps its two model-id settings (primary + repair). Admins can pin a per-session **Eval Preset** at session start (stored in `session_spec.eval_preset`, admin-only, survives retries); students always run the defaults. Each preset declares the product roles where it is selectable, so a Study Sheet preset cannot leak into evaluation. The versioned admin catalog endpoint `GET /admin/api/models` is the sole selectable-model source: it serves render-ready variants, lifecycle, role eligibility, cache semantics, capability evidence, warnings, defaults, and presets to every admin surface. Active Session status carries the pinned model and thinking mode separately from the administrator's saved draft for the next Session.
_Avoid_: model config (ambiguous), preset (unqualified — Lesson preset was a retired concept).

**Study Sheet**:
The study summary the notes worker generates after a **Session** (`session_note_jobs`) — one per Session that reaches notes generation. Rendered in the post-session modal and stacked on the **Runtime Lesson** afterwards. "Session notes" in pipeline code refers to the same artifact; **Study Sheet** is the canonical term. Student-facing label: "Folha de estudos" — the legacy on-lesson label "Anotações" was retired (2026-06-11).
_Avoid_: *anotações*, notes (unqualified).

**Prompt Analysis Section**:
The first section *inside the post-session prompt itself* — per-concept evidence analysis written in `<concept_analysis>` blocks. LLM-internal output structure, not a runtime/state concept. **Not** the same as **Eval Phase**: prompt analysis happens while the pipeline shows `eval_phase='analyzing'`.
_Avoid_: old numbered prompt labels, phase (unqualified).

**Prompt Scoring Section**:
The second section *inside the post-session prompt itself* — the JSON `<scores>` output. LLM-internal output structure, not a runtime/state concept. **Not** the same as **Eval Phase**: prompt scoring is generated inside the LLM response, then the worker enters `eval_phase='scoring'` to parse and apply the scores.
_Avoid_: old numbered prompt labels, phase (unqualified).

### Cost accounting

**Cost Event**:
An immutable, idempotent observation of one provider charge or zero-charge execution, carrying its product operation, actor, Student, Session or Job, model, provider, native currency, and event-time BRL reconciliation facts.
_Avoid_: usage row, invoice line, mutable total.

**Cost Operation**:
The extensible product work that incurred a Cost Event, grouped under a stable Cost Category such as tutoring, Evaluation, Study Sheet, Intro Note, Concept Graph, or Session Compression.
_Avoid_: model (a model is provenance), pipeline (unless naming the actual pipeline), generic execution.

**Cost Reconciliation State**:
Whether a Cost Event is `pending`, `zero_charge`, or `reconciled`. Absence of trustworthy instrumentation is not a zero-cost event and is represented separately as unavailable coverage.
_Avoid_: cost status, missing cost, assumed zero.

**Cost Coverage**:
The date from which one Cost Category is known to emit complete Cost Events. A category without Cost Coverage is visibly unavailable (`--`) rather than hidden or reported as zero.
_Avoid_: partial total, inferred coverage, no activity.

### Identity and accounts

> User is identity, Membership is institutional affiliation, Placement is Group assignment, and Student Profile is learning memory. None substitutes for another.

**User**:
A person's authenticated identity and account-setup state. A User may be a Student or an administrator; access and curriculum are derived elsewhere.
_Avoid_: account, login.

**Institution**:
A paying institutional partner, such as Inteli, containing Memberships and Groups. Its lifecycle affects every descendant without erasing each Group or Student's own local lifecycle.
_Avoid_: organization, tenant, client.

**Lifecycle State**:
The operational availability of an Institution, Group, or Student account: **active**, **paused**, or **archived**. Paused blocks study but preserves login and read access; archived removes active operation and Student login while preserving restorable data. Deletion is separate and irreversible.
_Avoid_: suspended, disabled, deleted (unless deletion is intended), status (unqualified).

**Access Group** (short form: **Group**):
A named Student population inside one Institution. It owns one Lifecycle State, one Placement Rule, and exactly one shared Curriculum Assignment.
_Avoid_: cohort (that's the graduation-year concept), class, plan.

**Group Placement Rule** (short form: **Placement Rule**):
The criteria that automatically assign a Student to a Group, initially one graduation year plus a set of Courses, with either dimension optionally unrestricted. Rules in one Institution must be disjoint or strictly nested; the narrowest matching rule wins.
_Avoid_: sort keys, priority, first-created wins, auto-sort rule.

**Group Placement** (short form: **Placement**):
The actual assignment of a Student to a Group, recorded as automatic or manual. Manual Placement remains pinned until an administrator explicitly returns it to automatic placement.
_Avoid_: membership, inferred group, silent override, temporary group.

**Placement Exception**:
A manual Placement whose Student does not match the Group's current Placement Rule. It is a visible intentional exception, not an invalid Membership.
_Avoid_: placement error, mismatch (unqualified).

**Group Curriculum Assignment** (short form: **Curriculum Assignment**):
The shared academic configuration of one Group: one exact immutable Curriculum Release plus its current Module. Every available Subject and Concept Graph Revision derives from that pair.
_Avoid_: academic rules, academic context, curriculum exception, per-Student module.

**Institution Membership** (short form: **Membership**):
The pending, approved, or rejected affiliation decision between a Student and an Institution. Membership does not select a Group or curriculum; Student Group assignment is Placement, and platform administrators have no Membership.
_Avoid_: subscription, enrollment, placement.

**Access**:
The derived permission to use Companion. It combines account setup, Membership approval, a valid current Placement when approval requires one, the Student's Lifecycle State, and the effective Institution and Group lifecycles; it is never a payment state or expiry window.
_Avoid_: subscription status, trial, paywall, access window.

**Admin Test Context**:
A temporary Group selection made by an administrator in Settings. Chat inherits that Group's academic characteristics without changing the administrator's identity, Membership, or Placement.
_Avoid_: admin placement, impersonation, permanent module override.

**Student**:
A User in the learner role, carrying Course identity, one Institution Membership, and one current Group Placement. Admins are Users but not Students.
_Avoid_: learner, pupil, *aluno* (in code).

**Student Profile** (short form: **Profile**):
A Student's learning memory, including their Concept Map and longitudinal learning state. User says who the person is; Profile says what the Student knows.
_Avoid_: account state, user data, scoreboard.

**Internal Note**:
One team-private, human-authored Markdown document about a Student, with immutable revision history. It is distinct from evaluation evidence, Concept Evaluation Observation, and the Student-facing Study Sheet.
_Avoid_: source notes, evaluation observation, study notes.

### Domain-qualified state fields

Persisted state machines use domain-qualified field names such as Account Status, Session Status, Evaluation Job Status, Lifecycle State, and Concept Status. Bare `status` is reserved for protocol-level or already-scoped external payloads.

### UI Lexicon

Student-facing copy is PT-BR and intentionally does not use the English domain terms. These are the canonical UI labels — new UI copy must use them; code keeps using the domain terms. The _Avoid_ lists above ban these PT-BR words **in code**, not in UI copy.

| Domain term | Student-facing label |
|---|---|
| Course | curso |
| Module | módulo |
| Subject | matéria |
| Runtime Lesson | aula |
| Session | sessão |
| Study Mode (umbrella) | modo de estudo |
| Study Mode `curricular` | _(TBD)_ |
| Study Mode `livre` | _(TBD)_ |
| Study Mode `revisao` | _(TBD)_ |
| Lesson Mode `padrao` | Sessão Padrão |
| Lesson Mode `profundo` | Aprendizado Profundo |
| Concept | conceito |
| Study Sheet | Folha de estudos |
| Intro Note | Prévia da aula |
| Runtime Lesson segment `self_studies` | Autoestudos |
| Lesson Progression (in-session progress view) | Mapa da aula |

## Relationships

- A **Curriculum** has immutable **Curriculum Releases**; each Release contains Modules, Subjects, and exact Concept Graph Revisions.
- Source Fragments are rectified into Concept Facets; every Facet necessarily belongs to a Teachable Concept, and every Concept contains one or more Facets.
- Lessons select Teachable Concepts, not Facets; evidence over those Concepts may later contribute to mastery of a Composite Concept.
- A Teachable Concept has versioned Concept Digests derived from its Facets and supporting Source Fragments; Source Fragments remain the durable evidence beneath every Digest.
- An **Institution** has Memberships and Groups. A Student's Membership identifies institutional affiliation; their separate Placement identifies the current Group.
- A **Group** owns one Placement Rule, one Curriculum Assignment, and one Lifecycle State.
- A Student takes one **Course** as identity; their Group Curriculum Assignment determines available content and current Module.
- A `curricular` Session engages exactly one Subject; a `livre` / `revisao` / `custom` Session may span every Subject available in the Group's current Module.
- A Concept Graph contains Concepts with dependency edges; its exact Revision and Namespace are pinned by each Session.
- A Student has one Concept Map, which holds Concept State across the Concept Graph Revisions they have encountered.
- The **Concept Graph** is curriculum (read-only reference data); the **Concept Map** is student state (mutates each Session).

## Flagged ambiguities

- **"Class"**: older code and migrations used `class_id`, `current_class`, `ClassInfo`, `CLASS_LABELS`, etc. for what this glossary calls **Subject**. Resolution: **Subject** is the canonical term; code should use `subject_id` / `subject_label`. Migration `021_rename_class_to_subject.sql` keeps already-applied databases compatible. Do not introduce the word "class" for this concept in new prompts, docs, or APIs.
- **Session duration drift**: resolved. `redis_store.py` keeps `_SESSION_TTL = 1 * 60 * 60` (a 1-hour idle/standby window, refreshed each turn) and the live prompts no longer prescribe a session length, so the LLM paces itself by conversation flow rather than a hard-coded clock. When that idle window lapses, the session is **not** lost: a rolling `model_state_json` snapshot is persisted every turn, and the next read of session state (`get_session_status` or the `/api/me/context` heartbeat) auto-transitions the orphaned `active` row to `paused` via `auto_pause_expired_sessions`, so the student resumes instead of starting over.
- **Concept Status / Confidence source of truth**: resolved. The post-session LLM emits **Confidence** only; `apply_scores` ([app/services/concept_map.py](app/services/concept_map.py)) derives **Concept Status** deterministically from Confidence. Legacy/advisory `concept_status` or `status` fields in parsed scores are ignored during merge.

## Open questions for triage

All open questions surfaced during the initial grilling pass have been resolved, captured in the glossary, or deferred as product decisions outside this register. See [docs/open-questions.md](docs/open-questions.md) for the full resolution history.
