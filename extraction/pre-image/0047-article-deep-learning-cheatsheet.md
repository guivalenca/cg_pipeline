---
id: "47"
title: "Deep Learning cheatsheet"
source_url: "https://github.com/afshinea/stanford-cs-229-machine-learning/blob/master/en/cheatsheet-deep-learning.pdf"
fetch_url: "https://raw.githubusercontent.com/afshinea/stanford-cs-229-machine-learning/master/en/cheatsheet-deep-learning.pdf"
resolved_url: "https://raw.githubusercontent.com/afshinea/stanford-cs-229-machine-learning/master/en/cheatsheet-deep-learning.pdf"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T03:59:51.981347Z"
provider: "firecrawl"
strategy: "pdf"
cache_key: "65be14d21a924e78e81654593cda8da1cb30bcbbd9912894a914cbfef958208a"
firecrawl_status_code: 200
firecrawl_content_type: "application/pdf"
word_count: 758
char_count: 4448
content_sha256: "0dae51263b50ba52add18bd5d6a31af50b42440c1facbb45f4c52d040d79fafa"
image_count: 0
link_count: 0
warnings:
  - "missing_screenshot"
  - "rewritten_source_url"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes:
  - "github_blob_pdf_rewritten_to_raw_url"
  - "pdf_mode_auto"
  - "github_pdf_wrapper_rewrite"
  - "github_app_ui_or_wrapper_page"
---

# VIP Cheatsheet: Deep Learning

**Afshine Amidi and Shervine Amidi**  
**September 15, 2018**  

## Neural Networks

Neural networks are a class of models that are built with layers. Commonly used types of neural networks include convolutional and recurrent neural networks.

### Architecture

The vocabulary around neural networks architectures is described in the figure below:

Input layer  
Hidden layer 1  
Hidden layer k  
Output layer

By noting i the ith layer of the network and j the jth hidden unit of the layer, we have:

$$z_{j}^{[i]}={w_{j}^{[i]}}^{T}x+b_{j}^{[i]}$$  

where we note w, b, z the weight, bias and output respectively.

### Activation Functions

$$g(z)=\frac{1}{1+e^{-z}}$$  
$$\overline{g(z)=\frac{e^{z}-e^{-z}}{e^{z}+e^{-z}}}$$  
$$g(z)=\operatorname*{max}(0,z)$$  
$$g(z)=\operatorname*{max}(\epsilon z, 0)$$

### Learning Rate

The learning rate, often noted η, indicates at which pace the weights get updated. This can be fixed or adaptively changed. The current most popular method is called Adam, which is a method that adapts the learning rate.

### Backpropagation

Backpropagation is a method to update the weights in the neural network by taking into account the actual output and the desired output. The derivative with respect to weight w is computed using chain rule and is of the following form:

$$\frac{\partial L(z,y)}{\partial w}$$

As a result, the weight is updated as follows:
1. Step 1: Take a batch of training data.
2. Step 2: Perform forward propagation to obtain the corresponding loss.
3. Step 3: Backpropagate the loss to get the gradients.
4. Step 4: Use the gradients to update the weights of the network.

### Dropout

Dropout is a technique meant at preventing overfitting the training data by dropping out units in a neural network. In practice, neurons are either dropped with probability p or kept with probability 1 − p.

### Convolutional Layer Requirement

By noting W the input volume size, F the size of the convolutional layer neurons, P the amount of zero padding, then the number of neurons N that fit in a given volume is such that:

$$x_{i}\longleftarrow\gamma\frac{x_{i}-\mu_{B}}{\sqrt{\sigma_{B}^{2}+\epsilon}}+\beta$$

## Convolutional Neural Networks

### Recurrent Neural Networks

#### Types of Gates

Here are the different types of gates that we encounter in a typical recurrent neural network:

| Input gate | Forget gate | Output gate | Gate |
| --- | --- | --- | --- |
| Write to cell or not? | Erase a cell or not? | Reveal a cell or not? | How much writing? |

#### LSTM

A long short-term memory (LSTM) network is a type of RNN model that avoids the vanishing gradient problem by adding 'forget' gates.

## Reinforcement Learning and Control

The goal of reinforcement learning is for an agent to learn how to evolve in an environment.

### Markov Decision Processes

A Markov decision process (MDP) is a 5-tuple (S,A,{P_sa},γ,R) where:
- **S** is the set of states
- **A** is the set of actions
- **P_sa** are the state transition probabilities for s ∈ S and a ∈ A
- **γ** ∈ [0,1[ is the discount factor
- **R**: S×A −→ R or R: S −→ R is the reward function that the algorithm wants to maximize

### Policy

A policy π is a function π : S−→A that maps states to actions. Remark: we say that we execute a given policy π if given a state s we take the action a = π(s).

### Value Function

For a given policy π and a given state s, we define the value function Vπ as follows:  

### Bellman Equation

The optimal Bellman equations characterize the value function V of the optimal policy π*:  

$$V^{*}(s)=\operatornamewithlimits{argmax}{a \in \mathcal{A}}\sum_{s^{\prime}\in\mathcal{S}}P_{sa}(s^{\prime})V^{*}(s^{\prime})$$  

We initialize the value:

$$V_{0}(s)=0$$

We iterate the value based on the values before:

$$V_{i+1}(s)=R(s)+\operatorname*{max}_{a\in\mathcal{A}}\left[\sum_{s^{\prime}\in\mathcal{S}}\gamma P_{sa}(s^{\prime})V_{i}(s^{\prime})\right]$$

### Maximum Likelihood Estimate

The maximum likelihood estimates for the state transition probabilities are as follows:

$$P_{sa}(s^{\prime})=\frac{\text{# times took action } a \text{ in state } s \text{ and got to } s^{\prime}}{\text{# times took action } a \text{ in state } s}$$

### Q-Learning

Q-learning is a model-free estimation of Q, which is done as follows:

$$Q(s,a)\leftarrow Q(s,a)+\alpha\left[R(s,a)+\gamma\operatorname*{max}_{a^{\prime}}Q(s^{\prime},a^{\prime})-Q(s,a)\right]$$
