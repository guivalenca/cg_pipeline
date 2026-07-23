---
id: "12"
title: "Natural Language Processing In 5 Minutes | What Is NLP And How Does It Work? | Simplilearn"
source_url: "https://www.youtube.com/watch?v=CMrHM8a3hqw"
fetch_url: "https://www.youtube.com/watch?v=CMrHM8a3hqw"
resolved_url: "https://www.youtube.com/watch?v=CMrHM8a3hqw"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T04:38:45.090475Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "9211457dcd2d6047a36d4da22b5bdfb1f6f942f1e35ec71f43b7fabd6bc8cd77"
cache_keys:
  - "9211457dcd2d6047a36d4da22b5bdfb1f6f942f1e35ec71f43b7fabd6bc8cd77"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 329.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "c787c64d7a76e6b76ce64f4bc5575dc67578c3d08ac753839f7aad002b8835c0"
word_count: 1483
char_count: 9124
content_sha256: "5f487ef9338a68b691df602e1afad97db895bec113f3f048307c1dac9df02e2f"
image_count: 17
link_count: 0
total_token_count: 22956
estimated_input_tokens: 17693
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Natural Language Processing

**Spoken content:** Star Wars fans would be familiar with the golden, life-sized hospitality robot C-3PO. While Star Wars might be set in a galaxy far, far away, the reality of having machines talk and respond to us in a human-like manner is already a reality, which keeps getting more and more realistic with every passing day. The people you ask for queries on websites, your smart assistants, even calls made over the internet, all of them have one thing in common: none of them are actually human. Now, you must be thinking, if they are not human, how do they manage to sound and seem so human-like, how do they respond to me so intelligently, and how are they so articulate? This my friends, is the magic of natural language processing.

