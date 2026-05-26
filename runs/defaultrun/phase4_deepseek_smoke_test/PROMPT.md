# DeepSeek Pro Thinking Smoke Test Prompt: Phase 4 Lesson Reconciliation Evaluation

You are evaluating the quality of Phase 4 Lesson Reconciliation for a Concept Graph pipeline.

## Project Definitions

- Candidate Concept: a source-local teachable idea proposed before merging, deduplication, or final ID assignment.
- Concept: a final teachable idea small enough for the Companion to check with one to three focused questions. Avoid treating vague topics, activities, tool names, source titles, incidental mentions, or tiny fragments as Concepts.
- Coverage Criterion: an observable student behavior that shows evidence of covering a Concept in a session.
- Concept Provenance: lightweight structured evidence showing which sources, source roles, or inferred reasons support a Concept.
- Lesson Reconciliation: the lesson-local pass that merges source-grounded Candidate Concepts, removes incidental material, and preserves important lesson content.
- Candidate Pruning Reason: a controlled reason for removing a Candidate Concept during reconciliation. Avoid silent deletion.

## Input Files

You will receive one JSON packet per reconciled lesson. Each packet contains:

- lesson metadata: title, description, related labels;
- before_phase4_candidates: original candidate concepts before reconciliation;
- after_phase4.reconciled_candidates: final accepted lesson-local concepts;
- after_phase4.pruned_candidates: candidates removed during reconciliation;
- after_phase4.review_candidates: candidates preserved for human/later review;
- after_phase4.candidate_assignments: mapping from every input candidate to accepted, pruned, or review status.

Do not use any prior human score. Make your own judgment from the packets.

## Evaluation Dimensions

Score each lesson from 0 to 3 on each dimension:

- 0 = harmful or invalid
- 1 = weak / needs human repair
- 2 = acceptable with minor issues
- 3 = strong

Dimensions:

1. Concept validity: accepted items are real teachable Concepts, not topics, activities, tool names, source titles, incidental details, or fragments.
2. Granularity: reconciliation merges duplicates without making concepts too broad, preserves distinct teachable ideas, and avoids excessive fragmentation.
3. Evidence preservation: original candidates remain traceable through accepted, pruned, or review outputs; source roles, evidence types, anchors, and reasons remain usable. This dimension is about auditability, not whether the semantic decision was correct.
4. Assignment quality: every input candidate has a sensible assignment; accepted/pruned/review statuses are used correctly. This dimension is about the status decision, not merely whether an assignment row exists.
5. Pruning and review quality: pruned candidates are actually low-value, incidental, unsupported, duplicate, too broad, or unrelated; uncertain candidates are reviewed rather than silently dropped.
6. Coverage criteria quality: criteria are observable, checkable, and suitable for one to three focused tutor questions.
7. Lesson coherence: the final accepted set reflects what the lesson appears to teach, based on lesson metadata and candidate evidence.
8. Net Phase 4 benefit: compared with the original candidate list, Phase 4 reduced noise while preserving useful content for later Subject Merge and tutoring.

## Net Score Guardrails

Use these caps unless the packet gives unusually strong counter-evidence:

- Net cannot be 3 if the accepted set contains a meaningful block of off-lesson, administrative, setup, legal, career, environment, or generic programming concepts that the lesson metadata does not clearly support.
- Net cannot be 3 if any important part of the lesson is left in review, pruned under a questionable duplicate-like reason, or represented only by vague/general accepted concepts.
- Net cannot be above 2 when a lesson has obvious off-lesson accepted material, even if the remaining accepted concepts are good.
- Net cannot be above 1 when a large share of candidates are in unresolved review because a model or deterministic fallback omitted them.
- Net cannot be above 1 when many distinct teachable sub-concepts are pruned as duplicates but are not represented by accepted concepts.
- A lesson may still receive high Evidence Preservation if traceability is intact, even when Concept, Assignment, Pruning, or Net scores are low.

## Required Flags

Add any relevant flags per lesson:

- granularity_loss
- over_merge
- under_merge
- unsupported_acceptance
- questionable_prune
- review_needed
- off_lesson_acceptance
- strong_improvement

## Required Output

Return exactly these sections:

1. Overall Judgment
   - 3-6 sentences on whether Phase 4 is ready for downstream Subject Merge.

2. Lesson Score Matrix
   - A markdown table with one row per lesson and columns:
     Lesson, Concept, Granularity, Evidence, Assignment, Prune/Review, Criteria, Coherence, Net, Flags.

3. High-Confidence Problems
   - Bullet list of the most important defects, with lesson code and concrete examples.

4. Strong Transformations
   - Bullet list of places where Phase 4 clearly improved the candidate set.

5. Recommendation
   - One of: proceed, proceed_with_caution, repair_before_phase5.
   - Include the minimum repair scope if repair is needed.

## Evaluation Rules

- Do not judge from labels only. Compare descriptions, coverage criteria, assignments, pruned/review explanations, and lesson metadata.
- Do not reward structural validity if the accepted concepts are off-lesson or too broad.
- Treat review as unresolved work, not as acceptance.
- Treat deterministic omission review explanations as a process warning.
- Penalize accepted candidates that are setup instructions, environment configuration, career/certification details, legal/admin topics, or unrelated programming basics unless the lesson metadata clearly supports them as central lesson content.
- Penalize pruning that removes distinct teachable concepts under a duplicate-like reason, especially when the explanation says the concept belongs elsewhere but no accepted concept actually represents it.
- Distinguish "source-backed" from "lesson-worthy": a source-backed candidate can still be incidental, off-lesson, too broad, or unsuitable as a final Concept.
- Do not assume that a larger accepted set is better. Reward the smallest set that preserves the lesson's teachable distinctions.
- Do not assume that an operational tool step is a Concept just because a student might perform it. It must teach a transferable idea that the Companion could check with focused questions.
- Be strict but fair: a lesson can be structurally valid and still semantically weak.
