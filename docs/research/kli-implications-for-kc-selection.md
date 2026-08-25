# KLI implications for KC Selection

Date: 2026-08-23

This note supports the discussion in [KC Selection prompt: discussion and
draft](https://linear.app/thecompanion/issue/DEV-28/kc-selection-prompt-discussion-and-draft).
It does not draft the prompt. It separates claims made by the
Knowledge-Learning-Instruction framework from ways we might apply them in
Concept Universe.

The local product terms come from [CONTEXT.md](../../CONTEXT.md). A KC
Candidate contains a task, answer, statement, and axes. KC Selection chooses a
lesson-local set against the curricular record. The map for this effort says
that its decisions, rather than the older ADRs, are authoritative.

## Bottom line

KLI gives us a stronger account of a KC than "a small topic." A KC is an
unobservable piece of knowledge that should explain a learner's performance
across related tasks. The task and answer attached to a KC Candidate make the
knowledge concrete by showing one performance we expect from a learner. They
do not prove that the learner has acquired it, nor do they define a complete
tutoring policy.

KLI also gives us a good reason to care about different kinds of performance.
A learner may be able to do something without explaining it, explain it
without applying it, or do both. Two candidates about similar subject matter
can therefore contribute different knowledge to a lesson. Their axes only
raise that possibility. The tasks must show that the performances differ, and
the curricular record must make both performances worth teaching.

KLI does not settle the hard curriculum question. It assumes that someone has
specified what students should learn in a course, then asks what knowledge
that requires and how to teach and assess it. Source-derived KC Candidates can
make a curricular intention more concrete, show relationships the record left
implicit, and expose missing coverage. They cannot tell us which of several
plausible intentions the curriculum owner meant without an added product
policy.

## 1. What a KC is and what task plus answer contribute

### Findings from the research

Koedinger, Corbett, and Perfetti define a KC as an acquired unit of cognitive
function or structure inferred from performance on a set of related tasks.
They deliberately use the term broadly. It can cover a fact, concept, skill,
rule, schema, principle, misconception, or other piece of cognition. KCs are
not observed directly. Learner responses in assessment events are the
evidence used to infer them. An activity in a tutor can be both assessment and
instruction when the tutor evaluates a response and then supplies feedback or
help. See sections 2.1 and 3 of the [original KLI
paper](https://doi.org/10.1111/j.1551-6709.2012.01245.x).

That definition makes the project fields easier to explain:

- The **statement** names the proposed knowledge in a reusable form.
- The **task** supplies conditions under which the learner must use that
  knowledge.
- The **answer** shows the response that would count as success on that task.

This mapping is an application of KLI, not terminology used by the paper. It
is still a faithful one. KLI describes KCs through conditions of application
and responses, and it calls evaluated learner responses assessment events.

One task and answer are not enough to establish mastery. KLI says even simple
KCs need multiple assessment events to support an inference of robust
acquisition. For knowledge that should generalize, the tasks must vary enough
to reveal whether the learner acquired the right conditions of application.
Immediate accuracy is weaker evidence than delayed success, and accuracy does
not establish fluency without timing evidence. Integrative KCs may require a
comparison between easier tasks that use supporting KCs and harder tasks that
also use the integrative KC. See sections 3.1.1, 3.1.3, and 3.3.1 of the
[KLI paper](https://files.eric.ed.gov/fulltext/ED535880.pdf).

The framework supports instruction that adapts at KC level. It distinguishes
early induction and sense making from later refinement and fluency building.
In one example, the tutor faded worked steps only after its student model
estimated that a learner could explain the relevant KC. The underlying study
found better learning with adaptive fading than with fixed fading or problem
solving alone. See section 6.3 of KLI and [Salden et al.'s two
experiments](https://doi.org/10.1007/s11251-009-9107-8).

This kind of adaptation depends on an estimate built from observations, not a
literal comparison with one answer string. The earlier knowledge-tracing work
modeled the probability that a learner had acquired each production rule and
used those estimates to choose an individualized sequence until each rule met
the system's mastery policy. See [Corbett and Anderson's primary
study](https://doi.org/10.1007/BF01099821).

Aleven and Koedinger provide a concrete version of repair during instruction.
Their Geometry Cognitive Tutor required correct solution steps and correct
explanations, gave feedback and progressively more detailed hints, assigned
remedial problems from its student model, and required every targeted skill to
cross a mastery threshold. In two classroom experiments, adding guided
self-explanation to guided problem solving improved explanation and transfer.
The paper also warns that the quality of explanations matters. In its study,
feedback and hints contributed to the eventual correctness of many
explanations. See [Aleven and Koedinger
2002](https://doi.org/10.1207/s15516709cog2602_1), especially sections 2, 3,
7.1, and 7.2.

### Product inference

The task and answer should tell a selector more than "what this candidate is
about." They show what the tutor will eventually ask the Student to produce
and what successful performance looks like. This matters to selection because
two similar statements can demand different evidence from the Student.

It is also reasonable to explain that the tutor will use the task and answer
to judge whether to continue supporting this KC or move forward. The careful
version is "evidence toward that decision." KLI does not justify saying that
one expected answer proves understanding, or that a tutor should repeat the
same exchange until the Student matches it. A later tutoring design still has
to decide what evidence is sufficient, how varied it must be, and what repair
to try after weak evidence.

Put plainly, KLI supports refusing to move on because a learner produced
vaguely relevant talk. It does not support treating one model answer as a
complete mastery test.

## 2. Knowledge types and complementary candidates

### Findings from the research

KLI does not define the project's `explain`/`do` and
`concept`/`procedure` fields as two orthogonal binary axes. Its taxonomy asks
four different questions about a KC:

1. Are its conditions of application constant or variable?
2. Is its response constant or variable?
3. Can the learner verbalize it?
4. Does it have an accessible rationale?

Labels such as fact, concept, skill, procedure, rule, and principle are rough
names for combinations of those properties. The paper explicitly warns that
the labels do not map one-to-one to the taxonomy. See Tables 2 and 3 and
section 3.1 of the [KLI
paper](https://doi.org/10.1111/j.1551-6709.2012.01245.x).

The closest KLI distinction to `explain` and `do` is observable behavior. A
learner can:

- do but not explain, which provides evidence for non-verbal knowledge;
- explain but not do, which may indicate inert verbal knowledge;
- do and explain, which provides evidence for both.

KLI treats verbal and non-verbal knowledge of the same content as able to
coexist. It also reports that different assessment tasks can reveal different
mixtures of the two. This is why an action and an explanation about nearby
content are not automatically duplicates.

The distinction affects instruction. KLI proposes that simple associations
and some non-verbal skills may benefit from retrieval and practice, while
complex rules, integrated knowledge, and KCs with rationales may need worked
examples, comparisons, explanation, or dialog. These are conditional
hypotheses, not a lookup table. The paper notes that verbalization can waste
time or interfere in some mainly perceptual tasks. See sections 3.1.4, 3.1.5,
3.2, and 3.3.2 of the [KLI
paper](https://files.eric.ed.gov/fulltext/ED535880.pdf).

The classroom evidence for complementarity is strongest when explanation is
paired with action, not substituted for it. In Aleven and Koedinger's study,
students who explained their solution steps developed better explanation and
transfer while continuing to solve problems. The authors interpret the result
as better integrated verbal and visual knowledge and less reliance on shallow
procedures. [Aleven and Koedinger
2002](https://doi.org/10.1207/s15516709cog2602_1) supports the possibility
that explanation and action around the same subject can make distinct
contributions.

### Product inference

The project's axes are useful summaries of the performance and knowledge a
task emphasizes. They are KLI-informed, but they are not the KLI taxonomy.
The eventual prompt should not imply otherwise.

Axis differences are evidence to inspect, not a selection rule. Two candidates
are plausibly complementary when their tasks ask for distinct demonstrations
that the lesson actually values. For example, one may test use in a case while
another tests a rationale that supports transfer. They remain redundant when
the different labels hide substantially the same learner performance, or when
the curricular record only calls for one form.

The whole set matters. Relevance to the subject gets a candidate considered.
Its distinct contribution to what the Student should know, explain, or do
decides whether it belongs beside the others. KLI supports this logic because
complex performance may depend on several KCs and because different tasks can
expose different forms of knowledge. KLI does not supply an algorithm for
choosing the set.

## 3. The curricular record and source-derived candidates

### Findings from the research

KLI starts with target academic learning. It recommends focusing a KC analysis
on knowledge students should acquire in a given course. The target content and
target Student population determine the useful level of decomposition. A
lower-level prerequisite may be treated as already mastered only when the
incoming population supports that assumption. See section 3 and notes 1 and 9
of the [KLI paper](https://files.eric.ed.gov/fulltext/ED535880.pdf).

The framework distinguishes knowledge needed to achieve instructional
objectives from the objectives themselves. Its job is to analyze the former
at a useful level. It does not decide what a course ought to value. See section
7 of the [KLI
paper](https://doi.org/10.1111/j.1551-6709.2012.01245.x).

Detailed task analysis can reveal hidden prerequisites, misconceptions, and
integrative KCs that a broad objective does not list. KLI also calls the work
of identifying KCs partly an art because knowledge is unobservable and the
available analytic tools are limited. Later primary research showed that
learner data can expose a flawed KC decomposition and that instruction built
from the improved model can produce better learning. That makes a KC model a
testable hypothesis, not a fact guaranteed by a fluent statement. See
[Koedinger et al. 2013](https://doi.org/10.1007/978-3-642-39112-5_43).

KLI says nothing about curricular records, source publications, or selecting
source-derived candidates. It supplies no rule for deciding when source
content may repair an ambiguous syllabus entry. Any answer to that question
is an inference or a product decision.

### Product inference

The curricular record and KC Candidates have different authority:

- The curricular record says why this lesson exists and which direction the
  institution intends.
- The KC Candidates show, at higher resolution, what the validated Source
  Publications make teachable and assessable.

"Meet in the middle" should be asymmetric. The record chooses the direction.
The candidates provide detail inside that direction. They can show that two
forms of knowledge belong together, that a prerequisite is needed for the
intended performance, or that the sources do not support part of the record.
They cannot silently choose a new direction simply because the available
candidates form a coherent story.

This does not reduce selection to literal phrase matching. A rich record can
justify knowledge it implies without naming, especially a prerequisite or an
integrative KC needed to perform the intended work. The selector should be
able to read the candidates together and recognize those relationships. The
limit is that every inclusion still needs a traceable curricular reason.

A sparse or ambiguous record can produce three different cases:

1. **The candidates fit no plausible reading of the record.** This is a
   coverage gap or a bad record, not permission to invent a lesson.
2. **The candidates support several plausible readings.** The intended lesson
   is underdetermined. Candidate coherence cannot tell us which reading the
   curriculum owner meant.
3. **The candidates add detail to one plausible, textually anchored reading.**
   They may supply the missing specificity, but the result remains an
   interpretation rather than an intention stated by the record.

In the third case, the candidate set can supply meaning without replacing
curricular intention. It fills in the "what" and "how" inside an anchored
"why." In the second case, doing the same thing would hide a product choice
inside the model's output.

## 4. Implications and risks for the later prompt discussion

These are design implications, not prompt text.

| Item | Status | Implication or risk |
| --- | --- | --- |
| Define a KC as knowledge inferred through performance across related tasks | KLI finding | Avoid defining the KC as a statement, topic, or single task. |
| Explain the task and answer as one observable demonstration and its expected response | Product inference grounded in KLI | This makes their later tutoring role concrete without claiming one response proves mastery. |
| Tell the selector that the tutor will use performance evidence to advance or repair | Product inference | Keep the claim at the level of evidence. A mastery threshold and repair policy belong to later tutoring design. |
| Treat `explain`/`do` and `concept`/`procedure` as useful summaries | Product decision | Call them KLI-informed. Presenting them as the KLI taxonomy would be inaccurate. |
| Let similar candidates coexist when their tasks demand distinct, curriculum-valued evidence | Product inference grounded in KLI | Axis mismatch alone must not manufacture complementarity. |
| Judge contribution to the whole selected set, not isolated relevance | Product decision consistent with KLI | KLI explains why different KCs and evidence types may combine, but does not define the optimization rule. |
| Let candidates elaborate a curricular direction | Product inference | Require an anchor in title, description, or subjects so source emphasis does not become curriculum intention. |
| Report sparse-record ambiguity and missing coverage | Product decision | Otherwise the model may turn source availability into a silent curriculum rewrite. |
| Infer prerequisite inclusion | Open product decision | The answer depends on the intended Student baseline, which the current selection input does not state. |
| Infer intention from a coherent candidate set when the record permits several readings | Open product decision | KLI cannot authorize this. If allowed, it should be explicit and auditable. |

The later discussion still needs to settle four questions:

1. How much curricular support is enough for a candidate that the record does
   not name directly?
2. What learner baseline should the selector assume when judging
   prerequisites?
3. When the record is sparse, should the selector make the narrowest anchored
   selection, make a qualified interpretation, or stop with an ambiguity
   signal?
4. Should the batch-level gap field cover ambiguity and curricular conflict as
   well as missing source coverage?

## Primary sources

- Kenneth R. Koedinger, Albert T. Corbett, and Charles Perfetti. ["The
  Knowledge-Learning-Instruction Framework: Bridging the Science-Practice
  Chasm to Enhance Robust Student
  Learning"](https://doi.org/10.1111/j.1551-6709.2012.01245.x), 2012.
- Vincent Aleven and Kenneth R. Koedinger. ["An Effective Metacognitive
  Strategy: Learning by Doing and Explaining with a Computer-Based Cognitive
  Tutor"](https://doi.org/10.1207/s15516709cog2602_1), 2002.
- Albert T. Corbett and John R. Anderson. ["Knowledge Tracing: Modeling the
  Acquisition of Procedural
  Knowledge"](https://doi.org/10.1007/BF01099821), 1995.
- Ron J. C. M. Salden, Vincent Aleven, Rolf Schwonke, and Alexander Renkl.
  ["The Expertise Reversal Effect and Worked Examples in Tutored Problem
  Solving"](https://doi.org/10.1007/s11251-009-9107-8), 2010.
- Kenneth R. Koedinger, John C. Stamper, Elizabeth A. McLaughlin, and Tristan
  Nixon. ["Using Data-Driven Discovery of Better Student Models to Improve
  Student Learning"](https://doi.org/10.1007/978-3-642-39112-5_43), 2013.
