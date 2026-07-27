# Empirical findings

What the experiment runs taught us, in plain language, for whoever builds
the next stage. Each finding says what we saw, where the evidence lives
(run ids; the run ledger is the database), and what to do about it.
Period covered: r0003 to r0067, 2026-07-26.

## About prompts

**Enumerate examples and you bias the output.** Telling the model a task
"can be a question, an explanation, etc" pushes everything into those
forms. Define by function ("something a learner could be asked to do")
and let form emerge. The same held in revision: naming "the passage, the
article" as deixis markers would have made the model hunt those words and
miss the rest.

**Stack constraints and you get literalism, not quality.** Generation
v002 added "everything it tests must come from the source, and everything
it needs must be in the task itself" to an already-working prompt. Result
(r0050, r0051 vs r0046, r0047): transfer tasks vanished, paraphrase
framing died, and deixis went up in flash because the prompt itself
mentions "source" three times and the model mirrors vocabulary. The cure
was replacing the constraint with a fact about the situation ("the
learner will answer with no text in front of them", v003/v004). When a
prompt fails, swap a constraint for a fact; do not add another rule.

**Judge prompt changes with counted measures, never impressions.** We
called v002's results "good enough" by eye, then a controlled comparison
showed quality had dropped. The rubric that caught it: deixis rate (tasks
pointing at "the passage"), transfer tasks present or not, paraphrase
framing present or not, factual errors. Cheap to count, hard to argue
with.

**One wording clause can carry a whole behavior.** Removing "keeping what
already works" between revision v002 and v003 did not change verdicts at
all, but let rewrite amplitude swing freely between trials (r0063
fabricated a full code block; r0065 stayed minimal). Anchor size with a
minimality clause if uniform rewrites matter.

## About models (DeepSeek v4, flash and pro)

**Pro thinking is immune to prompt wording on deixis; flash is not.**
Across generation v001 to v004, flash's deixis rate moved 15% → 27% →
14% → 9% with wording; pro sat near 20% regardless. Prompt engineering
has a ceiling per model; measure before iterating further.

**Flash reasons from intent, pro from the printed fact.** The one factual
error in the whole window (r0051): flash claimed 'the' was absent from a
vocabulary because the code's intent was to remove stopwords; the printed
output kept "The" because the check runs before lowercasing. Pro read the
printed fact. That is why pro thinking is the judge wherever the judgment
is interpretation (task-triage, task-revision).

**Freeing a cautious model does not give it judgment.** Revision v003
cured flash's excess of unfixable verdicts, but it then rescued a task
that deserved to die (a why-question whose stored answer contains no
reason; r0066) and renamed a source function. Pro kept killing it in all
six of its runs. Prompts move willingness; they do not move discernment.

**Stub passages produce trivia under every model and every prompt.** The
granular division's heading-plus-code-stub passages yielded memorization
and counting tasks in all eight model-and-prompt combinations tried. When
every combination fails the same way, the input division is the problem,
not the prompt. That retired the granular division for task generation.

## About the pipeline shape

**The answer field is the load-bearing piece of revision.** A task that
points at "the passage" can be rebuilt blind because its answer carries
the referent (sentences, vocabularies, variable names). Rewrites anchored
on the answer were consistent with it in 11 of 12 reconstruction cases;
the one failure (r0061, a permuted vocabulary) is exactly the class the
source-holding triage pass catches. Blind revision and sourced triage
cover each other's failure mode; keep them paired.

**Discard, don't fix — but only for content defects.** Filler passages,
unsupported tasks, unfixable tasks: absence is the cure. Form defects
(deixis in an otherwise good task) are the one category worth rewriting,
because discarding them would cost ~20-30% of a good generator's output.

**Two verdicts from the same model family agree when it matters.** The
final chain (r0052 generation → r0065 revision → r0067 triage) came out
31/31 supported with zero unsure. Watch the self-judgment caveat: pro
judging pro's own output can inflate agreement; a flash cross-check is
cheap when a number looks too clean.

## Provider quirks (native DeepSeek API; historical after the OpenRouter move)

- deepseek-v4-flash defaults to thinking; non-thinking required an
  explicit `{"thinking": {"type": "disabled"}}` (a missing one cost us
  run r0048, 14/14 failures).
- Thinking mode rejected forced tool_choice; the working preset was
  `{"thinking":{"type":"enabled"},"tool_choice":"auto","reasoning_effort":"high"}`
  plus a require-tool guard treating prose as a failed call.
- Prefix caching rewards byte-identical, source-first templates: every
  per-passage and per-task call puts the whole source first and the
  variable part last.

## Provider quirks (OpenRouter, certified 2026-07-26)

The pipeline moved to OpenRouter (key OPEN_ROUTER_API_KEY, base URL is the
client default). A live audit certified tool calls, thinking, effort and
embeddings. What changed against native DeepSeek:

- Model ids gain the vendor prefix: `deepseek/deepseek-v4-flash`,
  `deepseek/deepseek-v4-pro`. Thinking is per-request on the same id.
- The thinking preset can stay the native passthrough
  (`{"thinking":{"type":"enabled"},"tool_choice":"auto","reasoning_effort":"high"}`,
  accepted verbatim) or the documented unified form
  (`{"reasoning":{"effort":"high"},"tool_choice":"auto"}`). Flash defaults
  to non-thinking here, the opposite of the native API.
- Forced tool_choice under thinking works on OpenRouter; the native
  rejection is gone. The require-tool guard stays anyway.
- Usage fields moved: cache hits are
  `prompt_tokens_details.cached_tokens` (no explicit miss counter), and a
  real `cost` in USD comes back per call. aggregate_usage flattens the
  nested details.
- Requests are routed across upstream providers, and prefix cache is per
  provider: a run whose calls bounce between providers loses cache hits.
  If cache economics matter for a big run, pin with the `provider`
  routing field.
- Embedding ids are not discoverable via GET /models; they must be known
  a priori. Certified working: `qwen/qwen3-embedding-8b` (4096 dims) and
  `openai/text-embedding-3-small` (1536 dims).
