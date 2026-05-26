---
id: "35"
title: "Monte Carlo Simulation Made Super Easy!"
source_url: "https://www.youtube.com/watch?v=n0LmyI075mg"
fetch_url: "https://www.youtube.com/watch?v=n0LmyI075mg"
resolved_url: "https://www.youtube.com/watch?v=n0LmyI075mg"
firecrawl_title: null
description: null
fetched_at: "2026-05-26T17:00:32.523704Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "44c3774b9b4f94721a3e6995873093f9cff62d48017f56c2e4f79eb792cb924a"
cache_keys:
  - "44c3774b9b4f94721a3e6995873093f9cff62d48017f56c2e4f79eb792cb924a"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 432.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "0888469e6525e314f91061c9e8ee51f07334a3e8ad1799d57f38db5f19f8ed63"
word_count: 2124
char_count: 11116
content_sha256: "27b018829b58ac3634c0966ff0aa3ca1ef968010eb0394250aa6d35d3b3feb88"
image_count: 16
link_count: 0
total_token_count: 29935
estimated_input_tokens: 23232
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Monte Carlo Simulation in Excel

**Spoken content:**
- [00:01] Hello and welcome. Today we're working on how to do Monte Carlo simulation in Excel.
- [00:06] Now I'm just trying to show you the easiest example I can show you.
- [00:10] And so this is a little income statement. So sales and variable cost and fixed cost
- [00:16] and you'll end up with a profit, hopefully, right? So sales minus variable cost minus fixed cost
- [00:21] gives us a profit or it could be a loss. Now to do Monte Carlo simulation, we need to know

