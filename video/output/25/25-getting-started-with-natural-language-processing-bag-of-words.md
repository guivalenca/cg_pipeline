---
id: "25"
title: "Getting started with Natural Language Processing: Bag of words"
source_url: "https://www.youtube.com/watch?v=UFtXy0KRxVI"
fetch_url: "https://www.youtube.com/watch?v=UFtXy0KRxVI"
resolved_url: "https://www.youtube.com/watch?v=UFtXy0KRxVI"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T05:48:07.829229Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "ca9c924ba182d4b33f93c38decf648a4d384eb32daaefacba6059723410458c7"
cache_keys:
  - "ca9c924ba182d4b33f93c38decf648a4d384eb32daaefacba6059723410458c7"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 386.0
transcript_source: "manual_captions"
transcript_sha256: "cdc7c4ae4f791dc9555ec3fdd570a3fd7b57c342a5094709a2940180eae5e12f"
word_count: 1952
char_count: 11301
content_sha256: "2f993f9ed3b81cc4da340055e94c1216dca10166cf74f047706659afda2ddece"
image_count: 12
link_count: 0
total_token_count: 26830
estimated_input_tokens: 20759
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Natural Language Processing Challenges

**Spoken content:**
- [00:00] YUFENG GUO: Natural language has many challenges that are unique
- [00:04] and separate it from other data types like images
- [00:07] and structured data.
- [00:08] So it requires a slightly different approach.
- [00:12] Today, we'll explore a foundational piece
- [00:15] of modeling natural language, called "bag of words."
- [00:18] What does it mean?
- [00:19] And how do we use it to process text?
- [00:22] Stay tuned to find out.
- [00:25] [THEME SONG]

