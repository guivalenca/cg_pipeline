# The Concept Universe: How the System Works

Purpose: the maintained design narrative for the Concept Universe. Update this
document whenever the model materially changes.

Predecessor: the earlier Fragment/Facet model, including the CG pipeline
findings and the first extraction experiment record, was kept for a while at
`docs/archive/concept-system-vision-compilation-2026-07-14-fragment-facet-model.md`
and removed from the tree on 2026-07-28; it remains available in git history.

Status convention: the body of this document states only what has been
formally decided. Anything still under design is marked "(open, see Open
Questions)" and explained in that section. Items intentionally left for future
implementation are in Deferred. Future readers: do not treat open or deferred
items as settled.

Formally closed decisions are also recorded, with their context and
consequences, as ADRs in `docs/adr/`. The v1 simplification of 2026-08-01/02
— this document's current shape — is ADR 0011: the system was deliberately
reduced to what the founder can fully own, with the deeper graph design
(`directed-precedence-graph.md` in the research archive at
`~/Desktop/concept-universe-research/`) kept as deferred ambition.

## The founding principle

The entire system rests on one distinction: **facts versus interpretations**.

A fact is something that happened and is true forever: "this source said this,
on these lines", "this student demonstrated this, on this date". Facts are
stored permanently, are never edited, and never require an AI to be right.

An interpretation is a judgment built on top of facts: "these two units
are the same knowledge", "this student has mastered this component".
Interpretations are computed, versioned, and can always be recomputed when our
models, prompts, or understanding improve.

Facts live in ledgers that only grow. Interpretations live above them and can
be rebuilt without losing history. This is what makes the system resilient:
being wrong in an interpretation costs a recomputation, never a corrupted
universe.

There are two ledgers: the **content ledger** (everything sources have taught
us) and the **student ledger** (everything students have demonstrated).
Concepts are the joint where they meet.

## Scope and phasing

The system is built in two phases (ADR 0003). Phase 1 is the universe itself:
the content ledger, extraction, Knowledge Components, Concepts, and lesson
plans. Phase 2 is the student ledger and mastery. The two meet only at KC
identity, so phase 2 attaches later without migration. During phase 1 the
Companion's current evaluation and Concept Map continue unchanged, and the
student data they accumulate is left as-is until it is reprocessed when
phase 2 lands.

Phase 1 is built externally to the Companion (ADR 0004): its own system, its
own schema, importing nothing from Companion internals. The originally
decided bridge — a disposable compiler emitting a Concept Graph in today's
format, with the Companion changing zero lines — was retired on 2026-08-02
(ADR 0004 as amended): making segments the unit the Companion consumes
changes the Companion itself (tutor ingestion, student evaluation), so the
legacy graph format will not survive as the seam. What the Companion will
actually consume is undesigned (open, see Open Questions) and depends on
the segment design.

The universe is designed as a web system operated through its admin
dashboard, built and run locally until it is wired into the Companion, then
deployed to Railway (ADR 0005 as amended). The admin dashboard is its
operating and curation surface: the founder drives the pipeline from it,
every dashboard action is recorded as a permanent curation fact, and every
creation phase boundary starts with a hard audit gate, relaxed per phase as
trust builds. The existing cg_pipeline repo is a quarry, not a foundation:
rules and adapters are ported selectively with review, and its transcribed
corpora serve as test fixtures.

## The content ingestion chain

The path a source travels, recorded as five kinds of permanent facts:

1. **Source**: the logical thing a teacher chose (an article, a video, a book
   chapter). Its identity comes from the small set of stable metadata (video
   ID, ISBN, canonical URL). Everything else about it (content, authors,
   remaining metadata) is free to change over time.
2. **Source Snapshot**: the source's material as it was at a moment in time.
   When the underlying material changes, a new snapshot is created next to the
   old one; nothing is overwritten.
3. **Artifact**: a processed form of a snapshot created for model consumption,
   typically extracted Markdown, but also transcripts or OCR output. Each
   artifact records which tool version produced it, and improved tooling
   produces new artifacts beside old ones.
