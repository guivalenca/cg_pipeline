---
id: "41"
title: "What is word2vec? - Programming with Text"
source_url: "https://www.youtube.com/watch?v=LSS_bos_TPI"
fetch_url: "https://www.youtube.com/watch?v=LSS_bos_TPI"
resolved_url: "https://www.youtube.com/watch?v=LSS_bos_TPI"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T04:43:45.895349Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "62181053a33317f35c413f14e77e406024287db0d8497246eff974ae31cdfb18"
cache_keys:
  - "62181053a33317f35c413f14e77e406024287db0d8497246eff974ae31cdfb18"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 620.0
transcript_source: "manual_captions"
transcript_sha256: "9f481cfac0326ac8e1b57bee7c9912a264a9fa6550384a30464a1d2c562cd671"
word_count: 1323
char_count: 8263
content_sha256: "9a45ee1e35882ecda95ef89e84425c1ef3719a5dbc626dd8f277fde971207171"
image_count: 10
link_count: 0
total_token_count: 41911
estimated_input_tokens: 33343
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## 00:00 Introduction to Word2Vec

**Spoken content:** The speaker introduces a new session about "word2vec," acknowledging that he has used it but gained a deeper understanding after reading an "amazing tutorial by Allison Parrish." He mentions the tutorial is a Python notebook titled "Understanding Word Vectors" posted as a Gist on GitHub. He encourages viewers to read the tutorial directly but will also explain it in his own words. He notes the tutorial's Creative Commons 4.0 license for content and Creative Commons Zero for code, allowing reuse with attribution.

