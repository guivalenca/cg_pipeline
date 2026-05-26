---
id: "67"
title: "Feature Extraction and Embeddings in NLP: A Beginners guide to understand Natural Language Processing"
source_url: "https://www.analyticsvidhya.com/blog/2021/07/feature-extraction-and-embeddings-in-nlp-a-beginners-guide-to-understand-natural-language-processing/"
fetch_url: "https://www.analyticsvidhya.com/blog/2021/07/feature-extraction-and-embeddings-in-nlp-a-beginners-guide-to-understand-natural-language-processing"
resolved_url: "https://www.analyticsvidhya.com/blog/2021/07/feature-extraction-and-embeddings-in-nlp-a-beginners-guide-to-understand-natural-language-processing/"
firecrawl_title: "Feature Extraction and Embeddings in Natural Language Processing"
description: "In this article, we will discuss the various methods of feature extraction and word embeddings practiced in Natural Language processing."
fetched_at: "2026-05-12T03:59:52.728091Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "b5e8a8f84ccc7c11df05b63838f5e4275f2eda439f4f358dfb2430e2091652a4"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=UTF-8"
word_count: 1433
char_count: 8912
content_sha256: "234e135da90b5f869036bbe41c27d32d42b938303b40c0c5e6fcfe41cf13d0d4"
image_count: 13
link_count: 268
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "template_heavy_blog"
---

# Feature Extraction and Embeddings in NLP: A Beginners guide to understand Natural Language Processing

