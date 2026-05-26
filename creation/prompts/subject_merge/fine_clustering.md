# Subject Merge Fine Clustering

## Quick Start

Inside one topic area, create tight candidate clusters that are worth a later same-concept decision. Use only the provided candidate cards.

## Identity Filter

Cluster candidates only when they might be the same teachable idea at the same level, testable with the same question.

Do not cluster just because candidates share a keyword. Keep candidates separate when one adds implementation, math, limitation, application, deeper mechanism, tool-specific behavior, or a broader/narrower student action.

Doubt means singleton. Under-clustering is safer than sending unrelated candidates to merge evaluation.

## Output

Return one JSON object only:

```json
{
  "clusters": [
    {
      "id": "cluster_001",
      "label": "Short candidate cluster",
      "rationale": "Why these candidates may share concept identity.",
      "candidate_ids": ["candidate-id"]
    }
  ]
}
```

## Self-Check

- Every input candidate ID appears exactly once.
- Each non-singleton cluster has a plausible same-concept reason.
- Implementation, limitation, application, math, and deeper-revisit candidates were not grouped with definitions just because labels overlap.
- Mixed-language same-level candidates were clustered when their teachable idea matches.
- No web search or external knowledge was used.