**On-screen content:**
The video shows a split screen. On the left, a web browser displays a GitHub Gist titled "understanding-word-vectors.ipynb" by "aparrish." The Gist's description states: "Understanding word vectors: A tutorial for 'Reading and Writing Electronic Text,' a class I teach at ITP. (Python 2.7) Code examples released under CC0, other text released under CC BY 4.0."
The right side of the screen shows the speaker, a man with glasses and a beard, wearing a dark hoodie, standing in front of a white background. He gestures enthusiastically.
![GitHub Gist: Understanding Word Vectors by Allison Parrish](video-frame://41@00:42)

## 01:27 Allison Parrish's Talk and Course Goal

**Spoken content:** The speaker also recommends Allison Parrish's YouTube talk, "Experimental Creative Writing with the Vectorized Word," from the Strange Loop conference, as further inspiration. He states his end goal for this tutorial series is to create a P5.js sketch in the browser to interact with word2vec, specifically to answer "what is word2vec?" and then use it in projects to create "weird stuff with text on a web page."

**On-screen content:**
The left side of the screen now shows a YouTube video titled "Experimental Creative Writing with the Vectorized Word" by Allison Parrish, from the "Strange Loop" channel.
![YouTube video: Experimental Creative Writing with the Vectorized Word](video-frame://41@01:30)

## 02:10 What is Word Embedding?

**Spoken content:** The speaker moves to a whiteboard to explain "word2vec." He describes it as a machine learning process, similar to classification or regression analysis, that produces "word embeddings." A word embedding means that any given word, like "apple," can be associated with a vector—an array of numbers (e.g., 0.7, 1.2, -0.345...). This allows for mathematical operations on words. He poses a question: "Apple" + "Purple" = "Plum"? He suggests that by quantifying words as numerical vectors, we can perform mathematical operations (like addition) on these vectors, and then find the word whose vector is most similar to the resulting vector. This is possible because of the data the word2vec model is trained on.

**On-screen content:**
The speaker is now standing in front of a whiteboard.
Initially, the whiteboard has "word2vec" written at the top.
![whiteboard: word2vec](video-frame://41@02:15)
As he speaks, he adds:
- "word embedding" to the right of "word2vec."
- An arrow from "apple" to a bracketed list of numbers: "[0.7, 1.2, -0.345,...]"
- Below that, he writes: `"apple"` + `"purple"` => `"plum"`
- He then draws arrows from "apple" and "purple" to empty brackets, implying they also have numerical representations that can be added.
![whiteboard: word2vec, word embedding, "apple" -> [0.7, 1.2, -0.345,...], "apple" + "purple" => "plum"](video-frame://41@03:07)
He also draws a square with a circle and an arrow inside, labeled "velocity," to illustrate vectors.
![whiteboard: vector illustration with velocity](video-frame://41@07:05)
He then draws another square, showing "apple" as a point, an arrow representing "purple," and the resulting point as "plum."
![whiteboard: vector addition of "apple" and "purple" to get "plum"](video-frame://41@07:24)

## 05:38 Animal Similarity and Simple Linear Algebra

**Spoken content:** The speaker returns to Allison Parrish's tutorial, which simplifies the concept by assigning two numbers to each animal: a "cuteness" score (0-100) and a "size" score (0-100). This creates a simple "word embedding" for animals.

**On-screen content:**
The left side of the screen shows a table from the Jupyter Notebook titled "Animal similarity and simple linear algebra." The table has three columns: "animal," "cuteness (0-100)," and "size (0-100)."
Rows include:
- kitten: 95, 15
- hamster: 80, 8
- tarantula: 8, 3
- puppy: 90, 20
- crocodile: 5, 40
- dolphin: 60, 45
- panda bear: 75, 40
- lobster: 2, 15
- capybara: 70, 30
- elephant: 65, 90
- mosquito: 1, 1
- goldfish: 25, 2
- horse: 50, 60
- chicken: 25, 25
![table: Animal Cuteness and Size Scores](video-frame://41@05:55)

## 06:18 Animal Space Visualization

**Spoken content:** The speaker explains that by plotting these two numbers (cuteness and size), we can visualize the relationships between animals. Animals that are physically close on the graph are considered similar in terms of these two properties. He mentions calculating the "Euclidean distance" between these points to quantify their similarity.

**On-screen content:**
The Jupyter Notebook displays a scatter plot titled "Animal Space." The x-axis is "cuteness" (0-100) and the y-axis is "size" (0-100). Each animal from the table is represented as a bubble on the plot. For example, "kitten" and "puppy" are close, while "elephant" is in the top right (high cuteness, high size). "Horse" and "dolphin" are also shown to be close.
![scatter plot: Animal Space with Cuteness vs. Size](video-frame://41@06:20)

## 06:48 Vectors and Relationships

**Spoken content:** The speaker further elaborates on the concept of vectors, relating it to his previous tutorials on velocity vectors in particle systems. He shows how moving from one word to another in this "animal space" can represent a relationship. For instance, an arrow from "chicken" to "kitten" represents a relationship, and a similar arrow from "tarantula" to "hamster" suggests an analogy. He clarifies that this 2D example uses hard-coded values for demonstration, making it easy for our brains to process.

**On-screen content:**
The scatter plot is shown again, with two arrows drawn:
- A red arrow from "chicken" to "kitten."
- A blue arrow from "tarantula" to "hamster."
The text below the diagram explains: "You can understand this arrow as being the relationship between a tarantula and a hamster, in terms of their size and cuteness (i.e. tarantulas are about the same size, but hamsters are much cuter). In the same diagram, I've also transposed this same arrow (this time in red) so that its origin point is 'chicken.' The arrow ends closest to 'kitten.' What we've discovered is that the same size as a chicken but much cuter is... a kitten. To put it in terms of an analogy: Tarantulas are to hamsters as chickens are to kittens."
![scatter plot: Animal Space with vector arrows showing relationships](video-frame://41@07:37)

## 08:13 Higher Dimensions and Next Steps

**Spoken content:** The speaker explains that while 2D visualization is helpful, real word2vec models use much higher dimensional spaces (e.g., 100 or 300 dimensions), which cannot be easily visualized directly. He mentions "dimensionality reduction" techniques for visualizing word clusters. He summarizes that word2vec establishes complex relationships between words in higher-dimensional space. He outlines the next steps:
1.  Port Allison's example of colors associated with numbers (like red = 255,0,0) into JavaScript.
2.  Look at traditionally understood word2vec models with large dictionaries and their associated high-dimensional word embeddings.
He concludes by saying he will do a JavaScript port of Allison's Python code in the next video.

**On-screen content:**
The speaker is back in front of the whiteboard, which still contains the "word2vec," "word embedding," and vector diagrams. He gestures as he explains the concepts.
![whiteboard: word2vec, word embedding, and vector diagrams](video-frame://41@08:14)

## 10:09 Outro

**Spoken content:** The speaker waves goodbye and encourages viewers to read Allison Parrish's page.

**On-screen content:**
The speaker is inside a blue cartoon train window, waving. Upbeat music plays.
![speaker in cartoon train window](video-frame://41@10:09)
