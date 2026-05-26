---
id: "36"
title: "A Hitchhikers Guide to Sentiment Analysis using Naive Bayes Classifier"
source_url: "https://towardsdatascience.com/a-hitchhikers-guide-to-sentiment-analysis-using-naive-bayes-classifier-b921c0fb694"
fetch_url: "https://towardsdatascience.com/a-hitchhikers-guide-to-sentiment-analysis-using-naive-bayes-classifier-b921c0fb694"
resolved_url: "https://towardsdatascience.com/a-hitchhikers-guide-to-sentiment-analysis-using-naive-bayes-classifier-b921c0fb694/"
firecrawl_title: "A Hitchhiker's Guide to Sentiment Analysis using Naive-Bayes Classifier | Towards Data Science"
description: null
fetched_at: "2026-05-12T03:59:51.884202Z"
provider: "firecrawl"
strategy: "static_with_actions"
cache_key: "6778258b645cae185de8de87dc4af096d965bf29c118076c5ef8c0afdaf659f4"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=UTF-8"
word_count: 2681
char_count: 15922
content_sha256: "571e64cfa26a414e08effeae786580ab11d376acbbdc0a88d6fddfcd5c76985b"
image_count: 26
link_count: 29
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "medium_network_member_wall_possible"
---

# A Hitchhiker’s Guide to Sentiment Analysis using Naive-Bayes Classifier

