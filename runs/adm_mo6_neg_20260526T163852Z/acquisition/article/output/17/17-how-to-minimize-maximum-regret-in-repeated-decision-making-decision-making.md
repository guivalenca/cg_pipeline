---
id: "17"
title: "How to Minimize Maximum Regret in Repeated Decision Making Decision-Making"
source_url: "https://homepage.univie.ac.at/karl.schlag/research/decision/regret8.pdf"
fetch_url: "https://homepage.univie.ac.at/karl.schlag/research/decision/regret8.pdf"
resolved_url: "https://homepage.univie.ac.at/karl.schlag/research/decision/regret8.pdf"
firecrawl_title: null
description: null
fetched_at: "2026-05-26T16:42:00.625276Z"
provider: "firecrawl"
strategy: "pdf"
cache_key: "ccd640544e0f6dad29499b18a3869dd1958f28012c7b55ad78dae7635e7eedd5"
firecrawl_status_code: 200
firecrawl_content_type: "application/pdf"
word_count: 15273
char_count: 79422
content_sha256: "cb774ff5aeceab53bcb4aa98956b5ad4540082dfe30f8ab126f6263de4c31d39"
image_count: 0
link_count: 2
warnings:
  - "missing_screenshot"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes:
  - "pdf_mode_auto"
---

# How to Minimize Maximum Regret in Repeated Decision-Making

Karl H. Schlag1

July 13 2003

1 Economics Department, European University Institute, Via della Piazzuola 43, 50133 Florence, Italy, Tel: 0039-055-4685951, email: [schlag@iue.it](mailto:schlag@iue.it)

* * *

Abstract

Consider repeated decision making in a stationary noisy environment given a nite set of actions in each round. Payo¤s belong to a known bounded interval. A rule or strategy attains minimax regret if it minimizes over all rules the maximum over all payo¤ distributions of the di¤erence between achievable and achieved discounted expected payo¤s. Linear rules that attain minimax regret are shown to exist and are optimal for a Bayesian decision-maker endowed with the prior where learning is most di¢ cult. Minimax regret behavior for choosing between two actions given small or intermediate dis- count factors is derived and only requires two rounds of memory. JEL classication: D81, D83. Keywords: Two-armed bandit, Bernoulli, bounded rationality, minimax regret, limited mem- ory.

* * *

# Introduction

Decision-making is an elementary part of human behavior. It is the foundation of any model of strategic interaction. The theory of decision making thus inuences directly or indirectly almost any economic prediction. Rational decision making as we call it today (von Neumann- Morgenstern 1944, Savage 1972) proceeds as follows. The decision-maker rst species a prior probability distribution over the set of states that may occur. Then he selects the action that maximizes expected utility and updates his initial prior after any new information arrives. We will refer to a decision-maker as Bayesian if he behaves according to this procedure as probability updating follows Bayes rule. The underlying behavioral rule will be called Bayesian optimal. Rational decision-making has been criticized from the beginning. In particular it has been questioned whether individuals are able to form priors and whether they have the ability and time to perform the necessary calculations when making their choices and updating their prior. These objections are particularly relevant when stakes are low, time is scarce and priors are di¤use (cf Simon, 1982). We follow an alternative approach and investigate behavior of a decision-maker who makes choices that attain minimax regret (Wald, 1950, Robbins, 1952, cf. Savage, 1951). This is a distribution-free approach in the sense that priors for the specic decision problem are not specied by the decision-maker. The advantage of a distribution-free approach is that the decision-maker does not have to determine a new prior and compute a new behavior each time he faces a similar decision problem. Instead he behaves the same at each rst encounter and adapts behavior over time through experience and learning to the specic environment. Numerous di¤erent rules are suggested in the literature to describe learning without priors. This paper adds to the few papers (e.g. Börgers et al., 2001, Schlag, 1998) that formally select among such rules. The environment of this paper is the same as in the classic multi-armed bandit problem which can be described as follows. An individual must repeatedly choose from a nite set of actions or arms. Each choice yields a random payo¤ which is drawn from an action dependent distribution that is stationary and independent of previous choices or payo¤s achieved. All payo¤s are assumed to belong to the interval \[0; 1\]. The specication of a set of actions and of a payo¤ distribution for each action will be called a decision problem. So the individual repeatedly and independently faces the same decision problem. Finally, the classic multi-armed bandit specication includes a prior which is a probability measure over the set of decision problems. In the alternative setting where payo¤s only belong to f0; 1g we call the decision problem a Bernoulli decision problem. The payo¤ distribution underlying a choice of an action in a given decision problem the individual actually faces should not be confused with the prior distribution over the decision problems the individual might face. A rule or strategy is a description of which action the individual chooses next given his pre- vious observations. We distinguish between deterministic rules that do not involve randomizing between actions and (randomized) rules that are probability measures over deterministic rules. We assume that the individual is risk neutral and that future payo¤s are discounted with a given discount factor where 2 (0; 1). An action that maximizes expected payo¤s in a given decision problem as a best action. For a given rule and a given decision problem regret is dened as the di¤erence between the maximal discounted expected payo¤ obtainable (i.e. the payo¤ to choosing a best action forever) and the discounted expected payo¤ achieved by this rule in this decision problem. Regret is strictly positive whenever the decision maker is a priori uncertain (or ignorant) of which action is best. This results from the fact that regret is never negative, that regret can be interpreted as the discounted sum of regret per round and that zero regret will not be attained in round one if the decision-maker is uncertain about which action is best. Before introducing our methodology in more detail it is useful to explain how selecting behavior according maxmin (Wald, 1950, Gilboa and Schmeidler, 1989) fails in our setting. We allow for any prior over decision problems that yield payo¤s in \[0; 1\]. For any given rule expected payo¤s are minimized when each action yields the payo¤ 0 for sure. So all rules yield the same minimal expected payo¤ and hence a maxmin decision maker should be indi¤erent among all rules. There is little value to learning about the returns to the di¤erent actions if all actions yield similar expected payo¤s. We will ignore such decision problems and focus on an individual who wishes to perform well when there is an incentive to learn. Performance of a rule will be measured by the maximal regret it achieves over the set of all decision problems. Accordingly we search for rules that attain minimax regret which means that the decision maker minimizes over all rules the maximum regret over all decision problems of this rule. In other words, minimax regret behavior minimizes the maximum loss due to ignorance of the true state of a¤airs. 1 In our main characterization of minimax regret behavior we extend results obtained by Berry and Fristedt (1985) for Bernoulli two-armed bandits to our setting in which payo¤s belong to \[0; 1\] and where more than two actions are allowed. Accordingly, a rule attains minimax regret if and only if it is an equilibrium strategy of the decision-maker in the zero sum game with nature where the decision-maker minimizes, and nature maximizes regret. A rule that attains minimax regret is shown to exist within the set of Bernoulli equivalent rules that are symmetric. A Bernoulli equivalent rule is a rule that is linear in payo¤s and that behaves in any decision problem as in the Bernoulli decision problem in which actions receive the same expected payo¤ as in the original decision problem. A rule (or a prior) is called symmetric if its description does not depend on how the actions are labelled. As in Berry and Fristedt (1985) we are able to show the relationship between minimax regret and Bayesian decision-making. Any minimax regret rule is Bayesian optimal under a so-called worst case prior that has the interpretation that it is the environment in which learning is most di¢ cult for a Bayesian decision maker. More formally, a worst case prior maximizes over all priors the regret of a Bayesian decision-maker and is an equilibrium strategy of nature in the ctitious zero sum game mentioned above. Conrming our intuition we nd that worst case priors exist within the set of symmetric priors that put weight on Bernoulli decision problems only. In the rest of the paper we investigate minimax regret behavior in more detail when there are two actions only. Special focus is on whether minimax regret can be attained by a rule with nite memory. Specically, a rule has n round memory for some natural number n if the next choice only depends on choices or payo¤s obtained in the previous n rounds. The minimal size of memory needed to describe a rule is a candidate measure of a rules complexity. Our results build on understanding under which circumstances worst case priors are simple where simple refers here to the fact that their support only contains two Bernoulli decision 1 See French (1986) for a discussion of minimax regret along with alternative distribution free measures of behavior. Other studies on minimax regret include Chamberlain (2000) and, in terms of relative regret, Neeman (2001).

* * *

problems. Let Q0 be the symmetric prior that puts equal weight on the two deterministic (two- action) decision problems in which one action yields payo¤ 1 and the other payo¤ 0. When minimax regret can be attained with a rule with nite memory then Q0 is the only candidate for a symmetric worst case prior that is simple in the above sense. This is proven using results by Kakigi (1983) and Samaranayake (1992) on Bayesian optimal decision-making under simple priors. Furthermore we show that Q0 can only be a worst case prior when 0:62, here proofs rely on investigating Taylor expansions of the regret of a Bernoulli equivalent rule near Q0. This means for > 0:62 that either the worst case prior is not simple or minimax regret cannot be attained by a rule with nite memory. Further results below complete the picture as they show that Q0 is in fact a worst case prior for all 0:62. It is intuitive that Q0 is a worst case prior when is su¢ ciently small as Q0 maximizes the minimum regret in the rst round. Aside we obtain that minimax regret behavior is never deterministic as long as 0:62: There is an obvious candidate for a simple symmetric Bernoulli equivalent rule that attains minimax regret when Q0 is a worst case prior as such a rule must be Bayesian optimal against Q0: It is the single round memory rule that species in the rst round to choose each action equally likely and in any later round to repeat the previous action with probability equal to the payo¤ obtained in the previous round. Our calculations show that this rule attains minimax regret if and only if 0:41. We also nd that there is no single round memory rule that attains minimax regret when > 0:41. Typical for Bernoulli equivalent rules, the single round memory rule selected above prescribes random behavior whenever a payo¤ is realized in (0; 1). We nd that there exists a single round memory rule that is deterministic apart from the choice in the rst round if and only if 1=3. A rule with this property for all 1=3 species to choose each action equally likely in the rst round and in later rounds to repeat the previous action if and only if the payo¤ obtained in the previous round was greater than 1=3. We then present a symmetric Bernoulli equivalent two round memory rule that attains minimax regret if and only if 0:62. Should payo¤s be only realized in f0; 1g then this rule species to choose each action equally likely in the rst round, to choose the same action again in the next two rounds whenever receiving payo¤ 1 and to switch actions otherwise. Behavior after receiving interior payo¤s is more intricate and essentially involves a four state stochastic automaton. We also show that there is no two round memory rule that attains minimax regret for larger than 0:62 if it attains minimax regret for all 0:62. Finally we investigate for which values of between 0:41 and 0:62 minimax regret can be attained with two round memory of actions but only on a single round memory of previous payo¤s

- rules we call two round action memory rules. We nd that minimax regret is attainable with such a rule if and only if 0:54. The rule presented with this property is Bernoulli equivalent, symmetric, species to choose the same action again after receiving payo¤ 1 and to sometimes choose it again after receiving payo¤ 0 if the same action has been chosen twice in a row. This is the rst paper in which minimax regret behavior has been explicitly derived for two- armed bandits. Partial results existed previously only for the scenario in which all payo¤s are contained in f0; 1g. Berry and Fristedt (1985) provided upper and lower bounds on minimax regret when is close to 1. A series of papers in the statistics and in the machine learning literature present specic examples of rules to be used when the decision maker is innitely patient, i.e. = 1 (e.g. Robbins, 1952, 1956, Samuels, 1968, Narendra and Thathachar, 1989). In particular, two rules suggested by Robbins (1952, 1956) coincide to the rules selected by us for small ( 0:41) and for intermediate ( 0:62) discount factors when payo¤s are limited to f0; 1g. The presentation of the material proceeds as follows. Section two introduces the basic setting. In Section three we supply the main characterization result of minimax regret behavior and worst case priors. In Section four we analyze separately rules that attain minimax regret among those with single round memory, two round memory and two round action memory.

# 2 Decision Problems, Rules and Selection

Let Y denote the set of probability measures over the set Y. A multi-action decision problem (W; P) consists of a nite set of actions or arms W = a1; ::; ajW jwith jW j 2 and for each action c 2 W a measurable payo¤ distribution Pc2 \[0; 1\]. 2 Sometimes we will index parameters by the decision problem D they refer to, e.g. write Pc(D) instead of Pc. The set 2 Our results can be applied to payo¤ distributions over a known bounded interval \[; !\] by rst rescaling payo¤s into \[0; 1\] using the linear transformation x 7! ! x :

* * *

