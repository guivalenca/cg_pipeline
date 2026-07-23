# The concept universe: living design

Purpose: preserve the current shared understanding of the new concept system as
it develops. This is the maintained design narrative, not a fixed
implementation specification. Settled decisions, working ideas, and open
questions are labelled separately so later conversations can change the
picture without erasing how it evolved.

Status: active exploration. Update this document whenever the model materially
changes. `CONTEXT.md` holds only concise domain language that has actually been
agreed; this document holds the larger reasoning and unresolved design.

Interactive companion: `docs/concept-universe.html`. Update the universe when
the system model, decision status, or important interactions materially change.

The earlier `docs/concept-ledger-vision.md` remains useful historical framing,
but this document is the current statement of the vision.

## 1. The ambition

Companion should own a persistent "mini universe" of reusable knowledge rather
than regenerate isolated Concept Graphs for every Course, Module, Subject, or
Institution. Once knowledge is extracted from a teaching source, it should
remain available permanently, retain its provenance, and enrich the company's
understanding of that knowledge.

Institutions contribute more than content. By selecting material for lessons
and arranging lessons over time, teachers provide real pedagogical evidence:
which Concepts belong together, what they tend to teach first, and which paths
they believe make sense. At scale, student outcomes can add another evidence
layer: which Concepts are difficult, which preceding Concepts help, and which
teaching paths produce better understanding.

The company-wide knowledge structure and an institution's curriculum are
therefore different things:

- the concept universe contains reusable knowledge;
- institutional lessons are contextual paths through that knowledge;
- student learning data eventually describes how students move through and
  understand it.

## 2. Why the current system is insufficient

Today, the concept pipeline consumes lesson sources and creates concepts inside
static, Subject-scoped graph artifacts. Those concepts are not reused across
Courses, Modules, Subjects, or Institutions, even when other sources teach the
same idea. Content changes require regeneration and promotion of static data,
and the pipeline's inputs, intermediate artifacts, decisions, and failures are
difficult to inspect.

This causes several losses:

- repeated extraction of knowledge the company has already seen;
- duplicate but disconnected concepts;
- no durable history of how source material was processed;
- no company-wide view of how teachers connect and sequence knowledge;
- no foundation for comparing teaching paths with student outcomes.

## 3. Current shared model

### 3.1 Source Fragment — settled

A Source Fragment is an immutable, source-specific unit of knowledge preserving
how one teaching source presents an idea. It is granular extraction output, not
the reusable platform Concept itself.

Only explicitly expressed ideas become Fragments. A Fragment may faithfully
paraphrase or condense its source, but every part of the idea must be directly
supported by a contiguous Evidence Span from an immutable Source Revision. If
validating the idea requires additional domain knowledge or a further
derivation, it is an implication and must not be extracted as a Fragment.

The initial minimal model-output contract is the Fragment idea plus the start
and end line of its Evidence Span. Infrastructure generates identity, restores
the exact source text, calculates character offsets, and validates the range.
Source line numbers are prompt-time annotations; the stored Markdown is not
modified. Multiple non-contiguous Evidence Spans remain a later option only if
real tests demonstrate that they are necessary.

Every Source Fragment remains available permanently. It keeps provenance back
to the source material and the processing run that produced it.

Every Source Fragment must enter at least one Concept Facet. There is no orphan
or unassigned Fragment pool. If it does not match an existing Facet, the system
creates a new Facet inside an existing or new Teachable Concept. Semantic
comparison decides reuse versus creation, not whether the Fragment enters the
universe.

Source Fragments are never destructively merged into a new text and discarded.

### 3.2 Concept Facet — settled foundation

A Concept Facet is a simple rectifying grouping for Source Fragments that make
essentially the same semantic contribution. It prevents a granular Concept
from accumulating an unstructured flat collection of dozens of repetitive
Fragments while preserving every Fragment and its provenance.

A Facet is necessarily part of a Teachable Concept. It is not an independent
learning or mastery unit, and lessons do not select Facets. The exact rules for
whether a Fragment may support multiple Facets and whether a Facet may ever be
shared by Concepts remain open.

### 3.3 Teachable Concept — settled foundation

A Teachable Concept is the granular reusable, platform-owned learning unit. It exists
independently of any one Source, Course, Module, Subject, Institution, or
lesson.