![image from Unsplash](https://towardsdatascience.com/wp-content/uploads/2021/05/1Zpl6opHBZPpQu6RHkxvn3Q-scaled.jpeg)image from [Unsplash](https://unsplash.com/photos/g5gia1p67hE)

**Classification** lies at the heart of Machine Learning and Human Intelligence. Recognizing voices or faces or what images we see on a daily basis all come under the umbrella of classification. Now coming to Naive Bayes , for anyone starting out in the field of Natural Language Processing , this is the first step one takes towards this goal ;that is why it is of paramount importance we understand how to implement this and what’s going on under the bonnet . In this article we are going to learn how to implement Naive-Bayes from scratch and use it for Sentiment analysis.

**INDEX:**

1. **SENTIMENT ANALYSIS**  
2. **TERMINOLOGY**  
3. **NAIVE-BAYES THEOREM**  
4. **DERIVATION**  
5. **TRAINING THE MODEL**  
6. **SOLVED EXAMPLE**  
7. **CONCLUSION**  

## SENTIMENT ANALYSIS

Now sentiment analysis as the name suggests is basically the task where we classify the sentiment of the statement or more simply the emotion one particular statement is trying to convey ; whether its positive or negative , sad or sarcastic; insulting or wholesome and kind . Let’s elaborate this point with a few more examples;

Let’s say there’s a new restaurant in Town and you and your friend decided to have dinner there and experience this place. You really enjoyed yourself and when your friend asks for your opinion, you say something along the lines :

![image from Unsplash](https://towardsdatascience.com/wp-content/uploads/2021/05/11F7pWpwSJwHo9VaKKjspyg-scaled.jpeg)image from [Unsplash](https://unsplash.com/photos/Gg5-K-mJwuQ)

1. _" This place is great . The food is delicious and the ambience is quite enjoyable"_

Now your friend has contrary beliefs. This new place was not to his liking. So when you in turn ask for his opinion he remarks:

2. _"This place is pathetic. The food is horrible and the ambience is quite overpowering for me and makes me really uncomfortable"_

I think we can all agree that statement 1 expresses a positive sentiment while statement 2 represents a negative sentiment or an emotion. What’s also important for us to notice is what EXACTLY gave us the clues which allowed us to classify the sentences into positive or negative.

The Answer? The cues…

if you look closely… There are certain words in the sentences that dictate the emotion . Positive words like _**great, delicious, enjoyable**_ etc. make the sentence positive while words like _**pathetic , horrible , uncomfortable**_ etc. make the sentence negative . In fact if we just replace these special cues in a sentence it completely changes its meaning. Let me show you:

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1oyHfVbHUey328QXGU2zlfg.png)image by author

In each of these examples , if you notice, by changing one pivotal word changes the entire flavor of the sentence while the rest of the sentence remains exactly the same . This is the essence of Sentiment Analysis . Also we are going to limit our discussion to **binary classification** , classifying the sentences as either positive or negative.

## TERMINOLOGY

Now before digging into mathematics let’s first talk about terminology . What we are going to do here falls under **Supervised Machine Learning** ; which means that we will be provided with training inputs and each of these inputs will be associated with its correct output . Now it’s the job of your model to make sense of this data , observe and analyze the relationship between the given inputs and outputs and finally predict with reasonable accuracy the output ; given a new input.

Going further ; we usually denote input as x and output as y where y ∈[y, yb, yc,…..yn] classes and it’s your model’s task to predict which output class a particular input x belongs to . Now in this case we will be dealing with words and sentences so there is a slight change in terminology . Our input will be ‘ _**d**_‘ for document (sentences basically) consisting of a number of features and our output would be ‘ _**c**_‘ for class. Here the class will represent either positive(for positive sentiment) or negative (for negative sentiment).

So finally we will get an input d and our model has to learn to predict which class , ‘c’ , it belongs to .

Now that we are done with the nitty gritty and the fine details let’s start with the theorem.

## NAIVE-BAYES THEOREM

Let’s first look into **Bayes Theorem:**

P(A | B) = P(B | A) * P(A) / P(B) ->(1)

Let’s Look into the terms:

- P(A | B) = Probability of event A happening given that event B happens  
- P(B | A) = Probability of event B happening given that event A happens  
- P(A) = Probability of event A happening  
- P(B) = Probability of event B happening  

The Bayes Theorem thus gives us a way to find the Conditional Probability . Bayes Theorem lies in the heart of the Naive Bayes theorem.

Now we are in a position to describe Multinomial Naive – Bayes Theorem. As the name suggests, this theorem uses a Bayesian Classifier with a simplified assumption about how the features interact.

One of the most important assumptions we have considered in Naive-Bayes is called the **bag-of-words.** It implies that all the algorithm really cares about is the word and its frequency i.e. how many times the word has appeared in our data . The position of the word in our sentence(document) does not matter at all. We only have to keep track of the number of times a particular word appeared in our document . That’s it.

Let me explain with an example:

" _Tea makes me happy. Black Tea, Green Tea, Milk Tea, it does not matter what kind it is ; as long as it’s tea I am satisfied. I have grown up drinking tea and every sip reminds me of the good old days"_

Let’s analyze it further:

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1KlZogKOs83E1T-PFGeGmvg.png)image by author

This is basically what bag-of-words concept boils down to . It does not matter where the words _tea , I, happy , satisfied_ etc. have been used in the sentences , all that matters is it’s frequency.

![image from Unsplash](https://towardsdatascience.com/wp-content/uploads/2020/12/1FECFHfZVPk0Cb5eYRoGTxA-scaled.jpeg)image from [Unsplash](https://unsplash.com/photos/GkinCd2enIY)

## DERIVATION

Now let’s try to formulate this mathematically.

If you may recall, our main goal was to find the class (whether positive or negative sentiment) given a particular sentence(document). So we can approach this problem this way:

1. Suppose we have a set of possible classes C.  
2. We find the probability of a document being in a particular class.

So essentially conditional probability of a class given a document.

3. We iterate over all the classes and find which class has the maximum conditional probability ; giving us our answer.

Combining all the steps together we get :

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1y6IhsCE_PNtQU8OeoKJRKg.png)image by author

Here the term ĉ denotes the class with the maximum probability.

We were already introduced to the Bayes Theorem ; so now we can plug in the formula for conditional probability in eqt(2)

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1qwUpVLGTAu8VG-i8v9f51A.png)image by author

We can simplify this equation even more . While iterating over the classes our document of course does not change , only the class changes ; so we can safely remove the P(d) from our denominator without causing any major problems. So our modified equation thus becomes:

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1M2lALOx-mCVKDwnTLdTv3g.png)image by author

