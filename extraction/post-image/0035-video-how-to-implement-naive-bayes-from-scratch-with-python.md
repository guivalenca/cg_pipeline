---
id: "35"
title: "How to implement Naive Bayes from scratch with Python"
source_url: "https://www.youtube.com/watch?v=TLInuAorxqE"
fetch_url: "https://www.youtube.com/watch?v=TLInuAorxqE"
resolved_url: "https://www.youtube.com/watch?v=TLInuAorxqE"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T04:41:52.793219Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "708dc8839f113ebdbb8a875a5014944db46f752f27b9a3f760d5e5eb8a3b5703"
cache_keys:
  - "708dc8839f113ebdbb8a875a5014944db46f752f27b9a3f760d5e5eb8a3b5703"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 877.0
transcript_source: "local_whisper_vtt"
transcript_sha256: "b231678885223f1a2d7ff7f73d07e1dab5178cc6ec76e9508331d2388474922f"
word_count: 3079
char_count: 17820
content_sha256: "7408274d0e1d77cb2e0e7ca99b06552c3b5924308851c29e8a2cd6071cbd0f1a"
image_count: 16
link_count: 0
total_token_count: 57554
estimated_input_tokens: 47165
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Naive Bayes

**Spoken content:** Welcome to another video of the Machine Learning from Scratch course presented by Assembly AI. In this series, we implement popular machine learning algorithms using only built-in Python functions and NumPy. In this lesson, we learn about Naive Bayes. As always, we start with a short theory section and then we jump to the code. So let's get started.