The Teachable Concept contains one or more Facets. As new sources arrive, their
Fragments may join existing Facets or establish new Facets within the Concept.
The Concept grows without erasing the distinct way each source presented its
knowledge.

A Concept backed by one Facet containing one Fragment is valid. It may grow
later as related knowledge arrives from other Sources and contexts.

Lessons select Concepts, not Facets. A Concept is intended to be one coherent,
granular unit that can be taught through a coherent explanation and assessed
through a focused task family. The operational definition of those two tests
still requires a small running experiment with real source material.

### 3.4 Composite Concept — settled foundation

A Composite Concept is a greater learning idea composed of multiple granular
Teachable Concepts. Lessons teach and assess the component Concepts. Evidence
over those Concepts later contributes to an aggregate judgment of mastery over
the Composite. For example, Perceptron may be a Composite whose component
Concepts cover inference, learning, and linear-separability limitations.

The exact aggregation rule, whether a Concept may belong to multiple
Composites, and how incomplete component coverage caps Composite mastery remain
open.

### 3.5 Concept Digest — settled for now

The full Fragment collection is too large to place into tutoring prompts,
especially when a lesson contains many segments and each segment contains many
Concepts. A Teachable Concept therefore has a compact, versioned, source-backed
Concept Digest: an informational teaching snapshot derived from its Facets and
supporting Fragments.

The Digest is a lossy teaching representation; it is not the durable source of
truth and is not part of the universe's relationship structure. The underlying
Source Fragments remain the evidence and allow future recompilation.

Current direction:

- compile the Digest asynchronously when the collection materially changes;
- allow an AI process to reconcile the Fragments into a concise teaching
  representation;
- keep the result versioned, auditable, and linked to supporting Fragments;
- cache and reuse it so normal lesson assembly does not require another
  compilation call;
- revisit the exact compiler, quality bar, and review process when the total
  system is better understood.

This decision is intentionally provisional. It is sufficient for continuing
the design without pretending the distillation problem is solved permanently.

## 4. Sources, identity, artifacts, and reprocessing

### 4.1 Permanent source history — settled intent

The system needs a permanent record of everything it ingests. That history must
include the original material and important by-products such as extracted
Markdown, OCR, transcripts, or other normalized forms. These artifacts must be
available for inspection and future reprocessing.

No processing result silently overwrites an earlier one. A future, improved
extractor should be able to remove noise from an old source while retaining the
old artifact, the new artifact, the processing versions, and the relationship
between them.

### 4.2 Source identity — strategy settled, per-type fields open

Primary deduplication should not use extracted content. Current extraction can
include noise, and improving that extraction in the future should not make the
same logical source appear to be a new source.

Source identity uses a fingerprint derived from stable metadata, with a
different identity strategy for each source type rather than one universal
formula. The exact per-type tuples remain open. Likely inputs may include
platform video ID for hosted video; ISBN, edition, and page range for books;
or canonical locator, title, author, publisher, and other type-specific fields.

Several different identities must not be collapsed into one value:

- the logical Source identity, derived primarily from stable metadata;
- a particular revision of the original material when the source changes;
- a processing artifact produced from that material;
- a processing or extraction run using a particular pipeline version.

A checksum of original bytes or fetched material may still be useful for
integrity and change detection, but it is not the primary logical Source
identity. A checksum of extracted Markdown must not determine Source identity.

### 4.3 Reuse versus reprocessing — settled intent

If the same source is used in two lessons, the system should not ingest and
extract it twice merely because the lesson context changed. Both lessons can
reference the same stored source material, artifacts, and Source Fragments.

Reprocessing is explicit and additive. It creates another run and possibly new
artifacts or Fragments while preserving the previous results. The policies for
superseding noisy Fragments and rebuilding Concept Digests remain open.

## 5. Lessons as contextual paths

### 5.1 Building a lesson from its material — settled direction

An institution supplies materials for a particular lesson or day. The pipeline
extracts Source Fragments from those materials, rectifies similar Fragments
into Facets, and assembles Facets into granular Teachable Concepts. The lesson
selects the Concepts supported by its material; it does not select Facets.

The lesson-facing Digest for a selected Concept should preserve the emphasis of
the lesson's own supporting Fragments rather than inject the entire
company-wide Fragment collection. The relationship between this contextual
Digest and a possible company-wide canonical Digest remains open.

