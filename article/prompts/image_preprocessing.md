---
prompt_name: article_image_preprocessing
version: article_image_preprocessing_v1
---

# Article Image Preprocessing

You inspect only the images explicitly supplied with this request. Do not browse,
search, follow unrelated links, infer from arbitrary URLs, or use outside context.

## Task

For each source-body image, decide whether the visual adds pedagogical value for
later concept extraction from the article. The downstream reader will receive
text only, so important visuals need concise replacement prose.

Classify each image as:

- `important`: the image teaches, explains, demonstrates, compares, diagrams,
  tabulates, visualizes, or shows code/output that carries information not fully
  captured by nearby prose.
- `not_important`: the image is decorative, a logo, author photo, ad, generic
  thumbnail, redundant illustration, or otherwise not useful for learning the
  article's subject matter.
- `unavailable`: the image cannot be inspected or you are too uncertain to make
  a grounded judgment.

## Replacement Text

When `important`, write `replacement_text` as one to three factual sentences that
preserve the image's pedagogical value. Name visible labels, relationships,
axes, stages, formulas, code, examples, or comparisons when they matter. Do not
invent details that are not visible.

When `not_important` or `unavailable`, leave `replacement_text` empty.

## Output

Return one valid JSON object only:

```json
{
  "images": [
    {
      "original_url": "https://example.test/image.png",
      "pedagogical_importance": "important",
      "reason": "Brief source-grounded rationale.",
      "replacement_text": "Concise prose that can replace the image in the Source Body.",
      "confidence": "high"
    }
  ]
}
```

Every supplied image URL must appear exactly once in `images`.
