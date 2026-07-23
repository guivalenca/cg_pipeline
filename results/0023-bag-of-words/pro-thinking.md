# Source Fragment Extraction — DeepSeek V4 Pro

- **Source:** `0023-an-introduction-to-bag-of-words-and-how-to-code-it-in-python-for-nlp.md`
- **Model:** `deepseek-v4-pro`
- **Thinking:** on (high)
- **Generated:** 2026-07-14T18:37:03.951235+00:00
- **Latency:** 101.1 seconds
- **Usage:** Prompt: 5640; completion: 7616; total: 13256
- **Fragments:** 24

## Fragment 1

Bag of Words (BOW) is a method to extract features from text documents for training machine learning algorithms; it creates a vocabulary of all the unique words occurring in all the documents in the training set.

**Evidence:** L007–L007

```text
[L007] Bag of Words (BOW) is a method to extract features from text documents. These features can be used for training machine learning algorithms. It creates a vocabulary of all the unique words occurring in all the documents in the training set.
```

## Fragment 2

In simple terms, BOW represents a sentence as a collection of words with their counts, mostly disregarding the order in which they appear.

**Evidence:** L009–L009

```text
[L009] **In simple terms, it’s a collection of words to represent a sentence with word count and mostly disregarding the order in which they appear.**
```

## Fragment 3

BOW is an approach widely used with natural language processing, information retrieval from documents, and document classifications.

**Evidence:** L011–L015

```text
[L011] BOW is an approach widely used with:
[L012] 
[L013] 1. Natural language processing
[L014] 2. Information retrieval from documents
[L015] 3. Document classifications
```

## Fragment 4

At a high level, the BOW pipeline involves cleaning text, tokenizing, building a vocabulary, and generating vectors.

**Evidence:** L017–L019

```text
[L017] On a high level, it involves the following steps.
[L018] 
[L019] Image summary: A left-to-right workflow diagram shows the Bag of Words pipeline: clean text, tokenize, build vocabulary, and generate vectors. It emphasizes that text is first normalized, then split into tokens, then converted into a vocabulary, and finally represented as vectors. [Original image: Image](https://cdn-media-1.freecodecamp.org/images/qRGh8boBcLLQfBvDnWTXKxZIEAk5LNfNABHF)
```

## Fragment 5

Generated BOW vectors can be input to a machine learning algorithm.

**Evidence:** L021–L021

```text
[L021] **Generated vectors can be input to your machine learning algorithm.**
```

## Fragment 6

Sentences can be initially represented as a collection (list) of individual words.

**Evidence:** L035–L043

```text
[L035] These two sentences can be also represented with a collection of words.
[L036] 
[L037] ```
[L038] 1. ['John', 'likes', 'to', 'watch', 'movies.', 'Mary', 'likes', 'movies', 'too.']
[L039] ```
[L040] 
[L041] ```
[L042] 2. ['John', 'also', 'likes', 'to', 'watch', 'football', 'games']
[L043] ```
```

## Fragment 7

For each sentence, multiple occurrences of a word are replaced with a word count, producing a dictionary that maps each word to its frequency in that sentence.

**Evidence:** L045–L053

```text
[L045] Further, for each sentence, remove multiple occurrences of the word and use the word count to represent this.
[L046] 
[L047] ```
[L048] 1. {"John":1,"likes":2,"to":1,"watch":1,"movies":2,"Mary":1,"too":1}
[L049] ```
[L050] 
[L051] ```
[L052] 2. {"John":1,"also":1,"likes":1,"to":1,"watch":1,"football":1,   "games":1}
[L053] ```
```

## Fragment 8

The combined word frequency across all sentences in a document forms the vocabulary; each sentence is then represented as a vector whose length equals the vocabulary size.

**Evidence:** L055–L063

