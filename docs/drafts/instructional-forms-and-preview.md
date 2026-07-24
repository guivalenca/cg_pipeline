# Instructional forms and the preview as pedagogy

Status: draft for discussion. Not an implementation plan and not a PRD. This is a guiding unit: it states a problem, a hypothesis, and the evidence around it, so that the direction can be debated before anything is specified.

## 1. The problem

The Companion currently teaches in one register. Sessions are strongly socratic from the first turn to the last: the tutor asks, the student reasons, the tutor probes. This is applied uniformly, regardless of two things that vary a great deal:

- The student's state with respect to the material. A student meeting a concept for the first time is questioned in the same mode as a student who has already built a partial model of it. For the first student, the questions land on nothing: there is no prior structure to probe, so the dialogue degrades into the student guessing at what the tutor wants.
- The type of the material itself. A definition, a classification, a procedure, and a principle with a rationale are not the same kind of knowledge, and there is no reason to expect one questioning style to serve all of them equally.

There is a second, related problem. The pre-lesson preview ("Prévia da aula", the Intro Note) exists, but it is an afterthought: optional, weakly produced, and disconnected from the session's pedagogy. Nothing in the session assumes the student read it, and nothing in the preview is designed to prepare the specific reasoning the session will demand. The one artifact that could give the student an expository foundation before the questioning begins is the one artifact the system treats as decoration.

## 2. The hypothesis

This is the founder's hypothesis, stated as such: the Companion may be too socratic.

Concretely:

- Students would likely benefit from sessions that begin with an expository, low-critical-thinking introduction to the topic. The preview should stop being an optional artifact and become the natural, first-class opening of the session itself: the moment where the tutor simply presents, clearly and without demanding production, what the student is about to work on. Only after that foundation is laid should the session move into the high-engagement socratic part.
- More broadly, sessions should switch learning forms throughout the lesson rather than holding one form for ninety minutes. Expository presentation, worked examples, retrieval practice, socratic questioning, and self-explanation are different instruments, and the tutor should pick the instrument per moment: per segment, per concept, per state of the student.

The founder is confident this will significantly improve the system. The purpose of this document is to test that confidence against the research literature, honestly, including the strongest counterpoint.

## 3. What the literature says

