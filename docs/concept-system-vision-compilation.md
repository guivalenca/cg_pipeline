# The Concept Universe: How the System Works

Purpose: the maintained design narrative for the Concept Universe. Update this
document whenever the model materially changes.

Predecessor: the earlier Fragment/Facet model, including the CG pipeline
findings and the first extraction experiment record, is preserved unchanged at
`docs/archive/concept-system-vision-compilation-2026-07-14-fragment-facet-model.md`.

Status convention: the body of this document states only what has been
formally decided. Anything still under design is marked "(open, see Open
Questions)" and explained in that section. Items intentionally left for future
implementation are in Deferred. Future readers: do not treat open or deferred
items as settled.

Formally closed decisions are also recorded, with their context and
consequences, as ADRs in `docs/adr/`.

## The founding principle

The entire system rests on one distinction: **facts versus interpretations**.

A fact is something that happened and is true forever: "this source said this,
on these lines", "this student demonstrated this, on this date". Facts are
stored permanently, are never edited, and never require an AI to be right.

An interpretation is a judgment built on top of facts: "these two grains
are the same idea", "this student has mastered this component".
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
own schema, importing nothing from Companion internals. The bridge is a
one-way, deliberately disposable compiler that emits a Concept Graph in
today's format at the seam the Companion already consumes graphs through; the
Companion changes zero lines, and exported concept ids embed universe identity
so phase-1 data remains mappable later.

The universe runs as a deployed service, not a local pipeline (ADR 0005). The
admin dashboard is its operating and curation surface: the founder drives the
pipeline from the web, every dashboard action is recorded as a permanent
curation fact, and every creation phase boundary starts with a hard audit
gate, relaxed per phase as trust builds. The existing cg_pipeline repo is a
quarry, not a foundation: rules and adapters are ported selectively with
review, and its transcribed corpora serve as test fixtures.

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
   reading one artifact and reporting what it found (the passages and
   grains below). A reading is a fact about what that extractor said, even
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
grains: there is no metadata-only or top-down extraction path, because
fact-layer grains require passage provenance (ADR 0006). The teacher
signal is not lost; the Syllabus permanently records the assignment, and a
syllabus reference with no ingested source surfaces in the dashboard as a
visible coverage gap rather than a synthetic extraction.

## Extraction: passages and grains

From an artifact, a Model Reading extracts two kinds of units.

**Passages** are the source cut into its natural teaching pieces, each tagged
by function: definition, motivation, worked example, procedure, limitation.
They stay faithful to the source and carry provenance. Non-textual content (a
diagram, a chart) currently simply belongs to its passage; how such assets are
represented and used is left for future implementation (see Deferred).

**KC Grains** (short form: grains) are the Companion's base learning unit:
source-local observations of a skill, statements of what a student could walk
away with, expressed as capabilities. The term is ours, not the literature's:
the literature's "learning objective" names a much coarser unit spanning
several Knowledge Components, which is exactly the collision the rename
avoids. Each grain points at the evidence in the source that supports it. How
grains are sized (open, see Open Questions) and how exactly they are
extracted, including their precise relationship to passages, is still being
designed (open, see Open Questions). What is decided: passages may suggest
grains but must never constrain them. Also decided: grains are extracted only
for what a source teaches, never for what it assumes; assumed background is
not evidence (a source that assumes dot products has taught us nothing about
dot products).

## The grain and KC objects

Grains and KCs are structured objects, not phrasings; a phrase is one field
among few. Every grain and KC carries three axes drawn from the
tutoring-systems literature: its condition→response form (when given X, the
student does or produces Y), its knowledge type (fact, category, or rule),
and its modality (do versus explain). Axis mismatches are hard boundaries: a
"do" grain never merges into an "explain" KC, and a fact never joins a rule.

A grain carries: its statement, its axes, and provenance to the passages and
Model Reading that produced it.

A KC carries: its frozen id (ADR 0008), its canonical phrasing (the human
handle and the embedding anchor), its axes, two or three exemplar checking
questions (born with the KC, refreshed alongside the canonical; they are
identity substance and the anchor material admission judging reads), its
membership log, and its versioned digests.