```text
[L055] Assuming these sentences are part of a document, below is the combined word frequency for our entire document. Both sentences are taken into account.
[L056] 
[L057] ```
[L058] {"John":2,"likes":3,"to":2,"watch":2,"movies":2,"Mary":1,"too":1,  "also":1,"football":1,"games":1}
[L059] ```
[L060] 
[L061] The above vocabulary from all the words in a document, with their respective word count, will be used to create the vectors for each of the sentences.
[L062] 
[L063] **The length of the vector will always be equal to vocabulary size. In this case the vector length is 11.**
```

## Fragment 9

To create a BOW vector for a sentence, initialize all positions to zero, then iterate through each word in the vocabulary, incrementing the value at the corresponding position if the sentence contains that word.

**Evidence:** L065–L067

```text
[L065] In order to represent our original sentences in a vector, each vector is initialized with all zeros — **[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]**
[L066] 
[L067] This is followed by iteration and comparison with each word in our vocabulary, and incrementing the vector value if the sentence has that word.
```

## Fragment 10

A large vocabulary results in a sparse vector with many zero values; sparse vectors require more memory and computational resources, and the vast number of dimensions can make modeling very challenging for traditional algorithms.

**Evidence:** L079–L081

```text
[L079] The vector is always proportional to the size of our vocabulary.
[L080] 
[L081] A big document where the generated vocabulary is huge may result in a vector with lots of 0 values. This is called a **sparse vector**. Sparse vectors require more memory and computational resources when modeling. The vast number of positions or dimensions can make the modeling process very challenging for traditional algorithms.
```

## Fragment 11

The input to a BOW algorithm is multiple sentences and the output is the vectors.

**Evidence:** L085–L085

```text
[L085] The input to our code will be multiple sentences and the output will be the vectors.
```

## Fragment 12

Stopwords are words that do not contain enough significance to be used in the algorithm; they can be removed by storing a list of words considered to be stop words.

**Evidence:** L099–L099

```text
[L099] **Stopwords** are words which do not contain enough significance to be used without our algorithm. We would not want these words taking up space in our database, or taking up valuable processing time. For this, we can remove them easily by storing a list of words that you consider to be stop words.
```

## Fragment 13

Tokenization is the act of breaking up a sequence of strings into pieces called tokens (such as words, keywords, phrases, and symbols); tokens can be individual words, phrases, or whole sentences, and punctuation marks are typically discarded in the process.

**Evidence:** L101–L101

```text
[L101] **Tokenization** is the act of breaking up a sequence of strings into pieces such as words, keywords, phrases, symbols and other elements called **tokens**. Tokens can be individual words, phrases or even whole sentences. In the process of tokenization, some characters like punctuation marks are discarded.
```

## Fragment 14

A Python word_extraction function can implement tokenization and stopword removal by using a regex to replace non-word characters with spaces, splitting on whitespace, lowercasing all words, and filtering out words present in a predefined ignore list.

**Evidence:** L104–L108

```text
[L104] def word_extraction(sentence):
[L105]     ignore = ['a', "the", "is"]
[L106]     words = re.sub("[^\\w]", " ",  sentence).split()
[L107]     cleaned_text = [w.lower() for w in words if w not in ignore]
[L108]     return cleaned_text
```

## Fragment 15

For more robust stopword removal, the Python nltk library provides predefined sets of stopwords per language, accessible via nltk.corpus.stopwords.

**Evidence:** L111–L117

```text
[L111] For more robust implementation of stopwords, you can use python **nltk** library. It has a set of predefined words per language. Here is an example:
[L112] 
[L113] ```
[L114] import nltk
[L115] from nltk.corpus import stopwords
[L116] set(stopwords.words('english'))
[L117] ```
```

## Fragment 16

A tokenize function can iterate over all sentences, extract words from each using word_extraction, collect them, and return a sorted list of unique words.

**Evidence:** L122–L128

