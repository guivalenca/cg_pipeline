---
id: "16"
title: "Video 2: Decision Analysis 1.1 (Costs) - Optimistic, Conservative, Minimax Regre"
source_url: "https://www.youtube.com/watch?v=ajkXzvVegBk"
fetch_url: "https://www.youtube.com/watch?v=ajkXzvVegBk"
resolved_url: "https://www.youtube.com/watch?v=ajkXzvVegBk"
firecrawl_title: null
description: null
fetched_at: "2026-05-26T16:57:40.147603Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "6da4c48731ef14574b7f6121e6c222799d345e436d18f49e305fca7f538fc208"
cache_keys:
  - "6da4c48731ef14574b7f6121e6c222799d345e436d18f49e305fca7f538fc208"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 300.0
transcript_source: "manual_captions"
transcript_sha256: "411fc40b2b07bbb9c14d71308dc48ef63c300adb4ddd85a575dc033d6982d07c"
word_count: 1103
char_count: 6407
content_sha256: "5a5d28d229ca0fb48707c14b7fb93c5b27a88930d00ac0c4d3a5d7ce1c80fc63"
image_count: 7
link_count: 0
total_token_count: 15365
estimated_input_tokens: 16134
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## 0:00 Decision Making Without Probabilities (Cost Example)

**Spoken content:**
- [00:00] Welcome! In this brief video, we will be discussing
- [00:03] decision making without probabilities where cost is involved.
- [00:08] We will cover the Optimistic or Maximax approach, the Conservative or Maximin approach,
- [00:16] and also the Minimax Regret approach.

