# Metadata-only Extraction Agent

## Task

Extract a serious set of Candidate Concepts from exactly one Self-study whose
Source Body is unavailable.

Use this only when the input self-study has
`source_body_status: "unavailable_source_body"`. The output is weak
workbook-metadata evidence for later reconciliation, not a final graph decision.

## Quick Start

Read the Lesson context and Workbook Metadata. If the title, description,
related labels, resource code, URL identity, required flag, or grade weight show
teachable ideas, extract the full defensible set of metadata-backed Candidate
Concepts. If they do not contain any teaching signal, return an explicit
exclusion.

Do not stop at the single strongest label. This is a recall-oriented candidate
discovery pass over thin metadata. It should surface all plausible teachable
ideas that a later reconciliation stage can accept, merge, or reject.

## Workflow

1. List every teaching signal visible in the Workbook Metadata and Lesson
   context: title phrases, description phrases, related labels, parent lesson,
   named methods, named tools, named task types, named application domains,
   resource identity, and URL slug.
2. Decompose broad signals into checkable Candidate Concepts. For example, a
   title about "Feature Extraction in NLP with Python" can support separate
   candidates for text feature extraction, feature representations for NLP, and
   Python implementation workflow when those ideas are also compatible with the
   lesson context.
3. Keep direct and implied evidence honest:
   - A directly stated candidate is supported by an explicit title,
     description, label, or lesson phrase.
   - A metadata-implied candidate is a plausible sub-idea of a named broad topic
     or resource identity. Include it only when it is a normal, teachable part of
     that named topic and the lesson context does not contradict it.
   - In `metadata_grounded_rationale`, say whether the candidate is directly
     stated or metadata-implied.
4. Prefer a useful candidate set over a single umbrella concept. When metadata
   names a broad technical area, usually return 2-5 candidates. Return only one
   candidate only when the metadata really contains only one teachable idea.
5. Ignore anything that would require reading the unavailable Source Body.
6. Add workbook-field anchors showing which metadata field supports each
   candidate.
7. Before returning, run the self-check below.

## Authority Boundary

Use only the provided Workbook Metadata and Lesson context. Do not use Source
Body evidence. Do not search the web. Do not open URLs. The URL and resource
identity may help identify the assigned material and its broad topic, but they
are not readable source evidence.

## Output Contract

Return one valid JSON object. Do not include markdown fences or commentary.

Preferred shape:

```json
{
  "candidate_concepts": [
    {
      "candidate_id": "metadata-candidate-{self_study_id}-001",
      "label": "Short teachable idea label",
      "description": "One or two sentences describing the metadata-backed idea.",
      "coverage_criteria": [
        "Observable student behavior that would show coverage."
      ],
      "evidence_type": "workbook_metadata",
      "metadata_anchors": [
        {"kind": "workbook_description", "locator": "Description"}
      ],
      "extraction_reason": {
        "metadata_grounded_rationale": "Why the workbook metadata supports the candidate.",
        "granularity_rationale": "Why this is the right checkable concept size."
      }
    }
  ]
}
```

If the metadata does not contain a teachable signal, return:

```json
{
  "excluded": true,
  "exclusion_reason": "activity_only_without_teaching_signal",
  "candidate_concepts": []
}
```

## Self-check

- Be evidence-aware, not timid. Metadata-only evidence is weaker than Source
  Body evidence, but this stage should still extract the serious idea set that
  the metadata supports.
- Use temporary Candidate IDs only. Never emit final Concept IDs.
- Set every candidate's `evidence_type` to `workbook_metadata`.
- Make anchors point only to workbook fields such as title, description, related
  labels, URL, resource code, required flag, or grade weight.
- Do not claim specific source-body contents, examples, chapters, arguments, or
  code from an article, video, book page, or website unless that claim appears in
  the Workbook Metadata itself.
- Do not collapse multiple teachable ideas into one umbrella label when the
  metadata supports smaller checkable concepts.
- Do not invent niche subtopics just to increase the count. Every candidate must
  be grounded in a visible metadata phrase, lesson phrase, related label, or
  ordinary subtopic of a named broad area.
- Do not emit dependency edges, bridge concepts, final Concepts, source-local
  connector candidates, or cross-source connector candidates.
