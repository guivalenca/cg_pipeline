---
id: "46"
title: "Video 1: The Essence of Real Option"
source_url: "https://www.youtube.com/watch?v=T1JKwzJ-KMc"
fetch_url: "https://www.youtube.com/watch?v=T1JKwzJ-KMc"
resolved_url: "https://www.youtube.com/watch?v=T1JKwzJ-KMc"
firecrawl_title: null
description: null
fetched_at: "2026-05-26T17:05:46.927743Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "c869e78f1b0690ad5e6241ccc2c38fd282fbd02f6557bcf2788a3c8936b44afb"
cache_keys:
  - "c869e78f1b0690ad5e6241ccc2c38fd282fbd02f6557bcf2788a3c8936b44afb"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 948.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "05da50adbdab232a7eb39e61f1dcc787e55b23a5786eb4b5ec8581a6eec93a9b"
word_count: 5143
char_count: 29388
content_sha256: "b074a90a32d534cfc94a4f12f61350662bc21f5ed3f779be0672f58e7e727515"
image_count: 20
link_count: 0
total_token_count: 64035
estimated_input_tokens: 50983
warnings:
  - "title_mismatch"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Real Options in Valuation

**Spoken content:**
- [00:00] There is very little in valuation that I think of as new, different or sophisticated.
- [00:15] Much of what we do has always been done.
- [00:18] This session is an exception.
- [00:21] I want to talk about the application of option pricing models in valuation.
- [00:26] Not to value options, that's been around a while, but to value real businesses.
- [00:30] What kind of businesses?
- [00:31] It could be an oil company with undeveloped reserves.
- [00:34] A young biotechnology company.
- [00:36] Equity in a deeply troubled company.
- [00:38] A company losing money with a lot of debt.
- [00:40] This session I hope to flesh out why I think of investments in these businesses as options
- [00:46] and what the implications are for investors.