of all multi-action decision problems will be denoted by D. A multi-armed bandit is described
by a nite set of actions W and by a prior (or probability measure) Q 2 D over the set of
multi-action decision problems with action set W. We add the term Bernoulliif realized payo⁄s
only belong to f0; 1g. The set of all Bernoulli multi-action decision problems will be denoted by
3
D0. Payo⁄s 0 and 1 are sometimes referred to as failure and success respectively.

Q\\in\\Delta\\mathcal{D}

{mathcal D\_\_{0}},

Consider an individual who repeatedly faces the same multi-armed bandit (W; Q). In each of
a sequence of rounds the individual is asked to choose an action from W. Before the rst round
nature selects the multi-action decision problem W; P~ the individual will be facing according
to the prior Q. Choice of action c in round t yields a payo⁄ realized according to P~cthat is
drawn independently of previous choices and payo⁄ realizations.

\\left(W,\\tilde{P}\\right)

\\tilde{P}\_{c}

A rule (or strategy) is the formal description of how the individual makes his choice as a func-
1 m
tion of his previous experience. A deterministic rule is a mapping f : ;\[m=1f fW \[0; 1\]gg !\
k=1\
W where f (;) is the action chosen in the rst round and f (a1; x1; ::; am; xm) is the action choosen\
in round m+1 after choosing action akand receiving payo⁄ xkin round k for k = 1; ::; m. The set\
of deterministic rules will be denoted by F. A (randomized) (behavioral) rule is a probability\
measure over the set deterministic rules and hence an element of F. We identify c 2 W with\
the probability distribution in W that selects c with probability one so that F F. We will\
also write (;) as the probability of choosing action c in the rst round and (a1; x1; ::; am; xm)\
c c\
as the probability of choosing action c in round m +1 after the history (a1; x1; ::; am; xm). Notice\
that these probabilities need not be independent across rounds.\
Assume throughout that the individual decision-maker is risk neutral and discounts future\
\
f\\left(\\emptyset\\right)\
\
\\cdot,f\\left(a\_{1},x\_{1},..,a\_{m},x\_{m}\\right)\
\
a\_{k}\
\
k=1,..,m\
\
x\_{k}\
\
\\mathcal{F}.\
\
\\phi\
\
c\\in W\
\
\\Delta W\
\
\ {mathcal F\\subset\\Delta{\\mathcal{F}}}\
\
\\phi\\left(a\_{1},x\_{1},..,a\_{m},x\_{m}\\right)\_{c}\
\
\\phi\\left(\\emptyset\\right)\_{c}\
\
Assume throughout that the individual decision-maker is risk neutral and discounts future\
4\
payo⁄s with a given discount factor 2 (0; 1). For a given rule and a given decision prob-\
(n) (n)\
lem D let pc= pc(; D) be the probability of choosing action c 2 W in round n un-\
R\
conditional on previous choices. Letc(D) = xdPc(x; D) denote the expected payo⁄ of\
choosing action c when facing the multi-action decision problem (W; D). Then (; D) :=\
P1 P(n)\
n 1\
(1) pc(; D)c(D) is the discounted value of future payo⁄s. The regret\
n=1 c2W\
3\
The machine learning literature (cf Naremdra and Thathachar, 1989) refers to the Bernoulli case as the Pmodel and to our setting with payo⁄s in \[0; 1\] as the S-model. In the Q-model the support of the payo⁄ distribution\
is nite.\
4\
Our analysis also applies to agents that are not risk neutral by replacing each payo⁄ x with a von Neumann-\
\
\\phi\
\
c;\\in;W\
\
\\begin{array}{r}{\\pi\_{c}\\big(D\\big),=,\\int x d P\_{c},(big,x\\big)}\\end{array}\
\
\\pi^{\\delta}\\left(\\phi,D\\right):=\
\
\\begin{array}{l}{\\left(1-\\delta\\right)\\sum\_{n=1}^{\\infty}\\delta^{n-1}\\sum\_{c\\in W}p\_{c}^{\\left(n\\right)}\\left(\\phi,D\\right)\\pi\_{c}\\left(D\\right)}\\end{array}\
\
(W,D)\
\
4\
Our analysis also applies to agents that are not risk neutral by replacing each payo⁄ x with a von Neumann-\
Morgenstern utility u (x) where u (0) = 0 and u (1) = 1.\
\
u\\left(0\\right)=0\
\
\\flat\\left(1\\right)=1\
\
* * *\
\
(or opportunity loss) of a rule when facing the multi-action decision problem D is dened as\
L (D) := maxc2Wfc(D)g (; D). Regret is a measure of the loss due to ignorance of the\
5\
true state of a⁄airs where the state of a⁄airs is identied with a decision problem. Elements of\
arg maxc2Wfc(D)g will sometimes be referred to as best actions.\
R\
\
\\phi\
\
\ {\\it L} _{\\phi}\\left(D\\right):=\\operatorname{m a x}_{c\\in W}\\left{\\pi\_{c}\\left(D\\right)\\right}-\\pi^{\\delta}\\left(\\phi,D\\right)\
\
\\begin array}{r}{\\mathrm{m a x} _{c\\in W}\\left{\\pi_{c}\\left(D\\right)\\right}}\\end{array}\
\
R\
A Bayesian decision-maker is an individual who chooses a rule ^ 2 arg max (D) dQ~ (D).\
His choice ^ = ^ Q~ is called a Bayesian optimal rule under Q~. We will call Q a worst case\
prior if it maximizes the expected regret of a Bayesian decision-maker over all priors, i.e.\
R\
Q 2 arg maxQ2 DL^(Q)(D) dQ (D). Simplifying we obtain that Q is a worst case prior if and\
R\
only if Q 2 arg maxQ2 Dmin2 FL (D) dQ (D).\
~ is unknown (while W is known) then according to Savage (1972) the individual\
\
\\hat{\\phi}=\\hat{\\phi}\\left(\\tilde{Q}\\right)\
\
\\begin{array}{r}{\\int\\pi\_{\\phi}^{\\delta}\\left(D\\right)d\\tilde{Q}\\left(D\\right)}\\end{array}\
\
{tilde\\cal Q}\
\
\\bar{Q}\
\
\\begin{array}{r}{\\bar{Q}\\in\\arg\\operatorname\*{m a x} _{Q\\in\\Delta\\mathcal{D}}\\int L_{\\hat{\\phi}\\left(Q\\right)}\\left(D\\right)d Q\\left(D\\right)}\\end{array}\
\
\\begin{array}{r}{\\bar{Q}\\in\\arg\\operatorname\*{m a x} _{Q\\in\\Delta\\mathcal{D}}\\operatorname\*{m i n}_{\\phi\\in\\Delta\\mathcal{F}}\\int L\_{\\phi}\\left(D\\right)d Q\\left(D\\right)}\\end{array}\
\
If the prior Q~ is unknown (while W is known) then according to Savage (1972) the individual\
species a subjective prior Q^ and chooses a Bayesian optimal rule under Q^. We follow an\
alternative approach (Wald, 1950, Gibbons, 1952) that is distribution-free as the individual\
does not invoke a specic prior to select a rule. We assume that the individual selects a rule\
that minimizes among all rules the maximal regret among all decision problems (W; D). More\
specically, we say that attains minimax regret if 2 arg min2 FsupD2DL (D).\
\
\\hat{Q}\
\
\\tilde{Q}\
\
\\hat{Q}\
\
\\phi^{\*}\
\
\\phi^{ _}\\in{\ \ \\operatorname{a r g}\\operatorname_{m i n}} _{\\phi\\in\\Delta\\mathcal{F}}\\operatorname\*{s u p}_{D\\in\\mathcal{D}}L\_{\\phi}\\left(D\\right)\
\
3 A General Characterization\
\
As the various actions belonging to W cannot be distinguished (apart from their labels), symmetry will play an important role in our investigation.\
Given D 2 D and a permutation of the elements of W let D 2 D be the multi-action\
\
Given D 2 D and a permutation of the elements of W let D 2 D be the multi-action\
decision problem dened by permuting the labels of the actions in D using such that Pc(D ) =\
P(c)(D) for c 2 W. For a given multi-armed bandit (W; Q) with Q 2 D let Q be the\
distribution dened by exchanging each decision problem D in the support of Q by D . A prior\
\
D\\in{\\mathcal{D}}\
\
D\_{\\iota}\\in\\mathcal{D}\
\
P\_{\\iota\ c((c)}\\left(D\\right)\
\
c;\\in;W\
\
Q\\in\\Delta D\
\
Q\_{\\iota}\
\
D\_{\\iota}\
\
Q\
\
5\
Notice how we thus di⁄er from the approach of Savage (1951, cf. French, 1986) that is based on a set of\
states, each being without uncertainty and where regret is considered in each state separately.\
\
* * *\
\
Q is called symmetric if Q = Q holds for any permutations of the elements of W. The set of\
symmetric priors over a subset Z of D will be denoted bypZ.\
\
Q=Q,\
\
W\
\
\\Delta\_{p}\\mathcal{Z}\
\
Given a deterministic rule f and a permutation of the elements of W let f be the deterministic rule that is derived from f by permuting actions with such that f (;) = f (;) and\
c (c)\
f (a1; x1; ::; am; xm) = ( (a1); x1; ::; (am); xm). A randomized rule is called symmetric\
c (c)\
if (T) = (ff s.t. f 2 T g) holds for all permutations of W and for all measurable sets of\
deterministic rules T. The set of symmetric randomized rules will be denoted bypF. Notice\
1 j\
that if is symmetric then (;) = for all c 2 W.\
c jW\
\
f\_{\\iota}\
\
\ _{f_{\\iota}\\left(a\_{1},x\_{1},..,a\_{m},x\_{m}\\right) _{c}=\\phi\\left(\\iota\\left(a_{1}\\right),x\_{1},..,\\iota\\left(a\_{m}\\right),x\_{m}\\right)\_{\\iota\\left(c\\right)}}\
\
f\_{\\iota}\\left(\\emptyset\\right) _{c}=f\\left(\\emptyset\\right)_{\\iota(c)}\
\
\\phi\ T()\\=\\phi\\left(\\left{f\_{\\iota}\ {\\mathrm{s.t.~}}\ f\\in T\\right}\\right}\
\
\\begin array}{r}{\\phi\\left(\\emptyset\\right)\_{c}=\\frac{1}{\|W\|}}\\end{array}\
\
\\Delta\_{p}\\mathcal{F}\
\
\\phi\
\
3.2 Linearity and Bernoulli Equivalence\
\
In our setting there are no restrictions on how the action prescribed by a given rule in a given\
round depends on previous payo⁄s obtained. We will nd that simple rules in the sense that\
behavior is a linear function of previous payo⁄s will play an important role for attaining minimax\
regret behavior. More specically, a subset of the linear rules called Bernoulli equivalent rules\
will play this important role.\
\
A rule is called linear if (a1; x1; ::; am; xm) is linear in xkfor all k = 1; ::; m and all m\
c\
which means that\
\
\\phi\\left(a\_{1},x\_{1},..,a\_{m},x\_{m}\\right)\_{c}\
\
\\phi\
\
\\phi\\left(a\_{1},x\_{1},..,a\_{m},x\_{m}\\right) _{c}=\\sum_{j\_{1}=0}^{1}\ ..sum\_{j\_{m}=0}^{1}\\left\[\\Pi\_{k=1}^{m}\\left(j\_{k}x\_{k}+\\left(1-j\_{k}\\right)\\left(1-x\_{k}\\right)\\right)\\right\]\\phi\\left(a\_{1},j\_{1},..,a\_{m},j\_{m}\\right)\_{c}\
\
(1)\
\
holds for all m and for all ai2 W and xi2 \[0; 1\], i = 1; ::; m. The set of linear rules will be\
L\
denoted by F.\
\
a\_{i}\\in W\
\
\\Delta^{L}\\mathcal{F}\
\
A linear rule is called Bernoulli equivalent if in any decision problem it behaves as it does in\
the Bernoulli decision problem in which actions have the same expected payo⁄ as in the original\
decision problem. More formally, given D 2 D let D0 (D) 2 D0 be dened by the fact that\
c(D) =c(D0 (D)) holds for all c 2 W. Then we require for all D 2 D and for any sequence\
of actions a1; ::; amthat the probability that action aiis chosen in round i for all i = 1; ::; m is\
\
\\phi\
\
D\\in{\\mathcal{D}}\
\
D\_{0}\\left(D\\right),\\in,\ \\mathcal{D}\_{0}\
\
a\_{1},...,a\_{m}\
\
i=1,..,m\
\
a\_{i} the same under D as it is under D0 (D). Formally,\
\
D\_{0}\\left(D\\right)\
\
\\begin{array}{l c l}{}&{}&{\\displaystyle\\int\\phi\\left(\\emptyset\\right) _{a_{1} **}\\prod\_{k=1}^{m-1}\\phi\\left(a\_{1},x\_{1},..,a\_{k},x\_{k}\\right) _{a_{k+1}}d P\_{a\_{1}}\\left(x\_{1}\\right)..d P\_{a\_{m-1}}\\left(x\_{m-1}\\right)}\ {=}&{\\displaystyle\\sum\_{j=1}^{m}\\sum\_{y\_{j}=0}^{m}\\prod\_{j=1}^{m}\\left(y\_{j}\\pi\_{a\_{j}}+\\left(1-y\_{j}\\right)\\left(1-\\pi\_{a\_{j}}\\right)\\right)\*\\phi\\left(\\emptyset\\right) _{a_{1}**}\\prod\_{k=1}^{m-1}\\phi\\left(a\_{1},y\_{1},..,y\_{k},x\_{k}\\right) _{a_{k+1}}}\ \\end{array}\
\
B\
The set of Bernoulli equivalent rules with support M F will be denoted by M.\
\
\\Delta^{B}M\
\
Next we illustrate why not all linear rules are Bernoulli equivalent. Consider a linear rule\
f. It is easily checked that f satises the conditions imposed on a Bernoulli equivalent rule\
in the rst two rounds. However this is not necessarily true in round three. For instance, the\
probability of obtaining the sequence of actions a,b,b in the rst three rounds equals\
Z\
\
\\begin{aligned}{}&{{}f\\left(\\emptyset\\right) _{a}\\int f\\left(a,x\\right)_{b}f\\left(a,x,b,y\\right) _{b}d P_{a}\\left(x\\right)d P\_{b}\\left(y\\right)}\ {=}&{{};f\\left(\\emptyset\\right) _{a}\\left(\\pi_{b}\\int f\\left(a,x\\right) _{b}f\\left(a,x,b,1\\right)_{b}d P\_{a}\\left(x\\right)+\\left(1-\\pi\_{b}\\right)\\int f\\left(a,x\\right) _{b}f\\left(a,x,b,0\\right)_{b}d P\_{a}\\left(x\\right)\\right)}\ \\end{aligned}\
\
If f prescribes to randomize independently in each round then\
Z\
\
\\int f\\left(a,x\\right) _{b}f\\left(a,x,b,1\\right)_{b}d P\_{a}\\left(x\\right)=\\left(\\pi\_{a}f\\left(a,1\\right) _{b}+\\left(1-\\pi_{a}\\right)f\\left(a,0\\right) _{b}\\right)\\left(\\pi_{a}f\\left(a,1,b,1\\right) _{b}+\\left(1-\\pi_{a}\\right)f\\left(a,0,b,1\\right)\_{b}\\right).\
\
On the other hand, if f is Bernoulli equivalent then\
Z\
\
\\int f\\left(a,x\\right) _{b}f\\left(a,x,b,1\\right)_{b}d P\_{a}\\left(x\\right)=\\pi\_{a}f\\left(a,1\\right) _{b}f\\left(a,1,b,1\\right)_{b}+\\left(1-\\pi\_{a}\\right)f\\left(a,0\\right) _{b}f\\left(a,0,b,1\\right)_{b}.\
\
f\\left(\\emptyset\\right)\_{a}>0\
\
f\\left(a,0,b,y\\right) _{b}=f\\left(a,1,b,y\\right)_{b}\
\
Finally we show how to extend a rule dened on the set of Bernoulli decision problems\
to a Bernoulli equivalent rule. We present two ways to generate the same behavior. (A) When\
a payo⁄, say xi2 \[0; 1\], is obtained in round i then realize an independent random variable\
that yields 1 with probability xiand 0 otherwise. Remember the realization dxi2 f0; 1g of this\
random variable and forget the payo⁄ xiitself. Apply the rule in all later rounds as if dxiwas the\
1\
payo⁄ received in round i. (B) Given a sequence z = (zi) with zi2 \[0; 1\] for all i dene the rule\
i=1\
\
\\phi\ {\
\
\ \ d{} _{x_{i}}\\in{0,1}\
\
d\_{x\_{i}}\
\
x\_{i}\
\
z=(z\_{i})\_{i=1}^{\\infty}\
\
z\_{i}\\in\[0,1\]\
\
* * *\
\
zby settingz(;) = (;) and settingz(a1; x1; ::; am; xm) = a1; 1fx z g; ::; am; 1fxm zmg for any history (a1; x1; ::; am; xm) where 1fx izig is the indicator function that takes value 1 if xiziand value 0 otherwise. The Bernoulli equivalent extention of the rule is then obtained by randomizing over the set of ruleszby choosing ziiid from a uniform distribution on \[0; 1\] for all i. Under the behavior dened in (A), each sequence of actions has the same probability of occurring in the decision problem D as it does in the Bernoulli decision problem D0 (D). None- the-less, the construction in (A) does not formally dene a rule as the memory of the decision- maker is changed which is not allowed in our denition of a randomized rule. Our second alternative (B) leads to a formal denition of a rule. It is easily shown that the rule dened in (B) is behaviorally equivalent to the one described in (A) and hence that it is Bernoulli equivalent.\
\
Remark 1 Linear rules, in particular Bernoulli equivalent rules, typically involve randomizing when receiving payo¤ s in (0; 1). More specically, it is easily deduced from (1) for a linear rule f that either f (a1; x1; ::; an; xn) is independent of x1; ::; xnor f (a1; x1; ::; an; xn) 2= W for all x1; ::; xn2 (0; 1). In contrast we show in the appendix that Bayesian optimal rules typically do not involve randomizing behavior.\
\
3.3 The Result The following characterization will be very useful as it reduces the search for a rule that attains minimax regret to the search for an equilibrium of a zero-sum game. At the same time it reveals a close connection between minimax regret behavior and Bayesian decision making. Proposition 1 i) There exists a worst case prior inpD0 and a rule in\
B pF that attains minimax regret. The value of minimax regret is strictly positive. ii) 2 B pF attains minimax regret and Q 2pD0 is a worst case prior if and only if Z Z Z L (D) dQ (D) L (D) dQ (D) L (D) dQ (D) 8 2pF 8Q 2pD0:\
\
(iii) 2 F attains minimax regret and Q 2 D is a worst case prior if and only if Z Z Z L (D) dQ (D) L (D) dQ (D) L (D) dQ (D) 8 2 F 8Q 2 D: (2)\
\
* * *\
\
In particular, any rule that attains minimax regret is Bayesian optimal under any worst case\
prior.\
\
The above generalizes ndings that Berry and Fristedt (1985) have obtained for Bernoulli\
two-armed bandits.\
\
Proof. We rst review the results Berry and Fristedt (1985) obtained for Bernoulli two-armed\
bandits which is statement (i) and the ifstatements of (ii) and (iii). They introduce a topology\
on the set of strategies and then show for the zero sum game where the individual chooses a\
rule to minimize regret and nature chooses a prior to maximize regret that a Nash equilibrium\
(; Q ) exists. If (; Q ) is a such a Nash equilibrium (i.e. (2) holds when restricted to the\
case of jW j = 2 and Q 2 D0) then\
Z Z Z\
\
(\\phi^{ _},Q^{_})\
\
(\\phi^{ _},Q^{_})\
\
\|W\|=2\
\
Q\\in\\Delta\\mathcal{D}\_{0})\
\
\\begin{aligned}{}&{{}\ L\_{\\phi^{ _}}\\left(D\\right)d Q^{_}\\left(D\\right)=\\operatorname\*{m a x} _{Q\\in\\Delta\\mathcal{D}_{0}}\\int L\_{phi\ {'}}\\left(D\\right)d Q\\left(D\\right)\\geq\\operatorname\*{m i n} _{\\phi\\in\\Delta\\mathcal{F}}\\operatorname\*{m a x}_{Q\\in\\Delta\\mathcal{D} _{0}}\\int L_{\\phi}\\left(D\\right)d Q\\left(D\\right)}\ {\\geq}&{{}\ \\operatorname\ {operatorname\*{m a x}} _{Q\\in\\Delta\\mathcal{D}_{0}}\\operatorname\*{m i n} _{\\phi}\\int L_{\\phi}\\left(D\\right)d Q\\left(D\\right)\\geq\\operatorname\*{m i n} _{\\phi\\in\\Delta\\mathcal{F}}\\int L_{\\phi}\\left(D\\right)d Q^{ _}\\left(D\\right)=\\int L\_{\\phi^{_}}\\left(D\\right)d Q^{\*}\\left(D\\right)}\ \\end{aligned}\
\
which proves the ifstatement of (iii) for Bernoulli two-armed bandits. Berry and Fristedt (1985)\
also ensure the existence of a strictly positive lower bound on the value of minimax regret so this\
R\
completes (i) for Bernoulli two-armed bandits. Quasi-concavity of maxQ2 D0L (D) dQ (D)\
R\
as a function of shows thatpF \ arg min2 FmaxQ2 D0L (D) dQ (D) 6= ;. Similarly,\
R\
quasi-convexity of min2 FL (D) dQ (D) as a function of Q is used to show thatpD0\
\
R\
arg maxQ2 D0min2 FL (D) dQ (D) 6= ;. Finally, the if statement of (ii) follows from\
R\
the fact thatpD0 \ arg maxQ2 D0L (D) dQ (D) 6= ; if 2pF and similarly,pF\
\
R\
arg min2 FL (D) dQ (D) 6= ; if Q 2pD0. The above can be generalized to Bernoulli\
multi-armed bandits immediately.\
\
\\begin{array}{r}{\\mathrm{m a x} _{\\boldsymbol{Q}\\in\\Delta\\mathcal{D}_{0}}\\int L\_{\\boldsymbol{\\phi}}\\left(\\boldsymbol{D}\\right)d Q\\left(\\boldsymbol{D}\\right)}\\end{array}\
\
\\Delta\_{p}\\mathcal{F}\
\
\\Delta\_{p}\\mathcal{D}\_{0}\\cap\
\
Q\
\
\\textstyle\\kappa\_{Q\\in\\Delta\\mathcal{D} _{0}}\\operatorname\*{m i n}_{\\phi\\in\\Delta\\mathcal{F}}\\int L\_{\\phi}\\left(D\\right)d Q\\left(D\\right);\\neq;\\emptyset\
\
\\begin{array}{r}{\\cap,\\arg\\operatorname\*{m a x} _{Q\\in\\Delta\\mathcal{D}_{0}}\\int\\mathcal{L} _{\\phi^{}}\\left(D\\right)d Q\\left(D\\right),\\neq,\\emptyset,,{\\mathrm{i f}},,\\phi^{},\\in,\\Delta_{p}\\mathcal{F}}\\end{array}\
\
\\Delta\_{p}\\mathcal{F}\\cap\
\
\\Delta\_{p}\\mathcal{D}\_{0}\
\
{0,1}\
\
In the following we will show that the above also holds when payo⁄s are not restricted\
B\
to f0; 1g. Let (; Q ) 2 F D0 be a Nash equilibrium of the zero-sum game when\
R\
restricting attention to D0. Since is Bernoulli equivalent, maxQ2 D0L (D) dQ (D) =\
R R\
maxQ2 DL (D) dQ (D) and Q 2 D0 implies that min2 FL L (D) dQ (D) =min2 F\
R\
L (D) dQ (D) and hence (2) holds. Notice furthermore that the ifstatement of (iii) holds\
as stated by the same proof as when we considered only D0. Part (i) and the ifstatement of\
(ii) then also follow as above.\
\
#,(\\phi^{ _},Q^{_}),\\in,\\Delta^{B}\\mathcal{F}\\times\\Delta\\mathcal{I}\
\
\\begin{array}{r}{\\operatorname\*{m a x} _{Q\\in\\Delta\\mathcal{D}_{0}}\\int L\_{\\phi^{\*}}\\left(D\\right)d Q\\left(D\\right)=}\\end{array}\
\
\\mathcal{D}\_{0}\
\
Q^{\*}\\in\\Delta\\mathcal{D}\_{0}\
\
\\phi^{\*}\
\
\\begin array}{{l}{\ \ \\operatorname\*{{m n n}} _{\\phi\\in\\Delta\\mathcal{F}^{L}}\\int L_{\\phi}\\left(D\\right)d Q^{ _}\\left(D\\right)=\\operatorname_{m{m n}}\_{\\phi\\in\\Delta\\cdot{}}}\ \\end{array}\
\
\\begin{array}{r}{\\int L\_{\\phi}\\left(D\\right)d Q^{\*}\\left(D\\right)}\\end{array}\
\
\\begin{array}{r}{\\mathrm{m a x} _{\\mathcal{Q}\\in\\Delta\\mathcal{D}}\\int L_{\\phi{}^{\*}}\\left(\\boldsymbol{D}\\right)d Q\\left(\\boldsymbol{D}\\right)}\\end{array}\
\
\\mathcal{D}\_{0}\
\
* * *\
\
Consider now the only ifstatements of (ii) and (iii). If attains minimax regret and Q is a worst case prior then Z Z Z L (D) dQ (D) sup L (D) dQ (D) = min sup L (D) dQ (D) Q2 D 2 F Q2 D Z Z Z max inf L (D) dQ (D) = inf L (D) dQ (D) L (D) dQ (D) Q2 D 2 F 2 F R so the claim follows as we know that min2 FsupQ2 D 0 L (D) dQ (D) = maxQ2 D0inf2 F R L (D) dQ (D) holds.\
\
# 4 Two-Armed Bandits\
\
In the following we investigate minimax regret behavior when there are two actions only. Let W = fa; bg. Special attention will focus on whether minimax regret behavior can be implemented with a rule that has nite memory. An important ingredient will be to understand Bayesian optimal behavior under specic very simple priors. We say that the rule has n round memory if (a1; x1; ::; am; xm) c is independent of (ak; xk) for k m n. has nite memory if there exists n such that has n round memory. has n round action memory if has n round memory and if (a1; x1; ::; am; xm) c is independent of xk for k m 1. The amount of memory needed to implement a rule can be considered a measure of its complexity.\
\
## 4.1 Necessary Conditions\
\
Following Proposition 1, rules that attain minimax regret are Bayesian optimal under some prior over Bernoulli decision problems. Insights into Bayesian optimal behavior can thus teach us about minimax regret behavior. Unfortunately many results on Bayesian optimal decision making deal only with independent arms-we do not expect a worst case prior ever to have this property. We will use results on dependent arms due to Kakigi (1983) and Samaranayake (1992) who consider priors that put weight on two Bernoulli decision problems. Q 2pD0 will be called a symmetric two point Bernoulli prior if it only has two elements in its support, formally if there exist v and w with 0 v < w 1 such that Q D~ = 1=2 for D~ 2 D0 with1D~ = v and2D~ = w. We will write Q = Q (v; w) and also write\
\
* * *\
\
Q0 instead of Q (0; 1). Kakigi (1983) derives a particular Bayesian optimal rule for such priors. Results found in Samaranayake (1992) can be used to show that a Bayesian optimal rule under such a prior will have the stay with a winner property. The rule is said to have the stay with a winner property if it species to choose the same action again after any success, i.e. if (a1; x1; ::; am; 1) a m = 1 for all ak, xk, k = 1; ::; m 1, all amand all m. 6\
\
Proposition 2 Consider jW j = 2. If the nite memory rule attains minimax regret and Q (v; w) is a worst case prior (for instance when arg maxD2D 0 : a(D)>b(D)L (D) is single val- ued) then Q (v; w) = Q0.\
\
Proof. First assume 0 < v < w < 1. Kakigi (1983) shows that the following symmetric rule is Bayesian optimal under such a prior Q (v; w). Choose action a in round one. Choose action a in round n if and only if the updated belief that a yields a higher expected payo¤ than b is at least 0:5. Notice that this rule cannot be implemented with a nite memory as 0 < v < w < 1. What we have to show in the following is that no Bayesian optimal rule will have nite memory. It is shown in Kakigi (Proof of Theorem 2, 1983) that the di¤erence between the value of choosing a and the value of choosing b when continuing thereafter optimally is non decreasing in the belief that action a yields a higher expected payo¤ than action b. Let r (s) denote this di¤erence where s is the corresponding belief. Samaranayake (Example 2.2, 1992) shows that actions a and b are negatively correlated after any history. Since v < w, the support of the marginal distributions of choosing a (or of choosing\
\
b) has two elements. So the results in Proposition 5.2(b) in Samaranayake (1992) holds with strict inequalities. This means that a Bayesian decision maker strictly prefers action c over action d after action c yielded a success. Thus r (s\
+\
\
) \> 0 if s +\
is the updated belief after having belief 1=2 and receiving a success by choosing a. Together with the fact that r is non decreasing we obtain that r is strictly increasing in s. In other words, the rule from Kakigi (1983) described above prescribes the unique Bayesian optimal behavior whenever the belief does not equal 1=2. Hence no Bayesian optimal rule under Q (v; w) with 0 < v < w < 1 has nite memory. 6 Note that the result proven by Berry and Fristedt (1985) for independent arms is weaker as it only states that there always exists a Bayesian optimal rule with the stay with a winner property.\
\
* * *\
\
Now assume v = 0 and w 2 (0; 1). Consider a Bayesian optimal behavior under Q (0; w).\
As behavior when s = 1=2 does not matter we can assume that is symmetric and species to\
switch after any failure. Of course locks in on the same action whenever he obtains the rst\
success. We now calculate regret of when facing Q (0; w) for some w 2 (0; 1). Let z be the\
1 1 1\
future value after only failures obtained previously. Then z = (1) w + ww + 1 w z\
2 2 2\
w (1) w\
so z = w21 and hence L (Q (0; w)) = w z =. L (Q (0; w)) as a function of w\
2 + + w 2 2 + w\
obtains its unique maximum when w = 1 and hence Q (0; w) is never a worst case prior if w < 1.\
\
v=0\
\
w\\in(0,1)\
\
Q\\left(0,w\\right)\
\
s=1/2\
\
\\phi^{\*}\
\
\\phi^{\*}\
\
\\bar{w},(,\\bar{\ },,,,,,)\
\
\\phi^{\*}\
\
\\begin{array}{r}{z=\\left(1-\\delta\\right)\\frac{1}{2}\\bar{w}+\\frac{1}{2}\\bar{w}\\delta\\bar{w}+\\left(1-\\frac{1}{2}\\bar{w}\\right)\\delta\\bar{z}}\\end{array}\
\
\\begin{array}{r}{\\mathrm{s o}\ z=\\bar{w}\\frac{1-\\delta+\\bar{w}\\delta}{2-2\\delta+\\bar{w}\\delta}}\\end{array}\
\
\\begin{array}{r}{L\_{\\phi^{ _}}\\left(Q\\left(0,\\bar{w}\\right)\\right)=\\bar{w}-z=\\frac{\\left(1-\\delta\\right)\\bar{w}}{2-2\\delta+\\bar{w}\\delta},;L\_{\\phi^{_}}\\left(Q\\left(0,\\bar{w}\\right)\\right.}\\end{array}\
\
\\bar{w}\
\
w<1\
\
\\bar{w}=1\
\
Q\\left(0,w\\right)\
\
Finally, assume v > 0 and w = 1. Let be the symmetric Bayesian optimal rule under\
Q (v; 1) that switches after a failure and has the stay with a winner property. Consider regret\
under Q (v; 1) for some v 2 (0; 1). Let x be the future value of payo⁄s after only achieving\
successes in the previous rounds with the worse action. We obtain x = (1) v + vx + (1 v)\
\
- 2v v 1 1 + 2v v 1 (1)(1 v)\
  so x = and hence L (Q (v; 1)) = 1 =. L (Q (v; 1)) as a\
  1v 2 2 1v 2 1 v\
  function of v obtains its unique maximum when v = 0 and hence Q (v; 1) is never a worst case\
  prior if v > 0.\
\
v>0\
\
w=1\
\
\\phi^{\*}\
\
Q\\left(v,1\\right)\
\
Q\\left(\\bar{v},1\\right)\
\
\\bar{v}\\in(0,1)\
\
x=\\left(1-\\delta\\right)\\bar{v}+\\bar{v}\\delta x+\\left(1-\\bar{v}\\right)\\delta\\bar\
\
\\begin{array}{r}{x=\\frac{\\delta{!!!}+!\\bar{v}-2!\\delta\\bar{v}}{1\ !-!\\delta\\bar{v}}}\\end{array}\
\
\\begin{array}{r}{L\_{\\phi^{ _}}\\left(Q\\left(\\bar{v},1\\right)\\right)=1-\\frac{1}{2}-\\frac{1}{2}\\frac{\\delta+\\bar{v}-2\\delta\\bar{v}}{1-\\delta\\bar{v}}=\\frac{1}{2}\\frac{\\left(1-\\delta\\right)\\left(1-\\bar{v}\\right)}{1-\\delta\\bar{v}}.\\enspace L\_{\\phi^{_}}\\left(Q\\left(\\bar{v},1\\right)\\right).}\\end{array}\
\
Q\\left(v,1\\right)\
\
v>0\
\
So Q0 is the only candidate for a simple worst case prior. Using Taylor expansions of regret\
we derive an upper bound on the set of discount factors under which Q0 can be a worst case\
prior.\
\
Q\_{0}\
\
Q\_{0}\
\
p\
1 1\
Proposition 3 Consider jW j = 2. Then Q0 is not a worst case prior for > 5 0:62.\
2 2\
\
\|W\|=2\
\
Q\_{0}\
\
\\begin array}{r}{\\cdot\\delta>\\frac{1}{2}\\sqrt{5}-\\frac{1}{2}\\approx0.62}\\end{array}\
\
Proof. Consider a symmetric Bernoulli equivalent rule that attains minimax regret with Q0\
being a worst case prior. Since is symmetric, (;) = 1=2. Since is a Bayesian optimal\
a\
rule under Q0, has the stay with a winner property and (c; 0) = 0 for c 2 fa; bg. So all we\
c\
have to check in order for to attain minimax regret is that Q0 maximizes regret of the rule\
.\
\
Q\_{0}\
\
\\phi^{\*}\
\
\\phi^{\*}\
\
\\phi^{\*}\\left(c,0\\right)\_{c}=0\
\
Q\_{0}\
\
c\\in{a,b}\
\
O\
\
\\phi^{\*}\
\
{Q\\left(v,1\\right):0\\leq v<1}\\cup{Q\\left(0,w\\right):0<w\\leq1}.\
\
Q\_{0}\
\
Q\\left(v,1\\right)\
\
Q\\left(0,w\\right)\
\
* * *\
\
0\
Below we alter the behavior of to obtain a rule that chooses if possible a best response\
0 0\
to both Q (v; 1) and Q (0; w). retains the properties of that is a best response to\
0\
Q0 and that Q0 maximizes regret under. The latter follows since L (Q0) = L 0 (Q0) and\
L (Q) L 0 (Q) implies L 0 (Q0) L 0 (Q).\
\
\\phi^{\*}\
\
\\phi^{\\prime}\
\
Q\\left(v,1\\right)\
\
\\phi^{\\prime}\
\
Q\\left(0,w\\right)\
\
\\phi^{\\prime}\
\
\\phi^{\*}\
\
Q\_{0}\
\
Q\_{0}\
\
\\phi^{\\prime}\
\
L\_{\\phi^{\*}}\\left(Q\_{0}\\right)=L\_{\\phi^{\\prime}}\\left(Q\_{0}\\right)\
\
L\_{\\phi^{\*}}\\left(Q\\right)\\geq L\_{\\phi^{\\prime}}\\left(Q\\right)\
\
L\_{\\phi^{\\prime}}\\left(Q\_{0}\\right)\\geq L\_{\\phi^{\\prime}}\\left(Q\\right)\
\
0\
Let choose action a forever after observing a failure from action b and a success from action\
0\
a in the rst two rounds. Here chooses a best response to both Q (0; w) and to Q (v; 1). Let\
0\
choose action a forever after observing (a; 1; a; 1) or (a; 1; a; 0; a; 1). As we are only interested\
in rst order approximation, we ignore the possibility that we could be facing (a; b) = (v; 1).\
0\
Similarly, based on rst order approximation chooses action a forever after observing two\
failures of b and one failure of a in the rst three rounds.\
\
\\phi^{\\prime}\
\
a\
\
\\phi^{\\prime}\
\
Q\\left(0,w\\right)\
\
\\phi^{\\prime}\
\
(a,1,a,1)\
\
(a,1,a,0,a,1)\
\
\\left(\\pi\_{a},\\pi\_{b}\\right)=\\left(v,1\\right)\
\
\\phi^{\\prime}\
\
Let x = (c; 1; c; 0) and y = (d; 0; c; 0) for c 6= d. Then\
d d\
\
x=\\phi^{\*}\\left(c,1,c,0\\right)\_{d}\
\
y=\\phi^{\*}\\left(d,0,c,0\\right)\_{d}\
\
c\\neq d\
\
\\begin{array}{l c l}{\\pi\_{\\phi^{\\prime}}^{\\delta}}&{=}&{\\left(1-\\delta\\right)\\frac{1}{2}w+\\left(1-\\delta\\right)\\delta\\frac{1}{2}\\left(1+w\\right)w+\\frac{1}{2}w\\delta^{2}w+\\frac{1}{2}w^{2}\\delta^{2}w}\ {}&{}&{+\\left(1-\\delta\\right)\\delta^{2}\\left(\\frac{1}{2}w\\left(1-w\\right)x+\\frac{1}{2}\\left(1-w\\right)y+\\frac{1}{2}\\left(1-w\\right)\\left(1-y\\right)\\right)w}\ {}&{}&{+\\delta^{3}\\left(\\frac{1}{2}\\left(1-w\\right)w^{2}\\left(1-w\\right)w+\\frac{1}{2}w\\left(1-w\\right)w w\\right)}\ {}&{}&{+\\frac{1}{2}\\left(1-w\\right)\\delta^{3}w\\left(\\left(1-y\\right)++w w+(1-y\ w)y\\right)+o\\left(\\left(1-w\\right)^{2}\\right)}\ \\end{array}\
\
where the expressions refer in the order of their appearance to the payo⁄s in round one and\
two, continuation payo⁄ starting round three after the events (b; 0; a; 1) and (a; 1; a; 1), round\
\
two, continuation payo⁄ starting round three after the events (b; 0; a; 1) and (a; 1; a; 1), round\
three payo⁄s after (a; 1; a; 0), (a; 0; b; 0) and (b; 0; a; 0) and continuation payo⁄s starting round\
four after (a; 1; a; 0; a; 1), (a; 1; a; 0; b; 0) and after (a; 0; b; 0; b; 0), (a; 0; b; 0; a; 1), (b; 0; a; 0; a; 1)\
and (b; 0; a; 0; b; 0). Consequently,\
\
and (b; 0; a; 0; b; 0). Consequently,\
\
L\_{\\phi^{\\prime}}=\\frac{1}{2}\\left(1-\\delta\\right)-\\frac{1}{2}\\left(1-\\delta\\right)\\left(1-\\delta-\\delta^{2}-x\\delta^{2}\\right)\\left(1-w\\right)+o\\left(\\left(1-w\\right)^{2}\\right).\
\
(a,1,a,0,a,1)\
\
2 2\
Since Q0 maximizes L 0 (Q) we obtain 1 x2 0 which implies 1 0\
p\
1 1\
which implies 5.\
2 2\
\
Q\_{0}\
\
p\
1 1\
Corollary 4 Consider jW j = 2 and > 5. Then either there is no nite memory rule\
2 2\
that attains minimax regret or arg maxD2D : (D)> (D)L (D) is not single valued for any\
0 a b\
that attains minimax regret.\
\
We combine Propositions 2 and 3 to obtain the following.\
\
\|W\|=2\
\
1-\\delta-\\delta^{2}-x\\delta^{2},\\geq,0\
\
\\phi^{\*}\
\
\\textstyle\ \ {textstyle delta leq frac11}sqrt\\textstyle-\\frac12.\
\
\\begin{array}{r}{\\delta>\\frac{1}{2}\\sqrt{5}-\\frac{1}{2}}\\end{array}\
\
\\overset{\\cdot}{\ }underset}{D\ {\\in}\\mathcal{D} _{0}\\underset{}{:}{\\pi_{a}(D)>\\pi\_{b}(D)}L\_{\\phi^{\*}}\\left(D\\right)\
\
* * *\
\
p\
1 1\
At this point of our analysis we have no evidence for which values (if any) of 5\
2 2\
p\
1 1\
that Q0 is a worst case prior. However, if Q0 is a worst case prior at = 5 then the\
2 2\
expansion technique used in the proof of Proposition 3 reveals properties of a minimax regret\
rule.\
\
\\begin{array}{r}{\\delta\\leq\\frac{1}{2}\\sqrt{5}-\\frac{1}{2}}\\end{array}\
\
Q\_{0}\
\
Q\_{0}\
\
\\begin{array}{r}{\\delta,=,{\\frac{1}{2}}{\\sqrt{5}},-,{\\frac{1}{2}}}\\end{array}\
\
p\
1 1\
Lemma 5 Consider jW j = 2 and = 5. Assume that is a symmetric rule that attains\
2 2\
minimax regret and assume that Q0 is a worst case prior. Then (c; 0) = 0, (c; 1; c; 0) = 1,\
c c\
(c; 1; c; 1; c; 0) = 1, (c; 1; c; 0; c; 0) = 0, (c; 0; d; 1; d; 0) = 1, (c; 0; d; 0; c; 0) = 0 if\
c c d c\
(c; 0; d; 0) < 1, (c; 0; d; 0; d; 0) = 0 if (c; 0; d; 0) > 0 and in the rst three rounds\
d d d\
does not switch after a success.\
\
\|W\|=2\
\
\\textstyle\\hat{\\delta}=\ {\\frac{1}{2}}{\\sqrt{5}}!-!{\\frac{1}{2}}\
\
\\phi^{\*}\
\
Q\_{0}\
\
\\phi^{ _}\\left(c,0\\right)\_{c}!=!0,,\\phi^{_}\\left(c,1,c,0\\right)\_{c}!=!1\
\
\\phi^{ _}\\left(c,1,c,1,c,0\\right)\_{\_c{}};=;1,\ \\phi^{_}\\left(c,1,c,0,c,0\\right) _{c{}}\\;=;0,\ \\phi^{\*}\\left(c,0,d,1,d,0\\right){d\_d};=;1,\ \\phi^{\*}\\left(c,0,d,0,c,0\\right)_{\_c};=;0\
\
\\phi^{\*}\\left(c,0,d,0\\right)\_{d}:<:1,\ \ phi^{{\*}}\\left(c,0,d,0,d,0\\right)\_{d}:=:0::\\mathrm{}{i f}:\\phi^{\*\*}\\left(c,0,d,0\\right)\_{d}:>:0\
\
\\phi^{\*}\
\
Consequently, no single round memory nor any n round action memory for some n attains\
minimax regret under this critical value of. Nor does one of the rules suggested by Robbins\
(1956) or Isbell (1959) for n > 2 (and = 1) have this property.\
\
\\delta\
\
Proof. First we provide the analogous calculations as in the proof of Proposition 3 when facing\
(a; b) = (1; v). We calculate where we do not explicitly calculate events where two successes\
of the worse action occur. Then\
\
\\left(\\pi\_{a},\\pi\_{b}\\right)=\\left(1,v\\right)\
\
\\pi^{\\delta}\
\
\\pi^{\\delta}=\\frac{1}{2}+\\frac{1}{2}\\left(1-\\delta\\right)v+\\frac{1}{2}\\left(1-v\\right)\\delta+\\frac{1}{2}v\\left(1-v\\right)x\\delta^{2}+\\frac{1}{2}v\\left(1-v\\right)\\left(1-x\\right)\\left(1-v\\right)\\delta^{3}+o\\left(v^{2}\\right)\
\
where the expressions refer to the event (a; 1; a; 1; :::), the payo⁄ in round one from choosing\
action b and the events (b; 0; a; 1; a; 1; :::), (b; 1; b; 0; a; 1; a; 1; :::) and (b; 1; b; 0; b; 0; a; 1; a; 1; :::).\
Consequently\
1 1\
\
(b,1,b,0,b,0,a,1,a,1,...)\
\
{\_{\\phi^{\\prime}}}=\\frac{1}{2}\\left({1-\\delta}\\right)-\\frac{1}{2}\\left({1-\\delta}\\right)\\left({1-\\delta-\\left({1-x}\\right){\\delta^{2}}}\\right)v+o\\left({{v^{2}}}\\right)\
\
1-\\delta-\\delta^{2}+x\\delta^{2}\\geq0\
\
Looking a bit more carefully at the above calculations as well as those in the proof of\
Proposition 3 it is easily veried that Q0 is not a worst case prior if one of the conditions in the\
statement of the proposition do not hold.\
\
Q\_{0}\
\
Q\_{0}\
\
\|W\|=2\
\
Proposition 6 Consider jW j = 2. If Q0 is a worst case prior and attains minimax regret\
then (;) = 1=2.\
a\
\
\\phi^{\*}\\left(\\emptyset\\right)\_{a}=1/2\
\
* * *\
\
Proof. Consider a rule that attains minimax regret when Q0 is a worst case prior. Then\
is Bayesian optimal under Q0. Let Dcbe the Bernoulli two-action decision problem with\
Pc(1) = Pd(0) = 1 where d 6= c. Then L (Da) = 1 (;) (;) and L (Db) =\
a b\
1 (;) (;). Since Q0 is a worst case we obtain L (Da) = L (Db) and hence\
b a\
(;) = 1=2.\
a\
\
\\phi^{\*}\
\
Q\_{0}\
\
\\phi^{\*}\
\
Q\_{0}\
\
D\_{c}\
\
P\_{c}\\left(1\\right),=,P\_{d}\\left(0\\right),=,1\
\
\\neq c.\
\
{\\cal L} _{\\phi^{\*}},(D_{a});=;{\\bf1},-,\\phi^{ _},(\\emptyset)\_{a},-,\\phi^{_},(\\emptyset)\_{b},\\delta\
\
1-\\phi^{ _}\\left(\\emptyset\\right)\_{b}-\\phi^{_}\\left(\\emptyset\\right)\_{a}\\delta\
\
Q\_{0}\
\
L\_{\\phi^{ _}}\\left(D\_{a}\\right),=,L\_{\\phi^{_}}\\left(D\_{b}\\right)\
\
4.2 Su¢ cient conditions\
\
\\phi^{\*}\\left(\\emptyset\\right)\_{a}=1/2\
\
Q\_{0}\
\
Above we show that Q0 is the only candidate for a simple worst case prior. For any symmetric\
1\
rule regret equals L (D) = (1) ja bj + (1) o ( ) so we actually expect Q0 (which\
2\
maximizes ja bj) to be a worst case prior for su¢ ciently small. Interestingly we nd below\
that Q0 does not have to be that small for this to be true.\
\
\\phi\
\
\\begin{array}{r}{\\mathcal{L} _{\\phi}\\left(D\\right)=\\left(1-\\delta\\right)\\frac{1}{2}\\left\|\\pi_{a}-\\pi\_{b}\\right\|+\\left(1-\\delta\\right)o\\left(\\delta\\right)}\\end{array}\
\
Q\_{0}\
\
\\left\|\\pi\_{a}-\\pi\_{b}\\right\\\\
\
\\delta\
\
Q\_{0}\
\
4.2.1 Single round memory\
\
In the following we search for single round memory rules that attain minimax regret. Note that\
for single round memory rules there is no di⁄erence between linearity and Bernoulli equivalence.\
\
Proposition 7 Consider jW j = 2.\
\
\|W\|=2\
\
(i) The symmetric linear single round memory rule that has the stay with a winner\
p\
property and that satises (a; 0) = 0 attains minimax regret if and only if 2 1 0:41.\
a\
This rule yields\
1 1 1\
\
\\phi^{\*}\
\
\\phi^{\*}\\left(a,0\\right)\_{a}=0\
\
i f,\\delta\\leq\\sqrt{2},-1\\approx0.41\
\
\\pi^{\\delta}=\\frac{1}{2}\\left(\\pi\_{a}+\\pi\_{b}\\right)+\\frac{1}{2}\\delta\\frac{1}{1+\\delta\\left(1-\\pi\_{a}-\\pi\_{b}\\right)}\\left(\\pi\_{a}-\\pi\_{b}\\right)^{2}\ .\
\
(ii) For any 2 (0; 1) there is no other symmetric linear single round memory rule that\
attains minimax regret.\
p\
\
p\
(iii) There is no single round memory rule that attains minimax regret for some > 2 1.\
\
\\delta,\\in,(0,1)\
\
Notice that Bayesian optimal rules generally do not have nite memory even when is small.\
For instance, as pointed out in the proof of Proposition 2, any Bayesian optimal rule under the\
two point distribution Q (v; w) with 0 < v < w < 1 does not have nite round memory.\
\
\\delta>\\sqrt{2-1}\
\
Q\\left(v,w\\right)\
\
Proof. It follows immediately that the rule described above is the unique symmetric linear\
single round memory Bayesian optimal rule under Q0. Let zcbe the discounted future value of\
payo⁄s conditional on choosing action c. Then za= (1)a+aza+ (1a) zb. Similar\
\
\\delta\
\
\\phi^{\*}\
\
0<v<w<1\
\
Q\_{\\mathrm{c}}\
\
z\_{a}=\\left(1-\\delta\\right)\\pi\_{a}+\\delta\\pi\_{a}z\_{a}+\\left(1-\\pi\_{a}\\right)\\delta z\_{b}.\
\
* * *\
\
expression for zband solving the two equations in the two unknowns zaand zbyields the\
\
expression for = 0:5 (za+ zb) given above.\
\
## Fora> bwe obtain\
\
d 1 1 + 2 + 2 4a4 2 a+ 2 2 2 a+ 4 2 a b2 2 2 b L = 2 da2 (1 + a b)\
\
where the enumerator is decreasing ina. Ifa= 1 then the enumerator is also increasing inb.\
\
Evaluating the enumerator ata= 1 andb= 0 we obtain 1 2 2 which has the positive p d p root 2 1. Hence da L 0 holds for allaandbif 2 1. On the other hand, if p d > 2 1 then da L < 0 holds whena= 1 andb= 0.\
\
## Similarly we obtain fora> b\
\
2 d 1 (1 + 2a) L = 2 : db2 (1 + a b) p Thus, L is maximized at (a;b) = (1; 0) and Q0 is a worst case prior if and only if 2 1.\
\
Since is the unique symmetric linear single round memory rule that is Bayesian optimal under\
\
Q0 there is no alternative symmetric linear single round memory rule that attains minimax regret p when 2 1.\
\
It is easily veried that arg maxD2D 0 : a(D)>b(D)L (D) is single valued for all 2 (0; 1). p Thus, by Corollary 4 does not attain minimax regret when > 2 1.\
\
Note that pb= 2 1 1+1+ 2 a a is the sum of the discounted probabilities of choosing action b b under where pbcan be derived as the solution to = (1 pb)a+ pb b.\
\
Consider an alternative symmetric linear single round memory rule. Let qcbe the prob-\
\
ability of choosing action c in the next round given c is chosen in the present round, then\
\
q c=cy + (1c) z where y = (c; 1)cand z = (c; 0)c. Consequently () =a+ 1 1+ 2qa () and L = 1 1+ 2qa () when > . It is easily veried that 2 1+ qa qbb a 2 1+ qa qba b a b d L < 0 < d L when > . Thus is among linear symmetric single round memory rules dy dz a b\
\
the only candidate for a Bayesian optimal rule and hence the only candidate for a symmetric\
\
## rule that attains minimax regret.\
\
Following Propositions 6 and 7, any single round memory rule that attains minimax regret\
\
randomizes in round one, choosing each action with probability 0:5. However, the rule selected\
\
in Proposition 7 also randomizes in later rounds whenever receiving a payo¤ in (0; 1). In the following we investigate when and whether this sort of randomizing is also necessary for attaining\
minimax regret.\
\
Proposition 8 Consider jW j = 2. Consider a single round memory rule with (c; x) 2\
c\
f0; 1g for all x 2 \[0; 1\]. Then\
\
\|W\|,=,2\
\
x\\in\[0,1\]\
\
\\phi\\left(c,x\\right)\_{c}\\in\
\
(i) attains minimax regret for all 1=3 if and only if (;) = 1=2, (c; x) = 0 if\
a c\
x < 1=3 and (c; x) = 1 if x > 1=3.\
c\
\
\\delta,\\leq,1/3\
\
i f;\\phi\\left(\\emptyset\\right) _{a};=;1/2,,;\\phi\\left(c,x\\right)_{c};=;0;;i f\
\
x<1/3\
\
\\phi\\left(c,x\\right)\_{c}=1,,\\mathit{i f},x>1/3\
\
\\delta>1/3\
\
(ii) does not attain minimax regret for > 1=3.\
\
o o\
Proof. Consider a symmetric single round memory rule with (c; x) 2 f0; 1g for all x 2\
c\
o\
\[0; 1\]. Consider D 2 arg max Lo(D). Then behaves (in terms of sequences\
D2D0: a(D)>b(D)\
of actions chosen) when facing D as the rule dened in Proposition 7 does when facting\
o\
D0 2 D0 dened by Pc(1; D0) = Pc(fx : (c; x) = 1g; D ). Setting qc= Pc(1; D0) and using\
c\
1 qqa\
the expression pbfrom the proof of Proposition 7 we obtain Lo(D ) = (a b).\
2 1+1+ q2a b\
\
\\phi^{o}\\left(c,x\\right)\_{c}\\in\\left\\0,1\\right}\
\
D^{ _}\\in\\operatorname{a r g}\\operatorname_{m a x} _{D\\in\\mathcal{D}_{0}:\\pi\_{a}(D)>\\pi\_{b}(D)}L\_{\\phi^{o}}\\left D right))\
\
\\phi^{o}\
\
\\phi^{\*}\
\
D^{\*}\
\
D\_{0}\\in\\mathcal{D}\_{0}\
\
P\_{c}\\left(\ 1,D\_{0}\\right)=P\_{c}\\left(\\left{x:\\phi^{o}\\left(c,x\\right)\_{c}=1\\right},D^{\*}\\right)\
\
q\_{c}=P\_{c}\\left(1,D\_{0}\\right)\
\
p\_{b}\
\
\\begin{array}{r}{L\_{\\phi^{o}}\\left(D^{\*}\\right)=\\frac{1}{2}\\frac{1+\\delta-2\\delta q\_{a}}{1+\\delta-\\delta q\_{a}-\\delta q\_{b}}\\left(\\pi\_{a}-\\pi\_{b}\\right)}\\end{array}\
\
o o\
Now assume that attains minimax regret. Leto= supxf (c; x) = 0g andu=\
c\
o o\
infxf (c; x) = 1g. Since D maximizes the regret of we derive thata(D ) = qa+\
c\
(1 qa)oandb(D ) = qb u. Sinceo u, the decision-maker can lower this maximal\
regret by choosing a rule witho=u=:. In other words, the decision-maker chooses and\
nature chooses qaand qband regret is given by\
\
\\phi^{o}\
\
\\begin array}{r}{\\rho\_{ _0},=,\\operatorname\*{s u p}_{x}\\left{\\phi^{0}\\left(c,x\\right)\_{c},=,0\\right}}\\end{array}\
\
\\rho\_{u}\ =\
\
\\operatorname{{f n f}} _{x}\\left{\\phi^{o}\\left(c,x\\right)_{c}=1\\right}\
\
D^{\*}\
\
\\left(1-q\_{a}\\right)\\rho\_{o}\
\
\\phi^{o}\
\
\\pi\_{b}\\left(D^{\*}\\right),=,q\_{b}\\rho\_{u}\
\
\\rho\_{o}\\geq\\rho\_{u}.\
\
\\rho\_{o}=\\rho\_{u}=:\\rho.\
\
\\rho\
\
q\_{a}\
\
L\_{f^{o}}\\left(D^{\*}\\right)=\\frac{1}{2}\\frac{1+\\delta-2\\delta q\_{a}}{1+\\delta-\\delta q\_{a}-\\delta q\_{b}}\\left(q\_{a}+\\left(1-q\_{a}\\right)\\rho-q\_{b}\\rho\\right)\ .\
\
q\_{b}\
\
Following Proposition 7, if f attains minimax regret then Q0 is a worst case prior. Hence we\
need to verify that\
\
\\begin{array}{l c l}{\\displaystyle\\frac{d}{d q\_{a}}L\_{f^{o}}\| _{(q_{a},q\_{b})=(1,0)}}&{=}&{\\displaystyle\\frac{1}{2}\\left(1-\\delta\\right)\\left(1-\\rho\\right)-\\frac{1}{2}\\delta\\left(1+\\delta\\right)\\geq0}\ {\\displaystyle\\frac{d}{d q\_{b}}L\_{f^{o}}\| _{(q_{a},q\_{b})=(1,0)}}&{=}&{-\\displaystyle\\frac{1}{2}\\left(1-\\delta\\right)\\left(\\rho-\\delta\\right)\\leq0}\ \\end{array}\
\
\\rho=1/3\
\
\\delta\\leq\\rho\\leq1/3.\
\
\\delta\\leq1/3\
\
\\textstyle{\\frac{d}{d q\_{1}}L\\geq0}\
\
\\delta\\leq1/3\
\
* * *\
\
4.2.2 Two round memory\
\
Next we search for two round memory rules that attain minimax regret. The rule we select for\
small and intermediate discount factors turns out to be a Bernoulli equivalent extension of a\
rule suggested by Robbins (1956) for use in Bernoulli two-action decision problems instead when\
= 1\. When payo⁄s are in f0; 1g this rule prescribes to switch back and forth until the rst\
success is obtained and then only to switch after two consecutive failures.\
\
^\\mathrm{a}\
\
\\delta=1\
\
Proposition 9 Consider jW j = 2. Consider the Bernoulli equivalent symmetric two round\
memory rule that has the stay with a winner property and that satises (c; 0) = (c; 0; c; 0) =\
c c\
(d; 0; c; 0) = 0 and (c; 1; c; 0) = 1 for fc; dg = fa; bg. Then\
c c\
\
\|W\|,=,2\
\
\\phi^{\*}\
\
\\phi^{ _}\\left(c,0\\right)\_{c}=\\phi^{_}\\left(c,0,c,0\\right)\_{c}=\
\
\\phi^{\*}\\left(d,0,c,0\\right)\_{r}=0\
\
\\phi^{\*}\\left(c,1,c,0\\right)\_{c}=\ 1\ \\it{f o r}\ {c,d}={a,b}\
\
\\pi^{\\delta}=\\frac{1}{2}\\left(\\pi\_{a}+\\pi\_{b}\\right)+\\frac{1}{2}\\delta\\frac{\\left(\\pi\_{a}-\\pi\_{b}\\right)^{2}\\left(1+\\delta-\\delta\\left(\\pi\_{a}+\\pi\_{b}\\right)\\right)}{\\delta^{2}\\left(1-\\pi\_{a}\\right)^{2}+\\delta^{2}\\left(1-\\pi\_{b}\\right)^{2}+\\left(1-\\delta\\right)\\left(1+\\delta\\left(2-\\pi\_{a}-\\pi\_{b}\\right)\\right)}\
\
p\
1 1\
and attains minimax regret if and only if 5 0:62. No other symmetric two round\
2 2\
p\
1 1\
memory rule attains minimax regret when = 5.\
2 2\
\
\\phi^{\*}\
\
\\textstyle\\mathit{i f\ }\\delta\\leq\\frac{1}{2}\\sqrt{5}!-!\\frac{1}{2}\\approx0.62\
\
\\textstyle{\\hat{\\delta}={\\frac{1}{2}}{\\sqrt{5}}-{\\frac{1}{2}}}}\
\
The only adjustment to the rule suggested by Robbins (1956) is that we require the decisionmaker to choose each action equally likely in the rst round. Notice that (d; 1; c; 0) is not\
c\
explicitly specied as (d; 1; c; 0) for d 6= c occurs with zero probability.\
\
\\phi^{\*}\\left(d,1,c,0\\right)\_{c}\
\
(d,1,c,0)\
\
d\\neq c\
\
dened above is simple to implement in Bernoulli two-action decision problems. However\
when payo⁄s can also be realized in (0; 1) then implementation is a bit more complicated as\
randomization is not independent across rounds. Recalling our discussion of Bernoulli equivalent\
rules in Section 3.2, one way to make the choices when observing an interior payo⁄ xmin round\
m is to take a draw dmfrom a lottery that yields 1 with probability xmand 0 with probability\
1 xmand then to remember dmfor two rounds and to act, when making choices in round\
m + 1 and m + 2, as if dmwas the payo⁄ realized in round m. Of course memory of dmfor two\
rounds is not necessary after am+16= amas in this case (am; xm; am+1; xm+1) is independent\
of xm.\
\
\\phi^{\*}\
\
d\_{m}\
\
x\_{m}\
\
1-x\_{m}\
\
An alternative way to directly dene the behavior of for all payo⁄s in \[0; 1\] is using\
the following stochastic automaton with the four states a1, a2, b1 and b2 which is graphically\
represented in Figure 1. Choose action c in state ci. Use the transition function g to nd out\
which state to enter in round one and which state to enter in the next round given the current\
\
d\_{m}\
\
m+1\
\
m+2\
\
x\_{m}\
\
\\phi^{\*}\\left(a\_{m},x\_{m},a\_{m+1},x\_{m+1}\\right)\
\
* * *\
\
state where g : ;\[(fa1; a2; b1; b2g \[0; 1\]) ! fa1; a2; b1; b2g is given by g (;) a1 = g (;) b1 = 1=2\
\
(so start o¤ in state a1 and b1 each with probability 1=2) and g (c1; x) c2 = 1 g (c1; x) d1 =\
\
g (c2; x) c2 = 1 g (c2; x) c1 = x for x 2 \[0; 1\] and fc; dg = fa; bg. State c2 can be interpreted has\
\
higher condence in action c for c 2 fa; bg :\
\
Figure 1: The selected two round memory rule as\
\
## a stochastic automaton with four states.\
\
Proof. Consider a symmetric two round memory rule that attains minimax regret when 1 p 1 = 2 5 2 . Following Lemma 5 we obtain (c; 0) c = 0, (c; 1; c; 0) c = 1, (c; 0; d; 1) d = 1,\
\
(c; 0; c; 0) c = 0, (c; 0; d; 0) d 2 f0; 1g and has the stay with a winner property.\
\
If (c; 0; d; 0) d = 1 andb= 0 then\
\
1 1 + + 2 + 3 + 2 2 2 a2a3 2 a3 3 a+ 2 3 2 a L =a 2 3 2 2 3 3 2 1 + + +a2a+2 a2a+ 2 a\
\
d 22 and2L (1; 0) = (2 1) (1 +) so this rule does not attain minimax regret if > 1=2. (da) If instead (c; 0; d; 0) d = 0 (which is the rule selected in the statement) then\
\
() 1 + 2 2 2 + 2 2 2 1 a b a a a L = 2 2 2 2 2 : 2 1 +a b a b+2 a+b\
\
1 p 1 d d Assume 2 5 2 . By rst showing that d L 0 and then that da L 0 holds when b\
\
b= 0 it can easily be veried that (a;b) = (1; 0) is the unique maximizer of L conditional\
\
ona>b. This means that Q0 is a worst case prior. 1 p 1 Now assume > 2 5 2 . It can also be easily veried that arg maxa> b L (a;b) is single\
\
valued. Thus, by Corollary 4 does not attain minimax regret.\
\
* * *\
\
To keep this paper short we refrain from an exhaustive analysis of two round memory rules\
as we did for single round memory rules. However notice that following Proposition 9 we know\
o\
that there is no two round memory rule that attains minimax regret for all 2 (0; ) where\
p5\
o 1 1\
\
> .\
> 2 2\
\
\\hat{\\delta}\\in(0,\\hat{\\delta}^{0})\
\
\\begin{array}{r}{\\delta^{o}>\\frac{1}{2}\\sqrt{5}-\\frac{1}{2}}\\end{array}\
\
Combining the result on Q0 in the proof of Proposition 9 with Propositions 3 and 6 we\
obtain:\
\
Q\_{0}\
\
p\
1 1\
Corollary 10 Consider jW j = 2. (i) Q0 is a worst case prior if and only if 5. (ii)\
2 2\
p\
1 1\
There is no deterministic rule that attains minimax regret when 5.\
2 2\
\
\|W\|=2\
\
Q\_{0}\
\
\\delta\\leq{\\textstyle\\frac{1}{2}}{\\sqrt{5}}-{\\textstyle\\frac{1}{2}}.\ \ i i)\
\
\\textstyle\\delta\\leq\\frac{1}{2}\\sqrt{5}-\\frac{1}{2}\
\
Part (ii) is presented as it is an easy corollary of our previous results. A more general proof\
that this holds for all 2 (0; 1) is far from obvious.\
\
\\hat{\\delta}\\in(0,1)\
\
4.2.3 Two round action memory\
\
Consider now two round action memory rules. In the following we investigate how this restriction\
changes the range of discount factors given in Proposition 9 in which minimax regret can be\
achieved.\
\
Proposition 11 Consider jW j = 2. There exists0with00:54 such that:\
\
(i) If0then the symmetric linear rule f with two round action memory that has\
\
- 1 +\
  the stay with a winner property and that satises f (c; ; c; 0) = 0:84 and f (c; 0) =\
  c0 0c\