![Siddharth M](https://av-eks-lekhak.s3.amazonaws.com/media/lekhak-profile-images/converted_image_1jV4NCP.webp)

[Siddharth M](https://www.analyticsvidhya.com/blog/author/siddharth1698/) Last Updated :
20 Jul, 2021

6 min read

This article was published as a part of the [Data Science Blogathon](https://datahack.analyticsvidhya.com/contest/data-science-blogathon-10/True/)

## Introduction

In Natural Language Processing, Feature Extraction is one of the trivial steps to be followed for a better understanding of the context of what we are dealing with. After the initial text is cleaned and normalized, we need to transform it into their features to be used for modeling. We use some particular method to assign weights to particular words within our document before modeling them. We go for numerical representation for individual words as it’s easy for the computer to process numbers, in such cases, we go for word embeddings.

![Feature Extraction and Embeddings 1](https://editor.analyticsvidhya.com/uploads/56750Extraction-using-Python.jpg)

_Source: https://www.analyticsvidhya.com/blog/2020/06/nlp-project-information-extraction/_

In this article, we will discuss the various methods of feature extraction and word embeddings practiced in Natural Language processing.

### Feature Extraction:

#### **Bag of Words:**

In this method, we take each document as a collection or bag having all the words in it. The idea is to analyze the documents. The document here refers to a unit. In case we want to find all the negative tweets during the pandemic, each tweet here is a document. To obtain the bag of words we always perform all those pre-requisite steps like cleaning, stemming, lemmatization, etc… Then we generate a set of all the words that are available before sending it for modeling.

“Tackling is the best part of football” -> { ‘tackle’, ‘best’, ‘part’, ‘football’ }

We can get repeated words within our document. A better representation is a vector form, that can tell us how many times each word can occur in a document. The following is called a document term matrix and is shown below:

![What is a term-document matrix? Feature Extraction and Embeddings](https://qph.fs.quoracdn.net/main-qimg-27639a9e2f88baab88a2c575a1de2005)

_Source: https://qphs.fs.quoracdn.net/main-qimg-27639a9e2f88baab88a2c575a1de2005_

It tells us about the relationship between a document and the terms. Each of the values in the table tells about the term frequency. To find the similarity, we go for the cosine similarity measure.

#### **TF-IDF:**

One problem that we encounter in the bag-of-words approach is that it treats every word equally, but in a document, there is a high chance of particular words being repeated more often than others. In a news report about Messi winning the Copa-America tournament, the word Messi would be more frequently repeated. We cannot give Messi the same weight as any other word in that document. In the news report, if we take each sentence as a document, we can count the number of documents each time Messi occurs. This method is called document-frequency.

We then divide the term frequency by the document frequency of that word. This helps us with the frequency of occurrence of terms in that document and inverse to the number of documents it appears in. Thus we have the TF-IDF. The idea is to assign particular weights to words that tell us about how important they are in the document.

![Feature Extraction and Embeddings TD-IDF](https://editor.analyticsvidhya.com/uploads/88298tfidf_ex3.png)

_Source: https://sci2lab.github.io/ml_tutorial/tfidf/_

#### **One-hot Encoding:**

For better analysis of the text we want to process, we must come up with a numerical representation of each word. This can be solved using the One-hot Encoding method. Here we treat each word as a class and in a document wherever the word is we assign 1 for it in the table and all other words in that document get 0. This is similar to the bag of words, but here we just keep each word in a bag.

![One-hot encoding Feature Extraction and Embeddings](https://editor.analyticsvidhya.com/uploads/856111_ArM6Z5jeptCQ082DYn9nDQ.png)

_Source:https://towardsdatascience.com/word-embedding-in-nlp-one-hot-encoding-and-skip-gram-neural-network-81b424da58f2_

### Word Embedding:

One-hot encoding works well when we have a small set of data. When there is a huge vocabulary, we can encode it using this method as the complexity increases a lot. We require a method that can control the size of the words we represent. We do this by limiting it to a fixed-sized vector. We want to find an embedding for each word. We want them to show us some properties. Like, if two words are similar they must be closer to each other in representation, and two opposite words if their pairs exist, they both must be having the same difference of distances. These help us find synonyms, analogies, etc…

![word Embeddings](https://editor.analyticsvidhya.com/uploads/450121_sAJdxEsDjsPMioHyzlN3_A.png)

_Source: https://miro.medium.com/max/1400/1*sAJdxEsDjsPMioHyzlN3_A.png_

#### **Word2Vec:**

Word2Vec is widely used in most of the NLP models. It transforms the word into vectors. Word2vec is a two-layer net that processes text with words. The input is in the text corpus and the output is a set of vectors: feature vectors represent the words on that corpus. While Word2vec is not a deep neural network, it converts text into an unambiguous form of computation for deep neural networks. The purpose and benefit of Word2vec are to collect vectors of the same words together in vector space. That is, it finds mathematical similarities. Word2vec creates vectors that are distributed by numerical presentations of word elements, features such as individual word context. It does so without human intervention.

Given enough data, usage, and conditions, Word2vec can make the most accurate predictions about the meaning of a word based on previous appearances. That guess can be used to form word-and-word combinations (eg “big” i.e. “large” to say “small” is “tiny”), or group texts and separate them by topic. Those collections can form the basis for the search, emotional analysis, and recommendations in various fields such as scientific research, legal discovery, e-commerce, and customer relationship management. The result of the Word2vec net is a glossary where each item has a vector attached to it, which can be embedded in an in-depth reading net or simply asked to find the relationship between the words.

Word2Vec can capture the contextual meaning of words very well. There are two flavors. In one of the methods, we are given the neighboring words called the continuous bag of words (CBoW), and in which we are given the middle word called skip-gram and we predict the neighboring words. Once we get a pre-trained set of weights we can save it and this can be used later for word vectorization without the need for transformation again. We store them on a lookup table.

![word2vec Feature Extraction and Embeddings](https://editor.analyticsvidhya.com/uploads/38289word2vec_diagrams.png)

_Source: https://wiki.pathmind.com/word2vec_

#### **GloVe:**

GloVe – global vector for word representation. An unsupervised learning algorithm by Stanford is used to generate embedding words by combining a word matrix for the word co-occurrence of matrix from the corpus. Emerging embedded text shows an attractive line format for a word in a vector space. The GloVe model is trained in the zero-level global co-occurrence matrix, which shows how often words meet in a particular corpus. Completing this matrix requires one pass per entire corporation to collect statistics. For a large corpus, this transaction may cost a computer, but it is a one-time expense in the future. Subsequent follow-up training is much faster because the number of non-matrix entries is usually much smaller than the total number of entries in the corpus.

The following is a visual representation of word embeddings:

![GloVe](https://editor.analyticsvidhya.com/uploads/619221_gcC7b_v7OKWutYN1NAHyMQ.png)

_Source: https://miro.medium.com/max/1400/1*gcC7b_v7OKWutYN1NAHyMQ.png_

### References:

1. Image – https://www.develandoo.com/blog/do-robots-read/
2. https://nlp.stanford.edu/projects/glove/
3. https://wiki.pathmind.com/word2vec
4. https://www.udacity.com/course/natural-language-processing-nanodegree–nd892

## Conclusion:

![NLP](https://editor.analyticsvidhya.com/uploads/214550_xjHCGhipvNmwp0wo.jpg)

_Source:https://medium.com/datatobiz/the-past-present-and-the-future-of-natural-language-processing-9f207821cbf6_

**About Me:** I am a Research Student interested in the field of Deep Learning and Natural Language Processing and currently pursuing post-graduation in Artificial Intelligence.