**On-screen content:**
![slide: Decision Making Without Probabilities Cost Example](video-frame://16@0:00)

## 0:19 Payoff Table and Objectives

**Spoken content:**
- [00:19] We will be using this payoff table where Payoffs are costs.
- [00:24] The approach we will use in this tutorial is applicable to all cases where smaller payoff
- [00:30] values are preferred over larger ones. The objective could be to minimize cost, minimize
- [00:37] customer waiting time, minimize risk, minimize distance, and so on.

**On-screen content:**
![table: Payoff Table with Alternatives d1, d2, d3 and States of Nature S1, S2, S3. Values are d1: 12, -5, 14; d2: 15, 11, -9; d3: 5, 18, -5.](video-frame://16@0:20)
* Decision making approaches:
    * Optimistic (Maximax)
    * Conservative (Maximin)
    * Minimax Regret
* Payoff Table
    * Costs
    * Minimize Cost
    * Minimize Customer Waiting Time
    * Minimize Risk
    * Minimize Distance

## 0:43 Optimistic (Maximax) Approach

**Spoken content:**
- [00:43] The Optimistic or Maximax Approach Using this approach we choose the alternative
- [00:49] with the best of the best payoffs. Note that the payoffs are costs, therefore the smaller
- [00:55] the better. For d1 , the best payoff is -5
- [01:00] For d2 , the best is -9 and for d3, the best is -5.
- [01:08] The overall best is -9. Therefore the optimistic decision is to choose d2.

**On-screen content:**
![table: Payoff Table with Best column showing -5 for d1, -9 for d2, -5 for d3. The overall Best is -9.](video-frame://16@0:43)
* Optimistic (Maximax) Approach
    * Best of Bests
    * Costs
    * Decision: Choose d2

## 1:16 Conservative (Maximin) Approach

**Spoken content:**
- [01:17] The Conservative or Maximin Approach Using this approach, we choose the alternative
- [01:22] that has best of the worst payoffs. We first choose the worst payoff in each alternative,
- [01:30] and then choose the best of them. Since these are costs, for d1, the worst is
- [01:37] 14 for d2 , the worst is 15
- [01:40] and for d3, the worst is 18. The best of these worst payoffs is 14
- [01:47] Therefore the conservative decision is to choose d1.

**On-screen content:**
![table: Payoff Table with Worst column showing 14 for d1, 15 for d2, 18 for d3. The Best of these Worsts is 14.](video-frame://16@1:16)
* Conservative (Maximin) Approach
    * Best of Worsts
    * Costs
    * Decision: Choose d1

## 1:52 Minimax Regret Approach

**Spoken content:**
- [01:53] The Minimax Regret Approach Using this approach, we choose the alternative
- [01:58] with the minimum of all the maximum regrets across all alternatives.
- [02:04] Regret is the difference between the best payoff and the actual payoff received in a
- [02:09] particular state of nature.
- [02:12] Therefore for s1 the best payoff is 5 since we are dealing with costs.
- [02:17] That is, if you knew s1 was going to occur, you would have chosen d3.
- [02:23] So if s1 occurs and you already chose d1, your regret will be 12 – 5 = 7.
- [02:31] That is, if you could pay $5 for an item and you paid $12 instead, your regret will be $7
- [02:41] Note that if these are profits, we will subtract all payoffs from the best, which in that case
- [02:47] would be the largest value. But because they are costs, we will subtract the smallest from
- [02:53] other payoffs. Whatever you do, make sure your regret values are not negative.
- [02:59] So going back to s1 If instead you chose d2, you’re paying $15
- [03:05] when you could pay $5 and your regret will be 15 – 5 which equals 10.
- [03:13] And if you chose d3, your regret is 5 – 5 which equals 0. That is, there is no regret.

**On-screen content:**
![table: Payoff Table with calculations for regret for S1. Regret = Payoff Received - Best Payoff.](video-frame://16@1:52)
* Minimax Regret Approach
    * Minimum of Maximum Regrets
    * For costs, Regret = Payoff Received - Best Payoff
    * S1 calculations:
        * d1: 12 - 5 = 7
        * d2: 15 - 5 = 10
        * d3: 5 - 5 = 0

## 3:21 Minimax Regret Calculations for S2 and S3

**Spoken content:**
- [03:21] For s2 your best payoff is -5.
- [03:25] So if you chose d1, your regret will be -5 minus -5 which equals 0 → no regret.
- [03:34] Note that the double negative becomes positive. And you if you chose d2, your regret is 11
- [03:40] minus -5 which equals 16. If you chose d3, your regret will be 18 minus
- [03:47] -5 which equals 23.
- [03:51] If s3 occurs, the best payoff is -9.
- [03:55] So if you chose d1, your regret will be 14 minus -9 which gives 23.
- [04:01] And you if you chose d2, your regret is -9 minus -9 which equals 0.
- [04:07] If you chose d3, your regret will be -5 minus -9 which equals 4

**On-screen content:**
![table: Payoff Table with calculations for regret for S2 and S3.](video-frame://16@3:21)
* S2 calculations:
    * d1: -5 - (-5) = 0
    * d2: 11 - (-5) = 16
    * d3: 18 - (-5) = 23
* S3 calculations:
    * d1: 14 - (-9) = 23
    * d2: -9 - (-9) = 0
    * d3: -5 - (-9) = 4

## 4:14 Regret Table and Final Decision

**Spoken content:**
- [04:15] Here is the Regret Table. Note that after regrets are calculated, the
- [04:20] approach for determining the best alternative is exactly the same for profit and cost problems.
- [04:28] Since the decision is to be made based on minimax regret, we first determine the maximum
- [04:34] regret for each alternative, and then choose the minimum.
- [04:37] For d1, the maximum regret is 23, for d2, the maximum is 16,
- [04:44] for d3, the maximum regret is 23. The minimum of these maximum regrets is 16.
- [04:52] Therefore the minimax regret decision is to choose d2.
- [04:57] Please leave your comments or questions below.
- [05:00] Thanks for watching.

**On-screen content:**
![table: Regret Table with Maximum column showing 23 for d1, 16 for d2, 23 for d3. The Minimum of these Maximums is 16.](video-frame://16@4:14)
* Regret Table
    * Max Regret for d1: 23
    * Max Regret for d2: 16
    * Max Regret for d3: 23
    * Min of Maximums: 16
    * Decision: Choose d2
