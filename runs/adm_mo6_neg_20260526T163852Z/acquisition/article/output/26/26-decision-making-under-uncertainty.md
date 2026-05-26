---
id: "26"
title: "Decision Making Under Uncertainty"
source_url: "https://anvari.net/DecisionMaking/DecisionUncertainty.pdf"
fetch_url: "https://anvari.net/DecisionMaking/DecisionUncertainty.pdf"
resolved_url: "https://anvari.net/DecisionMaking/DecisionUncertainty.pdf"
firecrawl_title: "_tmp_chap10.dvi"
description: null
fetched_at: "2026-05-26T16:44:49.174388Z"
provider: "firecrawl"
strategy: "pdf"
cache_key: "bf4cccde32efa2b2bfa09f2ce40bf3cd7701a7fb16090b1b21aa06816ef6e198"
firecrawl_status_code: 200
firecrawl_content_type: "application/pdf"
word_count: 36693
char_count: 214572
content_sha256: "5ae34a2807773bc03bd15a861176d823e9eebedb024ed604d507e390210a626b"
image_count: 0
link_count: 0
warnings:
  - "missing_screenshot"
  - "very_long_content"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes:
  - "pdf_mode_auto"
---

Decision
Making
Under
Uncertainty
\[Image: Im1\]

ormal decision analysis in the face of uncertainty frequently occurs
at the most strategic levels of a companys planning process and
Ftypically involves teams of high-level managers from all areas of the
company. This is certainly the case with Du Pont, as reported by two
internal decision analysis experts, Krumm and Rolle (1992), in their article
Management and Application of Decision and Risk Analysis in Du Pont.
Du Ponts formal use of decision analysis began in the 1960s, but because
of a lack of computing power and distrust of the method by senior-level
management, it never really got a foothold. However, by the mid-1980s
things had changed considerably. The company was involved in a
faster-moving, more uncertain environment, more people throughout the
company were empowered to make decisions, and these decisions had to
be made more quickly. In addition, the computing power had arrived to
\[Image: Im1\]

* * *

make large-scale quantitative analysis feasible. Since that time, Du Pont has embraced formal decision-making analysis in all its businesses, and the trend is almost certain to continue. The article describes a typical example of decision analysis within the company. One of Du Ponts businesses, Business Z (so-called for reasons of confidentiality), was stagnating. It was not set up to respond quickly to changing customer demands, and its financial position was declining due to lower prices and market share. A decision board and a project team were empowered to turn things around. The project team developed a detailed timetable to accomplish three basic steps: frame the problem, assess uncertainties and perform the analysis, and implement the recommended deci- sion. The first step involved setting up a strategy table to list the possible strategies and the factors that would affect or be affected by them. The three basic strategies were (1) a base-case strategy (continue operating as is), (2) a product differentiation strategy (develop new products), and (3) a cost leadership strategy (shut down the plant and streamline the product line). In the second step, the team asked a variety of experts throughout the company for their assessments of the likelihood of key uncertain events. In the analysis step they then used all of the information gained to determine the strategy with the largest expected net present value. Two important aspects of this analysis step were the extensive use of sensitivity analysis (many what-if questions) and the emergence of new hybrid strat- egies that dominated the strategies that had been considered to that point. In partic- ular, the team finally decided on a product differentiation strategy that also decreased costs by shutting down some facilities in each plant. By the time of the third step, implementation, the decision board needed little convincing. Since all of the key people had been given the opportunity to provide input to the process, everyone was convinced that the right strategy had been selected. All that was left was to put the plan in motion and monitor its results. The results were impressive. Business Z made a complete turnaround, and its net present value in- creased by close to $200 million. Besides this tangible benefit, there were definite intangible benefits from the overall process. As Du Ponts vice president for finance said, The D&RA \[decision and risk analysis\] process improved communication within the business team as well as between the team and corporate management, resulting in rapid approval and execution. As a decision maker, I highly value such a clear and logical approach to making choices under uncertainty and will continue to use D&RA whenever possible. ■

## 10.1 INTRODUCTION

n this chapter we will provide a formal framework for analyzing decision prob- lems that involve uncertainty. We will discuss the most frequently used criteria for

# Ichoosing among alternative decisions, how probabilities are used in the decision-

making process, how decisions made at an early stage affect decisions made at a later stage, how a decision maker can quantify the value of information, and how attitudes toward risk can affect the analysis. Throughout, we will employ a powerful graphi- cal tooldecision treesto guide the analysis. A decision tree enables the decision maker to view all important aspects of the problem at once: the decision alternatives, the uncertain outcomes and their probabilities, the economic consequences, and the chronological order of events. We will show how to implement decision trees in Ex- cel by taking advantage of a very powerful and flexible add-in from Palisade called PrecisionTree.

Chapter 10 _Decision Making Under Uncertainty_

* * *

Many examples of decision making under uncertainty exist in the business world. Here are several examples.

■Companies routinely place bids for contracts to complete a certain project within a fixed time frame. Often these are sealed bids, where each of several companies presents in a sealed envelope a bid for completing the project; then the envelopes are opened, and the low bidder is awarded the bid amount to complete the project. Any particular company in the bidding competition must deal with the possible uncertainty of its actual cost of completing the project (should it win the bid), as well as the uncertainty involved in what the other companies will bid. The trade-off is between bidding low in order to win the bid and bidding high in order to make a profit. ■Whenever a company contemplates introducing a new product into the market, there are a number of uncertainties that affect the decision, probably the most important being the customers reaction to this product. If the product generates high customer demand, then the company will make a large profit. But if demand is low (and, after all, the vast majority of new products do poorly), then the company might not even recoup its development costs. Because the level of customer demand is critical, the company might try to gauge this level by test marketing the product in one region of the country. If this test market is a success, the company can then be more optimistic that a full-scale national marketing of the product will also be successful. But if the test market is a failure, the company can cut its losses by abandoning the product. ■Borison (1995) describes an application of formal decision analysis by Oglethorpe Power Corporation (OPC), a Georgia-based electricity supplier. The basic decision OPC faced was whether to build a new transmission line to supply large amounts of electricity to parts of Florida and, if they decided to build it, how to finance this project. OPC had to deal with several sources of uncertainty: the cost of building new facilities, the demand for power in Florida, and various market conditions, such as the spot price of electricity. ■Ulvila (1987) describes the decision analysis performed by the U.S. Postal Service regarding the purchase of automation equipment. One of the investment decisions was which type of OCR (optical character recognition) equipment the Postal Service should purchase (or convert) for reading single- and/or multiple-line addresses on packages. An important factor in this decision was the level of use by businesses of the zip+4 (nine-digit zip codes). Zip+4 usage had been recommended for some time but was used only sporadically. The Postal Service was uncertain about the future level of business zip+4 usage. If businesses used the nine-digit codes heavily in the future, then a certain type of (expensive) OCR equipment would be most economical. If business use of zip+4 did not increase, then purchasing this equipment would be a waste of money. The decision was an extremely important one, given the expense of the proposed equipment and the fact that the Postal Service would have to live with whatever equipment it purchased for a number of years. ■Utility companies must make many decisions that have significant environmental and economic consequences. \[Balson et al. (1992) provide a good discussion of such consequences.\] For these companies it is not necessarily enough to conform to federal or state environmental regulations. Recent court decisions have found companies liablefor huge settlementswhen accidents occurred, even though the companies followed all existing regulations. Therefore, when utility companies decide, say, whether to replace equipment or mitigate the effects of environmental

10.1 Introduction pollution, they must take into account the possible environmental consequences
(such as injuries to people) as well as economic consequences (such as lawsuits).
An aspect of these situations that makes decision analysis particularly difficult is that
the potential disasters are often extremely improbable; hence, their likelihoods
are very difficult to assess accurately.

10.2 ELEMENTS OF A DECISION ANALYSIS
A

lthough decision making under uncertainty occurs in a wide variety of contexts, all problems have three elements in common: (1) the set of decisions (or
Astrategies) available to the decision maker, (2) the set of possible outcomes
and the probabilities of these outcomes, and (3) a value model that prescribes results,
usually monetary values, for the various combinations of decisions and outcomes.
Once these elements are known, the decision maker can find an optimal decision,
depending on the optimality criterion chosen. Rather than discussing these elements in
the abstract, we introduce them in the context of the following extended example.

EXAMPLE

10.1

BIDDING FOR A GOVERNMENT CONTRACT
AT SCITOOLS

SciTools Incorporated, a company that specializes in scientific instruments, has been
invited to make a bid on a government contract. The contract calls for a specific number
of these instruments to be delivered during the coming year. The bids must be sealed (so
that no company knows what the others are bidding), and the low bid wins the contract.
SciTools estimates that it will cost $5000 to prepare a bid and $95,000 to supply the
instruments if it wins the contract. On the basis of past contracts of this type, SciTools
believes that the possible low bids from the competition, if there is any competition,
and the associated probabilities are those shown in Table 10.1. In addition, SciTools
believes there is a 30% chance that there will be no competing bids.

Lets discuss the three elements of SciTools problem. First, SciTools has two basic
strategies: submit a bid or do not submit a bid. If SciTools submits a bid, then it must
decide how much to bid. Based on SciTools cost to prepare the bid and its cost to
supply the instruments, there is obviously no point in bidding less than $100,000
SciTools wouldnt make a profit even if it won the bid. Although any bid amount over

TABLE 10.1 Data for Bidding Example

Greater than $125,000

Solution

| Low Bid | Probability |
| --- | --- |
| Less than $115,000 | 0.2 |
| Between $115,000 and $120,000 | 0.4 |
| Between $120,000 and $125,000 | 0.3 |
| Greater than $125,000 | 0.1 |

* * *

$100,000 might be considered, the data in Table 10.1 might persuade SciTools to limit
1
its choices to $115,000, $120,000, and $125,000.
The next element of the problem involves the uncertain outcomes and their proba-

The next element of the problem involves the uncertain outcomes and their probabilities. We have assumed that SciTools knows exactly how much it will cost to prepare
a bid and how much it will cost to supply the instruments if it wins the bid. (In reality, these are probably estimates of the actual costs.) Therefore, the only source of
uncertainty is the behavior of the competitorswill they bid, and if so, how much?
From SciTools standpoint, this is difficult information to obtain. The behavior of the
competitors depends on (1) how many competitors are likely to bid and (2) how the
competitors assess their costs of supplying the instruments. However, we will assume
that SciTools has been involved in similar bidding contests in the past and can, therefore, predict competitor behavior from past competitor behavior. The result of such
prediction is the assessed probability distribution in Table 10.1 and the 30% estimate
of the probability of no competing bids.
The last element of the problem is the value model that transforms decisions

The last element of the problem is the value model that transforms decisions
and outcomes into monetary values for SciTools. The value model is straightforward
in this example, but it can become quite complex in other applications, especially
when the time value of money is involved and some quantities (such as the costs of
environmental pollution) are difficult to quantify. If SciTools decides right now not to
bid, then its monetary value is $0no gain, no loss. If it makes a bid and is underbid by
a competitor, then it loses $5000, the cost of preparing the bid. If it bids B dollars and
wins the contract, then it makes a profit of B − $100,000, that is, B dollars for winning
the bid, less $5000 for preparing the bid, less $95,000 for supplying the instruments.
For example, if it bids $115,000 and the lowest competing bid, if any, is greater than
$115,000, then SciTools makes a profit of $15,000.
It is often convenient to list the monetary outcomes in a payoff table,asshown

It is often convenient to list the monetary outcomes in a payoff table,asshown
in Table 10.2. For each possible decision and each possible outcome, the payoff table
lists the monetary value to SciTools, where a positive value represents a profit and a
negative value represents a loss. At the bottom of the table, we list the probabilities of
the various outcomes. For example, the probability that the competitors low bid is less
than $115,000 is 0.7 (the probability of at least one competing bid) multiplied by 0.2
(the probability that the lowest competing bid is less than $115,000, given that there is
at least one competing bid).
It is sometimes possible to simplify payoff tables to better understand the essence

It is sometimes possible to simplify payoff tables to better understand the essence
of the problem. In the present example, if SciTools bids, then the only necessary
information about the competitors bid is whether it is lower or higher than SciTools

|  |  | Competitors' Low Bid($1000s) |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
|  |  | No Bid | <115 | >115,<120 | >120,<125 | >125 |
| SciTools' | No Bid | 0 | 0 | 0 | 0 | 0 |
| Bid($1000s) | 115 | 15 | -5 | 15 | 15 | 15 |
|  | 120 | 20 | -5 | -5 | 20 | 20 |
|  | 125 | 25 | -5 | -5 | -5 | 25 |
| Probability |  | 0.3 | 0.7(0.2) | 0.7(0.4) | 0.7(0.3) | 0.7(0.1) |

1
The problem with a bid such as $117,000 is that the data in Table 10.1 make it impossible to calculate the
probability of SciTools winning the contract if it bids this amount. Other than this, however, there is
nothing that rules out such an in-between bid.

* * *

bid. That is, SciTools cares only whether it wins the contract or not. Therefore, an alternative way of presenting the payoff table is shown in Table 10.3. The third and fourth columns of this table indicate the payoffs to SciTools, depend- ing on whether it wins or loses the bid. The rightmost column shows the probability that SciTools wins the bid for each possible decision. For example, if SciTools bids $120,000, then it wins the bid if there are no competing bids (probability 0.3) or if there are competing bids but the lowest of these is greater than $120,000 (proba- bility 0.7(0.3 + 0.1)). In this case the total probability that SciTools wins the bid is

0.3 + 0.28 = 0.58.
TABLE 10.3 **Alternative Payoff Table for SciTools Bidding Example**

## Monetary value

## Probability That

## SciTools Wins SciTools Loses SciTools Wins

**SciTools No bid** NA 0 0.00 **Bid 115** 15 −50.86 **($1000s) 120** 20 −50.58 **125** 25 −50.37

## Risk Profiles From Table 10.3 we can obtain risk profiles for each of SciTools deci-

sions. A risk profile simply lists all possible monetary values and their corresponding probabilities. For example, if SciTools bids $120,000, there are two monetary values possible, a profit of $20,000 or a loss of $5000, and their probabilities are 0.58 and

0.42, respectively. On the other hand, if SciTools decides not to bid, there is a sure monetary value of $0no profit, no loss. A risk profile can also be illustrated graphically as a bar chart. There is a bar above each possible monetary value with height proportional to the probability of that value. For example, the risk profile for a $120,000 bid decision is a bar chart with two bars, one above −$5000 with height 0.42 and one above $20,000 with height 0.58. The risk profile for the no bid decision is even simpler. It has a single bar above $0 with height 1. We have not shown these bar charts for this example because they are so simple, but in more complex examples they can provide very useful information.

## Expected Monetary Value (EMV) From the information we have discussed so far,

it is not at all obvious which decision SciTools should make. The no bid decision is certainly safe, but it is certain to make zero profit. If SciTools decides to bid, the probability that it will lose $5000 is smallest with the $115,000 bid, but this bid has the smallest potential profit. Of course, if SciTools knew what the competitors were going to do, its decision would be easy. However, this uncertainty is the defining aspect of the problems in this chapter. The decision must be made before the uncertainty is resolved. The most common way to make the choice is to calculate the expected monetary **value (EMV) of each alternative and then choose the alternative with the largest EMV.** The EMV is a weighted average of the possible monetary values, weighted by their probabilities. Formally, if v _i_ is the monetary value corresponding to outcome i and p _i_ is its probability, then EMV is defined as ∑ EMV = v _i_ _p_ _i_ In words, EMV is the mean of the probability distribution of possible monetary out- comes.

Chapter 10 _Decision Making Under Uncertainty_

* * *

TABLE 10.4 EMVs for SciTools Bidding Example

| Alternative | EMV Calculation | EMV |
| --- | --- | --- |
| No bid | 0(1) | $0 |
| Bid $115,000 | 15,000(0.86)+(-5000)(0.14) | $12,200 |
| Bid $120,000 | 20,000(0.58)+(-5000)(0.42) | $9,500 |
| Bid $125,000 | 25,000(0.37)+(-5000)(0.63) | $6,100 |

The EMVs for SciTools problem are listed in Table 10.4. They indicate that if
SciTools uses the EMV criterion for making its decision, it should bid $115,000, as
this yields the largest EMV.
It is very important to understand what an EMV implies and what it does not imply.

It is very important to understand what an EMV implies and what it does not imply.
If SciTools bids $115,000, then its EMV is $12,200. However, SciTools will certainly
not earn a profit of $12,200. It will earn $15,000 or it will lose $5000. So what does the
EMV of $12,200 really mean? It means that if SciTools could enter many gambles
like this, where on each gamble it would win $15,000 with probability 0.86 or lose
$5000 with probability 0.14, then on average it would win $12,200 per gamble. In
other words, the EMV can be interpreted as a long-term average.
It might seem peculiar, then, to base a one-time decision on EMV, which represents

other words, the EMV can be interpreted as a long-term average.
It might seem peculiar, then, to base a one-time decision on EMV, which represents
a long-term average. There are two ways to explain this apparent inconsistency. First,
most companies make frequent decisions under uncertainty. Although each decision
might have its own unique characteristics, it seems reasonable that if the company
plans to make many such decisions, it should be willing to play the averages, as
it does when it uses EMV as the decision criterion. Second, even if this is the only
such decision the company is ever going to make, decision theorists have proven that
under certain conditions, maximizing EMV is a rational basis for making this decision.
These certain conditions relate to the decision makers attitude toward risk. As we
will discuss later in this chapter, if the decision maker is risk averse and the possible
monetary payoffs or losses are large relative to her wealth, then EMV is not the
appropriate decision criterion to use. However, the EMV criterion has proved useful in
the vast majority of decision-making applications, so we will use it throughout most
of this chapter.
Decision Trees By now, we have gone through most of the steps of solving SciTools

Decision Tree Conventions To understand Figure 10.1, we need to know the following
conventions that have been established for decision trees.

Decision Trees By now, we have gone through most of the steps of solving SciTools
problem. We have listed the decision alternatives, the uncertain outcomes and their
probabilities, and the profits and losses from all combinations of decisions and outcomes. We have then calculated the EMV for each alternative and have chosen the
alternative with the largest EMV. All of this can be done efficiently using a graphical
tool called a decision tree. The decision tree that corresponds to SciTools problem
appears in Figure 10.1 (page 500). (This figure is actually part of an Excel spreadsheet
and was created with the PrecisionTree add-in. We will explain how it was created
shortly.)

1. Decision trees are composed of nodes (circles, squares, and triangles) and branches
   (lines).

2. The nodes represent points in time. A decision node (a square) is a time when the

3. The nodes represent points in time. A decision node (a square) is a time when the
   decision maker makes a decision. A probability node (a circle) is a time when the
   result of an uncertain event becomes known. An end node (a triangle) indicates


* * *

**FIGURE 10.1 Decision Tree for SciTools Bidding Example**

that the problem is completedall decisions have been made, all uncertainty has been resolved, and all payoffs/costs have been incurred.

**3.** Time proceeds from left to right. This means that any branches leading into a node (from the left) have already occurred. Any branches leading out of a node (to the right) have not yet occurred.
**4.** Branches leading out of a decision node represent the possible decisions; the de- cision maker can choose the preferred branch. Branches leading out of probability nodes represent the possible outcomes of uncertain events; the decision maker has no control over which of these will occur.
**5.** Probabilities are listed on probability branches. These probabilities are conditional on the events that have already been observed (those to the left). Furthermore, the probabilities on branches leading out of any particular probability node must sum to 1.
**6.** Individual monetary values are shown on the branches where they occur, and cumulative monetary values are shown to the right of the end nodes. (Actually, PrecisionTree shows two values to the right of each end node. The top one is the probability of getting to that end node, and the bottom one is the associated monetary value.) The decision tree in Figure 10.1 illustrates these conventions for a single-stage decision problem, the simplest type of decision problem. In a single-stage problem all decisions are made first, and then all uncertainty is resolved. Later in this chapter
Chapter 10 _Decision Making Under Uncertainty_ we will see multistage decision problems, where decisions and outcomes alternate. That is, a decision maker makes a decision, then some uncertainty is resolved, then the decision maker makes a second decision, then some further uncertainty is resolved, and so on. Because these multistage decisions problems are inherently more complex, we will focus initially on single-stage problems. Once a decision tree has been drawn and labeled with probabilities and monetary values, it can be solved easily. The solution for the decision tree in Figure 10.1 is shown in Figure 10.2. Among other things, it shows that the decision to bid $115,000 is optimal (follow the decision branches with True above them), with a corresponding EMV of $12,200 (the value under Bid? at the left of the tree). This is consistent with what we saw earlier for this example.

## Folding Back Procedure The solution procedure used to develop Figure 10.2 is called

**folding back on the tree. Starting at the right of the tree and working back to the left,** the procedure consists of two types of calculations.

**1.** At each probability node, we calculate the EMV (sum of monetary values times probabilities) and write it below the name of the node. For example, consider the node (top right) after SciTools decision to bid $115,000 and after it learns that
**FIGURE 10.2 Result of Folding Back to Obtain Optimal Decision**

10.2 Elements of a Decision Analysis there will be a competing bid. From that point, SciTools will either win $15,000 with probability 0.8 or lose $5000 with probability 0.2. The corresponding EMV is

0.8(15,000) + 0.2(−5000) = 11,000
and this value is entered below the node name Win bid?. Now, back up a step and consider the preceding probability node (the one to the left of the Win bid? node). At this point, SciTools has bid $115,000 and is about to discover whether there will be a competing bid. If there is none, with probability 0.3, then SciTools will win $15,000. But if there is a competing bid, with probability 0.7, the EMV from that point on is the $11,000 we just calculated. Essentially, this $11,000 summarizes the consequences of being at the Win bid? node, and SciTools acts the same as if it were going to receive $11,000 for certain. Therefore, the EMV for the Any competing bid? node is

0.3(15,000) + 0.7(11,000) = 12,200
This EMV is written below the node name.

**2.** Decision nodes are much easier. At each decision node we find the maximum of the EMVs and write it below the node name. PrecisionTree indicates the winner by placing True on the decision branch with the maximum EMV and False on all other branches emanating from this node. For example, consider the node where SciTools is deciding how much to bid (after already having decided to place a bid). The EMVs under the three succeeding probability nodes are $12,200, $9500, and $6100. Since the maximum of these is $12,200, the EMV for the How much to bid node is $12,200 and is written below the node name. After the folding-back process is completedthat is, after we have calculated EMVs for all nodeswe can trace the True labels from left to right to see the optimal strategy. In this case SciTools should place a bid, and it should be for $115,000. The EMV written below the leftmost decision node, $12,200, indicates SciTools EMV for this strategy. If SciTools is truly willing to use the EMV criterion, that is, if it is willing to play the averages, then the company should be indifferent between receiving $12,200 for certain and bidding $115,000with the associated risk of winning $15,000 or losing $5000.

## The PrecisionTree Add-In Decision trees present a challenge for Excel. We must

