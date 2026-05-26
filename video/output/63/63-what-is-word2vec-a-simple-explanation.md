---
id: "63"
title: "What is Word2Vec? A Simple Explanation"
source_url: "https://www.youtube.com/watch?v=hQwFeIupNP0"
fetch_url: "https://www.youtube.com/watch?v=hQwFeIupNP0"
resolved_url: "https://www.youtube.com/watch?v=hQwFeIupNP0"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T05:31:01.414371Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "3b5e1e498af188e054c9f3cfb96d89451d06f31bac9b6cc9e8aa6a4e4549b932"
cache_keys:
  - "3b5e1e498af188e054c9f3cfb96d89451d06f31bac9b6cc9e8aa6a4e4549b932"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 1107.0
transcript_source: "manual_captions"
transcript_sha256: "ab1575417af5eac3d3df0fc95092bd1bb2a0b01a92f5f1a5b804ada46514e90f"
word_count: 4646
char_count: 24649
content_sha256: "c28f16f5c6d2e691b938a96198569eed0bdced0288e444c1a18b4037364eda79"
image_count: 22
link_count: 0
total_token_count: 54116
estimated_input_tokens: 59534
warnings:
  - "title_mismatch"
gate_status: "passed_with_warnings"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Word2Vec

**Spoken content:**
- [00:00] word to work is a technique in computer
- [00:02] science that allows you to do
- [00:04] mathematics with the word. For example
- [00:07] you can give this equation to a computer
- [00:09] which will be something like king minus
- [00:12] men plus woman
- [00:13] and computer will tell you the answer is
- [00:16] queen.
- [00:17] What? Isn't that mind-boggling?
- [00:20] This is super cool. And it works really
- [00:23] well
- [00:24] and I'm not making this up. So how can
- [00:26] computer do this
- [00:28] well think about this computers don't