**On-screen content:**
![NYU Stern logo](video-frame://46@00:00)

## [00:49] Real Options as a Valuation Approach

**Spoken content:**
- [00:49] So now that we've talked about intrinsic and relative valuation,
- [00:52] it's time to turn our attention to the third and final approach to doing valuation.
- [00:57] Real options.
- [00:58] As I noted at the very start of the class, this is perhaps the only area of valuation
- [01:03] where we can draw new and different things.
- [01:06] Quasi-sophisticated models to do valuation.
- [01:09] But in this session I'd like to cut to the core and talk about the intuition that drives real option valuation.
## [01:15] Limitations of Discounted Cash Flow (DCF) Valuation

**Spoken content:**
- [01:15] When you do a discounted cash flow valuation, you take the expected cash flows and you discount them back
- [01:20] and you come up with a value for the asset, right?
- [01:23] Well, for most assets, that is an appropriate measure of value.
- [01:26] But you could argue that in some cases you're going to underestimate the value of an asset,
- [01:31] especially when there are the following options embedded in the asset.
- [01:35] The first is the option to delay.
- [01:38] An investment that looks bad today might become good tomorrow
- [01:41] and having the proprietary rights to the investment can still be valuable.
- [01:45] The second is you have the option to expand.
- [01:48] You can have an investment that does not look good today in terms of cash flows,
- [01:53] but it might give you a chance to enter a new market or create a new product that is incredibly valuable.
- [01:59] That is the option to expand.
- [02:01] And the third is the option to abandon.
- [02:03] In some investments you might get the right or the option to walk away from that investment if things don't go well.
- [02:10] That is the option to abandon.
- [02:12] Generically speaking, we're saying that if you have an asset with these options embedded in them,
- [02:17] traditional discounted cash flow valuation is going to understate the value of these assets.

**On-screen content:**
![slide: Underlying Theme: Searching for an Elusive Premium](video-frame://46@01:36)
**Underlying Theme: Searching for an Elusive Premium**
*   Traditional discounted cash flow models underestimate the value of investments, where there are options embedded in the investments to:
    *   Delay or defer making the investment (**delay**)
    *   Adjust or alter production as price changes (**flexibility**)
    *   Expand into new markets or products at later stages in the process, based upon observing favorable outcomes at the early stages (**expansion**)
    *   Stop production or abandon investments if the outcomes are unfavorable at early stages (**abandonment**)

## [02:22] Real Options as an Augmentation to DCF

**Spoken content:**
- [02:22] In fact, when you use option pricing in valuing businesses, you're arguing for attaching a premium to traditional discounted cash flow valuations.
- [02:31] So it's good to be clear, option pricing valuation is not an alternative to discounted cash flow valuation, it's an augmentation.
- [02:39] You first have to do a discounted cash flow valuation before you embark on option pricing.

**On-screen content:**
![slide: Underlying Theme: Searching for an Elusive Premium with text "Put another way, real option advocates believe that you should be paying a premium on discounted cash flow value estimates."](video-frame://46@02:22)
**Underlying Theme: Searching for an Elusive Premium**
*   Put another way, real option advocates believe that you should be paying a premium on discounted cash flow value estimates.

## [02:45] Illustrating Option Value with a Simple Investment

**Spoken content:**
- [02:45] To give you an idea of where the value of an option comes from, let me give you a very simple illustration.
- [02:51] Let's assume you have an investment where there's a 50% chance you could make 100 million and a 50% chance you could lose 120 million.
- [03:00] The expected value of this investment is negative, right?
- [03:03] You would not take this investment.

**On-screen content:**
![diagram: Decision tree for a bad investment with outcomes +100 and -120](video-frame://46@02:58)
**A bad investment...**
Today
Success 1/2 -> +100
Failure 1/2 -> -120

## [03:05] Transforming a Bad Investment into a Good One

**Spoken content:**
- [03:05] Now let's say I took the same investment and broke it down into two steps.
- [03:09] In the initial step, you take it in a smaller increment.
- [03:12] So in that first step, you get one of two outcomes.
- [03:15] Either the investment comes back as a good investment, in which case you make plus 20 million.
- [03:19] Or it comes back as a bad investment, in which case you lose 20 million.
- [03:22] If you lose the 20 million, you stop the investment right away.
- [03:27] But if you make the 20 million, you continue.
- [03:29] And if you win, you make another 80 million, giving you a total upside of 100 million.
- [03:34] And if you lose, you lose another 100 million, giving you a total downside of 120 million.
- [03:40] If you look at the probabilities, this investment is actually equivalent to the first investment.
- [03:45] There's a 50% chance that you'll make 100 million.
- [03:49] And there's a 50% chance, cumulatively, that you lose 120 million.

**On-screen content:**
![diagram: Decision tree for a two-step investment with outcomes +80, -100, and stop option](video-frame://46@03:13)
**Becomes a good one...**
Now
+20 (1/3) -> +80 (2/3)
           -> -100 (1/3)
-20 (2/3) -> STOP

## [03:53] The Essence of Real Options: Learning and Adaptive Behavior

**Spoken content:**
- [03:53] But here's the magic of options.
- [03:55] If you take the expected value of this investment, you're actually going to end up with a positive expected value.
- [04:01] A bad investment became a good investment when you took it in two steps.
- [04:06] Now step back and think about why the second investment was valuable and the first investment was not.
- [04:12] The first aspect that made the second investment more valuable is you got that first try.
- [04:17] You were able to observe what happened in that first try, learn from it, and adapt your behavior.
- [04:23] In fact, those are the two key words that drive the value of real options.
- [04:28] It's learning and adaptive behavior.
## [04:31] Real-World Example: Valuing an Oil Company

**Spoken content:**
- [04:31] Let me stop being abstract and give you a real-world example.
- [04:34] Let's suppose you have to value an oil company.
- [04:37] In a traditional discounted cash flow model, here's what you do.
- [04:41] You take the expected number of barrels of oil that will be produced each year.
- [04:45] You multiply by an expected oil price.
- [04:47] You come up with an expected cash flow.
- [04:49] And you discount back at a risk-adjusted rate.
- [04:51] What are you missing when you do that?
- [04:53] If you actually ran an oil company, you would not produce the same number of barrels of oil every year.
- [04:59] And here's why.
- [05:00] You get to observe the oil price first, right?
- [05:02] If oil prices are high, you might produce a lot of oil.
- [05:05] If oil prices are low, you might cut back on production.
- [05:08] You have the option to adjust production.
- [05:11] There's learning from looking at the oil price and adaptive behavior because it changed the production that you have based on that price.
- [05:18] That's what you're looking for in real options.
- [05:21] Is there a capacity to learn?
- [05:23] And can I change my behavior to make a business or asset more valuable?
## [05:28] Three Basic Questions for Applying Option Pricing

**Spoken content:**
- [05:28] So here are the three basic questions that I'd like to answer when I think about applying option pricing to value businesses.
- [05:36] First, when is there an option in a decision?
- [05:39] When should I even be talking about option pricing?
- [05:42] So let's start with that question.
- [05:43] Second question, when does that option have significant economic value?
- [05:48] And this is where you're going to see a drop-off in the number of options that you can actually value.
- [05:53] Most options that you see out there have either no value or so little value that it's not worth doing this.
- [05:59] So when does that option have significant economic value?
- [06:02] And the third and final question is, when can I use an option pricing model?
- [06:06] Those models that have been developed over the last 40 years to value that option.

**On-screen content:**
![slide: Three Basic Questions](video-frame://46@05:36)
**Three Basic Questions**
*   When is there a real option embedded in a decision or an asset?
*   When does that real option have significant economic value?
*   Can that value be estimated using an option pricing model?

## [06:10] Question 1: Identifying an Embedded Option

**Spoken content:**
- [06:10] So let's start with the first question.
- [06:12] When is there an option embedded in an action?
- [06:14] When should I be using option pricing?
- [06:16] There are three specific characteristics that I look for to identify something as an option.
- [06:22] First, options are derivative securities.
- [06:25] They derive their value from something else.
- [06:27] So there's got to be an underlying asset.
- [06:29] Second, options have contingent payoffs.
- [06:33] Something has to happen for your cash flow to pay off.
- [06:37] And third, options have limited lives.
- [06:39] An underlying asset, a contingent payoff, and limited lives.

**On-screen content:**
![slide: When is there an option embedded in an action? (Definition of an option)](video-frame://46@06:21)
**When is there an option embedded in an action?**
An option provides the holder with the right to buy or sell a specified quantity of an underlying asset at a fixed price (called a strike price or an exercise price) at or before the expiration date of the option.

![slide: When is there an option embedded in an action? (Characteristics of an option)](video-frame://46@06:30)
**When is there an option embedded in an action?**
*   There has to be a clearly defined underlying asset whose value changes over time in unpredictable ways
*   The payoffs on this asset (real option) have to be contingent on an specified event occurring within a finite period
*   Options have limited lives

## [06:43] Using Payoff Diagrams to Identify Options

**Spoken content:**
- [06:43] In fact, the best way to recognize when you're dealing with an option is to draw the payoff diagram for your cash flows.
- [06:50] And if your payoff diagram looks like an option/payoff diagram, you have an option on your hands.
- [06:56] So very quickly, let's review the two types of option/payoff diagrams you can face.
- [07:02] If you have a call option, you get the right to buy an asset at a fixed price.
- [07:06] Here's what your payoff diagram will look like.
- [07:08] There's a kink at the strike price.
- [07:10] And if your value of the asset exceeds the strike price, dollar for dollar you make profits.
- [07:15] But if the value of the asset falls below the strike price, you don't lose an unlimited amount.
- [07:19] You lose what you paid for the option.
- [07:21] So you have limited losses below the strike price, potentially unlimited profits above the strike price.
- [07:27] If you have a put option, it's like holding a mirror up to those same cash flows.
- [07:32] If the value falls below the strike price, now you lose money.
- [07:35] Not an unlimited amount because your price might not be able to drop below zero.
- [07:39] But if the value exceeds the strike price, you lose what you paid for the put.

**On-screen content:**
![diagram: Payoff Diagram on a Call option](video-frame://46@07:07)
**Payoff Diagram on a Call**
*   Net Payoff (Y-axis) vs. Price of underlying asset (X-axis)
*   Strike Price indicated on X-axis
*   Payoff is zero below strike price, then increases linearly above it.

![diagram: Payoff Diagram on Put Option](video-frame://46@07:31)
**Payoff Diagram on Put Option**
*   Net Payoff On Put (Y-axis) vs. Price of underlying asset (X-axis)
*   Strike Price indicated on X-axis
*   Payoff is zero above strike price, then increases linearly as price falls below it.

## [07:44] Application of Payoff Diagrams

**Spoken content:**
- [07:44] So here's how I use payoff diagrams.
- [07:46] And in the sessions following, you're going to see this happen.
- [07:49] Whenever I talk about a real option, I'm going to first draw the payoff diagram to see if, in fact, I have a call or a put option on my hands.
- [07:57] And once I do that, I'm on my way to using option pricing.
- [08:01] Second question you need to ask, when is there significant economic value to this option?
## [08:02] Question 2: When Does an Option Have Significant Economic Value?

**Spoken content:**
- [08:07] Let me give you the key word that I think drives the discussion of real options.
- [08:12] It's exclusivity.
- [08:14] If you and only you can exercise this option, this option has significant value.
- [08:19] The less exclusivity you have, the less value there is to the option.
- [08:24] Again, this might sound mysterious, but let me give you a very quick anecdote to bring this home.

**On-screen content:**
![slide: When does the option have significant economic value? (Exclusivity)](video-frame://46@08:04)
**When does the option have significant economic value?**
*   For an option to have significant economic value, there has to be a restriction on competition in the event of the contingency.
*   In a perfectly competitive product market, no contingency, no matter how positive, will generate positive net present value
*   At the limit, real options are most valuable when you have exclusivity – you and only you can take advantage of the contingency. They become less valuable as the barriers to competition become less steep.

## [08:29] Anecdote: The Importance of Exclusivity

**Spoken content:**
- [08:29] A few years ago, a second-year MBA came into my office, and he was very excited.
- [08:34] His landlord had given him, he said, an option to buy the apartment he was renting, and he wanted to use an option pricing model to value the option.
- [08:42] I said, "Okay. What price did he say you could buy this apartment at?"
- [08:47] The MBA student thought for a while, and he said, "You know what? He never mentioned a price."
- [08:52] So I said, "Let's get this straight.
- [08:54] Your landlord has told you you can buy the apartment you're renting right now, anytime over the next year,
- [08:59] for whatever the prevailing market price is, right?"
- [09:01] And he said, "Hey, I guess that's what I've got."
- [09:03] I said, "What do you think that's worth?"
- [09:05] Anybody can buy that apartment at that market price.
- [09:08] You have no exclusivity.
- [09:10] You have no option value.
- [09:12] So with every real option, this is a question we'll stop and ask.
- [09:15] Is there exclusivity?
- [09:17] And it's not a zero-one proposition.
- [09:19] If you have total exclusivity, the total value of the option will count.
- [09:22] If you have absolutely no exclusivity, there is no option value.
- [09:26] If you're somewhere in the middle, you get part of the value of the option.
## [09:30] Determinants of Option Value

**Spoken content:**
- [09:30] Now, once you decide your option is exclusivity, then we know what the determinants of option value are, and there are only six.
- [09:37] Three relate to the underlying asset.
- [09:39] One is the value of the underlying asset.
- [09:41] As that moves up and down, the value of your option will change.
- [09:44] The second is the variance in that value.
- [09:48] As that variance goes up, your options will become more valuable.
- [09:52] And this is where asset pricing gets turned on its head.
- [09:56] Because up until now, whenever we've talked about risk, we've been very clear.
- [10:00] As risk goes up, value goes down in a discounted cash flow model.
- [10:04] As risk goes up, multiples go down in a relative valuation.
- [10:07] But in an option pricing model, as risk goes up, value goes up.
- [10:11] And the reason is simple.
- [10:12] You're protected on the downside.
- [10:14] Remember those payoff diagrams?
- [10:16] You cannot lose more than what you paid for the option.
- [10:19] So variance and risk becomes your ally.
- [10:21] And the third and final characteristic relating to the underlying asset that matters is if that asset pays a dividend, it can affect the value of your asset.
- [10:29] If you have a call option on a stock or an asset that pays a dividend, on the day the dividend is paid, the value of the asset is going to drop,
- [10:36] which is going to make call options less valuable and put options more valuable.
- [10:40] There are two variables relating to the option that matter.
- [10:43] One is the exercise price itself.
- [10:45] As that changes, the value of the option will change.
- [10:47] The right to buy something at a fixed price becomes more valuable at a lower fixed price.
- [10:53] And the other is the life of the option.
- [10:55] The more time I give you to play the option, the more valuable it becomes.
- [10:59] There's only one macro variable that enters the option pricing model, and that's the level of interest rates.
- [11:04] And it matters for a simple reason.
- [11:06] When interest rates are high, the present value of what I have to pay in the future, remember the price is fixed, becomes lower.
- [11:12] So call options become more valuable at higher interest rates and put options become less valuable.
- [11:18] So once you have an option and you decide that that option has significant economic value, we know the variables that drive the value of the option.

**On-screen content:**
![slide: Determinants of option value](video-frame://46@09:35)
**Determinants of option value**
*   **Variables Relating to Underlying Asset:**
    *   **Value of Underlying Asset:** as this value increases, the right to buy at a fixed price (calls) will become more valuable and the right to sell at a fixed price (puts) will become less valuable
    *   **Variance in that value:** as the variance increases, both calls and puts will become more valuable because all options have limited downside and depend upon price volatility for upside
    *   **Expected dividends on the asset:** likely to reduce the price appreciation component of the asset, reducing the value of calls and increasing the value of puts
*   **Variables Relating to Option:**
    *   **Strike Price of Options:** the right to buy (sell) at a fixed price becomes more (less) valuable at a lower price
    *   **Life of the Option:** both calls and puts benefit from a longer life
*   **Level of Interest Rates:**
    *   **As interest rates increase, the right to buy (sell) at a fixed price in the future becomes more (less) valuable

## [11:26] Question 3: Can an Option Pricing Model Value the Real Option?

**Spoken content:**
- [11:26] So let's assume you found an option and you've decided it has significant economic value.
- [11:30] The next question and final question you face is can I use an option pricing model to value this option?
- [11:36] And here we've got to understand the basics of option pricing models.
- [11:39] I won't bore you with the details, but here are the two basic principles that govern how we use option pricing models or what drives option pricing models.
- [11:48] The first is the principle of replication.
- [11:50] What is replication?
- [11:52] You can replicate or you can create a portfolio of the underlying asset, neither borrowing or lending,
- [11:58] that is exactly the same cash flows as the option.
- [12:02] And once you do that, the second principle comes into play, which is arbitrage.
- [12:06] If the option in the replicating portfolio have exactly the same cash flows, they have to trade at the same price.
- [12:12] So all option pricing models are built on replication and arbitrage.

**On-screen content:**
![slide: When can you use option pricing models to value real options? (Replication principle)](video-frame://46@11:48)
**When can you use option pricing models to value real options?**
*   The notion of a replicating portfolio that drives option pricing models makes them most suited for valuing real options where:
    *   The underlying asset is traded - this yields not only observable prices and volatility as inputs to creating replicating portfolios but allows for the possibility of creating replicating portfolios
    *   An active marketplace exists for the option itself
    *   The cost of exercising the option is known with some degree of certainty

## [12:16] Challenges in Applying Option Pricing Models to Real Assets

**Spoken content:**
- [12:16] But step back.
- [12:17] To be able to do replication and arbitrage, here are the things you have to be able to do.
- [12:21] You have to be able to buy and sell the underlying asset.
- [12:24] You have to be able to buy and sell the option.
- [12:26] You have to be able to borrow and lend at the risk-free rate.
- [12:29] Now it's difficult to meet all three conditions, but the further away you get from those three conditions,
- [12:34] the less likely it is that option pricing models will deliver a fair estimate of value for your option.
- [12:40] Now with that set up, let me lay out the two basic option pricing models you might run into in practice.

**On-screen content:**
![slide: When can you use option pricing models to value real options? (Imprecision and market price deviation)](video-frame://46@12:28)
**When can you use option pricing models to value real options?**
*   When option pricing models are used to value real assets, we have to accept the fact that:
    *   The value estimates that emerge will be far more imprecise
    *   The value can deviate much more dramatically from market price because of the difficulty of arbitrage

## [12:41] Choices of Option Pricing Models: Black-Scholes vs. Binomial

**Spoken content:**
- [12:46] The first, of course, is the Black-Scholes model.
- [12:49] The model that invented option pricing, as we know it.
- [12:52] In the Black-Scholes model, we make restrictive assumptions about a number of variables.
- [12:58] For instance, we assume that options are European options.
- [13:01] What are European options?
- [13:03] European options can be exercised only at expiration.
- [13:06] We assume that the variance of the underlying asset remains fixed over the life of the option.
- [13:11] And finally, we assume that the prices of the underlying asset don't have any jumps to them.
- [13:16] They're continuous.
- [13:17] They move in small increments.
- [13:19] They're big assumptions, but if you make those assumptions, you end up with a very simple model.
- [13:24] Simple in terms of the inputs you need.
- [13:26] In the option pricing model, at least as seen by Black-Scholes, there are only six inputs that drive the value of an option.
- [13:32] The value of the underlying asset.
- [13:34] The strike price.
- [13:35] The life of the option.
- [13:37] The riskless rate.
- [13:38] The time to expiration.
- [13:40] And the variance in the value of the underlying asset.
- [13:42] That's it.
- [13:43] There are no external variables.
- [13:45] So of those variables, you can value any option.
- [13:48] But it does base it on restrictive assumptions.

**On-screen content:**
![slide: Choices of Models (Black-Scholes Model)](video-frame://46@12:48)
**Choices of Models**
*   **Black-Scholes Model:** Makes restrictive assumptions about volatility (fixed over option life) and early exercise (none) and price process for underlying asset (no jumps), but arrives at a parsimonious model where the option value is a function of only 6 observable inputs:
    *   The current price of the underlying asset
    *   The strike price on the option
    *   The life of the option
    *   The variance in the price of the underlying assets
    *   The riskless rate for the option life
    *   Dividends over the life of the option (not in original Black Scholes)

## [13:51] Binomial Model

**Spoken content:**
- [13:51] The alternative is the binomial model.
- [13:53] In the binomial model, you're less restrictive in your assumptions.
- [13:56] You can have early exercise.
- [13:57] You can even have variances changing over time.
- [14:00] But here's the catch.
- [14:01] A binomial model requires you to be able to specify the prices at every branch of the binomial model.
- [14:07] A lot more information needed to use the binomial model.
- [14:10] Now, if you look at real options, and especially at real options books, many of them emphasize the fact that the Black-Scholes model is ill-suited to value most real options.

**On-screen content:**
![slide: Choices of Models (Binomial Model)](video-frame://46@13:52)
**Choices of Models**
*   **Binomial Model:** This is a more general and less restrictive model but it requires more data on how the price of the underlying asset will evolve over time.

## [14:11] Practical Considerations for Model Choice

**Spoken content:**
- [14:19] They're right.
- [14:20] Most real options have changing variances over time and require early exercise.
- [14:25] But having agreed on those terms, I still think that using the binomial model is not an easy choice.
- [14:32] All of the information you need for the binomial will often lead you into a dead end.
- [14:37] And if you can estimate the entire binomial model, I would argue that there's a far simpler way, using decision trees and basic statistics, that you can value any asset.
- [14:47] So let me put it this way.
- [14:48] If you have the information to draw the entire binomial model, you don't need option pricing to value an asset.
- [14:54] If you don't have that information, you're going to be stuck with the Black-Scholes, notwithstanding its limitations.

**On-screen content:**
![slide: Choice of Option Pricing Models (Practitioners' arguments)](video-frame://46@14:11)
**Choice of Option Pricing Models**
*   Most practitioners who use option pricing models to value real options argue for the binomial model over the Black-Scholes and justify this choice by noting that:
    *   Early exercise is the rule rather than the exception with real options
    *   Underlying asset values are generally discontinuous

![slide: Choice of Option Pricing Models (Binomial model information needs)](video-frame://46@14:47)
**Choice of Option Pricing Models**
*   If you can develop a binomial tree with outcomes at each node, it looks a great deal like a decision tree from capital budgeting. The question then becomes when and why the two approaches yield different estimates of value.

## [15:00] Key Tests for Real Options

**Spoken content:**
- [15:00] So let me sum up.
- [15:01] Options are a useful tool to have, but to apply them in valuation, there are three basic tests you've got to meet.
- [15:08] First, you've got to make sure that there is an option embedded in an action.
- [15:12] Check for that.
- [15:13] Second, check to see if you have exclusivity.
- [15:15] If you have exclusivity, you have significant option value.
- [15:18] And third, check to see if you can trade on the underlying asset and the option, because only then can the option pricing models deliver an accurate estimate of value.
- [15:29] As we'll see, for every hundred options you run out there, maybe two or three will pass these tests.
- [15:34] But when they do, it's an interesting way and a useful way to estimate value.

**On-screen content:**
![slide: Key Tests for Real Options](video-frame://46@15:09)
**Key Tests for Real Options**
*   **Is there an option embedded in this asset/decision?**
    *   Can you identify the underlying asset?
    *   Can you specify the contingency under which you will get payoff?
*   **Is there exclusivity?**
    *   If yes, there is option value
    *   If no, there is none
    *   If in between, you have to scale value
*   **Can you use an option pricing model to value the real option?**
    *   Is the underlying asset traded?
    *   Can the option be bought and sold?
    *   Is the cost of exercising the option known and clear?

## [15:39] Outro

**On-screen content:**
![NYU Stern logo](video-frame://46@15:39)