somehow take advantage of Excels calculating capabilities (to calculate EMVs, for example) and its graphical capabilities (to depict the decision tree). Fortunately, there is now a powerful add-in, PrecisionTree developed by Palisade Corporation, that makes the process relatively straightforward. 2 This add-in not only enables us to build and label a decision tree, but it performs the folding-back procedure automatically and then allows us to perform sensitivity analysis on key input parameters. The first thing you must do to use PrecisionTree is to add it in. You do this in two steps. First, you must install the Palisade Decision Tools suite (or at least the PrecisionTree program) with the Setup program on the CD-ROM accompanying this book. Of course, you need to do this only once. Then to run PrecisionTree, there are three options:

2 The educational version of PrecisionTree included with this book is slightly scaled down from Palisades commercial version of PrecisionTree. The difference you are most likely to notice is that the educational version permits only 50 nodesof all types combinedin a decision tree.

Chapter 10 _Decision Making Under Uncertainty_

* * *

FIGURE 10.3
Palisade Decision
Tools Toolbar

FIGURE 10.5
Inputs for SciTools
Bidding Example

■If Excel is not currently running, you can launch Excel and PrecisionTree by
clicking on the Windows Start button and selecting the PrecisionTree item from the
Palisade Decision Tools group of the Programs group.
If Excel is currently running, the procedure in the previous bullet will launch

■If Excel is currently running, the procedure in the previous bullet will launch
PrecisionTree on top of Excel.

■If Excel is already running and the Decision Tools toolbar in Figure 10.3 is showing,
you can start PrecisionTree by clicking on its icon (the third from the left).

\[Image: Im5\]

You will know that PrecisionTree is ready for use when you see its toolbar (shown
in Figure 10.4) and a PrecisionTree menu to the left of the Help menu. By the way, if you
want to unload PrecisionTree without closing Excel, use the PrecisionTree/Help/About
menu item and click on Unload. Its a bit unconventional, but it works.

Using PrecisionTree PrecisionTree is quite easy to useat least its most basic items
arebut it can be confusing at first. We will lead you through the steps for the SciTools
example. (The file SCITOOLS.XLS shows the results of this procedure, but you should
work through the steps on your own, starting with a blank spreadsheet.)

1. Inputs. Enter the inputs shown in columns A and B of Figure 10.5.

2. New tree. Click on the new tree button (the far left button) on the PrecisionTree

