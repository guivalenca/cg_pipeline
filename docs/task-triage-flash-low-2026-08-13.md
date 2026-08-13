# Task-triage Flash-low promotion — 2026-08-13

## Decision

Use `deepseek/deepseek-v4-flash` with thinking enabled and
`reasoning_effort: low` as the default `task-triage` recipe. The prompt and
tool remain `task-triage/v001` and `tool-v001`.

## Experiment

Three runs judged the same 156 post-revision tasks from generation `r0025`,
granularity `r0027`, and revision `r0029`. Their prompt SHA, tool definition,
effective task manifest, worker count, maximum token count, and provider
routing policy were identical. Only the model preset and requested reasoning
effort varied.

| run | model preset | verdicts | cost | wall time |
| - | - | - | -: | -: |
| `r0032` | Pro, thinking high | 153 supported / 3 unsupported | $2.62576490 | 96.5 s |
| `r0039` | Flash, thinking low | 154 supported / 2 unsupported | $0.27110356 | 85.0 s |
| `r0040` | Flash, thinking high | 154 supported / 2 unsupported | $0.25415516 | 69.1 s |

Flash-low and Flash-high agreed on all 156 verdicts. Each agreed with Pro-high
on 155/156 verdicts (99.36%). Flash-low cost 89.68% less than Pro-high, or
about 9.69 times less. The lower observed cost of Flash-high is attributed to
its higher prompt-cache hit rate in this pair, not to reasoning effort:
Flash-low cached 90.94% of prompt tokens and Flash-high cached 98.29%.

## Reviewed divergence

The sole divergence was task `r0027-0009:t01`. It asks what it means for a
corporate data environment to be large and expects “a significant volume of
data.” The source passage describes diverse data sources, scalability,
performance, and fast processing rather than defining “large” solely as data
volume. Pro-high returned `unsupported`; both Flash runs returned `supported`.
Manual review favors the Pro verdict, so the Flash result contains one known
false positive. That quality difference is accepted for the approximately
90% task-triage cost reduction.

Two other disputed-looking tasks were rejected by all three runs: expanding
“DAG” where the source never expands the acronym, and naming two manual
Airflow trigger methods where the source and expected answer provide only one.

## Operational consequence

`r0039` is the current witness for the promoted recipe. Pro-high `r0032` and
Flash-high `r0040` remain immutable historical runs. The promoted Flash run
retains one additional task, so the source's exact downstream manifest changed
and `task-substance` reopened as the next pending stage. No downstream model
call was part of this experiment or promotion.