The short version: the hypothesis is well supported, with one important and legitimate counter-tradition (productive failure) that deserves a fair hearing, and one refinement the literature insists on (the right form depends on the student's competence, not only on the material).

### 3.1 Novices learn more from being shown than from being made to produce (the worked-example effect)

The worked-example effect is one of the oldest and most replicated findings in cognitive load theory: learners with low prior knowledge learn more from studying worked-out solutions than from solving the equivalent problems themselves. Sweller's account is that forcing novices to solve problems pushes them into weak search strategies (means-ends analysis) that consume working memory without building the schema the problem was supposed to teach; studying a worked example spends that same working memory on the structure of the solution. Sweller describes it as the best known and most widely studied of the cognitive load effects ([Wikipedia overview with primary references](https://en.wikipedia.org/wiki/Worked-example_effect); [Sweller, cognitive load overview](https://mcblogs.montgomerycollege.edu/thehub/wp-content/uploads/2025/02/Cognitive-load_Sweller.pdf)).

The effect is not small and not fragile. A 2023 meta-analysis of the worked-example effect in mathematics (Barbieri, Miller-Cotto, Clerjuste and Chawla, 55 studies, 181 effect sizes, elementary through postsecondary) found an average effect of g = 0.48 on mathematics performance ([Educational Psychology Review](https://link.springer.com/article/10.1007/s10648-023-09745-1); [PDF](https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf)). The broader argument that novices need substantial guidance, not discovery, was made forcefully by Kirschner, Sweller and Clark in "Why Minimal Guidance During Instruction Does Not Work" ([Educational Psychologist 2006](https://www.tandfonline.com/doi/abs/10.1207/s15326985ep4102_1); [PDF](https://itgs.ict.usc.edu/papers/Constructivism_KirschnerEtAl_EP_06.pdf)).

Conditions and limits, stated honestly:

- The effect holds for novices, in the early stage of skill acquisition. It weakens and then reverses as competence grows (next section). Worked examples offered late, when the student can already solve, are wasted time or worse.
- The literature converges on fading, not on examples forever: start with full worked examples, then progressively remove steps (completion problems), then full problem solving. The example is a ramp, not a destination.
- Examples work markedly better when paired with self-explanation prompts, that is, when the student is asked to explain why each step follows. A passive example silently read is the weak version of the treatment.
- Kirschner, Sweller and Clark's paper is polemical and drew serious published rebuttals (the 2007 commentaries in Educational Psychologist). The defensible reading is not "guidance always wins" but "novices need guidance"; the paper's critics mostly dispute the framing of inquiry methods, not the novice finding.

### 3.2 The advantage flips as the student gains competence (the expertise reversal effect)

Kalyuga, Ayres, Chandler and Sweller documented that instructional supports which help novices become neutral and then actively harmful for more knowledgeable learners ([The Expertise Reversal Effect, Educational Psychologist 2003](https://www.tandfonline.com/doi/abs/10.1207/S15326985EP3801_4)). The mechanism proposed is redundancy: once the learner has a schema, externally provided guidance duplicates what the schema already does, and processing the duplicate costs working memory. In Kalyuga's words, instructional guidance which may be essential for novices may have negative consequences for more experienced learners. The follow-up work draws the practical conclusion directly: instruction should be tailored to the learner's current knowledge level, with guidance faded as expertise grows ([Kalyuga 2007, Expertise Reversal Effect and Its Implications for Learner-Tailored Instruction](https://link.springer.com/article/10.1007/s10648-007-9054-3)).

This is the single most important refinement to the hypothesis. It says the question "should the Companion be expository or socratic?" is malformed. The correct question is "for this student, on this concept, right now, which form?", and the literature's answer is a crossover: exposition and worked examples for the unseen and the weak, generative work (problem solving, socratic probing, retrieval) for the shaky and the solid.

Limits: expertise reversal has been demonstrated many times but mostly in short lab or classroom studies with relatively coarse expertise measures. The crossover point is real; its precise location for a given student and concept is not something the literature can hand us. Any system that acts on it needs its own signal of the student's state, which is exactly what per-KC mastery is meant to be.

### 3.3 When telling beats withholding, and vice versa (the assistance dilemma)

Koedinger and Aleven named the general problem the assistance dilemma: every tutoring decision is a choice between giving information and withholding it, and both directions have documented failure modes. Withholding more than needed produces frustration and wasted time without learning; giving more than needed produces shallow performance that does not survive a delay or a transfer test ([Exploring the Assistance Dilemma in Experiments with Cognitive Tutors, Educational Psychology Review 2007](https://link.springer.com/article/10.1007/s10648-007-9049-0); [ERIC record](https://eric.ed.gov/?id=EJ785065); see also [Is it Better to Give than to Receive?, CogSci 2008](https://www.cs.cmu.edu/~bmclaren/pubs/KoedingerEtAl-IsItBetterToGiveThanToReceive-CogSci2008.pdf)).

Two points from this line of work matter here:

- There is no universally correct amount of assistance. Experiments with Cognitive Tutors found cases where adding worked examples to tutored problem solving improved efficiency at no cost to learning, and cases where withholding (forcing retrieval or self-explanation) was the winning move. The optimum depends on the student's state and the target knowledge.
- A tutor that is uniformly socratic has simply pinned itself to one end of the dilemma. That is a policy choice, not a resolution. The Companion today withholds by default, always. The literature says a fixed policy at either extreme leaves learning on the table.

Limits: the assistance dilemma is a framing, not a formula. Koedinger and Aleven are explicit that the field lacks a complete predictive theory of when to give and when to withhold; they offer the KLI framework (next section) as the path toward one.

### 3.4 Different knowledge types learn through different mechanisms (the KLI framework)

Koedinger, Corbett and Perfetti's Knowledge-Learning-Instruction framework is the closest thing the field has to a principled mapping from material type to instructional move ([Cognitive Science 2012](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1551-6709.2012.01245.x); [full PDF](http://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf)). Its taxonomy of knowledge components is essentially the one the Concept Universe is adopting: constant versus variable application conditions and responses (which yields facts and associations at one end, categories and concepts in the middle, rules, plans and schemas at the other), verbal versus non-verbal (explain versus do), and presence or absence of a rationale.

KLI distinguishes three families of learning processes and, crucially, argues that each KC type is best served by the instructional moves that feed its process. The paper's own tentative mapping (section 3.3.2, p. 774):

- Facts and simple associations (constant condition, constant response), and simple perceptual categories, learn through memory and fluency-building. Best served by recall practice, spacing, and optimized scheduling of practice. Not served by elaborate sense-making: prompting a student to self-explain a vocabulary fact is spending expensive time on a cheap component.
- Rules, schemas and skills (variable condition, variable response) learn through induction and refinement: the student's mind extracts the general condition from varied cases. Best served by worked-example study and by comparison and contrast across cases. This is largely non-verbal learning; students often acquire correct procedures they cannot articulate, and that is acceptable when doing is the goal.
- Principles and rules with rationales, and integrated knowledge that must be both done and explained, learn through understanding and sense-making. Best served by prompted self-explanation and by instructional dialogue and argumentation. The paper notes that self-explanation prompts show negative results precisely where non-verbal acquisition would suffice, and positive results where verbal knowledge is a learning objective. Discovery and argumentation, it adds, may be productive for KCs that have a rationale, and not for ones without.

Self-explanation itself is well quantified: a meta-analysis of induced self-explanation across 64 studies found a mean effect of g = 0.55 ([Bisra et al., Educational Psychology Review 2018](https://link.springer.com/article/10.1007/s10648-018-9434-x)).

The KLI authors frame the education wars directly: more worked-example study is at odds with more testing of recall, and pure practice is at odds with self-explanation prompts and extended dialogue, only if one insists on a single method for all knowledge. The taxonomy dissolves the contradiction by assigning each method its type. This is the strongest theoretical support for form-switching keyed to KC axes: it says the switching is not a stylistic preference but a consequence of how different components are learned.

Limits: KLI's mapping is offered by its authors as tentative hypotheses requiring further testing, each with some support, none with the evidential weight of the worked-example effect itself. The framework is also silent on motivation and affect, which it acknowledges. Treat the mapping as the best available default, not as settled law.

### 3.5 The honest counterpoint: productive failure (struggle first can beat instruction first)

Kapur's productive failure research is the strongest challenge to "exposition first", and it must be taken seriously because its evidence is good. In the productive-failure design, students attempt problems on a new concept before any instruction, typically generating multiple flawed solutions, and only then receive consolidating instruction that builds on their attempts. Sinha and Kapur's meta-analysis (166 comparisons, 53 studies, over 12,000 participants) found a significant moderate advantage for problem-solving-before-instruction over instruction-before-problem-solving: Hedges' g = 0.36 on conceptual understanding and transfer ([When Problem Solving Followed by Instruction Works, Review of Educational Research 2021](https://journals.sagepub.com/doi/10.3102/00346543211019105); [ERIC record](https://eric.ed.gov/?id=EJ1308129); see also [Kapur and Roll's overview](https://boldscience.org/wp-content/uploads/2025/04/Productive-Failure.pdf)).

How can this coexist with the worked-example effect? The regimes differ, and the differences tell us when each wins:

- Outcome measured. Productive failure's advantage shows on conceptual understanding and transfer, not on procedural fluency or basic recall, where direct instruction does at least as well. The worked-example literature's outcomes are mostly procedural.
- Design fidelity. The advantage was strongest when the initial struggle phase was carefully designed: problems that admit multiple intuitive but flawed solutions, drawing out prior knowledge, followed by instruction that explicitly compares student attempts with the canonical solution. Naive "let them flounder, then lecture" does not reliably reproduce the effect.
- Population. Effects favored problem-first for 6th grade through college; for younger learners (grades 2 to 5) and for domain-general skills, the direction reversed toward instruction-first.
- Kind of knowledge. Productive failure targets deep, rationale-bearing concepts (in KLI terms, principles). Nobody proposes discovering vocabulary or notation through failure.

The honest synthesis: the literature does not say exposition-first always wins. It says exposition and worked examples win for novices on procedural and factual material and on efficiency; a well-designed struggle phase can win for rationale-rich concepts when the goal is transfer, when the struggle is engineered, and when instruction reliably follows. Note what both traditions share and what the Companion currently lacks: in productive failure, high-quality direct instruction is mandatory, it just comes second. Neither tradition supports questioning without a consolidating expository phase anywhere in the session.

### 3.6 Retrieval practice earns its place as a form (the testing effect)

Actively retrieving material from memory produces substantially better long-term retention than re-studying it. Roediger and Karpicke's classic experiments showed rereaders ahead after five minutes (83% versus 71%) and behind after a week (40% versus 61%) ([The Power of Testing Memory, Perspectives on Psychological Science 2006](http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Roediger-Karpicke-2006_PPS.pdf); [Test-Enhanced Learning, Psychological Science 2006](https://journals.sagepub.com/doi/10.1111/j.1467-9280.2006.01693.x)). The effect is robust across a decade of follow-up work ([Karpicke, Retrieval-Based Learning: A Decade of Progress](https://files.eric.ed.gov/fulltext/ED599273.pdf)).

Implication: for material the student has already acquired (solid, and arguably shaky, mastery), the highest-value move is often neither exposition nor socratic dialogue but a plain retrieval attempt with feedback. Review moments inside sessions should be retrieval events, not re-explanations. Limits: the testing effect is strongest for retention of relatively discrete material; it is not a substitute for initial acquisition, and retrieval of material never properly acquired just rehearses errors.

### 3.7 The preview idea specifically: pre-training and advance organizers

Two lines of evidence bear directly on making the preview a first-class expository opening:

- Mayer's pre-training principle: people learn a complex lesson better when they first learn the names and basic characteristics of its key components. The rationale is load management: front-loading component knowledge frees working memory during the main lesson for building the causal or relational model. The principle is supported by a body of experiments summarized in Mayer and Pilegard's chapter on managing essential processing ([overview](https://sites.google.com/site/cognitivetheorymmlearning/pre-training-principle); [Mayer and Pilegard 2014 chapter record](https://www.researchgate.net/publication/292884042_Principles_for_managing_essential_processing_in_multimedia_learning_Segmenting_pre-training_and_modality_principles); [Mayer's CTML retrospective](https://link.springer.com/article/10.1007/s10648-023-09842-1)).
- Ausubel's advance organizers: introductory material at a higher level of abstraction, given before a lesson, improves learning when it provides a usable conceptual bridge between what the student knows and what is coming. Mayer's own review concluded organizers work when they genuinely scaffold assimilation, and not when they are mere summaries or extra facts ([background on Ausubel and Mayer's findings](https://www.structural-learning.com/post/ausubels-meaningful-learning-theory-teachers-guide)).

Both lines support the preview hypothesis with a shared qualification: a preview helps when it is designed as preparation for the specific cognitive work of the session (naming the components, activating the relevant prior knowledge, providing the bridge), and not when it is a generic summary of the topic. The current Intro Note fails exactly this test, which is consistent with it contributing little.

## 4. What this would mean for the Companion

Stated as direction, not as design:

- The preview becomes the expository opening of the pedagogy, not an optional artifact. The session's first movement is low-demand presentation: name the components, state the definitions, show the shape of the idea, possibly one worked case. Pre-training and the worked-example effect say this is where a novice's session should start; the expertise reversal effect says it should be skippable or compressed when mastery evidence shows the student past it. What is decisively rejected is the current arrangement, where exposition exists only as an off-path artifact the pedagogy never relies on.
- Sessions switch instructional form across the lesson. A session stops being ninety minutes of one register and becomes a sequence of deliberate moves: expository presentation, worked example, socratic questioning, self-explanation prompt, retrieval attempt, chosen per segment and per concept. Socratic dialogue remains the Companion's center of gravity, it just stops being the only tool.
- Form selection consumes the Concept Universe's KC axes. The knowledge-type axis (fact / category / rule) and the modality axis (do versus explain) map, per KLI, to default forms: facts to presentation plus retrieval practice, never extended socratic probing; categories and rules to worked examples and contrasting cases, with induction across varied instances; rule-with-rationale and explain-modality KCs to self-explanation and socratic dialogue, which is where the socratic method has its actual evidential mandate. The condition-response form of a KC tells the tutor what a retrieval or practice event for it even looks like.
- Later, form selection also keys on mastery state. The crossover logic from expertise reversal and the assistance dilemma: expository and worked-example forms for unseen and weak KCs, socratic and self-explanation forms for shaky KCs (where there is now a structure worth probing and an error worth surfacing), retrieval practice for solid KCs to consolidate retention. This is the adaptive version and depends on mastery-per-KC being computed from evidence, so it comes after the static (type-keyed) version.
- Relationship to the Concept Universe: this document describes a consumer of the Universe, not a change to it. Exactly as the student ledger consumes KCs to track evidence, instructional-form selection consumes the KC axes to choose how to teach each component. It is complementary to the Universe and validates the axes' design: if the axes could not drive decisions like these, they would be annotation for its own sake.
- A place for productive failure rather than a rejection of it. For rationale-bearing concepts where transfer is the goal, the session may deliberately invert the order: a short, engineered struggle on a well-chosen problem before the expository consolidation. This is a form in the repertoire, selected when the KC type warrants it, not the default opening.

## 5. Explicitly out of scope for now

- Implementation details of any kind: how forms are represented, how the session engine sequences them, how the preview is generated or merged into the session flow.
- Prompt design: no prompt text, no prompt architecture, no changes to `prompts/`.
- UI: how form switches appear to the student, what happens to the current Prévia da aula surface, admin controls.
- Evaluation design for measuring the improvement (necessary, but a separate discussion).

## 6. Open points

These are genuine invitations to disagree, not rhetorical questions.

- Is the expository opening a presentation or a conversation? The evidence supports low-demand input at the start for novices, but it does not require a monologue. A "warm" expository mode (tutor presents, student is invited to react but not tested) might preserve the Companion's voice. Or it might blur into weak socratic dialogue and lose the load-reduction benefit. Which failure worries you more?
- How much productive failure do we actually want? The meta-analytic effect is real but the design burden is high: it works when the struggle problems are carefully engineered. Our lessons are generated, not hand-crafted by researchers. Is an engineered-struggle form realistic at our content quality today, or should it wait until the type-keyed switching is proven?
- Does the mastery-keyed version need to wait? The document sequences static (type-keyed) selection before adaptive (mastery-keyed) selection because mastery-per-KC does not exist yet. One could argue the reverse: that the largest gains are in not re-exposing students to what they already know, so adaptivity should come first even in a crude form (for example, keyed only on unseen versus not-unseen).
- Is "too socratic" the right diagnosis, or is the real problem "socratic too early"? These lead to different systems. The first says reduce socratic share overall; the second says keep the share but move it to where the student has structure to probe. The evidence reads to me as the second, but the founder's intuition from watching sessions may distinguish them better than the literature can.
- What do we lose? The uniform socratic register is currently part of the product's identity and, plausibly, part of why sessions feel serious. Form-switching risks making sessions feel like a mixed bag of exercises. Is there a version of switching that preserves a single tutorial voice across forms, and is that a design constraint we should state now?
- Do we trust the KC axes to carry this weight? Form selection assumes the knowledge-type and modality tags are reliably assigned during compilation. If tagging quality is mediocre, type-keyed form selection amplifies tagging errors into pedagogy errors. Should form selection degrade gracefully to the current behavior when tags are low-confidence?

## Sources

- Sweller, worked-example effect overview: https://en.wikipedia.org/wiki/Worked-example_effect
- Sweller, cognitive load theory summary: https://mcblogs.montgomerycollege.edu/thehub/wp-content/uploads/2025/02/Cognitive-load_Sweller.pdf
- Barbieri, Miller-Cotto, Clerjuste, Chawla (2023), A Meta-analysis of the Worked Examples Effect on Mathematics Performance, Educational Psychology Review 35(11): https://link.springer.com/article/10.1007/s10648-023-09745-1 (PDF: https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf)
- Kirschner, Sweller, Clark (2006), Why Minimal Guidance During Instruction Does Not Work, Educational Psychologist 41(2): https://www.tandfonline.com/doi/abs/10.1207/s15326985ep4102_1 (PDF: https://itgs.ict.usc.edu/papers/Constructivism_KirschnerEtAl_EP_06.pdf)
- Kalyuga, Ayres, Chandler, Sweller (2003), The Expertise Reversal Effect, Educational Psychologist 38(1): https://www.tandfonline.com/doi/abs/10.1207/S15326985EP3801_4
- Kalyuga (2007), Expertise Reversal Effect and Its Implications for Learner-Tailored Instruction, Educational Psychology Review 19: https://link.springer.com/article/10.1007/s10648-007-9054-3
- Koedinger, Aleven (2007), Exploring the Assistance Dilemma in Experiments with Cognitive Tutors, Educational Psychology Review 19: https://link.springer.com/article/10.1007/s10648-007-9049-0 (ERIC: https://eric.ed.gov/?id=EJ785065)
- Koedinger, McLaren et al. (2008), Is it Better to Give than to Receive?, CogSci: https://www.cs.cmu.edu/~bmclaren/pubs/KoedingerEtAl-IsItBetterToGiveThanToReceive-CogSci2008.pdf
- Koedinger, Corbett, Perfetti (2012), The Knowledge-Learning-Instruction Framework, Cognitive Science 36(5): 757-798: https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1551-6709.2012.01245.x (PDF: http://pact.cs.cmu.edu/pubs/Koedinger,%20Corbett,%20Perfetti%202012-KLI.pdf)
- Bisra, Liu, Nesbit, Salimi, Winne (2018), Inducing Self-Explanation: a Meta-Analysis, Educational Psychology Review 30: https://link.springer.com/article/10.1007/s10648-018-9434-x
- Sinha, Kapur (2021), When Problem Solving Followed by Instruction Works: Evidence for Productive Failure, Review of Educational Research 91(5): https://journals.sagepub.com/doi/10.3102/00346543211019105 (ERIC: https://eric.ed.gov/?id=EJ1308129)
- Kapur, Roll, Productive Failure overview chapter: https://boldscience.org/wp-content/uploads/2025/04/Productive-Failure.pdf
- Roediger, Karpicke (2006), The Power of Testing Memory, Perspectives on Psychological Science 1(3): http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Roediger-Karpicke-2006_PPS.pdf
- Roediger, Karpicke (2006), Test-Enhanced Learning, Psychological Science 17(3): https://journals.sagepub.com/doi/10.1111/j.1467-9280.2006.01693.x
- Karpicke (2017), Retrieval-Based Learning: A Decade of Progress: https://files.eric.ed.gov/fulltext/ED599273.pdf
- Mayer, pre-training principle overview: https://sites.google.com/site/cognitivetheorymmlearning/pre-training-principle
- Mayer, Pilegard (2014), Principles for Managing Essential Processing in Multimedia Learning: https://www.researchgate.net/publication/292884042_Principles_for_managing_essential_processing_in_multimedia_learning_Segmenting_pre-training_and_modality_principles
- Mayer et al. (2024), The Past, Present, and Future of the Cognitive Theory of Multimedia Learning, Educational Psychology Review: https://link.springer.com/article/10.1007/s10648-023-09842-1
- Ausubel advance organizers and Mayer's review, background: https://www.structural-learning.com/post/ausubels-meaningful-learning-theory-teachers-guide