**On-screen content:**
![Yufeng Guo speaking in front of a white background, wearing a grey t-shirt with the Google Cloud logo](video-frame://25@00:00)

## [00:29] AI Adventures: Getting Started with Natural Language Processing: Bag of Words

**Spoken content:**
- [00:32] Welcome to "AI Adventures," where
- [00:34] we explore the art, science, and tools of machine learning.
- [00:38] My name is Yufeng Guo.
- [00:39] And on this episode, we're going to look
- [00:42] at how to use bag of words to classify natural language.

**On-screen content:**
![Title card: AI Adventures, Getting started with Natural Language Processing: Bag of words, Yufeng Guo @YufengG](video-frame://25@00:29)

## [00:46] The Special Nature of Natural Language

**Spoken content:**
- [00:47] Natural language is special because it
- [00:49] has structure inherent in the language while at the same time
- [00:53] being very free-form.
- [00:55] There are many ways you can say the same thing.
- [00:58] And you can also say very similar words,
- [01:00] and yet mean very different things.
- [01:03] So in much of machine learning, we

**On-screen content:**
![Slide: Natural language. Examples of sentences with subtle differences in meaning based on word choice or emphasis, such as "I never said my dog ate my homework." and "What were you thinking? 🤨 What were you thinking? 🤯"](video-frame://25@00:46)

## [01:03] Converting Data to Matrices

**Spoken content:**
- [01:05] aim to turn our data into matrices or tensors.
- [01:09] This is very natural for images since that's already
- [01:12] their inherent representation.
- [01:14] Structured data often meets a similar fate,
- [01:17] with numbers in a spreadsheet mapping very directly to input
- [01:21] matrix values.
- [01:22] But with natural language, we need
- [01:25] to somehow find a way to turn words into numbers so we can

**On-screen content:**
![Slide: Data -> Matrices. An image of a cat is shown with its Red, Green, and Blue color channels represented as matrices of numbers.](video-frame://25@01:03)

## [01:29] Bag of Words: Encoding Free-Form Text

**Spoken content:**
- [01:30] stick them into those matrices.
- [01:32] There are many ways that we can do this.
- [01:34] And today, we'll focus on an approach called "bag of words."

**On-screen content:**
![Slide: Bag of words: encoding free form text. A cloth bag filled with Scrabble tiles is shown.](video-frame://25@01:29)

## [01:39] Understanding Bag of Words with a Vocabulary Example

**Spoken content:**
- [01:40] Let's pretend for a moment that we're learning English
- [01:42] for the first time ever.
- [01:44] And for some reason, the first words
- [01:48] we have chosen to learn in our entire vocabulary
- [01:51] are these 10 shown here--
- [01:53] words like "dataframe" and "graph," "plot," "color,"
- [01:57] and "activation."
- [01:58] And so we want to be able to identify,
- [02:01] given some arbitrary text, whether that topic
- [02:05] is about pandas, keras, or Matplotlib.

**On-screen content:**
![Slide: Bag of words: Vocabulary. A list of 10 words: dataframe, layer, series, graph, column, plot, color, axes, read_csv, activation.](video-frame://25@01:39)
![Slide: Bag of words: Vocabulary and Possible labels. The vocabulary list is on the left, and a list of possible labels (pandas, keras, matplotlib) is on the right.](video-frame://25@02:04)

## [02:10] Processing an Input Sentence with Bag of Words

**Spoken content:**
- [02:10] How might we do that?
- [02:13] Perhaps if we looked at a sentence, like "how
- [02:16] to plot dataframe bar graph," we would
- [02:19] recognize just the words "plot," "dataframe," and "graph."
- [02:23] The rest of the sentence would look like a foreign language,
- [02:27] just gibberish.
- [02:28] Knowing only those three words in this sentence,
- [02:30] though, we might still be able to get
- [02:33] some sense of what it's about.

**On-screen content:**
![Slide: Bag of words: Inputs and Vocabulary. An input sentence "how to plot dataframe bar graph" is shown. The vocabulary list is on the right.](video-frame://25@02:10)

## [02:35] Encoding the Sentence into an Array

**Spoken content:**
- [02:36] And the way you might capture this information in an array
- [02:40] or matrix would be to first make an array that represents
- [02:44] your entire vocabulary.
- [02:45] So in this case, we have an array of just length 10.
- [02:48] We'd set all those values to 0 and turn
- [02:52] on the array indices that correspond
- [02:54] to the words in the sentence by setting them to 1.
- [02:57] Notice that this has nothing to do with the order
- [03:00] the words appear in the input sentence,
- [03:03] but everything to do with the order of the words
- [03:06] in our vocabulary list.
- [03:08] So now we've encoded or translated the English sentence
- [03:13] into an array of numbers based on our somewhat limited
- [03:17] understanding of English.
- [03:20] The words we don't recognize, we'll just ignore.
- [03:23] Notice that this has the effect of scrambling up
- [03:25] the order of the words, like, say, a bag of words.

**On-screen content:**
![Slide: Bag of words: Inputs and Vocabulary. The input sentence "how to plot dataframe bar graph" is shown with arrows pointing to the corresponding words in the vocabulary list (dataframe, plot, graph). Below, a binary array `[1 0 0 1 0 0 1 0 0 0]` represents the presence of these words in the vocabulary.](video-frame://25@02:48)

## [03:29] Preprocessing Labels for Prediction

**Spoken content:**
- [03:30] Of course, we should do the same for our labels.
- [03:33] This is much simpler, since there are only three of them.
- [03:37] In our case, we have some sentences
- [03:39] that have more than one label attached
- [03:41] to them at the same time, however,
- [03:43] since a sentence can talk about multiple topics at once.
- [03:47] In that case, we want to set all the relevant indices to 1,
- [03:51] leaving the rest as 0, just like we did for the words
- [03:54] from our training data.

**On-screen content:**
![Slide: Preprocessing labels. The input sentence and its encoded array are shown on the left. On the right, "Prediction" shows the labels `[pandas keras matplotlib]` and an encoded array `[1 0 1]`, indicating that "pandas" and "matplotlib" are relevant.](video-frame://25@03:29)

## [03:55] Inputs to Predictions: Machine Learning in Action

**Spoken content:**
- [03:56] Now we've turned the inputs as well as
- [03:58] the outputs, which both used to be words,
- [04:01] into arrays of numbers.
- [04:03] And we can let machine learning do what it does best--
- [04:07] map one set of numbers to another set of numbers.
- [04:10] All the heavy lifting is done in the preprocessing
- [04:13] as we transformed or encoded that text
- [04:16] into numerical representations.
- [04:18] Bag of words is a pretty simple approach for doing this task,
- [04:22] though it's worth pointing out that it might surprise you
- [04:25] how well it works in some situations.

**On-screen content:**
![Slide: Inputs to predictions. A matrix multiplication and addition operation is shown: `[1 2; 3 4] * [2 0; 1 2] + [4 3; 0 1] = [8 7; 10 9]`. Below, `inputs [1 0 0 1 0 0 1 0 0 0]` and `prediction [1 0 1]` are displayed.](video-frame://25@03:55)

## [04:28] Encoding Text with Keras

**Spoken content:**
- [04:29] How might we build a bag of words modeled with code?
- [04:33] Keras has a convenient preprocessing library
- [04:36] that we can use to handle much of this for us.
- [04:39] Using the Tokenizer class, we can
- [04:42] select the size of the vocabulary
- [04:44] we'd like to utilize.
- [04:45] In our example, we just had 10 words, which is quite small,
- [04:49] but in our code, let's choose something bigger, like 400.
- [04:52] This will then be fit on the entire body of the text
- [04:55] from your training data, selecting out
- [04:57] the most common 400 words.

**On-screen content:**
![Code snippet: Encoding text with Keras.
```python
tokenize = keras.preprocessing.text.Tokenizer(num_words=400)
tokenize.fit_on_texts(train_questions)

body_train = tokenize.texts_to_matrix(train_questions)
body_test = tokenize.texts_to_matrix(test_questions)
```
](video-frame://25@04:28)

## [05:00] Model Architecture for Bag of Words

**Spoken content:**
- [05:01] With the tokenization process complete, building the model
- [05:04] becomes quite straightforward and similar
- [05:06] to working with other structured data.
- [05:08] Since each row is now just an input of 1s and 0s,
- [05:12] using something as simple as a standard, fully connected,
- [05:15] deep neural network can be quite effective.
- [05:18] If you're planning on having multiple label classification,
- [05:22] where more than one label might be true for a single input,
- [05:25] as we do here, be sure that we choose a sigmoid activation
- [05:30] instead of the more common Softmax activation function,
- [05:33] and pair it with binary cross-entropy loss.

**On-screen content:**
![Code snippet: Model architecture.
```python
model = keras.models.Sequential()
model.add(keras.layers.Dense(50, input_shape=(vocab_size,), activation='relu'))
model.add(keras.layers.Dense(25, activation='relu'))
model.add(keras.layers.Dense(5, activation='sigmoid'))

model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
```
The 'sigmoid' activation is highlighted.](video-frame://25@05:00)

## [05:36] Conclusion and Further Resources

**Spoken content:**
- [05:37] So there you have it--
- [05:38] the bag of words model in a nutshell.
- [05:40] Understanding how bag of words works
- [05:43] and its advantages and drawbacks can
- [05:45] help you build your foundation in natural language processing
- [05:48] as you move on to more advanced approaches to encoding text.
- [05:52] For more details and examples, be
- [05:54] sure to check out the expanded blog post I have linked below
- [05:57] in the description.
- [05:59] Thanks for watching this episode of "Cloud AI Adventures."
- [06:01] And if you enjoyed it, please like it
- [06:03] and subscribe to get all the latest episodes right
- [06:06] when they come out.
- [06:07] For now, get started on your natural language processing
- [06:10] journey by checking out the tensor flow
- [06:12] word embedding tutorial I've linked below
- [06:14] in the description.
- [06:16] [MUSIC PLAYING]

**On-screen content:**
![Yufeng Guo speaking in front of a white background, wearing a grey t-shirt with the Google Cloud logo.](video-frame://25@05:36)
![Slide: Yufeng Guo @YufengG. Google Cloud logo.](video-frame://25@05:57)
![Slide: Looking for more tips on ML? Watch more. Google Cloud logo.](video-frame://25@06:15)
