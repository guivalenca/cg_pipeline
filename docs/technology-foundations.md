# Technology foundations for the Concept Universe

Purpose: study material. This document teaches the technologies relevant to the
Concept Universe design and maps each one onto our system so the design
conversation can be fully two-sided. It explains; it does not decide. Design
decisions remain in the discussion and in the vision document.

Reading guide: each section answers three questions. What is this? How does it
work? What role would it play in our system? Sources are linked inline.

---

## 1. Embeddings

### What they are

An embedding model turns a piece of text into a vector of numbers (typically
1,000 to 4,000 dimensions) such that texts with similar meaning land close
together in that vector space. You already know the mechanism from your neural
network background: the model is an encoder trained so that the geometry of its
output space mirrors semantics. "Can compute a bag-of-words vector for a
sentence" and "is able to calculate BOW representations of text" produce
vectors that are nearly parallel; either of them against "can identify UML
deployment diagrams" produces vectors that are nearly unrelated.

Similarity between two vectors is measured with cosine similarity: a single
number, roughly 0 to 1, computed in microseconds. That is the entire trick:
comparing meanings becomes comparing numbers.

### The two properties that define how to use them

1. They are cheap and fast. Embedding a short text costs a fraction of a cent
   and comparing vectors costs essentially nothing. You can compare one new
   objective against every facet in the universe instantly.
2. They are fuzzy. Similarity scores capture "these are about the same thing",
   not "these admit the same checking question". Two objectives about
   perceptron weights will score high whether or not they test the same
   capability. Embeddings are excellent at narrowing candidates and
   untrustworthy at making final calls.

Every correct use of embeddings in our system follows from taking both
properties seriously at once: use them to shortlist, never to decide.

### Role in our system

Candidate generation for facet matching (section 3), and nothing else decides
through them. Also the mechanism behind proposing reference links: "this new
objective's vector is close to the Perceptron concept's facets" is a proposal
generator, not a verdict.

### Choosing a model

