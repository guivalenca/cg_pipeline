# Companion Session Runtime Restructure Plan

This document captures the platform changes discussed beyond the autonomous Concept Graph pipeline. It explains how the Companion should eventually use Session Plan, Session Focus, Evidence Ledger, and boundary-only Focus Transition Signals to teach granular Concepts without prompt bloat, rushing, or strict mastery traps.

The phases below are starting lines for implementation, not a hard-coded process. They should be adjusted as we learn from implementation and testing.

## Scope In Current Project Split

This is a Companion-runtime document. It does not describe where Concept Graphs
are generated.

Current decision:

- Concept Graph generation is local-first manually invoked tooling, likely
  under `cg_pipeline/`, but remains outside the Companion runtime path.
- Remote OpenClaw on the VPS is used only for browser/operator acquisition
  work when local deterministic fetching is not enough.
- Companion receives only promoted `graph.json` artifacts.
- This repo owns loading, compatibility, prompt rendering, Session Plan /
  Session Focus runtime behavior, Evidence Ledger persistence, and post-session
  evaluation integration.

For the generation/runtime boundary, read
[Concept Graph Project](concept-graph.md) and
[Autonomous Concept Graph Pipeline Plan](concept-graph-pipeline-plan.md).

## Why Restructure The Runtime

The current runtime is simple: the backend generates one `<concept_graph_summary>` at session start, injects it into the first user message with the Student Profile and curriculum context, then the model manages the concept queue internally.

That simplicity becomes fragile as the Concept Graph gets more granular.

The old graph style had one to five broad Concepts per session. The new graph style may have many smaller Concepts and Coverage Criteria. Injecting all of that richly at once risks cost growth, context clutter, shallower teaching, and model confusion.

The target architecture keeps the graph granular internally, but gives the Companion only the right level of context for the current stretch of teaching.

The central idea is:

The full Concept Graph is the curriculum source of truth.

The Session Plan is the compact route for today's Lesson.

The Session Focus is the rich active window for the next part of the dialogue.

The Evidence Ledger records what the student actually showed.

The transcript remains the human conversation.

## Current Runtime Limitations

The current `summary_generator.py` builds one text summary from the selected session concepts. It includes labels, status, knowledge type, known issue, old hard-prerequisite fields, and an action directive. It does not include Coverage Criteria, Common Misconceptions, or Lesson Segment structure.

The current `system_prompt.txt` treats the concept graph summary as the teaching plan. Its old dependency language should be neutralized for v0 empty dependency lists.

That current hard prerequisite rule is too strong for the v0 graph. V0 graph
generation intentionally emits no dependency edges and relies on ordered Lesson
Segments. The three-level dependency model is reserved for future exam-study or
adaptive-remediation work.

The backend currently stores the generated concept graph summary and transcript history, but it does not explicitly store a current Concept, current Lesson Segment, Evidence Ledger, or Session Focus.

There is also a likely personalization issue to fix before deeper restructuring: evaluation already slices namespaced Concept Map entries into raw IDs for LLM use, but tutoring summary generation appears to look up raw `concept_id` directly against the full profile. This can make the tutor treat previously evaluated Concepts as `UNSEEN`.

## General Vision

The Companion should not receive the entire rich graph on every turn.

The Companion should receive a compact map of the Lesson plus a rich active focus.

The backend should own session state.

The tutor model should teach naturally and propose focus transitions only at natural boundaries.

The platform should not force strict mastery before advancing. It should help the student, preserve flow, record weak evidence, and revisit gaps later.

Advance means "move the conversation forward with a learning trail." It does not mean "the student mastered this Concept."

## Prompt And Context Blocks

The future model call should be assembled from several conceptual blocks.

**Static System Prompt** is stable behavior. It defines tone, Socratic teaching, brevity, emotional adaptation, knowledge-type teaching behavior, and rules about Session Focus. It should be cache-friendly.