4. **Model Reading**: one particular model, with one particular prompt,
   reading one artifact and reporting what it found (the passages, tasks and
   statements below). A reading is a fact about what that extractor said, even
   if the extractor was imperfect; better readings are added later, never
   substituted destructively.
5. **Syllabus**: the teacher's real input, and where sources enter the system:
   the mapping of a module's sources into days and class topics. The
   meaningful teacher signal is the day-level ordering of topics across the
   module; sources within a single day carry no order. The Syllabus is
   revisioned whenever the teacher changes it, and it is the honest record of
   how the institution actually sequenced its teaching. The received syllabus
   is the first version; when a referenced source proves unacquirable, the
   failure is recorded on the acquisition side, signaled for curation, and the
   fix (a corrected link, a replacement, an exclusion, any metadata
   correction) authors the next Syllabus version as a curation act (ADR 0006).

These five are the ingestion chain, not the whole fact layer. The fact layer
also includes session records ("this session ran on this date, against this
plan version"), the student evidence records described below, and human
curation decisions, all permanent.

A source the pipeline cannot acquire produces no snapshot and therefore no
extracted knowledge: there is no metadata-only or top-down extraction path,
because fact-layer units require passage provenance (ADR 0006). The teacher
signal is not lost; the Syllabus permanently records the assignment, and a
syllabus reference with no ingested source surfaces in the dashboard as a
visible coverage gap rather than a synthetic extraction.

## Extraction: from artifact to unitary KCs

Vocabulary, fixed by founder decision 2026-07-31: "grain" is retired. The
per-task unit is the **unitary KC**; the record backing it (task, answer,
statement, axes, provenance) is its **evidence**. Older documents and run
ledgers keep the historical term.

Extraction runs as a chain of stamped, single-question model calls (ADR
0009; ADR 0010 as amended; operational defaults per stage in
`docs/pipeline-defaults.md`), in a fixed order, each stage exactly once:

1. **Blocks** (deterministic code, no model): the artifact split into the
   units markdown already delimits. The atomic address unit; the only
   segmentation that is a fact.
2. **Passages**: a model groups adjacent blocks into the source's natural
   teaching pieces, as block ranges, never copied text. A passage cannot be
   factually wrong, only better or worse. A triage gate marks filler;
   silence is not a verdict — an unjudged passage stops the run.
3. **Tasks**: per teaching passage, with the whole source in context, a
   model writes assessment tasks — each a task plus a short answer in the
   model's own words, answerable from the source alone. Tasks are the
   extraction probe: knowledge is defined by what can test it (the KLI
   knowledge-component definition, adopted in ADR 0010).
4. **Gates**: a granularity stage splits packed tasks into parts; one blind
   revision pass repairs tasks that lean on text they cannot show; a
   triage with the source in hand catches invented referents; a substance
   gate discards pairs that are no evidence of learning. Everything
   generative happens before the gates. Discarded means discarded: volume
   is free, and the cure for a bad task is its absence.
5. **Statement**: each surviving task yields one class-neutral knowledge
   statement — the claim behind the task, worded free of the task's
   phrasing. The statement is the unit's handle and its embedding key.

The unitary KC born from one task is permanent and insert-only, and bears
the frozen id (ADR 0008). Extraction happens only for what a source
teaches, never for what it assumes; assumed background is not evidence (a
source that assumes dot products has taught us nothing about dot products).
Passages may suggest knowledge but never constrain it.

Non-textual content (a diagram, a chart) currently simply belongs to its
passage; representation and use of such assets is future work (see
Deferred).

## The axes

Every unitary KC carries two axes, each written by a single model call
(majority-of-3 voting retired 2026-08-02, ADR 0011):

- **Modality**: explain (put into words) versus do (apply to a case).
- **Knowledge type**: concept versus procedure. Fact was dropped as a class
  on 2026-07-28: no prompt detected it reliably, and any fact is learnable
  phrased as a concept.

The axes are drawn from the tutoring-systems literature, where they mark
boundaries across which knowledge does not transfer. They no longer guard
identity directly — the judge below tests transfer itself, which is what
the axes proxied. Their v1 jobs are two: pairs with different axes never
reach the judge (a "do" and an "explain" are never merge candidates, so
they are never judged), and the axes carry the instructional signal the
tutor consumes downstream, eventually superseding the Companion's older
fact/procedure/applied/conceptual teaching labels. An axis error therefore
costs a missed merge candidate or a teaching-style hint, never corrupted
identity — and axes, like every interpretation, are recomputable.

## From unitary KCs to Knowledge Components

Different sources teach the same content and produce equivalent unitary
KCs; a single source often does it twice. Equivalents resolve into one
**Knowledge Component (KC)**: the discrete, measurable unit of skill or
understanding that the whole system teaches against and measures against.
The v1 identity process (ADR 0011), whole and entire:

1. **Candidates.** Each statement is embedded (pgvector); its candidates
   are its semantic neighbors above cosine 0.70 (top 6) plus its top-5
   word-overlap neighbors. The union is deduplicated pairwise; candidates
   whose axes differ are dropped and never judged.
2. **Judging.** One model call per pair asks, in both directions, the
   surmise question: *does a learner who has genuinely mastered A
   necessarily master B?* — answered on four levels (clear yes / likely /
   unlikely / clear no), each direction on its own merits. Every verdict is
   a stamped permanent fact, judged once per pair per judge generation
   (ADR 0011 as amended): a new model or prompt version re-judges beside
   the old verdicts, and consumers read the newest verdict per pair.
3. **Committing.** Two unitary KCs are the same knowledge only when both
   directions are clear yes. A composite KC commits only when every pair
   inside it is such a double — a perfect clique, at any size. Anything
   weaker stays unmerged, and no human adjudicates content disputes.

The governing asymmetry: an uncommitted duplicate costs a redundant entry
on a dashboard; a wrong merge corrupts measurement. When in doubt, nothing
merges. The measured behavior (bench 2026-08-02): the judge's confident
core is stable across models and prompt forms, disagreement concentrates on
compound statements, and the clique rule automatically quarantines exactly
those regions by leaving them unmerged.

KCs are **derived snapshots**, recomputed from the verdict ledger; unitary
KCs bear the permanent ids (ADR 0008), and composite snapshot ids are
derived and re-mintable. Ingesting a new source is the same process run
incrementally: extract, state, embed, judge only the new candidate pairs,
recompute snapshots. Nothing global re-runs; the same KC surfacing from a
new source merges by the same rule that dedups a single source. Improving a
prompt or a model likewise never loses progress: verdicts are facts, and
every interpretation above them recomputes.

One-way implications (mastery of A carries B but not the reverse) and the
graded verdict levels are stored with everything else and consumed by
nothing in v1. They are the raw material of the future precedence map and
of the graph machinery designed in `directed-precedence-graph.md`
(research archive, `~/Desktop/concept-universe-research/`) — all deferred,
all buildable
later from the ledger without re-spending a judge call. Learning order in
v1 comes from the syllabus, the teacher's honest signal, not from the
graph.

Every KC also has a **digest**: a compact compiled teaching text built from
its members' evidence. Digests are self-contained, versioned, and recompile
when the KC's members change. They are what the tutor reads.

Every automated decision in this loop (verdicts, statements, vectors) is
stamped with the model and prompt version that produced it. Text is the
only canonical data; vectors and verdicts are derived and replayable.

## From Knowledge Components to Concepts

**Concepts** are big, human-named, vocabulary-anchored topics: Perceptron,
Bag of Words, Word2Vec. Their job is organization and readability: they let
humans (teachers, students, ourselves) properly consume the system.

A concept is made of three moving pieces, each changing at its own pace:

1. **Name**: deliberately near-frozen, changed only as an explicit curation
   act, because the name is the handle humans hold.
2. **Composition**: the set of KCs currently belonging to it, which grows as
   ingestion matches new material.
3. **Description**: a human-facing summary, occasionally recompiled when the
   contents materially change, and versioned.

A concept owns no content of its own and has no teaching authority: lessons
select KCs through the chain syllabus → sources → unitary KCs → KCs, never
through concepts. The concept is the shelf a KC is displayed on; its teaching
material is its KCs' digests, its assessment plan comes from its KCs, its
mastery is computed from its KCs' evidence, and a misfiled KC costs
readability, not learning. The process for aggregating KCs into Concepts is
undefined (open, see Open Questions).

## From Syllabus to lessons and sessions

Because the Syllabus maps sources to days, and sources yield unitary KCs,
and unitary KCs resolve into KCs, the system can determine which Knowledge
Components each class needs to teach. An LLM then assembles the **lesson
plan**: dividing the day's KCs into segments and ordering those segments. The
plan is an interpretation: computed, versioned, and recomputable as our
pipeline improves. When a session actually teaches, its session record pins
the plan version and KC digest versions it used, so taught plans are retained
as context for the evidence they produced; untaught drafts are disposable. The
rules for how segments are composed are not yet designed (open, see Open
Questions), but the consumption ladder is decided in principle: the KC is
the unit of measurement, not the unit of instruction. The tutor is never
handed a source's full KC list; it teaches a segment at a time, and the
fine-grained KC resolution exists for the evaluator, the ledger, and the
teacher's dashboard.

A session's teaching context is assembled by curated injection: the Companion
decides what enters the prompt, drawing on the selected KCs and digests and
their concept's name. This control is what guarantees curricular coverage and
instructional focus.

## The student ledger and mastery

This whole section is phase 2 (ADR 0003); it is recorded here so the design
stays whole, and the universe is built so it can attach without migration.

When a student finishes a segment, an LLM extracts **facts about the
student's learning** from the conversation: timestamped evidence records
anchored to the KCs that were exercised. These records are permanent; they are
the student ledger. The exact evaluation flow is still under discussion (open,
see Open Questions).

Mastery is then **computed, not stored as truth**: arithmetic over the
evidence ledger, costing zero tokens and recomputable at any moment. Each KC
carries a discrete state: **unseen, weak, shaky, or solid**. What exactly
promotes a KC out of "unseen" is not finalized (open, see Open Questions). The
v1 computation is counting-based; established mastery models such as Bayesian
Knowledge Tracing and Item Response Theory (which outperform LLMs at
predicting student performance) are upgrade paths that can later replace the
counting by swapping the computed view, with no data migration. The division
of labor is fixed either way: LLMs extract evidence, explicit math computes
mastery.

Concept-level mastery serves readability, through three views:

1. **Performance**: how the student does on the KCs they have seen; unmoved by
   new content.
2. **Coverage**: how much of the concept's current total they have touched;
   honestly drops when the topic grows.
3. **Score**: a combination of both, rated A through F, time-aware against the
   lesson schedule.

Not every KC weighs the same: teachers rank KCs by importance (ranking, not
numeric weights, because humans rank reliably and weigh unreliably); the
conversion from rank to weight is an implementation detail still open. Because
mastery is a view over permanent evidence, a student's demonstrated
understanding survives content changes, new sources, and reorganizations.

## Technology

The system runs on infrastructure we already operate: **Postgres** stores both
ledgers and every interpretation layer, and **pgvector**, an extension inside
it, handles the embedding search, keeping vectors and rows in the same
database under the same transactions. The universe is a web system operated
through the admin dashboard, running locally until it is wired into the
Companion and then deployed to Railway (ADR 0005 as amended). Model
calls go through one OpenRouter-compatible client, provider-stamped per
call, routed throughput-first with low-bit quantized providers excluded.

## Working method

The system is built through the harness: prompts are versioned files hashed
into each run, every run is recorded with its model and prompt stamps, and
prompt changes are evaluated by benched A/B comparison over the reference
corpus before adoption. Costs are measured per run, never estimated in
place of measurement.

On judgment quality (founder decision 2026-08-01): there is no human gold
standard. The founder does not adjudicate individual verdicts; a reference
model's verdicts are trusted until a concrete problem implicates specific
edges. Disagreement between judges locates pairs worth examining; it scores
neither judge. Flags and behavioral differences between models are treated
as information about the corpus, not noise to be optimized away (founder
decision 2026-08-02).

## Deferred to future implementation

Decided as out of scope for the initial system; the architecture keeps each
one cheap to add later because interpretations are recomputable:

- **The precedence map**: consumption of the stored one-way implications
  (learning-order structure, foundational/advanced reading of the graph).
  V1 stores the arrows and reads order from the syllabus.
- **Graph health machinery** from the directed-precedence-graph memo:
  k-plex tolerance and tension, node-health flags, the diagnostic exam
  menu, the whole-set veto gate, pendência objects, weighted disagreement
  tiebreaks, floor recalibration. Deferred whole by ADR 0011.
- **A remedy for contested "likely" verdicts** (the judge's known weak
  level); the second-model escalation tier was considered and dropped
  (founder decision 2026-08-01).
- **Concept links**: mastery flowing between related concepts (e.g. Perceptron
  feeding Neural Networks).
- **Non-textual assets**: the format, representation, and any retrieval of
  images, diagrams, and charts. Today an asset is simply part of its passage.
- **Dynamic KC boundary auditing** via learning-curve analysis over student
  evidence. Tracked as guivalenca/companion#73, label `post-concept-universe`.
- **The observer agent** for impartial evidence extraction.
- **Forgetting and retention modeling** over timestamped evidence.
- **Mastery model upgrades** beyond counting (BKT, IRT).
- **Full-rerun id reconciliation**: matching recomputed KCs back to existing
  ids when the whole interpretation layer is rebuilt with a new model or
  prompt.

## Open Questions

Each entry describes the problem, not just the question, so it can be picked
up without the original conversation. (The former open questions on the KC
membership test, unit sizing, and extraction method were closed by the
as-built pipeline and ADR 0011.)

1. **KC-to-Concept aggregation.** How are KCs assigned to concepts, and where
   do concept boundaries come from? Sketch under discussion: human vocabulary
   anchors boundaries, machines propose, curation confirms. Nothing decided.
2. **Segment composition.** Segments are the intermediary the tutor will
   consume — a per-lesson plan chunking the day's KCs into teachable groups.
   Sketch under discussion (2026-08-02): group by topic coherence, not by
   axis; the axes of a segment's KCs shape its phases (concept-explain
   opens, procedure-do closes in practice); one planning level only, no
   sub-segments. Nothing decided.
