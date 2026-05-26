# Pro Non-Thinking Smoke Test Comparison

Compared DeepSeek Pro non-thinking output against the prior evaluator matrix.

| Lesson | Prior Net | Pro Net | Net Diff | Mean Abs Diff | Notes |
|---|---:|---:|---:|---:|---|
| L01 | 1 | 1 | +0 | 0.88 | Both flag off-lesson concepts; Pro under-scored traceability |
| L02 | 1 | 1 | +0 | 0.50 |  |
| L03 | 0 | 2 | +2 | 0.75 | Pro caught questionable pruning but scored net much higher |
| L04 | 2 | 3 | +1 | 0.62 |  |
| L05 | 3 | 2 | -1 | 0.88 | Pro falsely reported review fallback; artifact has 0 review candidates |
| L06 | 2 | 3 | +1 | 0.62 | Pro more optimistic |
| L07 | 2 | 3 | +1 | 0.75 | Pro more optimistic |
| L08 | 2 | 2 | +0 | 0.50 |  |
| L09 | 3 | 3 | +0 | 0.12 |  |
| L10 | 2 | 2 | +0 | 0.25 |  |
| L11 | 2 | 3 | +1 | 0.88 | Pro more optimistic |
| L12 | 2 | 2 | +0 | 0.12 |  |

Overall mean absolute cell difference: 0.57

Main agreement: repair_before_phase5; L02 review fallback is serious; L03 pruning is questionable; L01/L04/L08 contain off-lesson acceptances; L09 is strong.
Main disagreement: Pro non-thinking over-praised L06/L07/L11, invented an L05 review fallback, and treated evidence/assignment traceability inconsistently.