### 5.2 Sequencing is contextual — settled

The pipeline still performs a sequencing phase over the combined material for
a lesson. It may recommend, for example, Variables, then Assignment, then
Conditions.

Order is not an intrinsic property of a Source Fragment or Teachable Concept.
The same source material may be used in different material combinations and
receive a different recommended position. The sequencing result belongs to its
lesson context and processing run.

The system permanently retains these contextual recommendations. Over time,
many lesson sequences can become pedagogical evidence that one Concept often
precedes another, without prematurely declaring that ordering a universal
prerequisite.

Each Lesson Revision preserves its exact ordered segments and the ordered
Concept list inside every segment. Sequencing evidence is derived from that
structure rather than stored as a separate web of pairwise edges:

- a Concept in an earlier segment has strong precedence evidence over a Concept
  in a later segment;
- an earlier Concept within the same segment has weak precedence evidence over
  a later Concept in that segment.

Strong and weak describe confidence in the observed teaching order, not
prerequisite severity or universal truth. A changed Lesson creates a new
immutable revision instead of overwriting the previous sequence. Only published
or actually taught revisions contribute to aggregated ordering patterns; drafts
and repeated edits remain provenance but do not count as independent teaching
evidence.

Working flow:

1. Identify the lesson's source material.
2. Reuse existing source records and artifacts where possible.
3. Extract or reuse Source Fragments.
4. Rectify similar Fragments into Facets and assemble Facets into granular
   Teachable Concepts.
5. Run sequencing over the lesson's combined material.
6. Store the contextual sequence with provenance.
7. Assemble the lesson from selected ordered Concepts and contextual Concept
   Digests.
8. Use assessment evidence over Concepts to derive Composite mastery later.

The name and exact shape of this contextual sequencing record remain open.

## 6. A simple example

Three sources teach introductory programming:

- Source A says a variable is a named box containing a value.
- Source B says a variable associates a name with a value and explains
  assignment.
- Source C explains comparisons and `if` conditions.

Their Source Fragments remain separate. Semantically equivalent contributions
are rectified into Facets; complementary Facets compose granular Concepts such
as variable assignment or conditional evaluation. Those Concepts may later
contribute to broader Composite mastery.

One lesson-material combination may produce:

`Variables -> Assignment -> Comparison -> If`

Another combination using one of the same sources may produce:

`Variables -> Comparison -> If -> Reassignment`

The shared source is not ingested twice. The two contextual sequences are both
retained because they describe different pedagogical recommendations.

## 7. Long-term value

At scale, the system may support:

- reuse of knowledge across institutional boundaries;
- increasingly resilient Concept Digests backed by diverse sources;
- evidence about which Concepts teachers group and sequence together;
- evidence-backed retrieval of possible foundation Concepts when a tutor
  detects a student gap;
- comparison of teaching paths with student outcomes;
- identification of difficult Concepts and helpful predecessors;
- institution-specific paths enriched by company-wide knowledge;
- learning paths that are no longer constrained to one Course or Subject.

Student-derived optimization is a long-term horizon, not the first version.

