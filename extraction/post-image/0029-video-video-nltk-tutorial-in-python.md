---
id: "29"
title: "(Vídeo) NLTK Tutorial in Python"
source_url: "https://www.youtube.com/watch?v=WYge0KZBhe0"
fetch_url: "https://www.youtube.com/watch?v=WYge0KZBhe0"
resolved_url: "https://www.youtube.com/watch?v=WYge0KZBhe0"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T05:31:01.384311Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "9838eb1331f4336fdb1a295c68fd0c7071c7d8343a9f62cdab507a8a5ad1bf37"
cache_keys:
  - "9838eb1331f4336fdb1a295c68fd0c7071c7d8343a9f62cdab507a8a5ad1bf37"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 519.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "404a280c4e39731ce2010fe5736c2f30d590dafbc6bff50f819f1722ef937883"
word_count: 2465
char_count: 14353
content_sha256: "1a9ebc66e4c0fc6e9b6b367a8966c1f947af3acc9af072ca9072aa1082777d9f"
image_count: 16
link_count: 0
total_token_count: 26099
estimated_input_tokens: 27911
warnings:
  - "title_mismatch"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes: []
---

## 00:00 Introduction to NLTK

**Spoken content:**
- [00:00] hello guys and welcome back to this video and this one we are going to install nltk and we are going
- [00:05] to see how we can use the nltk features such as the stemmer limitizer and all this kind of stuff
- [00:11] first of all nltk is a leading platform for by the building by some programs to work with the
- [00:15] human language it is you it is widely used for initial language processing and it has
- [00:20] a strong large corpora and lexical resources resources such as world net which we are going
- [00:26] to use later in this tutorial for limitizing and basically you cannot work in natural language
- [00:32] processing field without knowing about nltk so first of all we need to install it using

