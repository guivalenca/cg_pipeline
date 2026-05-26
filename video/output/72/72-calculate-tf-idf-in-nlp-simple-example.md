---
id: "72"
title: "Calculate TF-IDF in NLP (Simple Example)"
source_url: "https://www.youtube.com/watch?v=vZAXpvHhQow"
fetch_url: "https://www.youtube.com/watch?v=vZAXpvHhQow"
resolved_url: "https://www.youtube.com/watch?v=vZAXpvHhQow"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T04:46:30.421343Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "690b2723ec8d43e8a8f2ab8479a687bdc8dfa487fa56b0b16a06f89bd6a3591f"
cache_keys:
  - "690b2723ec8d43e8a8f2ab8479a687bdc8dfa487fa56b0b16a06f89bd6a3591f"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 501.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "8b19e87327d7cbce6e8d4538cd1093c4d7136f6d6093cf45e7088b4eeaa2419d"
word_count: 1649
char_count: 9073
content_sha256: "d2c37b3b95b3aa64f0728351a9fce7bcc0fa7a002816392237864de9a2056cfa"
image_count: 9
link_count: 0
total_token_count: 33139
estimated_input_tokens: 26943
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## 00:00 Calculating TF-IDF (very simple example)

**Spoken content:** Hello guys, in this video we will talk about TF-IDF and how it should be calculated with a very simple example. So, let's start.

