---
id: "23"
title: "An introduction to Bag of Words and how to code it in Python for NLP"
source_url: "https://www.freecodecamp.org/news/an-introduction-to-bag-of-words-and-how-to-code-it-in-python-for-nlp-282e87a9da04"
fetch_url: "https://www.freecodecamp.org/news/an-introduction-to-bag-of-words-and-how-to-code-it-in-python-for-nlp-282e87a9da04"
resolved_url: "https://www.freecodecamp.org/news/an-introduction-to-bag-of-words-and-how-to-code-it-in-python-for-nlp-282e87a9da04"
firecrawl_title: "An introduction to Bag of Words and how to code it in Python for NLP"
description: "By Praveen Dubey Bag of Words (BOW) is a method to extract features from text documents. These features can be used for training machine learning algorithms. It creates a vocabulary of all the unique words occurring in all the documents in the traini..."
fetched_at: "2026-05-12T03:59:51.394131Z"
provider: "firecrawl"
strategy: "standard"
cache_key: "cc5cd6e0ac7c41081a433044de92932772cff1d4c608cd9bd1840c374eaa6be5"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 1608
char_count: 9695
content_sha256: "0ab01571cdca835a8648a53d81c4d663697e8e34ee356270b75ce1efb7005113"
image_count: 4
link_count: 9
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

# Learn to code — free 3,000-hour curriculum

