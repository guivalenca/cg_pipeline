---
id: "24"
title: "Decision Analysis 3: Decision Trees"
source_url: "https://www.youtube.com/watch?v=ydvnVw80I_8"
fetch_url: "https://www.youtube.com/watch?v=ydvnVw80I_8"
resolved_url: "https://www.youtube.com/watch?v=ydvnVw80I_8"
firecrawl_title: null
description: null
fetched_at: "2026-05-26T17:21:03.937739Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "4d8ccb09bd52c8412f1d3644b47e2088577a73f9614b8e80db7bdd951bb3f214"
cache_keys:
  - "4d8ccb09bd52c8412f1d3644b47e2088577a73f9614b8e80db7bdd951bb3f214"
gemini_model: "gemini-2.5-flash-lite"
gemini_media_resolution: "low"
gemini_fps: 0.5
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 185.0
transcript_source: "manual_captions"
transcript_sha256: "d6a2d63c693506ed02ec480192b92474e2a72d0a5efefb461881ec6356321e8b"
word_count: 771
char_count: 4466
content_sha256: "4104436255b0e51d65e3d173aab501bb7a2e259a85b440f07d2acfea4e416d38"
image_count: 7
link_count: 0
total_token_count: 14975
estimated_input_tokens: 12025
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## 00:00 Introduction to Decision Trees

**Spoken content:**
- [00:00] Welcome to this Decision Analysis tutorial for constructing decision trees.

**On-screen content:**
![Title slide with text "Decision Trees Part 1 By Joshua Emmanuel"](video-frame://24@00:00)

## 00:05 Objectives

**Spoken content:**
- [00:05] We will be constructing a basic decision tree.
- [00:08] We will also be making decisions using the expected value approach.

**On-screen content:**
![Objectives list: Construct Decision Tree, Make Decision using Expected Value](video-frame://24@00:05)

## 00:13 Payoff Table

**Spoken content:**
- [00:13] We will be constructing a decision tree using this payoff table,
- [00:18] where payoffs are profits and the probabilities of the states of nature
- [00:23] are .4 and .6 respectively.

**On-screen content:**
![Payoff table with Alternatives: Stocks, Mutual Funds, Bonds and States of Nature: Growing, Declining. Probabilities: 0.4, 0.6. Payoffs for Stocks: 70, -13. Payoffs for Mutual Funds: 53, -5. Payoffs for Bonds: 20, 20.](video-frame://24@00:13)

## 00:28 Decision Tree Nodes

**Spoken content:**
- [00:28] Decision trees use two types of nodes:
- [00:32] A square or rectangle node called DECISION NODE
- [00:37] from which decision alternative branches will originate,
- [00:42] and a circle node called CHANCE NODE
- [00:45] from which states of nature or outcome branches will emanate.
- [00:51] The CHANCE NODE is also referred to as an OUTCOME NODE or EVENT NODE
- [00:57] Now let's construct a decision tree for this PAYOFF table.

**On-screen content:**
![Diagram showing a square labeled "Decision Node" and a circle labeled "Chance Node" with arrows indicating branches originating from them.](video-frame://24@00:28)

## 00:57 Constructing the Decision Tree

**Spoken content:**
- [01:01] We first draw a decision node
- [01:05] with branches coming out of the decision node representing decision alternatives.
- [01:10] Next we draw the chance node or outcome node
- [01:14] with respective states of nature or outcomes.
- [01:19] As it can be seen here for stocks.
- [01:22] The payoffs are placed at the end of the branches as you can see (70 and -13 for Stocks).
- [01:30] We do the same for Mutual Funds and for Bonds.
- [01:34] Notice that the payoff is 20 for Bonds
- [01:38] irrespective of the state of nature.
- [01:40] Therefore, we really don’t need to repeat 20,
- [01:44] we simply need to draw a single branch
- [01:47] from BONDS with a payoff of 20.

**On-screen content:**
![Decision tree diagram in progress. A decision node (square) branches into "Stocks" and "Bonds". The "Stocks" branch leads to a chance node (circle) with sub-branches "Growing (0.4)" and "Declining (0.6)", with payoffs 70 and -13 respectively. The "Bonds" branch leads to a single payoff of 20. A "Mutual Funds" branch is also shown, leading to a chance node with similar structure and payoffs 53 and -5.](video-frame://24@00:57)

## 01:51 Solving the Decision Tree

**Spoken content:**
- [01:51] Now let's solve the decision tree.
- [01:54] Solving the decision tree is also known as
- [01:57] folding back the decision tree.
- [02:00] In essence, we are going to calculate the expected
- [02:04] values and then choose the best.
- [02:06] For Stocks, the expected value is calculated as
- [02:10] .4 times 70 + .6 times -13 which is 20.2.
- [02:17] So we just usually write the 20.2 on the chance node for stocks.
- [02:23] We do the same for mutual funds. The expected
- [02:27] value is. 4 times 53 + .6 times -5 which is 18.2.
- [02:35] We also write that on the chance node for mutual funds.
- [02:38] For Bonds, no calculation is required.
- [02:43] We can only expect a payoff of 20 (for Bonds).

**On-screen content:**
![Decision tree diagram with expected values calculated and placed on chance nodes. Expected value for Stocks is 20.2. Expected value for Mutual Funds is 18.2. Payoff for Bonds is 20.](video-frame://24@01:51)

## 02:46 Making the Decision

**Spoken content:**
- [02:46] Now comparing the three values: 20.2, 18.2, and 20,
- [02:52] the best expected value is 20.2.
- [02:56] We usually just place that value close to the decision node.
- [03:00] Therefore, the decision is to invest in Stocks.
- [03:04] Thanks for watching!

**On-screen content:**
![Completed decision tree with the highest expected value (20.2) highlighted, indicating the optimal decision to "Invest in Stocks".](video-frame://24@02:46)