3. New tree. Click on the new tree button (the far left button) on the PrecisionTree
   toolbar, and then click on any cell (say, cell A14) below the input section to start
   a new tree. Click on the name box of this new tree (it probably says tree #1)
   to open a dialog box. Type in a descriptive name for the tree, such as SciTools
   Bidding, and click on OK. You should now see the beginnings of a tree, as shown
   in Figure 10.6 (page 504).

4. Decision nodes and branches. From here on, keep the finished tree in Figure 10.2

5. Decision nodes and branches. From here on, keep the finished tree in Figure 10.2
   in mind. This is the finished product we eventually want. To obtain decision nodes


|  | A | B | C |
| --- | --- | --- | --- |
| 1 | SciTools Bidding Example |  |  |
| 2 |  |  |  |
| 3 | Inputs |  |  |
| 4 | Cost to prepare a bid | $5,000 | Range namesBidCost: B4PrNoBid: B7ProdCost: B5 |
| 5 | Cost to supply instruments | $95,000 |  |
| 6 |  |  |  |
| 7 | Probability of no competing bid | 0.3 |  |
| 8 | Comp bid distribution (if they |  |  |
| 9 | <$115K | 0.2 |  |
| 10 | $115K to $120K | 0.4 |  |
| 11 | $120K to $125K | 0.3 |  |
| 12 | >$125K | 0.1 |  |

* * *

FIGURE 10.6
Beginnings of a New
Tree

FIGURE 10.7
Dialog Box for
Adding a New
Decision Node and
Branches

FIGURE 10.9
Decision Tree with
Decision Branches
Labeled

| 11 | $120K to $125K | 0.3 |
| --- | --- | --- |
| 12 | >$125K | 0.1 |
| 13 |  |  |
| 14 | SciTools Bidding | 1 |
| 15 |  | 0 |
| 16 |  |  |

and branches, click on the (only) triangle end node to open the dialog box in Figure
10.7. Click on the green square to indicate that this is a decision node, and fill in
the dialog box as shown. Were calling this decision Bid? and specifying that
there are two possible decisions. The tree expands as shown in Figure 10.8. The
boxes that say branch show the default labels for these branches. Click on either
of them to open another dialog box where you can provide a more descriptive
name for the branch. Do this to label the two branches No and Yes. Also, you
can enter the immediate payoff/cost for either branch right below it. Since there is
a $5000 cost of bidding, enter the formula

=-BidCost

right below the Yes branch in cell B19. (It is negative to reflect a cost.) The tree
should now appear as in Figure 10.9.
4\. More decision branches. The top branch is completed; if SciTools does not bid,

4. More decision branches. The top branch is completed; if SciTools does not bid,
   there is nothing left to do. So click on the bottom end node, following SciTools
   decision to bid, and proceed as in the previous step to add and label the decision node and three decision branches for the amount to bid. (Refer to Figure 10.2.) The tree to this point should appear as in Figure 10.10. Note that there are no monetary values below these decision branches because no immediate payoffs or costs are associated with the bid amount decision.

**5\. Probability nodes and branches. We now need a probability node and branches** from the rightmost end nodes to capture whether the competition bids. Click on the top one of these end nodes to bring up the same dialog box as in Figure 10.7. Now, however, click on the red circle box to indicate that this is a probability node. Label it Any competing bid?, specify two branches, and click on OK. Then label the two branches No and Yes. Next, repeat this procedure to form another probability node (with two branches) following the Yes branch, call it Win bid?, and label its branches as shown in Figure 10.11.

## 6\. Copying probability nodes and branches. You could now repeat the same pro-

cedure from the previous step to build probability nodes and branches following the other bid amount decisions, but because theyre structurally equivalent, you can save a lot of work by using PrecisionTrees copy and paste feature. Click on the leftmost probability node to open a dialog box and click on Copy. Then click on either end node to bring up the same dialog box and click on Paste. Do this again with the other end node. Decision trees can get very bushy, but this copy and paste feature can make them much less tedious to construct.

**FIGURE 10.10**

Tree with All Decision Nodes and Branches

**FIGURE 10.11 Decision Tree with One Set of Probability Nodes and Branches**

10.2 Elements of a Decision Analysis

* * *

## 7\. Labeling probability branches. You should now have the decision tree shown in

Figure 10.12. It is structurally the same as the completed tree in Figure 10.2, but

the probabilities and monetary values on the probability branches are not correct. Note that each probability branch has a value above and below the branch. The value above is the probability (the default values make the branches equally likely), and the value below is the monetary value (the default values are 0). We can enter any values or formulas in these cells, exactly as we do in typical Excel worksheets. As usual, it is a good practice to refer to input cells in these formulas whenever possible. Well get you started with the probability branches following the decision to bid $115,000. First, enter the probability of no competing bid in cell D18 with the formula

**=PrNoBid**

and enter its complement in cell D24 with the formula

**=1-D18**

Next, enter the probability that SciTools wins the bid in cell E22 with the formula

**=SUM(B10:B12)**

and enter its complement in cell E26 with the formula

**=1-E22**

**FIGURE 10.12 Structure of Completed Tree**

Chapter 10 _Decision Making Under Uncertainty_

* * *

(Remember that SciTools wins the bid only if the competitor bids higher, and in this part of the tree, SciTools is bidding $115,000.) For the monetary values, enter the formula

**=115000-ProdCost**

in the two cells, D19 and E23, where SciTools wins the contract. Note that we already subtracted the cost of the bid (cell B29), so we shouldnt do so again. This would be double-counting, and it should always be avoided in decision problems.

**8\. Enter the other formulas on probability branches. Using the previous step and**
Figure 10.2 as a guide, enter formulas for the probabilities and monetary values on
the other probability branches, that is, those following the decision to bid $120,000 or $125,000. Were finished! The completed tree in Figure 10.2 shows the best strategy and its associated EMV, as we discussed earlier. Note that we never have to perform the folding-back procedure manually. PrecisionTree does it for us. In fact, the tree is completed as soon as we finish entering the relevant inputs. In addition, if we change any of the inputs, the tree reacts automatically. For example, try changing the bid cost in cell B4 from $5000 to some large value such as $20,000. Youll see that the tree calculations update automatically, and the best decision is then not to bid, with an associated EMV of $0. **Risk Profile of Optimal Strategy** Once the decision tree is completed, PrecisionTree has several tools we can use to gain more information about the decision analysis. First, we can see a risk profile and other information about the optimal decision. To do so, click on the fourth button from the left on the PrecisionTree toolbar (it looks like a staircase) and fill in the resulting dialog box as shown in Figure 10.13. (You can experiment with other options.) The Policy Suggestion option allows us to see only that part of the tree that corresponds to the best decision, as shown in Figure 10.14 (page 508). The Risk Profile option allows us to see a graphical risk profile of the optimal decision. (If we checked the Statistics Report box, we would also see this information numerically.) As the risk profile in Figure 10.15 (page 508) shows, there are only two possible monetary outcomes if SciTools bids $115,000. It either wins $15,000 or loses $5000, and the former is much more likely. (The associated probabilities are 0.86 and
0.14.) This graphical information is even more useful when there are a larger number of possible monetary outcomes. We can see what they are and how likely they are.
**FIGURE 10.13**

Dialog Box for Information About Optimal Decision

10.2 Elements of a Decision Analysis

* * *

FIGURE 10.14
Subtree for Optimal
Decision

FIGURE 10.15
Risk Profile of
Optimal Decision

\[Image: Im16\]

\[Image: Im17\]

Sensitivity Analysis We have already stressed the importance of a follow-up sensitivity analysis for any decision problem, and PrecisionTree makes this relatively easy
to perform. First, we can enter any values into the input cells and watch how the tree
changes. But we can get more systematic information by clicking on PrecisionTrees
sensitivity button, the fifth from the left on the toolbar (it looks like a tornado). This
brings up the dialog box in Figure 10.16. It requires an EMV cell (and an optional
descriptive name) to analyze at the top and one or more input cells in the middle. The
specifications for these input cells are actually entered at the bottom of the dialog box.
The cell to analyze (at the top) is usually the EMV cell at the far left of the decision

The cell to analyze (at the top) is usually the EMV cell at the far left of the decision
treethis is the cell shown in the figurebut it can be any EMV cell. For example, if
we assume SciTools will prepare a bid and we want to see how sensitive the EMV from
that point on is to inputs, we could select cell C29 (refer to Figure 10.2) to analyze.
Next, for any input cell such as the production cost cell (B5), we enter a minimum
value, a maximum value, a base value (probably the original value in the model), and
a step size. For example, to specify these for the production cost, we clicked on the
Suggest Values button. This default setting varies the production cost by as much as
10% from the original value in either direction in a series of 10 steps. We can also enter
our own desired values. We did so for the probability of no competing bids, varying its
value from 0 to 0.6 in a sequence of 12 steps.
When we click on Run Analysis, PrecisionTree varies each of the specified inputs

* * *

**FIGURE 10.16**

Sensitivity Analysis Dialog Box

**FIGURE 10.17**

EMV versus Production Cost for Each of Two Decisions

(bid or dont bid). This type of graph is useful for seeing whether the optimal decision _changes over the range of the input variable. It does so only if the two lines cross. In_ this particular graph it is clear that the Bid decision dominates the No bid decision over the production cost range we selected. The Tornado sheet shows how sensitive the EMV of the optimal decision is to each of the selected inputs over the ranges selected. (See Figure 10.18 (page 510).) The length of each bar shows the percentage change in the EMV in either direction, so the longer the bar, the more sensitive this EMV is to the particular input. The bars are always arranged from longest on top to shortest on the bottomhence the name _tornado chart. Here we see that production cost has the largest effect on EMV, and bid_ cost has the smallest effect. Finally, the Spider Chart sheet contains the chart in Figure 10.19. It shows how much the optimal EMV varies in magnitude for various percentage changes in the input variables. The steeper the slope of the line, the more the EMV is affected by a particular input. We again see that the production cost has a relatively large effect, whereas the other two inputs have relatively small effects. Each time we click on the sensitivity button, we can run a different sensitivity analysis. An interesting option is to run a two-way analysis (by clicking on the Two

10.2 Elements of a Decision Analysis

* * *

**FIGURE 10.18**

Tornado Chart for SciTools Example

**FIGURE 10.19**

Spider Chart for SciTools Example

Way button in Figure 10.16). Then we see how the selected EMV varies as each pair of inputs vary simultaneously. We analyzed the EMV in cell C29 with this option, using the same inputs as before. A typical result is shown in Figure 10.20. For each of the possible values of production cost and the probability of no competitor bid, this chart indicates which bid amount is optimal. (By choosing cell C29, we are assuming SciTools will bid; the question is only how much.) As we see, the optimal bid amount remains $115,000 unless the production cost and the probability of no competing bid are both large. Then it becomes optimal to bid $125,000. This makes sense intuitively. As the chance of no competing bid increases and a larger production cost must be recovered, it seems reasonable that SciTools should increase its bid.

**FIGURE 10.20**

Two-Way Sensitivity Analysis

Chapter 10 _Decision Making Under Uncertainty_

* * *

We reiterate that a sensitivity analysis is always an important aspect in real decision
analyses. If we had to construct decision trees by handwith paper and pencila
sensitivity analysis would be virtually out of the question. We would have to recompute
everything each time through. Therefore, one of the most valuable features of the
PrecisionTree add-in is that it enables us to perform sensitivity analyses in a matter of
seconds. ■

PROBLEMS

Skill-Building Problems

1. The SweetTooth Candy Company knows it will need
   10 tons of sugar 6 months from now to implement its
   production plans. Jean Dobson, SweetTooths
   purchasing manager, has essentially two options for
   acquiring the needed sugar. She can either buy the
   sugar at the going market price when she needs it, 6
   months from now, or she can buy a futures contract
   now. The contract guarantees delivery of the sugar in
   6 months but the cost of purchasing it will be based
   on todays market price. Assume that possible sugar
   futures contracts available for purchase are for 5 tons
   or 10 tons only. No futures contracts can be purchased
   or sold in the intervening months. Thus, SweetTooths
   possible decisions are: (1) purchase a futures contract
   for 10 tons of sugar now, (2) purchase a futures
   contract for 5 tons of sugar now and purchase 5 tons
   of sugar in 6 months, or (3) purchase all 10 tons of
   needed sugar in 6 months. The price of sugar bought
   now for delivery in 6 months is $0.0851 per pound.
   The transaction costs for 5-ton and 10-ton futures
   contracts are $65 and $110, respectively. Finally, Ms.
   Dobson has assessed the probability distribution for
   the possible prices of sugar 6 months from now (in
   dollars per pound). Table 10.5 contains these possible
   prices and their corresponding probabilities.
   a. Given that SweetTooth wants to acquire the
   needed sugar in the least-cost way, formulate a

a. Given that SweetTooth wants to acquire the
needed sugar in the least-cost way, formulate a
payoff table that specifies the cost (in dollars)
associated with each possible decision and
possible sugar price in the future.
b. Use the PrecisionTree add-in to identify the

TABLE 10.5 Distribution of Possible
Sugar Prices

TABLE 10.6 Payoff Table for Carlisles Decision Problem

| Possible Sugar Prices in 6 Months($/pound) | Probability |
| --- | --- |
| 0.078 | 0.05 |
| 0.083 | 0.25 |
| 0.087 | 0.35 |
| 0.091 | 0.20 |
| 0.096 | 0.15 |

c. Generate a risk profile for SweetTooths optimal
decision.
2\. Carlisle Tire and Rubber, Inc. is considering

| Decision/Market Outcome | Market Expands | Market Stable | Market Contracts |
| --- | --- | --- | --- |
| Construct a new plant | 400,000 | -100,000 | -200,000 |
| Expand existing plant | 250,000 | -50,000 | -75,000 |
| Do nothing | 50,000 | 0 | -30,000 |

decision.
2\. Carlisle Tire and Rubber, Inc. is considering
expanding production to meet potential increases in
the demand for one of its tire products. Carlisles
alternatives are to construct a new plant, expand the
existing plant, or do nothing in the short run. The
market for this particular tire product may expand,

2. Carlisle Tire and Rubber, Inc. is considering
   expanding production to meet potential increases in
   the demand for one of its tire products. Carlisles
   alternatives are to construct a new plant, expand the
   existing plant, or do nothing in the short run. The
   market for this particular tire product may expand,

market for this particular tire product may expand,
remain stable, or contract. Carlisles marketing
department estimates the probabilities of these
market outcomes as 0.25, 0.35, and 0.40, respectively.
Table 10.6 contains Carlisles estimated payoff (in
dollars) table.

a. Use the PrecisionTree add-in to identify the
strategy that maximizes this tire manufacturers
expected profit. Also, perform sensitivity analysis
on the optimal decision and summarize your
findings. In response to which model inputs is the
expected profit value most sensitive?

* * *

b. Generate a risk profile for Carlisles optimal
decision.
3\. A local energy provider offers a landowner $180,000

decision.
3\. A local energy provider offers a landowner $180,000
for the exploration rights to natural gas on a certain
site and the option for future development. This
option, if exercised, is worth an additional $1,800,000
to the landowner, but this will occur only if natural
gas is discovered during the exploration phase. The
landowner, believing that the energy companys
interest in the site is a good indication that gas is
present, is tempted to develop the field herself. To do
so, she must contract with local experts in natural gas
exploration and development. The initial cost for
such a contract is $300,000, which is lost forever if
no gas is found on the site. If gas is discovered,
however, the landowner expects to earn a net profit of
$6,000,000. Finally, the landowner estimates the
probability of finding gas on this site to be 60%.
a. Formulate a payoff table that specifies the

a. Formulate a payoff table that specifies the
landowners payoff (in dollars) associated with
each possible decision and each outcome with
respect to finding natural gas on the site.
b. Use the PrecisionTree add-in to identify the

b. Use the PrecisionTree add-in to identify the
strategy that maximizes the landowners expected
net earnings from this opportunity. Also, perform
sensitivity analysis on the optimal decision and
summarize your findings. In response to which
model inputs is the expected profit value most
sensitive?
c. Generate a risk profile for landowners optimal

c. Generate a risk profile for landowners optimal
decision.
4\. Techware Incorporated is considering the

Table 10.7. The probabilities of observing a strong,
fair, and weak trend in the national economy in the
coming year are 0.30, 0.50, and 0.20, respectively.
a. Formulate a payoff table that specifies Techwares

decision.
4\. Techware Incorporated is considering the
introduction of two new software products to the
market. In particular, the company has four options
regarding these two proposed products: introduce
neither product, introduce product 1 only, introduce
product 2 only, or introduce both products. Research
and development costs for products 1 and 2 are
$180,000 and $150,000, respectively. Note that the
first option entails no costs because research and
development efforts have not yet begun. The success
of these software products depends on the trend of
the national economy in the coming year and
on the consumers reaction to these products.
The companys revenues earned by introducing
product 1 only, product 2 only, or both products in
various states of the national economy are given in

a. Formulate a payoff table that specifies Techwares
net revenue (in dollars) for each possible decision
and each outcome with respect to the trend in the
national economy.
b. Use the PrecisionTree add-in to identify the

b. Use the PrecisionTree add-in to identify the
strategy that maximizes Techwares expected net
revenue from the given marketing opportunities.
Also, perform sensitivity analysis on the optimal
decision and summarize your findings. In
response to which model inputs is the expected net
revenue value most sensitive?
c. Generate a risk profile for Techwares optimal

c. Generate a risk profile for Techwares optimal
decision.
5\. Consider an investor with $10,000 available to invest.

5. Consider an investor with $10,000 available to invest.
   He has the following options regarding the allocation
   of his available funds: (1) he can invest in a risk-free
   savings account with a guaranteed 3% annual rate of
   return; (2) he can invest in a fairly safe stock, where
   the possible annual rates of return are 6%, 8%, or
   10%; or (3) he can invest in a more risky stock where
   the possible annual rates of return are 1%, 9%, or
   17%. Note that the investor can place all of his
   available funds in any one of these options, or he can
   split his $10,000 into two $5000 investments in
   any two of these options. The joint probability
   distribution of the possible return rates for the two
   stocks is given in Table 10.8.
   a. Formulate a payoff table that specifies this

TABLE 10.7 Revenue Table for Techwares Decision Problem

| Decision/Trend in National Economy | Strong | Fair | Weak |
| --- | --- | --- | --- |
| Introduce neither product | $0 | $0 | $0 |
| Introduce product 1 only | $500,000 | $260,000 | $120,000 |
| Introduce product 2 only | $420,000 | $230,000 | $110,000 |
| Introduce both products | $820,000 | $390,000 | $200,000 |

b. Use the PrecisionTree add-in to identify the
strategy that maximizes the investors expected
earnings in one year from the given investment
opportunities. Also, perform sensitivity analysis
on the optimal decision and summarize your
findings. In response to which model inputs is the
expected earnings value most sensitive?
c. Generate a risk profile for this investors optimal

c. Generate a risk profile for this investors optimal
decision.
6\. A buyer for a large department store chain must place

decision.
6\. A buyer for a large department store chain must place
orders with an athletic shoe manufacturer 6 months
prior to the time the shoes will be sold in the
department stores. In particular, the buyer must

* * *

TABLE 10.8 Joint Probability Distribution of Safe and Risky
Stock Return Rates

| Safe Stock Return Rates(S)/Risky Stock Return Rates(R) | R=1% | R=9% | R=17% |
| --- | --- | --- | --- |
| S=6% | 0.10 | 0.05 | 0.10 |
| S=8% | 0.25 | 0.05 | 0.20 |
| S=10% | 0.10 | 0.05 | 0.10 |

decide on November 1 how many pairs of the
manufacturers newest model of tennis shoes to order
for sale during the upcoming summer season.
Assume that each pair of this new brand of tennis
shoes costs the department store chain $45 per pair.
Furthermore, assume that each pair of these shoes can
then be sold to the chains customers for $70 per pair.
Any pairs of these shoes remaining unsold at the end
of the summer season will be sold in a closeout sale
next fall for $35 each. The probability distribution of
consumer demand for these tennis shoes (in hundreds
of pairs) during the upcoming summer season has
been assessed by market research specialists and is
provided in Table 10.9. Finally, assume that the
department store chain must purchase these tennis
shoes from the manufacturer in lots of 100 pairs.

TABLE 10.9 Distribution of
Consumer Demand
for Tennis Shoes
Consumer

a. Formulate a payoff table that specifies the
contribution to profit (in dollars) from the sale of
the tennis shoes by this department store chain for
each possible purchase decision (in hundreds of
pairs) and each outcome with respect to consumer
demand.
b. Use the PrecisionTree add-in to identify the

| Consumer Demand | Probability |
| --- | --- |
| 1 | 0.025 |
| 2 | 0.050 |
| 3 | 0.075 |
| 4 | 0.100 |
| 5 | 0.150 |
| 6 | 0.200 |
| 7 | 0.175 |
| 8 | 0.100 |
| 9 | 0.075 |
| 10 | 0.050 |

subsequently selling pairs of the new tennis shoes.
Also, perform sensitivity analysis on the optimal
decision and summarize your findings. In
response to which model inputs is the expected
earnings value most sensitive?
c. Generate a risk profile for the buyers optimal

c. Generate a risk profile for the buyers optimal
decision.

Skill-Extending Problems

7. In designing a new space vehicle, NASA needs to
   decide whether to provide 0, 1, or 2 backup systems
   for a critical component of the vehicle. The first
   backup system, if included, comes into use only if the
   original system fails. The second backup system, if
   included, comes into use only if the original system
   and the first backup system both fail. NASA
   engineers claim that each system, independently of
   the others, has a 1% chance of failing if called into
   use. Each backup system costs $70,000 to produce
   and install within the vehicle. Once the vehicle is in
   flight, the mission will be scrubbed only if the
   original system and all backups fail. The cost of a
   scrubbed mission, in addition to production costs, is
   assessed to be $8,000,000.
   a. Use the PrecisionTree add-in to identify the
   strategy that minimizes NASAs expected total

assessed to be $8,000,000.
a. Use the PrecisionTree add-in to identify the
strategy that minimizes NASAs expected total
cost. Also, perform sensitivity analysis on the
optimal decision and summarize your findings. In
response to which model inputs is the expected
earnings value most sensitive?
b. Generate a risk profile for NASAs optimal

b. Generate a risk profile for NASAs optimal
decision.
8\. Mr. Maloy has just bought a new $30,000 sport utility

decision.
8\. Mr. Maloy has just bought a new $30,000 sport utility
vehicle. As a reasonably safe driver, he believes that
there is only about a 5% chance of being in an
accident in the forthcoming year. If he is involved in
an accident, the damage to his new vehicle depends
on the severity of the accident. The probability
distribution for the range of possible accidents and
the corresponding damage amounts (in dollars) are
given in Table 10.10 (page 514). Mr. Maloy is trying
to decide whether he is willing to pay $170 each year
for collision insurance with a $300 deductible. Note
that with this type of insurance, he pays the first $300
in damages if he causes an accident and the insurance
company pays the remainder.

* * *

TABLE 10.10 Distribution of Accident
Types and Corresponding
Damage Amounts

| Type of Accident | Conditional Probability | Damage to Vehicle |
| --- | --- | --- |
| Minor | 0.60 | $200 |
| Moderate | 0.20 | $1,000 |
| Serious | 0.10 | $4,000 |
| Catastrophic | 0.10 | $30,000 |

a. Formulate a payoff table that specifies the cost (in
dollars) associated with each possible decision
and type of accident.
b. Use the PrecisionTree add-in to identify the

b. Use the PrecisionTree add-in to identify the
strategy that minimizes Mr. Maloys annual
expected total cost. Also, perform sensitivity
analysis on the optimal decision and summarize
your findings. In response to which model inputs
is the expected earnings value most sensitive?
c. Generate a risk profile for Mr. Maloys optimal

c. Generate a risk profile for Mr. Maloys optimal
decision.
9\. The purchasing agent for a microcomputer manu-

TABLE 10.11 Distribution of Defective
Components in a Lot

decision.
9\. The purchasing agent for a microcomputer manufacturer is currently negotiating a purchase agreement
for a particular electronic component with a given
supplier. This component is produced in lots of
1000, and the cost of purchasing a lot is $30,000.
Unfortunately, past experience indicates that this
supplier has occasionally shipped defective components to its customers. Specifically, the proportion
of defective components supplied by this supplier is
described by the probability distribution given in
Table 10.11. While the microcomputer manufacturer
can repair a defective component at a cost of $20

Proportion of Defective
Components

| Components | Probability |
| --- | --- |
| 0.05 | 0.50 |
| 0.10 | 0.25 |
| 0.25 | 0.15 |
| 0.50 | 0.10 |

each, the purchasing agent is intrigued to learn that
this supplier will now assume the cost of replacing
defective components in excess of the first 100 faulty
items found in a given lot. This guarantee may be
purchased by the microcomputer manufacturer prior
to the receipt of a given lot at a cost of $1000 per lot.
The purchasing agent is interested in determining
whether it is worthwhile for her company to purchase
the suppliers guarantee policy.
a. Formulate a payoff table that specifies the

a. Formulate a payoff table that specifies the
microcomputer manufacturers total cost (in
dollars) of purchasing and repairing (if necessary)
a complete lot of components for each possible
decision and each outcome with respect to the
proportion of defective items.
b. Use the PrecisionTree add-in to identify the

b. Use the PrecisionTree add-in to identify the
strategy that minimizes the expected total cost
of achieving a complete lot of satisfactory
microcomputer components. Also, perform
sensitivity analysis on the optimal decision and
summarize your findings. In response to which
model inputs is the expected earnings value most
sensitive?
c. Generate a risk profile for the purchasing agents

ll applications of decision making under uncertainty follow the procedures
discussed so far. We first identify the possible decision alternatives, assess
Arelevant probabilities, and calculate monetary values. Then we use a decision
tree (or influence diagram) to identify the alternative with the largest EMV and follow
this up with a thorough sensitivity analysis. We can also examine the risk profiles
for the various alternatives. This is particularly useful if criteria other than EMV
maximization are considered, as we will discuss in Section 7.8. In this section we will
illustrate the process with several single-stage examples, where the decision maker
makes one decision and then learns which of several uncertain outcomes occurs. In
the next section we will examine multistage examples, where two or more sequential
decisions must be made.
The following example illustrates a decision problem most of us face on an annual

The following example illustrates a decision problem most of us face on an annual
basis, although most of us probably do not go to the trouble of analyzing it formally.

10.3 MORE SINGLE-STAGE EXAMPLES
A

c. Generate a risk profile for the purchasing agents
optimal decision.

* * *

10.2

SELECTING HEALTH CARE PLANS
AT STATE UNIVERSITY

Each year employees at State University are asked to decide on one of three health care
3
plans. The terms of these are as follows:

Plan 1: The monthly cost is $24. There is a $500 deductible. The participant pays
all expenses until payments for the year equal $500. After that, 90% of remaining
expenses are paid by the insurer.
Plan 2: This is the same as plan 1, except that the monthly cost is $1 and the

Plan 2: This is the same as plan 1, except that the monthly cost is $1 and the
deductible amount is $1000.
Plan 3: The monthly cost is $20. There is no deductible. The employee pays 30%

Plan 3: The monthly cost is $20. There is no deductible. The employee pays 30%
of all medical expenses. The rest is paid by the insurer.

Which of these three plans should an employee choose?

Solution

Clearly, the solution will vary from one employee to another, depending on the assessed
probability distribution of medical expenses. To illustrate, however, we will consider
an employee who assesses the distribution of yearly medical expenses shown in Table
10.12. These expenses include hospital visits, surgery, office visits, and prescriptions,
all of which are covered under the terms of the plans. As in the previous example, this
distribution is only an approximation of the real distribution, which would contain a
continuum of expenses. However, it is probably adequate for making a decision among
the three plans.

TABLE 10.12 Distribution of Medical Expenses
for Insurance Example

24(12)+500+0.1(100)=5798

However, if this employees medical expenses are only $200, then the cost is

| Total Medical Expense | Probability |
| --- | --- |
| $200 | 0.30 |
| $600 | 0.50 |
| $1000 | 0.15 |
| $5000 | 0.03 |
| $15,000 | 0.02 |

24(12)+200=\ 5488

* * *

The costs for the other plans and other outcomes can be calculated in a similar manner.
We list all of the costs in Table 10.13.
The choice is certainly not clear from this table. The plan with the lowest premium,

FIGURE 10.21
Inputs and Cost
Table for Medical
Example

The choice is certainly not clear from this table. The plan with the lowest premium,
plan 2, looks good if the years medical expenses are low. This is also true for the nodeductible plan, plan 3, although its cost is quite large in case of a disaster. For moderate
medical expenses, plan 1 is obviously inferior, but it is the best for guarding against a
disaster. These trade-offs could be illustrated by risk profiles, which you might want to
examine. Instead, we turn directly to the decision tree.

| Medical Expense | Plan 1 | Plan 2 | Plan 3 |
| --- | --- | --- | --- |
| $200 | $488 | $212 | $300 |
| $600 | $798 | $612 | $420 |
| $1000 | $838 | $1012 | $540 |
| $5000 | $1238 | $1412 | $1740 |
| $15,000 | $2238 | $2412 | $4740 |

USING PRECISIONTREE

The decision tree can be formed with the following steps.
●

●1 Inputs. Enter the inputs for the three plans and the probabilities from Table 10.12
in the top left portion of the spreadsheet (down to row 15). (See Figure 10.21 and the
file MEDICAL.XLS.)
●Cost table. For later use in the decision tree, calculate the costs to the employee

●2 Cost table. For later use in the decision tree, calculate the costs to the employee
(not counting insurance premiums) in the range B19:D23. To do this, enter the formula
=IF($A19<=B$6,$A19,B$6+B$7\*($A19-B$6))

|  | A | B | C | D |
| --- | --- | --- | --- | --- |
| 1 | Medical insurance problem |  |  |  |
| 2 |  |  |  |  |
| 3 | Inputs for plans |  |  |  |
| 4 |  | Plan1 | Plan2 | Plan3 |
| 5 | Monthly cost | $24 | $1 | $20 |
| 6 | Deductible | $500 | $1,000 | $0 |
| 7 | Copay Pot | 10% | 10% | 30% |
| 8 |  |  |  |  |
| 9 | Distribution of medical expenses |  |  |  |
| 10 |  | Expense | Prob |  |
| 11 |  | $200 | 0.3 |  |
| 12 |  | $600 | 0.5 |  |
| 13 |  | $1,000 | 0.15 |  |
| 14 |  | $5,000 | 0.03 |  |
| 15 |  | $15,000 | 0.02 |  |
| 16 |  |  |  |  |
| 17 | Out of pocket cost table (plan along top, expense along side), not including premiums |  |  |  |
| 18 |  | Plan1 | Plan2 | Plan3 |
| 19 | $200 | $200 | $200 | $60 |
| 20 | $600 | $510 | $600 | $180 |
| 21 | $1,000 | $550 | $1,000 | $300 |
| 22 | $5,000 | $950 | $1,400 | $1,500 |
| 23 | $15,000 | $1,950 | $2,400 | $4,500 |

* * *

in cell B19 and copy this to the range B19:D23. This IF function says that if the medical expense is less than the deductible, the employee pays it all. Otherwise, the employee pays the deductible amount plus a percentage of the remainder.

● **3 Decision tree. Use PrecisionTree to create the decision tree shown in Figure**

10.22. Here are some tips. First, create the decision node and decision branches, and enter formulas for their values as 12 times the relevant monthly premiums. Then create a single probability node and its branches, label the branches, and enter formulas for the probabilities with absolute references. For example, enter the formula **=$C$11** for the probability of the top branch. Next, copy the probability node to the end nodes below it. (Do you see the effect of the absolute references?) Finally, link the values for all of the probability branches to the cells in the cost table. (We know of no quick way to do this. We entered 15 separate formulas, one for each branch. However, it is much easier to create a cost table and link branch formulas to it than to create the branch formulas directly from input values.) ●

## 4 Minimize costs. If we quit here, we would mistakenly choose the worst of the

three plans. This is because PrecisionTree maximizes EMV by default, and in this problem we want to minimize the EMV of the costs. However, this is simple to change. Click on the name box at the far left in the decision tree. This brings up a dialog box (not shown here) where we can select the Minimize option.

**FIGURE 10.22**

Decision Tree for Medical Insurance Example

10.3 More Single-Stage Examples

* * *

As we see from Figure 10.22, the optimal plan is plan 3. Its EMVan expected
costis $528. The EMVs for plans 1 and 2 are $753 and $612. Evidently, this employees chances of large medical expenses where plan 3 is at its worst are not large
enough to outweigh plan 3s no-deductible benefit. However, we might want to experiment with various inputs, either the properties of the plans or the employees medical
expense distribution, to see whether plan 3 continues to be the preferred plan. For example, if the probabilities in Table 10.12 change to 0.30, 0.40, 0.15, 0.10, and 0.05, so that
large expenses are much more probable, the EMVs for the three plans become $827,
$722, and $750. Now plan 2 is preferred, although the difference in EMV between
plans 2 and 3 is quite small.
We can use this insurance example to illustrate one nonmonetary aspect of decision

We can use this insurance example to illustrate one nonmonetary aspect of decision
problems that is difficult to incorporate into a decision tree. At the university where
we teach, there is another insurance plan in addition to the types in the example.
Its premiums are low, and there are no copaymentsthe insurer pays all medical
expenses. This plan is clearly the cheapest of all plans offered, but it is not chosen
by many employees. Why? The plan is through an HMO, where all employees must
go to a specified set of physicians; otherwise, the plan does not pay their expenses.
Evidently, many employees believe that the cost of having to go to physicians they
would not choose otherwise outweighs the dollar savings from the plan. ■

The following example illustrates one method for using a continuous probability
distribution in a decision tree model.

EXAMPLE

Solution

10.3

Let p be the percentage of lightbulbs that are defective. Then the profit to FreshWay
from buying from supplier A is
{

FreshWay, a chain of supermarkets, requires 24,000 fluorescent lightbulbs for its stores.
There are two suppliers of these lightbulbs. Supplies A offers them at $4.00 per bulb
and will replace the first 900 defective bulbs with guaranteed good ones for $3.00 each.
It will replace all defectives after the first 900 for nothing. Supplier B is similar. It will
charge $4.15 per bulb, replace the first 1200 defectives for $1.00 each, and replace all
defectives after the first 1200 for nothing. FreshWay plans to sell these lightbulbs for
$4.40 apiece and charge its customers nothing for replacement of defectives. The only
uncertainty is the number of defective bulbs from either supplier. Based on historical
data from each supplier, FreshWay believes that the percentage of defectives is normally
distributed with mean 4% and standard deviation 1% from supplier A, and mean 4.2%
and standard deviation 1.2% from supplier B. Which supplier should be chosen to
maximize FreshWays EMV?

PURCHASING LIGHTBULBS AT FRESHWAY
SUPERMARKETS

\\mathrm{P r o f i t}=\\left{\\begin{array}{l l}{24,000(4.40-4.00)-(24,000p)(3.00)}&{\\mathrm{i f ~~}p\\leq900/24,000}\ {24,000(4.40-4.00)-(900)(3.00)}&{\\mathrm{i f~~}p>900/24,000}\\end{array}\\right.

A similar expression holds for supplier B. The only random quantity in this expression
is p, which is normally distributed. The question is how we can model the continuous
distribution of p in a discrete decision treethat is, a tree with a discrete number

* * *

FIGURE 10.23
Inputs and
Calculations for
Lightbulb Example

of probability branches. The method usually used is to approximate the continuous
normal distribution by a discrete distribution with a relatively small number, say 5, of
equally likely values.
The idea is to divide the normal distribution into an equal number of equal proba-

The idea is to divide the normal distribution into an equal number of equal probability regions and take the midpoint (in a probability sense) of each region as a value for
the decision tree. For example, if we use five points, then each region has probability
0.2. The probability halfway between 0 and 0.2 is 0.1, so the first point on the tree
is the 10th percentile of the normal distribution. Similarly, the next point is the 30th
percentile, the next is the 50th, the next is the 70th, and the last is the 90th.
Figure 10.23 illustrates the calculations. (See the file LIGHTBULB.XLS.) Through

Figure 10.23 illustrates the calculations. (See the file LIGHTBULB.XLS.) Through
row 13 we enter the given inputs for the problem. Then in rows 1726 we enter the
information well use in the decision tree regarding the percentage defective for each
supplier. This information is based on the five-point approximation to the normal
distribution. For example, the 10th percentile of the normal distribution for supplier A
is found in cell C17 with the formula

=NORMINV(B17,$B$12,$C$12)

and this is copied down to cell C21. Then the cost to FreshWay from defectives,
assuming the value in C17 is the percentage of defectives, is calculated in cell D17
with the formula

=$C$7 _IF(C17<=$D$7/Quantity,Quantity_ C17,$D$7)

and it is copied down to cell D21. Similar formulas are used for supplier B.

USING PRECISIONTREE

|  | A | B | C | D |
| --- | --- | --- | --- | --- |
| FreshWay lightbulb purchasing example |  |  |  |  |
| 2 |  |  | Range namesQuantity: B3SellingPrice: B4 |  |
| 3 | Quantity | 24000 |  |  |
| 4 | Selling price | $4.40 |  |  |
| 5 |  |  |  |  |
| 6 |  | UnitCost | ReplaceCost | Charge for first: |
| 7 | Supplier A | $4.00 | $3.00 | 900 |
| 8 | Supplier B | $4.15 | $1.00 | 1200 |
| 9 |  |  |  |  |
| 10 | Distribution of percent defective: normal |  |  |  |
| 11 |  | Mean | Stdev |  |
| 12 | Supplier A | 4.0% | 1.0% |  |
| 13 | Supplier B | 4.2% | 1.2% |  |
| 14 |  |  |  |  |
| 15 | Percentages to use on decision tree |  |  |  |
| 16 |  | Midpoint probability | Percentile | FreshWay's cost |
| 17 | Supplier A | 0.1 | 2.72% | $1,957.28 |
| 18 |  | 0.3 | 3.48% | $2,502.43 |
| 19 |  | 0.5 | 4.00% | $2,700.00 |
| 20 |  | 0.7 | 4.52% | $2,700.00 |
| 21 |  | 0.9 | 5.28% | $2,700.00 |
| 22 | Supplier B | 0.1 | 2.66% | $638.91 |
| 23 |  | 0.3 | 3.57% | $856.97 |
| 24 |  | 0.5 | 4.20% | $1,008.00 |
| 25 |  | 0.7 | 4.83% | $1,159.03 |
| 26 |  | 0.9 | 5.74% | $1,200.00 |

It is now straightforward to construct the decision tree shown in Figure 10.24 (page 520).
We enter the revenue from selling the bulbs and the cost of purchasing them in cells
B33 and B47. For example, the formula in cell B33 is

=Quantity\*(SellingPrice-B7)

* * *

FIGURE 10.24
Decision Tree for
Lightbulb Example

FIGURE 10.25
Tornado Chart to
Analyze the EMV
for Supplier B

Then we link the monetary values below the probability branches to the relevant cells
in the D17:D26 range.
The EMVs for suppliers A and B are $7088 and $5027, so supplier A is the clear

in the D17:D26 range.
The EMVs for suppliers A and B are $7088 and $5027, so supplier A is the clear
choice. Evidently, the higher price charged by supplier B and its slightly higher mean
percentage of defects outweigh its better deal on replacing defectives. Of course, if
supplier B really wants to get FreshWays business, it could attempt to sweeten its deal
in a number of ways. Sensitivity analysis is useful to see how the EMV for supplier
B (in cell C47) is affected by the various input parameters. We tried this, varying the
inputs in cells B8, C8, D8, and B13 by PrecisionTrees default values (10% in either
direction) and keeping track of the change in the EMV for supplier B. The tornado chart
in Figure 10.25 makes it very clear that the most important input is the unit purchase
cost. The effects of the other three inputs are practically negligible in comparison. If
supplier B wants FreshWays business, it will have to lower its unit purchase cost.

\[Image: Im27\]

* * *

MODELING ISSUES

The discrete approximation used in Example 10.3 can be used in any decision tree
with continuous probability distributions, regardless of whether they are normal. We
first need to decide how many values to have in the discrete approximation. The usual
choices are 5 or 3. (Surprisingly, a three-point approximation does an adequate job

choices are 5 or 3. (Surprisingly, a three-point approximation does an adequate job
in many situations.) Then we need to use the inverse functionin the previous
example it was the NORMINV functionto find the values to use in the decision tree.
The appropriate inverse function is available in Excel for a number of widely used
continuous distributions. ■

choices are 5 or 3. (Surprisingly, a three-point approximation does an adequate job
in many situations.) Then we need to use the inverse functionin the previous
example it was the NORMINV functionto find the values to use in the decision tree.
The appropriate inverse function is available in Excel for a number of widely used
■

PROBLEMS

Skill-Building Problems

10. Each day the manager of a local bookstore must
    decide how many copies of the community
    newspaper to order for sale in her shop. She must
    pay the newspapers publisher $0.40 for each
    copy and sells the newspapers to local residents
    for $0.50 each. Newspapers that are unsold at
    the end of day are considered worthless. The
    probability distribution of the number of copies of
    the newspaper purchased daily at her shop is
    provided in Table 10.14. Employ a decision tree to
    find the bookstore managers profit-maximizing
    daily order quantity.

TABLE 10.14 Distribution of Daily Local
Newspaper Demand

11. Two construction companies are bidding against one
    another for the right to construct a new community
    center building in Lewisburg, Pennsylvania. The first
    construction company, Fine Line Homes, believes
    that its competitor, Buffalo Valley Construction, will
    place a bid for this project according to the
    distribution shown in Table 10.15. Furthermore,
    Fine Line Homes estimates that it will cost $160,000
    for its own company to construct this building.
    Given its fine reputation and long-standing service

| TABLE 10.14 | Distribution of Daily Local Newspaper Demand |  |
| --- | --- | --- |
| Daily Demand for Local Newspaper | Probability |  |
| 10 | 0.10 |  |
| 11 | 0.15 |  |
| 12 | 0.30 |  |
| 13 | 0.20 |  |
| 14 | 0.15 |  |
| 15 | 0.10 |  |

TABLE 10.15 Distribution of Possible
Competing Bids for
Construction Project

| Buffalo Valley Construction's Bid | Probability |
| --- | --- |
| $160,000 | 0.40 |
| $165,000 | 0.30 |
| $170,000 | 0.20 |
| $175,000 | 0.10 |

within the local community, Fine Line Homes
believes that it will likely be awarded the project in
the event that it and Buffalo Valley Construction
submit exactly the same bids. Employ a decision
tree to identify Fine Line Homes profit-maximizing
bid for the new community center building.
12\. Suppose that you have sued your employer for

bid for the new community center building.
12\. Suppose that you have sued your employer for
damages suffered when you recently slipped and fell
on an icy surface that should have been treated by
your companys physical plant department.
Specifically, your injury resulting from this accident
was sufficiently serious that you, in consultation
with your attorney, decided to sue your company for
$500,000. Your companys insurance provider has
offered to settle this suit with you out of court. If
you decide to reject the settlement and go to court,
your attorney is confident that you will win the case
but is uncertain about the amount the court will
award you in damages. He has provided his
assessment of the probability distribution of the
courts award to you in Table 10.16 (page 522). Let
S be the insurance providers proposed out-of-court
settlement (in dollars). For which values of S will
you decide to accept the settlement? For which
values of S will you choose to take your chances in
court? Of course, you are seeking to maximize the
expected payoff from this litigation.

* * *

| Amount of Court Award | Probability |
| --- | --- |
| $0 | 0.025 |
| $50,000 | 0.075 |
| $100,000 | 0.100 |
| $200,000 | 0.125 |
| $300,000 | 0.175 |
| $400,000 | 0.200 |
| $500,000 | 0.300 |

13. Suppose that one of your colleagues has $2000
    available to invest. Assume that all of this money
    must be placed in one of three investments: a
    particular money market fund, a stock, or gold. Each
    dollar your colleague invests in the money market
    fund earns a virtually guaranteed 12% annual return.
    Each dollar he invests in the stock earns an annual
    return characterized by the probability distribution
    provided in Table 10.17. Finally, each dollar he
    invests in gold earns an annual return characterized
    by the probability distribution given in Table 10.18.
    a. If your colleague must place all of his available

TABLE 10.17 Distribution of Annual
Returns for Given Stock

| Annual Returns for Gold | Probability |
| --- | --- |
| -36% | 0.10 |
| -12% | 0.20 |
| 12% | 0.40 |
| 36% | 0.20 |
| 60% | 0.10 |

b. Suppose now that your colleague can place all of
his available funds in one of these three
investments as before, or he can invest $1000 in
one alternative and $1000 in another. Assuming
that he seeks to maximize his expected total
earnings in one year, how should he allocate his
$2000?

14. A home appliance company is interested in
    marketing an innovative new product. The company
    must decide whether to manufacture this product
    essentially on its own or employ a subcontractor to
    manufacture it. Table 10.19 contains the estimated
    probability distribution of the cost of manufacturing
    1 unit of this new product (in dollars) under the
    alternative that the home appliance company
    produces the item on its own. Table 10.20 contains
    the estimated probability distribution of the cost of
    purchasing 1 unit of this new product (in dollars)
    under the alternative that the home appliance
    company commissions a subcontractor to produce
    the item.
    a. Assuming that the home appliance company

Skill-Extending Problems

b. Perform sensitivity analysis on the optimal
expected cost. Under what conditions, if any,

the item.
a. Assuming that the home appliance company
seeks to minimize the expected unit cost of
manufacturing or buying the new product, should
the company make the new product or buy it
from a subcontractor?
b. Perform sensitivity analysis on the optimal

TABLE 10.19 Distribution of Unit
Production Cost under
"Make" Alternative

| Cost Per Unit | Probability |
| --- | --- |
| $50 | 0.20 |
| $53 | 0.25 |
| $55 | 0.30 |
| $57 | 0.20 |
| $59 | 0.05 |

* * *

would the home appliance company select an
alternative different from the one you identified
in part a?
15\. A grapefruit farmer in central Florida is trying to

in part a?
15\. A grapefruit farmer in central Florida is trying to
decide whether to take protective action to limit
damage to his crop in the event that the overnight
temperature falls to a level well below freezing. He
is concerned that if the temperature falls sufficiently
low and he fails to make an effort to protect his
grapefruit trees, he runs the risk of losing his entire
crop, which is worth approximately $75,000. Based
on the latest forecast issued by the National Weather
Service, the farmer estimates that there is a 60%
chance that he will lose his entire crop if it is left
unprotected. Alternatively, the farmer can insulate
his fruit by spraying water on all of the trees in his
orchards. This action, which would likely cost the
farmer C dollars, would prevent total devastation
but might not completely protect the grapefruit trees
from incurring some damage as a result of the
unusually cold overnight temperatures. Table 10.21
contains the assessed distribution of possible
damages (in dollars) to the insulated fruit in light of
the cold weather forecast. Of course, this farmer
seeks to minimize the expected total cost of coping
with the threatening weather.

TABLE 10.21 Distribution of Damages to
Insulated Grapefruit Crop
Damage to

a. Formulate a payoff table that specifies the
contribution to profit (in dollars) from the sale of
the tennis shoes by this department store chain
for each possible purchase decision (in hundreds
of pairs) and each outcome with respect to
consumer demand. Use an appropriate discrete
approximation of the given normal demand
distribution.
b. Construct a decision tree to identify the buyers

| Grapefruit Crop | Probability |
| --- | --- |
| $0 | 0.30 |
| $5000 | 0.15 |
| $10,000 | 0.10 |
| $15,000 | 0.15 |
| $20,000 | 0.30 |

b. Set C equal to the value identified in part a.
Perform sensitivity analysis to determine under
what conditions, if any, the farmer might be
better off not spraying his grapefruit trees and
taking his chances in spite of the threat to his
crop.
16\. Consider again the department store buyers

b. Construct a decision tree to identify the buyers
course of action that maximizes the expected
profit (in dollars) earned by the department store
chain from the purchase and subsequent sale of
tennis shoes in the coming year.
17\. Consider again the purchasing agents decision

17. Consider again the purchasing agents decision
    problem described in Problem 9. Assume now that
    the proportion of defective components supplied by
    this supplier is well described by the triangular
    distribution with parameters 0, 0, and 1. (This is
    called the right triangular distribution with
    range 1.)
    a. Formulate a payoff table that specifies the

range 1.)
a. Formulate a payoff table that specifies the
microcomputer manufacturers total cost
(in dollars) of purchasing and repairing (if
necessary) a complete lot of components for each
possible decision and each outcome with respect
to the proportion of defective items. Use an
appropriate discrete approximation of the given
triangular distribution for the proportion of
defective items.
b. Construct a decision tree to identify the

defective items.
b. Construct a decision tree to identify the
purchasing agents course of action that
minimizes the expected total cost (in dollars)
of achieving a complete lot of satisfactory
components.
18\. A retired partner from Goldman Sachs has 1 million

18. A retired partner from Goldman Sachs has 1 million
    dollars available to invest in particular stocks or
    bonds. Each investments annual rate of return
    depends on the state of the economy in the
    forthcoming year. Table 10.22 (page 524) contains
    the distribution of returns for these stocks and bonds
    as a function of the economys state in the coming
    year. This investor wants to allocate her $1 million to
    maximize her expected total return 1 year from now.
    a. If X = Y = 15%, find the optimal investment

a. If X = Y = 15%, find the optimal investment
strategy for this investor.
b. For which values of X (where 10% < X < 20%)

b. For which values of X (where 10% < X < 20%)
and Y (where 12.5% < Y < 17.5%), if any, will
this investor prefer to place all of her available
funds in the given stocks to maximize her
expected total return one year from now?
c. For which values of X (where 10% < X < 20%)

c. For which values of X (where 10% < X < 20%)
and Y (where 12.5% < Y < 17.5%), if any, will
this investor prefer to place all of her available
funds in the given bonds to maximize her
expected total return one year from now?

* * *

TABLE 10.22 Distribution of Annual Returns for Given Stocks
and Bonds

| State of the Economy | Probability | Annual Returns for Given Stocks | Annual Returns for Given Bonds |
| --- | --- | --- | --- |
| Very strong | 0.20 | 25% | 20% |
| Moderately strong | 0.40 | 20% | 17.5% |
| Fair | 0.25 | X% | Y% |
| Moderately weak | 0.10 | 10% | 12.5% |
| Very weak | 0.05 | 5% | 10% |

10.4 MULTISTAGE DECISION PROBLEMS
S

o far, all of the examples have required a single decision. We now examine
a problem where the decision maker must make at least two decisions that
Sare separated in time, such as when a company must decide whether to buy
information that will help it make a second decision. The following example illustrates
the typical situation.

EXAMPLE

10.4

The company wants to use a decision tree approach to find the best strategy.

MARKETING A NEW PRODUCT AT ACME

The Acme Company is trying to decide whether to market a new product. As in
many new-product situations, there is considerable uncertainty about whether the new
product will eventually catch on. Acme believes that it might be prudent to introduce
the product in a regional test market before introducing it nationally. Therefore, the
companys first decision is whether to conduct the test market. Acme estimates that the
fixed cost of the test market is $3 million. If it decides to conduct the test market, it
must then wait for the results. Based on the results of the test market, it can then decide
whether to market the product nationally, in which case it will incur a fixed cost of
$90 million. On the other hand, if the original decision is not to run a test market, then
the final decisionwhether to market the product nationallycan be made without
further delay. Acmes unit margin, the difference between its selling price and its unit
variable cost, is $18 (in the test market and in the national market).
Acme classifies the results in either the test market or the national market as great,

* * *

# Solution

We begin by discussing the three basic elements of this decision problem: the possible strategies, the possible outcomes and their probabilities, and the value model. The possible strategies are clear. Acme must first decide whether to conduct a test market. Then it must decide whether to introduce the product nationally. However, it is important to realize that if Acme decides to conduct a test market, it can base the national market decision on the results of the test market. In this case its final strategy will be a contingency plan, where it conducts the test market, then introduces the product nationally if it receives sufficiently positive test market results and abandons the product if it receives sufficiently negative test market results. The optimal strategies from many multistage decision problems involve similar contingency plans. Regarding the uncertain outcomes and their probabilities, we note that the given probabilitiesprobabilities of test market outcomes and conditional probabilities of national market outcomes given test market outcomesare exactly the ones we need in the decision tree. This is because the test market outcome is known before the national market outcome will occur. However, suppose Acme decides not to run a test market and then decides to market nationally. Then what are the probabilities of the national market outcomes? It is important to realize that we cannot simply assess three new probabilities for this situation. These probabilities are implied by the given probabilities. This follows from the rules of conditional probability. If we let T1, T2,andT3 be the test market outcomes, and N be any of the national market outcomes, then by the addition rule for probability and the conditional probability formula,

_P (N) = P (N and T1_) \+ P (N and T2) + P (N and T3) **(10.1)** = P (N \|T1) P (T1) + P (N \|T2) P (T2) + P (N \|T3) P (T3) **(10.2)**

(This is sometimes called the law of total probability.) For example, if N1 represents a great national market, then from equation (10.1),

_P (N1_) = (0.8)(0.3) + (0.3)(0.6) + (0.05)(0.1) = 0.425

Similarly, we find that P (N2) = 0.37 and P (N3) = 0.205. These are the probabilities we need to use for the probability branches when no test market is used. Finally, the monetary values in the tree are straightforward. There are fixed costs of test marketing or marketing nationally, and these are incurred as soon as these go ahead decisions are made. From that point, we observe the sales volumes and multiply them by the unit margin to obtain the profits.

_PRECISION_

## USING PRECISIONTREE

_TREE_ The inputs for the decision tree appear in Figure 10.26 (page 526). (See file ACME. XLS.) The only calculated values in this part of the spreadsheet are in row 28, which follow from equation (10.1). Specifically, the formula in cell B28 is

**=SUMPRODUCT(B22:B24,$B$16:$B$18)**

which we copy across row 28. The tree is then straightforward to build and label, as shown in Figure 10.27 (page 527). Note how the fixed costs of test marketing and marketing nationally appear on the decision branches where they occur, so that only the selling profits need to be placed on the probability branches. Also, the probabilities on the various probability branches are exactly those listed in Figure 10.26. The interpretation of this tree is fairly straightforward if we realize that each value just below each node name is an EMV. For example, the 807 in cell B43 is the EMV for

10.4 Multistage Decision Problems

* * *

**FIGURE 10.26**

Inputs for Acme Marketing Example

the entire decision problem. It means that Acmes best EMV is $807,000. As another example, the 5910 in cell D47 means that if Acme ever gets to that pointthe test market has been conducted and it has been greatthe EMV for ACME is $5,910,000. Each of these EMVs has been calculated by the folding-back procedure we discussed earlier, starting from the right and working back toward the left. PrecisionTree takes EMVs at probability nodes and maximums at decision nodes. We can also see Acmes optimal strategy by following the TRUE branches from left to right. Acme should first run a test market. If the test market results are great, then the product should be marketed nationally. However, if the test market results are only fair or awful, the product should be abandoned. In these cases the prospects from a national market look bleak, so Acme should cut its losses. (And there are losses. In these latter two cases, Acme has spent $3,000,000 on the test market and has recouped only $1,800,000 or $540,000 on test market sales.) The risk profile from the optimal strategy appears in Figure 10.28 (page 528). It is based on the data in Figure 10.29 (page 528). (These were obtained by clicking on PrecisionTrees staircase button and selecting the Statistics and Risk Profile options.) We see that there is a small chance of two possible large losses (approximately $73 million and $35 million), there is a 70% chance of a moderate loss of about $1 or $2 million, and there is a 24% chance of an $18.6 million profit. Of course, the net effect is an EMV of $807,000. You might argue that the large potential losses and the slightly higher than 70% chance of some loss should persuade Acme to abandon the product right awaywithout a test market. However, this is what playing the averages with EMV is all about. Since the EMV of this optimal strategy is greater than 0, the EMV of abandoning the product right away, Acme should go ahead with this optimal strategy if the company is indeed an EMV maximizer. In Section 10.8 we will see how this reasoning can change if Acme is a risk-averse decision makeras it might be with multimillion dollar losses looming in the future!

Chapter 10 _Decision Making Under Uncertainty_

* * *

**FIGURE 10.27 Decision Tree for Acme Marketing Example**

**Expected Value of Sample Information** The role of the test market in the Acme marketing example is to provide information in the form of more accurate probabilities of national market results. Information usually costs something, as it does in Acmes problem. Currently, the fixed cost of the test market is $3 million, which is evidently not too much to pay because Acmes best strategy is to conduct the test market. However, we might ask how much this test market is worth. This is easy to answer. From the decision tree in Figure 10.27, we see that the EMV from test marketing is $807,000 better than the decision not to test market (and then abandon the product). Therefore, if the fixed cost of test marketing were any more than $807,000 above its current value,

10.4 Multistage Decision Problems

* * *

FIGURE 10.28
Risk Profile of
Optimal Strategy

FIGURE 10.29
Distribution of
Profit/Loss from the
Optimal Strategy

\[Image: Im30\]

|  | A | B | C |
| --- | --- | --- | --- |
| 16 | PROFILE: |  |  |
| 17 | # | X | P |
| 18 | 1 | -73200 | 0.015 |
| 19 | 2 | -35400 | 0.045 |
| 20 | 3 | -2460 | 0.1 |
| 21 | 4 | -1200 | 0.6 |
| 22 | 5 | 18600 | 0.24 |

Acme would be better not to run a test market. Equivalently, the most Acme would be
willing to pay for the test market (as a fixed cost) is $3.807 million.
This value is called the expected value of sample information,orEVSI.In

This value is called the expected value of sample information,orEVSI.In
general, we can write the following expression for EVSI:

\ {bf}E V S{\\bf I}={\\bf E M}{\\bf V};{\\bf w i t h};{\\it f r e e};{\\bf i n f o r m a t i o n}-{\\bf E M V};{\\bf w i t h o u t};{\\it i n f o r m a t i o n}

In Acmes problem, the EMV with free information is $3.807 million (just dont charge
for the test market fixed cost), and the EMV without any test market information is $0
(because Acme abandons the product when there is no test market available). Therefore,

{\\mathrm{E V S I}}=\\S3.807-\\S0=\\S3.807{\\mathrm{~m i l l i o n}}

Expected Value of Perfect Information The reason for the term sample is that the
information does not remove all uncertainty about the future. That is, even after the
test market results are in, there is still uncertainty about the national market results.
Therefore, we might go one step further and ask how much perfect information is
worth. We can imagine perfect information as an envelope that contains the true final
outcome (of the national market). That is, either the national market will be great,
the national market will be fair, or the national market will be awful is written
inside the envelope. Admittedly, no such envelope exists, but if it did, how much would
Acme be willing to pay for it?
We can answer this question with the simple decision tree in Figure 10.30. Now

* * *

**FIGURE 10.30**

EVPI for Acme Marketing Example

that there will be a loss from marketing nationally, so it will abandon the product. Folding back in the usual way produces an EMV of $7.65 million. Now compare this $7.65 million with the EMV in the top part of Figure 10.27 that results from no test market, namely, $0. The difference, $7.65 million, is called the **expected value of perfect information,orEVPI. It represents the maximum amount** the company would pay for perfect information about the final outcome (of the national market). In general, the expression for EVPI is

EVPI = EMV with free perfect information − EMV with no information

## In Acmes case this expression becomes

EVPI = $7.65 − $0 = $7.65 million

The EVPI may appear to be an irrelevant concept since perfect information is almost never availableat any price. However, it is often useful because it represents an upper _bound on the EVSI for any potential sample information. That is, no sample information_ can ever be worth more than the EVPI. For example, if Acme is contemplating an expensive test market with an anticipated fixed cost of more than $8 million, then there is really no point in pursuing it any further. The information gained from this test market, no matter how reliable it is, cannot possibly justify its cost because its cost is greater than the EVPI. ■

10.4 Multistage Decision Problems

* * *

Skill-Building Problems

19. The senior executives of an oil company are trying
    to decide whether to drill for oil in a particular field
    in the Gulf of Mexico. It costs the company
    $300,000 to drill in the selected field. Company
    executives believe that if oil is found in this field its
    estimated value will be $1,800,000. At present, this
    oil company believes that there is a 50% chance that
    the selected field actually contains oil. Before
    drilling, the company can hire a geologist at a cost
    of $30,000 to prepare a report that contains a
    recommendation regarding drilling in the selected
    field. There is a 55% chance that the geologist
    will issue a favorable recommendation and a
    45% chance that the geologist will issue an
    unfavorable recommendation. Given a favorable
    recommendation from the geologist, there is a 75%
    chance that the field actually contains oil. Given an
    unfavorable recommendation from the geologist,
    there is a 15% chance that the field actually
    contains oil.
    a. Assuming that this oil company wishes to

a. Assuming that this oil company wishes to
maximize its expected net earnings, determine its
optimal strategy through the use of a decision
tree.
b. Compute and interpret the expected value of

c. Compute and interpret the expected value of
perfect information (EVPI) in this decision
problem.
20\. A local certified public accountant must decide

Before the purchase decision is made, the
CPA can hire an experienced copying machine
repairperson to evaluate the quality of the first
machine. Such an evaluation would cost the CPA
$60\. If the repairperson believes that the first
machine is satisfactory, there is a 65% chance that
its annual maintenance cost will be $0 and a 35%
chance that its annual maintenance cost will be
$150\. If, however, the repairperson believes that the
first machine is unsatisfactory, there is a 60% chance
that its annual maintenance cost will be $150 and a

40% chance that its annual maintenance cost will be
$300\. The CPAs office manager believes that the
repairperson will issue a satisfactory report on the
first machine with probability 0.50.
a. Provided that the CPA wishes to minimize

a. Provided that the CPA wishes to minimize
the expected total cost of purchasing and
maintaining one of these two machines for a
1-year period, which machine should she
purchase? When, if ever, would it be worthwhile
for the CPA to obtain the repairpersons review
of the first machine?
b. Compute and interpret the expected value of

b. Compute and interpret the expected value of
sample information (EVSI) in this decision
problem.
c. Compute and interpret the expected value of

c. Compute and interpret the expected value of
perfect information (EVPI) in this decision
problem.
21\. FineHair is developing a new product to promote

problem.
21\. FineHair is developing a new product to promote
hair growth in cases of male pattern baldness. If
FineHair markets the new product and it is
successful, the company will earn $500,000 in
additional profit. If the marketing of this new
product proves to be unsuccessful, the company will
lose $350,000 in development and marketing
costs. In the past, similar products have been
successful 60% of the time. At a cost of $50,000, the
effectiveness of the new restoration product can be
thoroughly tested. If the results of such testing are
favorable, there is an 80% chance that the marketing
efforts of this new product will be successful. If the
results of such testing are not favorable, there is a
mere 30% chance that the marketing efforts of this
new product will be successful. FineHair currently
believes that the probability of receiving favorable
test results is 0.60.
a. Identify the strategy that maximizes FineHairs

a. Identify the strategy that maximizes FineHairs
expected net earnings in this situation.
b. Compute and interpret the expected value of

expected net earnings in this situation.
b. Compute and interpret the expected value of
sample information (EVSI) in this decision
problem.
c. Compute and interpret the expected value of

problem.
c. Compute and interpret the expected value of
perfect information (EVPI) in this decision
problem.
22\. Hank is considering placing a bet on the upcoming

problem.
22\. Hank is considering placing a bet on the upcoming
showdown between the Penn State and Michigan
football teams in State College. The winner of this
contest will represent the Big Ten Conference in the
Rose Bowl on New Years Day. Without any
additional information, Hank believes that each team
has an equal chance of winning this big game. If he
wins the bet, he will win $500; if he loses the bet, he
will lose $550. Before placing his bet, he may decide
to pay his friend Al, who happens to be a football
sportswriter for the Philadelphia Enquirer, $50 for
Als expert prediction on the game. Assume that Al predicts that Penn State will win similar games 55%
of the time, and that Michigan will win similar
games 45% of the time. Furthermore, Hank knows
that when Al predicts that Penn State will win, there
is a 70% chance that Penn State will indeed win the
football game. Finally, when Al predicts that
Michigan will win, there is a 20% chance that Penn
State will proceed to win the upcoming game.
a. In order to maximize his expected profit from

a. In order to maximize his expected profit from
this betting opportunity, how should Hank
proceed in this situation?
b. Compute and interpret the expected value of

proceed in this situation?
b. Compute and interpret the expected value of
sample information (EVSI) in this decision
problem.
c. Compute and interpret the expected value of

c. Compute and interpret the expected value of
perfect information (EVPI) in this decision
problem.
23\. A product manager at Clean & Brite seeks to

problem.
23\. A product manager at Clean & Brite seeks to
determine whether her company should market a
new brand of toothpaste. If this new product
succeeds in the marketplace, C&B estimates that it
could earn $1,800,000 in future profits from the sale
of the new toothpaste. If this new product fails,
however, the company expects that it could lose
approximately $750,000. If C&B chooses not to
market this new brand, the product manager believes
that there would be little, if any, impact on the
profits earned through sales of C&Bs other
products. The manager has estimated that the new
toothpaste brand will succeed with probability
0.55. Before making her decision regarding this
toothpaste product, the manager can spend $75,000
on a market research study. Such a study of
consumer preferences will yield either a positive
recommendation with probability 0.50 or a negative

recommendation with probability 0.50. Given a
positive recommendation to market the new product,
the new brand will eventually succeed in the
marketplace with probability 0.75. Given a negative
recommendation regarding the marketing of the new
product, the new brand will eventually succeed in
the marketplace with probability 0.25.
a. In order to maximize expected profit in this case,

a. In order to maximize expected profit in this case,
what course of action should the C&B product
manager take?
b. Compute and interpret the expected value of

b. Compute and interpret the expected value of
sample information (EVSI) in this decision
problem.
c. Compute and interpret the expected value of

c. Compute and interpret the expected value of
perfect information (EVPI) in this decision
problem.

| Survey Indication/Actual Performance | Very Strong | Moderately Strong | Fair | Poor |
| --- | --- | --- | --- | --- |
| Very strong | 13 | 12 | 2 | 3 |
| Moderately strong | 10 | 20 | 6 | 4 |
| Fair | 5 | 12 | 15 | 8 |
| Poor | 1 | 3 | 9 | 22 |

TABLE 10.23 Distribution of Payoffs for New
Business Law Textbook
Textbook Estimated

Skill-Extending Problems

24. A publishing company is trying to decide whether to
    publish a new business law textbook. Based on a
    careful reading of the latest draft of the manuscript,
    the publishers senior editor in the business textbook
    division assesses the distribution of possible payoffs
    earned by publishing this new book. Table 10.23
    contains this probability distribution. Before making
    a final decision regarding the publication of the
    book, the editor can learn more about the texts
    potential for success by thoroughly surveying
    business law instructors teaching at universities
    across the country. Historical frequencies based on
    similar surveys administered in the past are provided
    in Table 10.24.
    a. Find the strategy that maximizes the publishers

a. Find the strategy that maximizes the publishers
expected payoff (in dollars).

* * *

b. What is the most (in dollars) that the publisher
should be willing to pay to conduct a new survey
of business law instructors?
c. If the actual cost of conducting the given survey

c. If the actual cost of conducting the given survey
is less than the amount identified in part a,what
should the publisher do?
d. Assuming that a survey could be constructed that

d. Assuming that a survey could be constructed that
provides perfect information to the publisher,
how much should the company be willing to pay
to acquire and implement such a survey?
25\. Sharp Outfits is trying to decide whether to ship

to acquire and implement such a survey?
25\. Sharp Outfits is trying to decide whether to ship
some customer orders now via UPS or wait until
after the threat of another UPS strike is over. If
Sharp Outfits decides to ship the requested
merchandise now and the UPS strike takes place, the
company will incur $60,000 in delay and shipping
costs. If Sharp Outfits decides to ship the customer
orders via UPS and no strike occurs, the company
will incur $4000 in shipping costs. If Sharp Outfits
decides to postpone shipping its customer orders via
UPS, the company will incur $10,000 in delay costs
regardless of whether or not UPS goes on strike. Let
p represent the probability that UPS will go on
strike and impact Sharp Outfitss shipments.

a. For which values of p, if any, does Sharp Outfits
minimize its expected total cost by choosing to
postpone shipping its customer orders via UPS?
b. Suppose now that, at a cost of $1000, Sharp

b. Suppose now that, at a cost of $1000, Sharp
Outfits can purchase information regarding the
likelihood of a UPS strike in the near future.
Based on similar strike threats in the past, the
probability that this information indicates the
occurrence of a UPS strike is 27.5%. If the
purchased information indicates the occurrence
of a UPS strike, the chance of a strike actually
occurring is 0.105/0.275. If the purchased
information does not indicate the occurrence of a
UPS strike, the chance of a strike actually
occurring is 0.680/0.725. Provided that
p = 0.15, what strategy should Sharp Outfits
pursue to minimize its expected total cost?
c. Continuing part b, compute and interpret the

c. Continuing part b, compute and interpret the
expected value of sample information (EVSI)
when p = 0.15.
d. Continuing part b, compute and interpret the

d. Continuing part b, compute and interpret the
expected value of perfect information (EVPI)
when p = 0.15.

10.5 BAYES’ RULE
I

10.5

n multistage decision problems we typically have alternating sets of decision nodes
and probability nodes. The decision maker makes a decision, some uncertain out-
Icomes are observed, the decision maker makes another decision, more uncertain
outcomes are observed, and so on. In the resulting decision tree, all probability branches
at the right of the tree are conditional on outcomes that have occurred earlier, to their
left. Therefore, the probabilities on these branches are of the form P ( A\|B),whereB
is an event that occurs before event A in time. However, it is sometimes more natural
to assess conditional probabilities in the opposite order, that is, P (B\| A). Whenever
this is the case, we require Bayes rule to obtain the probabilities we need on the tree.
Essentially, Bayes rule is a mechanism for updating probabilities as new information
becomes available. We illustrate the mechanics of Bayes rule in the following example.
\[See Feinstein (1990) for a real application of this example.\]

n multistage decision problems we typically have alternating sets of decision nodes
and probability nodes. The decision maker makes a decision, some uncertain outcomes are observed, the decision maker makes another decision, more uncertain
outcomes are observed, and so on. In the resulting decision tree, all probability branches
at the right of the tree are conditional on outcomes that have occurred earlier, to their
left. Therefore, the probabilities on these branches are of the form P ( A\|B),whereB
is an event that occurs before event A in time. However, it is sometimes more natural
to assess conditional probabilities in the opposite order, that is, P (B\| A). Whenever
this is the case, we require Bayes rule to obtain the probabilities we need on the tree.
Essentially, Bayes rule is a mechanism for updating probabilities as new information
becomes available. We illustrate the mechanics of Bayes rule in the following example.
\[See Feinstein (1990) for a real application of this example.\]

* * *

of all athletes use drugs, 3% of all tests on drug-free athletes yield false positives, and
7% of all tests on drug users yield false negatives. The question then is what we can
conclude from a positive or negative test result.

Solution

Let D and ND denote that a randomly chosen athlete is or is not a drug user, and
let T + and T − indicate a positive or negative test result. We are given the following
probabilities. First, since 5% of all athletes are drug users, we know that P (D) =
0.05 and P (ND) = 0.95. These are called prior probabilities because they represent
the chance that an athlete is or is not a drug user prior to the results of a drug
test. Second, from the information on drug test accuracy, we know the conditional
probabilities P (T +\|ND) = 0.03 and P (T −\|D) = 0.07. But a drug-free athlete tests
either positive or negative, and the same is true for a drug user. Therefore, we also have
the probabilities P (T −\|ND) = 0.97 and P (T +\|D) = 0.93. These four conditional
probabilities of test results given drug user status are often called the likelihoods of
the test results.
Given these priors and likelihoods, we want posterior probabilities such as

T+

P(D)=

P(N D)=0.95

P(T!+!\|N D)!=!0.03

P(\\dot{T-\|D\|)}=0.07

P(T-\|N D)\ {,=,}0.97

P(T!+!\|D)!=!0.93

Given these priors and likelihoods, we want posterior probabilities such as
P (D\|T +), the probability that an athlete who tested positive is a drug user, or
P (ND\|T −), the probability that an athlete who tested negative is drug free. They
are called posterior probabilities because they are assessed after the drug test results.
This is where Bayes rule enters. We will develop Bayes rule in some generality and
then apply it to the present example.
Let A be any information event, such as the result of a drug test, and let

P(D\|T+)

P(N D\|T-)

Let A be any information event, such as the result of a drug test, and let
B1, B2,...,B be any mutually exclusive and exhaustive set of events. That is, exactly
n
one of the B s must occur. To apply Bayes rule, we assume that the prior probabilities
i
P (B1), P (B2),..., P (B) are given, as are the likelihoods P ( A\|B) for each i.Then
n i
we want the posterior probabilities P (B \| A) for each i. Bayes rule shows how to find
i
these. For any i,wehave
P ( A\|B ) P (B )

B\_{1},B\_{2},\\ldots,B\_{n}

B\_{i}

P(B\_{1}),P(\\dot{B\_{2}}),\\dots,P(B\_{n})

P(A\|B\_{i})

P(B\_{i}\|A)

P(B\_{i}\|A)=\\frac{P(A\|B\_{i})P(B\_{i})}{P(A\|B\_{1})P(B\_{1})+\\cdots+P(A\|B\_{n})P(B\_{n})}

Bayes rule

This formula says that a typical posterior probability is a ratio. The numerator is
a likelihood times a prior, and the denominator is the sum of likelihoods times
priors.
Before illustrating Bayes rule numerically, we make two other observations about

Before illustrating Bayes rule numerically, we make two other observations about
the terms in Bayes rule. First, we can use the multiplication rule of probability to write
any product of a likelihood and a prior as
P ( A\|B) P (B) = P ( A and B)

P(A\|B\_{i})P(B\_{i})=P(A;\ {\\mathrm{a n d}};B\_{i})

B\_{i}

As we will see shortly, this natural by-product of Bayes rule will come in very handy
in decision trees.

* * *

FIGURE 10.31
Bayes Rule for
Drug-Testing
Example

It is fairly easy to implement Bayes rule in a spreadsheet, as illustrated in Figure
10.31 for the drug example. Here A corresponds to either test result, and B1 and B2
4
correspond to D and ND. (See the file DRUGBAYES.XLS.) In words, we want to
see how the chances of D and ND change after seeing the results of the drug test.
The given priors and likelihoods are listed in the ranges B5:C5 and B9:C10. We

B\_{1}

B\_{2}

The given priors and likelihoods are listed in the ranges B5:C5 and B9:C10. We
then calculate the products of likelihoods and priors in the range B15:C16. The formula
in cell B15 is

=B$5\*B9

and this is copied to the rest of the B15:C16 range. Their row sums are calculated in
the range D15:D16. These represent the unconditional probabilities of the two possible
results. They are also (as we saw above) the denominators of Bayes rule. Finally, we
calculate the posterior probabilities in the range B21:C22. The formula in cell B21 is

=B15/$D15

and this is copied to the rest of the B21:C22 range. The various 1s in the margins of
Figure 10.31 are row sums or column sums that must equal 1. We show them only as
checks of our logic.

|  | A | B | C | D |
| --- | --- | --- | --- | --- |
| 1 | Illustration of Bayes' rule using drug example |  |  |  |
| 2 |  |  |  |  |
| 3 | Prior probabilities of drug user status |  |  |  |
| 4 |  | User | Non-user |  |
| 5 |  | 0.05 0.95 |  | 1 |
| 6 |  |  |  |  |
| 7 | Likelihoods of test results, given drug user status |  |  |  |
| 8 |  | User | Non-user |  |
| 9 | Test positive | 0.93 0.03 |  |  |
| 10 | Test negative | 0.07 0.97 |  |  |
| 11 |  | 1 | 1 |  |
| 12 |  |  |  |  |
| 13 | Joint probabilities of drug user status and test results |  |  |  |
| 14 |  | User | Non-user | Unconditional |
| 15 | Test positive | 0.0465 | 0.0285 | 0.075 |
| 16 | Test negative | 0.0035 | 0.9215 | 0.925 |
| 17 |  |  |  | 1 |
| 18 |  |  |  |  |
| 19 | Posterior probabilities of drug user status |  |  |  |
| 20 |  | User | Non-user |  |
| 21 | Test positive | 0.620 | 0.380 | 1 |
| 22 | Test negative | 0.004 | 0.996 | 1 |

Note that a negative test result leaves little doubt that the athlete is drug free.
The posterior probability that the athlete is drug free, given a negative test result, is
0.996. However, there is still a lot of doubt about an athlete who tests positive. The
posterior probability that the athlete uses drugs, given a positive test result, is only
0.620. This asymmetry occurs because of the prior probabilities. We are fairly certain
that a randomly selected athlete is drug free because only 5% of all athletes use drugs.
It takes a lot of evidence to convince us otherwise. This initial bias, plus the fact that
the test produces a few false positives, means that athletes with positive test results still
have a decent chance (probability 0.380) of being drug free. Is this a valid argument

4
The Bayes2 sheet in this file illustrates how Bayes rule can be used when there are more than two
possible test results and/or drug user categories.

* * *

for not requiring drug testing of athletes? We explore this question in the following continuation of the drug-testing example. It all depends on the costs. (It might also depend on whether there is a second type of test that could help confirm the findings of the first test. However, we wont consider such a test.) ■

# EXAMPLE 10.5 (continued)

## DRUG TESTING COLLEGE ATHLETES

The administrators at State University are trying to decide whether to institute manda- tory drug testing for the athletes. They have the same information about priors and likelihoods as in the previous example, but now they want to use a decision tree approach to see whether the benefits outweigh the costs. 5

## Solution

We have already discussed the uncertain outcomes and their probabilities. Now we need to discuss the decision alternatives and the monetary valuesthe other two elements of a decision analysis. We will assume that there are only two alternatives: perform drug testing on all athletes or dont perform any drug testing. In the former case we assume that if an athlete tests positive, this athlete is barred from sports. The monetary values are more difficult to assess. They include

■the benefit B from correctly identifying a drug user and barring him or her from sports ■the cost C1 of the test itself for a single athlete (materials and labor) ■the cost C2 of falsely accusing a nonuser (and barring him or her from sports) ■the cost C3 of not identifying a drug user (either by not testing at all or by obtaining afalsenegative) ■the cost C4 of violating a nonusers privacy by performing the test

It is clear that only C1 is a direct monetary cost that is easy to measure. However, the other costs and the benefit B are real, and they must be compared on some scale to enable administrators to make a rational decision. We will do so by comparing everything to the cost C1, to which we will assign value 1. (This does not mean that the cost of testing an athlete is necessarily $1; it just means that we will express all other costs as multiples of C1.) Clearly, there is a lot of subjectivity involved in making these comparisons, so sensitivity analysis on the final decision tree is a must. Before developing this decision tree, it is useful to form a benefitcost table for both alternatives and all possible outcomes. Because we will eventually maximize expected net benefit, all benefits in this table have a positive sign and all costs have a negative sign. These net benefits appear in Table 10.25 (page 536). The first two columns are relevant if no tests are performed; the last four are relevant when testing is performed. For example, if a positive test is obtained for a nonuser, there are three

Again, see Feinstein (1990) for an enlightening discussion of this drug-testing problem at a real university.

10.5 Bayes Rule

* * *

TABLE 10.25 **Net Benefit for Drug-Testing Example**

## Dont Test Perform Test

_**DND D\* and T + \*ND and T + D and T − NDand T −**_

−C3 0 _B − C1_ −(C1 + C2 + C4) −(C1 + C3) −(C1 + C4)

costs: the cost of the test (C1), the cost of falsely accusing the athlete (C2), and the cost of violating the nonusers privacy (C4). The other entries are obtained similarly. The solution with PrecisionTree shown in Figure 10.32 is now fairly straightfor- ward. (See the file DRUG.XLS.) We first enter all of the benefits and costs in an input section. These, together with the Bayes rule calculations from before, appear at the top of the spreadsheet. Then we use PrecisionTree in the usual way to build the tree and enter the links to the values and probabilities.

**FIGURE 10.32 Decision Tree for Drug-Testing Example**

Chapter 10 _Decision Making Under Uncertainty_

* * *

Before we interpret this solution, we discuss the timing (from left to right). If drug testing is performed, the result of the drug test is observed first (a probability node). Each test result leads to an action (bar from sports or dont), and then the eventual benefit or cost depends on whether the athlete uses drugs (again a probability node). You might argue that the university never knows for certain whether the athlete uses drugs, but we must include this information in the tree to get the benefits and costs correct. If no drug testing is performed, then there is no intermediate test result node or branches. Now to the interpretation. First, we discuss the benefits and costs shown in Fig- ure 10.32. These were chosen fairly arbitrarily, but with some hope of reflecting reality. They say that the largest cost is falsely accusing (and barring) a nonuser. This is 50 times as large as the cost of the test. The benefit of identifying a drug user is only half this large, and the cost of not identifying a user is 40% as large as barring a nonuser. The violation of privacy of a nonuser is twice as large as the cost of the test. Based on these values, the decision tree implies that drug testing should not be performed. The EMVs for testing and for not testing are both negative, indicating that the costs outweigh the benefits for each, but the EMV for not testing is slightly less negative. 6

What would it take to change this decision? Well start with the assumption, probably accepted by most people in our society, that the cost of falsely accusing a nonuser (C2) ought to be the largest of the benefits or costs in the range B4:B10. In fact, because of possible legal costs, we might argue that C2 should be more than 50 times the cost of the test. But if we increase C2, the scales are tipped even farther in the direction of not testing. On the other hand, if the benefit B from identifying a user and/or the cost C3 for not identifying a user increase, then testing might be the preferred alternative. We tried this, keeping C2 constant at 50. When B and C3 both had value 45, no testing was still optimal, but when they both increased to 50the same magnitude as C2then testing won out by a small margin. However, it would be difficult to argue that B and C3 should be of the same magnitude as C2. Other than the benefits and costs, the only other thing we might vary is the accuracy of the test, measured by the error probabilities in cells B14 and B15. Presumably, if the test makes fewer false positives and false negatives, testing might be a more attractive alternative. We tried this, keeping the benefits and costs the same as those shown in

Figure 10.32 but changing the error probabilities. Even when each error probability

was decreased to 0.01, however, the no-testing alternative was still optimalby a fairly wide margin. In summary, based on a number of reasonable assumptions and parameter settings, this example has shown that it is difficult to make a case for mandatory drug testing. ■

6 The university in the Feinstein (1990) study came to the same conclusion.

10.5 Bayes Rule

* * *

PROBLEMS

Skill-Building Problems

26. Consider a population of 2000 individuals, 800 of
    whom are women. Assume that 300 of the women
    in this population earn at least $60,000 per year, and
    200 of the men earn at least $60,000 per year.
    a. What is the probability that a randomly selected

a. What is the probability that a randomly selected
individual from this population earns less than
$60,000 per year?
b. If a randomly selected individual is observed to

b. If a randomly selected individual is observed to
earn less than $60,000 per year, what is the
probability that this person is a man?
c. If a randomly selected individual is observed to

probability that this person is a man?
c. If a randomly selected individual is observed to
earn at least $60,000 per year, what is the
probability that this person is a woman?
27\. Yearly automobile inspections are required for

probability that this person is a woman?
27\. Yearly automobile inspections are required for
residents of the state of Pennsylvania. Suppose that
18% of all inspected cars in Pennsylvania have
problems that need to be corrected. Unfortunately,
Pennsylvania state inspections fail to detect these
problems 12% of the time. Consider a car that is
inspected and is found to be free of problems. What
is the probability that there is indeed something
wrong that the inspection has failed to uncover?
28\. Consider again the landowners decision problem

wrong that the inspection has failed to uncover?
28\. Consider again the landowners decision problem
described in Problem 3. Suppose now that, at a cost
of $90,000, the landowner can request that a
soundings test be performed on the site where
natural gas is believed to be present. The company
that conducts the soundings concedes that 30% of
the time the test will indicate that no gas is present
when it actually is. When natural gas is not present
in a particular site, the soundings test is accurate
90% of the time.
a. Given that the landowner pays for the soundings

29. The chief executive officer of a firm in a highly
    competitive industry believes that one of her key
    employees is providing confidential information to
    the competition. She is 90% certain that this
    informer is the vice-president of finance, whose
    contacts have been extremely valuable in obtaining
    financing for the company. If she decides to fire this
    vice-president and he is the informer, she estimates

that the company will gain $500,000. If she decides
to fire this vice-president but he is not the informer,
the company will lose his expertise and still have an
informer within the staff; the CEO estimates that
this outcome would cost her company about $2.5
million. If she decides not to fire this vice-president,
she estimates that the firm will lose $1.5 million
whether or not he actually is the informer (since in
either case the informer is still with the company).
Before deciding whether to fire the

90% of the time.
a. Given that the landowner pays for the soundings
test and the test indicates that gas is present, what
is the landowners revised estimate of the
probability of finding gas on this site?
b. Given that the landowner pays for the soundings

b. Given that the landowner pays for the soundings
test and the test indicates that gas is not present,
what is the landowners revised estimate of the
probability of not finding gas on this site?
c. Should the landowner request the given

Before deciding whether to fire the
vice-president for finance, the CEO could order lie
detector tests. To avoid possible lawsuits, the lie
detector tests would have to be administered to all
company employees, at a total cost of $150,000.
Another problem she must consider is that the
available lie detector tests are not perfectly reliable.
In particular, if a person is lying, the test will reveal
that the person is lying 95% of the time. Moreover,
if a person is not lying, the test will indicate that the
person is not lying 85% of the time.
a. In order to minimize the expected total cost of

b. Should the CEO order the lie detector tests for all
of her employees? Explain why or why not.
c. Determine the maximum amount of money that

30. A customer has approached a bank for a $10,000
    one-year loan at a 12% interest rate. If the bank does
    not approve this loan application, the $10,000 will
    be invested in bonds that earn a 6% annual return.
    Without additional information, the bank believes
    that there is a 4% chance that this customer will
    default on the loan, assuming that the loan is
    approved. If the customer defaults on the loan, the
    bank will lose $10,000.
    At a cost of $100, the bank can thoroughly

a. What course of action should the bank take to
maximize its expected profit?
b. Compute and interpret the expected value of

At a cost of $100, the bank can thoroughly
investigate the customers credit record and supply a
favorable or unfavorable recommendation. Past
experience indicates that in cases where the
customer did not default on the approved loan, the
probability of receiving a favorable recommendation
on the basis of the credit investigation was 77/96.
Furthermore, in cases where the customer defaulted
on the approved loan, the probability of receiving a
favorable recommendation on the basis of the credit
investigation was 1/4.
a. What course of action should the bank take to c. Compute and interpret the expected value of
perfect information (EVPI) in this decision
problem.
31\. A company is considering whether to market a new

31. A company is considering whether to market a new
    product. Assume, for simplicity, that if this product
    is marketed, there are only two possible outcomes:
    success or failure. The company assesses that the
    probabilities of these two outcomes are p and
    1 − p, respectively. If the product is marketed and it
    proves to be a failure, the company will lose
    $450,000. If the product is marketed and it proves to
    be a success, the company will gain $750,000.
    Choosing not to market the product results in no
    gain or loss for the company.
    The company is also considering whether to

The company is also considering whether to
survey prospective buyers of this new product. The
results of the consumer survey can be classified as
favorable, neutral, or unfavorable. In similar cases
where proposed products proved to be market
successes, the likelihoods that the survey results
were favorable, neutral, and unfavorable were 0.6,
0.3, and 0.1, respectively. In similar cases where
proposed products proved to be market failures, the
likelihoods that the survey results were favorable,
neutral, and unfavorable were 0.1, 0.2, and 0.7,
respectively. The total cost of administering this
survey is C dollars.
a. Let p = 0.4. For which values of C,ifany,

a. Let p = 0.4. For which values of C,ifany,
would this company choose to conduct the
consumer survey?
b. Let p = 0.4. What is the largest amount that this

b. Let p = 0.4. What is the largest amount that this
company would be willing to pay for perfect
information about the potential success or failure
of the new product?
c. Let p = 0.5andC = $15,000. Find the strategy

c. Let p = 0.5andC = $15,000. Find the strategy
that maximizes the companys expected earnings
in this situation. Does the optimal strategy
involve conducting the consumer survey?
Explain why or why not.
32\. The U.S. government is attempting to determine

32. The U.S. government is attempting to determine
    whether immigrants should be tested for a
    contagious disease. Lets assume that the decision
    will be made on a financial basis. Furthermore,
    assume that each immigrant who is allowed to enter
    the United States and has the disease costs the
    country $100,000. Also, each immigrant who is
    allowed to enter the United States and does not have
    the disease will contribute $10,000 to the national
    economy. Finally, assume that x percent of all
    potential immigrants have the disease. The U.S.
    government can choose to admit all immigrants,
    admit no immigrants, or test immigrants for the
    disease before determining whether they should be
    admitted. It costs T dollars to test a person for the
    disease; the test result is either positive or negative.
    A person who does not have the disease always tests
    negative. However, 20% of all people who do have

the disease test negative. The governments goal is
to maximize the expected net financial benefits per
potential immigrant.
a. Let x = 10 (i.e., 10%). What is the largest value

a. Let x = 10 (i.e., 10%). What is the largest value
of T at which the U.S. government will choose
to test potential immigrants for the disease?
b. How does your answer to the question in part a

b. How does your answer to the question in part a
change when x increases to 15?
c. Let x = 10 and T = $100. Find the

c. Let x = 10 and T = $100. Find the
governments optimal strategy in this case.
d. Let x = 10 and T = $100. Compute and

d. Let x = 10 and T = $100. Compute and
interpret the expected value of perfect
information (EVPI) in this decision problem.

Skill-Extending Problems

33. A city in Ohio is considering replacing its fleet of
    gasoline-powered automobiles with electric cars.
    The manufacturer of the electric cars claims that this
    municipality will experience significant cost savings
    over the life of the fleet if it chooses to pursue the
    conversion. If the manufacturer is correct, the city
    will save about $1.5 million dollars. If the new
    technology employed within the electric cars is
    faulty, as some critics suggest, the conversion to
    electric cars will cost the city $675,000. A third
    possibility is that less serious problems will arise
    and the city will break even with the conversion. A
    consultant hired by the city estimates that the
    probabilities of these three outcomes are 0.30, 0.30,
    and 0.40, respectively.
    The city has an opportunity to implement a

a. What actions should this city take to maximize
the expected savings?
b. Should the city implement the pilot program at a

and 0.40, respectively.
The city has an opportunity to implement a
pilot program that would indicate the potential cost
or savings resulting from a switch to electric cars.
The pilot program involves renting a small number
of electric cars for 3 months and running them under
typical conditions. This program would cost the city
$75,000. The citys consultant believes that the
results of the pilot program would be significant but
not conclusive; she submits Table 10.26 (page 398),
a compilation of probabilities based on the
experience of other cities, to support her contention.
For example, the first row of her table indicates that
given that a conversion to electric cars actually
results in a savings of $1.5 million, the conditional
probabilities that the pilot program will indicate that
the city saves money, loses money, and breaks even
are 0.6, 0.1, and 0.3, respectively.
a. What actions should this city take to maximize

b. Should the city implement the pilot program at a
cost of $75,000?
c. Compute and interpret the expected value of

cost of $75,000?
c. Compute and interpret the expected value of
sample information (EVSI) in this decision
problem.

* * *

| Actual Outcome of Conversion/Pilot Program Indication | Savings | Loss | Break Even |
| --- | --- | --- | --- |
| Savings | 0.6 | 0.1 | 0.3 |
| Loss | 0.1 | 0.4 | 0.5 |
| Break Even | 0.4 | 0.2 | 0.4 |

34. A manufacturer must decide whether to extend
    credit to a retailer who would like to open an
    account with the firm. Past experience with new
    accounts indicates that 45% are high-risk customers,
    35% are moderate-risk customers, and 20% are
    low-risk customers. If credit is extended, the
    manufacturer can expect to lose $60,000 with
    a high-risk customer, make $50,000 with a
    moderate-risk customer, and make $100,000 with a
    low-risk customer. If the manufacturer decides not
    to extend credit to a customer, the manufacturer
    neither makes nor loses any money.
    Prior to making a credit extension decision, the

neither makes nor loses any money.
Prior to making a credit extension decision, the
manufacturer can obtain a credit rating report on the
retailer at a cost of $2000. The credit agency
concedes that its rating procedure is not completely
reliable. In particular, the credit rating procedure
will rate a low-risk customer as a moderate-risk
customer with probability 0.10 and as a high-risk
customer with probability 0.05. Furthermore, the
given rating procedure will rate a moderate-risk
customer as a low-risk customer with probability
0.06 and as a high-risk customer with probability
0.07. Finally, the rating procedure will rate a
high-risk customer as a low-risk customer with
probability 0.01 and as a moderate-risk customer
with probability 0.05.
a. Find the strategy that maximizes the

a. Find the strategy that maximizes the
manufacturers expected net earnings.

b. Should the manufacturer routinely obtain credit
rating reports on those retailers who seek credit
approval? Why or why not?
c. Compute and interpret the expected value of

c. Compute and interpret the expected value of
sample information (EVSI) in this decision
problem.
35\. A television network earns an average of $1.6

problem.
35\. A television network earns an average of $1.6
million each season from a hit program and loses an
average of $400,000 each season on a program that
turns out to be a flop. Of all programs picked up by
this network in recent years, 25% turn out to be hits
and 75% turn out to be flops. At a cost of C dollars,
a market research firm will analyze a pilot episode
of a prospective program and issue a report
predicting whether the given program will end up
being a hit. If the program is actually going to be
a hit, there is a 90% chance that the market
researchers will predict the program to be a hit. If
the program is actually going to be a flop, there is a
20% chance that the market researchers will predict
the program to be a hit.
a. Assuming that C = $160,000, identify the

ational decision makers are sometimes willing to violate the EMV maximization criterion when large amounts of money are at stake. These decision
Rmakers are willing to sacrifice some EMV to reduce risk. Are you ever willing
to do so personally? Consider the following scenarios.

a. Assuming that C = $160,000, identify the
strategy that maximizes this television networks
expected profit in responding to a newly
proposed television program.
b. What is the maximum value of C that this

10.6 INCORPORATING ATTITUDES TOWARD RISK
R

1. You have a chance to enter a lottery where you will win $100,000 with probability
   0.1 or win nothing with probability 0.9. Alternatively, you can receive $5000 for
   certain. How many of youtruthfullywould take the certain $5000, even though

b. What is the maximum value of C that this
television network should be willing to incur in
choosing to hire the market research firm?
c. Compute and interpret the expected value of

choosing to hire the market research firm?
c. Compute and interpret the expected value of
perfect information (EVPI) in this decision
problem.

* * *

the EMV of the lottery is $10,000? Or change the $100,000 to $1,000,000 and the $5000 to $50,000 and ask yourself whether youd prefer the sure $50,000!

**2.** You can either buy collision insurance on your expensive new car or not buy it, where the insurance costs a certain premium and carries some deductible provision. If you decide to pay the premium, then you are essentially paying a certain amount to avoid a gamblethe possibility of wrecking your car and not having it insured. You can be sure that the premium is greater than the expected cost of damage; otherwise, the insurance company would not stay in business. Therefore, from an EMV standpoint you should not purchase the insurance. But how many of you drive without this type of insurance? These examples, the second of which is certainly realistic, illustrate situations where rational people do not behave as EMV maximizers. Then how do they act? This question has been studied extensively by many researchers, both mathematically and behaviorally. Although the answer is still not agreed upon universally, most researchers believe that if certain basic behavioral assumptions hold, people are expected utility maximizersthat is, they choose the alternative with the largest expected utility. Al- though we will not go deeply into the subject of expected utility maximization, the discussion in this section will acquaint you with the main ideas.

# Utility Functions

We begin by discussing an individuals utility function. This is a mathematical function that transforms monetary valuespayoffs and costsinto utility values. Essentially, an individuals utility function specifies the individuals preferences for various mon- etary payoffs and costs and, in doing so, it automatically encodes the individuals attitudes toward risk. Most individuals are risk averse, which means intuitively that they are willing to sacrifice some EMV to avoid risky gambles. In terms of the utility function, this means that every extra dollar of payoff is worth slightly less to the in- dividual than the previous dollar, and every extra dollar of cost is considered slightly more costly (in terms of utility) than the previous dollar. The resulting utility functions are shaped as shown in Figure 10.33. Mathematically, these functions are said to be **increasing and concave. The increasing part means that they go uphilleveryone** prefers more money to less money. The concave part means that they increase at a decreasing rate. This is the risk-averse behavior. There are two problems involved in implementing utility maximization in a real decision analysis. The first is obtaining an individuals (or companys) utility function; we will discuss this below. The second is using the resulting utility function to find the best decision. This second step is actually quite straightforward. We simply substitute

**FIGURE 10.33** Utility

Risk-Averse Utility Function

Monetary value

10.6 Incorporating Attitudes Toward Risk utility values for monetary values in the decision tree and then fold back as usual. That is, we calculate expected utilities at probability branches and take maximums (of expected utilities) at decision branches. We will look at a numerical example later in this section. So the real work involves finding an individuals (or companys) utility function in the first place.

### Assessing a Utility Function

We will outline a method that can be used to estimate a persons utility function. There are two things we must understand about this method. First, it asks the person to make a series of trade-offs. Because each of us has different attitudes toward risk, we will not all make the trade-offs in the same way. Therefore, each of us will obtain our own utility function. Second, even a particular persons utility function is not unique. If U (x) represents a persons utility function, then it turns out that aU (x) + b also describes that persons utility function, for any constants a and b with a > 0. They are equivalent in the sense that they lead to exactly the same decisions. We take advantage of this nonuniqueness by specifying two points on the utility function. Specifically, we begin by asking the person for two monetary values that represent the worst possible loss and the best possible gain imaginable. Lets say these values are − A and B. Then we arbitrarily assign utility values 0 and 1 to these two monetary values, that is, U (− A) = 0andU (B) = 1. Dont worry about the absolute magnitudes, 0 and 1, weve assignedwe could assign any other values, such as 14 and 320. The important thing is to use these as anchors and then obtain other utility values in terms of them. The procedure is as follows. Given any two known utility values, say, U (x) and _U (y),wherex and y are monetary values, we present the person with a choice between_ the following two options:

■Option 1: Obtain a certain payoff of z. ■Option 2: Obtain a payoff of either x or y, depending on the flip of a fair coin.

Then we ask the person to select the monetary value z in option 1 so that he or she is indifferent between the two options. If the person is indifferent, then the expected utilities from the two options must be equal. We will call the resulting value of z the **indifference value. This leads to the equation for U (z):**

_U (z) = 0.5U (x) + 0.5U (y)_ **(10.3)**

In words, we have generated a new utility value from two known utility values. This process continues until we have enough utility values to approximate a utility curve. (Note that if any of x, y,andz are negative, then payoff really means cost.) We will illustrate this procedure with the following example.

# EXAMPLE 10.6

## ASSESSING THE UTILITY FUNCTION FOR A SMALL BUSINESS

John Jacobs owns his own business. Because he is about to make an important decision where large losses or large gains are at stake, he wants to use the expected utility criterion to make his decision. He knows that he must first assess his own utility

Chapter 10 _Decision Making Under Uncertainty_ function, so he hires a decision analysis expert, Susan Schilling, to help him out. How
might the session between John and Susan proceed?

Solution

Susan first asks John for the largest loss and largest gain he can imagine. He answers
with the values $200,000 and $300,000, so she assigns utility values U (−200,000) = 0
and U (300,000) = 1 as anchors for the utility function. Now she presents John with
the choice between two options:

U(-200,,000)=0

■Option 1: Obtain a payoff of z (really a loss if z is negative).
Option 2: Obtain a loss of $200,000 or a payoff of $300,000, depending on the flip

■Option 2: Obtain a loss of $200,000 or a payoff of $300,000, depending on the flip
of a fair coin.

Susan reminds John that the EMV of option 2 is $50,000 (halfway between
−$200,000 and $300,000). He realizes this, but because he is quite risk averse, he
would far rather have $50,000 for certain than take the gamble in option 2. Therefore,
the indifference value of z must be less than $50,000. Susan then poses several values
of z to John. Would he rather have $10,000 for sure or take option 2? He says hed
rather take the $10,000. Would he rather pay $5000 for sure or take the gamble in option 2? (This is like an insurance premium.) He says hed rather take option 2. By this
time, we know the indifference value of z must be less than $10,000 and greater than
−$5000\. With a few more questions of this type, John finally decides on z = $5000 as
his indifference value. He is indifferent between obtaining $5000 for sure and taking
the gamble in option 2. We can substitute these values into equation (10.3):

U(S000)=055(-200,000)+0.5U(300,000)=0.5(0)+0.5(1)=0.5

Note that John is giving up $45,000 in EMV because of his risk aversion. The EMV of
the gamble in option 2 is $50,000, and he is willing to accept a sure $5000 in its place.
The process would then continue. For example, since she now knows U (5000) and

The process would then continue. For example, since she now knows U (5000) and
U (300,000), Susan could ask John to choose between these options:

■Option 1: Obtain a payoff of z.
Option 2: Obtain a payoff of $5000 or a payoff of $300,000, depending on the flip

■Option 2: Obtain a payoff of $5000 or a payoff of $300,000, depending on the flip
of a fair coin.

If John decides that his indifference value is now z = $130,000, then with equation (10.3) we know that

U130,000)=0.5U(5000)+0.5U(300,000)=0.5(0.5)+0.5(1)=0.78

Note that John is now giving up $22,500 in EMV because the EMV of the gamble in
option 2 is $152,500. By continuing in this manner, Susan can help John assess enough
utility values to approximate a continuous utility curve. ■

* * *

### Exponential Utility

For these reasons there are classes of ready-made utility functions that have been developed. One important class is called exponential utility and has been used in many financial investment analyses. An exponential utility function has only one adjustable numerical parameter, and there are straightforward ways to discover the most appropri- ate value of this parameter for a particular individual or company. So the advantage of using an exponential utility function is that it is relatively easy to assess. The drawback is that exponential utility functions do not capture all types of attitudes toward risk. Nevertheless, their ease of use has made them popular. An exponential utility function has the following form:

_U (x) = 1 − e_ −x / R **(10.4)**

Here x is a monetary value (a payoff if positive, a cost if negative), U (x) is the utility of this value, and R > 0 is an adjustable parameter called the risk tolerance. Basically, the risk tolerance measures how much risk the decision maker will tolerate. The larger the value of R, the less risk averse the decision maker is. That is, a person with a large value of R is more willing to take risks than a person with a small value of R. To assess a persons (or companys) exponential utility function, we need only to assess the value of R. There are a couple of tips for doing this. First, it has been shown that the risk tolerance is approximately equal to that dollar amount R such that the decision maker is indifferent between the following two options:

■Option 1: Obtain no payoff at all. ■Option 2: Obtain a payoff of R dollars or a loss of R/2 dollars, depending on the flip of a fair coin.

For example, if you are indifferent between a bet where you win $1000 or lose $500, with probability 0.5 each, and not betting at all, then your R is approximately $1000. From this criterion it certainly makes intuitive sense that a wealthier person (or company) ought to have a larger value of R. This has been found in practice. A second tip for finding _R is based on empirical evidence found by Ronald_ Howard, a prominent decision analyst. Through his consulting experience with sev- eral large companies, he discovered tentative relationships between risk tolerance and several financial variablesnet sales, net income, and equity. \[See Howard (1992).\] Specifically, he found that R was approximately 6.4% of net sales, 124% of net in- come, and 15.7% of equity for the companies he studied. For example, according to this prescription, a company with net sales of $30 million should have a risk tolerance of approximately $1.92 million. Howard admits that these percentages are only guide- lines. However, they do indicate that larger and more profitable companies tend to have larger values of R, which means that they are more willing to take risks involving given dollar amounts. We illustrate the use of the expected utility criterion, and exponential utility in particular, with the following example.

# EXAMPLE 10.7

## DECIDING WHETHER TO ENTER RISKY VENTURES AT VENTURE LIMITED

Venture Limited is a company with net sales of $30 million. The company currently must decide whether to enter one of two risky ventures or do nothing. The possible

Chapter 10 _Decision Making Under Uncertainty_

* * *

PRECISION
TREE

FIGURE 10.34
Dialog Box for
Specifying the
Exponential Utility
Criterion

outcomes of the less risky venture are a $0.5 million loss, a $0.1 million gain, and a $1
million gain. The probabilities of these outcomes are 0.25, 0.50, and 0.25. The possible
outcomes of the more risky venture are a $1 million loss, a $1 million gain, and a $3
million gain. The probabilities of these outcomes are 0.35, 0.60, and 0.05. If Venture
Limited can enter at most one of the two risky ventures, what should it do?

Solution

We will assume that Venture Limited has an exponential utility function. Also, based
on Howards guidelines, we will assume that the companys risk tolerance is 6.4% of
its net sales, or $1.92 million. (Well do a sensitivity analysis on this parameter later
on.) We can substitute into equation (10.4) to find the utility of any monetary outcome.
For example, the gain from doing nothing is $0, and its utility is

U(0)=1-e^{-0/1.92}=1-1=0

As another example, the utility of a $1 million loss is

U(-1)=1-e^{-(-1)/1.92}=1-1.683=-0.683

These are the values we use (instead of monetary values) in the decision tree.

USING PRECISIONTREE

Fortunately, PrecisionTree takes care of all the details. After we build a decision tree
and label it (with monetary values) in the usual way, we click on the name of the tree
(the box on the far left of the tree) to open the dialog box in Figure 10.34. We then fill
in the utility function information as shown in the upper right section of the dialog box.
This says to use an exponential utility function with risk tolerance 1.92. It also indicates
that we want expected utilities (as opposed to EMVs) to appear in the decision tree.

The completed tree for this example appears in Figure 10.35 (page 546). (See
the file VENTURE.XLS.) We build it in exactly the same way as usual and link
probabilities and monetary values to its branches in the usual way. For example, there
is a link in cell C22 to the monetary value in cell A10. However, the expected values
shown in the tree (those shown in color on your screen) are expected utilities,andthe
optimal decision is the one with the largest expected utility. In this case the expected
utilities for doing nothing, investing in the less risky venture, and investing in the more

* * *

**FIGURE 10.35**

Decision Tree for Risky Venture Example

risky venture are 0, 0.0525, and 0.0439. Therefore, the optimal decision is to invest in the less risky venture. Note that the EMVs of the three decisions are $0, $0.175 million, and $0.4 million. The latter two of these are calculated in row 14 as the usual sumproduct of monetary values and probabilities. So from an EMV point of view, the more risky venture is defi- nitely best. However, Venture Limited is sufficiently risk averse, and the monetary val- ues are sufficiently large, that the company is willing to sacrifice EMV to reduce its risk. How sensitive is the optimal decision to the key parameter, the risk tolerance? We can answer this by changing the risk tolerance (through the dialog box in Figure 10.34) and watching how the decision tree changes. 7 You can check that when the company becomes more risk tolerant, the more risky venture eventually becomes optimal. In fact, this occurs when the risk tolerance increases to approximately $2.075 million. In the other direction, when the company becomes less risk tolerant, the do nothing decision eventually becomes optimal. This occurs when the risk tolerance decreases to approximately $0.715 million. So the optimal decision depends heavily on the attitudes toward risk of Venture Limiteds top management.

## Certainty Equivalents Now suppose that Venture Limited has only two options. It

can either enter the less risky venture or receive a certain dollar amount x and avoid

We show the risk tolerance in cell B5, but the values in the decision tree are not linked to that cell. We need to go through the dialog box to change the risk tolerance.

Chapter 10 _Decision Making Under Uncertainty_ the gamble altogether. We want to find the dollar amount x such that the company is
indifferent between these two options. If it enters the risky venture, its expected utility
is 0.0525, calculated above. If it receives x dollars for certain, its (expected) utility is

FIGURE 10.36
Decision Tree with
Certainty Equivalents

U(x)=1-e^{-x/1.92}

−x /1.92
To find the value x where it is indifferent between the two options, we set 1 − e
−x /1.92
equal to 0.0525, or e = 0.9475, and solve for x. Taking natural logarithms of
both sides and multiplying by −1.92, we obtain

1-e^{-x/1.92}

e^{-x/1.92}=0.9475

x=-1.92\\ln(0.9475)\\approx50.104;\\mathrm{m i l l i o n}

This value is called the certainty equivalent of the risky venture. The company is
indifferent between entering the less risky venture and receiving $0.104 million to
avoid it. Although the EMV of the less risky venture is $0.175 million, the company
acts as if it is equivalent to a sure $0.104 million. In this sense, the company is willing
to give up the difference in EMV, $71,000, to avoid a gamble.
By a similar calculation, the certainty equivalent of the more risky venture is

By a similar calculation, the certainty equivalent of the more risky venture is
approximately $0.086 million. That is, the company acts as if this more risky venture
is equivalent to a sure $0.086 million, when in fact its EMV is a hefty $0.4 million!
So in this case it is willing to give up the difference in EMV, $314,000, to avoid this
particular gamble. Again, the reason is that the company dislikes risk. We can see these
certainty equivalents in PrecisionTree by adjusting the Display box in Figure 10.34
to show Certainty Equivalent. The tree then looks as in Figure 10.36. The certainty
equivalents we just discussed appear in cells C24 and C32.

Is Expected Utility Maximization Used?

|  | A | B | C | D |  |
| --- | --- | --- | --- | --- | --- |
| 16 |  |  |  |  |  |
| 17 | Risky ventures | None | FALSE | 0 |  |
| 18 | 0 | 0 |  |  |  |
| 19 | Which venture?0.10354 |  |  |  |  |
| 20 |  |  |  |  |  |
| 21 |  |  | Bad 25.0% -0.5 | 0.25-0.50000 |  |
| 22 |  |  | Outcome0.10354 |  |  |
| 23 | Less risky | TRUE |  |  |  |
| 24 |  | 0 | Fair 50.0% 0.1 | 0.50.10000 |  |
| 25 |  |  |  | Good 25.0% 1 | 0.251.00000 |
| 26 |  |  |  |  |  |
| 27 |  |  |  |  |  |
| 28 |  |  |  |  |  |
| 29 |  |  |  |  |  |
| 30 |  |  |  |  |  |
| 31 |  | More risky | FALSE | 0 | Outcome0.08620 |
| 32 |  |  |  |  |  |
| 33 |  |  |  |  |  |
| 34 |  |  |  |  |  |
| 35 |  |  |  |  |  |
| 36 |  |  |  |  |  |

The above discussion indicates that utility maximization is a fairly involved task. The
bottom line, then, is whether the difficulty is worth the trouble. Theoretically, expected
utility maximization might be interesting to researchers, but is it really used? The
answer appears to be: not very often. For example, one recent article on the practice
of decision making \[see Kirkwood (1992)\] quotes Ronald Howardthe same person
we quoted earlieras having found risk aversion to be of practical concern in only

* * *

5% to 10% of business decision analyses. This same article quotes the president of
a Fortune 500 company as saying, Most of the decisions we analyze are for a few
million dollars. It is adequate to use expected value (EMV) for these.
With these comments in mind, it is clear that knowledge of expected utility maxi-

With these comments in mind, it is clear that knowledge of expected utility maximization is an important requirement for anyone intending to specialize in the field. In
some of the greatest success stories, expected utility maximization was indeed implemented. For nonspecialists, however, a passing knowledge of the concepts is sufficient.

PROBLEMS

Skill-Building Problems

36. Suppose that a decision makers utility as a function
    of his wealth, x, is given by U (x) = ln x (the
    natural logarithm of x).
    a. Is this decision maker risk averse? Explain why

a. Is this decision maker risk averse? Explain why
or why not.
b. The decision maker now has $10,000 and two

b. The decision maker now has $10,000 and two
possible decisions. For decision 1, he loses $500
for certain. For decision 2, he loses $0 with
probability 0.9 and loses $5000 with probability
0.1. Which decision maximizes the expected
utility of his net wealth?
37\. An investor has $10,000 in assets and can choose

utility of his net wealth?
37\. An investor has $10,000 in assets and can choose
between two different investments. If she invests in
the first investment opportunity, there is an 80%
chance that she will increase her assets by $590,000
and a 20% chance that she will increase her assets
by $190,000. If she invests in the second investment
opportunity, there is a 50% chance that she will
increase her assets by $1.19 million and a 50%
chance that she will increase her assets by $1000.
This investor has an exponential utility function for
final assets with a risk tolerance parameter equal to
$600,000. Which investment opportunity will she
prefer?
38\. Consider again FreshWays decision problem

prefer?
38\. Consider again FreshWays decision problem
described in Example 10.3. Suppose now that
FreshWays utility function of profit π, earned from
the acquisition and sale of the 24,000 fluorescent
lightbulbs, is U (π) = ln(π). Find the course of
action that maximizes FreshWays expected utility.
How does this optimal decision compare to the
optimal decision with an EMV criterion? Explain
any difference in the two decisions.
39\. Consider again the landowners decision problem

U(x)=x^{2}

40. Consider again Techwares decision problem
    described in Problem 4. Suppose now that
    Techwares utility function of net revenue r
    (measured in dollars), earned from the given
    −r/350,000
    marketing opportunities, is U (r) = 1 − e.
    a. Find the course of action that maximizes

U(r)=\\tilde{1-e^{-r/350,000}}

a. Find the course of action that maximizes
Techwares expected utility. How does this
optimal decision compare to the optimal decision
with an EMV criterion? Explain any difference
in the two optimal decisions.
b. Repeat part a when Techwares utility function is

in the two optimal decisions.
b. Repeat part a when Techwares utility function is
−r/50,000
U (r) = 1 − e.
41\. Consider again the banks customer loan decision

\\bar{,,,,}^{\ {\ {}}r({)}}1-e^{-r/50,000}.

U (r) = 1 − e.
41\. Consider again the banks customer loan decision
problem in Problem 30. Suppose now that the
banks utility function of profit π (in dollars) is
−π/10,000
U (π) = 1 − e. Find the strategy that
maximizes the banks expected utility in this case.
How does this optimal strategy compare to the
optimal decision with an EMV criterion? Explain
any difference in two optimal strategies.

U(\\pi)=\\dot{1-e^{-\\pi/10,000}}

Skill-Extending Problems

42. Suppose that a decision maker has a utility
    function for monetary gains x given by
    0.5
    U (x) = (x + 10,000).
    a. Show that this decision maker is indifferent

U(x)=(x+10{,}000)^{0.5}

a. Show that this decision maker is indifferent
between gaining nothing (i.e., $0) and entering a
risky situation where she gains $80,000
with probability 1/3 and loses $10,000 with
probability 2/3.
b. If there is a 10% chance that one of the decision

potential loss of her cherished item?
43\. A decision maker is going to invest $2000 for a
period of 6 months. Two potential investments are
available to him: U.S. Treasury bills and gold. If this
decision maker invests the $2000 in T-bills, he is
sure to end the 6-month period with $2592. If this
decision maker invests in gold, there is a 75%
chance that he will end the 6-month period with

* * *

$800 and a 25% chance that he will end up with
$20,000. The decision makers utility function of
√
ending up with x dollars is U (x) = x.
a. Should this decision maker invest in gold or

U(x)={\\sqrt{x}}

a. Should this decision maker invest in gold or
T-bills?
b. Suppose the decision maker invests a proportion

b. Suppose the decision maker invests a proportion
y of his $2000 in T-bills and the remaining
fraction (1 − y) of his available funds in gold. In

this case his gain or loss from either investment
is reduced proportionally. For example, if he
invests half of his money in gold, he will either
lose $600 with probability 0.75 or gain $9000
with probability 0.25. Given the same utility
√
function U (x) = x, find the investors optimal
choice of y.

U(x)={\\sqrt{x}}

10.7 CONCLUSION
I

n this chapter we have discussed methods that can be used in decision-making
problems in which future uncertainty is a key element. Perhaps the most important
Iskill we can gain from this chapter is the ability to approach decision problems
that include uncertainty in a systematic manner. This systematic approach requires the
decision maker to list all possible decisions or strategies, list all possible uncertain
outcomes, assess the probabilities of these outcomes (possibly with the aid of Bayes

n this chapter we have discussed methods that can be used in decision-making
problems in which future uncertainty is a key element. Perhaps the most important
skill we can gain from this chapter is the ability to approach decision problems
that include uncertainty in a systematic manner. This systematic approach requires the
decision maker to list all possible decisions or strategies, list all possible uncertain
outcomes, assess the probabilities of these outcomes (possibly with the aid of Bayes

various parameters of the problem, a sensitivity analysis should be conducted to see
whether the best decision continues to be best within a range of problem parameters.

b. Which capacity level should Ford choose?
45\. You are CEO of the venture capital firm D&D. Billy

PROBLEMS

a. Explain why a capacity of 1,300,000 is not a
good choice.
b. Which capacity level should Ford choose?

44. Ford is going to produce a new vehicle, the Pioneer,
    and wants to determine the amount of annual
    capacity it should build. Fords goal is to maximize
    the profit from this vehicle over the next 10 years.
    Each vehicle will sell for $13,000 and incur a
    variable production cost of $10,000. Building 1 unit
    of annual capacity will cost $3000. Each unit of
    capacity will also cost $1000 per year to maintain,
    even if the capacity is unused. Demand for the
    Pioneer is unknown but marketing estimates the
    distribution of annual demand to be as shown in
    Table 10.27. Assume that unit sales during a year is
    the minimum of capacity and annual demand.
    a. Explain why a capacity of 1,300,000 is not a

Skill-Building Problems

45. You are CEO of the venture capital firm D&D. Billy
    comes to you with an investment proposition. You
    estimate that your distribution of cash flows from
    this investment is as shown in Table 10.28.

TABLE 10.27 Distribution of Annual
Demand

TABLE 10.28 Distribution of Cash
Flow

| Annual Demand | Probability |
| --- | --- |
| 400,000 | 0.25 |
| 900,000 | 0.50 |
| 1,300,000 | 0.25 |

a. If you are trying to maximize the expected value
of the firms cash flows, should you take the
project?

* * *

b. Suppose you assess your firm to be risk averse,
with an exponential utility function. You also use
the rule of thumb that the firms risk tolerance is
about 6.4% of its annual revenues, which are $30
million. Determine whether D&D should enter
the venture.
46\. Pizza King (PK) and Noble Greek (NG) are

46. Pizza King (PK) and Noble Greek (NG) are
    competitive pizza chains. Pizza King believes there
    is a 25% chance that NG will charge $6 per pizza, a
    50% chance NG will charge $8 per pizza, and a 25%
    chance that NG will charge $10 per pizza. If PK
    charges price p1 and NG charges price p2, PK will
    sell 100 + 25( p2 − p1) pizzas. It costs PK $4 to
    make a pizza. PK is considering charging $5, $6, $7,
    $8, or $9 per pizza. In order to maximize its
    expected profit, what price should PK charge for a
    pizza?
47. Sodaco is considering producing a new product:

p\_{1}

p\_{2}

100+25(\\dot{p\_{2}}-p\_{1})

pizza?
47\. Sodaco is considering producing a new product:
Chocovan soda. Sodaco estimates that the annual
demand for Chocovan, D (in thousands of cases),
has the following probability distribution:
P (D = 30) = 0.30, P(D = 50) = 0.40,
P (D = 80) = 0.30. Each case of Chocovan sells for
$5 and incurs a variable cost of $3. It costs $800,000
to build a plant to produce Chocovan. Assume that if
$1 is received every year (forever), this is equivalent
to receiving $10 at the present time. If Sodaco
decides to build the plant and produce Chocovan,
find the expected net present value of its profit.
48\. Many decision problems have the following simple

\\mathbf{I f}

P(D=30)=0.30,P(D=50)=0.40

P(D=80)=0.30.

find the expected net present value of its profit.
48\. Many decision problems have the following simple
structure. A decision maker has two possible
decisions, 1 and 2. If decision 1 is made, a sure cost
of c is incurred. If decision 2 is made, there are two
possible outcomes, with costs c1 and c2 and probabilities p and 1 − p. We assume that c1 < c < c2.
The idea is that decision 1, the riskless decision, has
a moderate cost, whereas decision 2, the risky
decision, has a low cost c1 or a high cost c2.
a. Find the decision makers cost table, that is, the

c\_{2}

p

c\_{1}<c<c\_{\\gamma}

1-p

c\_{1}

c\_{2}

a. Find the decision makers cost table, that is, the
cost for each possible decision and each possible
outcome.
b. Calculate the expected cost from the risky

49. During the summer, Olympic swimmer Adam
    Johnson swims every day. On sunny summer days
    he goes to an outdoor pool, where he may swim for
    no charge. On rainy days he must go to a domed
    pool. At the beginning of the summer, he has the
    option of purchasing a $15 season pass to the domed
    pool, which allows him use for the entire summer. If
    he doesnt buy the season pass, he must pay $1 each
    time he goes there. Past meteorological records

indicate that there is a 60% chance that the summer
will be sunny (in which case there is an average of 6
rainy days during the summer) and a 40% chance
the summer will be rainy (an average of 30 rainy
days during the summer).
Before the summer begins, Adam has the

b. Calculate the expected cost from the risky
decision.
c. List as many scenarios as you can think of that

Before the summer begins, Adam has the
option of purchasing a long-range weather forecast
for $1. The forecast predicts a sunny summer 80%
of the time and a rainy summer 20% of the time. If
the forecast predicts a sunny summer, there is a 70%
chance that the summer will actually be sunny. If the
forecast predicts a rainy summer, there is an 80%
chance that the summer will actually be rainy.
Assuming that Adams goal is to minimize his total
expected cost for the summer, what should he do?
Also find the EVSI and the EVPI.
50\. Erica is going to fly to London on August 5, and

Also find the EVSI and the EVPI.
50\. Erica is going to fly to London on August 5, and
return home on August 20. It is now July 1. On
July 1, she may buy a one-way ticket (for $350) or a
round-trip ticket (for $660). She may also wait until
August to buy a ticket. On August 1, a one-way
ticket will cost $370, and a round-trip ticket will
cost $730. It is possible that between July 1 and
August 1, her sister (who works for the airline) will
be able to obtain a free one-way ticket for Erica. The
probability that her sister will obtain the free ticket
is 0.30. If Erica has bought a round-trip ticket on
July 1 and her sister has obtained a free ticket, she
may return half of her round trip to the airline. In
this case, her total cost will be $330 plus a $50
penalty. Use a decision tree approach to determine
how to minimize Ericas expected cost of obtaining
round-trip transportation to London.
51\. A nuclear power company is deciding whether to

round-trip transportation to London.
51\. A nuclear power company is deciding whether to
build a nuclear power plant at Diablo Canyon or at
Roy Rogers City. The cost of building the power
plant is $10 million at Diablo and $20 million at
Roy Rogers City. If the company builds at Diablo,
however, and an earthquake occurs at Diablo during
the next 5 years, construction will be terminated and
the company will lose $10 million (and will still
have to build a power plant at Roy Rogers City).
Without further expert information the company
believes there is a 20% chance that an earthquake
will occur at Diablo during the next 5 years. For $1
million, a geologist can be hired to analyze the fault
structure at Diablo Canyon. She will predict either
that an earthquake will occur or that an earthquake
will not occur. The geologists past record indicates
that she will predict an earthquake on 95% of the
occasions for which an earthquake will occur and no
earthquake on 90% of the occasions for which an
earthquake will not occur. Should the power
company hire the geologist? Also find the EVSI and
the EVPI.

* * *

52. Joans utility function for her asset position x
    (for x between 0 and $160,000) is given by
    √
    U (x) = x /400.
    a. Is Joan risk averse? Explain.

U(x)=\\sqrt{x}/400

a. Is Joan risk averse? Explain.
b. Currently, Joans assets consist of $10,000 in

b. Currently, Joans assets consist of $10,000 in
cash and a $90,000 home. During a given year,
there is a 0.001 probability that Joans home will
be destroyed by fire or other causes. How much
should Joan be willing to pay for insurance that
covers her home completely from this type of
destruction?
53\. My current annual income is $40,000. I believe that

destruction?
53\. My current annual income is $40,000. I believe that
I owe $8000 in taxes. For $500, I can hire a CPA to
review my tax return. There is a 20% chance she
will save me $4000 in taxes and an 80% chance she
wont save me anything. If x is my disposable
income for the current year, my utility function is
√
given by U (x) = x /200.
a. Am I risk averse or risk seeking?

U(x)=\\sqrt{x}/200

a. Am I risk averse or risk seeking?
b. Should I hire the accountant?

b. Should I hire the accountant?

Skill-Extending Problems

54. City officials in Ft. Lauderdale, Florida, are trying to
    decide whether to evacuate coastal residents in
    anticipation of a major hurricane that may make
    landfall near their city within the next 48 hours.
    Based on previous studies, it is estimated that it will
    cost approximately 1 million dollars to evacuate the
    residents living along the coast of this major
    metropolitan area. However, if city officials choose
    not to evacuate their residents and the storm strikes
    Fort Lauderdale, there would likely be some deaths
    as a result of the hurricanes storm surge along the
    coast. While city officials are reluctant to place
    an economic value on the loss of human life
    resulting from such a storm, they realize that it may
    ultimately be necessary to do so to make a sound
    judgment in this situation. Prior to making the
    evacuation decision, city officials consult hurricane
    experts at the National Hurricane Center in Coral
    Gables regarding the accuracy of past predictions.
    They learn that in similar past cases, hurricanes that
    were predicted to make landfall near a particular
    coastal location actually did so 60% of the time.
    Moreover, they learn that in past similar cases
    hurricanes that were predicted not to make landfall
    near a particular coastal location actually did so

20% of the time. Finally, in response to similar
threats in the past, weather forecasters have issued
predictions of a major hurricane making landfall
near a particular coastal location 40% of the time.
a. Let L be the economic valuation of the loss of

a. Let L be the economic valuation of the loss of
human life resulting from a coastal strike by the
hurricane. Employ a decision tree to help these
city officials make a decision that minimizes the
expected cost of responding to the threat of the
impending storm as a function of L. To proceed,
you might begin by choosing an initial value of
L and then perform sensitivity analysis on
the optimal decision by varying this model
parameter. Summarize your findings.
b. For which values of L will these city officials

b. For which values of L will these city officials
always choose to evacuate the coastal residents,
regardless of the Hurricane Centers prediction?
55\. A homeowner wants to decide whether he should

TABLE 10.29 Expected Winter Heating Costs for Homeowners
Decision Problem

regardless of the Hurricane Centers prediction?
55\. A homeowner wants to decide whether he should
install an electronic heat pump in his home. Given
that the cost of installing a new heat pump is fairly
large, the homeowner would like to do so only if he
can count on being able to recover the initial
expense over five consecutive years of cold winter
weather. Upon reviewing historical data on the
operation of heat pumps in various kinds of winter
weather, he computes the expected annual costs of
heating his home during the winter months with and
without a heat pump in operation. These cost figures
are shown in Table 10.29. The probabilities of
experiencing a mild, normal, colder than normal,
and severe winter are 0.2(1 − x), 0.5(1 − x),
0.3(1 − x),andx, respectively.
a. Given that x = 0.1, what is the most that the

| Decision Alternatives | Mild | Normal | Colder than Normal | Severe |
| --- | --- | --- | --- | --- |
| Purchase pump | $420 | $590 | $720 | $900 |
| Don’t purchase pump | $358 | $503 | $612 | $765 |

a. Given that x = 0.1, what is the most that the
homeowner is willing to pay for the heat pump?
b. If the heat pump costs $500, how large must x be

b. If the heat pump costs $500, how large must x be
before the homeowner decides it is economically
worthwhile to install the heat pump?
c. Given that x = 0.1, compute and interpret the

c. Given that x = 0.1, compute and interpret the
expected value of perfect information (EVPI)
when the heat pump costs $500.
d. Repeat part c when x = 0.15.

d. Repeat part c when x = 0.15.
56\. Consider a company that manufactures computer

56. Consider a company that manufactures computer
    memory chips in lots of ten chips. From past
    experience, the company knows that 80% of all lots
    contain 10% defective chips, and 20% of all lots
    contain 50% defective chips. If an acceptable (that
    is, 10% defective) batch of chips is sent on to the
    next stage of production, processing costs of

* * *

$10,000 are incurred. If an unacceptable (that is,
50% defective) batch is sent on to the next stage of
production, processing costs of $40,000 are
incurred. This company also has the option of
reworking a batch of chips at a cost of $10,000. A
reworked batch is guaranteed to be acceptable.
Alternatively, at a cost of $1000, the company can
test one memory chip from each batch in an
attempt to determine whether the given batch is
unacceptable. If a randomly selected chip is found
to be defective, the batch from which the chip came
is acceptable with probability 8/18. If a randomly
selected chip is found not to be defective, the batch
from which the chip came is acceptable with
probability 72/82.
a. Determine how this company can minimize the

a. Determine how this company can minimize the
expected total cost per batch of computer
memory chips.
b. Compute and interpret the expected value of

b. Compute and interpret the expected value of
sample information (EVSI) in this decision
problem.
c. Compute and interpret the expected value of

problem.
d. Suppose now that this manufacturers utility
0.5
function of cost c per batch is U (c) =−c.
Find the strategy that maximizes the
manufacturers expected utility. How does this
optimal strategy compare to the optimal decision
with an EMV criterion? Explain any difference
in two optimal strategies.
57\. Patty is trying to determine whether to take

57. Patty is trying to determine whether to take
    management science or statistics. If she takes
    management science, she believes there is a 10%
    chance she will receive an A, a 40% chance she will
    receive a B, and a 50% chance she will receive C. If
    Patty takes statistics, she has a 70% chance of
    receiving a B, a 25% chance of a C, and a 5%
    chance of a D. Patty is indifferent between the
    following two options:
    ■Option 1: Receiving a B for certain

■Option 4: A 25% chance at an A and a 75%
chance at a D
In order to maximize the expected utility
associated with her final grade, which course should
Patty take?
58\. Many men over 50 take the PSA blood test. The

■Option 1: Receiving a B for certain
■Option 2: A 70% chance at an A and a 30%

in Quebec City into two groups. Two-thirds of the
men were asked to be tested for prostate cancer and
one-third were not asked. Eventually, 8137 men
were screened for prostate cancer (PSA plus digital
rectal exam) in 1989; 38,056 men were not
screened. By 1997 only 5 of the screened men had
died of prostate cancer while 137 of the men who
were not screened had died of prostate cancer.
(Source: New York Times May 19,1998)
a. Discuss why this study seems to indicate that

a. Discuss why this study seems to indicate that
screening for prostate cancer saves lives.
b. Despite the results of this study, many doctors

b. Despite the results of this study, many doctors
are not convinced that early screening for
prostate cancer saves lives. Can you see why they
doubt the conclusions of the study?
59\. You have just been chosen to appear on Hoosier

doubt the conclusions of the study?
59\. You have just been chosen to appear on Hoosier
Millionaire! The rules are as follows: There are
four hidden cards. One says STOP and the other
three have dollar amounts of $150,000, $200,000,
and $1,000,000. You get to choose a card. If the card
says STOP, you win no money. At any time you
may quit and keep the largest amount of money that
has appeared on any card you have chosen, or you
may continue. If you continue and choose the STOP
card, however, you win no money. As an example,
you might first choose the $150,000 card, then the
$200,000 card, and then choose to quit and receive
$200,000.
a. If your goal is to maximize your expected payoff,

a. If your goal is to maximize your expected payoff,
what strategy should you follow?
b. Suppose your utility function for an increase in

what strategy should you follow?
b. Suppose your utility function for an increase in
cash satisfies U (0) = 0, U ($40,000) = 0.25,
U ($120,000) = 0.50, U ($400,000) = 0.75 and
U ($1,000,000) = 1. Are you risk averse?
Explain.
c. After drawing a curve through the points in part

c. After drawing a curve through the points in part
b, determine a strategy that maximizes your
expected utility. (Alternatively, you might want
to assess and use your actual utility function.)
60\. You are trying to determine how much money to put

a. If you are risk neutral and want to maximize
your expected disposable income, how much
should you put in your TSB?

60. You are trying to determine how much money to put
    in your Tax Saver Benefit (TSB) plan. At the
    beginning of the calendar year, a TSB allows you
    to put money into an account. The money in
    the account can be used to pay for medical
    expenses incurred during the year. Once the TSB is
    exhausted, you must pay the medical expenses out
    of pocket. The benefit of the TSB is that money
    placed in the TSB is not subject to federal taxes. The
    catch is that any money left in the TSB at the end of
    the year is lost to you. Suppose the federal tax rate is
    40% and your current annual salary is $50,000. You
    believe that it is equally likely that your medical
    expenses during the current year will be $3000,
    $4000, $5000, $6000, or $7000.
    a. If you are risk neutral and want to maximize b. Suppose you assess a utility function for
    disposable income given by U (x) =
    0.713595
    0.000443x.(Whosaidtheyallhaveto
    have nice round numbers?) Are you risk averse?
    How much should you put in the TSB?
61. Peter is thinking of purchasing an advertising

0.\\dot{0}0043x^{0.713595}

How much should you put in the TSB?
61\. Peter is thinking of purchasing an advertising
company from Amanda. At present, only Amanda
(not Peter) knows the current value of the company.
Peter knows, however, that there is an equal chance
that the company is worth 10, 20, 30, 40, 50, 60, 70,
80, 90, or 100 million dollars. Amanda will accept
an offer from Peter only if Peter bids at least the
value of the company. For example, if Amanda
knows the company is worth $20 million, she will
accept any bid of $20 million or higher. As soon as
Peter purchases the company, his reputation as a
skilled businessman immediately increases the
actual value of the company by 80%.
a. Suppose Peter is risk neutral and is considering

actual value of the company by 80%.
a. Suppose Peter is risk neutral and is considering
bidding 10, 20, 30, 40, 50, 60, 70, 80, 90, or 100
million dollars. What should he bid?
b. Suppose Peters utility function for financial

b. Suppose Peters utility function for financial
gains or losses (in millions of dollars) is given by
1.7
U (x) = ((x + 82)/144). Determine whether
Peter is risk averse or risk seeking and determine
Peters optimal decision.
62\. Sarah Chang is the owner of a small electronics

p\_{1}

\\bar{U}(x)=((x+82)/144)^{1

If she continues the project, Chang must invest
$200,000 in research and development. In addition,
making a proposal (which she will decide whether
to do after seeing whether the R&D is successful or
not) requires developing a prototype timing system
at an additional cost of $50,000. Finally, if Chang
wins the contract, the finished product will cost an
additional $150,000 to produce.
a. Develop a decision tree that can be used to solve

Peters optimal decision.
62\. Sarah Chang is the owner of a small electronics
company. In 6 months a proposal is due for an
electronic timing system for the 1998 Olympic
Games. For several years, Changs company has
been developing a new microprocessor, a critical
component in a timing system that would be superior
to any product currently on the market. However,
progress in research and development has been slow,
and Chang is unsure about whether her staff can
produce the microprocessor in time. If they succeed
in developing the microprocessor (probability p1),
there is an excellent chance (probability p2)that
Changs company will win the $1 million Olympic
contract. If they do not, there is a small chance
(probability p3) that she will still be able to win the
same contract with an alternative, inferior timing
system that has already been developed.

p\_{1})

p\_{2},

p\_{3},

p\_{3}

p\_{1},p\_{2}

cells) and automatically see her optimal EMV
and optimal strategy from the tree.
If p2 = 0.8andp3 = 0.1, what value of p1

b. If p2 = 0.8andp3 = 0.1, what value of p1
makes Chang indifferent between abandoning
the project and going ahead with it?
c. How much would Chang be willing to pay the

p\_{3}=0.1

p\_{1}=0.4,

c. How much would Chang be willing to pay the
Olympic organization (now) to guarantee her the
contract in the case where her company is
successful in developing the contract? (This
guarantee is in force only if she is successful in
developing the product.) Assume p1 = 0.4,
p2 = 0.8, and p3 = 0.1.
d. Suppose now that this a big project for Chang.

p\_{2}=0.8.

d. Suppose now that this a big project for Chang.
Therefore, she decides to use expected utility as
her criterion, with an exponential utility function.
Using some trial and error, see which risk
tolerance changes her initial decision from go
ahead to abandon when p1 = 0.4, p2 = 0.8,
and p3 = 0.1.
63\. Suppose an investor has the opportunity to buy the

p\_{1}=0.4,,p\_{2}=0.8

and p3 = 0.1.
63\. Suppose an investor has the opportunity to buy the
following contract, a stock call option, on March 1.
The contract allows him to buy 100 shares of ABC
stock at the end of March, April, or May at a
guaranteed price of $50 per share. He can exercise
this option at most once. For example, if he
purchases the stock at the end of March, he cant
purchase more in April or May at the guaranteed
price. The current price of the stock is $50. Each
month, we assume the stock price either goes up by
a dollar (with probability 0.6) or down by a dollar
(with probability 0.4). If the investor buys the
contract, he is hoping that the stock price will go up.
The reasoning is that if he buys the contract, the
price goes up to $51, and he buys the stock (that is,
he exercises his option) for $50, he can turn around
and sell the stock for $51 and make a profit of $1 per
share. On the other hand, if the stock price goes
down, he doesnt have to exercise his option; he can
just throw the contract away.
a. Use a decision tree to find the investors optimal

a. Use a decision tree to find the investors optimal
strategy (that is, when he should exercise the
option), assuming he purchases the contract.
b. How much should he be willing to pay for such a

b. How much should he be willing to pay for such a
contract?
64\. The Ventron Engineering Company has just been

contract?
64\. The Ventron Engineering Company has just been
awarded a $2 million development contract by the
U.S. Army Aviation Systems Command to develop
a blade spar for its Heavy Lift Helicopter program.
The blade spar is a metal tube that runs the length of
and provides strength to the helicopter blade. Due to
the unusual length and size of the Heavy Lift
Helicopter blade, Ventron is unable to produce a
single-piece blade spar of the required dimensions,
using existing extrusion equipment and material.
The engineering department has prepared two below.
The sectioning option involves joining several
shorter lengths of extruded metal into a blade spar of
sufficient length. This work will require extensive
testing and rework over a 12-month period at a total
cost of $1.8 million. While this process will
definitely produce an adequate blade spar, it merely
represents an extension of existing technology.
To improve the extrusion process, on the other

represents an extension of existing technology.
To improve the extrusion process, on the other
hand, it will be necessary to perform two steps:
(1) improve the material used, at a cost of $300,000,
and (2) modify the extrusion press, at a cost of
$960,000. The first step will require 6 months of
work, and if this first step is successful, the second
step will require another 6 months of work. If both
steps are successful, the blade spar will be available
at that time, that is, a year from now. The engineers
estimate that the probabilities of succeeding in
steps 1 and 2 are 0.9 and 0.75, respectively.
However, if either step is unsuccessful (which will
be known only in 6 months for step 1 and in a year
for step 2), Ventron will have no alternative but to
switch to the sectioning processand incur the
sectioning cost on top of any costs already incurred.
Development of the blade spar must be

Development of the blade spar must be
completed within 18 months to avoid holding up the
rest of the contract. If necessary, the sectioning work
can be done on an accelerated basis in a 6-month
period, but the cost of sectioning will then increase
from $1.8 million to $2.4 million.
Frankly, the Director of Engineering, Dr.

a. Develop a decision tree to maximize Ventrons
EMV. This includes the revenue from this
project, the side benefits (if applicable) from an
improved extrusion process, and relevant costs.
You dont need to worry about the time value of
money; that is, no discounting or NPVs are
required. Summarize your findings in words in
the spreadsheet.
b. What value of side benefits would make Ventron

from $1.8 million to $2.4 million.
Frankly, the Director of Engineering, Dr.
Smith, wants to try developing the improved
extrusion process. This is not only cheaper (if
successful) for the current project, but its expected
side benefits for future projects could be sizable.
Although these side benefits are difficult to gauge,
Dr. Smiths best guess is an additional $2 million.
(Of course, these side benefits are obtained only if
both steps of the modified extrusion process are
completed successfully.)
a. Develop a decision tree to maximize Ventrons

b. What value of side benefits would make Ventron
indifferent between the two alternatives?
c. How much would Ventron be willing to pay,

c. How much would Ventron be willing to pay,
right now, for perfect information about both

steps of the improved extrusion process? (This
information would tell Ventron, right now, the
ultimate success/failure outcomes of both steps.)
65\. Ligature, Inc. is a company that does contract work

65. Ligature, Inc. is a company that does contract work
    for publishing companies. It specializes in writing
    textbooks for secondary schools. Because states
    such as Texas and California typically adopt only
    about four to eight textbooks for any given subject
    and grade level (from which individual schools can
    choose), the potential for large profits is great.
    Ligature is currently negotiating a contract with

choose), the potential for large profits is great.
Ligature is currently negotiating a contract with
Brockway and Coates (B&C), a large publishing
company, to write a social studies series for grades
912\. Actually, the development of the books is
already well under way, and the only details not yet
worked out concern the fee B&C will pay Ligature.
Ligature has always operated on a fixed fee basis.
Under this arrangement, B&C would pay Ligature
its costs, in this case $4.15 million, plus 25%.
Ligature would receive this payment in 6 months, at
the beginning of year 1. Although this is still an
option, the companies have also been discussing a
royalty arrangement as an alternative.
Under the royalty plan, B&C would still pay

royalty arrangement as an alternative.
Under the royalty plan, B&C would still pay
Ligature its $4.15 million costs at the beginning of
year 1, but Ligature would then receive yearly
royalty payments at the ends of years 1 through 5.
These payments would depend on (1) total sales over
the five years, (2) the timing of sales, and (3) the
negotiated royalty rate, that is, Ligatures percentage
of each sales dollar. As for timing, both parties agree
that 10% of total sales will be in year 1, 20% will be
in each of the next 2 years, 30% will be in year 4,
and 20% will be in year 5. They also estimate that
the probability distribution of total sales is discrete,
with possible values $25 million, $30 million, $50
million, and $70 million, and corresponding
probabilities 0.10, 0.45, 0.30, and 0.15.
To guard its interests, B&C has imposed the

Ligature is interested in maximizing the NPV
of its profit from this project (discounted back to the
beginning of year 1), using a 10% discount rate. The
following steps lead you through the required
calculations to solve the problem. No decision
tree is required for this problem.
a. The file P10\_65.XLS supplies the inputs in an

tree is required for this problem.
a. The file P10\_65.XLS supplies the inputs in an
input section (blue border), and it has a
calculation section (red border). First, calculate
the upper part of the calculation section. To do so, enter any trial value for total sales in cell G8
and do the necessary calculations to eventually
find (in cell G17) the NPV to Ligature from the
royalty agreement. At this point, you can use any
royalty rate in the RoyRate cell (C28).
Using the calculations from part a, complete the

b. Using the calculations from part a, complete the
data table in the middle part of the calculation
section. It should show the NPV to Ligature for
any potential value of total sales. Then use these
NPVs to calculate the expected NPV to Ligature
in the ExpNPV cell (G27).
c. Suppose the current offer on the table is a 3%

in the ExpNPV cell (G27).
c. Suppose the current offer on the table is a 3%
royalty rate. In the bottom part of the calculation
section, use IF comparisons to see which
arrangement, fixed fee or royalty, each party
would favor.
d. Continuing part c (with the 3% offer on the

d. Continuing part c (with the 3% offer on the
table), what do you think the two parties will
eventually agree upon? That is, will they
stick with the 3% royalty rate, move to a
different royalty rate, or settle on the fixed fee
arrangement? Answer below cell B36.
66\. The American chess master Jonathan Meller is

66. The American chess master Jonathan Meller is
    playing the Soviet expert Yuri Gasparov in a
    two-game exhibition match. Each win earns a player
    one point, and each draw earns a half point. The
    player who has the most points after two games
    wins the match. If the players are tied after two
    games, they play until one wins a game; then the
    first player to win a game wins the match. During
    each game, Meller has two possible strategies: to
    play a daring strategy or to play a conservative
    strategy. His probabilities of winning, losing, and
    drawing when he follows each strategy are shown in
    Table 10.30. To maximize his probability of winning
    the match, what should the American do?

67. Based on Balson et al. (1992). An electric utility
    company is trying to decide whether to replace its
    PCB transformer in a generating station with a new
    and safer transformer. To evaluate this decision, the
    utility needs information about the likelihood of an
    incident, such as a fire, the cost of such an incident,
    and the cost of replacing the unit. Suppose that the
    total cost of replacement as a present value is
    $75,000. If the transformer is replaced, there is
    virtually no chance of a fire. However, if the current
    transformer is retained, the probability of a fire is


TABLE 10.30 Probabilities for Chess
Problem

| Strategy | Win | Loss | Draw |
| --- | --- | --- | --- |
| Daring | 0.45 | 0.55 | 0.00 |
| Conservative | 0.00 | 0.10 | 0.90 |

assessed to be 0.0025. If a fire occurs, then the
cleanup cost could be high ($80 million) or low ($20
million). The probability of a high cleanup cost,
given that a fire occurs, is assessed at 0.2.
a. If the company uses EMV as its decision

a. If the company uses EMV as its decision
criterion, should it replace the transformer?
b. Perform a sensitivity analysis on the key

b. Perform a sensitivity analysis on the key
parameters of the problem that are difficult to
assess, namely, the probability of a fire, the
probability of a high cleanup cost, and the high
and low cleanup costs. Does the optimal decision
from part a remain optimal for a wide range of
these parameters?
c. Do you believe EMV is the correct criterion

c. Do you believe EMV is the correct criterion
to use in this type of problem involving
environmental accidents?
68\. Based on Mellichamp et al. (1993). Construction

68. Based on Mellichamp et al. (1993). Construction
    equipment managers typically have many large
    pools of engines, transmissions, and other equipment units to maintain. One approach to this
    maintenance is to use oil analysis, where the oil
    from any of these is subjected periodically to an
    inspection. These inspections can sometimes signal
    an impending failure (for example, too much iron in
    the oil), and preventive maintenance is then
    performed (at a relatively low cost), eliminating the
    risk of failure (failure would result in a relatively
    high cost). However, oil analysis costs money, and it
    is not perfect. That is, it can indicate that a unit is
    defective when in fact it is not about to fail, and it
    can indicate that a unit is nondefective when in fact
    it is about to fail. As a possible substitute for oil
    analysis, the company could simply change the oil
    periodically, thereby reducing the probability of a
    failure.
    Suppose the company has four alternatives:

failure.
Suppose the company has four alternatives:
(1) do nothing, (2) use oil analysis only, (3) replace
oil only, or (4) replace oil and do oil analysis. For
option (1) the probability of a failure is p1,andthe
cost of a failure is C1. For option (2), the probability
of a failure remains at p1. If the unit is about to fail,
the oil analysis will indicate this with probability
1 − α; if the unit is not about to fail, the oil analysis
will indicate this with probability 1 − β. (Therefore,
α and β are the error probabilities of the oil
analysis.) The oil analysis itself costs C2, and if it
indicates that a failure is about to occur, the oil will
be changed, at cost C3, and preventive maintenance
will be performed. The cost of maintenance to
restore a unit that is about to fail is C4, whereas the
cost of maintenance for a unit that is not about to
fail is C5. The only difference between options (3)
and (4) is that the probability of a failure decreases
to p2 after changing the oil. The values of these
parameters for a particular class of units (engines in
light trucks, say) appear in Table 10.31 (page 556).

1-\\beta.

C\_{1}

p\_{1}

p\_{2}

* * *

TABLE 10.31 Parameters for Oil Analysis
Problem

| Parameter | Value |
| --- | --- |
| $p\_{1}$ | 0.10 |
| $p\_{2}$ | 0.04 |
| $\\alpha$ | 0.30 |
| $\\beta$ | 0.20 |
| $C\_{1}$ | $1200.00 |
| $C\_{2}$ | $20.00 |
| $C\_{3}$ | $14.80 |
| $C\_{4}$ | $500.00 |
| $C\_{5}$ | $250.00 |

p\_{1}

\\alpha

p\_{2}

\\beta

C\_{1}

C\_{2}

C\_{3}

C\_{4}

b. If the company has 500 units, what should it do?
What is the expected cost for the entire fleet?
c. Suppose that the company has different types of

C\_{5}

c. Suppose that the company has different types of
units. For example, the cost of an oil change
might be higher for some, or the cost of a failure
might be higher or lower. Run a sensitivity
analysis on any of the parameters you believe
might be key parameters and see whether the
optimal decision changes in ways you would
anticipate.
69\. Based on Hess (1993). A company that is heavily

69. Based on Hess (1993). A company that is heavily
    involved in R&D projects believes it might have the
    potential to develop a very lucrative commercial
    product that would (if successful) reduce pulp mill
    water pollution. At the current stage, however,
    everything is quite uncertain, and the company is
    trying to decide whether to go ahead with its R&D
    or abandon the product. The following are the
    primary risks:
    ■Would market tests confirm that there is a

■Even if there is a significant market and the
process is technically feasible, would the
companys board sanction the new plant
capital necessary to produce the product on a
commercial scale?
■Assuming the answers to the above questions are

significant market for the product?
■Could the company develop a new process for
making this productthat is, is it technically
feasible?
■Even if there is a significant market and the

TABLE 10.32 Probabilities for Water
Pollution Problem

0.6\\pm0.15

0.6\\pm0.15

0.8\\pm0.2

| Event | Probability |
| --- | --- |
| Significant market | 0.6±0.15 |
| Technically feasible | 0.6±0.15 |
| Board sanctions plant expenditures | 0.8±0.2 |
| Commercial success | 0.8±0.2 |

indicates the companys uncertainty about the true
probabilities.
The primary economic factors are the

The primary economic factors are the
following:
■the research expenses to identify a new

■the research expenses to identify a new
production process for the product
■the marketing development cost to determine

■the marketing development cost to determine
whether there is a significant market
■the process development costs, including

whether there is a significant market
■the process development costs, including
presanction engineering
■the commercial development costs, both before

■the commercial development costs, both before
and after the boards sanction
■the venture value (net present value) if successful

and after the boards sanction
■the venture value (net present value) if successful
The estimates of these values are shown in Table
10.33. Again, the plus-or-minus values indicate the
companys considerable uncertainty about the
values. All values are in millions of dollars.
The timing of events is as follows:

The timing of events is as follows:
Decide whether to abandon product now. (This is

The timing of events is as follows:
■Decide whether to abandon product now. (This is
really the only nontrivial decision the company
will make.) If not, then:
■Spend on research and marketing development. If

■Spend on research and marketing development. If
marketing development indicates an insignificant
market for the product or research indicates that
the process is technically infeasible, cut expenses
and quit. Otherwise:
Spend on process and commercial development.

■Spend on process and commercial development.
If company board then declines to sanction
money for plant, cut expenses and quit.
Otherwise:
Spend on further commercial development. By

Analyze the companys problem. Obviously,
with the high degree of uncertainty, sensitivity
analysis is the key. Note that there are many
uncertainties about the input parameters in
Tables 10.32 and 10.33. In fact, there are far too
many to allow you to try every combination.
Therefore, just try a few combinations that you
believe might be the most important.

* * *

TABLE 10.33 Monetary Estimates for Water Pollution Problem

| Expense or Gain | Net Present Value |
| --- | --- |
| Research expense | $0.8±25% |
| Market development expense | $0.2±25% |
| Process development expense (presanction) | $3.0±25% |
| Commercial development expense (presanction) | $0.5±25% |
| Commercial development expense (postsanction) | $1.0±25% |
| Value if successful | $25.0±50% |

80.8\\pm25%

80.2\\pm25%

53.0\\pm25%

80.5\\pm25%

81.0\\pm25%

525.0\\pm50%

* * *

GMC Motor Company II
T

his case is a continuation of GMC I (from
Chapter 6). Management at GMC is gener-
Tally pleased with the modeling effort that
has been done for capacity planning in the coming
year. However, some managers have asked about
the effect demand forecasts for the second year out
could have on the recommended strategy.
Although demand forecasts for the coming year

Although demand forecasts for the coming year
are considered to be quite reliable, forecasts two or
more years in the future have been less accurate.
Accordingly, analysts at GMC formulate several demand scenarios in the future, and assign probabilities to each scenario. The situation for the coming
two years is summarized in Table 10.34.
Three demand scenarios are possible in the sec-

two years is summarized in Table 10.34.
Three demand scenarios are possible in the second year. Scenario A corresponds to a robust economic expansion and increasing market share for
GMC cars. Scenario B represents little change from
the first year, although there is a relative shift away
from the smaller Lyra to the larger Libra and Hydra models. Scenario C represents an economic recession and decreased demand for all car lines. In
scenario C, the decrease in demand for Libras and
Hydras is larger than for the economical Lyras. Analysts give scenario A a slightly higher probability
of occurring than scenarios B and C.
Management at GMC wants to consider all possible configurations of capacity in the next two years.

of occurring than scenarios B and C.
Management at GMC wants to consider all possible configurations of capacity in the next two years.
As before, the Lyra and/or Libra plants can be retooled, but retooling can be done in either the first
or second year. Because of the enormous costs of
changing a plant configuration, a plant that is retooled in the first year cannot be returned to its original configuration in the second year. The costs and
characteristics of the original and retooled plants are
the same in either year. For convenience, these are
repeated in Table 10.35.
In addition to selecting the plant configurations

on the observed demand, GMC plans its production accordingly. For example, in the second year,
GMC must decide on its plant configurations before
the demand scenario is revealed, but can determine
its production plan after the demand scenario is revealed. This sequence of events is consistent with
the relative time periods involved. Reconfiguring a
plant is a major undertaking that must be planned in
advance, so this decision must be made before the
demand scenario is revealed. Production during a
year can be altered to best meet the demand as it develops during the year. For modeling purposes, the
production decision can be made after the demand
scenario is revealed. Also, no inventory is carried
from one year to the next.
The demand diversion matrix is assumed to be

The demand diversion matrix is assumed to be
constant for both years. For convenience, it is repeated in Table 10.36.

Questions

GMC wants to decide whether to retool the Lyra and
Libra plants in each of the coming two years. In addition, GMC wants to determine its production plan at
each plant for each year. Based on the previous data,
formulate a mixed integer programming model for
solving GMCs production planningcapacity expansion problem for the coming two years. Assume
that GMCs objective is to maximize total average
profit for the two years. For simplicity, assume that
no discounting of profits is done for the second year.
In the past, GMC had solved problems sepa-

In the past, GMC had solved problems separately for each scenario. The three optimal solutions
were compared and then a final decision was made.
What are the three optimal solutions corresponding
to each scenario? (For example, assuming that scenario A occurs with probability 1.0, what is the optimal solution? Then repeat for scenarios B and C.)
How do the three separate optimal solutions com-
8
pare to the overall optimal solution found before?

8
Acknowledgment: The idea for GMC I and II came from
Eppen et al. (1989).

* * *

TABLE 10.34

Demand Forecasts and Probabilities for
GMC Case Study

|  |  | Second Year |  |  |
| --- | --- | --- | --- | --- |
| Model | First Year | Scenario A | Scenario B | Scenario C |
| Lyra | 1400 | 1700 | 1300 | 1300 |
| Libra | 1100 | 1500 | 1200 | 800 |
| Hydra | 800 | 1100 | 850 | 600 |
| Probability | 1 | 0.4 | 0.3 | 0.3 |

TABLE 10.35 Plant Characteristics for GMC Case Study

|  | Lyra | Libra | Hydra | New Lyra | New Libra |
| --- | --- | --- | --- | --- | --- |
| Capacity(in 1000s) | 1000 | 800 | 900 | 1600 | 1800 |
| Fixed cost(in $ millions) | 2000 | 2000 | 2600 | 3400 | 3700 |
| Profit Margin by Car Line(in 1000s) |  |  |  |  |  |
| Lyra | 2 | - | - | 2.5 | 2.3 |
| Libra | - | 3 | - | 3 | 3.5 |
| Hydra | - | - | 5 | - | 4.8 |

| TABLE 10.36 Demand Diversion Matrix for GMC Case Study |  |  |  |
| --- | --- | --- | --- |
|  | Lyra | Libra | Hydra |
| Lyra | - | 0.3 | 0.05 |
| Libra | 0 | - | 0.10 |
| Hydra | 0 | 0.0 | - |

* * *

Jogger Shoe Company
T

he Jogger Shoe Company is trying to decide whether to make a change in its most
Tpopular brand of running shoes. The new
style would cost the same to produce, and it would
be priced the same, but it would incorporate a new
kind of lacing system that (according to its marketing research people) would make it more popular.
There is a fixed cost of $300,000 of changing over
to the new style. The unit contribution to before-tax
profit for either style is $8. The tax rate is 35%. Also,
because the fixed cost can be depreciated and will
therefore affect the after-tax cash flow, we need a
depreciation method. We assume it is straight-line
depreciation.
The current demand for these shoes is 190,000

The current demand for these shoes is 190,000
pairs annually. The company assumes this demand

will continue for the next 3 years if the current style
is retained. However, there is uncertainty about demand for the new style, if it is introduced. The company models this uncertainty by assuming a normal
distribution in year 1, with mean 220,000 and standard deviation 20,000. The company also assumes
that this demand, whatever it is, will remain constant
for the next 3 years. However, if demand in year 1
for the new style is sufficiently low, the company can
always switch back to the current style and realize
an annual demand of 190,000. The company wants a
strategy that will maximize the expected net present
value (NPV) of total cash flow for the next 3 years,
where a 15% interest rate is used for the purpose of
calculating NPV.

* * *

Westhouser Paper Company
T

he Westhouser Paper Company in the state
of Washington currently has an option to
Tpurchase a piece of land with good timber
forest on it. It is now May 1, and the current price
of the land is $2.2 million. Westhouser does not
actually need the timber from this land until the
beginning of July, but its top executives fear that
another company might buy the land between now
and the beginning of July. They assess that there is 1
chance out of 20 that a competitor will buy the land
during May. If this does not occur, they assess that
there is 1 chance out of 10 that the competitor will
buy the land during June. If Westhouser does not take
advantage of its current option, it can attempt to buy
the land at the beginning of June or the beginning of
July, provided that it is still available.
Westhousers incentive for delaying the pur-

Westhousers incentive for delaying the purchase is that its financial experts believe there is a
good chance that the price of the land will fall significantly in one or both of the next two months. They
assess the possible price decreases and their probabilities in Tables 10.37 and 10.38. Table 10.37 shows

| Price Decrease | Probability |
| --- | --- |
| $0 | 0.5 |
| $60,000 | 0.3 |
| $120,000 | 0.2 |

the probabilities of the possible price decreases during May. Table 10.38 shows the conditional probabilities of the possible price decreases in June, given
the price decrease in May. For example, if the price
decrease in May is $60,000, then the possible price
decreases in June are $0, $30,000, and $60,000 with
respective probabilities 0.6, 0.2, and 0.2.
If Westhouser purchases the land, it believes

TABLE 10.38 Distribution of Price Decrease in June

| Price Decrease in May |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| $0 |  | $60,000 |  | $120,000 |  |
| June Decrease | Probability | June Decrease | Probability | June Decrease | Probability |
| $0 | 0.3 | $0 | 0.6 | $0 | 0.7 |
| $60,000 | 0.6 | $30,000 | 0.2 | $20,000 | 0.2 |
| $120,000 | 0.1 | $60,000 | 0.2 | $40,000 | 0.1 |