![An introduction to Bag of Words and how to code it in Python for NLP](https://cdn-media-1.freecodecamp.org/images/1*dcFrKbfBRJzm514gaxp4YA.jpeg)

By Praveen Dubey

Bag of Words (BOW) is a method to extract features from text documents. These features can be used for training machine learning algorithms. It creates a vocabulary of all the unique words occurring in all the documents in the training set.

**In simple terms, it’s a collection of words to represent a sentence with word count and mostly disregarding the order in which they appear.**

BOW is an approach widely used with:

1. Natural language processing
2. Information retrieval from documents
3. Document classifications

On a high level, it involves the following steps.

![Image](https://cdn-media-1.freecodecamp.org/images/qRGh8boBcLLQfBvDnWTXKxZIEAk5LNfNABHF)

**Generated vectors can be input to your machine learning algorithm.**

Let’s start with an example to understand by taking some sentences and generating vectors for those.

Consider the below two sentences.

```
1. "John likes to watch movies. Mary likes movies too."
```

```
2. "John also likes to watch football games."
```

These two sentences can be also represented with a collection of words.

```
1. ['John', 'likes', 'to', 'watch', 'movies.', 'Mary', 'likes', 'movies', 'too.']
```

```
2. ['John', 'also', 'likes', 'to', 'watch', 'football', 'games']
```

Further, for each sentence, remove multiple occurrences of the word and use the word count to represent this.

```
1. {"John":1,"likes":2,"to":1,"watch":1,"movies":2,"Mary":1,"too":1}
```

```
2. {"John":1,"also":1,"likes":1,"to":1,"watch":1,"football":1,   "games":1}
```

Assuming these sentences are part of a document, below is the combined word frequency for our entire document. Both sentences are taken into account.

```
{"John":2,"likes":3,"to":2,"watch":2,"movies":2,"Mary":1,"too":1,  "also":1,"football":1,"games":1}
```

The above vocabulary from all the words in a document, with their respective word count, will be used to create the vectors for each of the sentences.

**The length of the vector will always be equal to vocabulary size. In this case the vector length is 11.**

In order to represent our original sentences in a vector, each vector is initialized with all zeros — **[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]**

This is followed by iteration and comparison with each word in our vocabulary, and incrementing the vector value if the sentence has that word.

```
John likes to watch movies. Mary likes movies too.[1, 2, 1, 1, 2, 1, 1, 0, 0, 0]
```

```
John also likes to watch football games.[1, 1, 1, 1, 0, 0, 0, 1, 1, 1]
```

For example, in sentence 1 the word `likes` appears in second position and appears two times. So the second element of our vector for sentence 1 will be 2: **[1, 2, 1, 1, 2, 1, 1, 0, 0, 0]**

The vector is always proportional to the size of our vocabulary.

A big document where the generated vocabulary is huge may result in a vector with lots of 0 values. This is called a **sparse vector**. Sparse vectors require more memory and computational resources when modeling. The vast number of positions or dimensions can make the modeling process very challenging for traditional algorithms.

### Coding our BOW algorithm

The input to our code will be multiple sentences and the output will be the vectors.

The input array is this:

```
["Joe waited for the train", "The train was late", "Mary and Samantha took the bus",
"I looked for Mary and Samantha at the bus station",
"Mary and Samantha arrived at the bus station early but waited until noon for the bus"]
```

#### Step 1: Tokenize a sentence

We will start by removing stopwords from the sentences.

**Stopwords** are words which do not contain enough significance to be used without our algorithm. We would not want these words taking up space in our database, or taking up valuable processing time. For this, we can remove them easily by storing a list of words that you consider to be stop words.

**Tokenization** is the act of breaking up a sequence of strings into pieces such as words, keywords, phrases, symbols and other elements called **tokens**. Tokens can be individual words, phrases or even whole sentences. In the process of tokenization, some characters like punctuation marks are discarded.

```
def word_extraction(sentence):
    ignore = ['a', "the", "is"]
    words = re.sub("[^\\w]", " ",  sentence).split()
    cleaned_text = [w.lower() for w in words if w not in ignore]
    return cleaned_text
```

For more robust implementation of stopwords, you can use python **nltk** library. It has a set of predefined words per language. Here is an example:

```
import nltk
from nltk.corpus import stopwords
set(stopwords.words('english'))
```

#### Step 2: Apply tokenization to all sentences

```
def tokenize(sentences):
    words = []
    for sentence in sentences:
        w = word_extraction(sentence)
        words.extend(w)
    words = sorted(list(set(words)))
    return words
```

The method iterates all the sentences and adds the extracted word into an array.

The output of this method will be:

```
['and', 'arrived', 'at', 'bus', 'but', 'early', 'for', 'i', 'joe', 'late', 'looked', 'mary', 'noon', 'samantha', 'station', 'the', 'took', 'train', 'until', 'waited', 'was']
```

#### Step 3: Build vocabulary and generate vectors

Use the methods defined in steps 1 and 2 to create the document vocabulary and extract the words from the sentences.

```
def generate_bow(allsentences):
    vocab = tokenize(allsentences)
    print("Word List for Document \n{0} \n".format(vocab));
    for sentence in allsentences:
        words = word_extraction(sentence)
        bag_vector = numpy.zeros(len(vocab))
        for w in words:
            for i,word in enumerate(vocab):
                if word == w:
                     bag_vector[i] += 1
        print("{0}\n{1}\n".format(sentence,numpy.array(bag_vector)))
```

Here is the defined input and execution of our code:

```
allsentences = ["Joe waited for the train train", "The train was late", "Mary and Samantha took the bus",
"I looked for Mary and Samantha at the bus station",
"Mary and Samantha arrived at the bus station early but waited until noon for the bus"]
```

```
generate_bow(allsentences)
```

The output vectors for each of the sentences are:

```
Output:
```

```
Joe waited for the train train[0. 0. 0. 0. 0. 0. 1. 0. 1. 0. 0. 0. 0. 0. 0. 0. 0. 2. 0. 1. 0.]
```

```
The train was late[0. 0. 0. 0. 0. 0. 0. 0. 0. 1. 0. 0. 0. 0. 0. 1. 0. 1. 0. 0. 1.]
```

```
Mary and Samantha took the bus[1. 0. 0. 1. 0. 0. 0. 0. 0. 0. 0. 1. 0. 1. 0. 0. 1. 0. 0. 0. 0.]
```

```
I looked for Mary and Samantha at the bus station[1. 0. 1. 1. 0. 0. 1. 1. 0. 0. 1. 1. 0. 1. 1. 0. 0. 0. 0. 0. 0.]
```

```
Mary and Samantha arrived at the bus station early but waited until noon for the bus[1. 1. 1. 2. 1. 1. 1. 0. 0. 0. 0. 1. 1. 1. 1. 0. 0. 0. 1. 1. 0.]
```

As you can see, **each sentence was compared with our word list generated in Step 1. Based on the comparison, the vector element value may be incremented**. These vectors can be used in ML algorithms for document classification and predictions.

We wrote our code and generated vectors, but now let’s understand bag of words a bit more.

### Insights into bag of words

The BOW model only considers if a known word occurs in a document or not. It does not care about meaning, context, and order in which they appear.

This gives the insight that similar documents will have word counts similar to each other. In other words, the more similar the words in two documents, the more similar the documents can be.

### Limitations of BOW

1. **Semantic meaning**: the basic BOW approach does not consider the meaning of the word in the document. It completely ignores the context in which it’s used. The same word can be used in multiple places based on the context or nearby words.
2. **Vector size**: For a large document, the vector size can be huge resulting in a lot of computation and time. You may need to ignore words based on relevance to your use case.

This was a small introduction to the BOW method. The code showed how it works at a low level. There is much more to understand about BOW. For example, instead of splitting our sentence in a single word (1-gram), you can split in the pair of two words (bi-gram or 2-gram). At times, bi-gram representation seems to be much better than using 1-gram. These can often be represented using N-gram notation. I have listed some research papers in the resources section for more in-depth knowledge.

You do not have to code BOW whenever you need it. It is already part of many available frameworks like CountVectorizer in sci-kit learn.

Our previous code can be replaced with:

```
from sklearn.feature_extraction.text import CountVectorizer
vectorizer = CountVectorizer()
X = vectorizer.fit_transform(allsentences)
print(X.toarray())
```

It’s always good to understand how the libraries in frameworks work, and understand the methods behind them. The better you understand the concepts, the better use you can make of frameworks.

**Thanks for reading the article. The code shown is available on my [GitHub](https://gist.github.com/edubey/c52a3b34541456a76a2c1f81eebb5f67).**

### **Resources to read more on bag of words**

1. [Wikipedia-BOW](https://en.wikipedia.org/wiki/Bag-of-words_model)
2. [Understanding Bag-of-Words Model: A Statistical Framework](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.453.5924&rep=rep1&type=pdf)
3. [Semantics-Preserving Bag-of-Words Models and Applications](https://ieeexplore.ieee.org/document/5428847)
