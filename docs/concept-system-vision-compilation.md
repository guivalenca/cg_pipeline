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

## The founding principle

The entire system rests on one distinction: **facts versus interpretations**.

A fact is something that happened and is true forever: "this source said this,
on these lines", "this student demonstrated this, on this date". Facts are
stored permanently, are never edited, and never require an AI to be right.

An interpretation is a judgment built on top of facts: "these two objectives
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
   objectives below). A reading is a fact about what that extractor said, even
   if the extractor was imperfect; better readings are added later, never
   substituted destructively.
5. **Syllabus**: the teacher's real input, and where sources enter the system:
   the mapping of a module's sources into days and class topics. The
   meaningful teacher signal is the day-level ordering of topics across the
   module; sources within a single day carry no order. The Syllabus is
   revisioned whenever the teacher changes it, and it is the honest record of
   how the institution actually sequenced its teaching.

These five are the ingestion chain, not the whole fact layer. The fact layer
also includes session records ("this session ran on this date, against this
plan version"), the student evidence records described below, and human
curation decisions, all permanent.

## Extraction: passages and objectives

From an artifact, a Model Reading extracts two kinds of units.

**Passages** are the source cut into its natural teaching pieces, each tagged
by function: definition, motivation, worked example, procedure, limitation.
They stay faithful to the source and carry provenance. Non-textual content (a
diagram, a chart) currently simply belongs to its passage; how such assets are
represented and used is left for future implementation (see Deferred).

**Learning objectives** are the Companion's base learning unit: statements of
what a student could walk away with, expressed as capabilities. Each objective
points at the evidence in the source that supports it. How objectives are
sized (open, see Open Questions) and how exactly they are extracted, including
their precise relationship to passages, is still being designed (open, see
Open Questions). What is decided: passages may suggest objectives but must
never constrain them.

## From objectives to Knowledge Components

Different sources often teach the same content and therefore produce similar
objectives. We resolve this by grouping equivalent objectives into a
**Knowledge Component (KC)**: a discrete, measurable unit of cognitive skill
or understanding. The KC is the key teachable and assessable unit of the
system. The exact test that decides whether two objectives belong to the same
KC has not been formally defined (open, see Open Questions).

The grouping runs as semantic entity resolution, a two-stage loop:

1. **Blocking** (cheap, recall-oriented): embed the new objective into a
   vector and search it, via pgvector, against the canonical phrasing vectors
   of existing KCs. This collapses the unaffordable "compare everything
   against everything" space into a short candidate list.
2. **Judging** (careful, precision-oriented): an LLM examines each candidate
   pair and issues one of three verdicts: match, no-match, or uncertain.
   Uncertain routes to a human. We avoid binary verdicts because they convert
   model hesitation into silent errors.

A match joins the objective to the KC; all no-matches create a new KC. Every
time a KC gains an objective, an LLM refreshes its canonical phrasing, which
triggers a cheap re-embedding of its vector. How pairwise verdicts are turned
into group membership when matches chain (open, see Open Questions) has not
been discussed.

Every KC also has a **digest**: a compact compiled teaching text built from
its backing objectives' evidence. Digests are self-contained, versioned, and
recompile when the KC's objectives change. They are what the tutor reads.

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

A concept owns no content of its own: its teaching material is its KCs'
digests, its assessment plan comes from its KCs, its mastery is computed from
its KCs' evidence. The process for aggregating KCs into Concepts is undefined
(open, see Open Questions).

## From Syllabus to lessons and sessions

Because the Syllabus maps sources to days, and sources yield objectives, and
objectives resolve into KCs, the system can determine which Knowledge
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
database under the same transactions.

## Deferred to future implementation

Decided as out of scope for the initial system; the architecture keeps each
one cheap to add later because interpretations are recomputable:

- **Concept links**: mastery flowing between related concepts (e.g. Perceptron
  feeding Neural Networks).
- **Non-textual assets**: the format, representation, and any retrieval of
  images, diagrams, and charts. Today an asset is simply part of its passage.
- **Dynamic KC boundary auditing** via learning-curve analysis over student
  evidence.
- **The observer agent** for impartial evidence extraction.
- **Forgetting and retention modeling** over timestamped evidence.
- **Mastery model upgrades** beyond counting (BKT, IRT).

## Open Questions

Each entry describes the problem, not just the question, so it can be picked
up without the original conversation.

1. **KC membership test.** What rule decides that two objectives are "the same
   skill" and belong in one KC? The leading candidate is "do they admit the
   same checking question?", but this has not been formally adopted, and no
   candidate has been validated against real material. The planned validation
   is a hand experiment on the perceptron sources in our fixture.
2. **Objective sizing rule.** What makes something one objective rather than
   two, or too trivial to be one at all? Checkability (one focused question
   could test it) is a candidate criterion, not a decision.
3. **Objective extraction method.** How exactly are objectives derived during
   a Model Reading? Passages may suggest objectives but must never constrain
   them (decided); whether extraction works from passages plus a
   contextualization of the source, from the source directly, or another
   arrangement, is unresolved.
4. **Grouping policy for chained matches.** Judging is pairwise, so verdicts
   can chain: A matches B, B matches C, yet A and C are different skills.
   Without explicit rules, one vaguely-phrased objective in the middle welds
   two distinct skills into one KC. The policy for turning pairwise verdicts
   into group membership has not been discussed at all.
5. **KC-to-Concept aggregation.** How are KCs assigned to concepts, and where
   do concept boundaries come from? Sketch under discussion: human vocabulary
   anchors boundaries, machines propose, curation confirms. Nothing decided.
6. **Expected answers on objectives.** Should an objective carry a description
   of what a satisfactory demonstration looks like? Raised, unexplored.
7. **Segment composition rules.** How segments may combine concepts and KCs
   (one concept per segment, several, several segments of one concept) is
   deliberately parked.
8. **Evaluation flow.** When and how evidence is extracted at segment close,
   and by which agent, is under active discussion.
9. **"Seen" trigger.** Leaning toward "a segment the student finished", but
   not decided.
10. **Rank-to-weight conversion.** Teachers rank KC importance; the curve
    converting rank into weight is undecided.
11. **Digest source weighting.** Whether a KC digest should ever emphasize the
    current lesson's own sources over other backing sources. Instinct: no for
    v1.