**Curriculum Context** is short. It tells the model the Course, Module, Subject, and Lesson context. It should not override the Session Plan.

**Student State Slice** is relevant student memory. It contains the student's status, confidence, known issues, recent evidence, and unresolved debts for the Concepts relevant to the current Lesson or current Session Focus. It should not dump the full Student Profile unless needed.

**Session Plan** is the compact route. It lists the Lesson Segments in order, their Instructional Roles, the Concepts in each Segment, student status at a glance, and key dependency/bridge information.

**Session Focus** is the rich active window. It gives the current Lesson Segment, current Concepts, machine-facing descriptions, Coverage Criteria, Common Misconceptions, relevant dependencies, unresolved prerequisites, and the next bridge Concepts.

**Conversation Memory** is the human conversation so far. It may later be compressed, but the raw visible transcript should remain separate from internal learning evidence.

**Evidence Ledger** is structured learning evidence. It is not a transcript and should not be rendered as normal conversation.

## Text-First Prompting

The model should receive structured clear text by default, not raw graph JSON.

This follows the current pattern of `<concept_graph_summary>`, but the content should evolve into clearer blocks such as `<session_plan>` and `<session_focus>`.

The Session Focus should look like a teaching brief:

Current Focus: Tokenizacao e contagem.

Instructional Role: teach.

Current Concept: Tokenizacao em PLN.

Teach: tokenization is controlled division of text into processable units; cover why tokens are not always words and why tokenization affects later counts and vectorization.

Check that the student can explain why tokenization is not just splitting by spaces.

Check that the student can connect tokenization choices to counts, vectorization, or classification.

Watch for the student thinking tokens are always words.

Next bridge: Bag of Words counts tokens, so use tokenization as the bridge into representation.

Raw provenance, extraction confidence, source URLs, critic reports, and source excerpts should not be injected by default.

## Session Plan

Session Plan means the compact ordered plan for a Session.

It is derived from a Lesson, the Lesson Segments produced by the Concept Graph pipeline, and the Student's current Concept Map.

The Lesson Segment's Instructional Role is a planned runtime hint. It helps the platform decide how to position the Segment in the Session Plan and how richly to render it in Session Focus. It is not a property of the Concept itself. The v0 Concept Graph pipeline emits only `teach`; richer roles are reserved for runtime-aware work.

A newly assigned Concept should normally appear in a Segment with Instructional Role `teach`. `Practice`, `overview`, `review`, and `repair` make more sense when the Concept has already been seen in some capacity, is only being oriented lightly, or is being revisited because of prior evidence or Unresolved Learning Debt, so they should be introduced with the later Session Plan / Session Focus runtime changes rather than Phase 7 graph generation.

It should answer:

What are we trying to cover today?

In what order?

Which Lesson Segment is current?

Which Concepts are overview, teach, practice, review, or repair?

Which Concepts are already solid, shaky, weak, or unseen for this student?

Which dependencies shape the route?

The Session Plan should stay compact enough to fit in context even when the Lesson has many micro-Concepts.

The model should use the Session Plan as a route map, not as an instruction to rush through every Concept.

## Session Focus

Session Focus means the rich active window of the Session Plan.

It usually corresponds to one Lesson Segment, not exactly one Concept.

The Session Focus may contain one Concept, several related Concepts, a repair slice, or a review/synthesis slice. The graph should not enforce a hard cap, but the focus should be small enough for a natural stretch of dialogue.

Session Focus exists because a model can teach more deeply when it has the detailed criteria and misconceptions for the current topic, rather than a large undifferentiated list.

The Session Focus should contain:

Current Lesson Segment.

Instructional Role.

Current Concepts.

Machine-facing Concept descriptions.

Coverage Criteria.

Common Misconceptions.

Relevant Blocking, Hard, and Soft Dependencies.

Student-specific known issues for those Concepts.

Unresolved Learning Debt relevant now.

Next bridge Concepts.