Explicit `soft`, `hard`, and `blocking` prerequisites are out of scope for the
current Concept Universe. A macro Concept-to-Concept prerequisite is too vague
to drive useful remediation. The system will preserve lesson sequencing and
student evidence instead. A far-future model-assisted retrieval capability is
tracked in [GitHub issue #37](https://github.com/guivalenca/companion/issues/37)
and requires substantially more data before even a beta.

## 8. Product and platform direction retained from earlier discussions

The system should become a visible, database-backed part of Companion rather
than remain a collection of local CLI stages and files. The expected product
surfaces remain:

- source curation before processing;
- operations visibility across pipeline inputs, outputs, runs, and failures;
- exploration and review of Teachable Concepts and their relationships.

Human curation decisions are durable data. Exclusions, source-handling choices,
edits, associations, sequence approvals, and publication decisions must survive
re-imports and reprocessing.

The existing schema name `runtime_graph.v0` is disliked and will be replaced as
part of this refactor. The replacement vocabulary and contract are not yet
settled.

## 9. Design principles currently accepted

- Preserve extracted knowledge and provenance; do not destructively merge it.
- Reusable Concepts are global to the platform, not owned by a curriculum
  slice.
- Similar Source Fragments are rectified through Facets without losing their
  provenance.
- A Teachable Concept is a granular learning unit composed of one or more
  Facets; a Concept Digest is its compact derived teaching representation.
- Lessons select Concepts, not Facets; Concepts contribute to broader
  Composite mastery.
- Derived artifacts are versioned and recomputable.
- Lesson sequencing is contextual evidence, not an intrinsic global order.
- Prerequisites are not part of the current universe; preserve evidence that
  may later support actionable foundation retrieval instead.
- Reusing a Source in another lesson must not require ingesting it again.
- Improved processing adds history instead of rewriting history.
- Human decisions and processing provenance are first-class data.
- The complete collection stays behind the scenes; runtime teaching receives a
  bounded representation.

## 10. Interactive universe — agreed visual language

The visualization should feel like a spatial knowledge universe rather than a
pipeline diagram or an architecture flowchart.

- Source Fragments appear as small dots. Selecting one reveals its provenance
  and source-specific knowledge.
- A Teachable Concept appears as a softly shaded organic neighborhood or blob
  containing its relevant Source Fragment dots. Facets organize similar dots
  within the region but remain visually subordinate. The Concept is the region
  itself, not a separate large node inside it.
- Concept names remain slightly visible inside their regions and become clearer
  on hover or selection.
- Composite Concepts need a visual treatment distinct from the granular
  Concept blobs; that treatment has not yet been decided.
- Distance between Fragment dots should approximately represent semantic
  similarity; spatial placement must not be merely decorative.
- Connections and lines remain subtle or hidden unless they are important to
  the selected context. Selection may reveal the relevant relationships.
- Concept Digests do not appear as entities on the universe canvas. A Digest is
  informational detail shown when its Teachable Concept is selected.
- Sources do not appear as entities on the universe canvas. Source provenance
  appears when a Source Fragment is selected.
- Lessons do not appear as permanent entities on the universe canvas. Selecting
  a Lesson temporarily overlays its contextual ordered path through Concepts.
- The initial view focuses on the Word Embeddings and Word2Vec region of the SI
  Module 6 Computação curriculum. The broader 227-concept curriculum remains
  available through zooming and panning.

The current SI Module 6 concepts are already consolidated pipeline outputs, so
they can seed provisional Teachable Concept regions and real lesson paths but
cannot be presented as the original granular Source Fragments.

## 11. Open decisions

Resolve these gradually rather than as one schema exercise:

1. Which metadata fields form the agreed logical Source identity tuple for each
   source kind?
2. How are Source revisions distinguished when metadata remains stable but the
   material changes?
3. When may two institutions share processing for the same logical Source, and
   what access or licensing constraints apply?
4. What exact semantic test places Fragments in the same Facet, and when is a
   new Facet created?
5. What material change triggers Concept Digest recompilation?
6. What must the Concept compiler output, and how is it validated against its
   supporting Fragments?
7. How does a lesson combine its own Fragment emphasis with the company-wide
   Concept Digest?
8. Who reviews or approves contextual sequencing recommendations?
9. How do repeated contextual sequences become weighted Concept relationship
   evidence?
10. How are noisy or superseded Fragments treated without deleting history?
11. What replaces Concept Graph, Runtime Lesson, and `runtime_graph.v0` in the
    new domain language?
12. How will current Student Concept Map identities migrate toward reusable
    platform Concepts?
13. May one Fragment support multiple Facets, may a Facet belong to multiple
    Concepts, and may a Concept contribute to multiple Composites?
14. What operational test defines one coherent explanation and one focused task
    family for a granular Concept?
15. How is Composite mastery derived from component Concept evidence, including
    components that have not yet been taught or assessed?
16. In the small pre-code Perceptron experiment, can humans consistently move
    real pipeline candidates through Fragment, Facet, Concept, and Composite
    boundaries without recreating the current over-merging problem?

## 12. Current CG pipeline findings

The acquisition/extraction package does not currently extract concepts. It
produces a complete derived Markdown **Source Body** for each workbook
Self-study and publishes those bodies through an Extraction Corpus. The first
fragment-like objects appear in creation phase 03 as source-local **Candidate
Concepts**. Each Candidate is grounded by source anchors and is intended to be
small enough for one to three focused questions. Cross-source merging and
deduplication are explicitly deferred.

The current Candidate Concept is therefore the closest existing analogue to a
Source Fragment, but it is not yet the desired entity. Candidate identity is
run/workbook-row scoped, extraction includes lesson context, and later stages
may prune, merge, or split Candidates. A permanent reusable Fragment instead
needs stable identity within a Source Revision, lesson-independent extraction,
immutable provenance, and guaranteed entry into at least one Concept Facet.
Lesson relevance should be a separate association.

Creation currently applies two later reconciliation layers:

1. Lesson reconciliation may merge near-duplicates, split compound Candidates,
   map one Candidate to multiple lesson concepts, or prune it.
2. Subject merge groups lesson concepts using the intended identity test
   "the same teachable idea at the same level, testable with the same
   question." At this point inputs can be merged or retained but not split.

Real artifacts show that these rules do not reliably preserve granularity.
Stemming and Lemmatization were extracted as distinct source-local Candidates
and later combined into one final concept. In another Computacao run, several
separately checkable perceptron Candidates were progressively condensed into
one broad concept with multiple distinct coverage checks. Conversely, some
near-duplicate concepts survive subject merge. This confirms that the final
pipeline Concept is not a safe identity boundary for the universe.

The current pipeline also combines several responsibilities in one final
Concept record: identity, mutable descriptive content, Fragment/candidate
membership, and lesson occurrence. Its content-derived identifier changes when
the generated description, criteria, or supporting candidates change, and its
scope is course/module/subject rather than company-wide. The universe must
separate durable Concept identity from Fragment evidence, Facet rectification,
versioned Concept Digests, contextual lesson occurrences, and Composite
mastery.

The current working granularity model is more structured than the existing
"one to three questions" heuristic:

- A Source Fragment is one source-grounded, independently expressible and
  checkable knowledge claim or capability, supported by precise anchors.
  Several question variants may test it, but independently testable objectives
  indicate separate Fragments.
- A Facet rectifies Fragments making essentially the same semantic
  contribution; it is organization inside a Concept, not a lesson selection or
  mastery unit.
- A Teachable Concept is a granular learning unit composed of one or more
  complementary Facets and is what a Lesson selects and assesses.
- A Composite is a greater idea whose mastery is derived from evidence over
  multiple component Concepts.

The four entity roles are settled as the current model. Their exact boundary
rules and relationship cardinalities still require a small running experiment
with real source material before implementation.

## 13. First Source Fragment extraction prototype

On 2026-07-14, the first live extraction experiment used the real SI Module 6
source `0023-an-introduction-to-bag-of-words-and-how-to-code-it-in-python-for-nlp.md`.
The experiment removed provenance frontmatter, numbered the remaining 232 Source
Body lines, rendered `prompts/source-fragment-extraction.txt`, and exposed only
the strict `submit_source_fragments` tool with `idea`, `start_line`, and
`end_line`.

The same prompt and Source Body were sent directly to the DeepSeek API in four
configurations:

- V4 Flash without thinking: 25 Fragments, 11.3 seconds.
- V4 Flash with high thinking: 21 Fragments, 23.8 seconds.
- V4 Pro without thinking: 26 Fragments, 16.3 seconds.
- V4 Pro with high thinking: 24 Fragments, 101.1 seconds.

All four outputs passed deterministic validation: exactly one expected tool
call, valid JSON shape, non-empty ideas, and evidence ranges within the Source
Body. DeepSeek thinking mode rejected both a named forced tool and
`tool_choice=required`; thinking calls succeeded with automatic tool selection,
the prompt's explicit submission instruction, strict schema enforcement, and
local response validation. This is an API compatibility fact, not a conclusion
about extraction quality.

The four human-readable outputs live under
`results/0023-bag-of-words/`. They intentionally remain separate rather than
being synthesized into a comparison report. Human review must now judge
coverage, granularity, self-containment, fidelity, evidence minimality, code
handling, and duplicate treatment before the Fragment boundary or prompt is
changed.

## 14. Current-system facts relevant later

- Current curriculum artifacts use `runtime_graph.v0` and are loaded from
  static reference files.
- Current student Concept Map keys are scoped by Module and Subject, so global
  Teachable Concept identity is not yet the production identity model.
- The current pipeline lives separately and produces file-based intermediate
  artifacts.
- Companion uses Postgres for durable application data and Redis for live
  Session state.

These are compatibility constraints for a later viability and migration pass;
they do not define the desired concept universe.