**On-screen content:** The video opens with an Excel spreadsheet titled "Intro to Monte Carlo Simulations in Excel". The spreadsheet shows a basic income statement structure with "Sales", "Variable Costs", and "Fixed Costs" in column B, and corresponding "Mean" and "Std Dev" values in columns C and D.
![Excel spreadsheet showing initial income statement setup with Mean and Std Dev for Sales, Variable Costs, and Fixed Costs](video-frame://35@00:00)

## [00:24] Estimating Sales with NORM.INV and RAND()

**Spoken content:**
- [00:28] the mean and we need to know the standard deviation of some numbers or group of numbers.
- [00:34] And so at Monte Carlo simulation says, look, instead of just doing one, let's do it a thousand times
- [00:41] or here I'm going to show you how to do it ten thousand times. It's just as easy to do it five
- [00:46] hundred or a thousand or ten thousand in Excel. So let's get started. Here's what we're going to do
- [00:51] with the estimate. We're going to use a function called the norm inverse. So the norm.inv, the
- [01:01] probability, I want to randomize this number for the probability. So I've got rand, R-A-N-D is a
- [01:08] function in Excel and I need to open the bracket and close the bracket. And what we'll have is this
- [01:14] number will be randomized from zero to one. And then because it's in this function, we're going to say,
- [01:21] we're going to use the mean and we're going to use the standard deviation and hit OK.

**On-screen content:** The speaker begins to enter a formula in cell C6 for Sales.
![Excel formula builder showing NORM.INV function with RAND() for probability, and C2 (Mean) and D2 (Std Dev) as arguments](video-frame://35@00:54)
The formula entered is `=NORM.INV(RAND(),C2,D2)`. This calculates a random sales value based on the mean and standard deviation.

## [01:27] Copying Formulas and Observing Volatility

**Spoken content:**
- [01:27] And we have estimated our sales. Now I can copy this down. I can copy the variable cost and the
- [01:36] fixed cost. So let's check the fixed cost. It's based on the mean of 150 and the standard deviation
- [01:42] of 15,000. And what will happen is you'll notice every time we enter something, every time we change
- [01:48] a formula or type something in, these numbers will randomize and come up with a new set of numbers.
- [01:54] So for example, we'll take 708 minus the 356 minus the 176. We'll hit enter and those three numbers
- [02:03] will update automatically, but the formula will still stay. 6, 16, 338, 130, and then 147 right now
- [02:12] is our profit calculation. So here's what we're going to do. We're going to say, OK, the 10,000 simulation,

**On-screen content:** The `NORM.INV` formula is copied down to cells C7 and C8 for Variable Costs and Fixed Costs, respectively, referencing their corresponding Mean and Std Dev values.
![Excel spreadsheet showing NORM.INV formulas copied for Variable Costs and Fixed Costs, with calculated values](video-frame://35@01:34)
A profit calculation is then added in cell C9: `=C6-C7-C8`.
![Excel spreadsheet showing calculated profit and the formula for profit](video-frame://35@02:04)
The values in C6, C7, C8, and C9 change with every action due to the `RAND()` function.

## [02:15] Setting Up 10,000 Simulations

**Spoken content:**
- [02:19] this is simulation zero, and I'm going to point to the here now at 74,000. Every time we hit enter,
- [02:27] it's going to update and randomize again. So this is called a volatile function. So what I want to do
- [02:33] is I want to do a column for 10,000. So I have zero right here. And what I'm going to do is on the home
- [02:42] ribbon, I'm going to go to the right here and do a series. The series I want is in a column. I want
- [02:51] it to go up by one. So the step value is one. I want it to stop at 10,000. So I'm going to hit OK.
- [02:58] And so you see what I have now is I've got 10,000 cells in a column and it's numbered one through 10,000.

**On-screen content:** The speaker sets up a "Simulations" column (F) and a "Profit" column (G). Cell G4 is linked to the profit calculation in C9 (`=C9`).
![Excel spreadsheet showing "Simulations" column with "0" and "Profit" column with a value linked to the main profit calculation](video-frame://35@02:20)
The speaker uses the "Fill Series" feature (Home tab > Fill > Series) to create a column of numbers from 1 to 10,000 in column F.
![Excel "Series" dialog box set to create a column series from 1 to 10000](video-frame://35@02:46)
![Excel spreadsheet with "Simulations" column filled from 0 to 10000](video-frame://35@03:00)

## [03:06] Running the Monte Carlo Simulation with Data Table

**Spoken content:**
- [03:06] So what I'm going to do, here's a little trick to do Monte Carlo simulation. Anything you can estimate,
- [03:12] you can do Monte Carlo simulation. Sounds super fancy, but it's not really. Here's what happens.
- [03:18] I'm going to highlight this entire column with the cells to the right. I'm going to go to the data
- [03:27] ribbon. And then do you see this what if analysis? We're going to do a data table. So the data table,
- [03:34] we could put two different inputs, a row and a column. Here I've got a column, but I don't want
- [03:39] it to use new numbers. I want it to just recalculate. So I'm going to use a blank cell.
- [03:45] I'm pointing to a blank cell. You see there's nothing in there. I want to hit OK. And it'll
- [03:50] take just a second to refresh. And what we'll see is that this number, this original profit is
- [03:59] then recalculated and simulated 10,000 times. Now, the cool thing about this is we can now

**On-screen content:** The speaker selects the range F4:G10004 (the 10,000 simulations and the linked profit cell).
![Excel spreadsheet with the "Simulations" and "Profit" columns selected](video-frame://35@03:20)
They then navigate to Data > What-If Analysis > Data Table. In the Data Table dialog, for "Column input cell", a blank cell (E5) is selected.
![Excel "Data Table" dialog box with a blank cell E5 selected as the Column input cell](video-frame://35@03:32)
After clicking OK, Excel calculates 10,000 different profit outcomes based on the randomized sales, variable costs, and fixed costs.
![Excel spreadsheet showing 10,000 simulated profit values in column G](video-frame://35@03:52)

## [04:04] Analyzing Simulation Results: Mean, Min, Max

**Spoken content:**
- [04:06] highlight this and do the mean and the min and the max and figure out what's our risk of loss.
- [04:12] And that what we're worried about that, we do not want to lose money or we want the risk of losing
- [04:18] money to be really small. So I'm going to select this entire column and I'm going to name it. This is
- [04:23] called a named range. So I can go to formulas and name manager and I can say, I want a new and I'm going
- [04:33] to call this profit. So I've just named this range to be called profit. So there it is.
- [04:42] We see it's G4 through G10,003. All right. So now for the mean, the mean is the average.
- [04:52] So the average, and I can just start typing in profit and you see it says, hey, do you want this
- [04:58] profit right there? Yes, I do. And you see it selects everything in blue. So what is the average
- [05:04] of all those profit numbers? Well, it's 109,789. What is the minimum? Well, the min of profit
- [05:15] is 173. And that's a loss because it's in parentheses. That's a negative number. So we're worried about a
- [05:25] loss. There's a negative. The worst of all the 10,000 is negative 173. So $173,000 loss.
- [05:33] For max, we can do the maximum number of profit. Well, that's 433. Do you see the minimum change a
- [05:43] little bit? Well, what percent of the time of these 10,000 do we have a loss? So here's what I want to

**On-screen content:** The speaker selects the entire column G (the simulated profits) and creates a named range called "profit" using Formulas > Name Manager.
![Excel "New Name" dialog box showing "profit" as the name for the selected range G4:G10004](video-frame://35@04:32)
Below the initial income statement, the speaker calculates the Mean, Min, and Max of the "profit" named range.
-   **Mean:** `=AVERAGE(profit)` results in $109,789.
-   **Min:** `=MIN(profit)` results in ($173,152), indicating a loss.
-   **Max:** `=MAX(profit)` results in $433,914.
![Excel spreadsheet showing calculated Mean, Min, and Max for the simulated profits](video-frame://35@05:40)

## [05:44] Calculating Risk of Loss and Impact of Changes

**Spoken content:**
- [05:50] do. I want to go to, I'm just going to do the number as a general number. I'm going to do count
- [05:57] ifs. Count ifs is a function. And it's going to say, what's the range and what's my criteria? Well,
- [06:05] the range is profit, comma, and then my risk of loss is anything. I need to start with a quote
- [06:14] less than zero. And quote again, close my brackets. And it says 740 times out of the 10,000
- [06:26] is how many times we're less than zero. So that would be the 749 losses. And you see every time
- [06:34] it's going to update, we know this. If I divide this by the 10,000, then I'll have some kind
- [06:41] of estimate. I need to make it a percentage. So about 7% of the time we would lose money in
- [06:49] this example. Now, if we change this, we change fixed costs from 150 to 200,000, the risk of loss
- [06:57] will go up. So now it's 21%. We're worried about the risk of loss. And that's how you do
- [07:06] the Monte Carlo simulation, 10,000 simulations. Excel can do it.

**On-screen content:** The speaker calculates the "Risk of Loss" using the `COUNTIFS` function.
-   **Risk of Loss:** `=COUNTIFS(profit,"<0")` counts the number of times profit was less than zero. This initially shows 749.
![Excel spreadsheet showing the COUNTIFS formula for risk of loss and its result](video-frame://35@06:21)
This count is then divided by 10,000 to get a percentage: `=COUNTIFS(profit,"<0")/10000`.
![Excel spreadsheet showing the risk of loss as a percentage (7.04%)](video-frame://35@06:44)
The speaker then changes the "Fixed Costs" mean from $150,000 to $200,000.
![Excel spreadsheet showing Fixed Costs mean changed to 200,000](video-frame://35@06:54)
This change automatically updates all simulations and recalculates the summary statistics. The "Risk of Loss" increases significantly to 21.35%.
![Excel spreadsheet showing updated Mean, Min, Max, and Risk of Loss (21.35%) after changing Fixed Costs](video-frame://35@07:00)
