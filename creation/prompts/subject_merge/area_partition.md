# Subject Merge Area Partition

## Quick Start

Create broad topic areas for one subject so later calls compare nearby candidates instead of the whole inventory. Use only the provided candidate cards.

## Decision Rules

- Partition by teachable neighborhood, not by exact duplicate identity.
- Prefer small, coherent neighborhoods over one large catch-all area.
- A full subject should usually have 15-25 areas when enough candidates exist.
- Put every input candidate ID in exactly one area.
- Keep mixed-language versions of the same topic in the same area.
- Do not decide final merges here. This step only creates neighborhoods.

## Output

Return one JSON object only:

```json
{
  "clusters": [
    {
      "id": "area_001",
      "label": "Short topic area",
      "rationale": "Why these candidates belong in the same broad neighborhood.",
      "candidate_ids": ["candidate-id"]
    }
  ]
}
```

## Self-Check

- Every input candidate ID appears exactly once.
- No area is a miscellaneous dump unless the input truly has isolated topics.
- Area labels describe topics, not final accepted concepts.
- No web search or external knowledge was used.