The term P(d|c) is called **likelihood probability**

The second term P(c) is called **prior probability**

We can simplify it even further by dividing each document into a collection of features _f1 , f2, f3, ……..fn._

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1MvEG8JNxfhSaknHG92U7ew.png)image by author

At this point of our derivation we will make a very important assumption . We will assume that the probability of each feature f given is class is **independent** of each other. This is a very crucial step and it reduces the time complexity of our problem by a huge margin. Let’s understand that a bit more.

If two events X and Y are independent of each other then the probability of the events occurring together (P(X and Y)) becomes:

P( X ∩ Y) = P(X) * P(Y)

which means:

P( f 1 | c ∩ f 2 | c) = P(f 1 | c) * P(f 2 | c)

We can simplify eqt(5) even further! Also , assuming the events are independent from each other we do not have to take into account how each feature is related to one another or the probability of one feature occurring given another feature. This saves us a lot of computing power.

Thus our final equation becomes:

P( f 1 , f 2 , …., f n |c) = P( f 1 |c) · P( f 2 |c) · … · P( f n |c) ->(6)

or

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1pV7z10F7i6kt98zfFfT0Mg.png)image by author

Now of course the features in a sentence would be it’s words… so if we replace the features in our equation with _wi_ for the word at the i-th position we can re-frame our equation as follows:

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1uT-XIRDcpknpnfQEyJkbUA.png)image by author

Phew!!!! we are finally done with the derivation. Now, lets move onto how we can apply this concept in a practical problem.

## TRAINING THE MODEL

1. **Calculate the Prior Probability** . We will first find the number of documents belonging to each class . Finding the percentage of the documents in each class will give us the required prior probability.

Let’s assume the number of documents in class _c_ is _Nc._

Total number of documents is assumed to be _Ntotal._

So , P(c) = _Nc / Ntotal ->_(9)

2. **Calculate the** **Likelihood Probability**. This is where it gets slightly tricky . Our main goal is to find the fraction of times the word wi appears among all words in all documents of class c. We first concatenate all documents with category c into one big "category c" text. Then we use the frequency of wi in this concatenated document to give the likelihood probability.

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1pWo8uekXtbaXvtSgxtkaGQ.png)image by author

Here V is for Vocabulary which is a collection of all words in all documents irrespective of class.

We will however face a very unique problem at this point. Suppose the document we have as input is ,

d = " _I loved that movie_"

The word "loved" is only present in the positive class and no examples of "loved" is present in the negative class input .Now from eqt(8) we have to find the probability by multiplying the likelihood probability for each class.If we calculate out likelihood probability for the word "loved" for the class "negative" we get:

P("loved" | "negative") = 0

Now if we plug in this value in eqt(8) the entire probability of our class "negative" becomes zero ; no matter what the other values are.

To combat this problem we will introduce an add-on , **Laplace Smoothing Coefficient** , to both the numerator and the denominator . Our equation will be modified as follows:

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1uh4VJ42XKKA8c31VZHBN2Q.png)image by author

Here a is the Laplace smoothing coefficient . We usually consider its value to be 1.

3. **Plug in the prior and the likelihood probability in eqt(8).**

Now that we have calculated our prior and likelihood probability we can simply go ahead and plug it in .

There are few ways we can optimize this process though:

a. **Using Logarithm**: if we apply log on both sides of eqt(8) we can convert the equation to a linear function of the features, which would increase efficiency quite a lot.

b. **Stop Words**: Words like _the, a , an , was , when_ etc. do not usually contribute to the sentiment of the statement . We can remove them entirely to streamline our model training.

c. **Unknown Words:** Every time you face a word which is present in the test dataset but absent in the vocabulary created from the training data , it is advisable to drop the words entirely and not consider them in the probability calculations.