## Student State Slice

The Student State Slice should be narrow and relevant.

It should include the Student's name and basic session familiarity, but most of the value comes from Concept-specific state.

For today's Concepts, it should include Concept Status, Confidence, evidence summaries, source notes, known issues, and Unresolved Learning Debt.

The platform should fix the current profile slicing issue by applying `profile_slice_for_llm(profile, module_id, subject_id)` or equivalent before generating tutoring context.

Future versions may inject student state on a need-to-know basis, but the first implementation should favor correctness and simplicity: include the relevant Lesson slice and active focus slice.

## Future Dependency Behavior

The runtime should use this three-level dependency model only after dependency
inference is reintroduced.

Blocking Dependency means the dependent Concept cannot be meaningfully taught without explicit prerequisite evidence. Blocking should be rare.

Hard Dependency means the prerequisite is important and should normally be checked, but it should not create infinite loops. If the student is stuck, the gap can become Unresolved Learning Debt.

Soft Dependency means helpful background or scaffolding. It does not block advancement.

The old prompt language says hard prerequisites must be verified before teaching the dependent concept. That should stay disabled while v0 dependency lists are empty. In a future dependency-enabled graph, blocking behavior belongs only to Blocking Dependencies.

The Companion should assume normal Course/Module prior knowledge unless the student's answers reveal a gap. The platform should not add an `assumed_background` schema in the first restructuring pass.

## Focus Transition Signal

Focus Transition Signal means a hidden boundary-only event emitted by the Companion when the current focus naturally reaches a boundary.

It is not emitted every turn.

It is not a final evaluation.

It is not a per-turn grade.

It is not shown to the student.

It is stripped before transcript storage.

It proposes that the backend should stay, advance, defer unresolved criteria, revisit a dependency, or move to closing/synthesis.

The signal should be emitted only when:

The current Session Focus is ready to advance.

The current Session Focus should be deferred with Unresolved Learning Debt.

A Blocking Dependency prevents meaningful progress.

The Session should shift to closing or synthesis.

No signal means continue with the current focus.

The implementation can use a strict machine-readable envelope if needed for parsing, but teaching context sent into the model should remain text-first. The signal format is an implementation detail as long as it is hidden, bounded, parseable, and stripped from the human transcript.

## Backend Ownership And Optimistic Advancement

The backend owns the session state transition.

The Companion proposes a transition through a Focus Transition Signal.

The backend accepts the proposal optimistically by default, updates the Session Focus, and records the evidence. This avoids latency spikes and prevents a lightweight verifier from trapping the student.

The backend should not run a second strong model in the critical path just to decide whether the student can advance.

The backend should not hard-block progress except for clear Blocking Dependency cases.

An async auditor can later review evidence quality and update the Evidence Ledger. The auditor should not block the student response.

## Evidence Ledger

Evidence Ledger means structured learning evidence observed during the Session.

It is separate from the transcript.

It is collected by the tutoring runtime, not by the Concept Graph creation pipeline.

It may be updated from Focus Transition Signals, async auditors, post-session evaluation, or future lightweight parallel AI systems that inspect the conversation.

It should record which Concepts and Coverage Criteria have evidence, which are weak, and which became Unresolved Learning Debt.

It should not pretend to be final mastery. It is a learning trail.

The Evidence Ledger may eventually improve post-session evaluation, session notes, and future Student State Slices.

## Unresolved Learning Debt

Unresolved Learning Debt means a Coverage Criterion or misconception that did not get enough evidence during the Session.

The platform should carry it forward rather than force mastery.

Revisit policy:

Immediate revisit only if the gap blocks the next Concept through a Blocking Dependency.

Natural re-entry if a later Segment depends on it or offers a better concrete example.

End-of-session synthesis if it never fits naturally during the flow.

Future-session carry-forward if the debt remains unresolved.

The goal is to help the student, not to trap them.

## Bounded Remediation

