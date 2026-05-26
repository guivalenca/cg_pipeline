---
id: "33"
title: "Video 1: How to Forecast with Confidence Using Monte Carlo Simulation | The Statistical CFO"
source_url: "https://www.youtube.com/watch?v=3TGoyQvrKMo"
fetch_url: "https://www.youtube.com/watch?v=3TGoyQvrKMo"
resolved_url: "https://www.youtube.com/watch?v=3TGoyQvrKMo"
firecrawl_title: null
description: null
fetched_at: "2026-05-26T16:59:33.768568Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "511d4f5bf23e462105a35ad957dede935637863388588d6c5dd2c13786692227"
cache_keys:
  - "511d4f5bf23e462105a35ad957dede935637863388588d6c5dd2c13786692227"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 1270.0
transcript_source: "manual_captions"
transcript_sha256: "43423a190b1e1e3e2316c848fce1a43216c8d2c736afabd2380accda346f383c"
word_count: 6697
char_count: 36122
content_sha256: "204cba751a8e6d950b1e2af77ce9705c7e2ab8c644b388c74a5f45f06d1522d6"
image_count: 36
link_count: 0
total_token_count: 85733
estimated_input_tokens: 68300
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:06] Introduction to Monte Carlo Simulation for CFOs

**Spoken content:**
- [00:06] Hey everybody, it's Joshua Zabel, the
- [00:08] statistical CFO back with another
- [00:11] YouTube premiere.
- [00:12] If you like these YouTube premier, uh,
- [00:15] you can see on my shirt, I'm wearing a Mintab
- [00:17] exchange shirt.
- [00:18] Minitab exchanges are in-person events
- [00:20] where people a lot smarter than me come to
- [00:23] discuss different challenges and
- [00:25] organizations and explain how to problem
- [00:27] solve. So I encourage you to visit your Local
- [00:29] one, but for now, let's
- [00:32] stick to the agenda. So I'm
- [00:34] going to jump into my presentation. The presentation
- [00:36] today is about Monte Carlo simulation
- [00:39] and what a useful tool it is
- [00:41] for CFOs or other
- [00:43] finance professionals that are
- [00:45] usually forecasting.

