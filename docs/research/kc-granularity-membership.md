# KC membership and granularity: what the literature actually does

Research memo for the Concept Universe content system. Informs two open design questions: (1) the KC membership test (when are two learning objectives "the same skill"?) and (2) objective sizing (what makes something one objective, two, or too trivial to count?).

Sources were read directly (PDFs of KLI, LFA, Pelanek 2020, Koedinger & McLaughlin 2016, Razzaq et al. 2007, Moore et al. 2022) rather than relying on abstracts. Quotes are verbatim from those documents. Full citations with URLs in section 6.

---

## 1. How surveyed frameworks and systems operationalize KC identity and granularity

### 1.1 KLI framework (Koedinger, Corbett, Perfetti 2012)

The canonical definition: "We define a knowledge component (KC) as an acquired unit of cognitive function or structure that can be inferred from performance on a set of related tasks." Three things in that sentence matter for our design:

- **Identity is inferential and task-anchored.** A KC is not a statement in a document; it is a latent cause of consistent performance across a *set* of related assessment events. "KCs produce ... consistency in student performance and transfer across related AEs" is the framework's whole explanation for why KCs exist as a construct.
- **Grain size is fixed by time scale, not by topic.** "Many KCs describe mental processes at about the unit task level of Newell's time scales of human action ... Unit tasks last about 10 s and are essentially the leaf nodes or smallest steps in the decomposition of a reasoning task, that is, the application of a single operator in a problem solving space (e.g., applying a theorem in a geometry proof)." Measured application times in their Fig. 2 range from 4 s (Chinese vocabulary) to 37 s (geometry area).
- **Target the level where novices err.** "Within a hierarchy of components, a knowledge analysis for a particular course may focus only on a single level that lies just above the level at which novices have achieved success and fluency. KC descriptions at the target level ... can treat lower levels ... as atomic under the empirical constraint that the target population has mastered the lower level." This is the literature's answer to "too trivial to count": a candidate objective is not a KC for this audience if the audience already performs it fluently.

KLI also gives KCs internal structure that functions as a *structural identity criterion*: every KC is a condition-response pair, classified by whether the application condition is constant or variable, whether the response is constant or variable, whether it is verbal or non-verbal, and whether it carries a rationale (their Tables 2 and 3). Facts are constant-constant, categories/concepts are variable-constant, rules/procedures are variable-variable. Two consequences:

- **One question cannot certify a variable-condition KC.** "Variety in task contexts is needed to infer acquisition of variable condition KCs from AEs. Just because a second language English student correctly selects 'an' in '[a/an] orange' does not ensure the student has learned a (variable-constant) KC with the right generality." They cite disambiguating an overgeneralized KC ("angles that look equal => are equal") from the correct one ("base angles of an isosceles triangle => are equal") by varying assessment tasks. This is a direct constraint on our "same checking question" candidate: for anything above fact-level, the test must be a question *family* that samples the condition space, not one question.
- **Doing and explaining are different KCs.** The verbal/non-verbal distinction "is about observable behavior, emphasizing whether students can 'do' but not explain (indicating non-verbal knowledge), explain but not do (indicating 'inert' verbal knowledge), or do and explain." Aleven & Koedinger (2002) found geometry students more correct on making inferences than on explaining them. So "state the perceptron update rule" and "apply the perceptron update rule" are different KCs by construction, even though a casual reading groups them under one objective.
- **Integrative KCs exist and are invisible to single-task inspection.** "KCs sometimes are not inferable from a single behavioral pattern, but only from behavioral patterns across task situations varying in complexity." Example: two-step algebra symbolization is harder than both one-step parts combined; the missing piece was a recursive-grammar KC (Heffernan & Koedinger 1997). A membership test based only on reading objective texts will never surface these; only difficulty/transfer data does.

### 1.2 Cognitive Tutor / Carnegie Learning

KC = production rule in an ACT-R style cognitive model, tracked per rule by Bayesian knowledge tracing (Corbett & Anderson 1995). Granularity in practice, from the LFA paper's inventory of the Geometry Cognitive Tutor Area unit: 15 skills for one unit, e.g. "Circle-area: Given the radius, find the area of a circle", "Compose-by-addition: In a+b=c, given any two of a, b, or c, find the third", "Trapezoid-height: Given the area and the base, find the height of a trapezoid". Note the shape of these: each one names the *given information* (application condition) and the *sought response*. Forward and backward uses of the same formula are separate skills (Circle-area vs Circle-radius), which the LFA experiments partly validated and partly refuted with data (section 1.3).

