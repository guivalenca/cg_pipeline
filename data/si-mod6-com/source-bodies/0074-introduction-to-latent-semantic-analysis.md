---
id: "74"
title: "Introduction to Latent Semantic Analysis"
source_url: "https://www.youtube.com/playlist?list=PLroeQp1c-t3qwyrsq66tBxfR6iX6kSslt"
fetch_url: "https://www.youtube.com/watch?v=hB51kkus-Rc"
resolved_url: "https://www.youtube.com/watch?v=hB51kkus-Rc"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T05:31:46.401328Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "c6243a73c15bcd67654e700c78f7644d29859355732ab699d36c17c6ad502aab"
cache_keys:
  - "c6243a73c15bcd67654e700c78f7644d29859355732ab699d36c17c6ad502aab"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.1
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 204.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "0be0a6c401275dd6f1eedfc14ee0702310a2180e9efe02afe6d2a1cf988e1219"
word_count: 920
char_count: 5254
content_sha256: "71f20001c6e04fb69d52c05025ba9835e19db6e5d994141cdf37bd520f4c1214"
image_count: 5
link_count: 0
total_token_count: 11125
estimated_input_tokens: 7874
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## 00:00 Introduction to Latent Semantic Analysis

**Spoken content:**
- [00:00] JOSHUA COOK: Hi, my name is Joshua Cook,
- [00:06] and I'm a curriculum developer with Databricks.
- [00:08] Today, we're going to be talking about latent semantic analysis.
- [00:11] There is a link to the notebook I'll
- [00:13] be using in the video description
- [00:14] if you would like to follow along.
- [00:16] Before we begin, let's define some basic vocabulary.
## 00:19 Basic Vocabulary for NLP

**Spoken content:**
- [00:19] Natural language processing refers
- [00:21] to a family of techniques that are
- [00:22] used to derive meaning from text data.
- [00:25] A document refers to some collection of words
- [00:28] and represents the rows or instances of our data set.
- [00:31] A body is a collection of documents
- [00:34] and represents the entire data set.
- [00:36] A dictionary is the set of all words
- [00:38] that occur in at least one document in the data set.
- [00:42] A topic is a collection of words that co-occur.

**On-screen content:**
![definitions of Natural Language Processing, Document, Body, Dictionary, Topic](video-frame://74@00:19)

## 00:45 Understanding Latent Semantic Analysis

**Spoken content:**
- [00:45] In this lesson, we're going to be talking about latent semantic
- [00:48] analysis.
- [00:48] So the word latent means hidden, and in this context
- [00:52] refers to features that cannot be directly measured.
- [00:55] What we're going to be measuring or what has already
- [00:57] been measured are the words that are in our data set.
- [00:59] What we're interested in is latent features, hidden features,
- [01:03] that represent something essential in the data set.
- [01:06] Latent semantic analysis is a natural language processing
- [01:09] technique, as well as an unsupervised learning
- [01:11] technique, this as opposed to supervised learning.
- [01:13] So in supervised learning, we would have a target or a label.
- [01:16] With latent semantic analysis, we don't have this.
- [01:19] We're looking at something that's latent or inherent
- [01:21] to the data itself.
- [01:23] The aim of latent semantic analysis is to create representations
- [01:27] of the text data in terms of these topics or latent features.
- [01:32] A side benefit of this is that we're
- [01:33] going to be able to reduce the dimensionality
- [01:36] of the original text-based data set.
## 01:38 Latent Semantic Analysis Process

**Spoken content:**
- [01:38] As you can see in this diagram, latent semantic analysis
- [01:41] consists of two steps.
- [01:43] The first step is to generate a document term matrix,
- [01:46] and the second step is to perform a singular value decomposition
- [01:50] on that document term matrix.
- [01:52] The basic idea of a document term matrix

**On-screen content:**
![diagram: Latent Semantic Analysis process showing Raw Text Data -> Document Term Matrix -> Singular Value Decomposition -> Topic-Encoded Data](video-frame://74@01:39)

## 01:52 Document-Term Matrix Explained

**Spoken content:**
- [01:54] is that text documents can be represented
- [01:57] as points in Euclidean space.
- [01:59] You might know these as vectors.
- [02:02] Here is an example of a document term matrix.
- [02:04] As you can see, each row in this matrix
- [02:06] represents one of our documents.
- [02:08] In this case, one of four simple sentence fragments.
- [02:11] And then each column represents a word from the dictionary.
- [02:15] That is, a word that shows up in at least one
- [02:17] of the four documents.
- [02:20] If you look at the first row, the quick brown fox,
- [02:23] you can see that the word brown has the value 1,
- [02:26] the word fox has the value 1, the word quick has the value 1,
- [02:29] and the word the has the value 1.
- [02:31] And everywhere else is zeros.
- [02:33] So here we see these four documents as vectors.
- [02:36] As you can see, the quick brown fox is 1, 0, 1, 0, 1, 0, 1, 0.
- [02:42] The second step in a latent semantic analysis

**On-screen content:**
![diagram: documents as vectors in Euclidean space](video-frame://74@01:50)
![table: Document-Term Matrix with rows as sentences and columns as words, showing binary presence/absence](video-frame://74@02:01)
![code: four documents represented as binary vectors](video-frame://74@02:30)

## 02:42 Singular Value Decomposition (SVD)

**Spoken content:**
- [02:44] is to do a singular value decomposition on the document term matrix.
- [02:48] The singular value decomposition is similar to a principal component
- [02:52] analysis, if you're familiar with this statistical technique.
- [02:55] It's going to reduce the dimensionality of the original data set
- [02:59] by encoding it using these latent features.
- [03:02] With latent semantic analysis, these latent features
- [03:04] represent topics in the original text data.
- [03:08] In the next few videos, we're going
## 03:08 Next Steps: Building LSA with Scikit-learn

**Spoken content:**
- [03:09] to be looking at building a latent semantic analysis
- [03:12] using the open source Python library scikit-learn.
- [03:16] First, we'll look at a trivial implementation
- [03:18] using these four sentence fragments that we just looked at.
