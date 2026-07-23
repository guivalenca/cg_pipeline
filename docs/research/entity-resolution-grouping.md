# Grouping pairwise match verdicts into Knowledge Components: literature and industry practice

Research memo, 2026-07-23. Scope: how to turn pairwise LLM match verdicts over learning objectives into stable KC membership, with durable ids and an auditable merge/split trail. Sources: entity resolution (ER) literature, Master Data Management (MDM) practice, crowdsourced ER, and LLM-based ER work from 2023 onward.

Terminology mapping used throughout: our "objective" = an ER record; our "KC" = a resolved entity / cluster; our "canonical phrasing" = the golden record / cluster representative; our BLOCKING and JUDGING stages match the standard ER pipeline of blocking then matching then clustering. The stage we are missing is the third one, clustering, and the literature is unanimous that it is a distinct stage with its own algorithms, not a byproduct of pairwise verdicts.

---

## 1. Known failure modes of naive transitive merging

### 1.1 Chaining (the single-link effect)

Transitive closure over pairwise matches (called Partitioning or connected components in the literature) is the classic baseline and the classic failure. Hassanzadeh, Chiang, Lee and Miller evaluated 11 unconstrained clustering algorithms over similarity graphs for duplicate detection (Stringer framework, VLDB 2009). Their summary of Partitioning: "the algorithm may result in big clusters, the results in many records that are not similar being put in the same cluster." Numerically, at threshold 0.2 on medium-error datasets, Partitioning scored penalized clustering precision 0.101 while CENTER scored 0.593, Star 0.614, correlation clustering 0.612 and Markov clustering 0.599. Recall was high (0.953) precisely because everything welds together. Their conclusion: transitive closure "results in poor quality of duplicate groups... even when compared to other clustering algorithms that are as efficient." ([paper PDF](http://www.vldb.org/pvldb/vol2/vldb09-1025.pdf))

This is exactly our A-B-C scenario: two true matches plus one borderline edge produce one welded cluster, and each additional vague record extends the chain.

### 1.2 Bridge records: one vague item welds two skills

A vaguely phrased objective that plausibly matches two distinct skills becomes an articulation point in the match graph: a single node whose removal disconnects the cluster. The literature treats such structures as the signature of a bad merge:

- Articulation Point Clustering in the Stringer study exploits exactly this: it splits clusters at articulation points because those nodes are the least trustworthy links.
- Splink (UK Ministry of Justice, probabilistic linkage at national-statistics scale) ships graph metrics whose stated purpose is to "identify possible false positive links in clusters"; bridge edges and low cluster density are the flags. A cluster held together by one edge or one node is treated as suspect by default. ([Splink cluster evaluation](https://moj-analytical-services.github.io/splink/topic_guides/evaluation/clusters/overview.html), [graph metrics](https://moj-analytical-services.github.io/splink/topic_guides/evaluation/clusters/graph_metrics.html))

### 1.3 Pairwise views cannot see cluster-level incoherence

Barton, Neiman and Yuan (Amazon, WWW 2021 workshop) give a concrete example from product families: a 10-member cluster with exactly one wrong member has 45 pairs, of which 36 are correct matches and only 9 are mismatches, "and one or two of the 9 scores for mismatched edges may be high." Transitive closure and k-core both fail to split such a family. Their conclusion is that cluster health is a property of the whole set and must be scored as such (they train a GNN graph classifier to score candidate clusters before committing them; the earlier SuperPart model does the same with hand-built graph features such as mean weight of edges removed by transitive closure). ([arXiv 2105.05957](https://arxiv.org/abs/2105.05957))

### 1.4 Verdict noise is amplified by transitive inference

The crowdsourced ER line of work used transitivity to save money: given a=b and b=c, infer a=c without asking (Wang et al., SIGMOD 2013, "Leveraging Transitive Relations for Crowdsourced Joins"). It works only under near-perfect answers. Follow-up work exists specifically because it breaks under noise: with imperfect workers a single wrong positive propagates through every inferred edge, so later systems model crowd error explicitly, use control queries, and choose question order to bound the damage (Galhotra et al., "Select Your Questions Wisely: For Entity Resolution With Crowd Errors"; Vesdapunt et al., "Crowdsourcing Algorithms for Entity Resolution"). ([SIGMOD 2013](https://dl.acm.org/doi/pdf/10.1145/2463676.2465280), [arXiv 1701.08288](https://arxiv.org/pdf/1701.08288), [PVLDB 2014](https://dl.acm.org/doi/10.14778/2732977.2732982))

LLM judges inherit this problem and it is now measured: work on logical consistency of LLMs measures transitivity violations directly and finds that "LLMs with better transitivity perform better in entity matching tasks"; transitivity is proposed as a proxy for global reliability of the judge ([arXiv 2410.02205](https://arxiv.org/html/2410.02205v1)). So we should expect intransitive verdict sets (A=B, B=C, A≠C) as a normal operating condition, not an anomaly. A policy that has no answer for an explicit negative edge inside a would-be cluster is incomplete.

### 1.5 Incremental greedy assignment is order dependent

Saeedi, Peukert and Rahm (FAMER, ESWC 2020) studied exactly our setting: entities arriving over time, each greedily attached to the best existing cluster. Their max-both merge strategy (attach only when the link is the mutually best link in both directions) is good but still order dependent: worst-case insertion order produced "substantially lower recall and F-measure," while a repair mechanism (n-depth reclustering: re-cluster the new entity together with its graph neighborhood out to depth n) restored batch-level quality and made results "independent from the order in which new entities are added," at about one fifth the cost of full reclustering. ([ESWC 2020 open access](https://pmc.ncbi.nlm.nih.gov/articles/PMC7250616/), [FAMER project](https://dbs.uni-leipzig.de/research/projects/famer))

Lesson: a system that only ever appends to clusters and never revisits the neighborhood of a new arrival will accumulate order artifacts. A cheap local repair step is the known fix; full periodic re-runs are not required.

### 1.6 Canonical drift: the golden record poisons itself

Our canonical-phrasing refresh is the MDM golden record / survivorship process: after matching, survivorship rules decide which values form the canonical representation ([Profisee on survivorship](https://profisee.com/blog/mdm-survivorship/), [D&B on golden records](https://www.dnb.com/en-us/resources/master-data/what-are-golden-records-in-master-data-management.html)). The known failure: once a wrong record survives into the golden record, the canonical representation moves toward the intruder, and because matching runs against the canonical, the poisoned center attracts further wrong matches. In our design this loop is tighter than in classical MDM because we re-embed the refreshed canonical and use that vector for blocking: a single bad admission shifts the KC's position in embedding space and changes all future candidate lists.

Senzing's "generic value" mechanism is the relevant countermeasure pattern: when an attribute value (their example: an SSN shared by many people) turns out to match too many entities, the system demotes it as evidence and re-evaluates every prior decision that relied on it ([Senzing principle-based ER](https://senzing.com/what-is-principle-based-entity-resolution/)). Our analog: an objective whose embedding sits near many KC canonicals is by that fact weak evidence, and any merge it motivated should be flagged rather than trusted.

---

## 2. Candidate grouping policies

Common vocabulary for all policies below. Every pairwise verdict is stored permanently as a signed edge: match (+), no-match (−), uncertain (0, pending). Human answers are stored as constraint edges (must-link / cannot-link) that are never overridden by later automated runs; this is exactly Zingg's rule that incremental flows must not override human-approved records ([Zingg incremental flow](https://www.zingg.ai/post/fuzzy-matching-at-scale-part-5-incremental-flow-and-living-clusters)). The differences between policies are in what a KC is defined by, and what happens on multi-match.

### Policy A: Transitive merge with negative-edge veto (minimal fix)

Operational rules:
- 0 candidates match: create a new KC.
- 1 KC matches: attach; refresh canonical.
- 2+ KCs match: attach to the best one; the implied KC-KC merge is NOT executed automatically; it becomes a merge proposal that requires either a fresh whole-set judgment or a human.
- Any proposed attachment or merge that would place a cannot-link (human) or a strong LLM no-match edge inside one KC is blocked and routed to a human.
- Conflicting verdicts (A=B, B=C, A≠C inside one KC): route to human, no automatic resolution.

Tradeoffs. Id stability: high (KCs only grow, merges are rare and gated). Error containment: weak; within-KC drift still happens because membership is still defined by chains of member-to-member matches, just with a veto at merge time. Human workload: low at first, but errors surface late and as large messy tickets. Cost: cheapest. This is the floor, not a recommendation.

### Policy B: Canonical-anchor clustering (CENTER semantics)

Redefine membership: an objective belongs to a KC if and only if it matches the KC's canonical phrasing (the anchor), not any arbitrary member. This is the CENTER / Star family from the Stringer study, which beat transitive closure decisively on precision (0.593 to 0.638 PCPr vs 0.101 at low thresholds) at the same single-pass cost. Chains cannot form because there is no member-to-member edge in the membership definition; every member is within one hop of the anchor.

Operational rules:
- Blocking already searches canonicals only, so judging is objective-vs-canonical (plus 2-3 stored exemplar objectives for context).
- 0 matches: new KC, the objective itself becomes the initial canonical.
- 1 match: attach. Refresh canonical. Guard against drift: if the new canonical's embedding moves more than a set cosine distance from the previous canonical, or a member no longer matches the refreshed canonical, trigger a re-check of all members against the new anchor (cheap: cluster sizes are small).
- 2+ matches: attach to none. This is evidence the KCs may be duplicates OR the objective is vague. First test the objective for vagueness (does it match the two canonicals for different reasons?); a vague objective is quarantined or sent back for re-extraction rather than allowed to become a bridge. Only if the two canonicals themselves match does a KC-KC merge proposal open.
- Conflict: a no-match against the canonical simply means non-membership; intransitivity among members cannot arise structurally.

Tradeoffs. Id stability: high; the anchor is the KC. Error containment: good; a bad admission is repaired by the drift guard, and a vague objective is caught at the multi-match gate instead of welding. Human workload: moderate, concentrated on merge proposals and vagueness quarantine, which are the decisions that actually matter. Cost: low; one judge call per candidate KC. Risk: anchor quality is everything; a badly refreshed canonical mis-classifies future arrivals, hence the drift guard and exemplar context.

### Policy C: Correlation clustering with local repair (FAMER style)

Keep the full signed edge graph among objectives. A KC is a cluster in a correlation-clustering sense: partition to agree with as many + edges inside and − edges across as possible (Bansal, Blum, Chawla; NP-hard, greedy approximations standard). Do not recompute globally; on each arrival, run local repair on the neighborhood the new objective touches, i.e. FAMER's n-depth reclustering with n=1 or 2: gather the new objective, its candidate KCs, and their members' edges, re-cluster that subgraph, and diff the result against current membership.

Operational rules:
- 0 matches: new KC.
- 1 match: attach, then local repair on that KC's neighborhood; repair may expel an old member (split) or confirm.
- 2+ matches: local repair over the union decides between merge, split, or reassign; it can conclude that the two KCs merge, or that the new objective is a bridge and belongs to only one, or to a new KC.
- Conflicts are the normal input; correlation clustering is literally defined as minimizing disagreement with conflicting edges. Uncertain edges have zero weight and can be escalated when they are pivotal (their resolution would flip the local optimum).

Tradeoffs. Quality: best; this is the only policy that repairs old mistakes automatically, and FAMER showed repair restores batch quality regardless of arrival order. Id stability: the weak point; repairs move members and split clusters, so a survivorship rule for ids is mandatory (see section 3; Zingg's reassignment rule: the post-repair cluster sharing the most members with an old cluster inherits that cluster's id). Human workload: low routine, but humans see decisions after the fact more often. Cost: highest judge volume (repairs re-examine edges) and more engineering.

### Policy D: Whole-cluster validation gate (SuperPart / GNN pattern, LLM-implemented)

Not a standalone clustering policy but a commit gate composable with A, B or C: before committing any attachment beyond the trivial case, and before any KC-KC merge, present the entire proposed membership set to the judge as one task ("here are 6 objectives; do they form one skill, or should they be partitioned; if so, how") rather than relying on the pairwise verdicts alone. This is the Barton et al. insight (cluster health is a set property) executed with an LLM instead of a GNN. It also aligns with recent findings that LLMs judge better when they see candidates jointly rather than as isolated pairs: the ComEM line of work (COLING 2025, "Match, Compare, or Select?") composes pairwise matching with compare/select over candidate lists and finds joint views improve effectiveness and cost over independent binary calls ([ACL Anthology](https://aclanthology.org/2025.coling-main.8.pdf)). Related 2025-2026 work prunes spurious edges from LLM match graphs with community detection precisely to enforce consistency across the group ([LMCD, OpenReview](https://openreview.net/forum?id=NgMbGDCmAM)) and propagates labels on a refined graph to cut LLM cost ([arXiv 2605.25814](https://arxiv.org/pdf/2605.25814)).

Tradeoffs. Error containment: the strongest single lever against welding, because a weld is visible in the set view (two thematic halves) even when every pairwise edge passed. Cost: one extra judge call per non-trivial commit; cluster sizes here are small (a KC has few objectives), so the context fits easily. Id stability and workload: inherits from the base policy.

### Policy E: Periodic global re-cluster with id reconciliation

Run the whole corpus through batch clustering (e.g. correlation clustering or Markov clustering, which the Stringer study found among the most accurate and efficient) on a schedule, then reconcile: each new cluster inherits the id of the old cluster with which it shares the most members (Zingg's reassignZinggId), remainders get new ids, diffs become merge/split events. Tradeoffs: batch-quality output and simple mental model, but churn arrives in bursts, every burst is a pile of id events for downstream, and mastery records sit on stale groupings between runs. The literature position is that this is what incremental repair (Policy C) exists to avoid; keep it only as an audit tool (compare batch output to live state to measure drift), not as the source of truth.

### Recommended composite

Policy B as the membership definition, Policy D as the commit gate, and Policy C's local repair triggered narrowly (on canonical drift beyond threshold, on any human split/merge, and on vagueness demotion of a member). Rationale: B eliminates chain formation structurally rather than detecting it after the fact; D catches the welds B cannot see (anchor itself absorbed a bad member); C's repair, run only on triggers, gives the order-independence result from FAMER without its id churn. Human attention is spent exactly where the literature says errors concentrate: multi-match arrivals, KC-KC merge proposals, and pivotal uncertain edges.

---

## 3. Durable KC ids with merge/split trails

The strongest and most consistent industry lesson: the clustering engine's group id and the external identifier must be different things.

### 3.1 Never export the cluster id

Senzing states outright that its resolved entity id "is not a globally unique persistent identifier," just a name for a grouping that may be transient, because the engine re-evaluates prior decisions as data arrives ([Senzing deep dive](https://senzing.zendesk.com/hc/en-us/articles/360045732894-Senzing-Entity-Resolution-Deep-Dive-Quick-Track)). The recommended architecture around such engines ([Simmonds, "Entity Resolution and the Instability Problem"](https://www.bencode.io/posts/entity/)): mint your own stable external id, keep an internal mapping to the current cluster, anchor at the record level (source system, source record id) so any entity can be re-resolved from its members, and publish merge/split change events so downstream systems can maintain their own view. For us: the KC id is minted by us, mastery records key on it, and the vector-index-side cluster representation is an implementation detail behind it. Objectives (the records) keep their own ids forever and each carries its KC assignment; that is the record-level anchor that makes every repair replayable.

### 3.2 Merge: redirect, do not delete

Wikidata is the reference implementation at scale. On merge, the losing item's content moves to the winner and the losing id becomes a permanent redirect to the winner; redirects exist "to provide stable identifiers," since an id that stops resolving breaks every external reference to it ([Help:Merge](https://www.wikidata.org/wiki/Help:Merge), [Help:Redirects](https://www.wikidata.org/wiki/Help:Redirects), [design doc](https://meta.wikimedia.org/wiki/Wikidata/Development/Entity_redirect_after_merge)). Two operational details worth copying:

- References elsewhere are not rewritten at merge time; a bot rewrites them later. This deliberate lag makes merges cheaply revertible during a grace window.
- Double redirects (A→B, then B→C) are collapsed to direct redirects (A→C) by a bot, so lookup is always at most one hop.

Concrete scheme for us: `kc_redirects(old_id, new_id, merged_at, merge_event_id)`, collapsed transitively on write. Winner selection rule should be deterministic and stated: the KC with more anchored mastery records keeps its id (tie: older id wins). Every read path resolves through the redirect table; exports include a redirects section so external consumers can migrate at their own pace.

### 3.3 Split: survivorship of the id plus a birth record

Zingg's rule for id survivorship after any re-clustering: "for each cluster in the new output, it finds the cluster in the original output that shares the most records (by primary key), and assigns that cluster's original ZINGG_ID"; splits leave one side with the original id and give the other a new one ([Zingg](https://www.zingg.ai/post/fuzzy-matching-at-scale-part-5-incremental-flow-and-living-clusters)). Adopt exactly that: on split, the child with the larger member overlap (tie: more mastery anchorage) retains the id, each other child gets a fresh id, and a split event records the full member reassignment map. A redirect is not enough for splits because the old id remains live; the split event is what lets a downstream system holding mastery against the old KC decide which child inherits which student evidence, or route that question to a human.

### 3.4 Member-level lineage (the XREF pattern)

Informatica MDM keeps a cross-reference (XREF) table per master record: every contributing source record, which system it came from, and its state before consolidation, "used for tracking the lineage of data" and enabling unmerge that restores the pre-merge state, including a variant that restores dependent child records to their original parents ([XREF tables](https://docs.informatica.com/master-data-management/multidomain-mdm/10-3/overview-guide/key-concepts/content-metadata/cross-reference--xref--tables.html), [unmerge overview](https://docs.informatica.com/master-data-management/multidomain-mdm/10-4/data-director-user-guide/part-2--data-director-with-subject-areas/unmerging-records-in-the-xref-view/unmerging-records-overview.html)). Our equivalent already nearly exists: objectives are the xref rows. What must be added is history: `kc_membership(objective_id, kc_id, valid_from, valid_to, cause_event_id)` as an append-only log, plus an event table `kc_events(event_id, type ∈ {create, attach, merge, split, expel, canonical_refresh}, payload, actor ∈ {llm, human, repair}, at)`. With those two tables every current KC is a fold over events, any merge is unmergeable to its exact prior state, and every canonical refresh is attributable to the admission that caused it (which is what lets us audit canonical drift after the fact).

---

## 4. Feeding human uncertain-resolutions back into the loop

What the tools do:

- dedupe.io: active learning; the system maintains a pool of unlabeled pairs, surfaces the most uncertain ones, retrains weights after each label, and re-ranks the pool, so each answer improves what gets asked next ([how it works](https://dedupe.io/documentation/how-it-works.html)).
- Magellan (Konda, Doan et al., PVLDB 2016) is built around the how-to-guide notion: the human is in the loop across the whole pipeline (debugging blockers, labeling samples, iterating matchers), not just at a final verdict queue ([overview](https://www.vldb.org/pvldb/vol9/p1197-pkonda.pdf)).
- Zingg: human approvals and separations become fixed constraints that incremental runs "must respect," never overridden by the model ([Zingg](https://www.zingg.ai/post/fuzzy-matching-at-scale-part-5-incremental-flow-and-living-clusters)).
- Crowd ER literature: order questions so each answer maximizes what can be inferred, but under noisy answering do not blindly propagate inferred positives; use error-aware aggregation and control questions ([SIGMOD 2013](https://dl.acm.org/doi/pdf/10.1145/2463676.2465280), [arXiv 1701.08288](https://arxiv.org/pdf/1701.08288)).

Concrete design for us:

1. Human verdicts are constraint edges, not soft evidence. A human "same" is a must-link, a human "different" is a cannot-link; both are permanent, attributed, and checked by every future automated decision (a proposed merge crossing a cannot-link auto-routes back to a human with the old decision attached). This is the Zingg rule and it is what makes human time compound instead of evaporate on the next re-run.
2. Route by impact, not only by model uncertainty. An uncertain verdict on a pair inside an established KC is low stakes; an uncertain verdict on a bridge edge (one that would merge two KCs, or whose flip would split one) is high stakes even when the LLM is fairly confident. Priority = uncertainty × structural impact, the crowd-ER question-selection idea applied to a queue.
3. Propagate human answers one hop, carefully. A human cannot-link between objective X and KC K's canonical justifies auto-rejecting future near-duplicates of X against K (with the human decision cited), but a human must-link should not transitively weld anything beyond the pair it names; it attaches X and nothing else.
4. Close the loop into the judge. Resolved uncertain pairs are exactly the hard cases; keep the most recent and most representative ones per topic area as few-shot exemplars in the judging prompt, and keep a held-out slice to measure judge drift. This is the LLM-era version of dedupe's retraining step.
5. Monitor intransitivity as a health metric. Count triangles with two + edges and one − edge among recent verdicts; a rising rate means the judge or the canonical anchors are degrading before any user-visible weld appears ([arXiv 2410.02205](https://arxiv.org/html/2410.02205v1)).
6. Treat repeated multi-match as a signal about the objective, not the KCs. An objective that keeps matching several KCs is the "generic value" case (Senzing's SSN analogy): demote it as merge evidence, quarantine it, and prefer sending it back through extraction for sharper phrasing over letting a human force-place it.

---

## 5. Sources

Clustering from pairwise decisions:
- Hassanzadeh, Chiang, Lee, Miller. Framework for Evaluating Clustering Algorithms in Duplicate Detection. VLDB 2009. http://www.vldb.org/pvldb/vol2/vldb09-1025.pdf
- Bansal, Blum, Chawla. Correlation Clustering. Machine Learning 56, 2004. https://link.springer.com/article/10.1023/B:MACH.0000033116.57574.95
- Draisbach, Christen, Naumann. Transforming Pairwise Duplicates to Entity Clusters for High-quality Duplicate Detection. ACM JDIQ 2019. https://dlnext.acm.org/doi/10.1145/3352591
- Binette, Steorts. (Almost) All of Entity Resolution. Science Advances 2022. https://arxiv.org/pdf/2008.04443
- Christophides et al. End-to-End Entity Resolution for Big Data: A Survey. 2019. https://arxiv.org/pdf/1905.06397

Incremental ER and repair:
- Saeedi, Peukert, Rahm. Incremental Multi-source Entity Resolution for Knowledge Graph Completion. ESWC 2020. https://pmc.ncbi.nlm.nih.gov/articles/PMC7250616/ (FAMER project: https://dbs.uni-leipzig.de/research/projects/famer)
- Barton, Neiman, Yuan. Graph Neural Networks for Inconsistent Cluster Detection in Incremental Entity Resolution. WWW 2021 workshops. https://arxiv.org/abs/2105.05957
- Gruenheid, Dong, Srivastava. Incremental Record Linkage. PVLDB 2014. https://www.vldb.org/pvldb/vol7/p697-gruenheid.pdf
- Whang, Garcia-Molina. Entity Resolution with Evolving Rules. PVLDB 2010. https://dl.acm.org/doi/10.14778/1920841.1920894

Industry incremental practice and id stability:
- Zingg. Fuzzy Matching at Scale, Part 5: Incremental Flow and Living Clusters. https://www.zingg.ai/post/fuzzy-matching-at-scale-part-5-incremental-flow-and-living-clusters
- Simmonds. Entity Resolution and the Instability Problem. https://www.bencode.io/posts/entity/
- Senzing. Principle-Based Entity Resolution. https://senzing.com/what-is-principle-based-entity-resolution/ and Deep Dive: https://senzing.zendesk.com/hc/en-us/articles/360045732894-Senzing-Entity-Resolution-Deep-Dive-Quick-Track
- Splink. Cluster Evaluation and Graph Metrics. https://moj-analytical-services.github.io/splink/topic_guides/evaluation/clusters/overview.html

MDM golden record and merge/split provenance:
- Profisee. MDM Survivorship. https://profisee.com/blog/mdm-survivorship/
- Dun & Bradstreet. What Is a Golden Record in MDM. https://www.dnb.com/en-us/resources/master-data/what-are-golden-records-in-master-data-management.html
- Informatica MDM. Cross-Reference (XREF) Tables. https://docs.informatica.com/master-data-management/multidomain-mdm/10-3/overview-guide/key-concepts/content-metadata/cross-reference--xref--tables.html
- Informatica MDM. Unmerging Records Overview. https://docs.informatica.com/master-data-management/multidomain-mdm/10-4/data-director-user-guide/part-2--data-director-with-subject-areas/unmerging-records-in-the-xref-view/unmerging-records-overview.html
- Wikidata. Help:Merge https://www.wikidata.org/wiki/Help:Merge ; Help:Redirects https://www.wikidata.org/wiki/Help:Redirects ; Entity redirect after merge (design) https://meta.wikimedia.org/wiki/Wikidata/Development/Entity_redirect_after_merge

Human-in-the-loop and crowdsourced ER:
- Konda et al. Magellan: Toward Building Entity Matching Management Systems. PVLDB 2016. https://www.vldb.org/pvldb/vol9/p1197-pkonda.pdf
- dedupe.io. How It Works. https://dedupe.io/documentation/how-it-works.html
- Wang, Kraska, Franklin, Feng. Leveraging Transitive Relations for Crowdsourced Joins. SIGMOD 2013. https://dl.acm.org/doi/pdf/10.1145/2463676.2465280
- Galhotra et al. Select Your Questions Wisely: For Entity Resolution With Crowd Errors. CIKM 2017. https://arxiv.org/pdf/1701.08288
- Vesdapunt, Bellare, Dalvi. Crowdsourcing Algorithms for Entity Resolution. PVLDB 2014. https://dl.acm.org/doi/10.14778/2732977.2732982

LLM-based ER (2023+):
- Measuring, Evaluating and Improving Logical Consistency in LLMs (transitivity of LLM judgments). 2024. https://arxiv.org/html/2410.02205v1
- Wang et al. Match, Compare, or Select? An Investigation of LLMs for Entity Matching (ComEM). COLING 2025. https://aclanthology.org/2025.coling-main.8.pdf
- Clustering and Entity Matching via Language Model Community Detection (LMCD). OpenReview. https://openreview.net/forum?id=NgMbGDCmAM
- Adaptive Graph Refinement and Label Propagation with LLMs for Cost-Effective Entity Resolution. 2026. https://arxiv.org/pdf/2605.25814
- Unlocking the Power of LLMs for Multi-table Entity Matching (transitive consensus embedding matching). 2026. https://arxiv.org/pdf/2604.21238