**On-screen content:**
![Minitab logo](video-frame://33@00:03)
![Joshua Zabel, the Statistical CFO, wearing a Minitab Exchange shirt](video-frame://33@00:06)

## [00:45] Helping CFOs Forecast and Provide Confident Guidance Ranges

**Spoken content:**
- [00:47] All right.
- [00:48] Let's get into
- [00:49] the topic for today,
- [00:51] which is helping CFO's forecast
- [00:53] and provide confident guidance ranges
- [00:55] using Monte Carlo simulation. I
- [00:57] always like to start a little bit about
- [00:59] me, the statistical CFO, uh,
- [01:02] and about who this is for. It's really.
- [01:04] Members of the finance organizations
- [01:07] or frankly sales organizations, people
- [01:10] that might provide forecasts or guidance
- [01:12] ranges,
- [01:13] whether it be to your CFO,
- [01:15] to your CEO,
- [01:17] to the executive team, or to investors in
- [01:19] the case of a public or
- [01:21] private company setting.
- [01:23] More about me, I've got a
- [01:26] BA, an MA in economics, so I'm not
- [01:28] a statistician.
- [01:29] I am the current CFO. I've worked at
- [01:32] large companies, small companies,
- [01:35] private, public,
- [01:36] um, and on Wall Street, off Wall
- [01:39] Street, and
- [01:40] what really excites me about this discussion about Monte
- [01:42] Carlo is,
- [01:44] it's a great tool to communicate
- [01:46] what you're finding and what you're thinking.
- [01:49] Uh, and it really helps you as a
- [01:51] CFO or a professional,
- [01:53] uh, really lean into
- [01:55] information and data rather than gut
- [01:57] feel and instinct and bias,
- [01:59] and I'll show you how that comes

**On-screen content:**
![Slide: Helping CFOs Forecast and Provide Confident Guidance Ranges Using Monte Carlo Simulation for Scenario Analysis](video-frame://33@00:45)
![Slide: About The Statistical CFO and About Me](video-frame://33@00:57)
About The Statistical CFO
* For members of finance organizations (or sales organizations) that might provide forecasts or guidance ranges to investors, executives, or Boards.

About Me
* I have a BA and MA in Economics.
* I am a Chief Financial and Strategic Planning Officer of an international organization.
* I've worked on "Wall Street", "Main Street" and Minitab!
* Worked at small and large organizations
* Worked at public and private companies

Over the course of this webinar, you'll learn what Monte Carlo Simulation is about and how to communicate your findings.

## [02:01] Definition of a Monte Carlo Simulation

**Spoken content:**
- [02:01] about. OK, so what is
- [02:04] Monte Carlo simulation?
- [02:06] Well, Monte Carlo simulation, you can
- [02:08] see a lot of these definitions. What
- [02:10] you're doing is assigning probability distributions
- [02:13] to uncertain inputs.
- [02:15] You're then using the computer to randomly
- [02:18] sample those distributions,
- [02:20] get some outcomes, and then analyze those
- [02:22] results. In layman's
- [02:24] terms, what it really means is when you have
- [02:26] a formula,
- [02:28] and if you kind of think of sales, let's
- [02:30] imagine you have sales that's comprised
- [02:32] of Division A, Division B, and Division
- [02:35] C, and there are all sorts of ranges of
- [02:37] those sales.
- [02:38] Rather than running through scenarios yourself,
- [02:40] Monte Carlo simulation runs those scenarios
- [02:43] for you
- [02:44] and actually gives you the percentages
- [02:46] or the risks of those outcomes.
- [02:48] So it really quantifies risks
- [02:51] or really scenario analysis.

**On-screen content:**
![Slide: Definition of a Monte Carlo Simulation](video-frame://33@02:01)
**What is Monte Carlo Simulation?**
* Instead of plugging in single "best-guess" numbers, you:
  * Assign probability distributions to uncertain inputs (for example, demand, cost, or material yield).
  * Use a computer to randomly sample from those distributions thousands of times.
  * Record the resulting outcomes (profit, project completion date, tolerance stack-up, etc.).
  * Analyze the results statistically—mean, median, percentiles, and risk of exceeding or missing targets.
  * Run your finance formula thousands of times using realistic ranges (not single guesses) for key inputs, so you get odds for outcomes instead of one fragile number
* This lets you see the full range of possible results and their likelihoods, not just one deterministic answer.
* This lets you see the full range of possible results and their likelihoods, e.g., "there's a 95% chance profit exceeds $2M".

## [02:52] Where Did the Name Monte Carlo Simulation Come From?

**Spoken content:**
- [02:53] I always think it's interesting to talk
- [02:55] about where these names came from.
- [02:57] Monte Carlo simulation actually was invented
- [03:00] as part of the Manhattan Project.
- [03:02] The scientists there were actually using this
- [03:05] approach, random sampling,
- [03:06] to solve their problems.
- [03:09] And they viewed it as similar to
- [03:11] gambling, which is where the Monte Carlo
- [03:13] casino comes in, the name,
- [03:15] and so that's how the name came
- [03:17] about, hence Monte Carlo.

**On-screen content:**
![Slide: Where Did the Name Monte Carlo Simulation Come From?](video-frame://33@02:52)
* The name comes from the Monte Carlo Casino in Monaco, famous for games of chance.
* When the method was developed in the 1940s by Stanisław Ulam and John von Neumann during the Manhattan Project, they noticed that the approach—using random sampling to solve deterministic problems—was similar to gambling: roll the dice or spin the wheel thousands of times and look at the statistical pattern.
* So they nicknamed it "Monte Carlo" after the casino.

## [03:19] Why a CFO Should Use Monte Carlo Simulation

**Spoken content:**
- [03:19] OK, so why as a CFO
- [03:22] should you use it, or frankly as someone who's forecasting,
- [03:25] it allows you to plan using odds
- [03:27] and math, not just your opinion.
- [03:30] Thinking about there's a 24%
- [03:32] chance we're going to do this as opposed to I think
- [03:35] or I hope,
- [03:37] it incorporates analytics.
- [03:39] A lot of times forecasts are based
- [03:41] on instinct.
- [03:42] You're trying to read the people who are giving you the
- [03:44] forecast.
- [03:46] Some salespeople are biased
- [03:48] to be more conservative. Some are biased to be more.
- [03:50] Aggressive.
- [03:51] Uh, same thing with your marketing people might
- [03:54] consistently overspend or underspend.
- [03:56] Those are things in the mind of a CFO
- [03:58] that we try to do some math around.
- [04:01] Uh, this allows you to take analytics, uh,
- [04:03] which allows you to explain it and defend it.
- [04:06] It also helps you face realities.
- [04:08] Uh, I'd like to think people are inherently optimistic,
- [04:11] so we're hopeful that people will do better.
- [04:14] This puts some sobriety into
- [04:16] those forecasts,
- [04:17] and I think most importantly, it's a better
- [04:19] communication tool to your CEO
- [04:22] or your board.
- [04:23] It provides mathematical context
- [04:26] around that
- [04:27] forecast,
- [04:28] um, and it makes you sound smart, like you know what you're doing,
- [04:31] which is always a bonus too.

**On-screen content:**
![Slide: Why a CFO should use it](video-frame://33@03:19)
* Make plans with odds, not opinions
  * There's a 24% chance EBITDA < target."
* Incorporate analytics into your forecast
  * Don't just rely on gut instinct; get confidence levels of sales or spend
* Face realities
  * Takes the "hope" factor out of the equation
* Better communication to your CEO and/or Board of Directors
  * Provide mathematical context (and opinion)
  * And sound smarter too! 😉

## [04:32] Simplicity and Utility of Monte Carlo Simulation

**Spoken content:**
- [04:33] So, how simple can it be? It actually
- [04:35] can be quite simple. Uh, Monte Carlo simulation
- [04:38] sounds really fancy and may be advanced,
- [04:40] um, and frankly speaking, the more complex your
- [04:42] equation is,
- [04:44] the more useful it is.
- [04:46] Uh, so it can be quite complex, but it also
- [04:48] can be quite simple and used in a really simple
- [04:50] way. And I'm going to show you
- [04:52] examples
- [04:54] that are really simple, that are applicable
- [04:56] to things that you probably see all the time,
- [04:58] uh, and you'll see how easy it can be.

**On-screen content:**
![Slide: How simple can it be?](video-frame://33@04:32)
* Monte Carlo Simulation can be quite simple!
* The more complex your "equation" or forecast drivers, the more utility it has.

## [05:00] Example: Simple Equation Forecasting

**Spoken content:**
- [05:01] So let's start with that simple
- [05:03] example.
- [05:05] You're a CFO. I'm a CFO
- [05:07] trying to project revenues for a quarter.
- [05:09] Hypothetically, maybe you have 3 regions.
- [05:13] You can see the regions are projecting
- [05:15] different levels.
- [05:17] In this case, I have $10.20
- [05:19] dollars, $17 for each region
- [05:21] for the quarter.
- [05:23] But what they do typically in a forecast
- [05:25] is they'll highlight.
- [05:27] Various things at risk and they'll also
- [05:29] highlight potential upside.
- [05:31] So what do you do with this as a CFO
- [05:34] or a sales leader
- [05:36] or an executive who gets these
- [05:38] type of forecasts?
- [05:39] So you can see the basic math is if
- [05:41] you take the forecast,
- [05:43] uh, you have a forecast of $47
- [05:46] pretty straightforward.
- [05:48] If you look at the downside risk, you're
- [05:50] looking at $34
- [05:52] and if you look at the upside, it's $61.
- [05:55] And so now you have a situation where
- [05:57] you have a range of 34 to 61,
- [05:59] uh, with a forecast of 47.
- [06:02] Um, and that's all fine and good
- [06:05] until you start getting questions about this
- [06:07] from your boss or your board.
- [06:10] Um, and using Monte Carlo will give
- [06:12] us some of those contextual
- [06:14] answers.

**On-screen content:**
![Slide: Example: Simple Equation Forecasting](video-frame://33@05:00)
**Example: Simple Equation Forecasting**
* You're a CFO trying to project revenues for the Quarter. You have 3 regions:
  * Region 1: Projecting $10 for the quarter, with risks that could end up as $9 and upside of $12
  * Region 2: Projecting $20 for the quarter, with risks that could end up as $15 and upside of $22
  * Region 3: Projecting $17 for the quarter, with risks that could end up as $10 and upside of $27
* Basic forecasting math of $10+$20+$17 means the forecast is $47.
  * The risk to the downside is $34.
  * The upside is $61.
* How do you quantify risk/reward here?
* How do you answer your Board of Directors?

## [06:14] Addressing Board and CEO Questions with Monte Carlo Simulation

**Spoken content:**
- [06:15] So let me go specifically. So
- [06:17] this forecast gets presented,
- [06:19] the range is 34 to 61, and the
- [06:21] forecast is 47.
- [06:23] And so a board might actually ask you something
- [06:26] like, how likely is it we hit 34,
- [06:28] because that's really bad,
- [06:30] um, or a more optimistic board might
- [06:32] say, how likely is it we hit 64, that'd
- [06:34] be great.
- [06:35] Um, what do you think?
- [06:37] In your judgment, you know, what do you
- [06:39] think? Um,
- [06:41] The CEO may say, OK,
- [06:43] understanding those things, how much should we spend?
- [06:46] Because if 34 is a reality,
- [06:49] then we better cut back on spending
- [06:51] because we don't want to spend more money than our revenues.
- [06:55] But on the flip side, if 61
- [06:57] is a reality,
- [06:58] we should be investing some
- [07:00] of that upside.
- [07:02] So what should we do, Mr. CFO
- [07:04] or Mrs. CFO?
- [07:06] And then in the context of a public company,
- [07:09] imagine you get this and you're asked to give a guidance
- [07:11] range of revenue forecasts.
- [07:13] How do you give that range, 34
- [07:15] to 64,
- [07:17] is a pretty large range.
- [07:19] So what I'm going to ask you to do is take a moment now,
- [07:22] think about what you would do,
- [07:23] and I would say take a screenshot of
- [07:25] this slide,
- [07:27] because as I go through the exercise here, I'm
- [07:29] going to allude to these numbers,
- [07:31] and, and I just want you to kind of think context
- [07:34] of how you would deal with it.

**On-screen content:**
![Slide: When the Board Asks... How Do You Answer?](video-frame://33@06:14)
**When the Board Asks... How Do You Answer?**
* Based on current information...
  * The revenue range is $34 to $64 with a target/forecast of $47
* The Board Asks...
  * How likely is it we hit $34?
  * How likely is it we hit $64?
  * What do you think?
* The CEO Asks...
  * How much should we spend?
    * If $34 is a real risk, we better cut back!
    * If $64 is a real possibility, we should invest!
* What Do You Tell Investors?
  * If you're a public company, what guidance range do you provide?
Take a Moment and Think How What You Would Do and Why?

## [07:35] Understanding Distributions for Monte Carlo Simulation

**Spoken content:**
- [07:35] So I'm actually going to jump into the software in a
- [07:37] minute. Uh, but before I
- [07:40] jump into the software, when
- [07:42] you use Monte Carlo simulation,
- [07:44] you use different distributions
- [07:47] to do the simulation.
- [07:48] In statistics, distribution just describes
- [07:51] how a variables value
- [07:54] or spread out arranged possible
- [07:56] outcomes.
- [07:57] Uh, showing which values are more frequent or which
- [07:59] are less.
- [08:00] There are various distributions
- [08:02] that could be a whole talk in and of itself,
- [08:04] which I'm not going to jump into,
- [08:06] but I'm going to highlight three distributions
- [08:09] that I think are particularly applicable
- [08:12] for people in finance, or at least
- [08:14] the way we think.
- [08:16] The first one is a normal distribution. The
- [08:18] normal distribution is the classic bell
- [08:20] curve distribution, where most data
- [08:22] points cluster around the mean.
- [08:24] We all know that.
- [08:26] Then there's a triangular distribution. The reason
- [08:28] why I like it for financial
- [08:30] situations is oftentimes in finance,
- [08:33] we think of things in 3 cases.
- [08:35] We think of a bear case,
- [08:37] the minimum, a bull case, which
- [08:39] is the maximum, and a base case, which is
- [08:41] the most likely.
- [08:43] And so that's a helpful context to
- [08:45] think about how you could use Monte Carlo.
- [08:47] The other thing is a uniform distribution.
- [08:50] Which really deals with if you have a range.
- [08:52] So in the case that you just have the bear case
- [08:54] and the bull case, or the best case and the worst case,
- [08:57] it's a helpful range.
- [08:59] Now, I'm going to jump into the software
- [09:01] and show you how easy it is to do.

**On-screen content:**
![Slide: How simple can it be? Let's Jump Into the Software!](video-frame://33@07:35)
**How simple can it be?**
* Let's Jump Into the Software!
  * Before we jump in, you're going to see me use different "distributions."
  * In statistics, a distribution describes how a variable's values are spread out or arranged across all possible outcomes, showing which values are more frequent and which are less.
* I'm going to use a few distributions:
  * A **Normal** distribution is the typical "bell curve," where most data points cluster around the mean.
  * A **triangular** distribution where you know the min, the max and most likely
    * I think if this as the bear, bull and base case
  * A **uniform** distribution that makes any value between the bounds equally likely.

## [09:03] Running a Simple Monte Carlo Simulation in Minitab Workspace (Uniform Distribution)

**Spoken content:**
- [09:03] So I'm going to pull over
- [09:05] my web browser.
- [09:06] I'm gonna jump right into
- [09:08] app.minitab,
- [09:10] which is the mini tab Solution Center.
- [09:14] I'm gonna jump right into.
- [09:17] Minitab workspace, one of the applications
- [09:19] in the Solution Center,
- [09:20] which has our Monte Carlo simulation.
- [09:29] And when you get here, you can see it's asking
- [09:31] for a model and outputs.
- [09:33] And
- [09:34] if you remember, what did we talk about? We talked
- [09:36] about we wanted to, we had 3 regions, so
- [09:38] I'm going to say region 1.
- [09:41] Region 2
- [09:44] And
- [09:45] region 3.
- [09:49] I'm going to use the uniform distribution
- [09:51] for all of them.
- [09:53] That was the one that just had the, the range,
- [09:55] the worst and the, and the best, and I asked
- [09:57] you to take a screenshot of this,
- [09:59] and you can see we started with
- [10:01] 9 to 12,
- [10:03] and then we had 15
- [10:06] to 22
- [10:08] and
- [10:09] 10
- [10:10] to 27.
- [10:12] And then all I'm going to do is say total sales.
- [10:16] And you can see here the equation
- [10:18] is of total sales is my 3 regions
- [10:20] added up, which is region 1 plus region
- [10:22] 2 plus region 3.
- [10:24] And I'm gonna hit enter.
- [10:26] I have my
- [10:27] equation in, and now I'm gonna
- [10:29] do a simulation run,
- [10:32] and so that's it. It's simple as that.
- [10:34] I'm done.
- [10:35] You can see here the mean is 47,
- [10:38] uh, which is, which is good
- [10:40] because it actually shows that's pretty close to my
- [10:42] forecast.
- [10:43] Um, and then you can see other percentiles,
- [10:46] which I'm gonna dive into later.
- [10:48] Uh, but I'm going to first, what I like to
- [10:50] do is run the simulation multiple
- [10:52] times,
- [10:53] uh, with different,
- [10:55] uh, distributions. So I'm going to duplicate this distribution.

**On-screen content:**
![Minitab Solution Center interface](video-frame://33@09:05)
![Minitab Workspace interface for Monte Carlo Simulation](video-frame://33@09:28)
![Minitab Workspace showing inputs for Region 1, Region 2, Region 3 with Uniform distribution and their respective lower and upper bounds](video-frame://33@09:50)
![Minitab Workspace showing the equation for Total Sales as the sum of Region 1, Region 2, and Region 3](video-frame://33@10:17)
![Minitab Workspace displaying the results of the Monte Carlo simulation for Total Sales with a histogram and summary statistics, showing a mean of 47.000](video-frame://33@10:30)

## [10:56] Running a Monte Carlo Simulation with Triangular Distribution

**Spoken content:**
- [10:58] I now have it all over again. You can see it's
- [11:00] again, but this time instead of uniform,
- [11:02] I'm going to do triangular.
- [11:04] Remember, triangular was the base case.
- [11:07] The bull case and the bear case,
- [11:09] and if you'll remember here for
- [11:12] the regions I had 9 with a
- [11:14] forecast of 10 as the base case
- [11:16] and the bull case of 12
- [11:18] for the lower on the next one, I
- [11:20] had 15 as the bear case with
- [11:22] 20 as the base and 22
- [11:24] as the bowl case.
- [11:26] And for the last region,
- [11:28] I have 10.
- [11:29] 17 and 27.
- [11:32] And again, the same equation, I'm
- [11:34] just gonna run the simulation again.
- [11:45] There we go.
- [11:48] And you can see results again. Interestingly
- [11:50] enough, I have the mean of 47, so that's
- [11:52] great, and percentiles, which again, I'm
- [11:54] gonna show you in a minute.
- [11:56] Um, and then last, I'm gonna copy

**On-screen content:**
![Minitab Workspace showing inputs for Region 1, Region 2, Region 3 with Triangular distribution and their respective lower, base, and upper bounds](video-frame://33@11:03)
![Minitab Workspace displaying the results of the Monte Carlo simulation for Total Sales with a histogram and summary statistics, showing a mean of 47.000](video-frame://33@11:43)

## [11:57] Running a Monte Carlo Simulation with Normal Distribution

**Spoken content:**
- [11:59] this again.
- [12:01] And I'm going to run the normal distribution,
- [12:04] which I talked about.
- [12:06] Now, the difference in the normal distribution is
- [12:08] you can see, you have your mean,
- [12:10] uh, which in this case is going to be
- [12:12] 10.
- [12:15] 20 and 17
- [12:17] and standard deviation,
- [12:19] the quick
- [12:21] way to calculate standard deviation is take
- [12:23] the range over 4.
- [12:25] I've done that math,
- [12:26] uh, in preparing,
- [12:28] uh, but if you look at the slide I asked
- [12:30] you to take a screenshot of, you can quickly
- [12:32] take the ranges all of the, the,
- [12:35] the top of the range minus the bottom of the range,
- [12:37] divide by 4.
- [12:38] In this one, it was 10 was the range, divided by
- [12:40] 4 is 2.5.
- [12:42] Um, and once again, I'm going to run the simulation.
- [12:45] And again, I got a mean of 47.
- [12:48] So, really good news. I got 3 means
- [12:50] of 47. My forecast is 47,
- [12:53] so I'm feeling pretty good. Now, what I'm going to do is
- [12:55] go switch back now
- [12:57] to
- [12:57] the, uh, I'm going to take this
- [13:00] and move it away for now,
- [13:02] and I'm going to switch back to
- [13:04] my presentation mode here,
- [13:07] and I'm going to show you the results
- [13:10] of those simulations.

**On-screen content:**
![Minitab Workspace showing inputs for Region 1, Region 2, Region 3 with Normal distribution and their respective means and standard deviations](video-frame://33@12:02)
![Minitab Workspace displaying the results of the Monte Carlo simulation for Total Sales with a histogram and summary statistics, showing a mean of 47.000](video-frame://33@12:44)

## [13:13] Examining the Results of the Simulations

**Spoken content:**
- [13:13] So here are the results of the simulations.
- [13:16] Um, like I said, you can run one
- [13:18] type of stimulation. I like to run multiple
- [13:20] ones just because you see how quick and easy
- [13:22] it is,
- [13:23] and it gives you more context and more
- [13:25] confidence.
- [13:27] The way to read these, when you look at these percentiles,
- [13:29] and you can see I have it written down,
- [13:31] we'll start with the first uniform distribution, is
- [13:33] 90%
- [13:35] of the simulated outcomes are going to be less
- [13:37] than or equal to 55,
- [13:39] in this case, or 54.67.
- [13:42] The second. Uh, analysis or
- [13:44] stimulation came up with 52.5,
- [13:46] and the third one was 52.9.
- [13:49] Uh, so
- [13:51] that goes when we go into the ranges
- [13:53] that we talked about, the upside of
- [13:55] 61.
- [13:57] This gives me a pretty good impression
- [13:59] that 61 probably isn't a realistic
- [14:01] outcome.
- [14:02] How good can it be if the board asks?
- [14:05] Somewhere between 53
- [14:07] and 55 is probably a good
- [14:09] answer. Maybe you guessed 54
- [14:12] as a good range.
- [14:13] And then the other part is how bad can it be?
- [14:16] Uh, and again, looking at that 10th
- [14:18] percentile, so there's less than 10%
- [14:21] chance
- [14:22] the value is, uh,
- [14:24] in this case in a uniform 40,
- [14:27] the 2nd 142, and the 3rd 141,
- [14:30] and I'll highlight that here. Here's your 40, 42,
- [14:32] and 41.
- [14:33] Again,
- [14:34] when we looked at the first situation, our
- [14:36] worst case scenario was 34.
- [14:39] So when the board asked me how I feel about
- [14:41] this forecast,
- [14:43] the nice thing was we saw the
- [14:45] mean of 47 come up a
- [14:47] few times,
- [14:48] so I feel pretty good about that forecast of
- [14:50] 47 as the best
- [14:52] guess I can make.
- [14:54] Um, but I would also say that the range
- [14:56] is more realistic, something like,
- [14:58] you know, 41 or 40
- [15:01] to 42
- [15:02] to something like 54,
- [15:05] right? Which is a much tighter range
- [15:07] than the 34 to 61.
- [15:10] OK, so that's pretty simple.

**On-screen content:**
![Slide: Example: Let's Examine The Results](video-frame://33@13:13)
**Example: Let's Examine The Results**
![Table showing percentiles for Uniform Distribution](video-frame://33@13:13)
**Uniform Distribution**
* 90% of the simulated outcomes are going to be less than or equal to $55 and only 10% of the runs will exceed those values.
* There's also less than a 10% chance the value is less than $40.

![Table showing percentiles for Triangular Distribution](video-frame://33@13:13)
**Triangular Distribution**
* 90% of the simulated outcomes are going to be less than or equal to $52.5 and only 10% of the runs will exceed those values.
* There's also less than a 10% chance the value is less than $42.

![Table showing percentiles for Normal Distribution](video-frame://33@13:13)
**Normal Distribution**
* 90% of the simulated outcomes are going to be less than or equal to $53 and only 10% of the runs will exceed those values.
* There's also less than a 10% chance the value is less than $41.

## [15:11] Example: More Complex Equation Forecasting (Operating Income)

**Spoken content:**
- [15:13] Um, let's up the ante
- [15:15] here and make it a little more complex,
- [15:17] because you may say, well, that really seems simple. I don't really
- [15:19] need to do that,
- [15:20] um. OK, so now let's use those
- [15:22] same regions, those same
- [15:24] revenue projections here with
- [15:26] the same uncertainty around them, but
- [15:29] now we're trying to forecast the
- [15:31] operating income or the EBIT.
- [15:33] And so
- [15:34] we get a forecast from our sales team,
- [15:36] but our chief marketing officer says,
- [15:39] uh, and our CRO says, well,
- [15:42] our expenses are expected to be in the range of 10 to
- [15:44] 15. We're not quite sure.
- [15:47] Um, and then our R&amp;D and development team
- [15:49] says, well, the expenses are in a range of 6 to
- [15:51] 10. So now I've
- [15:53] added another
- [15:54] layer of complexity
- [15:56] because if I look at my forecasting
- [15:58] math of 47,
- [16:00] I had that downside of 34 to 61.
- [16:03] And now if the board says to you, what's the best
- [16:05] case scenario,
- [16:07] the best case scenario would be the 61, which
- [16:09] is the best case revenue, and the
- [16:11] least amount of expense, which would be 10
- [16:13] and 6, which would get me an operating
- [16:16] income of 45.
- [16:17] The worst case scenario would be the worst revenue
- [16:20] case and the most expenses, which would
- [16:22] be 9.
- [16:23] So now I've got a situation where I've got a range of
- [16:25] 45 and 9 or 9 to
- [16:27] 45,
- [16:28] which is a huge range. I have the
- [16:30] board asking me what I think
- [16:33] is likely going to happen.
- [16:34] Um, and right now the way I'm
- [16:37] doing that is guessing it. I'm basically
- [16:39] saying, well,
- [16:40] my marketing person is traditionally
- [16:42] conservative, so she's probably
- [16:45] OK at $10.
- [16:47] My R&amp;D folks are traditionally
- [16:49] aggressive,
- [16:50] so, you know, they are saying $6 to $10
- [16:53] but really, They're going to spend 12, I don't know.
- [16:56] And so
- [16:57] the way you want to give an answer is preferably
- [17:00] with the data. What is the data telling you?
- [17:02] Because that allows you to look at your board or your
- [17:04] CEO or your investors and say,
- [17:06] hey, look, based on the information I
- [17:08] have, this is the best guess I
- [17:10] can make based on the data.

**On-screen content:**
![Slide: Example 2: More "Complex" Equation Forecasting](video-frame://33@15:11)
**Example 2: More "Complex" Equation Forecasting**
* You're a CFO trying to project revenues for the Quarter. You have 3 regions:
  * Region 1: Projecting $10 for the quarter, with risks that could end up as $9 and upside of $12
  * Region 2: Projecting $20 for the quarter, with risks that could end up as $15 and upside of $22
  * Region 3: Projecting $17 for the quarter, with risks that could end up as $10 and upside of $27
* You also have expenses that you're trying to forecast:
  * Sales and Marketing Expenses of $10 to $15
  * Research and Development Expenses of $6 to $10
* What is your likely operating income (or EBIT)?
  * Remember: Forecasting math of $10+$20+$17 means the forecast is $47.
  * The risk to the downside is $34.
  * The upside is $61.
* Based on simple math...
  * The best case would be $61 - $10 - $6 = $45
  * The worst case would be $34 - $15 - $10 = $9
* When the Board Asks: What's our likely outcome? How Do You Answer?

## [17:13] Running a Complex Monte Carlo Simulation in Minitab Workspace (Uniform Distribution)

**Spoken content:**
- [17:13] So
- [17:14] how are we going to do this?
- [17:16] So I'm going to stick to a uniform distribution
- [17:18] because it's right now we believe
- [17:20] all the data points are
- [17:22] likely. We don't have any belief about
- [17:24] that distribution,
- [17:26] and so I'm going to jump in the software
- [17:28] again. So
- [17:30] let's hold on one second as I jump in
- [17:32] the software.
- [17:34] I'm dragging the software over
- [17:36] again. I'm going to go to my nice navigator.
- [17:40] I'm going to go to my first simulation,
- [17:42] which had the uniform distribution,
- [17:45] as you'll see. So if we look at the model,
- [17:47] you'll remember I had the uniform distribution.
- [17:49] I'm going to duplicate this simulation,
- [17:52] and I'm going to add.
- [17:54] Another X and another Y, and
- [17:56] the first X is gonna be sales
- [17:59] and marketing expense.
- [18:01] And
- [18:03] 3, I'll just say R&amp;D
- [18:05] for the interest.
- [18:07] Um, and again, we're gonna say that uniform
- [18:09] distribution, which is the one that you have the low
- [18:12] case and the best case,
- [18:13] and if you remember here,
- [18:15] my sales and marketing was gonna be 10
- [18:18] to 15.
- [18:20] And my R&amp;D was going to be 6 to 10.
- [18:24] But my equation has to change here, so
- [18:26] if you remember.
- [18:28] To find my operating income.
- [18:33] I'm gonna take my sales, only
- [18:35] this time I'm actually gonna subtract out
- [18:38] my expenses.
- [18:41] So,
- [18:42] not a very
- [18:44] complicated
- [18:45] equation here, but more complicated
- [18:48] than just the addition,
- [18:50] and I'm going to quickly run a simulation.
- [18:53] And again, here you can see the mean of 27,
- [18:55] that's important.
- [18:57] I'm going to go back to my
- [18:59] presentation where I've
- [19:01] highlighted the
- [19:03] Answers to make it much easier.

**On-screen content:**
![Slide: How Do We Do This?](video-frame://33@17:13)
**How Do We Do This?**
* Let's Jump Into the Software!
  * We'll stick to the Uniform distribution because we have a range..
  * ...and because we believe all values are equally likely
![Minitab Workspace interface showing the previous simulation results](video-frame://33@17:34)
![Minitab Workspace showing inputs for Sales and Marketing Expense and R&D with Uniform distribution and their respective lower and upper bounds](video-frame://33@18:08)
![Minitab Workspace showing the equation for Operating Income as Total Sales minus Sales and Marketing Expense minus R&D](video-frame://33@18:34)
![Minitab Workspace displaying the results of the Monte Carlo simulation for Operating Income with a histogram and summary statistics, showing a mean of 27.000](video-frame://33@18:50)

## [19:05] Examining the Results of the Complex Simulation

**Spoken content:**
- [19:05] And so
- [19:06] again, looking at that distribution here
- [19:09] you can see at the 90th percentile
- [19:11] we're at 34.5
- [19:13] and the 10% is
- [19:15] 19.
- [19:17] And so
- [19:18] rather than telling the board or my CEO I
- [19:20] have a range of 9. To 45.
- [19:23] Um, I can tighten that range
- [19:25] much more, 19 to 35,
- [19:27] and with a mean of 27,
- [19:29] gives me a really good data-driven
- [19:32] analysis
- [19:34] of what I believe the forecast
- [19:36] range is and the likely outcomes
- [19:38] will be.

**On-screen content:**
![Slide: Example: Let's Examine The Results (Uniform Distribution)](video-frame://33@19:05)
**Example: Let's Examine The Results**
**Uniform Distribution**
![Table showing percentiles for Uniform Distribution of Operating Income](video-frame://33@19:05)
* 90% of the simulated outcomes are going to be less than or equal to $34.5 and only ~10% of the runs will exceed those values.
* There's also less than a ~10% chance the value is less than $19.
**Rather than having a range of $9 to $45:**
**You have a much tighter range of:**
**$19 to $35**

## [19:39] Review and Conclusion

**Spoken content:**
- [19:39] So, let's review. First
- [19:42] of all,
- [19:43] uh, you can now talk about Monte Carlo
- [19:45] at cocktail parties and at your board,
- [19:47] which will make you sound smart,
- [19:50] hopefully.
- [19:51] Uh, but more importantly,
- [19:53] uh, keep in mind, Monte Carlo
- [19:55] provides insight. It lets you see a range of possibilities
- [19:58] and their likelihood,
- [19:59] and really lets you quantify risk.
- [20:03] It can be used for simple analysis, as I showed
- [20:05] you, or more complex.
- [20:07] Uh, the more complex your equation,
- [20:09] as you saw, the more utility it
- [20:11] has because by definition, there's more variability,
- [20:14] so it's really helpful.
- [20:15] Um, and I think where it's really
- [20:17] critical is a communication
- [20:19] tool. Um,
- [20:21] again, the CFO is always looked
- [20:23] to as what is your belief
- [20:25] of these things are going to happen and
- [20:27] inherently we have judgment, and
- [20:30] CFO does have some judgment and uses
- [20:32] judgment.
- [20:33] Uh, but a better CFO incorporates
- [20:35] data-driven analysis
- [20:37] with that judgment,
- [20:39] um, and Monte Carlo is a great way
- [20:41] to provide that data-driven analysis.

**On-screen content:**
![Slide: Review](video-frame://33@19:39)
![Slide: Monte Carlo Simulation Provides Insight](video-frame://33@19:50)
**Monte Carlo Simulation Provides Insight**
* Monte Carlo Simulation lets you see a range of possibilities and their likelihood → Lets you quantify risk
* Monte Carlo Simulation can be used for simple or more complex problems.
* Monte Carlo Simulation is a great communication tool!
  * Help you provide ranges to your CEO or Board

## [20:44] Questions and Call to Action

**Spoken content:**
- [20:44] So, that's the end of our talk.
- [20:47] Uh, if you have any questions, uh,
- [20:49] please submit them, uh, and, and
- [20:51] hopefully you have been submitting them, and we'll
- [20:53] get back to you.
- [20:54] And please comment if there's any other topics
- [20:56] on simulation or statistics that
- [20:58] you want to learn.
- [21:00] Thank you very much and have a great
- [21:02] day. Bye.

**On-screen content:**
![Slide: Questions? Thank you for your time! Please comment if you want to learn other ways to use simulation or statistics!](video-frame://33@20:44)
![Minitab logo and website](video-frame://33@21:03)