\
f (d; ; c; 0) = 0 for c 6= d attains minimax regret.\
c\
p\
1 1\
\
\|W\|=2\
\
\\delta\_{0}\
\
\\delta\_{0}\\approx0.54\
\
\\delta,\\leq,\\delta\_{0}\
\
\\begin{array}{r}{f^{+}\\left(c,\\cdot,c,0\\right) _{c}=\\frac{1-\\delta_{0}}{\\delta\_{0}}\\approx0.84}\\end{array}\
\
f^{+}\\left(c,0\\right)\_{c}=\
\
f^{+}\\left(d,\\cdot,c,0\\right)\_{c}=0\
\
c\\neq,\
\
p\
1 1\
(ii) If0< 5 then there is no two round action memory rule that attains minimax\
2 2\
regret.\
\
When compared with the two round memory rule from Proposition 9, the rule f given\
+\
above is simpler in two respects. First of all, f has two round action memory so it requires less\
+\
memory than. Second of all, randomization under f occurs independently in each round\
while the implementation of required a much more complicated randomization process.\
\
Proof. Consider a symmetric two round action memory rule that is Bayesian optimal against\
Q0. Then f (;) = 0:5, f (c; 0) = 0 and f (c; 1) = f (c; ; c; 1) = f (d; ; c; 1) = 1. In particular,\
a c c c c\
f has the stay with the winner property. Let = f (c; ; c; 0) and = f (d; ; c; 0) for c 6= d.\
d d\
\
f^{+}\
\
\\phi^{\*}\
\
f^{+}\
\
\\phi^{\*}\
\
f\\left(\\emptyset\\right) _{a}=0.5,f\\left(c,0\\right)_{c}=0\
\
f\\left(c,1\\right) _{c}=f\\left(c,\\cdot,c,1\\right)_{c}=f\\left(d,\\cdot,c,1\\right)\_{c}=1.\
\
\\mu=f\\left(d,\\cdot,c,0\\right)\_{d}\
\
\\lambda=f\\left(c,\\cdot,c,0\\right)\_{d}\
\
* * *\
\
For any given round except round one consider the state described by the present and\
previous choice. Then there are four states aa, ab, bb, ba where cd species that the present\
action is d and the previous action was c. Let vn, wn, ynand znbe the respective probabilities\
1 1 1\
of being in these states in round n 2. Then v2 =a, w2 = (1a), y2 =band\
2 2 2\
1\
z2 = (1b). Given the transition matrix M equal to\
2\
\
v\_{n},,w\_{n},,y\_{n}\
\
n,\\geq,2\
\
\\begin{array}{r}{v\_{2},=,\\frac{1}{2}\\pi\_{a},;w\_{2},=,\\frac{1}{2},(1-\\pi\_{a}),;y\_{2},=,\\frac{1}{2}\\pi\_{b}}\\end{array}\
\
\\begin{array}{r}{z\_{2}=\\frac{1}{2}\\left(1-\\pi\_{b}\\right)}\\end{array}\
\
\\begin{aligned}{}&{{}\\pi\_{a}+\\left(1-\\pi\_{a}\\right)\\left(1-\\lambda\\right)}&{0}&{0}&{{}\\pi\_{a}+\\left(1-\\pi\_{a}\\right)\\left(1-\\pi\_{a}\\right)}\ {}&{{}\\left(1-\\pi\_{a}\\right)\\lambda}&{0}&{0}&{{}\ (1-\\pi\_{a})\\mu}\ {}&{{}0}&{\\pi\_{b}+\\left(1-\\pi\_{b}\\right)\\left(1-\\mu\\right)}&{\\pi\_{b}+\\left(1-\\pi\_{b}\\right)\\left(1-\\lambda\\right)}&{0}\ {}&{{}0}&{\\left(1-\\pi\_{b}\\right)\\mu}&{\\left(1-\\pi\_{b}\\right)\\lambda}&{0}\ \\end{aligned}\
\
{\\mathrm{ ~~w e~~ o b t a i n ~~}}{\\left(\\begin{array}{l l l l}{v\_{n+1}}&{w\_{n+1}}&{y\_{n+1}}&{z\_{n+1}}\\end{array}\\right)}^{T}=M\\left({\\begin{array}{l l l l}{v\_{n}}&{w\_{n}}&{y\_{n}}&{z\_{n}}\\end{array}}\\right)^{T}{\\mathrm{~~ a n d~h e n c e}}\
\
\\begin{array}{r c l l}{L}&{=}&{\\operatorname\*{m a x}\\left{\\pi\_{a},\\pi\_{b}\\right}}\ {}&{}&{-\\frac{1}{2}\\left(1-\\delta\\right)\\left(\\pi\_{a}+\\pi\_{b}\\right)-\\left(1-\\delta\\right)\\delta\\left(\\begin{array}{c c c c c}{\\pi\_{a}}&{\\pi\_{b}}&{\\pi\_{b}}&{\\pi\_{a}}\ \\end{array}\\right)\\left(I d-\\delta M\\right)^{-1}\\left(\\begin{array}{c c c c c}{v\_{2}}&{w\_{2}}&{y\_{2}}&{z\_{2}}\ \\end{array}\\right)^{T}}\ \\end{array}\
\
4;4\
where Id 2 R is the identity matrix.\
\
I d\\in\\mathbb{R}^{4,4}\
\
The explicit expression for L is too elaborate to present here but it is easily veried for\
a> bthat\
\
\\begin{array}{l c l}{\\displaystyle\\frac{d}{d\\pi\_{b}}L\| _{(\\pi_{a},\\pi\_{b})=(1,0)}}&{=}&{\\displaystyle\\frac{1}{2}\\frac{\\left(1-3\\delta+\\delta\\lambda+2\\delta^{2}-3\\delta^{2}\\lambda-\\delta^{3}\\lambda^{2}-\\delta^{4}\\lambda^{2}\\right)+2\\delta^{4}\\lambda\\mu+\\left(\\delta^{3}-\\delta^{4}\\right)\\mu^{2}}{1-\\delta+\\delta\\lambda}}\ {\\displaystyle\\frac{d}{d\\pi\_{b}}L\| _{(\\pi_{a},\\pi\_{b})=(1,0)}}&{=}&{\\displaystyle-\\frac{1}{2}\\frac{(1-\\delta)\\left(1-2\\delta+\\delta\\lambda\\right)}{1-\\delta+\\delta\\lambda}}\ \\end{array}\
\
\\pi\_{a}>\\pi\_{b}\
\
In the following we search values of and\
\
that maximize the largest value of such that\
\
d d\
Lj(;)=(1;0)0 and Lj(;)=(1;0)0 holds. Let0,0and0be the solutions to this\
da a b db a b\
\
Lj(;)=(1;0)0 and Lj(;)=(1;0)\
da a b db a b\
problem. It follows that0= 1 which yields\
So we are looking for and such that 1\
\
0 holds. Let0,0and0be the solutions to this\
d 1 3 3 2\
Lj(;)=(1;0)= + 2 + 1 .\
da a b 2\
3 3 2\
2 + = 0 and + 2 + 1 = 0.\
\
3 3 2\
So we are looking for0and0such that 1 20+0 0= 0 and0+0 0 020+ 1 = 0.\
2001\
Solving these two equations yields0= and\
\
\\textstyle\\frac{d}{d\\pi\_{a}}L\| _{(\\pi_{a},\\pi\_{b})=(1,0)}\\geq0\
\
\\lambda\_{0},,\\mu\_{0}\
\
\\mu\_{0}=1\
\
\\delta\_{0}\
\
\\begin{array}{r}{\ \ \ {\\mathrm{s}}\ \\frac{d}{d\\pi\_{a\\mathrm{s}}}L\| _{(\\pi_{a},\\pi\_{b})=(1,0)}=\\frac{1}{2}\\left(-\\delta^{3}\\lambda+\\delta^{3}-\\delta^{2}\\lambda-2\\delta+1\\right)}\\end{array}\
\
\\delta\_{0}=\\sqrt\[3\]{\\left(\\frac{17}{27}+\\frac{1}{9}\\sqrt{33}\\right)}-\\frac{2}{9\\sqrt\[3\]{\\left(\\frac{17}{27}+\\frac{1}{9}\\sqrt{33}\\right)}}-\\frac{1}{3}\\approx0.54369.\
\
\\delta\_{0}\
\
\\begin{array}{r}{\\lambda\_{0}=\\frac{2\\delta\_{0}-1}{\\delta\_{0}}}\\end{array}\
\
\\delta>\\delta\_{0}\
\
Q\_{0}\
\
* * *\
\
In the following we consider0, =0, = 1 anda> bwhich yields\
\
\\delta\\leq\\delta\_{0},,\\lambda=\\lambda\_{0},,\\mu=1\
\
\\pi\_{a}>\\pi\_{b}\
\
L=\\frac{1}{2}\\frac{\\left(1-\\delta\\left(1-\\delta\\right)\\pi\_{a}+\\delta\\left(1+\\delta\\right)\\lambda\_{0}\\left(1-\\pi\_{a}\\right)-\\delta^{2}\\right)\\left(1-\\delta\\left(1-\\lambda\_{0}\\right)\\left(1-\\pi\_{b}\\right)\\right)\\left(\\pi\_{a}-\\pi\_{b}\\right)}{1-\\delta+\\lambda\_{0}\\left(2-\\pi\_{a}-\\pi\_{b}\\right)\\delta-\\left(1-\\lambda\_{0}\\right)\\left(1+\\lambda\_{0}\\right)\\left(1-\\pi\_{a}\\right)\\left(1-\\pi\_{b}\\right)\\delta^{2}+\\left(1-\\lambda\_{0}\\right)^{2}\\left(1-\\pi\_{a}\\right)\\left(1-\\pi\_{b}\\right)\\delta^{3}}\
\
and will prove that L attains its maximum at (a; b) = (1; 0).\
\
\ (\\pi\_{a},\\pi\_{b})=(1,0)\
\
d\
First we will prove that L 0. Leta= 1 w. Then\
db\
\
\\textstyle\\frac{d}{d\\pi\_{b}}L\\leq0\
\
\\pi\_{a}=1-w\
\
\\begin{array}{l c l}{\\displaystyle\\frac{d}{d\\pi\_{b}}L\| _{\\pi_{b}=0}}&{=}&{\\displaystyle-\\frac{1}{2}\\left(1-\\left(1-w-\\lambda\_{0}w\\right)\\delta-w\\left(1-\\lambda\_{0}\\right)\\delta^{2}\\right)\*}\ {}&{}&{\\displaystyle\\frac{\\left(1-\\left(2-\\lambda\_{0}\\right)\\delta+\\delta\\left(1+\\lambda\_{0}\\left(1-\\delta\\right)+\\lambda\_{0}^{2}\\delta\\right(1-\\lambda\_{0})^{2}\\delta^{2}\\right)w-\\left(1-\\lambda\_{0}\\right)\\delta^{2}w^{2}\\right)}{\\left(1+\\delta\\lambda\_{0}w-\\delta^{2}w+\\delta^{2}\\lambda\_{0}w\\right)^{2}\\left(1-\\delta+\\lambda\_{0}\\delta\\right)}}\ \\end{array}\
\
The enumerator of the second factor is the only term can take negative values. Looking at this\
d d\
term we nd that Lj(;)=(1;0)0 implies Lj=00 for allb. We also obtain\
db a b db b\
\
\\textstyle{\\frac{d}{d\\pi\_{b}}L\| _{(\\pi_{a},\\pi\_{b})=(1,0)}\\leq0}\
\
\\begin{array}{r}{\\frac{d}{d\\pi\_{b}}L\| _{\\pi_{b}=0}\\leq0}\\end{array}\
\
\\pi\_{b}\
\
\\frac{d}{d\\pi\_{b}}\\frac{d}{d\\pi\_{b}}L=-\\delta\\frac{\\left(1+\\delta\\lambda\_{0}-\\delta\\right)\\left(\\delta\\lambda\_{0}w+\\delta^{2}\\lambda\_{0}w-\\delta+1-w\\delta^{2}+\\delta u\\right)^{2}\\left(\\delta\\lambda\_{0}w+1-\\delta w\\right)^{2}}{\\left(1-\\left(1+\\pi\_{b}\\lambda\_{0}-\\lambda\_{0}-\\lambda\_{0}w\\right)\\delta-w\\left(1-\\lambda\_{0}\\right)\\left(1-\\pi\_{b}\\right)\\delta^{2}\\left(1+\\lambda\_{0}-\\left(1-\\lambda\_{0}\\right)\\delta\\right)\\right)^{3}}\\leq0\
\
d\
which completes the proof that L 0 holds for0.\
db\
\
\\textstyle{\\frac{d}{d\\pi\_{b}}L\\leq0}\
\
\\delta\\leq\\delta\_{0}\
\
Ifb= 0 then\
\
\\pi\_{b}=0\
\
\\frac{d}{d w}L=-\\frac{1}{2}\\frac{\\left(1-2\\delta-\\delta^{2}\\lambda\_{0}-\\delta^{3}\\lambda\_{0}+\\delta^{3}\\right)+2\\delta\\left(1+\\lambda\_{0}+\\delta\\lambda\_{0}-\\delta\\right)w}{\\displaystyle\\phantom+\\left+\\delta^{2}\\left(1+\\lambda\_{0}+\\delta\\lambda\_{0}-\\delta\\right)\\left(\\lambda\_{0}+\\delta\\lambda\_{0}-\\delta\\right)w^{2}\\right.}{\\left(w\\delta^{2}\\lambda\_{0}+\\delta\\lambda\_{0}w-w\\delta^{2}+1\\right)^{2}}\
\
d d\
Since 1 +0+00 we obtain Lj(w;)=(0;0)0 implies Lj=00 which completes\
dw b dw b\
the proof of the fact that (a; b) = (1; 0) maximizes L if0.\
\
1+\\lambda\_{0}+!!delta\\lambda\_{0}-\\delta\\geq0\
\
5 Conclusion\
\
This paper demonstrates how simple but well designed rules can have very powerful properties\
\
This paper demonstrates how simple but well designed rules can have very powerful properties\
\
when choosing between two actions under low and intermediate discount factors ( 0:62).\
Reducing search for minimax regret to search for a Nash equilibrium of a zero-sum game and\
\
Reducing search for minimax regret to search for a Nash equilibrium of a zero-sum game and\
discovering the importance of Q0 are the keys to deriving our results. Whether the cuto⁄ 0:62 is\
restrictive depends on the particular application as, besides the degree of patiency, the discount\
factor can also be interpreted as the probability of being able to choose again. When > 0:62\
\
factor can also be interpreted as the probability of being able to choose again. When > 0:62\
or when there are more than two actions then our results are weaker; minimax regret can be\
\
((\\pi\_{a},\\pi\_{b})=(1,0)\
\
\\delta\\leq\\delta\_{0}\
\
Q\_{0} attained with Bernoulli equivalent behavior. Lack of space has kept us from including existing material on the usefulness of single round memory when there are more than two actions and the discount factor is low. Our main characterization theorem remains a simple extension of results of Berry and Fristedt (1985) formulated for Bernoulli decisions and two actions only. The extension to more than two actions is immediate. Key to being able to allow for a range of payo¤s is understanding the importance of Bernoulli equivalent rules. Given our theorem and proof it is immediate that our characterization also applies when selecting among a closed subset of behavioral rules such as among the set of rules with a given memory. So how much memory is needed to attain minimax regret behavior when there are two actions? A single round su¢ ces when the discount factor is small. Randomization after receiving interior payo¤s by means of a simple linear rule improves performance and increases the maximal discount factor under which minimax regret is attainable from 0:33 to 0:41. For larger values of the discount factor at least two rounds of memory are necessary. A simple linear rule that depends on the action chosen two rounds ago but not of the payo¤ received in that round su¢ ces up to = 0:54: To achieve minimax regret for discount factors up to 0:62 requires a linear rule that is best described by a stochastic automaton with four states. Beyond 0:62 the analysis becomes substantially more di¢ cult. We only know that either minimax regret behavior does not have nite round memory or that any symmetric worst case prior has at least four decision problems in its support (i.e. there is more than one decision problem in which action one yields higher expected payo¤s than action two that maximizes regret under the candidate rule). On the side our analysis provides insights into when learning is most di¢ cult for a Bayesian. It is the symmetric prior over the deterministic decision problems, Q0, if and only if the discount factor is less than 0:62. For larger discount factors we only know that a worst case prior can always be found among the set of priors over the Bernoulli decision problems. This is very intuitive as it means that nature gives the Bayesian the hardest time if it draws from very similar decision problems that have maximal variation in the set of realizable payo¤s.\
\
* * *\
\
A Bayesian Optimal Behavior and Randomization\
\
The following result shows that a Bayesian optimal decision maker will typically never have an\
incentive to randomize.\
\
Proposition 12 For almost all symmetric priors there is some payo⁄ z 2 (0; 1) that can occur\
in any round with positive probability such that a Bayesian decision maker will not randomize\
after receiving z.\
\
Proof. Consider a symmetric prior Q 2pD such that there exists a payo⁄ z 2 (0; 1) that\
can occur for any D drawn under Q and that reveals that the current action is best, i.e.\
P (c(D) > d(D) j action c yields z, D unknown but drawn using prior Q) = 1, c 6= d. No-\
R\
tice that the set of such priors lies dense inpD. Consider any f 2 arg minf 2FLf(D) dQ (D)\
and any history (a1; x1; ::; am 1; xm 1) that can arise under f for some D drawn under Q. Then\
f (a1; x1; ::; am; z) = 1.\
am\
\
z\\in(0,1,\
\
Q\\in\\Delta\_{p}\\mathcal{D}\
\
\\therefore z,\\in,(0,1\
\
Q\
\
P\\left(\\pi\_{c}\\left(D\\right)>\\pi\_{d}\\left(D\\right)\\right)\
\
References\
\
\\Delta\_{p}\\mathcal{D}\
\
f\\left(a\_{1},x\_{1},..,a\_{m},z\\right) _{a_{m}}=1.5.\
\
Q),=,,1,,,c,\\neq=,d.\
\
\\textstyle{\\begin}{f f\\in\\operatorname{a r g}\\operatorname\*{m i n} _{f\\in\\mathcal{F}}\\int L_{f}\\left(D\\right)d Q\\left(D\\right)}\\end{array}\
\
\\left(a\_{1},x\_{1},..,a\_{m-1},x\_{m-1}\\right)\
\
\[1\] Berry, D.A. and B. Fristedt (1985), Bandit Problems: Sequential Allocation of Experiments,\
Chapman-Hall, London.\
\[2\] Brgers, T., Morales, A.J., and R. Sarin (2001), Expedient and Monotone Learning Rules,\
Mimeo, University College London, [http://www.ucl.ac.uk/~uctpa01/Papers.htm](http://www.ucl.ac.uk/~uctpa01/Papers.htm).\
\[3\] Chamberlain, G. (2000), Econometrics and Decision Theory, J. Econom. 95, 255-83.\
\[4\] French, S. (1986), Decision Theory: An Introduction to the Mathematics of Rationality,\
Chichester: Ellis Horwood Ltd.\
\[5\] Gilboa, I. and D. Schmeidler (1989), Maxmin Expected Utility with a Non-Unique Prior,\
J. Math. Econ. 18, 14153.\
\[6\] Isbell, J. R. (1959), On a Problem of Robbins, Ann. Math. Statist. 30, 606-10.\
\
\[7\] Kakigi, R. (1983), A Note on Discounted Future Two-Armed Bandits, Ann. Statist.\
11(2), 707-11.\
\
* * *\
\
\[8\] Narendra, K.S. and M.A.L. Thathachar (1989), Learning Automata: An Introduction. En- glewood Cli¤s: Prentice Hall. \[9\] Neeman, Z. (2001), The E¤ectiveness of English Auctions,Games Econ. Beh. (forthcom- ing). \[10\] Robbins, H. (1952), Some Aspects of the Sequential Design of Experiments, Bull. Amer. Math. Soc. 58(5), 527-35. \[11\] Robbins, H. (1956), A Sequential Decision Problem with a Finite Memory, Proc. Nat. Acad. Sci. 42, 920-3. \[12\] Samaranayake, K. (1992), Stay-With-A-Winnter Rule for Dependent Bernoulli Bandits, Ann. Statist. 20(4), 2111-23. \[13\] Samuels, S.M. (1968), Randomized Rules for the Two-Armed-Bandit with Finite Memory, Ann. Math. Stat. 39(6), 2103-7. \[14\] Savage, L. J. (1951), The Theory of Statistical Decision, J. Amer. Stat. Assoc. 46(253), 55-67. \[15\] Savage, L. J. (1972), The Foundation of Statistics, Dover, New York \[16\] Simon, H. (1982), Models of Bounded Rationality, MIT Press. \[17\] Tsetlin, M.L. (1961), On the Behaviour of Finite Automata in Random Media, Automa- tion and Remote Control 22, 1210-19. \[18\] von Neumann, J. and O. Morgenstern (1944), Theory of Games and Economic Behavior, Princeton Univ. Press. \[19\] Wald, A. (1950), Statistical decision functions, Chelsea: Bronx.
