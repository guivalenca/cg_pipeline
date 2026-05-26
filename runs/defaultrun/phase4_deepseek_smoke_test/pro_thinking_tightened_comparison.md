# Tightened Pro Thinking Smoke Test Comparison

| Lesson | Prior Net | Old Pro Thinking Net | Tightened Net | Change vs Old | Notes |
|---|---:|---:|---:|---:|---|
| L01 | 1 | 1 | 1 | +0 |  |
| L02 | 1 | 0 | 1 | +1 | Back to prior Net=1; still flags review_needed |
| L03 | 0 | 0 | 1 | +1 | Still too generous: questionable pruning should likely keep Net at 0 |
| L04 | 2 | 2 | 2 | +0 |  |
| L05 | 3 | 3 | 3 | +0 |  |
| L06 | 2 | 3 | 3 | +0 | Still more optimistic than prior |
| L07 | 2 | 3 | 3 | +0 | Still more optimistic than prior |
| L08 | 2 | 3 | 2 | -1 | Tightened prompt corrected over-optimistic 3 to 2 |
| L09 | 3 | 3 | 3 | +0 |  |
| L10 | 2 | 2 | 2 | +0 |  |
| L11 | 2 | 3 | 2 | -1 | Tightened prompt corrected over-optimistic 3 to 2 |
| L12 | 2 | 3 | 3 | +0 | Still optimistic despite mixed scope/tooling content |

Mean absolute cell difference, old Pro Thinking vs prior: 0.68
Mean absolute cell difference, tightened Pro Thinking vs prior: 0.47

Main improvement: the tightened prompt reduced inflated 3s on L08 and L11, preserved L05 as strong, and expanded off-lesson findings to L10/L11.
Remaining limitation: it still treats some traceable but semantically bad lessons as acceptable, especially L03 and L12.