The axes will eventually supersede the Companion's older
fact/procedure/applied/conceptual labels (through the compiler, later) and
enable future instructional-form selection (guivalenca/companion#74).

## From grains to Knowledge Components

Different sources often teach the same content and therefore produce similar
grains. We resolve this by grouping equivalent grains into a
**Knowledge Component (KC)**: a discrete, measurable unit of cognitive skill
or understanding. The KC is the key teachable and assessable unit of the
system. The exact test that decides whether two grains belong to the same
KC has not been formally defined (open, see Open Questions).

The grouping runs as semantic entity resolution under the canonical-anchor
policy (ADR 0007):

1. **Blocking** (cheap, recall-oriented): embed the new grain into a
   vector and search it, via pgvector, against the canonical phrasing vectors
   of existing KCs. This collapses the unaffordable "compare everything
   against everything" space into a short candidate list.
2. **Judging** (careful, precision-oriented): an LLM compares the new
   grain against each candidate KC's canonical phrasing and exemplar
   questions only, never against individual member grains, and issues one of
   five verdicts: match, no-match, contains, contained-by, or uncertain.
   Uncertain routes to a human; an axis mismatch is an automatic no-match. We
   avoid binary verdicts because they convert model hesitation into silent
   errors.
3. **Committing**: exactly one match joins the grain to that KC, after a
   whole-set gate in which a judge reads the entire resulting KC and confirms
   it is still one skill. No matches create a new KC. Multiple matches
   quarantine the grain for human review: membership is identity and
   identity is transitive, so a real double match means the grain is too
   coarse and must split into two grains, or the two KCs are duplicates
   and must merge, or a verdict is wrong. The human decides which.

A grain belongs to exactly one KC. Judging only against the canonical
makes match chains structurally impossible, which is the documented failure
mode of naive transitive merging. Occasional bad joins are accepted: they cost
optimization, not corruption, and recurring conflicts are a signal to improve
the system. Every time a KC gains a grain, an LLM refreshes its canonical
phrasing, which triggers a cheap re-embedding of its vector. A triggered local
repair pass over messy neighborhoods is deferred (guivalenca/companion#72).

Containment verdicts (one question pool sitting strictly inside the other)
are recorded as stamped KC-to-KC edges and consumed by nothing in v1. They
are an opportunistic byproduct, captured only when blocking happens to
surface the pair, never a sought-after prerequisite mapper. The edges are
concept-blind, and genuine "needed before, not part of" prerequisites remain
future work (see Deferred).

Intake runs as decomposed focused calls (ADR 0009): the Model Reading, a
sizing gate that passes, splits, or drops each candidate grain while writing
its axes, deterministic blocking, the membership judge, and the whole-set
gate, each a separate call whose output is a stamped fact. This is what makes
per-stage auditing in the dashboard and per-stage comparison in the harness
possible; stages may be subdivided further during execution.

KC identity is durable (ADR 0008): the id is minted once when the KC is born,
as a readable slug plus a short suffix derived from the initial canonical
phrasing, and never changes afterwards. Membership changes append to a
permanent membership log. A merge retires one id with a permanent redirect to
the survivor; a split keeps the id on the descendant retaining the most
grains and mints new ids, with pointers, for the rest. Merges are expected
in normal operation, because blocking is recall-oriented and the same skill
occasionally enters twice under different vocabulary until a bridging
grain exposes the duplicate.

Every KC also has a **digest**: a compact compiled teaching text built from
its backing grains' evidence. Digests are self-contained, versioned, and
recompile when the KC's grains change. They are what the tutor reads.

Every automated decision in this loop (verdicts, phrasings, vectors) is
stamped with the model and prompt version that produced it. Text is the only
canonical data; vectors and verdicts are derived and replayable.

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
select KCs through the chain syllabus → sources → grains → KCs, never through
concepts. The concept is the shelf a KC is displayed on; its teaching material
is its KCs' digests, its assessment plan comes from its KCs, its mastery is
computed from its KCs' evidence, and a misfiled KC costs readability, not
learning. The process for aggregating KCs into Concepts is undefined
(open, see Open Questions).

## From Syllabus to lessons and sessions

Because the Syllabus maps sources to days, and sources yield grains, and
grains resolve into KCs, the system can determine which Knowledge
Components each class needs to teach. An LLM then assembles the **lesson
plan**: dividing the day's KCs into segments and ordering those segments. The
plan is an interpretation: computed, versioned, and recomputable as our
pipeline improves. When a session actually teaches, its session record pins
the plan version and KC digest versions it used, so taught plans are retained
as context for the evidence they produced; untaught drafts are disposable. The
rules for how segments may combine concepts and KCs are not yet designed
(open, see Open Questions).

A session's teaching context is assembled by curated injection: the Companion
decides what enters the prompt, drawing on the selected KCs' canonical
phrasings and digests and their concept's name. This control is what
guarantees curricular coverage and instructional focus.

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
database under the same transactions. The universe is a deployed web service
operated through the admin dashboard (ADR 0005), not a local pipeline.

## Working method

The system is built through the harness: prompts are versioned, every run is
recorded with its model and prompt stamps, and a run-comparison view (same
fixture, two prompt versions, side by side, with a push action to adopt the
preferred result) is how prompt changes are evaluated and adopted.
cg_pipeline's transcribed corpora serve as fixtures.

The harness's first act is the perceptron hand experiment for the KC
membership and sizing rules: a multi-rater card sort, a blind question-swap
test, and a structural audit over the axes, with adoption thresholds agreed
in advance (about .7 kappa agreement on membership pairs, and question-swap
verdicts matching the piles on about 80% of pairs). Below those thresholds
the rule under test, not the raters, is revised before extraction scales.

## Deferred to future implementation

Decided as out of scope for the initial system; the architecture keeps each
one cheap to add later because interpretations are recomputable:

- **Concept links**: mastery flowing between related concepts (e.g. Perceptron
  feeding Neural Networks).
- **Non-textual assets**: the format, representation, and any retrieval of
  images, diagrams, and charts. Today an asset is simply part of its passage.
- **Dynamic KC boundary auditing** via learning-curve analysis over student
  evidence. Tracked as guivalenca/companion#73, label `post-concept-universe`.
- **The observer agent** for impartial evidence extraction.
- **Forgetting and retention modeling** over timestamped evidence.
- **Mastery model upgrades** beyond counting (BKT, IRT).
- **Triggered local repair** of messy KC neighborhoods, re-solving one small
  region with all stored verdicts at once and surfacing the result as a
  dashboard proposal. Tracked as guivalenca/companion#72, label
  `post-concept-universe`.
- **Full-rerun id reconciliation**: matching recomputed KCs back to existing
  ids when the whole interpretation layer is rebuilt with a new model or
  prompt.

## Open Questions

Each entry describes the problem, not just the question, so it can be picked
up without the original conversation.

1. **KC membership test.** What rule decides that two grains are "the same
   skill" and belong in one KC? The decision is scheduled for the KC-stage
   build and will be made empirically via the perceptron hand experiment (see
   Working method), not in the abstract. The leading candidate is
   question-pool interchangeability (two grains are one KC iff any fair
   checking question for one is a fair checking question for the other),
   proposed by the research memo
   (`docs/research/kc-granularity-membership.md`), which found our original
   "same checking question" candidate validated as a sizing gate but weak as
   an identity test. Regardless of the outcome, KCs carry exemplar questions
   (see the object section), so the material the decision needs accumulates
   either way.
2. **Grain sizing rule.** Adopted as a working rule: one focused question
   could test it (too big splits; nothing worth asking drops). Final
   confirmation waits until real extraction outputs are inspected in the
   harness; the rule is one prompt edit away from revision if outputs look
   wrong.
3. **Grain extraction method.** How exactly are grains derived during
   a Model Reading? Passages may suggest grains but must never constrain
   them (decided); whether extraction works from passages plus a
   contextualization of the source, from the source directly, or another
   arrangement, is unresolved.
4. **KC-to-Concept aggregation.** How are KCs assigned to concepts, and where
   do concept boundaries come from? Sketch under discussion: human vocabulary
   anchors boundaries, machines propose, curation confirms. Nothing decided.
5. **Segment composition rules.** How segments may combine concepts and KCs
   (one concept per segment, several, several segments of one concept) is
   deliberately parked.
6. **Digest source weighting.** Whether a KC digest should ever emphasize the
   current lesson's own sources over other backing sources. Instinct: no for
   v1.

Phase 2 questions, parked with the student ledger (ADR 0003):

7. **Expected answers on grains.** Should a grain carry a description
   of what a satisfactory demonstration looks like? Raised, unexplored.
8. **Evaluation flow.** When and how evidence is extracted at segment close,
   and by which agent.
9. **"Seen" trigger.** Leaning toward "a segment the student finished", but
   not decided.
10. **Rank-to-weight conversion.** Teachers rank KC importance; the curve
    converting rank into weight is undecided.