### 1.3 Learning Factors Analysis and DataShop model refinement (Cen, Koedinger, Junker 2006)

The literature's machinery for detecting KCs that are too coarse or too fine:

- **Statistical model.** The Additive Factors Model, a logistic regression with a per-student intercept, a per-KC intercept (difficulty), and a per-KC slope (learning rate over opportunities). Models are compared by AIC/BIC and, in later work, cross-validated RMSE.
- **Too coarse looks like blips.** "The power relationship might not be readily apparent in some complex skills, which have blips in their learning curves ... the power relationship holds if the complex skill can be decomposed into subskills, each of which exhibits a smoother learning curve." Concretely: the merged Compose-by-multiplication skill had final success .92, looking mastered, but splitting revealed CMarea (final .96) hiding CMsegment (final .60, under-practiced). Their conclusion: "students who have appeared to master the original rule ... might not get enough practice on the second split rule."
- **Split operator.** "Difficulty factors are incorporated into an existing cognitive model through a model operator called Binary Split, which splits a skill with a factor value, and a skill without the factor value." Factors are proposed by subject experts (Embed: shape alone vs embedded in another; Backward: forward vs backward form of a formula; Repeat: initial vs repeated use in a problem; FigurePart). A* search over split sequences, scored by AIC/BIC.
- **Merges are tested symmetrically.** Experiment 3 merged skills and let LFA re-split: "None of the models recovered Circle-CD. This suggests that it may not be necessary to have two separate skills for Circle-circumference and Circle-diameter. It appears that once students learn the formula circumference = pi*diameter, they can fairly easily apply it in the forward or backward direction." So the forward/backward distinction is a real KC boundary for some formulas and not for others; only data settles it.
- **DataShop's operational quality rubric.** The KC model help page: "The 'best' model would not only account for most of the data ... and fit the data well, but it would do so with fewest parameters (KCs)." A model "may model some knowledge components too coarsely, producing learning curves that spike or dip, or it may be too fine-grained (too many knowledge components), producing curves that end after one or two opportunities." The learning-curve page categorizes each KC's curve with thresholds: low error threshold 20% (from Bloom's mastery work), high error threshold 40%, plus an AFM slope threshold. Categories: "Low and flat" (over-practiced, too easy), "No learning" (flat slope; recommendation is to split the KC), "Still high" (needs more practice), "Too little data" (add tasks or merge KCs), "Good".
- KCluster (Yang et al. 2025) operationalizes "problematic KC" the same way: learning rate below 0.001 with initial success probability between 0.2 and 0.8, i.e. students are neither at floor nor ceiling and are not improving; that pattern flags a KC that is really several KCs.

### 1.4 Quantitative CTA and closing the loop (Koedinger & McLaughlin 2016; Koedinger, Stamper, McLaughlin, Nixon 2013)

This line of work states the deepest identity criterion in the literature: **difficulty and transfer must be explained by the same KC assignment.** "A key assumption behind DFA is that significant differences in task difficulty can be used to make non-obvious (sometimes counter-intuitive) inferences about underlying cognitive components and, in turn, these components help predict learning transfer and guide better instructional design." And: "statistical models that use the same KC matrix to predict task difficulty and learning transfer produce better results than models that use separate matrices."

The hidden-skill-transfer logic, verbatim: "If difficulty data indicates a hidden skill that makes an important task hard, then inventing new practice tasks to isolate practice of that hidden skill will transfer to better learning of that hard task." Their test: substitution practice (a novel task type isolating the hypothesized recursive-grammar KC) transferred to two-step story symbolization exactly on the problems whose difficulty data showed a composition effect, and not on the two problems without one. Prediction confirmed across 711 students.

Payoff evidence that KC boundaries matter for instruction: "An early example used learning curve analysis to identify hidden planning skills in geometry area that resulted in tutor redesign. In a close-the-loop experiment comparing the original tutor to the redesigned tutor, students reached mastery in 25% less time and performed better on complex planning problems on the post-test." The hidden planning KC is the cautionary example for any authoring-time membership test: the original expert model tagged composite-area steps with only computation KCs; the decomposition-planning KC was discovered from data, not from reading objectives.

Also relevant: expert intuition is systematically unreliable here (the "expert blind spot", Nathan, Koedinger & Alibali 2001; Koedinger & Nathan 2004 showed teachers wrongly predict equations are easier than matched story problems). Qualitative CTA (think-alouds, interviews; Clark et al. 2007) exists precisely because "cognitive task analysis remains as much an art as a science, in part because of the unobservable nature of knowledge" (KLI).

### 1.5 ASSISTments (Razzaq, Heffernan, Feng, Pardos 2007)

The most concrete authoring protocol found, and the source of the extensional view of KC identity:

- **Card-sort protocol.** "There were about 300 released test items for us to code. Because we wanted to be able to track learning between items, we wanted to come up with a number of knowledge components that were somewhat fine-grained but not too fine-grained such that each item had a different knowledge component. We therefore imposed upon our subject-matter expert that no one item would be tagged with more than 3 knowledge components. She was free to make up whatever knowledge components she thought appropriate. We printed 3 copies of each item so that each item could show up in different piles, where each pile represented a knowledge component." Result: 98 piles (WPI-98).
- **Names do not carry identity.** "She gave the knowledge components names, but the real essence of a knowledge component is what items it is tagged with. The name of the knowledge component served no-purpose in our computerized analysis."
- **Conjunctive semantics.** "A transfer model is a matrix that relates questions to the skills needed to solve the problem. We assume that students must know all of the skills associated with a question in order to be able to get the question correct."
- **Granularity comparison result.** Comparing WPI-1, WPI-5, WPI-39, WPI-106: the finer the model, the better it predicted student performance in the online system (WPI-98/106 best, then WPI-5, then WPI-1). Pardos & Heffernan replicated the direction with Bayesian networks. So prediction accuracy pushes toward fine grain; the practical cap comes from authoring cost and data per KC, not from modeling.
- Scaffolding questions exist to isolate KCs: the top-level item taps several KCs; each scaffold "directly assess[es] fewer knowledge components."

### 1.6 Open Learning Initiative (Bier, Lip, Strader, Thille, Zimmaro 2014; Moore, Nguyen, Stamper 2022)

OLI is the clearest published pipeline from learning objectives to KCs, i.e. exactly our extraction pipeline:

- Course design starts from "student-centered, measurable learning objectives"; a domain expert or learning engineer then creates a skills map (a Q-matrix) decomposing objectives into skills (used synonymously with KCs), and each low-stakes practice step is tagged with skills. Mastery is predicted per skill and rolled up to objectives.
- The objective/KC relationship is explicitly a two-level containment, with a stated grain-size contrast (Moore et al. 2022, running on OLI): "Skills used for these learning analytics systems are more fine-grained than learning objectives or common core standards that typically get mapped to sections or pages of a given course that encompass multiple skills. For instance, a learning objective for an algebra course might be 'Graph linear and quadratic functions and show intercepts, maxima, and minima' ... a skill tagged to a problem ... might be 'Identify the slope from an equation in the form of y=mx+b'. While the skill involves knowing other concepts such as slope-intercept form and arithmetic operations, it is specific enough to be assessed by a single problem and can be encompassed by the larger learning objectives."
- In the OLI courses Moore studied, experts tagged 3 skills per problem, and skill statements look like our objectives: "Identify the cation and anion and their charges", "Write chemical formulas for ionic compounds that contain polyatomic ions", "Iteration over a value using the range() function".
- Their quality rubric for a proposed skill tag (4 levels, inter-rater alpha .94): Expert Match; "Match, Not Granular" ("very similar to one of the three expert-generated ones, however it could be more specific"); "Problem Relevant" ("technically utilized in the problem, but it is not necessarily what is being assessed given the context", example: knowing what '+' means in an algebra problem); No Match. The middle two categories are precisely our two failure modes: too coarse, and true-but-not-the-point.

### 1.7 Khan Academy

Coarsest of the surveyed systems: skill = exercise (a problem-type cluster). Mastery mechanics per skill: complete a practice task ("typically, 5 correct in a row"), then spaced mastery/review cards promote through Familiar/Proficient/Mastered levels. Known simplification, stated by a former engineer: "All items within an exercise are assumed to have equivalent discernibility. This is certainly false, but a compromise we have made for now." Khan is evidence that a system can run at exercise-grain, and also evidence of what is lost: within-exercise difficulty structure is invisible.

### 1.8 OATutor (Pardos et al. 2023)

Open-source tutor with ~1,000 algebra problems from CC textbooks in structured JSON; every problem step carries skill tags, knowledge tracing runs per skill, and the KC model is deliberately swappable ("re-tagging content with different skills using ML" is an advertised research use). The KC lists derive from textbook curriculum structure. Useful to us mainly as an architecture precedent: KC model as replaceable data, not schema.

### 1.9 Pelanek 2020 (Umime): domain modeling under real constraints

The one paper squarely about our practical question, from the developer of a system with "hundreds of knowledge components, thousands of items". Key content:

- Endorses the KLI KC definition, then reframes pragmatically: KCs in a real system are "organizational units that group together related items". Acknowledges plainly that "a unit of cognitive function and a unit of organization within software are significantly different notions" and that research's implicit assumption that "all items within a knowledge component are similar ... is quite hard to satisfy with realistic educational content."
- **Objectives vs KCs, stated as a time-scale distinction:** "Learning objectives differ from knowledge components in their focus, purpose, and typical time scale. Whereas learning objectives focus on outcomes (what the student should be able to do), knowledge components ... highlight the cognitive aspect of performance ... at the time scale of 'unit tasks' that take students time at the order of 10 seconds. Learning outcomes are typically formulated at a coarser level of granularity and concern processes at the order of minutes or hours, spanning multiple knowledge components." Worked example: objective "Students will be able to add and subtract fractions" vs KC "addition of fraction with like denominators".
- **Granularity is an application decision, not a fact of the domain.** Anatomy example: "For high school students, it may be sufficient to have 'muscles' as a single KC. For medical students a more fine-grained division is necessary." His Table 3: coarse granularity + narrow coverage is "not useful"; fine granularity + wide coverage is "not managable"; realistic systems sit on the diagonal.
- **Item-count sizing rule (the only hard number of its kind found):** "A pragmatic view of KC definitions is concerned mainly with the size of knowledge components: How many items should belong to a KC? Within one practice session, we do not want students to see the same item multiple times ... For simple items that take less than 10 seconds (e.g., multiple-choice questions), we need at least 40 items for a meaningful KC. For more complex items (e.g., word problems), we need at least 15 items."
- **Type homogeneity rule.** "It is thus advantageous to have KCs homogeneous with respect to the type of content ... a KC that contains facts to be remembered should not contain rules to be understood, and the other way around." (Mirrors the KLI taxonomy as a membership constraint.)
- **Difficulty is not a KC boundary by default.** Three options for difficulty spread within a KC: split the KC (principled but costly, risks too-fine KCs), ignore it (degrades mastery decisions: "a student's streak is ruined by an excessively difficult example"), or his recommendation, keep one KC and bin items into about three difficulty levels. Warning that mechanical difficulty-based splits can encode the wrong thing: fraction-comparison items split by raw difficulty would group items solvable by the *wrong* heuristic "the result of the comparison is the same as the comparison of numerators".
- **Composition machinery.** Two ways to combine elementary KCs: integrative KC ("sequential composition: solving an item requires the application of all constituent KCs", strictly harder than the sum of parts) and union KC ("parallel composition: solving an item requires the application of only one constituent KC", used for interleaved practice, e.g. area of mixed shapes). Advice: add explicit integrative KCs only "when the integration effect is strong", ignore otherwise.
- **Open question he flags that hits our test directly:** the same topic practiced through different activity formats (constructed response vs multiple choice vs matching, for one-digit multiplication): "Should the different activities ... be considered as a single KC or as different KCs? ... We consider this to be an interesting open question in student modeling." Students answer MCQ versions 2 to 3 times faster. So "admits the same checking question" inherits a real ambiguity: the same knowledge probed through different formats behaves differently in data.
- Item-to-KC mapping: N:M Q-matrices are well studied but bring the "credit/blame assignment problem"; "from the practical perspective, it is much simpler to use the basic approach 'each item belongs to a single KC'", with duplication or integrative KCs handling the exceptions.

### 1.10 LLM-era KC discovery (2024-2025)

- Moore et al. 2024: GPT-4-generated KCs for MCQs matched human expert KCs 56% (chemistry) / 35% (e-learning); when they disagreed, human evaluators *preferred the LLM's KC about two-thirds of the time*. Expert KC labels are a weaker gold standard than they look.
- KCluster (Yang, Liu & Koedinger 2025): defines KC membership operationally as a clustering criterion over an LLM-induced similarity called congruity (average conditional log-likelihood lift between two question texts), clusters questions with affinity propagation, and has an LLM name each cluster. On three DataShop datasets it "discovers KC models that predict student performance better than the best expert-designed models available" (item-stratified CV RMSE, AFM). Their diagnostic example: one expert KC "apply_evidence" with a flat learning curve decomposed into four KCs whose curves each drop cleanly within four opportunities. Relevant to us two ways: (a) automated congruity clustering is a cheap second opinion on any manual grouping; (b) even at Carnegie Mellon, expert KC models routinely contain mergeable and splittable components, so our pipeline must treat every KC boundary as provisional.

---

## 2. Candidate membership tests

The literature does not contain a ready-made authoring-time membership rule; every mature operationalization is either structural (KLI condition-response), extensional (ASSISTments piles), or statistical after data arrives (LFA/AFM). The following are the operational candidates we could adopt, including ours.

### Test A: Same single checking question (our current candidate)

Rule: objectives O1 and O2 belong to one KC iff one focused question could test both.

Assessment against the literature, plainly:

- **As a sizing gate it is well supported.** Moore et al.'s definition of correct skill granularity is nearly our sentence: a skill is "specific enough to be assessed by a single problem". OLI, ASSISTments, and Cognitive Tutor KCs all pass it.
- **As an identity test it is weaker than literature practice on three counts.** (1) KLI: for any variable-condition KC (rules, concepts, i.e. most of what we teach), a single question cannot distinguish the intended generalization from an overgeneralized or memorized one; identity requires a question *family* spanning the condition space ("Variety in task contexts is needed"). (2) It is blind to hidden KCs: the composite-area checking question looked like one question, yet contained a planning KC and computation KCs that data later separated; the two-step symbolization question contained a hidden recursive-grammar KC. A question-identity test performed on objective texts inherits the expert blind spot. (3) Format sensitivity cuts the other way: the same knowledge probed as MCQ vs constructed response yields measurably different behavior, and whether that is one KC or two is an admitted open question (Pelanek), so "same question" can also split what should be merged.
- Direction of expected error: too coarse on multi-step or conceptual material (misses hidden components), too fine on surface variation (treats format or phrasing variants as different questions).

### Test B: Question-pool interchangeability (recommended refinement of A)

Rule: for each objective, imagine the pool of fair checking questions (varying surface features and application conditions, holding the target skill fixed). O1 and O2 are the same KC iff their pools are interchangeable: any fair question for O1 is a fair question for O2 and vice versa. If one pool strictly contains the other, that is a prerequisite or subsumption relation, not identity. If the pools merely overlap, they are different KCs sharing items (a Q-matrix situation).

- This is the ASSISTments extensional definition ("the real essence of a knowledge component is what items it is tagged with") moved to authoring time, and it matches the KLI requirement of task variety. It keeps checkability as the engine while fixing A's single-sample fragility.
- It also gives the sizing rule for free: an objective too broad to have a coherent question pool (its questions test recognizably different things) must split; an objective whose entire pool is answerable by the target audience already, or whose pool collapses to one memorized item that is not worth tracking, is below the floor.
- Cost: authors must think in pools, which is slower than thinking in single questions. Mitigation: require 2 or 3 exemplar questions per KC at authoring time, which we will want anyway for assessment.

### Test C: Condition-response identity (KLI-structural)

Rule: write each objective in condition => response form (when given X, the student does/produces Y). Same KC iff same application-condition pattern and same response type and same knowledge type (fact / category / rule) and same modality (do vs explain). Any mismatch on those four axes means different KCs.

- Pros: fast, fully author-side, catches the classic boundaries the data studies keep finding: forward vs backward use (Circle-area vs Circle-radius), do vs explain (Aleven & Koedinger), fact vs rule mixtures (Pelanek's homogeneity rule).
- Cons: it over-splits relative to data. LFA's merge experiment showed forward/backward is *not* a real boundary for circumference vs diameter. Structural distinctions are hypotheses that data sometimes rejects.

### Test D: Transfer identity (the literature's ground truth)

Rule: same KC iff practice on tasks drawn from O1 improves performance on tasks drawn from O2 to the same degree as practice on O2 itself, and their difficulty covaries (the same KC matrix predicts both). This is the criterion QCTA states and tests, and the one all statistical machinery (AFM, BKT) assumes.

- This is the truth-maker; every other test is a proxy for it. It is not available at authoring time and needs student data at scale. Adopt it as the definition of what our membership test is *trying to approximate*, and as the validation target, not as the operating rule.

### Test E: Statistical refinement loop (LFA/DataShop, later KCluster-style)

Rule: whatever grouping we author, treat it as KC model v1. Once evidence records exist: fit AFM per KC; flag "no learning" curves (slope near 0, success mid-range) and spiky curves as split candidates; flag curves that end after one or two opportunities and KCs students never fail as merge candidates; test hypothesized splits/merges by AIC/BIC and item-stratified CV; optionally run congruity clustering over our question texts as an automated counter-proposal.

- Not a membership test at authoring time; it is the correction mechanism every surveyed mature system relies on. The design implication is architectural: KC membership must be cheap to change after launch (re-tag objectives without destroying evidence records), because the literature guarantees our first model will be wrong somewhere.

**Recommendation.** Adopt B (question-pool interchangeability) as the operating membership test, with C as a structured worksheet that authors fill in to construct the pools (condition, response, knowledge type, do-vs-explain), D as the stated semantics of what a KC is, and E as the committed validation loop. Our original A survives as the sizing gate: one focused question *could* test it (else split); at least one question *worth asking this audience* exists (else drop).

---

## 3. Objective sizing heuristics found in the literature

Collected concrete rules, deduplicated:

1. **Unit-task time scale.** A KC operates at roughly 10 seconds of skilled mental action (4 to 37 s observed across domains); it is a leaf step, "the application of a single operator" (KLI). Objectives describing minutes-to-hours of activity are objective-level or concept-level, not KC-level, and should decompose.
2. **Single-problem assessability.** A skill is sized right when it "is specific enough to be assessed by a single problem" while a learning objective "encompass[es] multiple skills" and maps to sections or pages of a course (Moore et al. 2022; same containment in OLI's objectives -> skills map).
3. **Novice-error floor.** Do not create KCs below the level at which the target population already performs fluently; treat mastered subskills as atomic (KLI). Empirical signature of violating this: "low and flat" learning curves (DataShop) and Pelanek's over-practice warning.
4. **Bloom-verb discipline for the objective statement itself.** Mager's model: an objective states an observable performance, conditions, and criterion; verbs like "understand" and "learn" are unacceptable because unmeasurable. One observable verb per statement; two verbs of different Bloom levels (e.g. "define and apply") is two objectives, and per KLI's verbal/non-verbal distinction it is also two KCs.
5. **Caps per item and per objective.** ASSISTments capped tagging at 3 KCs per item; OLI courses tagged 3 skills per problem. If solving one checking question requires many KCs, either the question is a poor KC probe or an integrative KC is hiding.
6. **Item-pool viability.** A KC should be able to support enough distinct practice questions: at least ~40 simple items or ~15 complex items in a drill system (Pelanek). For us the transferable form is: if you cannot imagine several distinct checking questions for an objective, it is a fact-grade KC or too trivial; if practice would need to repeat one question, it is under-sized.
7. **Type homogeneity.** One KC must not mix facts with rules or procedures with explanations (Pelanek; KLI taxonomy). Mixed objectives split along the type boundary.
8. **Fine beats coarse for prediction, up to data limits.** WPI-98 beat WPI-5 beat WPI-1 for online prediction (Razzaq et al.); research consistently prefers finer KCs for fit and interpretability (Pelanek's literature summary), but curves ending after one or two opportunities mean too fine for the available practice (DataShop). Fine-grained wins only if each KC still accumulates enough observations.
9. **Difficulty variation alone is not grounds to split.** Prefer difficulty tiers within a KC (about three levels); split only when the difficulty difference traces to an identifiable knowledge difference, e.g. a rule the hard items require and the easy items do not (Pelanek; the a/an "sound not spelling" example vs the fraction-comparison counterexample).

---

## 4. Validation protocols for the perceptron hand experiment

Ordered from cheapest to most demanding. The first three are feasible now, on sources only; the last two need students.

**P1. Multi-rater card sort (ASSISTments replication).** Extract objectives from 3 or 4 perceptron sources independently. Two or three raters (humans and/or independent model runs with distinct prompts) sort all objectives into piles, each pile = one KC, cap 3 KCs per objective where an objective genuinely spans several. Compare partitions with an agreement measure over pairs (same-pile vs different-pile; Cohen's kappa or adjusted Rand). Moore et al. achieved inter-rater alpha .94 with a 4-level rubric, so high agreement is attainable; low agreement pinpoints exactly the objective pairs where the membership rule is underdetermined. Follow ASSISTments in treating names as irrelevant during sorting; name piles last.

**P2. Blind question-swap test (direct test of the B rule).** For each candidate KC grouping {O1, O2} produced by P1: one person/model writes 2 or 3 checking questions from O1's source context only; another writes them from O2's; a blind judge answers, for each question, "which objective does this test?" and "is this a fair test of the other objective, unchanged?". Membership holds iff questions cross over cleanly (judge cannot reliably attribute, and rates them fair for both). Partial crossover with a consistent direction indicates subsumption/prerequisite, not identity. This makes our own candidate test falsifiable instead of intuitive.

**P3. Structural audit (C worksheet).** For every surviving KC, write it as condition => response, tag knowledge type (fact/category/rule), and tag do-vs-explain. Any KC whose members disagree on an axis gets split or re-sorted. Perceptron-specific predictions this will surface: "state the update rule" vs "execute one update by hand" vs "explain why the update moves the boundary" are three KCs; "compute a dot product" is probably below the novice-error floor for our audience (check, do not assume); "trace convergence on linearly separable data" likely contains a hidden planning/setup KC in the geometry-planning pattern, since its obvious checking question is multi-step.

**P4. Difficulty-factor probes (DFA-style, first cohort).** For KCs the audit leaves merged but suspicious, author matched question pairs varying one factor (e.g. update with correctly-classified vs misclassified point; 2D vs 3D inputs; bias present vs absent; symbolic weights vs numeric). Large systematic success-rate gaps between matched variants indicate a hidden KC, per the DFA logic that difficulty differences under matched surface conditions implicate distinct components.

**P5. Learning-curve validation (once evidence records flow).** Map evidence records to KCs, fit AFM (or simply plot error rate by opportunity per KC given our early scale), apply the DataShop categorization with its default thresholds (low 20%, high 40%, slope near zero flagged). Split "no learning" KCs using P4's factors as candidate splits; merge "too little data" KCs; compare the authored model against one coarser (concept-level) and one finer (per-source-objective) alternative on held-out prediction, item-stratified, since that is the comparison regime under which small RMSE differences corresponded to real instructional gains (Koedinger & McLaughlin 2016, Table 3). Optionally run a KCluster-style congruity clustering over our question texts as an automated counter-model.

Success criterion for the hand experiment itself: P1 agreement above ~.7 kappa on membership pairs, and P2 crossover verdicts matching P1 piles on at least ~80% of pairs. Below that, the membership rule (not the raters) needs revision before scaling extraction.

---

## 5. Direct answers to the two open questions

**Q1 (membership).** "Do they admit the same checking question?" is directionally right but under-specified relative to the literature. The literature's actual identity relation is shared difficulty-and-transfer behavior (D), which authoring can only approximate. The best authoring-time approximation is question-pool interchangeability (B) constrained by condition-response structure (C): same application-condition pattern, same response type, same knowledge type, same do-vs-explain modality, and interchangeable fair-question pools. A single shared question is neither necessary (format variants can differ) nor sufficient (variable-condition KCs need question variety; multi-step questions hide components). Whatever we adopt must be revisable from data; every surveyed system that lived long enough revised its KC model.

**Q2 (sizing).** Checkability is validated as the sizing criterion, with the refinement that the unit is "one focused question could test it, and several distinct such questions could be written" (rules 1, 2, 6 above). The floor is empirical, not logical: an objective is too trivial when the target audience already answers its whole question pool fluently (rule 3), not when it looks small. Two-verb objectives split; fact/rule mixtures split; minutes-scale objectives decompose to ~10-second unit tasks.

---

## 6. Citations

- Koedinger, K. R., Corbett, A. T., & Perfetti, C. (2012). The Knowledge-Learning-Instruction Framework: Bridging the Science-Practice Chasm to Enhance Robust Student Learning. *Cognitive Science*, 36(5), 757-798. PDF: http://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf ; publisher page: https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1551-6709.2012.01245.x
- Cen, H., Koedinger, K., & Junker, B. (2006). Learning Factors Analysis: A General Method for Cognitive Model Evaluation and Improvement. *Proc. 8th Int. Conf. on Intelligent Tutoring Systems*. PDF: http://pact.cs.cmu.edu/pubs/Cen,%20Koedinger%20&%20Junker06.pdf ; Springer: https://link.springer.com/chapter/10.1007/11774303_17
- Koedinger, K. R., & McLaughlin, E. A. (2016). Closing the Loop with Quantitative Cognitive Task Analysis. *Proc. 9th Int. Conf. on Educational Data Mining*, 412-417. PDF: https://www.cais.usc.edu/wp-content/uploads/2018/02/Koedinger-2016-Quantitative-CTA.pdf
- Koedinger, K. R., Stamper, J. C., McLaughlin, E. A., & Nixon, T. (2013). Using Data-Driven Discovery of Better Student Models to Improve Student Learning. *Proc. AIED 2013*, 421-430. https://link.springer.com/chapter/10.1007/978-3-642-39112-5_43
- Liu, R., & Koedinger, K. R. (2017). Closing the Loop: Automated Data-Driven Cognitive Model Discoveries Lead to Improved Instruction and Learning Gains. *Journal of Educational Data Mining*, 9(1). https://jedm.educationaldatamining.org/index.php/JEDM/article/view/212
- Pelanek, R. (2020). Managing Items and Knowledge Components: Domain Modeling in Practice. *Educational Technology Research and Development*, 68, 529-550. Preprint: http://www.fi.muni.cz/~xpelanek/publications/domain-modeling.pdf ; Springer: https://link.springer.com/article/10.1007/s11423-019-09716-w
- Razzaq, L., Heffernan, N. T., Feng, M., & Pardos, Z. A. (2007). Developing Fine-Grained Transfer Models in the ASSISTment System. *Technology, Instruction, Cognition and Learning*, 5(3). PDF: https://web.cs.wpi.edu/~leenar/publications/ticl_final.pdf
- Pardos, Z. A., & Heffernan, N. T. (2007). The Effect of Model Granularity on Student Performance Prediction Using Bayesian Networks. *Proc. User Modeling 2007*. https://link.springer.com/chapter/10.1007/978-3-540-73078-1_60
- Bier, N., Lip, S., Strader, R., Thille, C., & Zimmaro, D. (2014). An Approach to Knowledge Component/Skill Modeling in Online Courses. OLI / Google white paper. https://research.google/pubs/pub48380/
- Moore, S., Nguyen, H. A., & Stamper, J. (2022). Leveraging Students to Generate Skill Tags that Inform Learning Analytics. *Proc. ICLS 2022*, 791-798. PDF: https://stevenjamesmoore.com/assets/papers/isls22_full_moore.pdf
- Moore, S., Schmucker, R., Mitchell, T., & Stamper, J. (2024). Automated Generation and Tagging of Knowledge Components from Multiple-Choice Questions. *Proc. L@S 2024*. https://arxiv.org/abs/2405.20526 ; https://dl.acm.org/doi/10.1145/3657604.3662030
- Yang, W., Liu, R., & Koedinger, K. R. (2025). KCluster: An LLM-based Clustering Approach to Knowledge Component Discovery. https://arxiv.org/abs/2505.06469
- Pardos, Z. A., Tang, M., Anastasopoulos, I., Sheel, S. K., & Zhang, E. (2023). OATutor: An Open-source Adaptive Tutoring System and Curated Content Library for Learning Sciences Research. *Proc. CHI 2023*. https://dl.acm.org/doi/10.1145/3544548.3581574
- DataShop help: KC Models. https://pslcdatashop.web.cmu.edu/help?page=kcm
- DataShop help: Learning Curves (curve categorization and thresholds). https://pslcdatashop.web.cmu.edu/help?page=learningCurve
- Corbett, A. T., & Anderson, J. R. (1994). Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge. *User Modeling and User-Adapted Interaction*, 4, 253-278. https://link.springer.com/article/10.1007/BF01099821
- Faus, M. (2014). Khan Academy Mastery Mechanics. https://mattfaus.com/2014/07/03/khan-academy-mastery-mechanics/
- Khan Academy Help Center: How do Khan Academy's Mastery levels work? https://support.khanacademy.org/hc/en-us/articles/5548760867853--How-do-Khan-Academy-s-Mastery-levels-work
- Mager, R. F. (1997). *Preparing Instructional Objectives* (3rd ed.). Summary of the performance/conditions/criterion model: https://assets.td.org/m/5fa0e935ed2dc942/original/Mager-s-Model-for-Writing-Learning-Objectives.pdf
- Clark, R. E., Feldon, D., van Merrienboer, J., Yates, K., & Early, S. (2007). Cognitive Task Analysis. In *Handbook of Research on Educational Communications and Technology* (3rd ed., 577-593). (Cited via KLI and Pelanek as the standard CTA reference.)
- Nathan, M. J., Koedinger, K. R., & Alibali, M. W. (2001). Expert Blind Spot: When Content Knowledge Eclipses Pedagogical Content Knowledge. *Proc. 3rd Int. Conf. on Cognitive Science*. (Cited via Moore et al. 2022 and QCTA.)
- Heffernan, N., & Koedinger, K. R. (1997). The Composition Effect in Symbolizing: The Role of Symbol Production vs. Text Comprehension. *Proc. 19th Annual Conf. of the Cognitive Science Society*, 307-312. (Source of the hidden recursive-grammar KC; cited via KLI and QCTA.)

Reading notes: KLI, LFA, Pelanek 2020, Koedinger & McLaughlin 2016, Razzaq et al. 2007, and Moore et al. 2022 were read in full from the PDFs above; quotes are verbatim. OLI 2014, KCluster, Moore et al. 2024, OATutor, DataShop help pages, and Khan Academy sources were consulted via page fetches; the original 2014 OLI white paper PDF link (squarespace) is dead, so its process description rests on the Google Research abstract, the Stanford OLI announcement, and secondary descriptions in Moore et al. 2022 and the Thille 2017 literature.