```text
[L122] def tokenize(sentences):
[L123]     words = []
[L124]     for sentence in sentences:
[L125]         w = word_extraction(sentence)
[L126]         words.extend(w)
[L127]     words = sorted(list(set(words)))
[L128]     return words
```

## Fragment 17

A generate_bow function builds the vocabulary via tokenize, then for each sentence creates a zero-filled NumPy array of vocabulary length and increments the count at each vocabulary position that matches a word in the sentence, outputting the resulting vector.

**Evidence:** L144–L154

```text
[L144] def generate_bow(allsentences):
[L145]     vocab = tokenize(allsentences)
[L146]     print("Word List for Document \n{0} \n".format(vocab));
[L147]     for sentence in allsentences:
[L148]         words = word_extraction(sentence)
[L149]         bag_vector = numpy.zeros(len(vocab))
[L150]         for w in words:
[L151]             for i,word in enumerate(vocab):
[L152]                 if word == w:
[L153]                      bag_vector[i] += 1
[L154]         print("{0}\n{1}\n".format(sentence,numpy.array(bag_vector)))
```

## Fragment 18

The BOW model only considers whether a known word occurs in a document; it does not consider meaning, context, or the order in which words appear.

**Evidence:** L201–L201

```text
[L201] The BOW model only considers if a known word occurs in a document or not. It does not care about meaning, context, and order in which they appear.
```

## Fragment 19

Similar documents will have word counts similar to each other; the more similar the words in two documents, the more similar the documents can be.

**Evidence:** L203–L203

```text
[L203] This gives the insight that similar documents will have word counts similar to each other. In other words, the more similar the words in two documents, the more similar the documents can be.
```

## Fragment 20

A limitation of BOW is that it does not consider semantic meaning or context; the same word can be used differently in multiple places based on context or nearby words.

**Evidence:** L207–L207

```text
[L207] 1. **Semantic meaning**: the basic BOW approach does not consider the meaning of the word in the document. It completely ignores the context in which it’s used. The same word can be used in multiple places based on the context or nearby words.
```

## Fragment 21

A limitation of BOW is vector size: for a large document, the vector size can be huge, resulting in significant computation and time; you may need to ignore words based on relevance to the use case.

**Evidence:** L208–L208

```text
[L208] 2. **Vector size**: For a large document, the vector size can be huge resulting in a lot of computation and time. You may need to ignore words based on relevance to your use case.
```

## Fragment 22

Instead of splitting sentences into single words (1-gram), BOW can use pairs of two words (bi-gram or 2-gram) or general N-gram representations; bi-gram representation can perform better than 1-gram.

**Evidence:** L210–L210

```text
[L210] This was a small introduction to the BOW method. The code showed how it works at a low level. There is much more to understand about BOW. For example, instead of splitting our sentence in a single word (1-gram), you can split in the pair of two words (bi-gram or 2-gram). At times, bi-gram representation seems to be much better than using 1-gram. These can often be represented using N-gram notation. I have listed some research papers in the resources section for more in-depth knowledge.
```

## Fragment 23

BOW is already available in frameworks such as scikit-learn's CountVectorizer, which can replace custom BOW code with a call to CountVectorizer().fit_transform(sentences) to produce the vector array.

**Evidence:** L212–L220

```text
[L212] You do not have to code BOW whenever you need it. It is already part of many available frameworks like CountVectorizer in sci-kit learn.
[L213] 
[L214] Our previous code can be replaced with:
[L215] 
[L216] ```
[L217] from sklearn.feature_extraction.text import CountVectorizer
[L218] vectorizer = CountVectorizer()
[L219] X = vectorizer.fit_transform(allsentences)
[L220] print(X.toarray())
```

## Fragment 24

Understanding the concepts and methods behind library implementations allows better use of frameworks.

**Evidence:** L223–L223

```text
[L223] It’s always good to understand how the libraries in frameworks work, and understand the methods behind them. The better you understand the concepts, the better use you can make of frameworks.
```