d. **Binary Multinomial Naive-Bayes** : This is a slightly modified version of the multinomial Naive-Bayes. Here we are going to place more importance on whether a word is present or not than its frequency . As we have already seen a single word can bring about a massive change in the sentiment of the sentence and thus it would be a logical way to disregard how many times that particular word appeared in a sentence and concentrate whether that particular word is present or not in the document.

## SOLVED EXAMPLE

Finally , now that we are familiar with Naive Bayes classifiers we can implement this knowledge in an example .

### Training Dataset:

![image by autor](https://towardsdatascience.com/wp-content/uploads/2021/05/103XeZQLwvssSAXg5XsDf3w.png)image by autor

### Test Dataset:

![image by author](https://towardsdatascience.com/wp-content/uploads/2021/05/1XLj3HTB-j-blswiquPsLaA.png)image by author

This is a fictitious dataset on movie reviews. The movie reviews have been divided into positive and negative classes respectively.

Let’s Solve the problem: (we will consider smoothing coefficient, _a,_ as 1)

_For the first test case:_

**Prior probability:**

P(c = ‘positive’) = 3/6 = 1/2 , P(c = ‘negative’) = 3/6 = 1/2

**Likelihood probability:**

P(‘Great’ | c = ‘Positive’) = 1 + 1 / (9 + 19) = 0.0714

P(‘movie’ | c = ‘Positive’) = 2 + 1 /(9 + 19) = 0.1071

P(‘Great’ | c = ‘Negative’) = 0 + 1/(10 + 19) = 0.0344

P(‘movie’ | c = ‘Negative’) = 0 + 1/(10 + 19) = 0.0344

Finally we apply our findings in eqt(8) and return the maximum probability :

P(c = ‘positive’) _P(‘Great’ | c = ‘Positive’)_ P(‘movie’ | c = ‘Positive’) = 0.5 _0.0714_ 0.1071 = 0.00382

P(c = ‘negative’) _P(‘Great’ | c = ‘Negative’)_ P(‘movie’ | c = ‘Negative’) = 0.5 _0.0344_ 0.0344 = 0.000591

Thus we can say the test case belongs to _**positive**_ class.

_For the second test case:_

**Prior probability:**

P(c = ‘positive’) = 3/6 = 1/2 , P(c = ‘negative’) = 3/6 = 1/2

In this example we encounter unknown words : _this , is._ We will not consider them in our calculations.

**Likelihood probability:**

P(‘boring’ | c = ‘Positive’) = 0 + 1 / (9 + 19) = 0.03571

P(‘pathetic’ | c = ‘Positive’) = 0 + 1 /(9 + 19) = 0.03571

P(‘and’ | c = ‘Positive’) = 0 + 1 /(9 + 19) = 0.03571

P(‘boring’ | c = ‘Negative’) = 1 + 1 / (10+ 19) = 0.0689

P(‘pathetic’ | c = ‘Negative’) = 1 + 1 / (10 + 19) = 0.0689

P(‘and’ | c = ‘Negative’) = 1 + 1 / (10 + 19) = 0.0689

Finally we apply our findings in eqt(8) and return the maximum probability :

P(c = ‘positive’) _P(‘boring’ | c = ‘Positive’)_ P(‘pathetic’ | c = ‘Positive’) _P(‘and’ | c = ‘Positive’) = 0.5_ 0.03571 _0.03571_ 0.03571 = 0.00002277

P(c = ‘negative’) _P(‘Great’ | c = ‘Negative’)_ P(‘movie’ | c = ‘Negative’) = 0.5 _0.0689_ 0.0689 * 0.0689 = 0.00016354

Thus we can say the test case belongs to _**negative**_ class.

## CONCLUSION

Sentiment analysis is widely used in social media monitoring , market research etc. It is one of the most important aspects of Natural Language Processing . Naive – Bayes Classifier with a great first step towards Natural Language processing . Hopefully you enjoyed reading this article .

The python code implementing Binary Multinomial Naive-Bayes Classifier can be found in my [github repo](https://github.com/19-ade/Binary_multinomial_naive_bayes) . The dataset has also been included in the repo.