3. **Digest source weighting.** Whether a KC digest should ever emphasize the
   current lesson's own sources over other backing sources. Instinct: no for
   v1.
4. **Naming of composite KCs.** A focused call after grouping writes one
   canonical statement from the member tasks and answers. The statement
   attaches to that composite snapshot; it does not change membership or the
   permanent unitary KCs. An `unsure` result leaves the composite unnamed.
5. **The Companion seam.** The disposable compiler emitting today's Concept
   Graph format was retired as the bridge (ADR 0004 as amended, 2026-08-02):
   segments as the consumption unit change the Companion itself — tutor
   ingestion, student evaluation, and whatever else reads the graph today.
   What the Companion will consume from the universe, at what boundary, and
   how much of the Companion changes, is undesigned and depends on the
   segment design (question 2).

Phase 2 questions, parked with the student ledger (ADR 0003):

6. **Expected answers on unitary KCs.** Should the evidence carry a
   description of what a satisfactory demonstration looks like? Raised,
   unexplored.
7. **Evaluation flow.** When and how evidence is extracted at segment close,
   and by which agent.
8. **"Seen" trigger.** Leaning toward "a segment the student finished", but
   not decided.
9. **Rank-to-weight conversion.** Teachers rank KC importance; the curve
   converting rank into weight is undecided.