A benchmark for exactly our language context now exists: MTEB-BR, 22 native
Brazilian Portuguese tasks across 93 models
([arXiv 2607.04581](https://arxiv.org/html/2607.04581v2)). Findings that
matter to us:

- Top proprietary model: Gemini-Embedding-001. Voyage models close behind.
- Top open-weight models (Qwen3-Embedding-8B, KaLM-Embedding-Gemma3-12B) reach
  essentially the same tier, so self-hosting is a real option.
- Portuguese-specific encoders showed no advantage over good multilingual
  models. We do not need a specialized Brazilian model.

Cost at our scale is trivial: current pricing runs $0.02 to $0.15 per million
tokens ([comparison](https://pricepertoken.com/embedding)), and our whole
universe is thousands of short texts. Embedding everything costs cents;
re-embedding the entire ledger after a model upgrade also costs cents. Choose
purely on measured quality: the practical move is to test two or three
finalists on our own objective pairs.

### The discipline that matters

Vectors are derived data, never truth. Text is canonical. Every stored vector
carries the model name and version that produced it. Embedding models
deprecate roughly yearly (Voyage 3.5 was superseded by Voyage 4 within a
year, and Voyage itself was acquired by MongoDB in 2025), so a model
migration must be a mechanical re-embed, not a data-model event. One version
column per table, adopted on day one.

---

## 2. Vector search and pgvector

### What it is

Once texts are vectors, "find the most similar items" becomes "find the
nearest vectors". A vector store is any database that can do this. Dedicated
vector databases (Pinecone, Qdrant, Weaviate, Turbopuffer) are services built
only for this. pgvector is an extension that adds the same capability inside
Postgres: a vector column type, similarity operators, and optional
approximate-nearest-neighbor indexes (HNSW), sitting next to ordinary rows.

### Why the answer at our scale is boring

The 2025-2026 consensus threshold: pgvector comfortably handles single-digit
millions of vectors; dedicated engines earn their keep at billions of vectors,
strict sub-20ms latency targets, or thousands of concurrent queries
([analysis](https://clickhouse.com/resources/engineering/scale-vector-search-postgres),
[trade-off discussion](https://zenvanriel.com/ai-engineer-blog/pgvector-vs-dedicated-vector-db/)).
Our universe is thousands of objectives: three to four orders of magnitude
below where pgvector even needs tuning. At this size an exact brute-force
scan (compare against everything, no index at all) completes in milliseconds,
which conveniently sidesteps approximate-search recall concerns entirely.

Keeping vectors in Postgres also preserves something dedicated stores give
up: the objective row, its evidence links, and its vector live in one
database under one transaction. No synchronization between two systems, no
second source of truth.

### Role in our system

One vector column on the facet table (and possibly the objective table), one
similarity query powering the matching loop. Nothing more.

---

## 3. The matching loop: semantic entity resolution

### What it is

"Do these two records refer to the same thing?" is an old, well-studied
problem called entity resolution. The modern LLM-era pattern, sometimes
called semantic entity resolution
([overview](https://towardsdatascience.com/the-rise-of-semantic-entity-resolution/)),
is a two-stage loop:

1. **Blocking** (cheap, recall-oriented): use embedding similarity to collapse
   the impossible-to-afford "compare everything against everything" space into
   a short candidate list. For each new item, retrieve the top-k most similar
   existing items.
2. **Judging** (expensive, precision-oriented): an LLM examines each candidate
   pair and issues a verdict using an explicit test.

The strongest recent validation ran on sanctioned-entity matching, far messier
data than ours: blocking plus GPT-4o pairwise judging reached 98.95% F1 against
91.33% for a tuned rule-based baseline
([study](https://arxiv.org/html/2603.11051)).

### Mapped onto our system

A new source is processed and yields the objective "can update perceptron
weights given a learning rate and an error".

1. Blocking: embed it, retrieve the ten nearest facets in the universe.
   Milliseconds, no LLM involved.
2. Judging: an LLM receives the new objective and the ten candidates and
   applies our test: "do any of these admit the same checking question?" It
   answers per candidate: match, no-match, or uncertain.
3. Outcome: match joins the objective to the facet; all no-match creates a
   new facet; uncertain routes to review.

The loop is industry-standard and we should copy it without shame. The judge
prompt, our checking-question test, is ours, and it is where the quality
lives.

### The four lessons the literature hands us

1. **Blocking recall is the ceiling.** A candidate never shortlisted is never
   judged, and that error is invisible. Tune the shortlist generously (larger
   k, permissive similarity cutoff) and let the judge handle precision.
   There is no universal threshold number; it must be calibrated on our own
   labeled pairs.
2. **Three verdicts, not two.** Match / no-match / uncertain, with the
   uncertain band routed to human review. Forcing binary answers converts
   model hesitation into silent errors.
3. **Transitivity needs a policy.** If A matches B and B matches C but A does
   not match C, naive grouping welds all three into one facet through the
   weakest edge. The clustering step (pairwise verdicts into facet
   membership) needs explicit rules, not just connected components.
4. **Every verdict is audit data.** Judge model, prompt version, and score
   recorded with each decision, so facet formation is replayable when models
   change. LLM judges are not reproducible across model versions; the ledger
   must remember which judge said what.

The hand experiment we have planned (manually faceting objectives from the
perceptron sources) doubles as the construction of the labeled pair set that
lesson 1 requires.

---

## 4. Knowledge components: our facets have a literature

### What they are

Learning science has a name for "the smallest unit of capability that
assessment can distinguish": the knowledge component (KC), formalized in the
Knowledge-Learning-Instruction framework. A KC is an acquired unit of
cognitive function, inferred from performance on tasks. The mapping to our
vocabulary is nearly one-to-one:

| Our term | Literature term |
|---|---|
| Facet | Knowledge component (KC) |
| Objective (source-extracted) | A source's phrasing of a KC |
| Checking question | Assessment item |
| Question-to-facet mapping | Q-matrix |
| Facet mastery state | KC mastery estimate |

### Why this matters: an empirical audit for facet boundaries

The most valuable import is a method, not a term. If students practice a
well-defined KC repeatedly, their error rate should decline smoothly with
practice opportunities: a clean learning curve. Decades of educational data
mining work uses deviations from that curve to detect boundary errors:

- A "facet" that is secretly two skills produces a jagged curve: practice on
  one skill does not improve the other, so performance jumps around depending
  on which sub-skill each question happens to hit.
- Two "facets" that are secretly one skill produce redundant curves that
  improve in lockstep.

The implication for us is strategic: **facet boundaries do not need to be
perfect on day one, because student evidence can eventually audit them.**
The checking-question test draws the initial lines; learning-curve analysis
over the evidence ledger tells us later where we drew them wrong. Recent work
even uses LLMs for exactly our extraction step
([EDM 2025](https://educationaldatamining.org/EDM2025/proceedings/2025.EDM.long-papers.170/index.html)).

This only works because our ledger is append-only and interpretations are
recomputable: redrawing a facet boundary is a re-clustering plus a mastery
recompute, with no history lost. The architecture we chose for resilience
turns out to be the same architecture that makes boundary correction cheap.

---

## 5. Mastery models: how the field computes "does the student know it"

### First, the cost fact worth internalizing

Mastery computation costs zero tokens. LLMs appear only at content-change
moments (extraction, matching, judging) and at evidence-creation moments
(observing a session). Everything downstream (facet states, concept
percentages, coverage, reference-link derivations) is arithmetic over
database rows, recomputable in milliseconds at any time. A 2026 result makes
the division of labor explicit: specialized mastery models outpredict
GPT-4-class LLMs on student performance at a fraction of the cost
([study](https://arxiv.org/pdf/2603.02830)). Models extract evidence; math
computes mastery.

### The main families, briefly

- **Bayesian Knowledge Tracing (BKT)**: models mastery of one KC as a hidden
  binary state. Each practice opportunity updates the probability of mastery
  via Bayes' rule, with parameters for guessing, slipping, and learning rate.
  Simple, interpretable, per-facet.
- **Item Response Theory (IRT)**: places student ability and question
  difficulty on the same scale; the probability of a correct answer is a
  logistic function of the gap between them. This is what Duolingo's
  Birdbrain runs ([IEEE Spectrum](https://spectrum.ieee.org/duolingo)),
  layered on Half-Life Regression for forgetting: each skill has a memory
  half-life, and review timing follows it
  ([paper](https://research.duolingo.com/papers/settles.acl16.pdf)). This is
  the mature version of the timestamped-evidence idea: retention prediction
  as a computed view over dated evidence.
- **Knowledge Space Theory (KST)**: the foundation under ALEKS. A domain is a
  set of items with prerequisite relations; a student's knowledge state is a
  feasible subset of mastered items; the "fringe" (items one step beyond the
  current state) is both the most informative place to assess and the best
  place to teach next
  ([ALEKS](https://www.aleks.com/about_aleks/knowledge_space_theory)).
- **Fractional Implicit Repetition (FIRe)**: Math Academy's propagation
  model. Successfully practicing an advanced topic counts as implicit,
  fractional practice of the topics it builds on, so credit trickles down
  through the prerequisite graph, and review scheduling exploits this to
  minimize explicit reviews
  ([writeup](https://www.justinmath.com/the-tip-of-math-academys-technical-iceberg/)).
  This is the deployed, industrial version of the Perceptron-to-Neural-
  Networks intuition: progress on a composed concept flowing to and from its
  components.

### Where our design sits

Performance and coverage as currently sketched are counting-based: evidence
tallies over seen facets and facet counts over the concept. That is a
legitimate v1, and the important property is architectural: because mastery
is a computed view over an append-only evidence ledger, upgrading the math
(counting now, BKT or IRT per facet later, forgetting curves after that) is
swapping the view, not migrating the data. The systems above differ enormously
in sophistication but share our structure: evidence in, model over it,
mastery out.

---

## 6. Context engineering: injection, retrieval, and the scoped tool

### The reframing the field went through

2025 replaced the question "should we use RAG?" with the discipline of
context engineering: an LLM has a finite attention budget, and the job is
curating what enters it at each step
([Anthropic's canonical statement](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
Two findings dominate:

- Curated context beats indiscriminate retrieval when the needed scope is
  knowable in advance. The strongest production evidence is a tutoring
  system: Khanmigo's accuracy improved when Khan Academy switched to always
  gathering curated human-written exercises, hints, and solutions before
  responding, rather than retrieving freely
  ([Khan Academy](https://blog.khanacademy.org/khanmigo-math-computation-and-tutoring-updates/)).
- Where content is too large to inject wholesale, the winning pattern is
  progressive disclosure: inject a catalog (identifiers plus one-line
  descriptions), let the model fetch full bodies on demand from a bounded
  set. This pattern was standardized industry-wide in late 2025
  ([Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)).

### Mapped onto our system

The Companion's spine stays injection, and this is best practice, not legacy:
a session knows its lesson, the lesson knows its concepts and objectives, the
digests are compiled ahead of time. The eight requisites depend on that
control; a runtime retriever choosing context mid-lesson would surrender
cobertura and foco to a similarity score.

Retrieval enters as a scoped tool, exactly matching the image idea: the
injected context carries a catalog of the lesson's assets ("figure 3: diagram
of perceptron weight update, fetchable by ID"), and the tutor pulls a body
when pedagogically useful. The fetchable set is bounded to the lesson's own
sources; retrieval operates inside the curated scope and never defines it.
No vector search is needed for this: it is a catalog lookup by ID.

One constraint to carry into implementation: pieces that only make sense
together must travel together in one fetchable unit. A definition and the
examples that ground it, split into separately fetchable items, will arrive
separated. We have already learned this lesson internally with prompt
assembly; it applies unchanged to disclosure design.

---

## 7. What we are deliberately not adopting

**GraphRAG and its successors (LazyGraphRAG, LightRAG, HippoRAG).** These
exist to *recover* structure from large unstructured corpora so retrieval can
answer questions that span many documents. Our problem is the inverse: we
deliberately build curated structure with provenance as first-class domain
data. Adopting a GraphRAG framework would discard the curation that is the
product's asset in exchange for a lossy auto-built index
([practitioner's guide](https://medium.com/graph-praxis/graph-rag-in-2026-a-practitioners-guide-to-what-actually-works-dca4962e7517)).

**Dedicated graph databases (Neo4j and kin).** They pay off at deep
traversals (roughly six or more hops), pathfinding, and graph algorithms over
large graphs. Our traversals are two or three hops over thousands of nodes;
a benchmark showed Postgres beating Neo4j about 4x on exactly that shape of
query ([benchmark](https://www.pedroalonso.net/blog/graphrag-vs-vector-postgres/)).
Two supporting facts: PostgreSQL 19 is shipping standard property-graph query
syntax over ordinary tables
([docs](https://www.postgresql.org/docs/19/ddl-property-graphs.html)), and
the embedded graph DB Kuzu was abandoned in October 2025 when its team was
acqui-hired ([The Register](https://www.theregister.com/2025/10/14/kuzudb_abandoned/)),
a reminder of the dependency risk in niche databases. The plausible far-future
trigger for revisiting: research-scale optimal-learning-path computation over
data volumes we do not yet have.

**Dedicated vector databases.** Section 2: our scale is three to four orders
of magnitude below their value threshold.

---

## 8. Glossary: our vocabulary against industry vocabulary

| Ours | Theirs | Note |
|---|---|---|
| Facet | Knowledge component (KC) | Section 4; richest literature match |
| Objective | Learning objective / KC phrasing | Knewton's graphs were objective-based |
| Checking question | Assessment item | Q-matrix maps items to KCs |
| Facet matching | Entity resolution | Blocking + judging, section 3 |
| Embedding shortlist | Blocking / candidate generation | Recall-oriented stage |
| Checking-question judge | Pairwise LLM matcher | Precision-oriented stage |
| Digest | Compiled context / curated injection | The prompt-facing teaching summary |
| Asset catalog + fetch | Progressive disclosure | Standardized pattern, section 6 |
| Reference link | Prerequisite edge (curated) | FIRe/KST propagate mastery through these |
| Student ledger | Evidence / interaction log | Knowledge tracing consumes it |
| Mastery computation | Knowledge tracing | BKT, IRT, KST, FIRe families |

---

## 9. Suggested deeper reading, in order

1. [Math Academy's technical iceberg](https://www.justinmath.com/the-tip-of-math-academys-technical-iceberg/):
   the closest published blueprint to the Concept Universe; prerequisite
   graphs, mastery propagation, spaced review, diagnostics.
2. [Anthropic on context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents):
   the injection-versus-retrieval reframing in full.
3. [The rise of semantic entity resolution](https://towardsdatascience.com/the-rise-of-semantic-entity-resolution/):
   the matching loop, with tooling names.
4. [MTEB-BR](https://arxiv.org/html/2607.04581v2): skim the task list and the
   leaderboard; the methodology is reusable for our own matching evaluation.
5. [ALEKS on Knowledge Space Theory](https://www.aleks.com/about_aleks/knowledge_space_theory):
   short, and the "fringe" idea generalizes.
