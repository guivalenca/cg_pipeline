---
id: "78"
title: "Text Summarization of COVID-19 Medical Articles using BERT and GPT-2 (Research Paper Walkthrough)"
source_url: "https://youtu.be/kC5kP1dPAzc"
fetch_url: "https://youtu.be/kC5kP1dPAzc"
resolved_url: "https://www.youtube.com/watch?v=kC5kP1dPAzc"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T04:47:12.364334Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "d77cd2c6bbde2a7e6620d99cb5a2ac96aed9aa0a371e08a88eae37d45b0963f7"
cache_keys:
  - "d77cd2c6bbde2a7e6620d99cb5a2ac96aed9aa0a371e08a88eae37d45b0963f7"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 1311.0
transcript_source: "manual_captions"
transcript_sha256: "ee7dc385ed4dd4dfe2d2b0ad61a5754b91d87e008e2fc551ba170c9a7b17b8e4"
word_count: 1463
char_count: 9639
content_sha256: "fdb699ac4c69a991a82f0b3b8fcbe4e8389eec10851378c39c382f2222a46a9d"
image_count: 17
link_count: 0
total_token_count: 86795
estimated_input_tokens: 70505
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Automatic Text Summarization of COVID-19 Medical Research Articles using BERT and GPT-2

**Spoken content:** The presenter introduces a recent preprint paper from Rockefeller University, published in June 2020, focusing on automatic text summarization of COVID-19 medical research articles using BERT and GPT-2.