**On-screen content:**
![slide: AssemblyAI Naive Bayes presented by Patrick Loeber](video-frame://35@00:00)

## [00:18] Naive Bayes Classifier Definition

**Spoken content:** So Naive Bayes is a probabilistic classifier based on applying Bayes' theorem with strong, also called naive, independence assumptions between the features.

**On-screen content:**
![slide: Naive Bayes classifier definition](video-frame://35@00:18)
The Naive Bayes classifier is a "probabilistic classifier" based on applying Bayes' theorem with strong (naive) independence assumptions between the features.

## [00:32] Bayes' Theorem

**Spoken content:** So let's learn about the Bayes' theorem first. It says that the probability of an event A given another event B can be calculated as the probability of B given A times the probability of A divided by the probability of B. So if we transfer this to our case with class labels and features, then we can say that the probability of Y given X is the probability of X given Y times the probability of Y divided by the probability of X. And in this case, Y are the class labels that we want to predict and X is the feature vector.

**On-screen content:**
![slide: Bayes' Theorem formula and its application to class labels and features](video-frame://35@00:32)
Bayes' Theorem
$P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}$

In our case:
$P(y|X) = \frac{P(X|y) \cdot P(y)}{P(X)}$
With feature vector $X = \{x_1, x_2, x_3, ..., x_n\}$

## [01:09] Assumption of Mutually Independent Features

**Spoken content:** So then we do the assumption that the features are mutually independent. For example, if we want to predict if someone takes the bus or walks, and we have two features if it's raining or not, and the distance to the destination. So then we make the assumption that these two features are independent. And in reality, often this is not the case, but this assumption still works really well for this classifier. That's also why we say this is a naive assumption.

**On-screen content:**
![slide: Assumption that features are mutually independent](video-frame://35@01:09)
Assume that features are mutually independent
$P(y|X) = \frac{P(X|y) \cdot P(y)}{P(X)}$

## [01:38] Splitting P(X|y) and Log-Trick

**Spoken content:** So if we make this assumption, we can split this part here, P of X given Y, into the different components and say this is the product. So P of X1 given Y times P of X2 given Y and so on. And these are all the single feature vector components. And these probabilities here are easier to set up. So now we want to select the class label Y. So we want to select the class with the highest posterior probability. So this P of Y given X is also called the posterior. And this is the formula we've just seen. So now we want to select Y as the argmax of the posterior. And then we can simplify this a little bit. So we can first get rid of P of X because this depends not on Y at all. So just throw this away. And then we also apply a little trick. So all these probabilities here are values between zero and one. And if we multiply this, then the number can become very small and we can run into inaccuracies. So for this, we apply a little trick. Instead of the product, we do a sum. And then we apply the logarithm. So if you apply the logarithm, we can change the product with a sum. And then this is the final formula to get Y.

**On-screen content:**
![slide: Splitting P(X|y) into product of individual probabilities and applying log-trick](video-frame://35@01:38)
Assume that features are mutually independent
$P(y|X) = \frac{P(X|y) \cdot P(y)}{P(X)}$
$\downarrow$
$P(y|X) = \frac{P(x_1|y) \cdot P(x_2|y) \cdot \dots \cdot P(x_n|y) \cdot P(y)}{P(X)}$

## [02:03] Selecting Class with Highest Posterior Probability

**Spoken content:** And now we need to know how we can calculate P of Y and also this P of X given Y.

**On-screen content:**
![slide: Formula for selecting class with highest posterior probability, simplified with log](video-frame://35@02:03)
Select class with highest posterior probability
$P(y|X) = \frac{P(x_1|y) \cdot P(x_2|y) \cdot \dots \cdot P(x_n|y) \cdot P(y)}{P(X)}$
$\downarrow$
$y = \text{argmax}_y P(y|X) = \text{argmax}_y \frac{P(x_1|y) \cdot P(x_2|y) \cdot \dots \cdot P(x_n|y) \cdot P(y)}{P(X)}$
$\downarrow$
$y = \text{argmax}_y (P(x_1|y) \cdot P(x_2|y) \cdot \dots \cdot P(x_n|y) \cdot P(y))$
$\downarrow$
$y = \text{argmax}_y (\log(P(x_1|y)) + \log(P(x_2|y)) + \dots + \log(P(x_n|y)) + \log(P(y)))$

## [03:07] Prior and Class Conditional Probabilities

**Spoken content:** So these are called the prior and class conditional. So first P of Y is called the prior probability, and we can simply calculate this as the frequency of each class. So we count how often this class label occurs. And then the P of Xi given Y is known as the class conditional probability. And for this, we model this with a Gaussian distribution. So here, this is the formula, where we have the mean and the standard deviation or then squared, this is the variance. So here we can see a plot of different Gaussian distributions for different means and standard deviations. So yeah, this is often a good choice to model probabilities.

**On-screen content:**
![slide: Prior and class conditional probabilities with Gaussian distribution formula and plot](video-frame://35@03:07)
Prior and class conditional
$P(y)$ (Prior probability) -> Frequency of each class
$P(x_i|y)$ (Class conditional probability) -> Model with Gaussian
$P(x_i|y) = \frac{1}{\sqrt{2\pi\sigma_y^2}} \exp(-\frac{(x_i - \mu_y)^2}{2\sigma_y^2})$
![diagram: Gaussian distribution plots with different means and standard deviations](video-frame://35@03:34)

## [03:53] Steps for Naive Bayes

**Spoken content:** And yeah, this is all that we need to code this up. So let's summarize the different steps. In the training step, we calculate the mean, the variance and the prior, so the frequency for each class with our training set. And then in the prediction step, we calculate the posterior for each class with the formula that we've just seen. And here we also plug in the Gaussian formula for these probabilities. And then we simply choose the class with the highest posterior probability. And that's it. So let's jump to the code.

**On-screen content:**
![slide: Steps for Naive Bayes training and predictions](video-frame://35@03:53)
Steps
Training:
*   Calculate mean, var, and prior (frequency) for each class
Predictions:
*   Calculate posterior for each class with
    $y = \text{argmax}_y (\log(P(x_1|y)) + \log(P(x_2|y)) + \dots + \log(P(x_n|y)) + \log(P(y)))$
    and Gaussian formula
*   Choose class with highest posterior probability

## [04:23] Python Class Structure

**Spoken content:** So first, let's import NumPy, of course, and then we want to create a class that we call Naive Bayes. And here we don't need an init function because we don't have any parameters to configure this. So instead, we want a fit method, which gets the training samples and the training labels. And then we also want a predict method with self and the test samples. So let's start with fit.

**On-screen content:**
![code: Naive Bayes class definition with fit and predict methods](video-frame://35@04:23)
```python
import numpy as np

class NaiveBayes:

    def fit(self, X, y):
        pass

    def predict(self, X):
        pass
```

## [04:54] Fit Method: Initial Setup

**Spoken content:** So here we want to get the number of samples and the number of features first. And we have this assumption that X and Y are already NumPy and D array. So this is already in the correct format. And then we can extract this by saying X dot shape with a small s X dot shape. Then let's get the number of unique classes and we store this in self dot underscore classes equals NumPy unique with Y. And then we get the number of different classes by saying the length of self dot underscore classes.

**On-screen content:**
![code: Fit method extracting sample and feature counts, and unique classes](video-frame://35@04:54)
```python
import numpy as np

class NaiveBayes:

    def fit(self, X, y):
        n_samples, n_features = X.shape
        self._classes = np.unique(y)
        n_classes = len(self._classes)

    def predict(self, X):
        pass
```

## [05:41] Fit Method: Calculate Mean, Variance, and Prior

**Spoken content:** And now the first thing we want to do is we want to calculate the mean, the variance and the prior for each class. So for this, let's initialize these with zeros first. So we say self dot underscore mean equals NumPy dot zeros. And now as a shape, we want to have n classes times n features. And then as data type, we can also say this is a NumPy float 64. So this is the default, but just to make this more clear that we work with floats here. And then let's copy this one time. So we also do the same for the variance. So we say self dot var equals this. And then also for the priors. So we say self dot priors, but here we only want n classes. So for each class, we want to have a prior. And now we want to calculate these. So we say for index and C in enumerate self dot underscore classes, then we only want to get the samples of this class. So X C equals X where Y equals equals C. And then we want to calculate the mean variance and prior and assign this. So we say self dot underscore mean and then of the current index. So for this class, and then for all the columns. So for all features, we can say this is simply X C dot mean along axis equals zero. And then we do the same for the variance. So we also say self dot var and here we can apply X dot var. So these are built in NumPy functions. And then for the priors, we say self dot underscore priors and of this index and this is X C dot shape zero. So this is the number of the how many samples we have divided by the as float the number of total samples. And now these are the priors. So now this is all that we have to do in the fit method.

**On-screen content:**
![code: Fit method calculating mean, variance, and prior for each class](video-frame://35@05:41)
```python
import numpy as np

class NaiveBayes:

    def fit(self, X, y):
        n_samples, n_features = X.shape
        self._classes = np.unique(y)
        n_classes = len(self._classes)

        # calculate mean, var, and prior for each class
        self._mean = np.zeros((n_classes, n_features), dtype=np.float64)
        self._var = np.zeros((n_classes, n_features), dtype=np.float64)
        self._priors = np.zeros(n_classes, dtype=np.float64)

        for idx, c in enumerate(self._classes):
            X_c = X[y == c]
            self._mean[idx, :] = X_c.mean(axis=0)
            self._var[idx, :] = X_c.var(axis=0)
            self._priors[idx] = X_c.shape[0] / float(n_samples)

    def predict(self, X):
        pass
```

## [08:27] Predict Method: Helper Function and Posterior Calculation

**Spoken content:** So let's go on with predict. So here, let's say Y prediction equals and then we use list comprehension and use a helper function underscore predict where we only put in one small feature component X for small X in large X. And then we want to return this as NumPy array. So let's say NumPy array of Y predict. And then we create this underscore predict which gets self and only a small X. So only one component. And here we want to calculate the posterior. So let's initialize this with an empty list. And then let's say let's write a comment. So we want to calculate the posterior probability for each class. So we say for index and C in enumerate self dot underscore classes, so the same enumeration that we do here. And then let's calculate this. So we say first the prior. And let's go back to the formula. So here we have this. So we have the logarithm of the prior plus the logs of all the class conditionals. So for this, we say NumPy log. And then we can simply access this. So we already calculated the priors. And then of this current class index. And then for the posterior, we say this is NumPy sum over NumPy log. And then here we want to apply the Gaussian distribution. So for this, we create a helper function that we call self dot underscore PDF for probability density function. And then this should get the index and the X. And then we have the posterior. So now we want to add this to the prior. So we say posterior equals posterior plus prior and then we append this to the list. So we say posteriors dot append the current posterior.

**On-screen content:**
![code: Predict method with helper function and posterior calculation loop](video-frame://35@08:27)
```python
    def predict(self, X):
        y_pred = [self._predict(x) for x in X]
        return np.array(y_pred)

    def _predict(self, x):
        posteriors = []

        # calculate posterior probability for each class
        for idx, c in enumerate(self._classes):
            prior = np.log(self._priors[idx])
            posterior = np.sum(np.log(self._pdf(idx, x)))
            posterior = posterior + prior
            posteriors.append(posterior)
```

## [10:57] Predict Method: Return Class with Highest Posterior

**Spoken content:** And then in the end, we want to return the class with the highest posterior. So here we say return and then self dot underscore classes off. And now here we want to say NumPy argmax of the Posteriors. And this is all that we need for predict.

**On-screen content:**
![code: Predict method returning the class with the highest posterior](video-frame://35@10:57)
```python
    def predict(self, X):
        y_pred = [self._predict(x) for x in X]
        return np.array(y_pred)

    def _predict(self, x):
        posteriors = []

        # calculate posterior probability for each class
        for idx, c in enumerate(self._classes):
            prior = np.log(self._priors[idx])
            posterior = np.sum(np.log(self._pdf(idx, x)))
            posterior = posterior + prior
            posteriors.append(posterior)

        # return class with the highest posterior
        return self._classes[np.argmax(posteriors)]
```

## [11:29] PDF Function (Gaussian Probability Density Function)

**Spoken content:** So now we only need the probability density function. So let's say self a define underscore PDF. This gets self. Then it gets the class index and X. And here, let's have a brief look at the formula again. So this here is the formula with the means and the variances. And let's split this into denominator and numerator. So let's first get the mean. So we say mean equals self dot underscore mean of this class index and the same for the variance. So we say var equals self dot underscore var of this class index. And then we say the numerator equals and now we apply this. So we say NumPy. This is the exponential function of minus and then we say X minus the mean to the power of two divided by two times the variance. So let's put this into parentheses as well. And also this part. So the minus and then this and then for the denominator equals so this is NumPy square root over and here we have two times NumPy dot pi times the variance. So then we want to return the numerator divided by the denominator. And this is all that we need. So now we are done and now we can test this.

**On-screen content:**
![code: PDF method implementing the Gaussian probability density function](video-frame://35@11:29)
```python
    def _pdf(self, class_idx, x):
        mean = self._mean[class_idx, :]
        var = self._var[class_idx, :]
        numerator = np.exp(- ((x - mean) ** 2) / (2 * var))
        denominator = np.sqrt(2 * np.pi * var)
        return numerator / denominator
```

## [13:31] Testing the Naive Bayes Classifier

**Spoken content:** So I already prepared some code for testing and let's go over this very quickly. You can also find the whole code on GitHub. So we import data sets and train test split from sklearn. Then let's have a helper function to calculate the accuracy. Then we call data sets make classification and create a toy data set with 1000 samples and 10 features and two classes. Then we split this into training and testing. Then we create our Naive Bayes classifier and call fit with the training samples and then we call predict with the test samples. And then we calculate the accuracy by comparing Y test and the predictions. And now let's run this and we see the accuracy is 96.5%. So it works pretty well. So yeah, this is all. I hope you enjoyed this and then I hope to see you in the next lesson.

**On-screen content:**
![code: Testing code for Naive Bayes classifier, including imports, accuracy function, dataset generation, training, prediction, and output](video-frame://35@13:31)
```python
if __name__ == "__main__":
    # Imports
    from sklearn.model_selection import train_test_split
    from sklearn import datasets

    def accuracy(y_true, y_pred):
        accuracy = np.sum(y_true == y_pred) / len(y_true)
        return accuracy

    X, y = datasets.make_classification(
        n_samples=1000, n_features=10, n_classes=2, random_state=123
    )
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=123
    )

    nb = NaiveBayes()
    nb.fit(X_train, y_train)
    predictions = nb.predict(X_test)

    print("Naive Bayes classification accuracy", accuracy(y_test, predictions))
```
**Terminal output:**
```
Naive Bayes classification accuracy 0.965