**On-screen content:**
![diagram: Star Wars logo pointing to C-3PO robot, then to a galaxy, then to a robot interacting with a human, then to a calendar, then to various digital assistants and websites](video-frame://00:00)

## [00:44] What is NLP?

**Spoken content:** What is NLP? Natural language processing, or NLP, refers to the branch of artificial intelligence that gives the machines the ability to read, understand, and derive meaning from human languages. NLP combines the field of linguistics and computer science to decipher language structure and guidelines, and to make models which can comprehend, break down, and separate significant details from text and speech.

**On-screen content:**
![diagram: NLP pointing to an AI robot reading a book, then to a blackboard with alphabet and punctuation, then to a combination of linguistics and computer science leading to deciphering language structure and making models](video-frame://00:44)

## [01:08] Why is NLP Important?

**Spoken content:** Every day, humans interact with each other through public social media, transferring vast quantities of freely available data to each other. This data is extremely useful in understanding human behavior and customer habits. Data analysts and machine learning experts utilize this data to give machines the ability to mimic human linguistic behavior. This helps save millions in terms of manpower and time, as you don't need to always have a person present at the other end of a phone. NLP is also a lot more widespread than you may realize. You use it every day in seemingly normal and insignificant situations. Don't know how to correctly spell a word? Autocorrect has you covered. Need to see if your article or thesis will get flagged for copyright violations? That's okay. A plagiarism checker will search through the web and find any cases of published documents, which may match your work line by line.

**On-screen content:**
![diagram: two people exchanging data via social media, leading to understanding human behavior and customer habits, then data being fed to a robot, saving time and manpower](video-frame://01:08)
![diagram: NLP applications including autocorrect and plagiarism checkers like Grammarly](video-frame://01:36)

## [02:01] How NLP Works: The Steps

**Spoken content:** While NLP seems really cool, yet a cutting-edge and complicated technology concept, it is actually pretty easy to learn. You start off with a document or an article. To make your algorithm understand what is going on in it, you need to process it into a form which is easily comprehensible by the machine. This is no different than making a child learn to read for the first time.

**On-screen content:**
![diagram: a person thinking about NLP, then a document being processed into a machine-understandable format](video-frame://02:01)

### [02:24] 1. Segmentation

**Spoken content:** You start off by performing segmentation, which is to break the entire document down into its constituent sentences. You can do this by segmenting the article along its punctuations like full stops and commas.

**On-screen content:**
![diagram: Segmentation process showing a sentence "Cricket was invented in England, supposedly by shepherds who herded their flock." being broken into two sentences: "Cricket was invented in England" and "supposedly by shepherds who herded their flock."](video-frame://02:24)

### [02:36] 2. Tokenization

**Spoken content:** For the algorithm to understand these sentences, we get the words in a sentence and to explain them individually to our algorithm. So we break down our sentence into its constituent words and store them. This is called tokenizing, where each word is called a token. We can make the learning process faster by getting rid of non-essential words which do not add much meaning to our statement and are just there to make our statement sound more cohesive. These words such as "are" and "the" are called stop words.

**On-screen content:**
![diagram: Tokenization process showing the sentence "Cricket was invented in England" broken into individual words (tokens) in boxes. Then, "was" and "in" are highlighted as non-essential words (stop words).](video-frame://02:36)

### [03:06] 3. Stemming

**Spoken content:** Now that we have the basic form of our document, we need to explain it to our machine. We first start off by explaining that some words like skipping, skips, skipped are the same word with added prefixes and suffixes. This is called stemming.

**On-screen content:**
![diagram: Stemming process showing "Skip + ing", "Skip + s", "Skip + ed" all pointing to the base word "Skip".](video-frame://03:06)

### [03:20] 4. Lemmatization

**Spoken content:** We also identify the base words for different word tense, mood, gender, etc. This is called lemmatization, stemming from the base word "limma".

**On-screen content:**
![diagram: Lemmatization process showing "Am", "Are", "Is" all pointing to the base word "Be" (Lemma).](video-frame://03:20)

### [03:29] 5. Part-of-Speech Tagging

**Spoken content:** Now we explain the concept of nouns, verbs, articles and other parts of speech to the machine by adding these tags to our words. This is called part of speech tagging.

**On-screen content:**
![diagram: Part-of-Speech Tagging showing the sentence "Cricket was invented in England" with each word tagged with its part of speech: "Cricket (Noun)", "was (Verb)", "invented (Verb)", "in (Preposition)", "England (Noun)".](video-frame://03:29)

### [03:40] 6. Named Entity Tagging

**Spoken content:** Next, we introduce our machine to pop culture references and everyday names by flagging names of movies, important personalities or locations, etc. that may occur in the document. This is called named entity tagging.

**On-screen content:**
![diagram: Named Entity Tagging showing symbols for movies, people, and locations, indicating recognition of named entities.](video-frame://03:40)

### [03:53] 7. Machine Learning Algorithm

**Spoken content:** Once we have our base words and tags, we use a machine learning algorithm like Naive Bayes to teach our model human sentiment and speech. At the end of the day, most of the techniques used in NLP are simple grammar techniques that we have been taught in school.

**On-screen content:**
![diagram: The processed sentence "Cricket was invented in England" being fed into a "naive bayes" algorithm, which then teaches a robot model human sentiment and speech.](video-frame://03:53)

## [04:08] Quiz Question and Conclusion

**Spoken content:** Here is a question for you. Which of these NLP techniques is used to obtain words from sentences? A. Stemming B. Tokenization C. Lemmatization D. Segmentation. Give it a thought and leave your answers in the comment section below. Three lucky winners will receive Amazon gift vouchers. With the increasing demand for automated language solutions, companies are looking for NLP experts to join them and are prepared to offer highly lucrative salaries as well. If you want to learn more about NLP, you can check out Simply Learn's postgraduate program in AI and Machine Learning in collaboration with IBM. In this program, you will learn about frameworks like Keras and TensorFlow and get hands-on experience and deep learning to become a truly experienced AI engineer. That brings us to the end of this video on NLP. We hope you enjoyed this video. If you did, a thumbs up would be really appreciated. Here's your reminder to subscribe to our channel and to click on the bell icon for more on the latest technologies and trends. Thank you for watching and stay tuned for more from Simply Learn.

**On-screen content:**
![quiz question: Which of these NLP Techniques is used to obtain words from sentences? a) Stemming b) Tokenization c) Lemmatization d) Segmentation](video-frame://04:08)
![diagram: companies seeking NLP experts with high salaries](video-frame://04:28)
![diagram: NLP leading to SimplyLearn's Post Graduate Program in AI and Machine Learning in collaboration with IBM](video-frame://04:37)
![diagram: program covers Keras and TensorFlow, leading to deep learning and becoming an AI engineer](video-frame://04:46)
![outro: thumbs up, share, subscribe, bell icon, "Thank you for watching and stay tuned for more from Simplilearn"](video-frame://04:55)