Bounded remediation means the Companion should not keep repairing the same gap indefinitely.

If the student misses a Coverage Criterion, the tutor can try a light repair when it fits the flow.

If the student still struggles, the tutor should mark the gap as Unresolved Learning Debt and continue when appropriate.

This prevents the session from becoming punitive or stuck.

The exact retry count should not be hard-coded too early. A good starting policy is one repair attempt for non-blocking gaps and more careful handling for Blocking Dependencies.

## Conversation Memory And Compression

The transcript remains the human-readable conversation.

Internal signals, Evidence Ledger entries, and backend planning state should not pollute the transcript.

Future versions can compress conversation memory to improve caching and cost. Compression should preserve pedagogically relevant information: what was asked, what the student answered, what misconceptions appeared, and what evidence was collected.

Compression should not replace the Evidence Ledger. The transcript summary tells what happened; the Evidence Ledger tells what was evidenced.

## Post-Session Evaluation

As the graph becomes granular, post-session evaluation should not blindly evaluate the entire Subject graph.

It should prefer the Session's Concepts and relevant Unresolved Learning Debt.

The existing Session Spec should become more important. The evaluator should know which Lesson Segments and Concepts were planned, which were reached, which were deferred, and what the Evidence Ledger recorded.

This should reduce cost, improve grounding, and avoid forcing the evaluator to score Concepts that were never part of the Session.

## Prompt Changes Needed

The static system prompt should be updated to understand Session Plan and Session Focus.

It should say that Session Plan is the route and Session Focus is the active teaching brief.

It should tell the Companion to teach the current focus deeply enough to gather evidence, not to rush through the full plan.

It should define Coverage Criteria as the evidence standard for coverage.

It should define Common Misconceptions as things to watch for, not a list to lecture through.

It should avoid hard-prerequisite behavior while v0 dependency lists are empty.
Future dependency-enabled graphs should replace the old hard-prerequisite rule
with Blocking, Hard, and Soft Dependency behavior.

It should define bounded remediation and Unresolved Learning Debt.

It should define when to emit a Focus Transition Signal and when not to.

It should explicitly say no per-turn grading and no visible mention of internal adaptation.

It should preserve the existing strong teaching rules: short responses, one question per turn, Socratic teaching for conceptual/applied knowledge, direct instruction for factual knowledge, and emotional adaptation.

## Platform State Changes

The session state stored in Redis should eventually include:

Session Plan identifier or embedded compact plan.

Current Lesson Segment ID.

Current Concept IDs.

Visited Lesson Segments.

Deferred Concepts and Coverage Criteria.

Evidence Ledger.

Unresolved Learning Debt.

Prompt variant and runtime mode.

Signal parsing diagnostics.

The persistent database should eventually store the Evidence Ledger or a compact post-session version of it with the transcript/evaluation record.

## Signal Safety

Focus Transition Signals must not appear in the user interface.

Focus Transition Signals must not appear in the human transcript.

If signal parsing fails, the platform should keep the visible assistant response and continue with the previous focus unless the failure is severe.

The platform should log signal parse failures for debugging.

The model should not be allowed to set final Confidence directly through the signal.

The model should not be allowed to mark a Concept permanently mastered through the signal.

## Cost And Latency Principles

Do not add a verifier call to every turn.

Do not emit Focus Transition Signals every turn.

Do not run a strong model in the critical path to approve every focus change.

Use the tutor model's boundary signal as a proposal.

Update focus optimistically.

Run lightweight or async auditing only after the student response is returned, or in batch.

Keep static prompt cacheable.

Keep Session Plan compact.

Keep Session Focus rich but small.

Compress transcript only when needed.

## Implementation Phases

These phases are starting lines, not a rigid plan.

### Phase 0: Correct Current Context Bugs

Fix the Concept Map slicing issue in tutoring preparation so student state is read correctly.

Add compatibility language for Lessons while keeping old `day_presets` graphs working.

