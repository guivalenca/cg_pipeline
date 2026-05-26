---
id: "46"
title: "A mostly complete chart of Neural Networks"
source_url: "https://www.bigdataheaven.com/wp-content/uploads/2019/02/AI-Neural-Networks.-22.pdf"
fetch_url: "https://www.bigdataheaven.com/wp-content/uploads/2019/02/AI-Neural-Networks.-22.pdf"
resolved_url: "https://www.bigdataheaven.com/wp-content/uploads/2019/02/AI-Neural-Networks.-22.pdf"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T03:59:51.975848Z"
provider: "firecrawl"
strategy: "pdf"
cache_key: "552cb6fa3bb85c8ac5f0cf91c241116e8725e056600a534ca99a8b87adab33bc"
firecrawl_status_code: 200
firecrawl_content_type: "application/pdf"
word_count: 13982
char_count: 94102
content_sha256: "8e2a8704b360432d1e5e9ad175280f0d6cf9f674c4e109dce512ec8beec2e57c"
image_count: 0
link_count: 1
warnings:
  - "missing_screenshot"
  - "ocr_pdf"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes:
  - "pdf_mode_ocr"
  - "chart_heavy_pdf_force_ocr"
---

Backfed Input Cell

A mostly complete chart of

Input Cell

Neural Networks

Noisy Input Cell

Hidden Cell

©2016 Fjodor van Veen - asimovinstitute.org

Probablistic Hidden Cell

Perceptron (P)

Feed Forward (FF)

Spiking Hidden Cell

Radial Basis Network (RBF)

Output Cell

Recurrent Neural Network (RNN)

Match Input Output Cell

Recurrent Cell

Long / Short Term Memory (LSTM)

Different Memory Cell

Memory Cell

Convolution or Pool

Kernel

Auto Encoder (AE)

Denoising AE (DAE)

Markov Chain (MC)

Hopfield Network (HN)

Boltzmann Machine (BM)

Deep Belief Network (DBN)

Deep Convolutional Network (DCN)

Deep Convolutional Inverse Graphics Network (DCIGN)

Generative Adversarial Network (GAN)

Liquid State Machine (LSM)

Deep Residual Network (DRN)

* * *

Neural N

formative chart to build network Graphs

©2016 Fjodor van Veen - asimovinstitute.org

Deep Feed Forward Example

Deep Recurrent Example (previous iteration)

Deep GRU Example (previous iteration)

* * *

| Linear Vector Spaces:
Definition. A linear vector space, $X$ is a set of elements (vectors) defined over a scalar field, $F$, that satisfies the following conditions:
1) if $x \\in X$ and $y \\in X$ then $xy \\in X$;
2) $x + y \\in X$;
3) $(x+y) \\cdot e = x \\cdot y + (y \\cdot e)$
4) There is a unique vector $e \\in X$, such that $x - 0 = y$ for all $x \\in X$.
5) For each vector $x \\in X$ there is a unique vector $y$ in X, to be called $(x,y)$ such that $x - y$ is multiplicative for all scalars $a \\in F$, and all vectors $x \\in X$.
6) For any two scalars $x \\in E$ and $y \\in E$ any $x \\in E$ ($a = (a\_1)b$)
7) For any two scalars $x \\in E$ and $y \\in E$ any $x \\in E$ ($a = (a\_1)b$)
8) $(a-b)x = ax + bx$.
9) $10)(x+y) = ax + ay$
Linear Independence: Consider $n$ vectors $\\{x\_1,x\_2,\\dots,x\_n\\}$. If there exists $n$ scalars $x\_1,x\_2,\\dots,x\_n$, at least one of which is nonzero, such that $x+x\_1+x\_2+\\cdots+x\_n=1$.
The $n$ lines are linearly dependent.

Spanning a Space:
Let $X$ be a linear space and let ${u\_1,u\_2,\\dots,u\_n}$ be a subset of vectors in $X$. This subspace span $X$ if and only if $X$ exists in some scalars $x\_1,x\_2,\\dots,x\_n$, such that $x=x\_1+x\_2+\\cdots+x\_n=1$.

Inner Product:
$(x,y)$ for any scalar function of $x$ and $y$.
$1.(x,y)=\\left(y\_x\\right)2.\\left(x\_y\\right)+\\left(y\_x\\right)+\\left(y\_y\\right)$
$3.(x,y) \\geq 0$, where equality holds iff $x$ is the zero vector.

Norm: Ascalar function $\|\|x\|\|$ is called a norm if it satisfies:
$1.\|\|x\|\| \\geq 0$
$2.\|\|x\|\| = 0$ if and only if $x = 0$.
$3.\|\|x\|\| = \|a\|\|\|\|x\|\|$
$4.\|\|x\|\| + y\|\| ≤ \|\|x\|\| + \|y\|\|$

Angle: The angle $\\theta$ bet. $2$ vectors $x$ and $y$ is defined by $\\cos \\theta=\\frac{\|x\|}{\|y\|}$
Orthogonality: $2$ vectors $x, y$ are said to be orthogonal if $f(x,y)=0$.
Gram Schmidt Orthogonization:
Assume that we have $n$ independent vectors $y\_1,y\_2,\\dots,y\_n$. From these vectors we will obtain $n$ orthogonal vectors $v\_1,v\_2,\\dots,v\_n$.
where $(v\_i,y\_i)$ $v\_i$ is the projection of $y\_i$ on $v\_i$

Vector Expansions:
$x=\\sum\_{i=1}^{n}x\_i v\_i=x\_1 v\_1+x\_2 v\_2+\\cdots+x\_n v\_n$,
for orthogonal vectors, $x\_j=(v\_j/x)\_j$

Reciprocal Basis Vectors:
$(r\_i,j\_v)=\\begin{cases}0 & i \\neq j \\1 & i=j\\end{cases}$, $x\_j=(r\_j,x)$
To compute the reciprocal basis vectors: set $B=\[v\_1v\_2,\\dots,v\_n\]$,
$R=\[r\_1,r\_2,\\dots,r\_n\]$, $R^T=B^{-1}$ In matrix form: $x^T=B^{-1}x^T$

Transformations:
A transformation consists of three parts: domain $X={x}$, range $Y={y}$, and a rule relating each $x\\in X$ to an element $y\\in Y$.

Linear Transformations: transformation $A$ is linear if:

1. for all $x\_1,x\_2\\in X$, $X(x\_1+x\_2)=A(x\_1)+A(x\_2)$
2. for all $x\\in X$, $A\\in R$, $A(x\_a)=aN(x\_b)$

Matrix Representations:
Let $(v\_1,v\_2,\\dots,v\_n)$ be a basis for vector space $X$, and let $(u\_1,u\_2,\\dots,u\_n)$ be a basis for vector space $Y$. Let $A$ be a linear transformation with domain $X$ and range $Y$. $A(x\_a)=y$.
The coefficients of the matrix representation are obtained from $A(v\_i)=\\sum\_{j=1}^{n}a\_{ij}u\_i$

Change of Basis: $B=\[t\_1,t\_2,\\dots,t\_n\]$, $B\_w=\[w\_1w\_2\\dots w\_n\]$
$A=\[B^TAB\]$
Eigenvalues and Eigenvectors: $Az=\\lambda z\_1$ and $A(-\\lambda z\_1)=0$
Diagonalization: $B=\[z\_1,z\_2,\\dots,z\_n\]$, where $z\_1,z\_2,\\dots,z\_n$ are the eigenvectors of a square matrix $A$,$-B^TAB=$diag($\\lambda\_1\\lambda\_2\\dots\\lambda\_n$)

Perceptron Architecture:
$a=hardim(Wp+b),w\_i=\[w^T,w^T,\\dots,w^T\]^T$
$a=hardim(W\_p)=hardim(\\omega^T p+b)$

Decision Boundary:
$W^p+b\_1=b\_2$
The decision boundary is orthogonal to the weight vector.
Single-layer perceptron takes both or both cells such that $Ax$ efficiency, as one of the cell fills B, is increased.

Hebb's Postulate:
When an onion of cell $A$ is near enough to excite a cell $B$ and repeatedly it persists into infinity, it some growth process on membrane takes place or both cells such that $Ax$ efficiency, as one of the cell fills B, is increased.

Liberal Associator: a purelinp(Wp)

The Hebb Rule: Supervised Form $w\_{ij}^new=w\_{ij}^old+t\_{q1}P\_{q1}$
$W=t\_1P\_1^+t\_2P\_2^++t\_4P\_4^+$
$W=\[t\_1 t\_2...t\_q\]TP^T$

Pseudoinverse Rule: WTP
When the number, $R$, of rows of $P$ is greater than the num ber of columns,$Q$, of $P$ and the columns of $P$ are independent, then the pseudoinverse can be computed by $(P^T=P^T)^{1/2}$

Variations of Hebbian Learning:
Filtered Learning: $W\_{new}=(1-\\gamma)W\_{old}+at\_1p\_q^p$
Delta Rule (Ch.10): $W\_{new}=W\_{old}+a(t\_q-a\_q)p\_q^p$
Unsupervised Hebb (Ch.13): $W\_{new}=W\_{old}+aa\_qp\_q^p$

Tavlor: $F(x)=F(x^ _)+\\nabla F(x)^T\|\_{x=x^_}-(x-x^ _)+\\frac{1}{2}(x-x^_)^2\\nabla F(x)^T\| _{x=x^}-\\frac{1}{2}(x-x^)^2\\nabla F(x)^T\|_{x=x^ _}$_
_Grad $\\nabla F(x)=\[\\frac{\\partial}{\\partial x\_1}F(x)\\frac{\\partial}{\\partial x\_2}F(x)\|\_{x=x^_}-\\frac{\\partial}{\\partial x\_n}F(x)\|\_{x=x^\*}\]$

Hessian: $F(x)=\[\\frac{\\partial}{\\partial x\_1}F(x)\\frac{\\partial}{\\partial x\_2}F(x)\| _{x=x^\*}-\\frac{\\partial}{\\partial x\_n}F(x)\|_{x=x^\*}\]$

Directional Derivatives:
$1^{\\text{nd}}D\_{\\text{dir.}}:\\frac{P^T F(x)}{\|p\|^2}$
$2^{\\text{nd}}D\_{\\text{dir.}}:\\frac{P^T \\nabla^2 F(x)}{\|p\|^2

1)\\mathrm{ ~~i f~~}x\\inin\ {cal X}\\mathrm{ ~~a n d~~}y\\in X{\\cal t}h\\mathrm{m}\ x\ y y\\in X\\2\ {\\cal X}+\ y-++x3}x+x=y+y+z=+

x\\in X,a(\\delta,)=(a,\\delta)x,

x^{+}(-x)=0,

(a+b)x=a x+b x.

xscriptstyle\\in,,,,,,,,-,

a(x+y)=a+y y

{\\mathbf{x} _{1},\\mathbf{x}_{2},\\ldots,\\mathbf{x}\_{mathrm}{ ~~a~~}}

\ _t mathbf w{{}}^T\\mathbf{\\mathit{p}}+b_{t}=0

a\_{1}x\_{1}+a\_{2}x\_{2}+\\cdots+a\_{2}x\_{2}=0

