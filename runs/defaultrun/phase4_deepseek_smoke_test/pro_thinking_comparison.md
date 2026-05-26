# Pro Thinking Smoke Test Comparison

Compared DeepSeek Pro Thinking output against the prior evaluator matrix and the Pro non-thinking run.

| Lesson | Prior Net | Pro Non-Thinking Net | Pro Thinking Net | Thinking vs Prior | Notes |
|---|---:|---:|---:|---:|---|
| L01 | 1 | 1 | 1 | +0 |  |
| L02 | 1 | 1 | 0 | -1 | Thinking harsher on deterministic review dump |
| L03 | 0 | 2 | 0 | +0 | Thinking agrees Net=0 but under-scores traceability because prunes were bad |
| L04 | 2 | 3 | 2 | +0 |  |
| L05 | 3 | 2 | 3 | +0 | Thinking corrected non-thinking false review-fallback claim |
| L06 | 2 | 3 | 3 | +1 | Thinking more optimistic than prior |
| L07 | 2 | 3 | 3 | +1 | Thinking more optimistic than prior |
| L08 | 2 | 2 | 3 | +1 | Thinking more optimistic than prior |
| L09 | 3 | 3 | 3 | +0 |  |
| L10 | 2 | 2 | 2 | +0 | Thinking newly flags Boolean/off-lesson issue |
| L11 | 2 | 3 | 3 | +1 | Thinking more optimistic than prior |
| L12 | 2 | 2 | 3 | +1 | Thinking more optimistic than prior |

Overall mean absolute cell difference, Pro non-thinking vs prior: 0.57
Overall mean absolute cell difference, Pro Thinking vs prior: 0.68

Main agreement: repair_before_phase5; L02 and L03 are severe; L01 and L04 contain off-lesson accepted concepts; L05 and L09 are strong.
Main improvement over non-thinking: no invented L05 review fallback, sharper diagnosis of L02/L03, and better minimum repair scope.
Remaining concern: Pro Thinking still over-praises several lessons with off-topic or operational concepts, especially L08/L12, and it treats bad pruning as low evidence/assignment scores rather than separating traceability from semantic quality.