Remove or neutralize the current hard-prerequisite language for v0 empty
dependency lists. Keep future `blocking`, `hard`, and `soft` semantics from
conflicting with the old hard-prerequisite wording when dependencies return.

### Phase 1: Enriched Static Session Brief

Before dynamic focus exists, enrich the current summary generator.

Include machine-facing Concept descriptions, Coverage Criteria, Common Misconceptions, dependency levels, and Lesson Segment information.

Render this as structured text, not raw JSON.

This phase does not create dynamic Session Focus. It gives immediate benefit and tests whether richer Concepts improve teaching.

### Phase 2: Session Plan And Initial Session Focus

Introduce a Session Plan builder.

Introduce a Session Focus renderer.

Store current Lesson Segment and current Concepts in backend session state.

At session start, inject compact Session Plan plus rich initial Session Focus.

The focus may still be static during this phase. That is acceptable as a stepping stone, but it is not the target architecture.

### Phase 3: Boundary-Only Focus Transition Signal

Teach the model to emit a hidden Focus Transition Signal only at natural focus boundaries.

Parse the signal in the backend.

Strip the signal before returning text to the user.

Do not store the signal in the human transcript.

Update current Session Focus optimistically.

Do not add a verifier call in the critical path.

### Phase 4: Evidence Ledger And Unresolved Learning Debt

Persist an Evidence Ledger in session state.

Record met, weak, and unresolved Coverage Criteria.

Carry Unresolved Learning Debt into later Session Focus selection, closing synthesis, and post-session evaluation.

Add bounded remediation behavior to the prompt and backend planner.

### Phase 5: Async Audit And Conversation Compression

Add optional lightweight async auditing of Focus Transition Signals and evidence summaries.

Use auditors to update the Evidence Ledger, not to block live conversation.

Add conversation compression when context growth becomes a real issue.

Keep transcript summary separate from Evidence Ledger.

### Phase 6: Evaluation And Notes Integration

Update post-session evaluation to use Session Plan, reached Concepts, Evidence Ledger, and Unresolved Learning Debt.

Avoid evaluating the entire Subject graph when the Session only covered a Lesson slice.

Update session notes to use the richer Lesson Segment and Evidence Ledger structure.

### Phase 7: Companion Simulation And QA

Add selective Companion Simulation later.

Do not include it in the first runtime restructure.

Use it for dense Lessons, suspicious Segments, prompt changes, or high-stakes Concepts once the core runtime is stable.

## Risks

The model could become too narrow if Session Focus lacks enough surrounding context. Mitigation: always include compact Session Plan and next bridge Concepts.

The model could rush if it treats focus transitions as a checklist. Mitigation: boundary-only signal, Coverage Criteria, and prompt language that advance does not mean mastery.

The system could trap students if dependencies are too strict. Mitigation: rare Blocking Dependencies, Hard Dependencies as debt-capable, bounded remediation.

Costs could spike if verification is synchronous. Mitigation: no per-turn verifier, no per-turn signal, optimistic advancement, async audit only.

Signals could leak to users or transcripts. Mitigation: strict stripping, tests, and signal diagnostics.

The Evidence Ledger could become fake precision. Mitigation: record qualitative evidence and criterion status, not final mastery.

The runtime could become over-engineered before graph quality is solved. Mitigation: implement phases incrementally and keep the pipeline-generated Concepts simple and strong.

## Success Criteria

The Companion receives enough context to teach the current focus deeply.

The Companion no longer has to manage a large rich graph internally.

The student experience stays conversational and does not feel graded every turn.

The backend knows what focus is active.

The transcript remains clean.

The Evidence Ledger records what was evidenced without pretending to be final mastery.

The system can advance with unresolved gaps and revisit them intelligently.

Prompt cost and latency remain bounded.

The runtime can use the new granular Concept Graph without regressing into shallow teaching or concept rushing.