\\chi\_{\\lambda,\\dots,kappa

x=x\_{1}u\_{1}+x\_{1}u\_{2}+\\cdots+x\_{n}u\_{n}

\\overline{{1,\|x\|\\geq}}0

3.\|a x\|=\|a\|\|x\|

\|x+y\|\\leq\|x\|+\|y\|

2,\|x\|=0,\\mathrm{i f n d},\\mathrm{i n}\|y,\\mathrm{i f},x=0.

\\begin{array}{c}{\ \ \ \ \ \ \\\ {\\bf r c c p p i r o n;L a a r i i g;\ u{\\bf E}}}{{\\bf\\bf{W}}^{n e w}=\ {\\bf{}}^{o l d}\ \ +{\ bf{}}{}bfbf{\\bf{e}}^{T}\ ,{\\bf\\Phi{}}^{n e w}=\ {\\bf\\Phi{}}^{o l d}\ +\ {\\bf{}}{\\bf{b}}^{o l d}\ +\ {\\bf{e}}\ ,}\ {\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \

3.(x,x)\\geq0

(x,y)=0,

\ y\_{b}y\_{b}...,y\_{l}

a\_{1}=h a r(\\ln\\vert(n\_{1})=h a r d(\\ln(1N{}^{2}p+b\_{1})

\\frac{(v\_{i},y\_{n})}{(v\_{i},v\_{i})}v\_{i}

\ _{V_{l}},V\_{\\lambda},.ldots.,V\_{n}.

x=\\sum\_{i=1}^{n}x\_{i}v\_{i}=x\_{1}v\_{1}+x\_{2}v\_{2}+\\cdots+x\_{n}v\_{n},,

{\\mathfrak{a}}=p u r e l i n({\\mathsf{W}}{\\mathfrak{p}})

\\overline{{\\left(r\_{i},v\_{j}\\right)=\\left{\\begin{matrix}{0}&{i\\neq j}\ {1}&{i=j}\\end{array}\\right.,}}}\ { _{j}==(r_{j},x)}

\ o r o r t h o g o n a l,v e c t o r s,x\_{j}=\\frac{(v\_{j},x)}{(v\_{j},v\_{j})}

\\mathbf{x}^{v}=\\mathbf{B}^{-1},\\mathbf{x}^{s}

A\\big(v\_{j}\\big)=\\dot{\\sum\_{i=1}^{m}a\_{i j}u\_{i}}

\\overline{{\\underline{{\\mathfrak{R u l e}}};S u}}e r v i s e d{,F o r m:},{\\hat{\\mathsf{w}}} _{i j}^{n e w}=\\mathsf{w}_{i j}^{o l d}+t\_{q i}P\_{q i}

\\begin{array}{l}{x\\in X,a\\in R,A(a x)=a A(x)}\\end{array}

X=\\left{x\_{i}\\right}

W=t\_{1}P\_{1}^{T}+t\_{2}P\_{2}^{T}+\\cdots+t\_{Q}P\_{Q0}^{T}

\\mathbb{R}^{-}}\[\_{\ {bf sf f\_{{1}}}\ {\\bf\\sf{f}} _{{2}}\\ldots{{\\bf\\sf{f}}}_{{}{\\sf{n}}}\];,;\\mathbb{R}^{T}=\ {\\bf\\sf{B}}^{-1}

y\_{t}\\in Y.

\\mathbf{W}=\\left\[\\begin{}\\\mathbf{{}t\_{1\\}t{ _22\ \ }\\mathbf{\ t{{mathbfmathfrak t t}}}_{\\mathbb{Q}}}\\end{array}\\right\]\\left\[\\begin{matrix}{\\mathbf{p} _{1}^{T}}\ {\\mathbf{p}_{2}^{T}}\ {\\vdots}\ {\\mathbf{p}\_{0}^{T}}\\end{array}\\right\]=\\mathbf{T}\\mathbf{P}^{T}

{u\_{1},u\_{2},\\dots,u\_{n}}

\\overline{{^{n e w}=(1-\\gamma)W^{l d+\\alpha mathfrak t\_{{q}}}\\mathfrak{p}\_{q{}}^{T}}}

\\overline{x\_{1},x\_{2}\\in X,A(x\_{1}\ x\_{2}))}=A(x\_{1})+A(x\_{2})

\\mathbf{W}^{n e w},=,\\mathbf{W}^{o l d},+,\\alpha(\\mathbf{t} _{q}\ -,\\mathbf{a}_{q})\\mathbf{p}\_{q}^{^T}

\\mathbf{\\nabla}\\cdot\\mathbf{P}^{+}=(\\mathbb{P}^{T}\\mathbb{P})^{-1}\\mathbf{\\nabla}^{T}

{\\bf B} _{t}=\[{\\bf t}_{1},,,{\\bf t} _{2},,\\stackrel{\\cdot}{\\sim},{\\bf\ \\dot{t}}_{n}\];,\\quad{\\bf B} _{w}=\[{\\bf w}_{1},,{\\bf w} _{2},\\ldots{\\bf w}_{n}\]

\\mathbf{W}=\\mathbf{T}\\mathbf{P}^{+}

{z,z\_{2},\\ldots,z\_{n}}

\\underline{{\\mathbf{T a v l o r}}};(mathbf x=F(\\mathbf x^{ _})+\\nabla F(\\mathbf x)^{T}\|\_{\\mathbf x=\\mathbf x^{_}}\\left(\\mathbf x-\\mathbf x^{\*}\\right)+

\\mathbf{H e b b,(C h.13):}\\mathbf{W}^{n e w},=,\\mathbf{W}^{o l d},+,\\alpha\\mathbf{a} _{q}\\mathbf{p}_{q}^{T}

\\underline{{\\underline{{\\mathbf{G r a d}}}}},\ {\\mathit{V F}}(\\mathbf{x})=\\left\[\ {\\frac{\\partial}{\\partial x\_ _{1}}}F(\\mathbf{x})\ \ \ \ {{\\frac{\\partial}{\\partial x_{2}}}}F(\\mathbf{x})\ \ \\ldots{{\\frac{\\partial}{\\partial x\_{n}}}}F(\\mathbf{x})\\right\]^{T}

{\\left\[\\begin{array}{l l}{{\\frac{\\partial}{\\partial{x\_{1}}^{2}}}F({\\dot{\\mathbf x}})}&{{}~{\\frac{\\partial}{\\partial{x\_{1}},\\partial{x\_{2}}}}F({\\mathbf x})\\ldots}&{{\\frac{\\partial}{\\partial{x\_{1}},\\partial{x\_{n}}}}F({\\mathbf x})}\\end{array}\\right\]}

{\\underline{{{mathrm H H e s s i n n}}}}\\nabla^{2}\\mathbb{F}(x)=

\\begin{array}{r l r l}{\\left\|\\frac{\\partial}{\\partial x\_{2},\\partial x\_{1}}F(\\mathbf{x})\\right.}&{\\left.\\frac{\\partial}{\\partial x\_{2}\ ^{{2}}}F(\\mathbf{x})\\ldots\\right.}&{\\left.\\frac{\\partial}{\\partial x\_{2},\\partial x\_{mathbf n}}(\\mathbf{x})\\right\|}\ {\\vdots}&{\ }&{\\vdots}&{\\vdots}\\end{array}

\\begin{array}{r}{:}\\end{array}

\\begin{array}{r}{\\boxed{\\begin{array}{r}{\\underline{{1bf^^{T}D i r.D e r.}}\_{\\parallel}{\\parallel\ \\bf{p{\ }}},\\underline{{\ \ \\frac{\ \ \\bf{p}^{T}D F(x)}{\\parallel\ \\parallel}}},\\underline{{\ ^{2bf}^{n d}}D i r.D e D..}}\ {\\underline{{\ {p\\bf\ p}^{T}F(x)\ \\parallel{\\bf p}}}}\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \

F(x)<F(x+\\Delta x)

F(x)!\\leq!F(x+\\Delta x)

\\begin{array}{l}{\\underbrace{\\stackrel{\\stackrel{\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \

\\delta>\|\\Delta x\|>0.

\\overline{{2^{}O r d e r C o n d i t i o n:}}\\nabla^{2}\\vec{F(\ x)}\|\_{x=x^{\*}}\\geq0,\\dot{(P o s i t i v e,S e m i:}

\\begin{array}{r}{\\boxed{\\mathfrak{Q u a d r a t i c\ f n}:F x={\\textstyle\\frac{1}{2}}\\mathbf{x}^{\\mathsf{T}}\\mathbf{A},\\mathbf{x}+\\mathbf{d}^{\\mathsf{T}}\\mathbf{x}+\\mathbf{c}}}\\end{array}

* * *

\| General Minimization Algorithm:
$x\_{k+1}=k\_{x}+a\_{p}p\_{p}$ or $\\Delta k=(k\_{k+1}-x\_k)=\\alpha\_{p}k\_{p}$
Steepest Descent Algorithm:
$x\_{k+1}=k\_{x}-a\_{p}g\_{k}$ where $g\_{k}=\\nabla F(x)\| _{x=x_{k}}$
Stable Learning Rate: $(\\alpha\_{c},\\text{constant})\\alpha<\\frac{2}{\\lambda\_{\\max}}$
Learning Rate to Minimize Along the Line:
$x\_{k+1}=k\_{x}+a\_{p}p\_{p}\\Rightarrow \\alpha\_{k}=-\\frac{1}{P\_{k}}\\alpha\_{AP}$ (for quadratic fn.)
After Minimization Along the Line:
$x\_{k+1}=k\_{x}+a\_{p}p\_{p}\\Rightarrow g\_{k}^{T}p\_{k}=0$
ADALINE: $a=\\text{purelin}(Wp(k)+b)$
Mean Square Error: $(\\text{for ADALINE it is a quadratic fn.})$
$F(x)=E\[e^{2}\]=E\[t-a\]^{2}=E\[(t-x^{2})z\]$
$F(x)=-2x^{2}h+x^{T}Rx$
$c=E\[t^{2}\], h=E\[tz\]$ and $R=\[ezz\]^{\\top}=A=2R, d=-2H$
Unique minimum, if it exists, $x^{ _}={R}^{-1}h$, where $x=\\left\[\\begin{array}{l}w\ b\\end{array}\\right\]$ and $z=\\left\[\\begin{array}{l}p\ 1\\end{array}\\right\]$_
_LMS Algorithm: $W(k+1)=W(k)+2\\alpha e(k)p^{T}(k)$_
_$b(k+1)=b(k)+2a(e(k))$_
_Convergence Point: $x^{_}=R^{-1}h$
Stable Learning Rate: $0<\\alpha/1/\\lambda\_{\\max}$ where $\\lambda\_{\\max}$ is the maximum eigenvalue of R
Adaptive Filter ADALINE:

| $a(k)=\\text{purelin}(Wp(k)+b)=\\sum\_{i=1}^{R}w\_{i,j}y(k-i+1)+b$ |
| --- |

\\mathsf{x} _{k+1}=\\mathsf{x}_{k}-\\mathsf{a} _{k}\\mathsf{a}_{k}

\\mathbf{x} _{k+1}=\\mathbf{x}_{k}+\\alpha\_{k}\\mathbf{p} _{k};;\\mathrm{o}\\mathbfDelta\\mathbfmathbf{x}_{k}=(\\mathbf{x} _{k+1}-\\mathbf{x}_{k})=\\alpha\_{k}\\mathbf{}\_{k}

{\\lambda\_{1}\\lambda\_{2},\\ldots,\\lambda\_{n}}

\\mathbf{x} _{k+1}=\\mathbf{\\tilde{x}}_{k}+\\alpha\_{k}\\mathbf{p} _{k}\\stackrel{i s}{\\Rightarrow}\\alpha_{k}=,-\\frac{\\mathbf{g} _{k}^{\\top}\\mathbf{p}}{\\mathbf{p}_{k}\ ^{\\top}\\mathbf{tilde p\_\_{k k}}},(\\mathtt{F o r,q u a d r a t i c,f n.})

x\_{k+1}=x\_{k}+a\_{k}p\_{k}\\Rightarrow p\_{k+1}^{T}p\_{k}=0

\\begin array}{r}{\\Delta\\mathbf{W}^{m}(k)=\\gamma\\Delta\\mathbf{W}^{m}(k-1)-(1-\\gamma)\\alpha,\\mathbf{s}^{m}(\\mathbf{a}^{m-1})^{T}}\\end{array}

A D A I N E:a=p u r e l i n(W p+b)

\\Delta\\mathbf{b}^{m}(k)=\\gamma\\Delta\\mathbf{b}^{m}(k-1)-(1-\\gamma)\\alpha,\\mathbf{s}^{m}

\\overline{{F(\\mathbf{x})=E\[e^{2}\]=\[\\dot{E}(\\dot{t}-\\alpha)^{2}\]=E\[(t-\\mathbf{x}^{T}\\dot{\\mathbf{z}})^{2}\]}}

F(x)=c-2x^{}}-{x^{7}}{x^{7}}{x^

\\mathbf{x}=\ \[{}\_{1}\\mathbf{w}\]

\ =E\[t^{2}\],\ \\bf h{h}=E\[t\\bf{z}\]\ \\mathrm}{}{a n d}\ \\bf{R}=E\[\\bf{z}\\bf{z}^{T}\]\\Rightarrow\_{A\ =\ 2\ \ R,\\bf\\mathrm{d}\ =\ -2\\bf{h}}

\\mathbf{x}^{\*}=\\mathbf{R}^{-1}\\mathbf{h}

:\\mathbf{x}^{\*}=\\mathbb{R}^{-1}\\mathbf{h}

\\lambda\_{m a x}

a(k)=p u r e l i n(\\mathsf{W p}(k)+b)=\\sum\_{i=1}^{R}\\mathbf{w}\_{1,i}y(k-i+1)+b

\\frac{{\\mathrm{L M S},\\mathrm{A l S r o t i t h:},\ \\mathbf{W}}k({\\boldsymbol{k}}+1)=\\mathbf{W}(k)+2\\alpha,\\mathbf{e}(k),\\mathbf{p}^{T}(k)}{\\mathbf{b}(k+1)=\\mathbf{b}(k)+2\\alpha,\\mathbf{e}(k)}

\\overline{{\\mathrm{\\bf sssociation};~a=hardlim(\\mathrm{W\\bf }^{0}\\mathrm{\\bf P}^{0}+\\mathrmW\\bf p)}}

\\begin{array}{r}{\\left\|\\begin{array}{l l l l}{\\mathbf{S e n s i t i v i t y}}&{\\mathbf{s}^{m}=\\frac{\\partial\\tilde{F}}{\\partial\\mathbf{n}^{m}}=\\left\[\\begin{matrix}{\\frac{\\partial\\tilde{F}}{\\partial\\mathbf{n} _{1}^{m}}}&{\\frac{\\partial\\tilde{F}}{\\partial\\mathbf{n}_{1}^{m}}}&{\\dots}&{\\frac{\\partial\\tilde{F}}{\\partial\\mathbf{n}\_{s^{m}}}}\\end{array}\\right\]^{T}}\\end{array}\\right.}\\end{array}

\ {\ {{W\\mathfrak q}}(q)={\\mathfrak W}(q-1)}+{\\mathfrak a},{\\mathfrak a}(q){\\mathfrak p}^{T}(q)

\\overline{{\ {\\bf W}(q)=(1-\\gamma){\\bf W}(q-1)+\\alpha,{\\bf a}(q){\\bf p}^{T}(q)}}

\\begin array}{r}{\\dot{f}^{m}\\big(n\_{j}^{m}\\big)=\\frac{\\partial f^{m}\\big(n\_{j}^{m}\\big)}{\\partial n\_{j}^{m}}}\\end{array}

\\mathbf{I n s t a r}:\\mathbf{a}=\ r a a l d i m(\\mathbf{\\hat{W}p+}),::\\mathbf{a}=h a r d l i m(\\mathbf{\\hat}\_{1}\\mathbf{\\hat{w}}^{T}\\mathbf{p}+b)

\\mathbf{a}=\\mathbf{a}^{n}

s^{\\sf{M}}=.\ {\\dot{\\sf F{F}}}^{\\sf{M}}({\\sf{n}}^{\\sf{M}})({\\sf{t}}-{\\sf{a}})

\\phantom{} _{i}\\mathbf{w}(q)=\\phantom{}_{i}\\mathbf{w}(q-1)+\\alpha,a\_{i}(q)(\\mathbf{p}(q)-\\phantom{}\_{i}\\mathbf{w}(q-1))

\_}\ \ w^{T}\\mathfrak{p}=\\Big\|\ \_{1}\\mathsf{w}\\Big\|\|\\mathfrak{p}\|\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \

O u1S u r a\ :alpha S a a sin(W)

\\mathbf{w{}}} _{{j}(q)=\\mathbf{{w}}_{j}(q-1)+\\alpha,\\left(\\mathbf{a}(q)-\\mathbf{w{}} _{j}(q-1)\\right)\\mathbf{{p}}_{j}(q)

\\begin{array}{r}{\\left\|\\begin{array}{l}{\\mathbf{s}^{m}=\\dot{\\mathbf{F}}^{m}(\\mathbf{n}^{m})(\\mathbf{W}^{m+1})^{T}\\mathbf{s}^{m+1};f o r;m=M-1,...,2,1,;w hmathrm r c}\ {\\dot{\\mathbf{F}}^{m}(\\mathbf{n}^{m})=\\mathrm{d i a g}(\\left\[\[\\hathat{f f}^{m}(n\_{1}^{m})\\stackrel{\\hat{f}^{m}(n\_{2}^{m})}{\\stackrel{\\hat{f}^{m}(n\_{2}^{m})}{\\stackrel{\\hat{f}^{m}({n\_{2}^{m}})}{\\stackrel{\\hat{f}^{m}({n\_{\ }^{m}})}{\ \ ,,,,,,,,},},}}}.\\{\\dot{f}^{m}(n\_{\\mathbf{s}^{m}}^{m})\\right\])}\\end{array}\\right.}\\end{array}\
\
\\begin{array}{l}{\\underbrace{\\mathbf{C o m p e t i t i v e\ L a v e r\ a}}=\\mathbf{c o m p e t}(\\mathbf{W}\\mathbf{p})=\\mathbf{c o m p e t}(\\mathbf{n})}\ {\\underbrace{\\mathbf{C o m p e t i t i v e\ L e a r n i n g\ w i t h\ t h e\ K o h o n e n\ R u l e}}.}\\end{array}\
\
=(1-a)\_{i}\\cdot\ (q-1)+a p(q\
\
\\begin{array}{r}{i:w\ q q=:\ w\\left(q-1\\right),\ i i\\neq i^{ _}\ \\mathrm{w h e r e}\ i i^{_}\ }\ {:cdots:\\cdots,\ cdots}\\end{array}\
\
\ \_{i}\\mathsf{w}(q)=\ \_{i}\\mathsf{w}(q-1)+\\alpha\\left(\\mathsf{p}(q)-\ \_{i}\\mathsf{w}(q-1)\\right)\
\
\\begin{array}{r}{=(1-\\alpha,),,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,\
\
{begin{} _{i}\\mathsf{w}^{1}(q)={}_{i}\\mathsf{w}^{1}(q-1)+\\alpha,\\Big(\\mathsf{p}(q)-\\mathsf{\\partial}\_{i}\\mathsf{w}^{1}(q-1)\\Big),}\\end{array}\
\
\\begin{array}{r}{\\frac{\\mathrm{L N O,N e t w o r k:}\ }{\\left(w\_{k,i}^{2}=1\\right)}\\Rightarrow\\mathrm{s u b c l a s s,}i,\\mathrm{s},\ amathrm{}}&{{}bf a^{1}=\\left{\|\ \ a,^{}\ }}\ {n\\end{}right.{}{\ ,!{\\bf}}^{1}=c o m p e t({{\\bf n}}^{1}),,,,,{{\\bf a}}^{2}={\\bf W}^{2}{\\bf a}^{1}}\
\
\\begin{array}{r}{{}{{}bf\\omega}^{\ }{\\bf w}^{1}(q)={{}\_{i}}{cdot}{{bf}}^{\\cdot}{{\\bf w}}^{\\cdot}\ \ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\ \\\\
\
\\begin{array}{r}{D e t a y;alpha t u t u t u(t-1),I n t e g r a t o r;\\alpha(t)=\\int\_{0}^{t}u(\\tau)d\\tau+\\alpha(0)^{-1}\\alpha\\tau(0)^{-1}}end{{}\
\
* * *\
\
MACHINE LEARNING IN EMOJI\
\
SUPERVISED\
\
human builds model based on input / output\
\
UNSUPERVISED\
\
human input, machine output human utilizes if satisfactory\
\
REINFORCEMENT\
\
human input, machine output human reward/punish, cycle continues\
\
BASIC REGRESSION\
\
linear\_model.LinearRegression()\
\
LINEAR\
\
Lots of numerical data\
\
LOGISTIC\
\
linear\_model.LogisticRegression()\
\
Target variable is categorical\
\
or\
\
cluster.KMeans()\
\
CLASSIFICATION\
\
NEURAL NET\
\
neural\_network.MLPClassifier()\
\
Complex relationships. Prone to overfitting Basically magic.\
\
covariance. EllipticalEnvelope()\
\
tree.DecisionTreeClassifier()\
\
K-NN\
\
neighbors.KNeighborsClassifier()\
\
Find best split randomly Can also be regression\
\
Group membership based on proximity\
\
RANDOM FOREST ensemble.RandomForestClassifier()\
\
DECISION TREE\
\
svm.SVC() svm.LinearSVC()\
\
If/then/else. Non-contiguous data Can also be regression\
\
Similar datum into groups based on centroids\
\
Maximum margin classifier. Fundamental Data Science algorithm\
\
CLUSTER ANALYSIS\
\
NAIVE BAYES GaussianNB() MultinomialNB() BernoulliNB()\
\
Finding outliers\
\
Updating knowledge step by step with new info\
\
through grouping\
\
SVM\
\
FEATURE REDUCTION\
\
T-DISTRIB STOCHASTIC NEITB EMBEDDING\
\
Visualize high dimensional data. Convert similarity to joint probabilities\
\
PRINCIPLE COMPONENT ANALYSIS\
\
Distill feature space into components that describe greatest variance\
\
CANONICAL CORRELATION ANALYSIS\
\
Making sense of cross-correlation matrices\
\
LINEAR DISCRIMINANT ANALYSIS\
\
Linear combination of features that separates classes\
\
OTHER IMPORTANT CONCEPTS\
\
BIAS VARIANCE TRADEOFF\
\
UNDERFITTING/OVERFITTING\
\
INERTIA\
\
ACCURACY FUNCTION\
\
PRECISION FUNCTION\
\
TP / (TP + FP)\
\
SPECIFICITY FUNCTION\
\
TN / (FP+TN)\
\
SENSITIVITY FUNCTION\
\
TP / (TP + FN)\
\
* * *\
\
Python For Data Science Cheat Sheet\
\
Learn Python for data science Interactively at [www.DataCamp.com](http://www.datacamp.com/)\
\
Scikit-Learn\
\
Scikit-learn is an open source Python library that implements a range of machine learning, preprocessing, cross-validation and visualization algorithms using a unified interface.\
\
A Basic Example\
\
````python\
>>> iris = datasets.load_iris()\
\
Loading The Data\
\
Your data needs to be numeric and stored as NumPy arrays or SciPy sparse matrices. Other types that are convertible to numeric arrays, such as Pandas DataFrame, are also acceptable.\
\
Create Your Model\
\
Preprocessing The Data\
\
Support Vector Machines (SVM)\
\
```python\
>>> from sklearn.svm import SVC\
>>> svc = SVC(kernel='linear')\
\
Naive Bayes\
\
Linear Regression\
\
Supervised Learning Estimators\
\
Unsupervised Learning Estimators\
\
KNN\
\
```python\
>>> from sklearn.naive_bayes import GaussianNB\
>>> gnb = GaussianNB()\
\
```python\
>>> from sklearn import neighbors\
>>> knn = neighbors.KNeighborsClassifier(n_neighbors=5)\
\
```python\
>>> from sklearn.cluster import KMeans\
>>> k means = KMeans(n clusters=3, random state=0)\
\
```python\
>>> from sklearn.linear_model import LinearRegression\
>>> lr = LinearRegression(normalize=True)\
\
Principal Component Analysis (PCA)\
\
```python\
>>> from sklearn.decomposition import PCA\
>>> pca = PCA(ncomponents=0.95)\
\
>>> lr.fit(X, y)\
\
```python\
>>> from sklearn.preprocessing import Normalizer\
>>> scaler = Normalizer().fit(X_train)\
>>> normalized_X = scaler.transform(X_train)\
>>> normalized_X = scaler.transform(X_test)\
\
Binarization\
\
Supervised learning\
\
```python\
>>> from sklearn.preprocessing import StandardScaler\
>>> scaler = StandardScaler().fit(X_train)\
>>> standardized_X = scaler.transform(X_train)\
>>> standardized_X_test = scaler.transform(X_test)\
\
```python\
>>> from sklearn.preprocessing import Binarizer\
>>> binarizer = Binarizer(threshold=0.0).fit(X)\
>>> binary X = binarizer.transform(X)\
\
Evaluate Your Model's Performance\
\
Classification Metrics\
\
| knn.score(X_test, y_test) | Estimator score method |\
| --- | --- |\
| from sklearn.metrics import accuracy_score | Metric scoring functions |\
| accuracy_score(y_test, y_pred) |  |\
\
Imputing Missing Values\
\
```python\
>>> from sklearn.preprocessing import Imputer\
>>> imp = Imputer(missing_values=0, strategy='mean', axis=0)\
\
```python\
>>> from sklearn.preprocessing import Imputer\
>>> imp = Imputer(missing_values=0, strategy='mean', axis=0)\
\
```python\
>>> y = enc.fit_transform(y)\
\
Accuracy Score\
\
Generating Polynomial Features\
\
Classification Report\
\
| &gt;&gt; from sklearn.metrics import classification_report | Precision, recall, f1-score |\
| --- | --- |\
| &gt;&gt; printclassification_report(y_test, y_pred) |  |\
\
```python\
>>> from sklearn.preprocessing import PolynomialFeatures\
>>> poly = PolynomialFeatures(5)\
>>> poly.fit_transform(X)\
\
Confusion Matrix\
\
```python\
>>> from sklearn.metrics import mean_squared_error\
>>> mean_squared_error(y_test, y_pred)\
\
Regression Metrics\
\
Mean Absolute Error\
\
Mean Squared Error\
\
```python\
>>> from sklearn.metrics import r2_score\
>>> r2_score(y_true, y_pred)\
\
R $ ^{2} $ Score\
\
```python\
>>> from sklearn.metrics import adjusted_rand_score\
>>> adjusted_rand_score(y_true, y_pred)\
...\
\
Clustering Metrics\
\
Adjusted Rand Index\
\
Homogeneity\
\
```python\
>>> from sklearn.metrics import homogeneity_score\
>>> homogeneity_score(y_true, y_pred)\
\
V-measure\
\
```python\
>>> from sklearn.metrics import v_measure_score\
>>> metrics.v_measure_score(y_true, y_pred)\
\
```python\
>>> from sklearn.cross_validation import cross_val_score\
>>> print(cross_val_score(knn, X_train, y_train, cv=4))\
>>> print(cross_val_score(lr, X, y, cv=2)]

Cross-Validation

randomized Parameter Optimization

param_grid=params)

```python
>>> from sklearn.grid search import RandomizedSearchCV
>>> params = ["n_neighbors": range(1,5),\
                   "weight": ["uniform", "distance"]]

```python
>>> print(grid.best_store_)
>>> print(grid.best_estimator_.n_neighbors)

```python
>>> rsearch = RandomizedSearchCV(estimator=knn,

Grid Search

```python
>>> rsearch.fit(X_train, y_train)
>>> print(rsearch.best_score )

DataCamp Learn Python for Data Science Interactively

---

Microsoft Azure Machine Learning: Algorithm Cheat Sheet

This cheat sheet helps you choose the best Azure Machine Learning Studio algorithm for your predictive analytics solution. Your decision is driven by both the nature of your data and the question you're trying to answer.

MULTICLASS CLASSIFICATION

Python For Data Science Cheat Sheet

Variables and Data Types

Variable Assignment

Calculations With Variables

>>> x+2

>>> x-2

String Operations

Asking For Help

```python
>>> my_string = 'thisStringIsAwesome'
>>> my_string
'thisStringIsAwesome'

>>> x**2

```python
>>> my_string * 2
'thisStringIsAwesomethisStringIsAwesome'
>>> my_string + 'Innit'
'thisStringIsAwesomeInnit'
>>> 'm' in my_string
True

>>> x82

Sum of two variables

Subtraction of two variables

Multiplication of two variables

Exponentiation of a variable

Remainder of a variable

Division of a variable

Lists

```python
>>> a = 'is'
>>> b = 'nice'
>>> my_list = ['my', 'list', a, b]
>>> my_list2 = [[4,5,6,7], [3,4,5,6]]

Selecting List Elements

String Operations

List Operations

```python
>>> my_string[3]
>>> my_string[4:9]

String Methods

```python
>>> my_list + my_list
{'my', 'list', 'is', 'nice', 'my',
>>> my_list * 2
{'my', 'list', 'is', 'nice', 'my',
>>> my_list2 > 4

```json
'list', 'is', 'mice']

'list', 'is', 'mice']

Data analysis

```python
>>> my_string.upper()
>>> my_string.lower()
>>> my_string.count("w")
>>> my_string.replace("o", "i")
>>> my_string.strip()

>>> import numpy

2D plotting

matplotlib

```python
>>> import numpy as np

>>> from math import pi

Libraries

Import libraries

Install Python

Leading open data science platform powered by Python

Free IDE that is included with Anaconda

ANACONDA

Numpy Arrays

```python
>>> np.insert(my_array, 1, 5)

Selecting Numpy Array Elements Subst

```python
>>> np.append(other_array)

Numpy Array Functions

```python
>>> my_array + np.array([5, 6, 7, 8])
array([6, 8, 10, 12])

my_2darray[rows,columns]

```python
>>> np.mean(my_array)

array([2, 4, 6, 8])

```python
>>> my_array > 3
array([False, False, False, True], dtype=bool)
>>> my_array * 2

```python
>>> my_array[0:2]
array([1, 2])

```python
>>> np.median(my_array)

```python
>>> np.median(my_array)
>>> my.array.coerce()
>>> np.std(my_array)

---

Python For Data Science Cheat Sheet

Bokeh

Learn Bokeh Interactively at www.DataCamp.com taught by Bryan Van de Ven,core contributor

Plotting With Bokeh

The Python interactive visualization library Bokeh enables high-performance visual presentation of large datasets in modern web browsers.

Bokeh's mid-level general purpose bokeh.plotting interface is centered around two main components: data and glyphs.

plot

data

The basic steps to creating plots with the bokeh.plotting interface are:

2. Create a new plot

3. Add renderers for your data, with visual customizations

1. Prepare some data:
Python lists, NumPy arrays, Pandas DataFrames and other sequences of values

Customized Glyphs

5. Show or save the results

```python
>>> p.circle('mpg', 'cyl', source=cds_df,
                selection_color='red',
                nonselection_alpha=0.1)

```python
>>> p = figure(title="simple line example",
                  x_axis_label='x',
                  v_axis_label='v')
````

**Step 2**

Hover Glyphs

> > > from bokeh.plotting import figure

````python
>>> from bokeh.io import output_file, show

```python
>>> p.line(x, y, legend="Temp.", line_width-2)  Step 3
>>> output_file("lines.html")  Step 4
>>> show(p)  Step 2

```python
>>> hover = HoverTool(tooltips=None, mode='vline')
>>> p.add_tools(hover)

Glyphs

```python
>>> p1.circle(np.array([1,2,3]), np.array([3,2,1]),
    fill_color='white')

```python
>>> color_mapper = CategoricalColorMapper(
    factors=['Europe', 'Asia', 'US'],
    palette=['red', 'green', 'blue'])

Scatter Markers

Also see Lists, NumPy & Pandas

```python
>>> from bokeh.plotting import figure
>>> p1 = figure(plot_width=300, tools='pan,box_zoom')
>>> p2 = figure(plot_width=300, plot_height=300,
                  x_range={0, 8}, y_range={0, 8})
>>> p3 = figure()

Line Glyphs

```python
>>> df = pd.DataFrame(np.array([[33.9, 4, 65], 'US'],
[[33.9, 4, 65]], axis=1))

```python
[21, 4, 4, 109, 'Europe']],
columns=['mpg', 'cyl', 'hp', 'origin'],
index=['Toyota', 'Fiat', 'Volvo'])

```python
>>> p2.square(np.array([1.5,3.5,5.5]), [1,4,3],
    color='blue', size=1)

```python
>>> p1.line([1,2,3,4], [3,4,5,6], line_width=2)
>>> p2.multi_line(pd.DataFrame([[1,2,3], [5,6,7]]),
                    pd.DataFrame([[3,4,5], [3,2,1]])

```python
>>> from bokeh.models import ColumnDataSource
>>> cds_df = ColumnDataSource(df)

Rows & Columns Layout

Plotting

```python
>>> from bokeh.layouts import row >>> from bokeh.layouts import columns
>>> layout = row(p1,p2, p3) >>> layout = column(p1,p2,p3)

Under the hood, your data is converted to Column Data Sources. You can also do this manually:

Rows

>>> import numpy as np

Data

```python
>>>layout = row(column(p1,p2), p3)

Grid Layout

Linked Plots

>>> row1 = [p1,p2]

>>> row2 = [p3]

```python
>>> tab1 = Panel(child=p1, title="tab1")
>>> tab2 = Panel(child=p2, title="tab2")

```python
>>> layout = gridplot([[p1,p2],[p3]])

Linked Brushing

```python
>>> p2.x_range = p1.x_range
>>> p2.y_range = p1.y_range

Linked Axes

Tabbed Layout

```python
>>> p4 = figure(plot_width = 100, tools='box_select,lasso_select')

```python
>>> from bokeh.models.widgets import Panel, Tabs

```python
>>> p5 = figure(plot_width = 200, tools='box_select,lasso_select')
>>> p5.figure(plot_width = 200)

```python
>>> p5.circle('npg', 'hp', source=cds_df)
>>> length = p5.fit()

Legend Orientation

```python
>>> layout = Tabs(tabs=[tab1, tab2])

```python
>>> p.legend.orientation = "horizontal"

Legend Background & Border

Legends

Legend Location

Inside Plot Area

```python
>>> p.legend.location = 'bottom_left'

```python
>>> r1 = p2.asterisk(np.array([1,2,3]), np.array([3,2,1])

```python
>>> legend = Legend(items=({"One" , [p1, r1]], {"Two" , [r2]]) , location=(0, -30))
>>> p.add_layout(legend, 'right')

Output

Statistical Charts With Bokeh

```python
>>> from bokeh.io import output_file, show
>>> output_file('my_bar_chart.html', mode='cdn')

```python
>>> from bokeh.io import output_notebook, show
>>> output_notebook()

Notebook Output

Bokeh's high-level bokeh.charts interface is ideal for quickly creating statistical charts

Embedding

```python
>>> from bokeh.charts import Bar
>>> p = Bar(df, stacked=True, pale)

Standalone HTML

```python
>>> from bokeh.embed import file_html

Box Plot

```python
>>> html = file_html(p, CDN, "my_plot")

```python
>>> from bokeh.charts import BoxPlot

Components

```python
>>> p = BoxPlot(df, values='vals', label='cyl',
                    legend='bottom_right')

>>> from bokeh.embed import components

>>> script, div = components(p)

Histogram

```python
>>> from bokeh.charts import Histogram
>>> p = Histogram(df, title='Histogram')

5 Show or Save Your Plots

Scatter Plot

```python
>>> from bokeh.charts import Scatter

```python
>>> show(p1)
>>> show(layout)

```python
>>> p = Scatter(df, x='mpg', y='hp', marker='square',
                xlabel='Miles Per Gallon',
                ylabel='Horsepower')

DataCamp

---

About

TensorFlow

TensorFlow is an open source software library for numerical computation using data flow graphs. TensorFlow was originally developed for the purposes of conducting machine learning and deep neural networks research, but the system is general enough to be applicable in a wide variety of other domains as well.

Skflow

Scikit Flow provides a set of high level model classes that you can use to easily integrate with your existing Scikit-learn pipeline code. Scikit Flow is a simplified interface for TensorFlow,to get people started on predictive analytics and data mining. Scikit Flow has been merged into TensorFlow since version 0.8 and now called TensorFlow Learn.

Keras

Keras is a minimalist, highly modular neural networks library, written in Python and capable of running on top of either TensorFlow or Theano

Installation

How to install new package in Python:

pip install <package-name>
Example: pip install requests

How to install tensorflow?

How to install Skflow

pip install keras update ~/.keras/keras.json - replace "theano" by "tensorflow"

Helpers

Python helper Important functions type(object) Get object type help(object) Get help for object (list of available methods, attributes, signatures and so on)

globals()
Return the dictionary containing the current scope's global variables.

str(object)
Transform an object to string

locals()
Update and return a dictionary containing the current scope's local variables.

id(object)
Return the identity of an object. This is guaranteed to be unique among simultaneously existing objects.
import __builtin__
dir(__builtin__)
Other built-in functions

TensorFlow Main classes

Main classes
tf.Graph()
tf.Operation()
tf.Tensor()
tf.Session()

Some useful functions

```python
tf.get_default_session()
tf.get_default_graph()
tf.reset_default_graph()
ops.reset_default_graph()
tf.device("/cpu:0")
tf.name_scope(value)
tf.convert_to_tensor(value)

TensorFlow Optimizers

Each classifier and regressor have following fields n_classes=0 (Regressor), n_classes are expected to be input (Classifiers) batch_size=32, steps=200,// except TensorFlowRNNClassifier - there is 50 optimizer='Adagrad' learning_rate=0.1,

GradientDescentOptimizer
AdadeltaOptimizer
AdagradOptimizer
MomentumOptimizer
AdamOptimizer
FtrlOptimizer
RMSPropOptimizer

Reduction

reduce_sum
reduce_prod
reduce_min
reduce_max
reduce_mean
reduce_all
reduce_any
accumulate_n

Activation functions
tf.nn?
relu
relu6
elu
softplus
softsign
dropout
bias_add
sigmoid
tanh
sigmoid_cross_entropy_with_logits
softmax
log_softmax
softmax_cross_entropy_with_logits
sparse_softmax_cross_entropy_with_logits
weighted_cross_entropy_with_logits
etc.

Main classes

Skflow

TensorFlowClassifier
TensorFlowRegressor
TensorFlowDNNClassifier
TensorFlowDNNRegressor
TensorFlowLinearClassifier
TensorFlowLinearRegressor
TensorFlowRNNClassifier
TensorFlowRNNRegressor

---

Python For Data Science Cheat Sheet

Keras

Learn Python for data science interactively at www.DataCamp.com

Keras

Keras is a powerful and easy-to-use deep learning library for Theano and TensorFlow that provides a high-level neural networks API to develop and evaluate deep learning models.

A Basic Example

```python
>>> import numpy as np
>>> from keras.models import Sequential
>>> from keras.layers import Dense
>>> data = np.random.randint(1000, 100)
>>> labels = np.random.randint(2, size=(1000, 1))
>>> model = Sequential()
>>> model.add(Dense(32,
                     activation='relu',
                     input_dim=100))
>>> model.add(Dense(1, activation='sigmoid'))
>>> model.compile(optimizer='rmsprop',
                 loss='binary_crossentropy',
                 metrics=['accuracy'])
>>> model.fit(data, labels, epochs=10, batch_size=32)
>>> predictions = model.predict(data)

Your data needs to be stored as NumPy arrays or as a list of NumPy arrays. Ideally, you split the data in training and test sets, for which you can also resort to the train_test_split module of sklearn.cross_validation.

Data

Keras Data Sets

```python
>>> from keras.datasets import boston_housing,
        mnist,
        cifar10,

```python
>>> (k_train,y_train),(k_test,y_test) = mnist.load_data()
>>> (k_train2,y_train2),(k_test2,y_test2) = botton_boosting_load_data()
>>> (k_train3,y_train3),(k_test3,y_test3) = indel_load_data()
>>> (k_train4,y_train4),(k_test4,y_test4) = indel_load_data(num_words=00000)
>>> num_classes = 10

```python
>>> from urllib.request import urlopen
>>> data = np.loadtxt(urlopen("http://archive.ics.uci.edu/
ml/machine-learning-databases/pima-indians-diabetes/
pima-indians-diabetes.data"),delimiter=",")
>>> X = data[:,0:8]
>>> y = data [:,8]

Sequential Model

Model Architecture

```python
>>> from keras.models import Sequential
>>> model1 = Sequential()
>>> model2 = Sequential()
>>> model3 = Sequential()

Multilayer Perceptron (MLP)

```python
>>> from keras.layers import Dense
>>> model.add(Dense(12,

```python
>>> model.add(Dense(8, kernel_initializer='uniform', activation='relu'))
>>> model.add(Dense(1, kernel_initializer='uniform', activation='sigmoid'))

input_dim=8,
kernel_initializer='uniform',
activation='relu')

Binary Classification

Multi-Class Classification

Preprocessing

```python
>>> model.add(Dense(512, activation='relu', input_shape=(784,)))

```python
>>> from keras.layers import Dropout

```python
>>> model.add(Dropout(0.2))

```python
>>> model.add(Dense(512,activation='relu'))
>>> model.add(Dense(8,8))

```python
>>> model.add(Dense(64,activation='relu',input_dim=train_data.shape[1]))
>>> model.add(Dense(1))

Convolutional Neural Network (CNN)

Regression

Sequence Padding

```python
>>> from keras.layers import Activation, Conv2D, MaxPooling2D, Flatten
>>> model2.add(Conv2D(32,(3,3),padding='same',input_shape=x_train.shape[1:]))
>>> model2.add(Activation('relu'))

Inspect Model

```python
>>> model2.add(ConV2D(32,(3,3)))
>>> model2.add(Activation('relu'))

Recurrent Neural Network (RNN

```python
>>> model2.add(MaxPooling2D(pc)
>>> model2.add(Dropout(0.25))

```python
>>> model2.add(Activation('relu'))
>>> model2.add(Conv2D(64,(3, 3)))

```python
>>> model2.add(Conv2b(64,(3, 3)))
>>> model2.add(Activation('relu'))

One-Hot Encoding

Also see NumPy & Scikit-Learn

Compile Model

```python
>>> model13.add(Embedding(20000, 128))
>>> model13.add(LSTM(128, dropout=0.2, recurrent_dropout=0.2))
>>> model13.add(Dense(1, activation='sigmoid'))

```python
>>> model2.add(Activation('relu'))

```python
>>> from keras.preprocessing import sequence
>>> x_train4 = sequence.pad_sequences(x_train4,maxlen=80)
>>> x_test5 = sequence.pad_sequences(x_test4,maxlen=80)

```python
>>> from keras.klayers import Embedding,LSTM

```python
>>> model2.add(Flatten())
>>> model2.add(Dense(512))

MLP: Binary Classification

```python
>>> from keras.utils import to_categorical
>>> Y_train = to_categorical(y_train, num_classes)
>>> Y_test = to_categorical(y_test3, num_classes)
>>> Y_train3 = to_categorical(y_train3, num_classes)
>>> Y_test3 = to_categorical(y_test3, num_classes)

```python
>>> model.compile(optimizer='rmsprop',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
MLP Regression

```python
>>> model.compile(optimizer='adam',
                  loss='binary_crossentropy',
                  metrics=['accuracy'])

MLP: Regression

Train and Test Sets

Recurrent Neural Network

Standardization/Normalization

```python
>>> model3.compile(loss='binary_crossentropy',
                    optimizer='adam',
                    metrics=['accuracy'])

```python
>>> df = pd.DataFrame(data,

```python
dt(x_train4,
    y_train4,
    batch_size=32,
    epochs=15,
    verbose=1,
    validation_data=(x_test4,y_test4)

A two-dimensional labeled data structure with columns of potentially different types

Evaluate Your Model's Performance

```python
>>> model3.predict(x_test4, batch_size=32)
>>> model3.predict_classes(x_test4,batch_size=32)

```python
>>> score = model3.evaluate(x_test,
                             y_test,
                             batch_size=32)

Prediction

Model Fine-tuning

```python
>>> from keras.optimizers import RMSprop
>>> opt = RMSprop(10,0.0001, decay=1e-6)
>>> model2.compile(loss='categorical_crossentropy',
                     optimizer=RMSprop,
                     metrics='accuracy')

```python
>>> from keras.utils import early_stopping
>>> early_stopping_monitor = EarlyStopping(patience=2)
>>> model3.fit(x_train4,

y_train4,

Python For Data Science Cheat Sheet

y_train4,
batch_size=32,

Learn Python for Data Science interactively at www.DataCamp.com

DataCamp

```python
validation_data=(x_test4,y_test4),
callbacks=[early_stopping_monitor])

pandas $y_{i}t = \beta^{t}x_{i t} + \mu_{i} + \epsilon_{i t}$

```python
>>> s = pd.Series([3, -5, 7, 4], index=['a', 'b', 'c', 'd'])

Read and Write to CSV

Series

Pandas Data Structures

```python
>>> pd.read_csv('file.csv', header=None, nrows=5)
>>> pd.to_csv('myDataFrame.csv')

Selection

Also see NumPy Arrays

Getting

```python
>>> pd.to_excel('dir/myDataFrame.xlsx', sheet_name='Sheet1')
Read multiple sheets from the same file

```python
>> df[1:]
Country
1    India
2    Brazil

Selecting, Boolean Indexing & Setting

Read and Write to SQL Query or Database Table

```python
>>> df.at([0], ['Country'])
'Belgium'

Country Brazil
Capital Brasilia
Population 207847528

```python
>>> xlsx = pd.ExcelFile('nle.xls')
>>> df = pd.read_excel(xlsx, 'Sheet1')

```python
>>> from sqlalchemy import create_engine
>>> engine = create_engine('sqlite://://:memory:')
>>> adducted_object = Object.from_string(engine)

By Label

```python
>>> engine = create_engine (sqlite:///memory: )
>>> pd.read_sql ("SELECT * FROM my_table", engine)
>>> pd.read_sql_table('my_table', engine)

```python
>>> pd.read_sql_table('my_table', engine)
>>> pd.read_sql_query("SELECT * FROM my_table;", engine

```python
read_sql() is a convenience wrapper around read_sql_table() and
read_sql_query()

Select single value by row & column labels

```python
>>> s.drop(['a', 'c'])

Dropping

Sort & Rank

```python
>>> df.sort_index(by='Country')
>>> s.order()
>>> df.rank()

(rows,columns)
Describe index
Describe DataFrame columns
Info on DataFrame
Number of non-NA values

```python
>>> df.shape
>>> df.index
>>> df.columns
>>> df.info()
>>> df.count()

Arithmetic Operations with Fill Methods

You can also do the internal data alignment yourself with the help of the fill methods:

Median of values

```python
>>> s.add(s3, fill_value=0)
a    10.0
b    -5.0
c    5.0
d    7.0

NA values are introduced in the indices that don't overlap:

```python
>>> f = lambda x: x*2
>>> df.apply(f)
>>> df.applymap(f)

internal Data Alignment

```python
>>> s.sub(s3, fill_value=2)
>>> s.div(s3, fill_value=4)
>>> s.mul(s3, fill_value=3)

---

Python For Data Science Cheat Sheet
NumPy Basics

Learn Python for Data Science Interactively at www.DataCamp.com

NumPy

The NumPy library is the core library for scientific computing in Python. It provides a high-performance multidimensional array object, and tools for working with these arrays.

>>> import numpy as np

NumPy Arrays

1D array

2D array

Creating Arrays

```python
>>> b = np.array([(4, 1, 5)])
>>> b = np.array([(1.5, 2, 3), (4, 5, 6)], dtype = float)
>>> c = np.array([[1.5, 2, 3], (4, 5, 6)], [(3, 2, 1), (4, 5, 6)]],
                    dtype = float)

Initial Placeholders

dtype = float)

>>> np.zeros({3,4})

```python
>>> np.ones((2,3,4),dtype=np.int16)
>>> d = np.arange(10,25,5)

>>> np.linspace(0,2,9)

Create an array of zeros
Create an array of ones
Create an array of evenly spaced values (step value)
Create an array of evenly spaced values (number of samples)
Create a constant array
Create a 2x2 identity matrix
Create an array with random values
Create an empty array

>>> e = np.full((2, 2), 7)

>>> f = np.eye(2)

```python
>>> np.random.random((2,2))
>>> np.empty((3,2))

1/0

Saving & Loading On Disk

```python
>>> np.save('my_array', a)
>>> np.savez['array.npz', a, b]
>>> np.load('my_array.npy')

Saving & Loading Text Files

```python
>>> np.loadtxt("myfile.txt")

```python
>>> np.loadtxt( myfile.txt )
>>> np.genfromtxt("my_file.csv", delimiter=',')

```python
>>> np.savetxt("myarray.txt", a, delimiter=" ")

Data Types

>>> np.int64

>>> np.float32

>>> np.complex

Signed 64-bit integer types
Standard double-precision floating point
Complex numbers represented by 128 floats
Boolean type storing TRUE and FALSE values
Python object type
Fixed-length string type
Fixed-length unicode type

```python
>>> np.string

Inspecting Your Array

>>> np.unicode

>>> np.object

```python
>>> a.shape
>>> len(a)
>>> b.ndim
>>> e.size
>>> b.dtype
>>> b.dtype.name
>>> b.austype(int)

Subsetting, Slicing, Indexing

Asking For Help

Array Mathematics

Arithmetic Operations

```python
>>> np.info(np.ndarray.dtype)

```python
>>> g = a - b
array([[-0.5,  0. ,  0. ],\
    [-3. , -3. , -3. ]])

>>> np.subtract(a,b)

array([[ 0.66666667, 1.\
[ 0.25 , 0.4\
\
```python\
array([[ 2.5,  4.,  6. ],\
    [ 5.,  7.,  9. ]])\
\
>>> b + a\
\
```python\
>>> np.pi * a * b\
>>> a * b\
array([[ 1.5,  4.,  9.],\
    [ 4.,  10.,  18.]])\
\
>>> np.add(b,a)\
\
>>> np.multiply(a,b)\
\
```python\
>>> np.exp(b)\
>>> np.sqrt(b)\
>>> np.sin(a)\
>>> np.cos(b)\
>>> np.log(a)\
>>> e.dot(f)\
array([[ 7.,  7.],\
 [ 7.,  7.]])\
\
```python\
>>> b[0:2,1]\
array([ 2.,  5.])\
\
Comparison\
\
Select the element at the 2nd index\
\
```python\
>>> b[:1]\
array([[1.5, 2., 3.]])\
\
Array-wise comparison\
\
Array-wise sum\
Array-wise minimum value\
Maximum value of an array row\
Cumulative sum of the elements\
Mean\
Median\
Correlation coefficient\
Standard deviation\
\
Select the element at row 0 column 2 (equivalent to b[1][2])\
\
Select items at index 0 and 1\
\
```python\
>>> c[1, ...]\
array([[ [ 3., 2., 1.],\
    [ 4., 5., 6.] ]])\
\
```python\
>>> a[ : :-1]\
array([3, 2, 1])\
Boolean Indexing\
\
Boolean Indexing\
>>> a[a<2]\
array([1])\
Fancy Indexing\
\
Create a view of the array with the same data\
Create a copy of the array\
Create a deep copy of the array\
\
Aggregate Functions\
\
Select items at rows 0 and 1 in column 1\
\
```python\
>>> b[ [1, 0, 1, 0], [0, 1, 2, 0]]\
array([ [4. , 2. , 6. , 1.5]])\
>>> b[ [1, 0, 1, 0]][:, [0, 1, 2, 0]]\
[[4. , 5. , 6. , 1.]]\
\
```python\
>>> a.sum()\
>>> a.min()\
>>> b.max(axis=0)\
>>> b.cumsum(axi=1)\
>>> a.mean()\
>>> b.median()\
>>> a.corrcoef()\
>>> np.bst(b)\
\
Select all items at row o (equivalent to b[0:1, :])\
\
Same as [1, :, :]\
\
```python\
array([[ 4., 5., 6., 4.],\
    [1.5, 2., 3., 1.5],\
    [4., 5., 6., 4.],\
    [1.5, 2., 3., 1.5]])\
\
Changing Array Shape\
\
Array Manipulation\
\
Adding/Removing Elements\
\
Transposing Array\
\
```python\
>>> g.reshape(3,-2)\
\
```python\
>>> i = np.transpose(b)\
>>> i.T\
\
```python\
>>> h.resize((2, 6))\
>>> np.append(h, g)\
>>> np.insert(a, 1, 5)\
>>> np.delete(a, [1])\
\
Copying Arrays\
\
Combining Arrays\
\
```python\
>>> h = a.view()\
>>> np.copy(a)\
>>> h = a.copy()\
\
Stack arrays vertically (row-wise)\
\
>>> np.c_[a,d]\
\
Sorting Arrays\
\
Permute array dimensions Permute array dimensions\
\
Stack arrays vertically (row-wise)\
Stack arrays horizontally (column-wise)\
\
Create stacked column-wise arrays\
\
```python\
>>> a.sort()\
>>> c.sort(axis=0)\
\
Create stacked column-wise arrays\
\
Split the array vertically at the 2nd index\
\
---\
\
Data Wranglin with pandas Cheat Sheet http://pandas.pyda\
\
ng\
a.org\
\
Tidy Data - A foundation for wrangling in pandas\
\
Syntax - Creating DataFrames\
\
Tidy data complements pandas's vectorized operations. pandas will automatically preserve observations as you manipulate variables. No other format works as intuitively with pandas.\
\
|  | a | b | c |\
| --- | --- | --- | --- |\
| 1 | 4 | 7 | 10 |\
| 2 | 5 | 8 | 11 |\
| 3 | 6 | 9 | 12 |\
\
df = pd.\
\
Specify va\
\
```csharp\
DataFrame(\
  {"a" : [4 ,5, 6],\
   "b" : [7, 8, 9],\
   "c" : [10, 11, 12]},\
  index = [1, 2, 3])\
````\
\
tues for each column.\
\
````python\
df = pd.DataFrame(\
    [[4, 7, 10],\
     [5, 8, 11],\
     [6, 9, 12]],\
    index=[1, 2, 3],\
    columns=['a', 'b', 'c'])\
Specify values for each row.\
\
In a tidy data set:\
\
Each observation is saved in its own row\
\
Each variable is saved in its own column\
\
Most pandas methods return a DataFrame so that another pandas method can be applied to the result. This improves readability of code.\
\
Method Chaining\
\
```python\
df = pd.DataFrame(\
    {"a" : [4 ,5, 6],\
     "b" : [7, 8, 9],\
     "c" : [10, 11, 12]},\
\
```python\
index = pd.MultiIndex.from_tuples(\
    [('d',1),('d',2),('e',2)],\
    names=['n','v']))\
Create DataFrame with a MultiIndex\
\
Reshaping Data - Change the layout of a data set\
\
df.sort_values('mpg')\
Order rows by values of a column (low to high).\
\
pd.melt(df)\
Gather columns into rows.\
\
```python\
df.rename(columns = {'y':'year'})\
Rename the columns of a DataFrame\
\
df.sort_values('mpg',ascending=False)\
Order rows by values of a column (high to low).\
\
```python\
df.reset_index()\
Reset index of DataFrame to row numbers, moving\
index to columns.\
\
```python\
df.drop(['Length','Height'], axis=1)\
Drop columns from DataFrame\
\
Subset Observations (Rows)\
\
```python\
df.drop_duplicates()\
Remove duplicate rows (only considers columns).\
\
df[df.Length > 7]\
Extract rows that meet logical criteria.\
\
df.tail(n)\
Select last n rows.\
\
df.head(n)\
Select first n rows.\
\
Subset Variables (Columns)\
\
df.sample(frac=0.5)\
Randomly select fraction of rows.\
\
df.sample(n=10)\
Randomly select n rows.\
\
df[['width','length','species']]\
Select multiple columns with specific names.\
\
df['width'] or df.width Select single column with specific name.\
\
Select columns whose name matches regular expression regex.\
\
regex (Regular Expressions) Examples\
\
Logic in Python (and pandas)\
\
| &lt; | Less than | != | Not equal to |\
| --- | --- | --- | --- |\
| &gt; | Greater than | df.column.isin(values) | Group membership |\
| == | Equals | pd.isnull(obj) | Is NaN |\
| &lt;= | Less than or equals | pd.notnull(obj) | Is not NaN |\
| &gt;= | Greater than or equals | &amp;,|,~,^,df.any(),df.all() | Logical and,or,not,xor,any,all |\
\
| regex (Regular Expressions) Examples |  |\
| --- | --- |\
| '\. ' | Matches strings containing a period '.' |\
| 'Length$' | Matches strings ending with word 'Length' |\
| '^Sepal' | Matches strings beginning with the word 'Sepal' |\
| '^x[1-5]$' | Matches strings beginning with 'x' and ending with 1,2,3,4,5 |\
| '^(?!Species$).*' | Matches strings except the string 'Species' |\
\
df.loc[[:,'x2':'x4']]\
Select all columns between x2 and x4 (inclusive).\
\
df.iloc[:,[1,2,5]]\
Select columns in positions 1, 2 and 5 (first column is 0).\
\
(8,1,,,,,44,,,1,0,1)1,\
\
:\mathfrak{l}:,\mathfrak{[1,2,5]}\
\
[\mathsf{a f}[\ \ {^{\prime}}\ {\mathfrak{a}}^{\prime}]\geq10,[\ {{^{\prime}}\ \mathfrak{a}}^{\prime},\ {{^{\prime}}\ \mathfrak{c}}^{\prime}]]\
\
Select rows meeting logical condition, and only the specific columns . . .\
lent/loo@2015.10.32/dwarfella sheetcheck Written by Iv Luntig. Precinct彦 Consultants\
\
---\
\
```python\
df['w'].value_counts()\
\
Count number of rows with each unique value of variable len(df)\
\
# of rows in DataFrame.\
\
```python\
df['w'].nunique()\
# of distinct values in a column.\
\
df.describe()\
\
Basic descriptive statistics for each column (or GroupBy)\
\
pandas provides a large set of summary functions that operate on different kinds of pandas objects (DataFrame columns, Series, GroupBy, Expanding and Rolling (see below)) and produce single values for each of the groups. When applied to a DataFrame, the result is returned as a pandas Series for each column. Examples:\
\
sum()\
\
Sum values of each object.\
**count()**\
Count non-NA/null values of each object.\
\
median()\
Median value of each object.\
quantile([0.25,0.75])\
Quantiles of each object.\
\
apply(function)\
Apply function to each object.\
\
min()\
Minimum value in each object.\
\
```max()\
Maximum value in each object.\
mean()\
\
mean() Mean value of each object.\
\
var()\
Variance of each object.\
\
std() Standard deviation of each object.\
\
Group Data\
\
df.groupby(by="col")\
Return a GroupBy object,\
grouped by values in column\
named "col".\
\
```python\
df.groupby(level="ind")\
Return a GroupBy object,\
grouped by values in index\
level named "ind".\
\
agg(function)\
Aggregate group using function.\
\
Handling Missing Data\
\
df.dropna()\
\
All of the summary functions listed above can be applied to a group. Additional GroupBy functions:\
\
Drop rows with any column having NA/null data.\
\
df.fillna(value)\
Replace all NA/null data with value.\
\
Make New Columns\
\
pandas provides a large set of vector functions that operate on all columns of a DataFrame or a single selected column (a pandas Series). These functions produce vectors of values for each of the columns, or a single Series for the individual Series. Examples:\
\
max(axis=1)\
Element-wise max.\
\
min(axis=1)\
Element-wise min.\
\
```python\
df.assign(Area=lambda df: df.Length*df.Height\
    Compute and append one or more new columns.\
df['Volume'] = df.Length*df.Height*df.Depth\
    Add single column.\
pd.qcut(df.col, n, labels=False)\
    Bin column into n buckets.\
\
Combine Data Sets\
\
The examples below can also be applied to groups. In this case, the function is applied on a per-group basis, and the returned vectors are of the length of the original DataFrame.\
\
shift(1)\
Copy with values shifted by 1.\
\
rank(method='dense')\
Ranks with no gaps.\
\
rank(method='min')\
Ranks. Ties get min rank.\
\
rank(pct=True)\
Ranks rescaled to interval [0, 1].\
\
```python\
shift(-1)\
Copy with values lagged by 1.\
cumsum()\
Cumulative sum.\
\
cummax()\
Cumulative max.\
\
rank(method='first')\
Ranks. Ties go to first value.\
\
cumprod()\
Cumulative product.\
\
Plotting\
\
df.plot.scatter(x='w',y='h')\
Scatter chart using pairs of points\
\
Windows\
\
Standard Joins\
\
```python\
pd.merge(adf, bdf,\
        how='left', on='x1')\
Join matching rows from bdf to adf.\
\
df.rolling(n)\
\
```python\
pd.merge(adf, bdf,\
how='right', on='x1')\
Join matching rows from adf to bdf.\
\
```python\
pd.merge(adf, bdf,\
        how='inner', on='x1')\
Join data. Retain only rows in both sets.\
\
```python\
pd.merge(adf, bdf,\
          how='outer', on='x1')\
Join data. Retain all values, all rows.\
\
Filtering Joins\
\
Return a Rolling object allowing summary functions to be applied to windows of length n.\
\
adf[adf.x1.isin(bdf.x1)]\
All rows in adf that have a match in bdf.\
\
```python\
adf[~adf.x1.isin(bdf.x1)]\
All rows in adf that do not have a match in bdf.\
\
df.expanding()\
\
Return an Expanding object allowing summary functions to be applied cumulatively.\
\
pd.merge(ydf, zdf)\
Rows that appear in both ydf and zdf (Intersection).\
\
```python\
pd.merge(ydf, zdf, how='outer')\
Rows that appear in either or both ydf and zdf\
(Union).\
\
C 3\
\
pd.merge(ydf, zdf, how='outer',\
    indicator=True)\
\
```javascript\
.query('_merge == "left_only"')\
\
```python\
.drop(['_merge'],axis=1)\
Rows that appear in ydf but not zdf (Setdiff).\
\
---\
\
Data Wrangling with dplyr and tidyr Cheat Sheet\
\
Studio\
\
Tidy Data - A foundation for wrangling in R\
\
dplyr::tbl_df(iris)\
\
Converts data to tbl class. tbl's are easier to examine than data frames. R displays only the data that fits onscreen:\
\
Tidy data complements R's vectorized operations. R will automatically preserve observations as you manipulate variables. No other format works as intuitively with R.\
\
Source: local data frame [150 x 5]\
\
Sepal.Length Sep\
1 5.1\
2 4.9\
3 4.7\
4 4.6\
5 5.0\
\
l.Width Petal.Length\
3.5 1.4\
3.0 1.4\
3.2 1.3\
3.1 1.5\
3.6 1.4\
\
Variables not shown: Petal.Width (dbl),\
Species (fctr)\
\
dplyr::glimpse(iris)\
\
Each observation is saved in its own row\
\
Information dense summary of tbl data.\
\
dplyr::data_frame(a = 1:3, b = 4:6)\
\
utils::View(iris)\
\
View data set in spreadsheet-like display (note capital V).\
\
Reshaping Data - Change the layout of a data set\
\
Combine vectors into data frame (optimized).\
\
x %>% f(y) *is the same as* f(x, y)\
y %>% f(x, ., z) *is the same as* f(x, y, z )\
\
Passes object on left hand side as first argument (or argument) of function on righthand side.\
\
|  | Sepal.Length | Sepal.Width | Petal.Length | Petal.Width | Species |\
| --- | --- | --- | --- | --- | --- |\
| 1 | 5.1 | 3.5 | 1.4 | 0.2 | setosa |\
| 2 | 4.9 | 3.0 | 1.4 | 0.2 | setosa |\
| 3 | 4.7 | 3.2 | 1.3 | 0.2 | setosa |\
| 4 | 4.6 | 3.1 | 1.5 | 0.2 | setosa |\
| 5 | 5.0 | 3.6 | 1.4 | 0.2 | setosa |\
| 6 | 5.4 | 3.8 | 1.7 | 0.4 | setosa |\
| 7 | 4.6 | 3.4 | 1.4 | 0.3 | setosa |\
| 8 | 5.0 | 3.4 | 1.5 | 0.2 | setosa |\
\
```python\
iris %>%\
  group_by(Species) %>%\
  summarise(avg = mean(Sepal.Width)) %>%\
  arrange(avg)\
\
tidyr::spread(pollution, size, amount)\
\
Order rows by values of a column (low to high).\
\
dplyr::%>%\
\
dplyr::arrange(mtcars, desc(mpg))\
Order rows by values of a column\
(high to low).\
\
Gather columns into rows.\
\
tidyr:unite(data, col, ..., sep)\
Unite several columns into one.\
\
dplyr::filter(iris, Sepal.Length > 7)\
\
dplyr::distinct(iris)\
\
Extract rows that meet logical criteria.\
\
Remove duplicate rows.\
\
Subset Variables (Columns)\
\
dplyr::sample_frac(iris, 0.5, replace = TRUE) Randomly select fraction of rows.\
\
dplyr::select(iris, Sepal.Width, Petal.Length, Species) Select columns by name or helper function.\
\
dplyr::sample_n(iris, 10, replace = TRUE)\
Randomly select n rows.\
\
Select columns whose name contains a character string.\
\
Helper functions for select - ?select\
\
Select and order top n entries (by group if grouped data).\
\
dplyr::top_n(storms, 2, date)\
\
dplyr::slice(iris, 10:15) Select rows by position.\
\
```sql\
select(iris, ends_with("Length"))\
Select columns whose name ends with a character string,\
\
select(iris, everything())\
Select every column.\
\
select(iris, matches("t.") )\
\
Logic in R - ?Comparison, ?base::Logic\
\
Select columns whose name matches a regular expression.\
\
```sql\
select(iris, num_range("x", 1:5))\
Select columns named x1, x2, x3, x4, x5.\
\
|  | Logic in R - ?Comparison, ?base::Logic |  |  |\
| --- | --- | --- | --- |\
| &lt; | Less than | != | Not equal to |\
| &gt; | Greater than | %in% | Group membership |\
| = | Equal to | is.na | Is NA |\
| &lt;= | Less than or equal to | !is.na | Is not NA |\
| &gt;= | Greater than or equal to | &amp;,|,!,xor,any,all | Boolean operators |\
\
```sql\
select(iris, starts_with("Sepal"))\
Select columns whose name starts with a character string.\
\
Select columns whose name starts with a character string.\
\
```sql\
select(iris, Sepal.Length,Petal.Width)\
Select all columns between Sepal.Length and Petal.Width (inclusive).\
````\
\
````sql\
select(iris, -Species)\
Select all columns except Species.\
\
Select all columns except Species.\
\
---\
\
Summarise Data\
\
dplyr::summarise(iris, avg = mean(Sepal.Length))\
\
Summarise data into single row of values.\
\
Apply summary function to each column.\
\
dplyr::summarise_each(iris, funs(mean))\
\
dplyr::count(iris, Species, wt = Sepal.Length)\
\
Count number of rows with each unique value of variable (with or without weights).\
\
Summarise uses summary functions, functions that take a vector of values and return a single value, such as:\
\
dplyr::first\
First value of a vector.\
\
dplyr::last Last value of a vector.\
\
dplyr::nth\
\
Nth value of a vector.\
\
dplyr::n\
# of values in a vector.\
\
dplyr::n_distinct\
\
# of distinct values in a vector.\
\
IQR of a vector.\
\
min\
\
Minimum value in a vector.\
\
max\
\
IQR\
\
Maximum value in a vector.\
\
mean\
\
Mean value of a vector.\
\
median Median value of a vector.\
\
var Variance of a vector.\
\
Group Data\
\
Standard deviation of a vector.\
\
sd\
\
dplyr::group_by(iris, Species)\
\
Group data into rows with the same value of Species.\
\
dplyr::ungroup(iris)\
\
Remove grouping information from data frame.\
\
iris %>% group_by(Species) %>% summarise(...)\
Compute separate summary row for each group.\
\
Make New Variables\
\
Compute and append one or more new columns.\
\
dplyr::mutate(iris, sepal = Sepal.Length + Sepal.Width)\
\
dplyr::mutate_each(iris, funs(min_rank))\
\
dplyr::transmute(iris, sepal = Sepal.Length + Sepal.Width) Compute one or more new columns. Drop original columns.\
\
Copy with values shifted by 1.\
\
Apply window function to each column.\
\
dplyr::lag\
\
Copy with values lagged by 1.\
\
dplyr::dense_rank Ranks with no gaps.\
\
Mutate uses window functions,functions that take a vector of values and return another vector of values,such as:\
\
dplyr::lead\
\
dplyr::min_rank\
Ranks. Ties get min rank.\
\
dplyr::percent_rank Ranks rescaled to [0, 1].\
\
window function\
\
dplyr::row_number\
Ranks. Ties got to first value.\
\
dplyr::ntile Bin vector into n buckets.\
\
Cumulative distribution.\
\
dplyr::between\
\
Are values between a and b?\
\
cumsum\
\
dplyr:cume_dist\
\
dplyr::cumall\
\
cummax\
\
Cumulative sum\
\
Cumulative max\
\
dplyr: cummean Cumulative mean\
\
cummin\
\
cumprod\
\
dplyr::cumany\
\
Cumulative min\
\
pmax\
\
pmin\
\
Mutating Joins\
\
```python\
dplyr::left_join(a, b, by = "x1")\
Join matching rows from b to a.\
\
iris %>% group_by(Species) %>% mutate(...)\
\
dplyr::right_join(a, b, by = "x1")\
Join matching rows from a to b.\
\
```python\
dplyr.inner_join(a, b, by = "x1")\
Join data. Retain only rows in both sets.\
\
```python\
dplyr::full_join(a, b, by = "x1")\
Join data. Retain all values, all rows.\
\
dplyr::semi_join(a, b, by = "x1")\
\
Filtering Joins\
\
dplyr::anti_join(a, b, by = "x1")\
\
All rows in a that have a match in b.\
\
Compute new variables by group.\
\
All rows in a that do not have a match in b.\
\
Set Operations\
\
dplyr::intersect(y, z)\
\
Rows that appear in both y and z.\
\
dplyr::union(y, z)\
Rows that appear in either or both y and z.\
\
dplyr::setdiff(y, z)\
Rows that appear in y but not z.\
\
Binding\
\
dplyr::bind_rows(y, z)\
Append z to y as new rows.\
\
dplyr::bind_cols(y,z)\
\
Append z to y as new columns.\
Caution: matches rows by position.\
\
---\
\
Python For Data Science Cheat Sheet\
\
SciPy - Linear Algebra\
\
Learn More Python for Data Science Interactively at www.datacamp.com\
\
SciPy\
\
SciPy\
\
The SciPy library is one of the core packages for scientific computing that provides mathematical algorithms and convenience functions built on the NumPy extension of Python.\
\
Interacting With NumPy\
\
Also see NumPy\
\
Index Tricks\
\
```python\
>>> import numpy as np\
>>> a = np.array([1,2,3])\
>>> b = np.array([[1+5j,2j,3j], (4j,5j,6j)])\
>>> c = np.array([[1,5,2,3], (4,5,6]], [(3,2,1), (4,5,6)])\
\
Create a dense meshgrid\
Create an open meshgrid\
stack arrays vertically (row-wise)\
Create stacked column-wise arrays\
\
Shape Manipulation\
\
```python\
>>> np.transpose(b)\
>>> b.hatten()\
>>> np.hstack((b,c))\
>>> np.vstack((a,b))\
>>> np.hsplit(c,2)\
>>> np.vsplit(d,2)\
\
Permute array dimensions\
Flatten the array\
Stack arrays horizontally (column-wise)\
Stack arrays vertically (row-wise)\
Split the array horizontally at the 2nd index\
Split the array vertically at the 2nd index\
\
Polynomials\
\
```python\
>>> from numpy import poly1d\
>>> p = poly1d([3,4,5])\
\
Vectorizing Functions\
\
```python\
>>> def myfunc(a):\
    if a < 0:\
        return a*2\
    else:\
        return a/2\
\
```python\
>>> np.vectorize(myfunc)\
\
Vectorize functions\
\
Other Useful Functions\
\
Return the real part of the array elements\
Return the imaginary part of the array elements\
Return a real array if complex parts close to o\
Cast object to a data type\
\
```python\
>>> np.real(b)\
>>> np.imag(b)\
>>> np.real_if_close(c,tol=1000)\
>>> np.cast['f'](np.pi)\
\
You'll use the linalg and sparse modules. Note that scipy.linalg contains and expands on numpy.linalg.\
\
Return the angle of the complex argument\
Create an array of evenly spaced values\
[number of samples]\
\
Unwrap\
\
Create an array of evenly spaced values (dig scale)\
Return values from a list of arrays depending on conditions\
Factorial\
\
```python\
>>> np.logspace(0,10,3)\
>>> np.select([c<4],[c*2])\
\
```python\
>>> misc.central_diff_weights(3)\
>>> misc.derivative(myfunc,1.0)\
\
Creating Matrices\
\
>>> from scipy import linalg, sparse\
\
```python\
>>> A = np.matrix(np.random.random((2,2)))\
>>> B = np.asmatrix(b)\
>>> C = np.mat(np.random.random((10,5))\
>>> D = np.mat([[3,4], [5,6]])\
\
Basic Matrix Routines\
\
Inverse\
\
```python\
inverse\
>>> A.I\
>>> linalg.inv(A)\
\
Transposition\
\
Inverse Inverse\
\
>>> A.T\
>>> A.H\
\
```python\
>>> linalg.norm(A)\
>>> linalg.norm(A,1)\
>>> linalg.norm(A,np.inf)\
\
Trace\
\
>>> np.trace(A)\
\
Tranpose matrix Conjugate transposition\
\
Rank\
\
```python\
>>> np.linalg.matrix_rank(C)\
2\
\
Solving linear problems\
\
```python\
>>> linalg.solve(A,b)\
>>> E = np.mat(a).T\
>>> linalg.lstsq(F,E)\
\
>>> linalg.pinv2(C)\
\
Generalized inverse\
\
Matrix rank\
\
Compute the pseudo-inverse of a matrix (least-squares solver)\
Compute the pseudo-inverse of a matrix (SVD)\
\
>>> np.subtract(A,D)\
\
Matrix Functions\
\
Creating Sparse Matrices\
\
>>> np.add(A,D)\
\
DIVISION\
>>> np.divide(A,D)\
\
Exponential Functions\
\
Creating Sparse Matrices\
\
```python\
>>> F = np.eye(3, k=1)\
>>> G = np.mat(np.identity(2))\
>>> C[C > 0.5] = 0\
>>> H = sparse.csr_matrix(C)\
>>> I = sparse.csc_matrix(D)\
>>> J = sparse.dok_matrix(E)\
>>> E.todense()\
>>> sparse.isspmat_matrix_csc(A)\
\
Logarithm Function\
>>> linalg.logm(A)\
\
>>> sparse.linalg.norm(I)\
\
```python\
>>> np.multiply(D,A)\
>>> np.dot(A,D)\
>>> np.vdot(A,D)\
>>> np.inner(A,D)\
>>> np.outer(A,D)\
>>> np.tensordot(A,D)\
>>> np.kron(A,D)\
\
Trigonometric Functions\
\
```python\
>>> sparse.linalg.inv(I)\
Norm\
\
Hyperbolic Trigonometric Functions\
\
Multiplication\
>>> A @ D\
\
```python\
>>> linalg.expm(A)\
>>> linalg.expm2(A)\
>>> linalg.expm3(D)\
\
Solving linear problems\
\
Inverse\
\
```python\
>>> linalg.sinm(D)\
>>> linalg.cosm(D)\
>>> linalg.tanm(A)\
\
```python\
hyperbolic trigonometry\
>>> linalg.sinh(M)\
>>> linalg.cosh(M)\
>>> linalg.tanh(A)\
````\
\
**Material Science Function**\
\
> > > sparse.linalg.spsolve(H, I)\
\
Matrix Sign Function\
\
> > > np.signm(A)\
\
Arbitrary Functions\
\
> > > linalg.funm(A, lambda x: x\*x)\
\
> > > sparse.linalg.expm(I)\
\
Decompositions\
\
Sparse Matrix Functions\
\
Asking For Help\
\
Eigenvalues and Eigenvectors >>> la, v = linalg.eig(A)\
\
Solve ordinary or general eigenvalue problem for s\
Unpack eigenvalues\
First eigenvector\
Second eigenvector\
Unpack eigenvalues\
\
ized square matrix\
\
````python\
>>> 11, 12 = 1a\
>>> v[:,0]\
>>> v[:,1]\
>>> linalg.eigvals(A)\
\
Singular Value Decomposition\
\
Singular Value Decomposition (SVD)\
\
```python\
>>> help(scipy.linalg.diagsvd)\
>>> np.info(np.matrix)\
\
Construct sigma matrix in SVD\
\
>>> P,L,U = linalg.lu(C)\
\
Sparse Matrix Decompositions\
\
```python\
>>> la, v = sparse.linalg.eigs(F,1)\
>>> sparse.linalg.svds(H, 2)\
\
Learn Python for Data Science Interactively\
\
Learn Python Interactively at www.DataCamp.com\
\
All plotting is done with respect to an Axes. In most cases, a subplot will fit your needs. A subplot is an axes on a grid system.\
\
Matplotlib is a Python 2D plotting library which produces publication-quality figures in a variety of hardcopy formats and interactive environments across platforms. matplotlib\
\
Matplotlib\
\
Prepare The Data\
\
2D Data or Images\
\
```python\
>>> data = 2 * np.random.random((10, 10))\
>>> data2 = 3 * np.random.random((10, 10))\
\
1D Data\
\
6 Show plot\
\
Figure\
\
The basic steps to creating plots with matplotlib are:\
\
Plot Anatomy & Workflow\
\
1 Prepare data\
\
```python\
>>> from matplotlib.lib.cbook import get_sample_data\
>>> img = np.load(get_sample_data('axes_grid/bivariate_normal.npy'))\
\
Axes/Subplot\
\
Plot Anatomy\
\
```python\
>>> fig = plt.figure()\
\
```python\
>>> import matplotlib.pyplot as plt\
\
```python\
>>> fig, ax = plt.subplots()\
>>> lines = ax.plot(x, y)\
>>> ax.scatter(x,y)\
>>> axes[0,0].bar([1,2,3], [3,4,5])\
>>> axes[1,0].barch([1,2,3], [0,1,2])\
>>> axes[1,1].line([0.45])\
>>> axes[1,1].axvline(0.65)\
>>> ax.fill(x,y,color='blue')\
>>> ax.fill_between(x,y,color='yellow')\
\
```python\
>>> ax = ng.add_subplot(111)\
>>> ax.plot(x, y, color='lightblue', linewidth=3)  Step 3.4\
>>> ax.scatter([2,4,6],\
\
Colors, Color Bars & Color Maps\
\
```python\
>>> U = -1 - X**2 + Y\
>>> V = 1 + X - Y**2\
\
```python\
>>> plt.plot(x, x, x**2, x, x**3)\
>>> ax.plot(x, y, alpha = 0.4)\
>>> ax.plot(x, y, c='k')\
>>> fig.colorbar(im, orientation='horizontal')\
>>> im = ax.imshow(img,\
                      cmap='neismic')\
\
```python\
>>> plt.plot(x,y,ls='solid')\
>>> plt.plot(x,y,'--')\
>>> plt.plot(x,y,'-',x**2,y**2,-.')\
>>> plt.setp(lines,color='r',linewidth=4.0)\
\
```python\
>>> ax.set_xlim(1, 6.5)\
>>> plt.savefig('foo.png')\
>>> plt.show()\
\
Text & Annotations\
\
Add an arrow to the axes Plot a 2D field of arrows Plot a 2D field of arrows\
\
```python\
>>> axes[0,1].arrow(0,0,0.5,0.5)\
>>> axes[1,1].quiver(y,z)\
>>> axes[0,1].streamplot(X,Y,U,V)\
\
Data Distributions\
\
Limits, Legends & Layout Limits & Autoscaling\
\
```python\
>>> ax.set(title='An Example Axes',\
    ylabel='Y-Axis',\
    xlabel='X-Axis')\
>>> ax.legend(loc='best')\
\
```python\
>>> ax.xaxis.set[ticks=range(1,5),\
>>> ticklabel={3,100,-12,"foo"})\
>>> ax.tick_params(dxmax=9,\
>>> direction='inout',\
>>> length=10)\
\
```python\
>>> fig, ax = plt.subplots()\
>>> im = ax.imshow(img,\
\
5 Save Plot\
\
```python\
Save figures\
>>> plt.savefig('foo.png')\
Save transparent figures\
>>> plt.savefig('foo.png', transparent=True)\
\
Show Plot\
\
Close & Clear\
\
Clear an axis Clear the entire figure Close a window\
\
DataCamp Learn Python for Data Science interactively\
\
---\
\
Data Visualization with ggplot2 Cheat Sheet\
\
Studio\
\
Basics\
\
ggplot2 is based on the grammar of graphics, the idea that you can build every graph from the same few components: a data set, a set of geom$ - visual marks that represent data points, and a coordinate system\
\
system.\
\
geom\
x=F\
y=A\
\
coordinate system\
\
plot\
\
To display data values, map variables in the data set to aesthetic properties of the geom like **size**, **color**, and **x** and **y** locations.\
\
data\
\
coordinate system\
\
plot\
\
Build a graph with qplot() or ggplot()\
\
aesthetic mappings\
\
```python\
qplot(x = cty, y = hwy, color = cyl, data = mpg, geom = "point")\
Creates a complete plot with given data, geom, and mappings. Supplies many useful defaults.\
\
ggplot(data = mpg, aes(x = cty, y = hwy))\
\
Begins a plot that you finish by adding layers to. No defaults, but provides more control than qplot().\
\
add layers elements with+\
\
```python\
ggplot(mpg, aes(hwy, cty)) +\
geom_point(aes(color = cyl))\
geom_smooth(method = "lm") +\
coord_cartesian() +\
scale_color_gradient() +\
theme_bw()\
\
layer = geom + default stat + layer specific mappings\
\
additional elements\
\
Add a new layer to a plot with a `geom_*()` or `stat_*()` function. Each provides a geom, a set of aesthetic mappings, and a default stat and position adjustment.\
\
Returns the last plot\
\
last_plot()\
\
ggsave("plot.png", width = 5, height = 5)\
\
Saves last plot as 5' x 5' file named "plot.png" in working directory. Matches file type to file extension.\
\
One Variable Continuous\
\
a <- ggplot(mpg, aes(hwy))\
\
a + geom_area(stat = "bin")\
\
```r\
+ geom_density(kernel = "gaussian")\
x, y, alpha, color, fill, linetype, size, weight\
b + geom_density(ya=县,count.)}\
\
x, y, alpha, color, fill, linetype, size\
\
b + geom_area(aes(y = ..density..), stat = "bin")\
\
a + geom_dotplot()\
\
x,y,alpha,color,fill\
\
a + geom_freqpoly()\
\
x, y, alpha, color, linetype, size\
b + geom_freqpoly(aes(y = ..density..))\
\
a + geom_histogram(binwidth = 5)\
\
x, y, alpha, color, fill, linetype, size, weight\
b + geom_histogram(aes(y = ..density...))\
\
b<- ggplot(mpg, aes(fl))\
\
x, alpha, color, fill, linetype, size, weight\
\
b + geom_bar()\
\
Graphical Primitives\
\
c<- ggplot(map, aes(long, lat))\
\
c + **geom_polygon**(aes(group = group))\
x, y, alpha, color, fill, linetype, size\
\
d <- ggplot(economics, aes(date, unemploy))\
\
Two Variables\
\
```python\
d + geom_path(lineend="butt",\
linejoin="round", linemitre=1)\
x, y, alpha, color, linetype, size\
\
```r\
d + geom_ribbon(aes(ymin=unemploy - 900,\
ymax=unemploy + 900))\
x, ymax, ymin, alpha, color, fill, linetype, size\
\
e <- ggplot(seals, aes(x = long, y = lat))\
\
```matlab\
xend = long + delta_long,\
yend = lat + delta_lat)\
x, xend, y, yend, alpha, color, linetype, size\
\
e + geom_segment(aes{\
\
```python\
+ geom_rect((aes(xmin = long, ymin = lat,\
xmax = long + delta_long,\
ymax = lat + delta_lat))\
xmax, xmin, ymax, ymin, alpha, color, fill,\
linetype, size)\
\
f + geom_jitter()\
\
x,y,alpha,color,fill,shape,size\
\
```python\
i + geom_bin2d(binwidth = c(5, 0.5))\
xmax, xmin, ymax, ymin, alpha, color, fill,\
linetype, size, weight\
\
geom_quantile()\
\
Continuous Bivariate Distribution i<- ggplot(movies, aes(year, rating))\
\
i+ geom_density2d()\
\
f + **geom_rug**(sides = "bl")\
alpha, color, linetype, size\
\
i + geom_hex()\
\
x,y, alpha, colour, linetype, size\
\
```python\
f + geom_smooth(model = lm)\
x, y, alpha, color, fill, linetype, size, weight\
\
x,y,alpha,colour,fill size\
\
+ **geom_text**(*aes*(label = *cty*))\
x, y, label, alpha, angle, color, family, fontface,\
hijust, lineheight, size, vjust\
\
j <- ggplot(economics, aes(date, unemploy))\
\
j + geom_area()\
\
geom_bar(stat = identity )\
x, y, alpha, color, fill, linetype, size, weight\
\
g + geom_bar(stat = "identity")\
\
```matlab\
g + geom_violin(scale = "area")\
x, y, alpha, color, fill, linetype, size, weight\
\
lower, middle, upper, x,ymax, ymin, alpha color, fill, linetype, shape, size, weight\
\
stackdir = "center")\
x, y, alpha, color, fill\
\
g + geom_boxplot()\
\
Visualizing error\
\
```python\
df <- data.frame(grp = c("A", "B"), fit = 4:5, se = 1:2)\
k <- ggplot(df, aes(grp, fit, ymin = fit-se, ymax = fit+se))\
\
h + geom_jitter()\
\
k + geom_crossbar(fatten = 2)\
x, y, ymax, ymin, alpha, color, fill, linetype,\
size\
\
```python\
k + geom_errorbar()\
x, ymax, ymin, alpha, color, linetype, size,\
width (also geom_errorbarh())\
\
k + geom_pointrange()\
\
x, y, ymin, ymax, alpha, color, fill, linetype shape, size\
\
Maps\
\
```python\
k + geom_linerange()\
x, ymin, ymax, alpha, color, linetype, size\
\
```python\
data <- data.frame(murder = USArrestsMurder,\
    state = tolower(rownames(USArrests)))\
map <- map_data("state")\
l <- ggplot(data, aes(fill = murder))\
\
x,y,z,alpha,colour,linetype,size,weight\
\
m + geom_contour(aes(z = z))\
\
+ **geom_map**(*aes(map_id = state)*, map = map) +\
**expand_limits**(*x = mapSlong*, y = mapStar)\
map_id, alpha, color, fill, linetype, size\
\
Three Variables\
\
```r\
seals$z <- with(seals, sqrt(delta_long^2 + delta_lat^2))\
m <- ggplot(seals, aes(long, lat))\
\
m + geom_raster(aes(fill = z), hjust=0.5,\
\
```matlab\
m + **geom_tile**(aes(fill = z))\
x, y, alpha, color, fill, linetype, size\
\
---\
\
Stats - An alternative way to build a layer\
\
Some plots visualize a transformation of the original data set. Use a **stat** to choose a common transformation to visualize, e.g. a **geom_bar**(state = "bin")\
\
data\
\
stat\
\
coordinate system\
\
plot\
\
Each stat creates additional variables to map aesthetics to. These variables use a common ..name.. syntax.\
\
stat functions and geom functions both combine a stat with a geom to make a layer, i.e. `stat_bin(geom="bar")` does the same as `geom_bar(stat="bin")`\
\
stat function\
\
variable created by transformation\
\
```python\
i+ stat_density2d(aes(fill = ..level..),\
geom = "polygon", n = 100)\
\
geom for layer parameters for stat\
\
a + stat_bin(binwidth = 1, origin = 10)\
\
a + stat_bindot(binwidth = 1, binaxis = "x")\
\
a + **stat_density**(adjust = 1, kernel = "gaussian")\
x, y, | ...count..., ...density..., ...scaled..\
\
f + stat_binhex(bins = 30)\
\
x, y, fill | ..count..., ..density..\
\
3 Variables\
\
x,y,z,order | ...level..\
\
m+ stat_spoke(aes{radius=z, angle = z})\
\
angle, radius, x, xend, y, yend | ...x..., ...xend..., ...y..., ...yend...\
\
```r\
m + stat_summary_hex(aes(z = z), bins = 30, fun = mean)\
x, y, z, fill | ..value..\
\
```r\
m + stat_summary2d(aes(z = z), bins = 30, fun = mean)\
x, y, z, fill | ..value..\
\
g + stat_boxplot(coef = 1.5)\
\
```r\
x | y | lower, _middle, _upper, _outliers\
\
g = stat_y_density(adjust = 1, kernel = "gaussian", scale = "area")\
\
x | density, _scaled, _count, _nolinwidth, _width\
\
Functions\
\
f + stat_ecdf(n = 40)\
\
```r\
f + stat_quantile(cquantiles = c(0.25, 0.5, 0.75), formula = y ~ log(x),\
method = "qr")\
x, v | stat_quantile ... x... v.\
\
```r\
f = stat_smooth(method = "auto", formula = y ~ x, se = TRUE, n = 80,\
fullrange = FALSE, level = 0.95)\
x, y | -se., -x., -y., -ymin., -ymax.\
\
fun = dnorm, n = 101, args = list(sd=0.5))\
x | y\
\
ggplot() + stat_function(aes(x = -3:3),\
\
[+ stat_identity()]\
\
```python\
ggplot() = stat_qq(aes(sample=1:100), distribution = qt,\
dparams = list(df=5))\
sample, x, y | ...x,...y.\
\
```java\
f + stat_sum()\
\
f + stat_summary(fun.data = "mean_cl_boot")\
\
Scales\
\
n<-b+geom_bar(aes(fill = fl))\
\
scale_\
\
n+scale_fill_manual{\
\
```python\
values = c("skyblue", "royalblue", "blue", "navy")\
limits = c(d="e", "p","r"), breaks = c("d", "e", "p", "r"),\
name = "fuel", labels = c("D", "E", "P", "R"))\
\
title to use in legend/axis\
\
range of values to include in mapping\
\
General Purpose scales Use with any aesthetic alpha, color, fill, linetype, shape, size\
\
scale_*_continuous() - map cont' values to visual values\
\
scale_*_discrete() - map discrete values to visual values\
\
**scale_*_identity() - use data values as visual values**\
\
```scala\
scale_*_manual(values = c()) - map discrete values to manually chosen visual values\
\
X and Y location scales\
\
Use with x or y aesthetics (x shown here)\
\
```r\
scale_x_date(labels = date_format("6m/%d"),\
  breaks = date_breaks("2 weeks")) - treat x\
values as dates. See ?stprintme for label formats.\
\
```python\
scale_x_datetime() - treat x values as date times. Use\
same arguments as scale_x_date().\
\
scale_x_log10() - Plot x on log10 scale\
\
scale_x_reverse() - Reverse direction of x axis\
\
scale_x_sqrt() - Plot x on square root scale\
\
Color and fill scales\
\
Discrete\
\
```r\
n <- b + geom_bar(\
  aes(fill = fl))\
\
+ scale_fill_brewer(\
  palette = "Blues")\
For palette choices:\
  library(RcolorBrewer)\
  display.brewer.all()\
\
```python\
+ scale_fill_grey(\
start = 0.2, end = 0.8,\
na.value = "red")\
\
```python\
o + scale_fill_gradient{\
  low = "red",\
  high = "yellow")\
\
```python\
o <- a + geom_dotplot(\
    aes(fill = ..x.))\
\
```python\
o + scale_fill_gradientn{\
\
Coordinate Systems\
\
Shape scales\
\
r<-b+geom_bar()\
\
```python\
p <- f + geom_point(\
    aes(shape = fl))\
\
0 □ 6 ♦\
1 ○ 7 ♦\
2 △ 8 ✕\
3 — 9 ♦\
4 × 10 ♦\
5 ♦ 11 ♦\
\
12 ♦ 18 ♦ 24 ♦\
13 ♦ 19 ♦ 25 ♦\
14 ♦ 20 ♦ • ★ •\
15 ♦ 21 ★ •\
16 ♦ 22 ○ 0\
17 ♦ 23 ◇ O\
\
The default cartesian coordinate system\
\
r + coord_fixed(ratio = 1/2)\
\
scale_shape_manual(\
values = c(3:7))\
Shape values shown in\
chart on right\
\
Size scales\
\
q<-f+geom_point(\
aes(size = cyl))\
\
+ `scale_size_area(max = 6)`\
Value mapped to area of circle\
(not radius)\
\
ratio, xlim, ylim\
\
Facets divide a plot into subplots based on the values of one or more discrete variables.\
\
Cartesian coordinates with fixed aspect ratio between x and y units\
\
r + coord_flip()\
\
+ **coord_polar**(theta = "x", direction=1)\
\
t + facet_grid(, ~ fl)\
facet into columns based on fl\
\
t+ facet_grid(year ~ .)\
facet into rows based on year\
\
r + coord_trans(ytrans = "sqrt")\
\
t+ facet_grid(year ~ fl)\
facet into both rows and columns\
\
t + facet_wrap(~ fl)\
wrap facets into a rectangular layout\
\
```python\
p + scale_shape(\
    solid = FALSE)\
\
p + scale_shape_manual{\
\
z + coord_map(projection = "ortho",\
\
fl:r\
\
xtrans, ytrans, limx, limy\
Transformed cartesian coordinates. Set extras and strains to the name of a window function.\
\
- "free_x" - x axis limits adjust\
\
t + facet_grid(y ~ x, scales = "free")\
x and y axis limits adjust to individual facet\
\
Set scales to let axis limits vary across facets\
\
orientation=c(41,-74,0))\
\
Map projections from the mapproj package (mercator (default), azequalarea, lagrange, etc.)\
\
projection, orientation,xlim,ylim\
\
- "free_y" - y axis limits adjust\
\
11. labeller = label_both)\
\
Set labeller to adjust facet labels\
\
t + facet_grid[, ~ fl, labeller = label_bquote(alpha ^ .(x))]\
$\alpha^e$ $\alpha^d$ $\alpha^e$ $\alpha^p$ $\alpha^r$\
\
Position Adjustments\
\
Position adjustments determine how to arrange geoms that would otherwise occupy the same space.\
\
s <- ggplot(mpg, aes(fl, fill = drv))\
\
s + geom_bar(position = "dodge")\
Arrange elements side by side\
\
s + geom_bar(position = "fill")\
Stack elements on top of one another,\
normalize height\
\
s + geom_bar(position = "stack") Stack elements on top of one another\
\
Each position adjustment can be recast as a function with manual width and height arguments\
\
f + geom_point(position = "jitter")\
Add random noise to X and Y position of each element to avoid overplotting\
\
s + geom_bar(position = position_dodge(width = 1))\
\
```python\
t + labs(title = "New title", x = "New x", y = "New y")\
All of the above\
\
t + xlab("New X label") Change the label on the X axis\
\
t + **theme**(legend.position = "bottom")\
Place legend at "bottom", "top", "left", or "right"\
\
Legends\
\
t + **guides**(color = "none")\
Set legend type for each aesthetic: colorbar, legend,\
or none (no legend)\
\
Themes\
\
+ theme_bw()\
\
White background with grid lines\
\
theme_grey()\
\
White background no gridlines\
\
Grey background (default theme)\
\
+ theme_minimal()\
Minimal theme\
\
Zooming\
\
Without clipping (preferred)\
\
```python\
t + coord_cartesian(\
    xlim = c(0, 100), ylim = c(10, 20))\
\
With clipping (removes unseen data points)\
\
t+ scale_x_continuous(limits = c(0, 100)) +\
scale_y_continuous(limits = c(0, 100))\
\
RStudio® is a trademark of RStudio, Inc. • CC BY RV Studio • info@rstudio.com • 844-448-1212 • rstudio.com\
\
Learn more at docs.ggplot2.org • ggplot2 0.9.3.1 • Updated: 3/15\
\
---\
\
Python For Data Science Cheat Sheet PySpark Basics\
\
PySpark Basics\
\
Learn Python for data science Interactively at www.DataCamp.com\
\
Spark\
\
PySpark is the Spark Python API that exposes the Spark programming model to Python\
\
APACHE Spark\
\
Initializing Spark\
\
SparkContext\
\
Inspect SparkContext\
\
>>> sc.master\
\
```python\
>>> str(sc.sparkHome)\
>>> str(sc.sparkUser())\
\
Retrieve SparkContext version\
\
>>> sc.appName\
\
Master URL to connect to\
Path where Spark is installed on worker nodes\
Retrieve name of the Spark User running\
SparkContext\
\
Return application name\
Retrieve application ID\
\
```python\
>>> sc.applicationId\
>>> sc.defaultParallelism\
>>> sc.defaultMinPartitions\
\
Return default level of parallelism Default minimum number of partitions for RDDs\
\
```python\
>>> from pyspark import SparkConf, SparkContext\
>>> conf = (SparkConf()\
          .setMaster("local")\
          .setAppName("My app")\
          .set("spark.executor.memory", "1g"))\
>>> sc = SparkContext(conf = conf)\
\
Configuration\
\
In the PySpark shell, a special interpreter-aware SparkContext is already created in the variable called sc.\
\
```bash\
$ ./bin/spark-shell --master local[2]\
$ ./bin/pyspark --master local[4] --py-files code.py\
\
Set which master the context connects to with the --master argument, and add Python .zip, .egg or .py files to the runtime path by passing a comma-separated list to --py-files.\
\
Loading Data\
\
Parallelized Collections\
\
```python\
>>> rdd = sc.parallelize([('a',7),('a',2),('b',2)])\
>>> rdd2 = sc.parallelize([('a',2),('d',1),('b',1)])\
>>> rdd3 = sc.parallelize(range(100))\
\
```python\
>>> rdd4 = sc.parallelize([(["a", ["x", "y", "z"]),\
    ("b", ["p", "r"])])\
\
Read either one text file from HDFS, a local file system or or any Hadoop-supported file system URI with `textFile()` or read in\
\
Retrieving RDD Information\
\
```python\
>>> rdd3.sum()\
4050\
\
```python\
>>> sc.parallelize([]).isEmpty()\
\
Using The Shell\
\
External Data\
\
Reshaping Data\
\
Maximum value of RDD elements\
\
Summary\
\
```python\
>>> rdd.reduce(lambda a, b: a + b)\
('a',7,'a',2,'b',2)\
\
```python\
>>> rdd.reduceByKey(lambda x,y : x+y)\
.collect()\
[(1, 2), (4, 5)]\
\
Compute variance of RDD elements\
\
Compute histogram by bins\
\
```python\
>>> rdd3.max()\
\
```python\
>>> rdd3.min()\
0\
\
```python\
>> rdd3.mean()\
49.5\
\
```python\
>>> rdd3.groupBy(lambda x: x % 2)\
    .mapValues(list)\
    collect()\
\
Grouping by\
\
Summary statistics (count, mean, stdev, max & min)\
\
```python\
>>> rdd.groupByKey()\
    .mapValues(list)\
    .collect()\
[('a', [7, 2]], ('b', [2])]\
\
```python\
>>> rdd.aggregateByKey((0,0),seqop,combop)\
.collect()\
\
```python\
>>> seqOp = (lambda x, y: [x(0)+y(x[1]+1)]\
>>> combOp = (lambda x, y:[x[0]+y(x[1]+y(x[1])])\
>>> rdd3.aggregate((0,0),seqOp,combOp)\
(4950,100)\
\
```python\
[('a', (9, 2)), ('b', (2, 1))]\
>>> rdd3.fold(0, add)\
1050\
\
Applying Functions\
\
```python\
>>> rdd.map(lambda x: x+(x[1],x[0]))\
\
```python\
[('a',7,7,'a'),('a',2,2,'a'),('b',2,2,'b')]\
>>> rdd5 = rdd.flatMap(lambda x: x+(x[1],x[0]))\
\
```python\
>>> rd5.collect()\
['a',7,'7','a',2,2,'a','b',2,2,'b']\
>>> rd4.flatMapValues(lambda x: x)\
.collect()\
\
Apply a function to each RDD element and flatten the result\
\
[('a', 'x'), ('a', 'y'), ('a', 'z'), ('b', 'p'), ('b', 'r')]\
\
Selecting Data\
\
```python\
>>> rdd.collect()\
\
Getting\
\
Return a list with all RDD elements\
\
[('a',7), ('a',2), ('b',2)]\
\
Return (key,value) RDD's keys\
\
[('a', 7), ('a', 2)]\
\
```javascript\
collect()\
[('a',7), ('a',2)]\
\
```python\
>>> rdd5.distinct().collect()\
[1, 2, 3, 4, 5]\
\
('a', 7)\
\
Sampling\
\
```python\
['a',2,'b',7]\
>>> rdd.keys().collect()\
\
[('b', 2), ('a', 7)]\
\
```python\
>>> rdd.filter(lambda x: "a" in x)\
\
Filtering\
\
Mathematical Operations\
\
Sort RDD by given function\
\
O(log(n))\
\
Θ(log(n))\
\
Return each (key,value) pair of rdd2 with no matching key in rdd\
\
Iterating\
\
Θ(log(n))\
\
```python\
>>> rdd.saveAsHadoopFile("hdfs://namenodehost/parent/child",\
    "org.apache.hadoop.mapred.TextOutputFormat")\
\
O(log(n))\
\
Θ(log(n))\
\
Return each rdd value not contained in rdd2\
\
O(log(n))\
\
Stopping SparkContext\
\
O(log(n))\
\
New RDD with 4 partitions Decrease the number of partitions in the RDD to 1\
\
Repartitioning\
\
LEGEND\
\
Saving\
\
O(log(n))\
\
Θ(log(n)) Θ(log(n))\
\
```python\
>>> rdd.subtract(rdd2)\
collect()\
\
Sort (key, value) RDD by key\
\
```python\
>>> sc.stop()\
\
```python\
>>> rdd.cartesian(rdd2).collect()\
\
Return the Cartesian product of rdd and rdd2\
\
Θ(log(n))\
\
Θ(log(n))\
\
[('d',1)]\
\
0(log(n))\
\
0(log(n))\
\
Execution\
\
Θ(log(n)) Θ(log(n))\
\
Θ(log(n))\
\
0(n)\
\
0(log(n))\
\
Θ(log(n)) Θ(log(n))\
\
$ ./bin/spark-submit examples/src/main/python/pi.py\
\
```python\
>>> rdd2.sortByKey()\
    .collect()\
[('a',2), ('b',1), ('d',1)]\
\
O(log(n))\
\
```python\
>>> rdd2.sortBy(lambda x: x[1])\
collect()\
\
0(log(n)) 0(log(n))\
\
Good Fair Bad\
\
0(log(n)) 0(log(n))\
\
0(log(n)) 0(log(n))\
\
0(n)\
\
DataCamp for Data Science\
\
Shell Sort\
\
$ \Omega ( n \log(n) ) $\
\
Radix Sort 1 10 100\
\
O(n(log(n)))^2)\
\
O(n+k)\
\
0(n^2)\
\
Θ(nk)\
\
0(n)\
\
0(n+k)\
\
0(n+k)\
\
0(n log(n))\
\
---\
\
Big-O Complexity Chart\
\
| Data Structure | Time Complexity |  |  |  |  |  |  |  | Space Complexity |\
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\
|  | Average |  |  |  | Worst |  |  |  | Worst |\
|  | Access | Search | Insertion | Deletion | Access | Search | Insertion | Deletion |  |\
| Array | θ(1) | θ(n) | θ(n) | θ(n) | 0(1) | 0(n) | 0(n) | 0(n) | 0(n) |\
| Stack | θ(n) | θ(n) | θ(1) | θ(1) | 0(n) | 0(n) | 0(1) | 0(1) | 0(n) |\
| Queue | θ(n) | θ(n) | θ(1) | θ(1) | 0(n) | 0(n) | 0(1) | 0(1) | 0(n) |\
| Singly-Linked List | θ(n) | θ(n) | θ(1) | θ(1) | 0(n) | 0(n) | 0(1) | 0(1) | 0(n) |\
| Doubly-Linked List | θ(n) | θ(n) | θ(1) | θ(1) | 0(n) | 0(n) | 0(1) | 0(1) | 0(n) |\
| Skip List | θ(log(n)) | θ(log(n)) | θ(log(n)) | θ(log(n)) | 0(n) | 0(n) | 0(n) | 0(n) | 0(n log(n)) |\
| Hash Table | N/A | θ(1) | θ(1) | θ(1) | N/A | 0(n) | 0(n) | 0(n) | 0(n) |\
| Binary Search Tree | θ(log(n)) | θ(log(n)) | θ(log(n)) | θ(log(n)) | 0(n) | 0(n) | 0(n) | 0(n) | 0(n) |\
| Cartesian Tree | N/A | θ(log(n)) | θ(log(n)) | θ(log(n)) | N/A | 0(n) | 0(n) | 0(n) | 0(n) |\
| B-Tree | θ(log(n)) | θ(log(n)) | θ(log(n)) | θ(log(n)) | 0(log(n)) | 0(log(n)) | 0(log(n)) | 0(log(n)) | 0(n) |\
| Red-Black Tree | θ(log(n)) | θ(log(n)) | θ(log(n)) | θ(log(n)) | 0(log(n)) | 0(log(n)) | 0(log(n)) | 0(log(n)) | 0(n) |\
| Splay Tree | N/A | θ(log(n)) | θ(log(n)) | θ(log(n)) | N/A | 0(log(n)) | 0(log(n)) | 0(log(n)) | 0(n) |\
| AVL Tree | θ(log(n)) | θ(log(n)) | θ(log(n)) | θ(log(n)) | 0(log(n)) | 0(log(n)) | 0(log(n)) | 0(log(n)) | 0(n) |\
| KD Tree | θ(log(n)) | θ(log(n)) | θ(log(n)) | θ(log(n)) | 0(n) | 0(n) | 0(n) | 0(n) | 0(n) |\
\
\overline{[\theta(n)]}\
\
\frac{thetatheta(\log(n))}{\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ }\
\
\frac{[0mathsf{n}]}{[(n)]}\
\
\frac{thetatheta(\log(n))}{\ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ \ }\
\
\underline{{\boxed{\(o g(n))}}}\
\
\box(\ \ \square(o g(n))]\
\
\overline({0(\log(n))}\
\
\underline{{\boxed(o g(n))}}\
\
[box(\log(n)]\
\
\ (\ \ \theta(\ g(n))\
\
\ (\ \ \square(\ g(n))\
\
\sqrt{0(n)}\
\
\underline{{\boxed(\ g(n))}}\
\
\boxed{\underline{{\theta(\log o n))}}}\
\
\ (\log(n))\
\
\underline{{\boxed{0(o o g(n))}}}\
\
\begin array}{l}{\overbrace{\ \ \underset{(theta)}{\ \ \0(o g(n))}}^{\ \underset{(\theta)({\ }079(n))}}}\end{array}\
\
\sqrt{(\log(n))}\
\
\boxed{\ {(\ G(\ g(n))}}\
\
\ {sqrt}(\ \ 9(\ g(n))]\
\
0(\log(n))1\
\
\over{\\frac{{theta}(omega9n)}{n-1}}\
\
\ (\ \ \theta(\ g(n))\
\
\frac{\box{\(\mathrm{{o o g(n)}})}}{\boxed{\mathrm{{o o g(n)}}}}\
\
\frac{0(\log(n))}{0(\log(n))}\
\
B(\log(n))\
\
[(\ \ 9(\ g9)n]\
\
\sqrt{(n)}]

\ 0(n)]

\ {0(n)}
```` |