**On-screen content:**
![Title slide: Calculating TF-IDF (very simple example) with corpus D documents and TF-IDF solution details](video-frame://72@00:00)

## 00:20 Introduction to TF-IDF

**Spoken content:** A very popular representation for text is the product of term frequency and inverse document frequency, commonly referred to as TF-IDF. The TF-IDF value of a term T in a given document D is like this. Note that a TF-IDF value is specific to a single document D, where IDF depends on the entire corpus.

**On-screen content:**
A very popular representation for text is the product of:
- Term Frequency (TF)
- Inverse Document Frequency (IDF)
Commonly referred to as TF-IDF.

The TF-IDF value of a term $t$ in a given document $d$:
$TFIDF(t, d) = TF(t, d) \times IDF(t)$

TFIDF value is specific to a single document $d$.
IDF depends on entire corpus.

## 00:45 Preprocessing and Feature Vectors

**Spoken content:** Systems employing the bag of words representation typically go through steps of stemming and stop words elimination before doing term counts. Term counts within the document from the TF values for each term and the document counts across the corpus from the IDF values. Each document thus becomes a feature vector and the corpus is set of these feature vectors. This can be used in a data mining algorithm for classification, clustering or retrieval.

**On-screen content:**
![Diagram showing Bag of Words representation leading to Stemming and Stopwords elimination, then Term count within the document for TF and Document counts across the corpus for IDF, ultimately forming a Feature vector for data mining applications](video-frame://72@00:45)

## 01:21 Calculation Example: Corpus and Question

**Spoken content:** That was a quick introduction to TF-IDF and now let's go to a simple task. Let's have a situation. We have some sentences. The first one is: A quick brown fox jumps over the lazy dog. What a fox! The second one: A quick brown fox jumps over the lazy fox. What a fox! Please keep in mind that all the sentences in our corpus are defined as small d. So we have D1 and D2. Based on this rule, our corpus is defined as the big D. Now we have some data. This data led us to shape a main question. And the question is like this: How word fox is relevant to corpus D documents? Remember we have documents D1 and D2.

**On-screen content:**
![Corpus D with two documents, d1 and d2, and the question about the relevance of the word "fox"](video-frame://72@01:55)
Corpus D
d1 A quick brown fox jumps over the lazy dog. What a fox!
d2 A quick brown fox jumps over the lazy fox. What a fox!

Question: How word fox is relevant to corpus D documents?

## 02:19 Solution: Calculating Term Frequency (TF)

**Spoken content:** Let's go to the solution part. Let's start in here with some definitions. What is DFIDF? In the first part of this calculation we need to clarify that DF is the frequency of any term in a given document. We need to calculate DF for document number one and document number two by a given argument, a word fox. So let's calculate. For document number one we have 12 words in total. In this context, we have a word fox occurred two times. Knowing this information we can calculate DF like this. 2 dividing by 12 equals 0.17. In the same way we calculate DF for document number two. In this case, we have fox occurred three times in this document. So the calculation will be as follow. 3 dividing by 12 equal to 0.25. Keeping in mind that D1 and D2 has the same number of total words. The first part of calculation is done.

**On-screen content:**
![TF-IDF calculation showing the corpus, question, and the TF calculation for documents d1 and d2](video-frame://72@02:48)
Solution:
TF-IDF
TF is the frequency of any "term" in a given "document".

$TF("fox", d1) = 2 / 12 = 0.17$
$TF("fox", d2) = 3 / 12 = 0.25$

## 03:42 Solution: Calculating Inverse Document Frequency (IDF)

**Spoken content:** Now we have to move to the second part. We need to calculate IDF. IDF is constant per corpus and account for the ratio of documents that include that specific term. We need to calculate IDF for full corpus that we have. For this we are using a logarithm. In this equation, at the upper side, we need to look at how many documents at our corpus a given word fox is accurate. Now we see that a word fox is accurate in document number one and in document number two. So, at the upper side of our equation, we need to input a value of two. On the lower side of this equation, we have to input a value of total documents that our corpus consists of. And that means we have to input value of two because we have two documents in total in our corpus. That resulting into logarithm 2 dividing by two and it is equal to zero.

**On-screen content:**
![IDF calculation showing the definition and the logarithmic formula with the result](video-frame://72@03:56)
IDF is constant per corpus, and accounts for the ratio of documents that include that specific "term".

$IDF("fox", D) = log(2/2) = 0$

## 04:58 Solution: Calculating TF-IDF for each document

**Spoken content:** Now we have enough information to calculate TF IDF for all documents in our corpus D. We have document number one and document number two. So, we will calculate TF IDF separately for each document in our corpus. For the first document, TF IDF equal to 0.17 from the first part of our calculation multiplied by 0. It is from second part of our calculation. And it is equal to zero. For the second document, we calculate TF IDF in the same rules that we applied for the first document. Let's do like this. 0.25 from the first part of our calculation and multiplied by 0 from the second part of our calculations. And it is equal to zero. Now we have calculated TF IDF for all documents in our corpus. And for document number one, TF IDF equal to zero. For the second document in our corpus, we have calculated TF IDF and it is equal to zero again.

**On-screen content:**
![TF-IDF calculation for both documents d1 and d2, showing the multiplication of TF and IDF values](video-frame://72@05:00)
$TFIDF("fox", d1) = 0.17 \times 0 = 0$
$TFIDF("fox", d2) = 0.25 \times 0 = 0$

## 06:16 Answering the Question

**Spoken content:** Now we have calculated TF IDF for all the documents in our corpus and that means that now we can answer to the main question in this task. How a word fox is relevant to corpus D documents? And the answer is: Using TF IDF that we have calculated just before, the word fox is equally relevant for both documents D1 and document D2 because we have the same values of TF IDF. It's zero.

**On-screen content:**
![Answer to the question, stating that the word "fox" is equally relevant for both documents](video-frame://72@06:30)
Answer: Using TF-IDF, the word "fox" is equally relevant for both document d1 and document d2.

## 06:51 TF and IDF Recap

**Spoken content:** This calculation can be applied in any amount of documents that you have in your corpus. And one more time again, what is TF and IDF? TF is a simple choice to use the raw count of a term in a document. And the IDF, inverse document frequency, is a measurement of how much information the word provides in our corpus. By saying corpus, I mean across all the documents that we are having.

**On-screen content:**
![Recap of TF and IDF definitions](video-frame://72@07:04)
TF is the frequency of any "term" in a given "document".
IDF is constant per corpus, and accounts for the ratio of documents that include that specific "term".

## 07:26 TF-IDF Summary and Uses

**Spoken content:** So by summarizing this video, TF IDF is a statistical measurement that evaluates how relevant a word is to a document in a collection of documents. This is done by multiplying two metrics: how many times a word appears in a document, and the inverse document frequency of the words across the set of documents. It has many uses, most importantly in automated text analysis, and is very useful for scoring words in machine learning algorithms for NLP. TF IDF was invented for document search and information retrieval. I hope that this video was useful for you, and I wish you never stop learning. If you like this one, please subscribe me and you will get more similar useful videos in future. So, see you there.

**On-screen content:**
![Summary of TF-IDF and its uses](video-frame://72@07:26)
TF-IDF is a statistical measurement that evaluates how relevant a word is to a document in a collection of documents.
This is done by multiplying two metrics: how many times a word appears in a document, and the inverse document frequency of the word across the set of documents.
It has many uses, most importantly in automated text analysis, and is very useful for scoring words in machine learning algorithms for NLP.
TF-IDF was invented for document search and information retrieval.
