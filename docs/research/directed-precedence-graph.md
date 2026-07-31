# From proximity groups to a directed precedence graph: KC identity as mutual mastery implication

Research memo, 2026-07-30. Scope: the design evolution decided in the founder
sessions of 2026-07-29/30, after the blind review of run r0130 ended the
embedding-proximity grouping plan. It replaces similarity-based KC formation
with a directed graph of mastery-implication verdicts over permanent unitary KCs,
and grounds each component of the new design in primary literature. This memo
documents the design under discussion; it is the basis for a future ADR and
decides nothing by itself. Prior memo on clustering-from-pairwise-verdicts:
[entity-resolution-grouping.md](entity-resolution-grouping.md) — its Policy C
(correlation clustering), shelved there in favor of the canonical anchor, is
promoted here to the foundation.

Terminology mapping used throughout:

| our term | meaning | literature counterpart |
| - | - | - |
| unitary KC | the permanent unit born from one task; insert-only | KLI knowledge component as inferred from one task ([Koedinger, Corbett & Perfetti 2012](http://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf)); ER record |
| evidence | the per-task record backing a unitary KC: task, answer, class-neutral knowledge statement, two voted axes | the observations a KC is inferred from |
| KC | derived snapshot: a cluster recomputed from the edge ledger; one unitary KC alone, or 2+ merged | resolved entity / cluster; KLI KC at the model grain size the evidence supports |
| composite KC | a KC holding 2+ unitary KCs merged by double arrows | multi-record resolved entity |
| directional edge A→B | one judged verdict: "mastery of A implies mastery of B" | surmise relation of knowledge space theory ([Doignon & Falmagne 1985](https://www.sciencedirect.com/science/article/abs/pii/S0020737385800316)) |
| double arrow A⇄B | both directions judged yes: same KC | mutual surmise (equally informative items); must-link edge |
| single arrow | one direction yes: nested relation, kept as map structure | strict surmise; precedence |
| tested-negative edge | a direction judged no | (−) edge of a signed graph ([Cartwright & Harary 1956](https://ucilnica.fri.uni-lj.si/pluginfile.php/1147/course/section/4647/Cartwright%20and%20Harary%20-%20Structural%20balance%20-%20A%20generalization%20of%20Heiders%20theory%2C%201956.pdf)) |
| tension | a tolerated negative edge inside a formed KC | frustrated edge / disagreement ([Bansal, Blum & Chawla 2004](https://link.springer.com/article/10.1023/B:MACH.0000033116.57574.95)) |
| pendência (pending state) | a double arrow that cannot yet close a clique with any group; a label on a live object, not a queue for humans | unresolved constraint awaiting evidence |
| node health | internal vs external double-arrow degree of a unitary KC | within-module degree and participation coefficient ([Guimerà & Amaral 2005](https://www.nature.com/articles/nature03288)) |

Terminology updated 2026-07-31 by founder decision: "grain" is retired; the
unit is the unitary KC, merged clusters are composite KCs, and the per-task
record (task, answer, statement, axes) is the unitary KC's evidence. Earlier
documents and run ledgers keep the historical term.

Arrow convention, fixed for the whole system: **A→B means "mastery of A
implies mastery of B". The arrow points from advanced to basic. Learning
order reads the arrows backwards.** This is stated once here and assumed
everywhere below.

---

## 1. Where we came from

The pipeline (state in [docs/pipeline-defaults.md](../pipeline-defaults.md))
extracts per-task knowledge units from source material: currently 33 units
from one Bag-of-Words article, each carrying a task, an answer, a
class-neutral knowledge statement (kc-statement v005, reference run r0130),
and two axes voted by a model panel (modality explain/do, knowledge-type
concept/procedure). The plan of record — ADR
[0010](../adr/0010-task-first-grain-extraction.md) stage 4 plus ADR
[0007](../adr/0007-kc-grouping-canonical-anchor.md) — was: embed the
statements, form proximity groups by cosine threshold, and have an LLM judge
merge group members into merged units and KCs, with membership anchored to a canonical
phrasing to prevent chaining.

The blind review of 2026-07-29
([reports/blind-review-2026-07-29-r0130-gemini.md](../../reports/blind-review-2026-07-29-r0130-gemini.md))
ended that plan with three findings:

1. **No similarity valley.** On a single-topic corpus, all 528 pairwise
   cosines live in 0.547–0.941; background (unrelated same-topic pairs) has
   median 0.695 and kinship starts around 0.79 — a gap of ~0.09 with no
   valley between the modes. Any absolute threshold is a knife-edge, and the
   review's own conclusion was that thresholds calibrated here will not
   transfer to other corpora or embedding models.
2. **Edge-threshold + connected components fails at every threshold.** At
   t = 0.80 the largest component swallows 20 of 33 nodes; at 0.84 it is
   still a 10-node chain; by 0.86, when components finally look sane, true
   kin pairs are already lost (sparse vectors at 0.827, CountVectorizer at
   0.799, tokenization at 0.787). This is the chaining failure the prior
   memo predicted from the ER literature (transitive closure precision 0.101
   in the Stringer benchmark; see
   [entity-resolution-grouping.md §1.1](entity-resolution-grouping.md)),
   now measured on our own data.
3. **The worst hubs are compound statements.** The degree-10 hub at t = 0.80
   is a BOW definition with a bolted-on "disregarding word order" clause; the
   clause relocates the statement into the *limitations* group (0.907 to the
   order-limitation statement) away from its natural definition sibling
   (0.832). One clause moved a statement across a KC boundary. Compoundness
   is not a cosmetic prompt defect; it is the single biggest structural
   failure of similarity-based grouping.

The review still salvaged useful machinery — average-linkage clustering finds
a shelf, panel axis-splits co-locate with geometric ambiguity 4-for-4 — but
the founder read the deeper lesson: on realistic corpora, semantic proximity
of statement *wording* does not define knowledge identity. Something else
must.

## 2. The turn: extensional identity and the directional primitive

Two ideas introduced by the founder in the 2026-07-29/30 sessions replace the
proximity model.

**Extensional identity via question pools.** A unitary KC's identity is not
its statement wording; it is the set of tasks/questions that test it. Two
unitary KCs are the same knowledge exactly when a learner who can answer one's question
pool can answer the other's, and vice versa. Statement text becomes evidence
about the pool, not the identity itself. This is precisely the KLI
framework's definition of a knowledge component: "an acquired unit of
cognitive function or structure that can be inferred from performance on a
set of related tasks"
([Koedinger, Corbett & Perfetti 2012](http://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf),
already adopted in ADR 0010 as the definition of the unit). In KLI practice two
tasks tap the same KC exactly when practice transfers between them, and a KC
model is validated empirically by whether learning curves smooth out under
it — the Learning Factors Analysis / Additive Factor Model tradition
([Cen, Koedinger & Junker 2006](https://link.springer.com/chapter/10.1007/11774303_17))
running over DataShop-style performance data
([Koedinger et al. 2010](https://www.semanticscholar.org/paper/A-Data-Repository-for-the-EDM-Community:-The-PSLC-Koedinger-Baker/c2d3a1661a97f10ad29d2ea56e09981e4cb758e1)).
Our LLM judge is a stand-in for that empirical transfer test until real
learner data exists (§10).

**The directional primitive.** The judge's question stops being symmetric
("are these the same?") and becomes directional: *"does mastery of A imply
mastery of B?"* — one direction per call, two calls per pair. Verdict
semantics:

- **Both directions yes (double arrow A⇄B): same KC.** Identity is defined
  as mutual implication over the question pools.
- **One direction yes (single arrow): a nested relation.** The unitary KCs
  are distinct; the arrow is kept as knowledge-map structure (§6).
- **Neither, or partial: distinct unitary KCs**, possibly related by weaker
  relations later.

This primitive has a fifty-year-old formal home: knowledge space theory's
**surmise relation**. Doignon & Falmagne define it on a domain of questions
as q ≤ q′ iff mastering q′ implies having mastered q — from a correct answer
to one item you may *surmise* mastery of the other
([Doignon & Falmagne 1985](https://www.sciencedirect.com/science/article/abs/pii/S0020737385800316),
Int. J. Man-Machine Studies 23:175–196; book-length treatment in *Learning
Spaces*, Springer 2011). Two properties of KST matter to us:

1. **It is deliberately causality-agnostic.** The surmise relation asserts a
   regularity over knowledge states — states containing q′ also contain q —
   and stays silent on *why*: pedagogy, logical dependency, curricular
   convention, or cognitive containment. The founder independently insisted
   that our direction must not be auto-labeled "prerequisite"; KST validates
   this instinct. An arrow is an observed implication, not a curriculum
   claim.
2. **It runs at scale in production.** ALEKS (Assessment and LEarning in
   Knowledge Spaces) is the applied system: knowledge states as sets of
   solvable problems, assessment navigating the precedence structure
   ([Cosyn, Uzun, Doble & Matayoshi 2021](https://www.sciencedirect.com/science/article/abs/pii/S0022249621000134),
   J. Math. Psychology 101; [ALEKS research pages](https://www.aleks.com/about_aleks/knowledge_space_theory)).
   The structure we are building is a surmise-relation graph whose items are
   unitary KCs and whose oracle is an LLM judge instead of expert querying.

For positioning: the education-NLP literature on *prerequisite* graphs —
[Talukdar & Cohen 2012](https://aclanthology.org/W12-2037/) predicting
prerequisite structure in Wikipedia,
[Liang et al. 2015](https://aclanthology.org/D15-1193/)'s reference-distance
metric, [Pan et al. 2017](https://aclanthology.org/P17-1133/) on MOOC
concepts — learns asymmetric *curricular* relations between named topics
from document signals. Ours is a different relation (mastery implication
between tested unitary KCs, judged pairwise) even though the graph shape is
similar; the non-"prerequisite" naming is load-bearing, not cosmetic.

## 3. The graph model

- **Nodes: unitary KCs.** Permanent and insert-only (unchanged from ADR 0010
  and consistent with the frozen-id policy of ADR 0008). A unitary KC is
  never edited in place by graph operations; the compound fix (§6) *splits*
  a unitary KC into new unitary KCs and retires the old one, which is an
  insert-only event.
- **Edges: stamped directional verdicts.** Each ordered pair judged gets one
  verdict, stored forever with its run stamp. An edge is judged **once per
  direction and never re-asked** (§7 for why). The ledger distinguishes
  three edge states per direction: yes, no (tested-negative), and untested —
  the untested/negative distinction is structural, not cosmetic (§5).
- **KCs: derived snapshots.** A KC is a cluster computed from the current
  edge ledger. It is recomputed — never hand-edited — as content arrives or
  the pipeline improves. Ingesting a new source runs the identical process:
  new unitary KCs are extracted, candidates proposed, directions judged, clusters
  recomputed. There is no special cross-source phase; the graph is the
  integration mechanism.
- **Terminology shift.** What ADR 0010 called "grains" produced by a
  grouping step are now the per-task units themselves — **unitary KCs** —
  and what it called KCs are the derived snapshots (**composite KCs** when
  they hold 2+ unitary KCs). The old intermediate ("proximity group → grain
  → KC") disappears.

## 4. Group formation as signed-graph clustering

The double-arrow subgraph plus tested-negative edges is a signed graph, and
KC formation is clustering on it. The literature chain:

**Structural balance.** [Heider 1946](https://psychclassics.yorku.ca/Heider/attitudes.htm)
(J. Psychology 21:107–112) introduced balance over triads of sentiment
relations; [Cartwright & Harary 1956](https://ucilnica.fri.uni-lj.si/pluginfile.php/1147/course/section/4647/Cartwright%20and%20Harary%20-%20Structural%20balance%20-%20A%20generalization%20of%20Heiders%20theory%2C%201956.pdf)
(Psychological Review 63:277–293) generalized it to signed graphs: a
triangle with two positive edges and one negative is *unbalanced*. Our
central anomaly — judge says A⇄B same, A⇄C same, but B≠C — is exactly an
unbalanced triangle. Balance theory tells us such triangles are not
paradoxes to be resolved by fiat but *tension* carried by the structure, and
a rising count of them is a health signal (the prior memo's §4.6 already
proposed monitoring them; the new design makes them first-class objects).

**Correlation clustering.** Given a signed graph, partition the nodes to
minimize disagreements (negative edges inside clusters plus positive edges
across). [Bansal, Blum & Chawla 2004](https://link.springer.com/article/10.1023/B:MACH.0000033116.57574.95)
(Machine Learning 56:89–113) formalized this and proved it NP-hard even on
complete graphs; standard practice is greedy/local approximation. Our graph
is incomplete (most pairs untested), which is the general weighted case
([Demaine, Emanuel, Fiat & Immorlica 2006](https://erikdemaine.org/papers/Clustering_TCS/),
Theoretical Computer Science 361:172–187, APX-hard) — another reason to
prefer cheap local rules over global optimization. The prior memo's Policy C
described exactly this ("conflicts are the normal input; correlation
clustering is literally defined as minimizing disagreement with conflicting
edges") and shelved it for id-stability reasons; the new design adopts its
worldview while neutralizing the id concern, because ids live on unitary KCs
(permanent) and KCs are declared snapshots with no pretense of engine-level
stability. FAMER-style local repair (re-cluster only the touched
neighborhood; see prior memo §1.5) remains the recompute pattern.

**The v1 clustering rule** is not an optimizer but a fixed, auditable
predicate over double arrows:

- **Size 2–3: perfect clique required.** Every pair in the group must be a
  tested double arrow.
- **Size ≥ 4: k-plex with tolerance 1.** Each member may carry at most one
  tested-negative internal edge; in
  [Seidman & Foster 1978](https://www.semanticscholar.org/paper/A-graph%E2%80%90theoretic-generalization-of-the-clique-Seidman-Foster/6ab2c1037c92bc29336815f8a3b1dd38c467035c)'s
  terms (J. Math. Sociology 6:139–154: a k-plex of size n has every vertex
  adjacent to at least n−k members; a clique is a 1-plex) our groups of size
  ≥ 4 are **2-plexes** over the double-arrow graph. The size split is
  exactly why Seidman & Foster restrict attention to k small relative to n:
  for n ≤ 3 a 2-plex is degenerate (a 3-node path qualifies), so small
  groups must be perfect cliques.
- **A tolerated internal negative is logged as *tension***, permanently
  attached to the KC snapshot. Tension is the input to node health (§5),
  not an error to be silently absorbed.
- **Tested-negative ≠ untested.** Only tested negatives count against the
  plex tolerance. Untested internal edges are a to-do, not evidence, and the
  entry rule keeps them rare: **a unitary KC joining a group is tested against
  all current members** (both directions each), so groups are fully tested
  at admission time and tolerance is spent only on genuine judge conflict.

Among the clique-relaxation family, k-plex is the right fit because it
bounds *per-member* missing edges — matching our semantics that one bad
verdict should not exile a member, but a member accumulating negatives is
suspect. k-core ([Seidman 1983](https://www.sciencedirect.com/science/article/abs/pii/037887338390028X),
Social Networks 5:269–287) bounds minimum degree without bounding size and
famously fails to split large contaminated families (the Amazon result in
the prior memo §1.3); density-based quasi-cliques bound only the aggregate
edge count and would let one member carry all the missing edges. We use
"quasi-clique" informally in conversation; the precise v1 rule is the
2-plex above.

## 5. Node health and the diagnostic menu

A unitary KC's membership strength is read off the graph, not re-litigated by
judges. The measure is the split between **internal degree** (double arrows
to own-KC members) and **external degree** (double arrows out of the KC) —
the community-cartography pair of within-module degree and participation
coefficient from
[Guimerà & Amaral 2005](https://www.nature.com/articles/nature03288)
(Nature 433:895–900): a node with links spread across modules (participation
coefficient near 1) is a connector or, in our reading, a suspect unitary KC; a
node with all links inside (near 0) is embedded. Exact flag thresholds are
calibration knobs deferred to the operational test (§10).

When a node is flagged, a **diagnostic menu** runs, ordered by cost:

0. **Fill untested edges in the region.** Cheapest; often the anomaly is an
   artifact of incompleteness. This is triadic-closure logic used as a test
   scheduler: where two strong ties exist, the third side should be examined
   — Granovetter's forbidden-triad argument
   ([Granovetter 1973](https://www.cs.cmu.edu/~jure/pub/papers/granovetter73ties.pdf),
   AJS 78:1360–1380) applied to verdicts instead of friendships.
1. **Compound check.** A dedicated exam on the unitary KC itself: "does this
   statement make more than one claim?" If yes, split into new unitary KCs
   (insert-only; the old one retires). The blind review proved compound
   statements are the dominant bridge mechanism, so this check is expected
   to pay for itself.
2. **Vagueness check.** The statement underdetermines its question pool;
   rewrite (again as a new unitary KC version).
3. **Downgrade double→single.** The identity verdict was actually a nesting
   caught too coarsely. Expected to be the most common resolution: the
   judge's yes/yes becomes yes/no, the unitary KC leaves the composite KC but stays on the
   map as a single arrow.
4. **The other endpoint is defective.** Symmetric application of 1–3 to the
   neighbor.
5. **Escalation of the specific conflicting edges to a stronger model.**
   Rare, structurally triggered, and the *only* place re-judging exists in
   the design.

**Hub taxonomy** (reading high-degree nodes): many *incoming* arrows =
foundational content — many advanced masteries imply it; this signal
strengthens as the corpus grows. Many *outgoing* arrows = advanced position,
and explicitly **not** proof of compoundness: the founder's counterexample
is a physician's clinical mastery implying elementary biology across many
territories — legitimately broad outgoing implication from one coherent
skill. Compoundness is diagnosed only by the direct exam (menu item 1),
never inferred from degree. Under a graded verdict scale (a 4-level
candidate idea, undecided — §10): strong doubles in a coherent neighborhood
mark the central unitary KC of a large composite KC; strong doubles across an incoherent
neighborhood raise compound suspicion; weak doubles everywhere indicate a
vague statement.

## 6. The relations layer: single arrows are the map

Single (one-way) arrows never threaten membership; they are the product. The
knowledge map's KC-to-KC structure is **inherited from member arrows**: if
unitary KCs of KC X carry arrows into unitary KCs of KC Y, X relates to Y.
This includes **cross-axis links**: unitary KCs on different axes (a
procedure-do and a concept-explain one) can relate by arrows but can never
merge into one composite KC — the axes partition identity but not structure.

**Non-transitivity is a rule, not an accident.** A→B and B→C never
auto-derive A→C as a fact. KST's surmise relation is transitive as an
idealization; our edges are noisy judge outputs, and the prior memo's
evidence (crowd-ER transitive inference breaking under noise, §1.4; measured
LLM transitivity violations,
[Liu et al. 2024](https://arxiv.org/abs/2410.02205)) says trusting chains
multiplies error. At most, a chain generates a *candidate* edge with decayed
confidence — the founder's illustrative scheme: one hop 0.8, two hops 0.64 —
queued for future judging like any other candidate. If real learner data
ever arrives (§10), those decays could become estimated probabilities
instead of priors.

**Candidate generation.** Embedding proposes pairs; it **never decides
truth, only who gets tested**. The v1 mechanism is per-node top-k nearest
neighbors rather than a global cosine threshold: linear cost in corpus size,
and it adapts to local density where a global threshold provably fails on
our geometry (§1). Structural proposals join the same queue: the untested
third side of a two-double-arrow path (triadic closure again), and decayed
chain candidates. All candidates flow into the same once-per-direction
judging.

## 7. The resilience model

The founder explicitly rejected verdict-scoreboards and routine re-sampling
for v1, on an infinite-regress argument: if three judgments disagree,
nothing guarantees a fourth converges, and a system that re-asks forever
never has a ledger, only a mood. Resilience instead comes from four
structural sources:

1. **Edges are judged once per direction and stamped.** The ledger is
   append-only fact, in the spirit of ADR 0001's facts-versus-
   interpretations split: the verdict *event* is a fact even when the
   verdict is wrong.
2. **KCs are derived views.** Any improvement — new unitary KCs, new edges, a
   better clustering rule — recomputes snapshots from the same ledger. No
   wrong verdict is load-bearing forever, because nothing downstream is
   hand-built on it.
3. **Evidence dilution.** As the graph grows, a wrong edge is increasingly
   outvoted by the structure around it: one bad double arrow cannot hold a
   unitary KC in a group against accumulating negatives (the plex rule), and one
   bad negative costs only a logged tension.
4. **New-question exams, not re-asks.** Structural symptoms (flags from §5)
   trigger *new* questions — compound exam, vagueness exam, fresh edges in
   the region — rather than repeating an old question hoping for a
   different answer. The escalation rung (menu item 5) is the sole,
   structurally-gated exception.

The **whole-set gate** survives from ADR 0007 in weakened, asymmetric form:
once a KC closes, a single judge call may read the entire member set and ask
"could one learner state explain all these tasks?" It can only **veto**
(reopen the KC as pendências), never merge or admit. The asymmetry is
deliberate: a gate that can override the pairwise layer in both directions
is a judge judging judges, which reopens the regress the once-per-direction
rule closed. The set-level view's value is documented (the Amazon
cluster-health result and the ComEM joint-view findings in the prior memo,
§§1.3, Policy D); veto-only keeps the value without the regress.

**Pendências.** A double arrow that cannot close a clique with any existing
group becomes a *pending* label on a live object — a lone unitary KC remains
its own active KC while pending. Pendências are resolved by future evidence
(new unitary KCs, new edges) — not by humans. The human role in this design is
operator: watch a dashboard of flags, tensions and pendência counts, tune
knobs, improve prompts. Humans never hand-decide content questions — a
sharpened restatement of ADR 0007's "recurring conflicts are a signal to
improve the system, not to automate the disputes away", with the human moved
one level further from the individual dispute.

## 8. Cost model

Measured on the r0130 corpus of 33 unitary KCs: per-node top-5 candidate generation
yields 125 unique pairs = 250 directional judge calls. Extrapolated at the
same k: ~1000 unitary KCs → ~8000 calls. The scheme is linear in corpus size for
fixed k (each node proposes k pairs, deduplicated), against quadratic for
exhaustive pairing (33 units: 528 pairs; 1000 units: ~500k pairs). Entry
testing (a joining unitary KC judged against all members) adds cost proportional
to group size, which stays small (~1.65 tasks/KC measured on this corpus,
expected to fall toward 1 on multi-source corpora per the blind review).
Diagnostic exams and escalations are triggered, not scheduled, so their cost
scales with anomaly count, not corpus size.

## 9. Open questions

Honestly open, in rough priority order:

1. **Flag thresholds** for internal/external degree (embeddedness): numbers
   deferred to the operational test.
2. **k for top-k candidate generation**: 5 is the measured default;
   untested whether recall of true kin pairs holds at 5 on mixed corpora.
3. **The 4-level graded verdict scale**: adopt, or stay binary per
   direction? If adopted, how graded verdicts aggregate into the
   clique/plex predicate is undesigned.
4. **The whole-set veto gate**: keep, or drop as redundant once node health
   works? Its regress-safety is argued, its marginal value unmeasured.
5. **Prompt design for the directional mastery question.** Unusually,
   biasing the judge with literature framing (KLI transfer language, KST
   surmise language) is considered genuinely helpful here rather than
   contamination — the framing *is* the definition of the relation. To be
   A/B tested like every stage prompt.
6. **The operational test**: run the full loop (candidates → 250 directional
   calls → plex formation → health flags → diagnostics) on the 33-unit
   corpus, with the blind review's manual grouping as the comparison
   partition. This is the next concrete step.
7. **Learner-data audit**: real learning curves are the ground truth this
   whole design proxies. When learner performance data exists, AFM-style
   curve analysis ([Cen et al. 2006](https://link.springer.com/chapter/10.1007/11774303_17))
   can audit KC snapshots (a KC whose members don't transfer shows as a
   ragged curve), and observed state prevalences can audit arrows the way
   ALEKS audits its structure against response data
   ([Cosyn et al. 2021](https://www.sciencedirect.com/science/article/abs/pii/S0022249621000134)).
   Whether decayed chain-candidates graduate into estimated probabilities
   lives here too.

## 10. Implications for existing ADRs

No ADR is edited until the founder freezes this design. When that happens:

- **ADR 0007 (canonical anchor + whole-set gate): superseded in part.** The
  canonical-anchor membership policy is replaced by double-arrow plex
  formation — the anchor prevented chaining by construction, and the
  directional primitive now prevents it by making identity mutual and
  tested. 0007's instincts survive transformed: the quarantine of
  multi-match units becomes the pendência state; the whole-set gate
  becomes veto-only; "verdicts stored as stamped facts" becomes the edge
  ledger, which was 0007's stated prerequisite for future repair and is now
  the system's backbone. The human-decides-conflicts rule is replaced by
  the operator model (§7).
- **ADR 0010 (task-first extraction): stages 1–3 and the amendments stand
  unchanged; stage 4 (grouping) and stage 5 (naming) are redefined.**
  Grouping is no longer embed-cluster-merge; it is candidate generation +
  directional judging + snapshot clustering. Naming attaches to derived KC
  snapshots rather than merge-produced units. The reliability metric
  ("re-run and compare final grains in embedding space") needs restating
  over graph outputs.
- **ADR 0008 (frozen ids): reinforced.** Unitary KCs are the permanent id-bearing
  layer; KC snapshot ids are explicitly derived and re-mintable, which
  resolves the id-stability objection that shelved correlation clustering
  in the prior memo.

## 11. Sources

Knowledge space theory:
- Doignon, Falmagne. Spaces for the assessment of knowledge. Int. J. Man-Machine Studies 23, 1985. https://www.sciencedirect.com/science/article/abs/pii/S0020737385800316
- Falmagne, Doignon. Knowledge Spaces and Learning Spaces (survey of the 2011 Springer book). https://arxiv.org/abs/1511.06757
- Cosyn, Uzun, Doble, Matayoshi. A practical perspective on knowledge space theory: ALEKS and its data. J. Mathematical Psychology 101, 2021. https://www.sciencedirect.com/science/article/abs/pii/S0022249621000134 (preprint: https://jmatayoshi.github.io/publications/JMP2021_KST_ALEKS_preprint.pdf)
- ALEKS. Knowledge Space Theory research pages. https://www.aleks.com/about_aleks/knowledge_space_theory

KLI and learning-curve validation:
- Koedinger, Corbett, Perfetti. The Knowledge-Learning-Instruction Framework. Cognitive Science 36(5), 2012. http://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf
- Cen, Koedinger, Junker. Learning Factors Analysis — A General Method for Cognitive Model Evaluation and Improvement. ITS 2006. https://link.springer.com/chapter/10.1007/11774303_17
- Koedinger, Baker, Cunningham, Skogsholm, Leber, Stamper. A Data Repository for the EDM Community: The PSLC DataShop. Handbook of Educational Data Mining, CRC Press 2010. https://www.semanticscholar.org/paper/A-Data-Repository-for-the-EDM-Community:-The-PSLC-Koedinger-Baker/c2d3a1661a97f10ad29d2ea56e09981e4cb758e1

Signed graphs and clustering:
- Heider. Attitudes and Cognitive Organization. J. Psychology 21, 1946. https://psychclassics.yorku.ca/Heider/attitudes.htm
- Cartwright, Harary. Structural Balance: A Generalization of Heider's Theory. Psychological Review 63(5), 1956. https://ucilnica.fri.uni-lj.si/pluginfile.php/1147/course/section/4647/Cartwright%20and%20Harary%20-%20Structural%20balance%20-%20A%20generalization%20of%20Heiders%20theory%2C%201956.pdf
- Bansal, Blum, Chawla. Correlation Clustering. Machine Learning 56, 2004. https://link.springer.com/article/10.1023/B:MACH.0000033116.57574.95
- Demaine, Emanuel, Fiat, Immorlica. Correlation Clustering in General Weighted Graphs. Theoretical Computer Science 361, 2006. https://erikdemaine.org/papers/Clustering_TCS/

Cohesive subgroups and node roles:
- Seidman, Foster. A graph-theoretic generalization of the clique concept. J. Mathematical Sociology 6, 1978. https://www.semanticscholar.org/paper/A-graph%E2%80%90theoretic-generalization-of-the-clique-Seidman-Foster/6ab2c1037c92bc29336815f8a3b1dd38c467035c
- Seidman. Network structure and minimum degree. Social Networks 5, 1983. https://www.sciencedirect.com/science/article/abs/pii/037887338390028X
- Guimerà, Amaral. Functional cartography of complex metabolic networks. Nature 433, 2005. https://www.nature.com/articles/nature03288
- Granovetter. The Strength of Weak Ties. American J. Sociology 78(6), 1973. https://www.cs.cmu.edu/~jure/pub/papers/granovetter73ties.pdf

LLM judge consistency:
- Liu, Guo, Liang, Shareghi, Vulić, Collier. Aligning with Logic: Measuring, Evaluating and Improving Logical Preference Consistency in Large Language Models. 2024. https://arxiv.org/abs/2410.02205

Prerequisite-graph learning (positioning, not adoption):
- Talukdar, Cohen. Crowdsourced Comprehension: Predicting Prerequisite Structure in Wikipedia. BEA workshop, NAACL 2012. https://aclanthology.org/W12-2037/
- Liang, Wu, Huang, Giles. Measuring Prerequisite Relations Among Concepts. EMNLP 2015. https://aclanthology.org/D15-1193/
- Pan, Li, Li, Tang. Prerequisite Relation Learning for Concepts in MOOCs. ACL 2017. https://aclanthology.org/P17-1133/

Internal:
- Prior memo: [entity-resolution-grouping.md](entity-resolution-grouping.md) (ER clustering policies; Policy C promoted here).
- Blind review: [reports/blind-review-2026-07-29-r0130-gemini.md](../../reports/blind-review-2026-07-29-r0130-gemini.md).
- ADRs [0001](../adr/0001-facts-versus-interpretations.md), [0007](../adr/0007-kc-grouping-canonical-anchor.md), [0008](../adr/0008-kc-identity-frozen-ids.md), [0010](../adr/0010-task-first-grain-extraction.md).
- Axis groundwork: [docs/lab/axis-definitions-research.md](../lab/axis-definitions-research.md) (KLI reading notes; adoption of the unit definition).