**On-screen content:**
![NLTK website homepage with description of NLTK, installation instructions, and NLTK data installation instructions](video-frame://00:00)

## 00:35 Installing NLTK

**Spoken content:**
- [00:36] bep install nltk so inside your terminal we're going to initiate the command bep install nltk
- [00:44] and of course because i have it here already it's going to tell me that it's already satisfied
- [00:51] and don't forget that you can apply this basically by having an explanation mark and
- [00:56] applying vip install nltk it have the same it will have the same result actually because
- [01:01] uh this is basically is the same as applying it to your terminal
- [01:05] so after installing nltk you need to install some corpora for example uh some data that it doesn't

**On-screen content:**
```bash
pip install nltk
```
![Terminal showing pip install nltk command and "Requirement already satisfied" message](video-frame://00:45)
```python
!pip install nltk
```
![Jupyter Notebook cell showing !pip install nltk command and "Requirement already satisfied" message](video-frame://00:59)

## 01:05 Installing NLTK Data

**Spoken content:**
- [01:12] come pre-installed with nltk because it has a large size so if you need instead if you need any
- [01:18] additional data on your nltk you have to start the nltk and then start nltk downloader so after
- [01:25] installing nltk you can initialize a python terminal inside your terminal or even inside your notebook and
- [01:32] then we're going to import nltk so we're going to import nltk so this line runs successfully so that's
- [01:41] mean that nltk is already installed and everything's fine so you can initialize the command nltk dot download
- [01:47] which is basically going to initialize some gui for you that you can install from it all the
- [01:52] packages that have in nltk you can see here this is the collections these are the corpora and these
- [01:58] are the models and all these are all the packages you can basically go here and install all the
- [02:02] packages if you have the enough space and you're going to deal with nltk for a large time and instead
- [02:08] you can just go through the corporate and install the corporate that you want the corporate that we're
- [02:12] going to need is wordnet so make sure you have wordnet installed and uh here we're going to
- [02:17] install it and of course it tells me that the package wordnet is up to date because i already
- [02:22] downloaded it so that's how you install ntk and its data so uh you have all of these documented here in
- [02:28] this notebook so if you needed to go back to it anytime you'll find it documented here

**On-screen content:**
![NLTK website showing instructions for NLTK data installation: import nltk, nltk.download()](video-frame://01:06)
![Terminal showing Python interpreter, import nltk, and nltk.download() command](video-frame://01:27)
![NLTK Downloader GUI with tabs for Collections, Corpora, Models, and All Packages. The Corpora tab is selected, showing a list of corpora with their identifiers, descriptions, sizes, and status. 'wordnet' is highlighted and shown as 'installed'.](video-frame://01:52)

## 02:33 Tokenization

**Spoken content:**
- [02:33] so let's get started first by import nltk in our notebook and have some text here the text here please
- [02:40] notice that the text here have wasn't which was which has a comma here and we're going to deal with
- [02:46] tokenizers first let's see the normal tokenizer the regix tokenizer that we have built before which was
- [02:51] surpassing uh the split function of the string and you can see here that we have wasn't as a single word
- [02:59] in some cases we need to interpret wasn't as two different words was and not because basically wasn't
- [03:06] and was uh we were treated differently but we need to have woes and not because then we can deal with
- [03:13] negation and we know that this woes is uh negated by the not so uh let's take a look at the tokenizer
- [03:21] of the nltk we have nltk dot wood tokenize so let's see the output of it and you can see here that
- [03:27] woes and not are separated woes and not are different tokens and this can be very useful in some cases so
- [03:34] first we have a word tokenizer that is better than the normal tokenizer and of course you can see here
- [03:39] that the empty set is not included in the words so you only have tokens that are actual tokens and not
- [03:45] empty space now into stemming to apply stemming there are multiple algorithms for stemming in ltk

**On-screen content:**
```python
import nltk
text = "Monticello wasn't designated as UNESCO World Heritage Site until 1987"
```
![Jupyter Notebook cell with import nltk and text variable definition](video-frame://02:35)

```python
import regex
regex.split(r'[\s\.,\']', text)
```
**Output:**
```
['Monticello', "wasn't", 'designated', 'as', 'UNESCO', 'World', 'Heritage', 'Site', 'until', '1987', '']
```
![Jupyter Notebook cell showing regex tokenizer code and its output](video-frame://02:47)

```python
nltk.word_tokenize(text)
```
**Output:**
```
['Monticello', 'was', "n't", 'designated', 'as', 'UNESCO', 'World', 'Heritage', 'Site', 'until', '1987']
```
![Jupyter Notebook cell showing nltk.word_tokenize code and its output](video-frame://03:20)

## 03:46 Stemming with Porter Stemmer

**Spoken content:**
- [03:51] and in general the portrait steamer is the steamer that we have talked about in the previous tutorial
- [03:56] which basically applies some rules like you're moving some additional characters and you're using
- [04:00] some different characters so the rules for portrait simmer can be found here uh it is all documented in the
- [04:07] nltk because it's an open source library so you can find all the code um and you can go through it
- [04:13] simply so to use the portrait simmer we're going to import the portrait simmer from nltk.stem and we're
- [04:18] going to initialize an object just some object here we have some words some plural words and we're going
- [04:24] to see what the steamer is going to apply to them and you can see here this is this is a different way
- [04:30] of defining strings when you have some variables and you need to include these variables inside the
- [04:34] string you just use an f in front of your string and this is basically means that this string is going
- [04:39] to be a formatted string and by having career places we're going to define variables inside the
- [04:44] string and these variables are going to call the variables themselves here so here we're going to
- [04:48] have word and uh this another character places we have going to have the steamer dot stem which is the
- [04:54] function that basically stem our string and we're going to pass the word so applying this still we're going to
- [05:00] have each word and each its corresponding stem so you can see here that it indeed apply the rule
- [05:07] which which basically was saying that if we have ses we're going to reduce it into a single s and we
- [05:13] have ies we reduce it into i and all these kind of rules that we have talked we we have looked into
- [05:20] these rules in the previous tutorial and you can double check it here in this so that's how you use the
- [05:26] the stemmer the porter stemmer there is another stemmer that is called the snowboard snowball stemmer

**On-screen content:**
```python
from nltk.stem import PorterStemmer
stemmer = PorterStemmer()
plurals = ['caresses', 'flies', 'mules', 'dies', 'denied', 'died',
           'agreed', 'owned', 'humbled', 'sized', 'meeting', 'stating',
           'siezing', 'itemization', 'sensational', 'traditional', 'reference',
           'colonizer', 'plotted']

for word in plurals:
    print(f"{word} >>> {stemmer.stem(word)}")
```
**Output:**
```
caresses >>> caress
flies >>> fli
mules >>> mule
dies >>> die
denied >>> deni
died >>> die
agreed >>> agre
owned >>> own
humbled >>> humbl
sized >>> size
meeting >>> meet
stating >>> state
siezing >>> siez
itemization >>> item
sensational >>> sensat
traditional >>> tradit
reference >>> refer
colonizer >>> colon
plotted >>> plot
```
![Jupyter Notebook cell showing Porter Stemmer code and its output](video-frame://04:14)

## 05:27 Stemming with Snowball Stemmer

**Spoken content:**
- [05:31] one of the advantages of snowball uh stemmer over the portrait stemmer is that it supports different
- [05:37] languages and you can check the languages that the snowboard stemmer support using the snowboard
- [05:43] stemmer the languages and you can see here it has arabic danish jewish english uh french german italian all
- [05:50] these kind of languages you can use and you can see it has the porter stemmer which is basically an
- [05:54] english stemmer which is this stemmer so let's initialize our stemmer we're going to initialize
- [06:00] it and we need to pass the language that we're going to be using and indeed it's going to be the english so
- [06:06] here we have the sn stemmer so let's apply the cell and let's take a look at the uh the output of these
- [06:11] cells basically most of the time the snowball stemmer and the porter stemmer have similar results but in some
- [06:18] cases the snowball stemmer um is better in most of the cases the snowball stemmer will be better let's
- [06:24] take a look at this one we have here the sn stemmer and we're going to stem the generously word take a
- [06:29] look at the stem it's generous what about the stemmer the portrait stemmer if we use the portrait
- [06:34] stemmer we're going to have it into a general because it's going to just remove all these uh text
- [06:40] so snowball stemmer and portrait stemmer are similar similar but the snowball stemmer most of the time have
- [06:45] better results so it might be better to go into snowball stemmer um most of the time so into

**On-screen content:**
```python
from nltk.stem.snowball import SnowballStemmer
SnowballStemmer.languages
```
**Output:**
```
('arabic', 'danish', 'dutch', 'english', 'finnish', 'french', 'german', 'hungarian', 'italian', 'norwegian', 'porter', 'portuguese', 'romanian', 'russian', 'spanish', 'swedish')
```
![Jupyter Notebook cell showing Snowball Stemmer languages code and its output](video-frame://05:30)

```python
sn_stemmer = SnowballStemmer('english')
```
![Jupyter Notebook cell initializing SnowballStemmer for English](video-frame://05:57)

```python
sn_stemmer.stem("generously")
```
**Output:**
```
'generous'
```
![Jupyter Notebook cell showing Snowball Stemmer stemming "generously" to "generous"](video-frame://06:09)

```python
stemmer.stem("generously")
```
**Output:**
```
'gener'
```
![Jupyter Notebook cell showing Porter Stemmer stemming "generously" to "gener"](video-frame://06:31)

## 06:51 Lemmatization

**Spoken content:**
- [06:51] limitizing and as we said in the previous tutorial limitizing is about reducing the word into its root
- [06:57] to do so we have to have a like a tree bank or a knowledge bank that have all the word and words and
- [07:05] its roots and this is called the wordnet so here we have wordnet limitizer in ltk um that's why we installed and
- [07:13] download the wordnet the wordnet corpora from the ltk download so initialize the wordnet limitizer
- [07:20] using a wordnet limitizer class and let's take a look at the uh limitization of all the plurus words
- [07:27] that we have defined um here and let's take a look at this and flies have been reduced into fly dies have been
- [07:37] reduced into die and um this might be a little bit weird but this is the root as limitizing seeds and
- [07:43] uh you can see here not all the cases are good but most of the case not all the cases are good but uh
- [07:50] each anywhere that it has already root for it it will be reduced into a web so in summary what we have

**On-screen content:**
```python
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()

for word in plurals:
    print(f"{word} >>> {lemmatizer.lemmatize(word)}")
```
**Output:**
```
caresses >>> caress
flies >>> fly
mules >>> mule
dies >>> die
denied >>> denied
died >>> died
agreed >>> agreed
owned >>> owned
humbled >>> humbled
sized >>> sized
meeting >>> meeting
stating >>> stating
siezing >>> siezing
itemization >>> itemization
sensational >>> sensational
traditional >>> traditional
reference >>> reference
colonizer >>> colonizer
plotted >>> plotted
```
![Jupyter Notebook cell showing WordNetLemmatizer code and its output](video-frame://07:09)

## 07:55 Summary and Next Steps

**Spoken content:**
- [07:55] done in this tutorial we have downloaded and installed nltk and we also know how to download nltk data
- [08:02] we now know how to use the nltk tokenizer and how it is better than the regix tokenizer we know how we
- [08:09] now know how to deal with nltk stemmers how to stem words both in portrait stemmer and snowball
- [08:15] stemmer and also in different languages because we have different languages in the snowball stemmer we
- [08:20] know also how to use the wordnet limitizer from uh nltk so that's it for this video in the next video we're
- [08:27] going to deal with different kind of features for our text specifically the the boss tags and the
- [08:33] parsing tree and we're going to see how we can apply these into our text so see you guys in the next one

**On-screen content:**
![Summary section with bullet points: How to install NLTK and its data, How to use NLTK tokenizers, NLTK stemmers, NLTK lemmatizers](video-frame://07:55)