**On-screen content:**
![text: King - man + woman = Queen](video-frame://63@00:17)

## [00:28] Representing Words as Vectors

**Spoken content:**
- [00:30] understand text so
- [00:31] they understand numbers. So if there is a
- [00:34] way to represent a word
- [00:36] king in a number such that it can
- [00:40] accurately represent the meaning of the
- [00:42] word king.
- [00:44] Now that number cannot be one number so
- [00:46] you need to have
- [00:47] set of numbers and in mathematics set of
- [00:50] numbers are called vectors
- [00:51] so let's think about this how about we
- [00:54] represent working
- [00:55] into a vector which is just a bunch of
- [00:58] numbers
- [00:59] such that it can represent the meaning
- [01:01] of word
- [01:02] king accurately. Now think about king
- [01:06] king has a different property so there
- [01:08] are different ways of representing
- [01:11] the word king. For example king has
- [01:13] authority
- [01:14] king is rich usually. King
- [01:18] has a gender of male, okay.
- [01:22] Does king have a tail no
- [01:25] generally horse will have a tail right
- [01:27] so that answer will be
- [01:29] zero so what if we do this all right so
- [01:32] for authority
- [01:33] we'll give number one for tail we'll
- [01:36] give number zero because
- [01:38] king doesn't have tail for being rich
- [01:41] we'll give number one. One meaning super
- [01:43] rich
- [01:44] zero meaning very poor and for gender
- [01:47] let's say we give number minus one minus
- [01:49] one is
- [01:50] male and one is female now we came up
- [01:54] with this vector one zero one minus one
- [01:57] that represents the meaning of word
- [02:00] king. You can do similar thing with

**On-screen content:**
![diagram: King represented as a vector with properties: authority = 1, has tail = 0, rich = 1, gender = -1, resulting in vector [1,0,1,-1]](video-frame://63@01:56)

## [02:01] Word Vectors for Different Words

**Spoken content:**
- [02:02] another word for example horse for horse
- [02:05] the property tail will be one
- [02:08] but the other property such as authority
- [02:10] being rich etc
- [02:12] will be close to zero and if you do this
- [02:15] for
- [02:16] all type of different words in your
- [02:17] vocabulary you will be able to do
- [02:20] a math so let me just show you a very
- [02:22] simple example here.

**On-screen content:**
![diagram: Comparison of King and Horse as vectors with properties: King: authority = 1, has tail = 0, rich = 1, gender = -1, vector [1,0,1,-1]. Horse: authority = 0.01, has tail = 1, rich = 0.1, gender = 1, vector [0.01,1,0.1,1]](video-frame://63@02:16)

## [02:24] Performing Math with Word Vectors

**Spoken content:**
- [02:24] Let's say I have a story of king and
- [02:26] queen and I want to represent
- [02:28] all the words in that story with
- [02:31] word vectors here i have different
- [02:34] properties such as authority event
- [02:35] hashtag and so on and let's say there is
- [02:38] a word called battle.
- [02:39] For battle battle is an event so the
- [02:42] that value is one remaining values are
- [02:44] zero
- [02:45] horse has a tail that's why it's one
- [02:48] horse might have little authority
- [02:50] 0.01 or might be a little rich 0.1
- [02:54] if it is a horse of a king
- [02:57] so and gender is 1. here like
- [03:01] values might not be 0 because i'll tell
- [03:04] you the reason behind that
- [03:05] a little later but when you have king
- [03:08] we already saw it's 1 0 0 1 -1
- [03:12] and for different words you can come up
- [03:14] with these
- [03:15] different type of vectors and once you
- [03:19] have the vectors you can do the
- [03:20] mathematics so now when i do king minus
- [03:23] men plus
- [03:23] woman just do a simple math 1 minus 0.2
- [03:28] plus 0.2 is 1
- [03:30] 0 0 I'm taking individual elements okay
- [03:32] one minus point three is point seven
- [03:35] plus point two point nine and that
- [03:38] result vector is similar to a vector of
- [03:41] queen.
- [03:42] It is not exactly the same but it's
- [03:44] quite similar right .9 and 1
- [03:45] that's only difference
- [03:47] so you already saw how that math works
- [03:50] when you give this equation to computer
- [03:52] computer will be able to tell you that
- [03:54] the answer
- [03:55] is queen and that is pretty
- [03:59] powerful. Now

**On-screen content:**
![table: Word vectors for battle, horse, king, man, queen based on properties: authority, event, has tail, rich, gender. Below, the vector math for King - man + woman = Queen is shown.](video-frame://63@03:40)

## [04:00] Learning Word Embeddings with Neural Networks

**Spoken content:**
- [04:02] you don't want to hand code all these
- [04:04] properties for all these words
- [04:06] let's say you're doing doing natural
- [04:08] language processing for
- [04:11] all the text on wikipedia there are so
- [04:13] many thousands of
- [04:14] words and to come up with these kind of
- [04:17] properties for each of these words will
- [04:19] be very very difficult
- [04:22] so you don't want to hand craft it in
- [04:25] computer programming
- [04:26] you can use basically neural networks
- [04:29] to learn these feature vectors so
- [04:33] these
- [04:33] these numbers are called feature vectors
- [04:36] okay
- [04:37] so authority event has still are called
- [04:40] features
- [04:40] in the language of machine learning
- [04:43] and using neural networks you can learn
- [04:46] these feature vectors.
- [04:47] You don't have to hand code it so let's
- [04:49] see how that is done
- [04:51] and by the way when you learn these
- [04:53] feature vectors one interesting thing
- [04:54] that will happen is you will not
- [04:56] know what these feature vectors are you
- [04:58] will not know that this one means
- [05:00] authority
- [05:01] but it will all work magically
- [05:04] so what you do is you take a fake
- [05:07] problem
- [05:07] and you try to solve it using neural
- [05:09] network and as a side effect
- [05:12] you get word embedding now what does
- [05:15] that mean
- [05:16] so what is a fake problem let's say the
- [05:18] fake problem is you want to
- [05:21] find a missing word in a sentence.
- [05:24] That's your fake problem well the
- [05:27] problem is real but
- [05:28] our goal is not to learn what is the
- [05:32] missing word in a sentence our goal is
- [05:34] to learn
- [05:34] word embedding as a side effect.

**On-screen content:**
![text: Embeddings are not hand crafted. Instead, they are learnt during neural network training.](video-frame://63@04:20)
![text: 1. Take a fake problem. 2. Solve it using neural network. 3. You get word embeddings as a side effect.](video-frame://63@05:06)
![text: fake problem: fill in a missing word in a sentence](video-frame://63@05:19)

## [05:37] Example of the Fake Problem

**Spoken content:**
- [05:38] Say there is a story of great king
- [05:40] Ashoka
- [05:41] you know he was the king in India in
- [05:44] ancient times
- [05:46] and when you're reading this story you
- [05:49] can take a fake problem which is
- [05:52] complete this sentence so here when I
- [05:55] say order his minister see based on
- [05:58] this tax this my taking order his
- [06:00] minister the emperor order his minister
- [06:02] I can say
- [06:03] the missing word is king or emperor
- [06:07] and when I give this task of filling in
- [06:10] the missing word
- [06:11] to a computer as a side effect
- [06:14] this is a very important keyword side
- [06:16] effect
- [06:17] as a side effect it will learn the
- [06:21] vectors for king and emperor.
- [06:24] These are those feature vectors and once
- [06:26] you have vectors you can do math
- [06:28] you can say king is almost equal to
- [06:31] emperor.
- [06:32] So see you will be able to derive the
- [06:34] synonyms the antonyms. You can do
- [06:36] math such as king minus man plus woman
- [06:38] is equal to queen
- [06:39] and so on. So now
- [06:43] let's look into this problem a little
- [06:45] further for example you have this

**On-screen content:**
![text: There lived a king called Ashoka in India. After Kalinga battle, he converted to Buddhism. This mighty king ordered his ministers to put together a peaceful treaty with their neighboring kingdoms. The emperor ordered his ministers to also build stupa, a monument with Buddha's teachings.](video-frame://63@05:40)
![diagram: Fake problem: fill in the blank for "___ ordered his ministers" with "king" or "emperor". Side effect: learned vectors for king and emperor.](video-frame://63@06:22)

## [06:46] Contextual Inference of Word Meaning

**Spoken content:**
- [06:47] sentence
- [06:48] eating something is not very is very
- [06:50] healthy
- [06:52] and if I ask you to fill in the missing
- [06:53] word.
- [06:55] well most likely you will say April and
- [06:56] walnut. Because that's
- [06:58] food and that's healthy pizza is also
- [07:01] food but it's not healthy so you won't
- [07:02] feel it and
- [07:03] forget truck eating talk is very healthy
- [07:06] are you crazy
- [07:08] similarly when you have the sentence the
- [07:10] likely keyword
- [07:11] will be rocket you are not going to say
- [07:14] NASA launched pizza
- [07:15] last month. So now
- [07:19] when you are in this process of
- [07:23] finding out the missing word you realize
- [07:25] one fact which is meaning of a word can
- [07:27] be inferred by a surrounding words.
- [07:30] If someone gives you surrounding words
- [07:32] so these surrounding words are also
- [07:33] called
- [07:34] context. So based on the context
- [07:37] you can figure out what that missing
- [07:39] word is.
- [07:41] So now let's take this paragraph

**On-screen content:**
![text: eating ___ is very healthy. Options: table, angry, truck, apple, pizza, walnut.](video-frame://63@06:57)
![text: NASA launched ___ last month. Options: table, angry, truck, rocket, apple, pizza.](video-frame://63@07:12)
![text: Meaning of word can be inferred by surrounding words](video-frame://63@07:20)

## [07:41] Generating Training Samples for Word Embeddings

**Spoken content:**
- [07:44] and we will
- [07:47] try to auto complete those missing words
- [07:51] and auto completing missing words is
- [07:54] really not the area of our interest it
- [07:56] is our fake problem
- [07:57] our area of interest is to learn the
- [07:59] word embeddings.
- [08:01] The vectors which can represent those
- [08:02] words.
- [08:04] So I will parse this paragraph and I
- [08:08] will take a window of
- [08:09] three words and here
- [08:13] I will say if I have a word lived
- [08:16] and a I can predict that there is a word
- [08:19] there
- [08:19] so I'm taking the second and third word
- [08:21] and trying to predict the first word
- [08:24] and these are my training samples so I
- [08:26] can move that window of three words
- [08:29] throughout the paragraph
- [08:30] generate all these training samples.
- [08:34] You see I generated all these training
- [08:36] samples.
- [08:37] And now this becomes a training set for
- [08:40] neural network.
- [08:41] So the words on the left hand side are
- [08:43] my x.
- [08:44] the word on the right hand side are my y.
- [08:48] and you feed x into neural network
- [08:51] and you want it to predict the word
- [08:53] worldwide.
- [08:54] Now if you have not seen my neural
- [08:57] network video please go watch it
- [08:59] you need to have some understanding of
- [09:01] neural network
- [09:02] in order to understand things which I am
- [09:05] going to explain in this video.
- [09:06] So if you don't know already what is
- [09:07] neural network pause the video right now.
- [09:10] I'm going to provide my neural network
- [09:11] video link in a video description
- [09:14] below. So just get some basic
- [09:16] understanding
- [09:19] assuming you have the basic
- [09:20] understanding now let's go back to our
- [09:22] problem which is you have training
- [09:24] samples.
- [09:25] And by the way this problem is called
- [09:27] self-supervised because
- [09:29] all you had was this paragraph you did
- [09:32] not have like X and Y
- [09:34] you had a paragraph from that paragraph.
- [09:37] You generated these training samples
- [09:40] now let's try to train our neural

**On-screen content:**
![text: There lived a king called Ashoka in India. After Kalinga battle, he converted to Buddhism. This mighty king ordered his ministers to put together a peaceful treaty with their neighboring kingdoms. The emperor ordered his ministers to also build stupa, a monument with Buddha's teachings.](video-frame://63@07:44)
![diagram: Training samples generated from the text: lived, a -> There; a, king -> lived; ordered, his -> king; ordered, his -> emperor.](video-frame://63@08:36)

## [09:40] Neural Network Architecture for Word2Vec

**Spoken content:**
- [09:42] network using each of these
- [09:44] training samples. So let's say my first
- [09:47] sample is order his so order his is an
- [09:50] input
- [09:51] based on that you want to predict
- [09:53] working which is an output
- [09:55] now you can build a neural network that
- [09:57] looks something like this
- [09:59] the input layer will have
- [10:02] a one hot encoded vector so let's say
- [10:06] there are 5000
- [10:07] words in my vocabulary
- [10:11] then there will be a vector of size 5000
- [10:14] and
- [10:14] only one of them will be one so if the
- [10:17] word is ordered
- [10:18] the value of order will be one and
- [10:21] remaining
- [10:22] numbers will be zero. And same thing is
- [10:25] for his see here's this one and
- [10:27] remaining numbers are zero and the size
- [10:28] of this vector is let's say five
- [10:30] thousand. 5000 is let's say
- [10:31] vocabulary. Vocabulary means
- [10:33] unique words in your text corpus
- [10:37] or in the you know text problem that
- [10:39] you're trying to solve
- [10:42] and in the hidden layer here I have put
- [10:46] 4 neurons and these 4 neurons
- [10:49] are the size of my embedding vector.
- [10:53] Now size of embedding vector could be
- [10:55] anything like there is no golden rule I
- [10:57] just selected 4.
- [10:58] but it's a hyper parameter to your
- [11:00] neural network it could be
- [11:01] 5 10 200 anything this is something you
- [11:04] learn
- [11:04] using trial and error in the output
- [11:08] layer.
- [11:08] I will have 5000
- [11:12] size vector
- [11:15] and when I feed this training sample
- [11:18] into my neural network what happens is
- [11:20] these weights or the edges will have
- [11:23] random weights
- [11:26] so using random weights it will predict
- [11:28] some output which will be wrong most
- [11:30] likely.
- [11:31] King is the right output so you all know
- [11:33] how neural network works how back error
- [11:36] propagation works
- [11:37] you compare your actual output which is
- [11:40] why
- [11:41] with your predicted output y hat you
- [11:44] take a loss
- [11:45] so loss is a difference between your
- [11:46] predicted output and actual output
- [11:48] and you back propagate again if you
- [11:51] don't know about back propagation
- [11:53] i have some videos you can check it out
- [11:56] but when you back propagate
- [11:57] essentially what you're doing is you are
- [12:00] adjusting all these weights
- [12:02] and then you take us and then you take a
- [12:05] second sample third sample
- [12:06] you take all 10 000 or 1 million samples
- [12:10] and your goal is to train a networks in
- [12:13] such a way that
- [12:14] when you input order is the network
- [12:17] accurately finds out
- [12:18] that it is a king so you expect
- [12:22] one to be here actually you expect in
- [12:24] the emperor here also you expect it to
- [12:26] be 1 because it could be anything

**On-screen content:**
![diagram: Neural network architecture for Word2Vec. Input layer with one-hot encoded vectors for "ordered" and "his". Hidden layer with 4 neurons. Output layer with probabilities for all words in the vocabulary.](video-frame://63@10:42)
![diagram: Neural network with backpropagation showing predicted output (ŷ), actual output (y), and loss.](video-frame://63@11:48)

## [12:28] Training and Learning Word Embeddings

**Spoken content:**
- [12:28] now you take the second sentence which
- [12:32] is
- [12:32] emperor ordered his and you're not
- [12:34] taking the whole sentence you're taking
- [12:36] a window of size three
- [12:37] it could be window of size four or five
- [12:40] depends on you how you want to
- [12:41] experiment.
- [12:43] But same thing happens here where you
- [12:45] feed
- [12:46] and input the neural network will find
- [12:48] out the output it will compare it with
- [12:50] the actual output
- [12:51] there is a loss and it will back
- [12:53] propagate.
- [12:55] And it takes the third sentence you know
- [12:57] from Kalinga and battle you're trying to
- [12:58] predict that the missing word is
- [13:00] after same thing there is predicted
- [13:04] output actual output loss
- [13:05] back propagation and eventually when you
- [13:08] have
- [13:09] done you are done feeding your
- [13:13] let's say 1 million elements and let's
- [13:15] say you run 10 or 15 or 50 epochs
- [13:18] and your neural network is strain at
- [13:20] that point
- [13:22] the word vector for king would be these
- [13:25] weights.
- [13:26] w1 w2 w3 w4 so those weights are nothing
- [13:31] but a trained word vector
- [13:35] and this vector will be very similar to
- [13:38] a vector of
- [13:39] emperor. So the vector for the emperor
- [13:41] will be w5 w6 w7 w8
- [13:45] just think about it it will be similar
- [13:47] because the input is same so
- [13:49] here order and his both for king and
- [13:52] emperor the input is same
- [13:54] so when the input is same you expect
- [13:56] that
- [13:57] or these weights will also be similar
- [14:01] and hence the vector for king and
- [14:03] emperor will be very similar
- [14:05] using this approach. This approach is

**On-screen content:**
![diagram: Neural network with backpropagation for "emperor ordered his".](video-frame://63@12:52)
![diagram: Neural network with backpropagation for "kalinga battle -> after".](video-frame://63@13:02)
![diagram: Neural network showing weights (w1-w4) as the word vector for "king".](video-frame://63@13:28)

## [14:05] CBOW vs. Skip-Gram

**Spoken content:**
- [14:07] called continuous bag of words
- [14:10] so here you have a context which is
- [14:13] order his
- [14:14] and based on that context you are trying
- [14:16] to predict
- [14:18] target which is king. There is a
- [14:21] second methodology called skip gram
- [14:25] in script gram we do reverse we have a
- [14:29] target working
- [14:30] and based on that we try to predict
- [14:33] order his.
- [14:34] Again, predicting target from context in
- [14:38] context from target these are fake
- [14:40] problems you know we are not interested
- [14:42] in solving this problem
- [14:43] but while we solve those problems as a
- [14:46] side effect
- [14:47] we get word embedding so we are more
- [14:49] interested in learning word embeddings
- [14:51] just to summarize word to Vec
- [14:55] is not a single method but it it could
- [14:58] be using one of the 2
- [14:59] techniques which is either continuous
- [15:02] back of words or skip gram
- [15:04] to learn word embeddings see the word
- [15:06] word to vec means
- [15:08] convert word to a vector so word to vec
- [15:12] is a
- [15:12] revolutionary invention in the field of
- [15:15] computer science
- [15:17] which allows you to represent words in
- [15:20] an
- [15:20] in a vector in a very accurate way so
- [15:24] that you can do mathematics with it.
- [15:27] Let's talk about script gram so in skip

**On-screen content:**
![diagram: Comparison of CBOW (given context words predict target word) and Skip-Gram (given target word predict context words).](video-frame://63@14:40)
![text: Word2Vec: 1. CBOW: Continuous Bag Of Words. 2. Skip Gram.](video-frame://63@15:00)

## [15:27] Skip-Gram Architecture

**Spoken content:**
- [15:29] gram
- [15:30] I have inverted my neural network
- [15:33] diagram so here you can see it's exactly
- [15:35] reversed then
- [15:36] the c bar here you have the word
- [15:40] king based on that you're trying to
- [15:42] predict order his
- [15:44] and you will do the same thing. You will
- [15:45] feed one sentence
- [15:47] calculate the expected output. Compare it
- [15:50] with the
- [15:51] actual output do back propagation and so
- [15:54] on.
- [15:55] And in that process you learn the word
- [15:57] embeddings for each of these
- [15:59] words you know. There are 5000 words less
- [16:02] in our vocabulary
- [16:03] so the embedding for Ashoka will be w1
- [16:07] to w4
- [16:07] the embedding would be m for emperor
- [16:09] would be w6 to w9.
- [16:12] So when you're using skip gram the word
- [16:15] embedding
- [16:16] is a layer between the input layer and
- [16:18] the hidden layer
- [16:20] in the c bar it was the weights between
- [16:24] hidden layer and the output layer.
- [16:27] You can do wonderful things with word to

**On-screen content:**
![diagram: Skip Gram neural network architecture. Input layer with one-hot encoded vector for "king". Hidden layer with 4 neurons. Output layer with probabilities for context words.](video-frame://63@15:54)

## [16:27] Applications of Word2Vec

**Spoken content:**
- [16:29] wack such as
- [16:30] usa minus Washington DC plus Delhi do
- [16:33] you have any guess
- [16:34] pause the video this is a quiz for you
- [16:38] well it is India okay any guess on this
- [16:42] one
- [16:44] wow you all are so smart yes apple
- [16:47] so computers can do this kind of
- [16:50] mathematics
- [16:52] this works really well.

**On-screen content:**
![text: King - man + woman = Queen. USA - Washington D.C. + Delhi = India. Samsun - Galaxy + iPhone = Apple.](video-frame://63@16:47)

## [16:55] Visualizing Word Embeddings

**Spoken content:**
- [16:56] I took this diagram from the towards
- [16:58] science
- [17:00] article you can represent these vectors
- [17:04] in a vector space.
- [17:06] So here I'm showing you three
- [17:08] dimensional vector space
- [17:09] that could be n dimensional vector space
- [17:12] and you know using a method called
- [17:14] Disney you can change that n-dimensional
- [17:18] vector space to two-dimensional vector
- [17:20] space
- [17:21] and you will find that
- [17:24] the word the relationship between
- [17:27] walking and walked will be similar to
- [17:30] swimming and swam.
- [17:31] So once you have learned this
- [17:32] relationship when you give a word
- [17:34] swimming to a computer
- [17:35] it will tell you the output is swam
- [17:39] It can also figure out a relationship
- [17:41] basically it will say okay
- [17:43] whatever is Madrid to Spain the
- [17:46] same thing is Rome to Italy
- [17:51] so it can draw it can learn
- [17:54] these kind of complex relationships
- [17:58] so that was all the theory behind word
- [18:00] to work
- [18:01] I hope you like this video if you did
- [18:04] please share it with your friends who
- [18:06] are confused about word embeddings
- [18:08] word to vector and if you have any
- [18:10] question post in a video comment below.
- [18:13] In the next video we will be looking at
- [18:16] the coding part
- [18:17] where using python we will see
- [18:20] how word to vec works and we'll run
- [18:22] some code
- [18:23] to see this magic in works. Thank you.

**On-screen content:**
![diagram: 3D vector space visualizations of word relationships: Male-Female (man, king, woman, queen), Verb tense (walking, walked, swimming, swam), and Country-Capital (Spain-Madrid, Italy-Rome, Turkey-Ankara, Russia-Moscow, Canada-Ottawa, Japan-Tokyo, Vietnam-Hanoi, China-Beijing).](video-frame://63@17:57)