**On-screen content:**
![title slide with authors and affiliations](video-frame://78@00:00)

## [00:21] Abstract: COVID-19 Open Research Dataset Challenge

**Spoken content:** The COVID-19 Open Research Dataset Challenge released a corpus of scholarly articles, calling for machine learning approaches to bridge the gap between researchers and rapidly growing publications. The authors leverage pre-trained NLP models like BERT and OpenAI GPT-2 for text summarization on this dataset. They evaluate results using ROUGE scores and visual inspection. Their model provides abstractive and comprehensive information based on extracted keywords, aiming to provide succinct summaries for articles without existing abstracts.

**On-screen content:**
![abstract text with highlights on key terms](video-frame://78@00:21)

## [01:54] Introduction: Text Summarization Approaches

**Spoken content:** The COVID-19 Open Research Dataset Challenge includes roughly 59,000 scholarly articles, with over 47,000 full-text articles related to COVID-19. Text summarization is an active research area focused on condensing large texts while retaining relevant information. Two main approaches are extractive summarization (extracting and concatenating important text spans) and abstractive summarization (generating new summaries that paraphrase the source text).

**On-screen content:**
![introduction section discussing COVID-19 dataset and text summarization types](video-frame://78@01:54)

## [02:54] Extractive vs. Abstractive Summarization

**Spoken content:** Extractive summarization focuses on generating new summaries that paraphrase the source text. Extractive approaches generally show high grammatical correctness and accuracy because they directly use sentences from the original text. Abstractive summarization is more challenging as it requires the model to represent semantic information and generate paraphrases creatively, making inferences from the source text.

**On-screen content:**
![comparison of extractive and abstractive summarization approaches](video-frame://78@02:54)

## [04:13] Low-Resource Challenge

**Spoken content:** A significant challenge is the low availability of domain-specific corpora. Unlike general summarization datasets like CNN/Daily Mail with 286k document-summary pairs, the COVID-19 related literature has only about 35k full-text abstract pairs. Additionally, the scientific terminology in peer-reviewed literature is often esoteric and not used in the mainstream text where large models like BERT and GPT were pre-trained, posing an impediment to fine-tuning.

**On-screen content:**
![section on low-resource challenge with highlighted text](video-frame://78@04:13)

## [05:10] Approach: Overall Outline (Extractive Part)

**Spoken content:** The project is divided into two parts: an unsupervised extractive part (used as a baseline) and a novel abstractive part. The unsupervised extractive summarization uses a pre-trained BERT model to perform sentence embedding, transforming each sentence into a 768-dimensional representation. K-medoid clustering is then applied to these high-dimensional representations, and the cluster centers are extracted as the summary.

**On-screen content:**
![approach section detailing unsupervised extractive summarization using BERT and K-medoid clustering](video-frame://78@05:10)
![diagram illustrating sentence embedding and K-medoid clustering for extractive summarization](video-frame://78@06:01)

## [07:01] K-Means vs K-Medoid Clustering

**Spoken content:** The presenter explains K-Means clustering first. Given N data points and a desired number of clusters K (e.g., K=2), K-Means initializes K cluster centroids randomly or using K-Means++. Each data point is assigned to the closest centroid based on Euclidean distance. Then, the centroids are updated by calculating the mean of all data points assigned to that cluster. This process iterates until centroids no longer significantly change position.

K-Medoid clustering is then introduced as an alternative. Unlike K-Means where centroids are virtual points, K-Medoid uses actual data points as cluster centers (medoids). The process is similar: initialize K medoids, assign data points to the closest medoid, but for updating, instead of taking the mean, it selects a new medoid from the cluster's data points that minimizes the sum of squared errors within that cluster. This ensures the medoid is an actual data point.

**On-screen content:**
![diagram comparing K-Means and K-Medoid clustering algorithms](video-frame://78@07:01)

## [12:22] Approach: Overall Outline (Abstractive Part)

**Spoken content:** For the abstractive summarization, keywords are extracted from the source text using existing token classification tools like NLTK's part-of-speech tagging or fine-tuned BERT. Verbs and nouns are typically extracted as keywords. These keywords are then paired with human-generated gold summaries and fed into the GPT-2 model. The results are compared against the gold summary using ROUGE scores.

**On-screen content:**
![approach section detailing abstractive summarization using keyword extraction and GPT-2](video-frame://78@12:22)
![diagram showing keyword extraction and pairing with abstract for GPT-2 input](video-frame://78@13:16)

## [13:48] Training Strategy of the Abstractive Summarization GPT-2

**Spoken content:** The GPT-2 model is trained on two tasks: language modeling (LM) and multiple-choice prediction (MC). For LM, the model predicts the next word token given previous tokens and context. For MC, given a set of keywords, the model chooses the correct gold summary from multiple choices. Each task has an associated loss. The LM task projects the hidden state to the word embedding output layer, using cross-entropy loss. For training, special tokens like `<summarize>` are used to separate keywords and the gold summary. Input sequences are padded to 1024 tokens, and longer inputs are truncated. For the MC task, the hidden state of the last token (`<endoftext>`) is passed through a linear layer for classification.

**On-screen content:**
![training strategy for abstractive summarization with GPT-2, showing LM and MC tasks](video-frame://78@13:48)
![diagram illustrating the input format for GPT-2 training with special tokens](video-frame://78@15:27)

## [17:13] Intuition of the Training Strategy

**Spoken content:** The language modeling training labels are right-shifted by one token because GPT-2 is auto-regressive, predicting the Nth token from N-1 previous tokens. The total loss is a weighted sum of the LM loss and MC loss (2:1 ratio). The intuition behind this strategy is using a masked self-attention mechanism to block information from tokens to the right. The special token `<summarize>` signifies the context, and GPT-2 learns this context cue. Multi-loss training aims to map local semantic context in keywords to the gold summary and retain global contextual information to distinguish gold summaries from distractors.

**On-screen content:**
![explanation of language modeling training labels and weighted loss](video-frame://78@17:13)
![explanation of masked self-attention and multi-loss training intuition](video-frame://78@17:51)

## [19:19] Figure 1: Overview of GPT-2 Multi-Loss Training

**Spoken content:** The diagram shows the GPT-2 multi-loss training. The input consists of 4 items: 1 true abstract and 3 distractors. Each item starts with a beginning-of-sentence token, followed by keywords, the `<summarize>` special token, the abstract/distractor text, an end-of-sentence token, and padding. This input goes through the GPT-2 language model (6 transformer blocks). The output then feeds into two heads: a Language Modeling head and a Multiple Choice head. The LM head predicts the next token, while the MC head classifies if the input was a true abstract or a distractor. The losses from both heads are combined to train the model.

**On-screen content:**
![diagram: Overview of GPT-2 multi-loss training, showing input, architecture, and two heads](video-frame://78@19:20)

## [20:13] Experiments and Results (Implicit)

**Spoken content:** The presenter briefly mentions that the paper includes experiments and results. He then elaborates on the intuition behind the multiple-choice loss: if the model incorrectly predicts a label (e.g., 1 instead of 0), the resulting loss adjusts the weights in the linear layer and within GPT-2. This adjustment aims to produce better embedding representations for the end-of-sequence token, aligning it with the correct label's distribution (e.g., distractor distribution for a '0' label). This, in turn, influences the language modeling head to generate words from the relevant distribution, leading to a lower multiple-choice loss.

**On-screen content:**
![section heading for Experiments and Results](video-frame://78@20:13)

## [21:16] Conclusion and Suggestion

**Spoken content:** The presenter concludes that the paper was an interesting read. He offers a suggestion for future work: instead of using just keywords as input for abstractive summarization, they could try using sentences extracted from an extractive summarization step as input to generate the abstractive summary.

**On-screen content:**
![title slide of the paper](video-frame://78@21:14)
