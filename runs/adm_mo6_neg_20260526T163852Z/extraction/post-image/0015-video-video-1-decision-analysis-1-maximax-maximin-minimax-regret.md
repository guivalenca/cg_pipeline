---
id: "15"
title: "Video 1: Decision Analysis 1 - Maximax, Maximin, Minimax Regret"
source_url: "https://www.youtube.com/watch?v=NQ-mYn9fPag"
fetch_url: "https://www.youtube.com/watch?v=NQ-mYn9fPag"
resolved_url: "https://www.youtube.com/watch?v=NQ-mYn9fPag"
firecrawl_title: null
description: null
fetched_at: "2026-05-26T17:20:45.639643Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "85d067925c3b7a7aa52c57409e28b6387e3d4b3d619b0bc3a8c7f8fc96d704e2"
cache_keys:
  - "85d067925c3b7a7aa52c57409e28b6387e3d4b3d619b0bc3a8c7f8fc96d704e2"
gemini_model: "gemini-2.5-flash-lite"
gemini_media_resolution: "low"
gemini_fps: 0.5
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 283.0
transcript_source: "manual_captions"
transcript_sha256: "45fc1eaa7240a25342633dd32c1ff2ebea58b04077f2c042715a1c57bf811c7a"
word_count: 881
char_count: 5044
content_sha256: "7288b1b4a0913deb30f3ec5ebd9a615bd605b1c12045fb28489b06427c1177e8"
image_count: 6
link_count: 0
total_token_count: 22035
estimated_input_tokens: 18395
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Decision Making Without Probabilities

**Spoken content:**
- [00:00] Welcome! In this brief video, we will be discussing decision making without
- [00:05] probabilities.
- [00:06] In this first part, we will consider Maximax
- [00:10] or the optimistic approach, the maximin
- [00:13] also known as conservative or pessimistic approach, and
- [00:17] the minimax regret approach to decision-making.

**On-screen content:**
![Title slide: Decision Making Without Probabilities Part 1 By Joshua Emmanuel](video-frame://15@00:00)

## [00:20] Payoff Table

**Spoken content:**
- [00:20] The table seen here
- [00:25] is referred to as a payoff table or decision table.
- [00:29] the alternate is on the left here
- [00:32] in the rows are referred to as
- [00:35] Decision Alternatives. They are the options available for the
- [00:39] decision maker to choose from
- [00:41] We will assume that the decision maker can
- [00:44] only choose one of these alternatives - invest in bonds
- [00:49] stocks, or mutual funds.
- [00:52] In the columns we have the economic conditions.
- [00:56] Since the decision maker does not have control over these,
- [01:00] we refer to them as states of nature
- [01:03] or outcomes. The values in the table
- [01:07] are called payoffs. They could be profit,
- [01:11] cost, distance, time, and so on.
- [01:15] In this example we treat them as profits.

**On-screen content:**
![Payoff Table with Alternatives (Bonds, Mutual Funds) and Economy (Growing, Stable, Declining) and Payoffs](video-frame://15@00:22)

## [01:18] Maximax Approach (Optimistic)

**Spoken content:**
- [01:18] The Maximax or Optimistic approach
- [01:23] Using this optimistic approach, we choose the alternative
- [01:27] with the best possible payoff. Looking at Bonds
- [01:32] the best payoff is 45. The best is 70 for stocks,
- [01:36] and the best is 53 for mutual funds.
- [01:40] The overall best is 70. Therefore the decision is to invest in stocks.

**On-screen content:**
![Payoff Table with Maximax (Best of Best) column highlighting 45, 70, 53, and the maximum of 70 for Stocks.](video-frame://15@01:18)

## [01:51] Maximin Approach (Conservative/Pessimistic)

**Spoken content:**
- [01:51] The maximin or conservative approach. Using this pessimistic approach
- [01:58] we choose the alternative with the best of the worst
- [02:02] payoffs. We first choose the the worst payoff
- [02:05] in each alternative and then choose the best of the worst.
- [02:09] Looking at Bonds, the worst payoff is 5,
- [02:13] the worst is -13 for stocks
- [02:16] and the worst is -5 for mutual funds.
- [02:20] The best of these is 5.
- [02:23] Therefore the pessimistic or conservative approach
- [02:28] is to invest in bonds. The minimax regret approach.

**On-screen content:**
![Payoff Table with Maximin (Best of Worst) column highlighting worst payoffs 5, -13, -5, and the maximum of 5 for Bonds.](video-frame://15@01:51)

## [02:32] Minimax Regret Approach

**Spoken content:**
- [02:35] Using this approach which choose the alternative
- [02:38] with the minimum of all maximum regrets
- [02:42] across all alternatives. Regret,
- [02:47] also known as opportunity loss is the difference between the best payoff
- [02:52] in a particular state of nature and the actual
- [02:55] payoff received. For example, if the economy is growing,
- [03:00] the best payoff is 70. If we happened to have invested in bonds,
- [03:05] then the regret will be 70 - 40
- [03:09] which is 30. If we invested in stocks
- [03:13] then there is no regret. If we invested in mutual funds,
- [03:18] then the regrets is 70 minus 53 which is 17.
- [03:22] Again, if the economy stable, the best payoff is 45,
- [03:27] so if we invested in bonds, there is no regret, the regret
- [03:32] is 45 - 30 if we invested
- [03:35] in stocks, if we invested in mutual funds
- [03:39] there is also no regret. For declining economy
- [03:43] the best payoff is 5. If we invested in bonds,
- [03:46] there is no regret; if we invested
- [03:50] in stocks the regret is five minus -13 which is
- [03:55] 18; if we invested in mutual funds, the regret is 5 minus -5
- [04:00] which is 10.

**On-screen content:**
![Payoff Table with calculations for regret in each state of nature for each alternative.](video-frame://15@02:32)

## [04:05] Regret Table and Decision

**Spoken content:**
- [04:05] Here is the regret table.
- [04:07] Since the decision is to be made
- [04:10] based on minimax regret, we first determine
- [04:14] the maximum regret for each alternative and then choose the minimum.
- [04:18] For bonds, the maximum
- [04:23] regret is 30. For stocks
- [04:27] it is 18, and for mutual funds,
- [04:30] it is 17. The minimum of these maximum regrets is 17.
- [04:35] The decision is to invest in mutual funds.
- [04:38] See you in part 2.
- [04:41] Thanks for watching!

**On-screen content:**
![Regret Table with Maximum Regret column highlighting 30, 18, 17, and the minimum of 17 for Mutual Funds.](video-frame://15@04:05)
