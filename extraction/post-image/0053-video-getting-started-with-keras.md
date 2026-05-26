---
id: "53"
title: "Getting Started with Keras"
source_url: "https://www.youtube.com/watch?v=J6Ok8p463C4"
fetch_url: "https://www.youtube.com/watch?v=J6Ok8p463C4"
resolved_url: "https://www.youtube.com/watch?v=J6Ok8p463C4"
firecrawl_title: null
description: null
fetched_at: "2026-05-12T05:48:56.355093Z"
provider: "gemini_multimodal"
strategy: "video_gemini_two_pass"
cache_key: "a3faa88e9071aba6e4dc5a6eade97b9aa2b7bde6324da8383d7be42a9d9cb73d"
cache_keys:
  - "a3faa88e9071aba6e4dc5a6eade97b9aa2b7bde6324da8383d7be42a9d9cb73d"
gemini_model: "gemini-2.5-flash"
gemini_media_resolution: "low"
gemini_fps: 0.33
prompt_version: "video_gemini_pass2_v1"
duration_seconds: 491.0
transcript_source: "manual_captions"
transcript_sha256: "ea608f2991bbf0cf8a9f8c75db5f2c94a395ebd3a67016ca6111122017551245"
word_count: 2557
char_count: 14730
content_sha256: "811a55ecce6dd5ac49c18ca27a413aa5fcd6d7e2634830323c43bbb783f18f83"
image_count: 28
link_count: 0
total_token_count: 34165
estimated_input_tokens: 26405
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

## [00:00] Introduction to Keras

**Spoken content:**
- [00:00] YUFENG GUO: Keeras?
- [00:02] Kaaris?
- [00:03] Kras?
- [00:05] Keras?
- [00:06] Carrots?
- [00:07] Keras.
- [00:09] What is Keras, and how can you use
- [00:11] it to get started creating your own machine learning models?
- [00:15] Stay tuned to find out.
- [00:17] [ELECTRONIC BEEPING]

**On-screen content:**
![text: Keeras? Kaaris? Kras? Keras? Carrots? Keras.](video-frame://53@00:00)
![animated satellite and stars with Google Cloud AI Adventures title card](video-frame://53@00:24)

## [00:25] Welcome to Cloud AI Adventures

**Spoken content:**
- [00:25] Welcome to Cloud AI Adventures, where
- [00:28] we explore the art, science, and tools of machine learning.
- [00:33] My name is Yufeng Guo.
- [00:34] And on this episode of AI Adventures,
- [00:37] I'll show you how to get started with Keras in the quickest way
- [00:40] possible.

**On-screen content:**
![Google Cloud AI Adventures title card with "Playing around with Keras" and speaker name Yufeng Guo](video-frame://53@00:24)

## [00:41] Keras Integration and Kaggle Kernels

**Spoken content:**
- [00:41] It's never been easier to get started with Keras.
- [00:45] Not only is Keras built into TensorFlow
- [00:47] via tensorflow.keras, you also don't even
- [00:51] have to install or configure anything
- [00:53] if you use a tool like Kaggle Kernels.
- [00:56] All you need to do is create your Kaggle account if needed
- [00:59] and sign in.
- [01:00] Then you have access to all that Keras has to offer.
- [01:04] Keras also exists as a standalone library,
- [01:08] but the TensorFlow version has the exact same APIs
- [01:11] and some extra features.
- [01:13] Let's head over to my Kaggle Kernel,
- [01:14] where I'll show you how to get started using Keras right now.

**On-screen content:**
![TensorFlow documentation page for Keras](video-frame://53@00:41)
![Kaggle Kernel UI showing a Python notebook](video-frame://53@00:54)
```python
from tensorflow import keras
keras.__version__
```
![Kaggle Kernel output showing Keras version '2.1.6-tf'](video-frame://53@01:12)

## [01:18] Fashion-MNIST Dataset and Initial Imports

**Spoken content:**
- [01:18] In a previous episode, we did some machine learning
- [01:21] on the dataset Fashion-MNST.
- [01:23] It's a dataset of 10 different types of fashionable items,
- [01:27] from pants and shirts to shoes and handbags,
- [01:30] all presented in 28 by 28 pixel grayscale.
- [01:33] Mmm, grayscale.
- [01:36] Today, we'll do a similar analysis using Keras.
- [01:40] So to use Keras, we'll just import TensorFlow like usual.
- [01:44] These imports are actually identical to what
- [01:46] we had before.
- [01:48] And we'll pull in numpy, and pandas, and natplotlib
- [01:51] just as we normally would.

**On-screen content:**
![Kaggle Kernel code for importing libraries](video-frame://53@01:18)
```python
# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load in 

import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import matplotlib.pyplot as plt

# Input data files are available in the "../input/" directory.
# For example, running this (by clicking run or pressing Shift+Enter) will list the files in the input directory

from subprocess import check_output
print(check_output(["ls", "../input"]).decode("utf8"))

# Any results you write to the current directory are saved as output.
```
![Kaggle Kernel output showing fashion-mnist dataset files](video-frame://53@01:46)

## [01:52] Preprocessing the Data

**Spoken content:**
- [01:54] And we continue operating kind of in the usual way.
- [01:57] We'll pull in our training and test CSVs
- [02:00] and load them up in pandas and take a look
- [02:02] at what they look like.
- [02:04] We've got our Label column on the far left
- [02:06] with numbers from zero through nine.
- [02:09] And we have our Pixels--
- [02:10] pixel 1, 2, 3, all the way up to pixel 784.
- [02:15] I've got a function here to preprocess
- [02:17] our data a little bit.
- [02:18] It's similar to what we had before.
- [02:19] I've just cleaned it up and made it a little more concise.
- [02:22] I'm pulling out the features and dividing by 255,
- [02:25] so we normalize all the grayscale values
- [02:27] to be between zero and one.
- [02:29] And I'll pull out the labels as well
- [02:31] and have them both be represented as an numpy arrays.
- [02:36] We use that function to pull out our training and test
- [02:39] data from the data frame and associate them
- [02:42] to explicit variables-- train_features
- [02:44] and train_labels, test_features and test_labels.
- [02:48] And we can see that the final shape of these variables
- [02:52] are exactly as we would expect--
- [02:54] 60,000 examples with 784 columns.
- [02:59] And then our labels are just the 60,000 values.
- [03:02] And we're going to take a peek at one of them.
- [03:04] This is our 20th training_feature set.
- [03:07] And some pixels in the middle, we
- [03:09] can see that they're indeed values between zero and one.
- [03:12] And we can also visualize it.
- [03:14] Here we have a shirt, and we can see that it looks exactly
- [03:17] as you'd expect--
- [03:18] kind of grainy and grayscale.

**On-screen content:**
![Kaggle Kernel code for loading CSVs and displaying head of training data](video-frame://53@01:52)
```python
data_train_file = "../input/fashion-mnist_train.csv"
data_test_file = "../input/fashion-mnist_test.csv"
df_train = pd.read_csv(data_train_file)
df_test = pd.read_csv(data_test_file)

df_train.head()
```
![Pandas DataFrame head showing 'label' and 'pixel' columns](video-frame://53@02:00)
![Kaggle Kernel code for get_features_labels function and applying it](video-frame://53@02:14)
```python
def get_features_labels(df):
    # Select all columns but the first
    features = df.values[:, 1:]/255
    # The first column is the label. Conveniently called 'label'
    labels = df['label'].values
    return features, labels

train_features, train_labels = get_features_labels(df_train)
test_features, test_labels = get_features_labels(df_test)

print(train_features.shape)
print(train_labels.shape)
print(test_features.shape)
print(test_labels.shape)
```
![Kaggle Kernel output showing shapes of training and test data (60000, 784) and (60000,)](video-frame://53@02:47)
![Kaggle Kernel code and output showing an example feature set](video-frame://53@03:01)
```python
# take a peek at some values in an image
train_features[20, 300:320]
```
![NumPy array output of pixel values](video-frame://53@03:05)
![Kaggle Kernel code and output showing a grayscale image of a shirt](video-frame://53@03:12)
```python
example_index = 22
plt.imshow(np.reshape(train_features[example_index], (28, 28)), cmap='gray')
```
![grayscale image of a shirt](video-frame://53@03:15)

## [03:21] Convert Labels to One-Hot Encoding

**Spoken content:**
- [03:22] Now, with Keras in this particular case,
- [03:24] we're going to need to one-hot hot encode our data.
- [03:27] And what that means is we're going to take our training
- [03:29] labels, which used to be just values like zero, three, seven,
- [03:35] and turn them into--
- [03:37] each of them-- into an array of length 10.
- [03:40] All 10 values in the array will be zeros except for one value.
- [03:45] That one value will be a 1.
- [03:47] And so that's why it's called one-hot encoding.
- [03:50] Now, where is that one located?
- [03:52] It's going to be exactly the number that it came from.
- [03:57] So, for example, if the value was seven,
- [03:59] the seventh zero will be a one.
- [04:01] If the number was four, then the fourth zero will be a one--
- [04:05] hence one-hot encoding.
- [04:07] And so we'll run Keras wtils.to_categorical,
- [04:11] which is a handy utility function that will just do this
- [04:14] for us.
- [04:15] And we'll observe that the train labels have now
- [04:17] turned from 60,000 rows of numbers
- [04:21] to 60,000 rows with 10 columns.
- [04:24] And we can see that indeed, in that same example label that we
- [04:28] saw before now, the zeroth index has a 1,
- [04:32] and everything else remains a zero.

**On-screen content:**
![Kaggle Kernel code and output showing original label shape (60000,) and an example label (0)](video-frame://53@03:21)
```python
train_labels.shape
train_labels[example_index]
```
![Kaggle Kernel code for one-hot encoding labels](video-frame://53@04:06)
```python
train_labels = tf.keras.utils.to_categorical(train_labels)
test_labels = tf.keras.utils.to_categorical(test_labels)

train_labels.shape
```
![Kaggle Kernel output showing new label shape (60000, 10)](video-frame://53@04:15)
![Kaggle Kernel output showing an example one-hot encoded label](video-frame://53@04:25)
```python
train_labels[example_index]
```
![NumPy array output of one-hot encoded label `array([1., 0., 0., 0., 0., 0., 0., 0., 0., 0.], dtype=float32)`](video-frame://53@04:29)

## [04:34] Creating the Model

**Spoken content:**
- [04:35] And now comes the really fun part of working with Keras--
- [04:39] creating our model.
- [04:41] Keras supplies a really easy and intuitive way
- [04:44] to build up your model from the ground up.
- [04:49] In this case, we're going to make a sequential model
- [04:51] and add layers on top of it.
- [04:54] The first letter we'll have has 30 nodes
- [04:57] and has an activation function of a rectified linear unit
- [05:00] for relu, which in the case of TensorFlow that we used before,
- [05:04] was the default activation function.
- [05:07] Then we'll have another fully-connected layer
- [05:10] or dense layer with 20 neurons, this time
- [05:13] also with a relu function.
- [05:15] And finally, we'll do our final mapping to the 10 output
- [05:19] values of zero through nine and have an activation
- [05:22] of the softmax, which basically just distributes
- [05:25] power probabilities across the 10 buckets.
- [05:30] And now we're ready to compile our model.
- [05:33] Keras uses this notation of compiling
- [05:35] a model as similar to when you do something
- [05:38] like string builder or something to just say, I'm done.
- [05:41] Put it all together for me.
- [05:43] And we'll supply a loss, optimizer, and metrics
- [05:46] for what kind of values we want to get out of it, for how
- [05:50] to optimize for the best values, as well as
- [05:54] how we want to measure loss.
- [05:55] In this case, we're using categorical cross entropy
- [05:59] because our outputs are categorical.
- [06:01] And cross entropy, in this case, happens to be a nice way
- [06:04] to measure our loss or error.

**On-screen content:**
![Kaggle Kernel code for creating and compiling a Keras sequential model](video-frame://53@04:34)
```python
# Create the model
model = tf.keras.Sequential()
model.add(tf.keras.layers.Dense(30, activation=tf.nn.relu, input_shape=[784,]))
model.add(tf.keras.layers.Dense(20, activation=tf.nn.relu))
model.add(tf.keras.layers.Dense(10, activation=tf.nn.softmax))

# We will now compile and print out a summary of our model
model.compile(loss='categorical_crossentropy',
              optimizers='rmsprop',
              metrics=['accuracy'])
```
![Keras model summary output showing layer types, output shapes, and parameter counts](video-frame://53@06:06)

## [06:06] Training with Keras

**Spoken content:**
- [06:08] With our model created, we're ready to run training.
- [06:11] Training with Keras is as easy as calling .fit.
- [06:15] When we call .fit, all we need to supply are
- [06:17] the training_features and training_labels.
- [06:20] It's also a good idea to supply epochs and batch_size
- [06:24] so that we can control the training a little more.
- [06:26] In this case, we have supplied an epoch
- [06:28] of two, which means we'll go through the entire dataset
- [06:31] twice over.
- [06:32] And we'll supply a batch_size of 128.
- [06:35] This means that with each training step,
- [06:38] the model will see 128 examples which will help guide
- [06:41] it to adjust its parameters.
- [06:44] And so we can see here Keras has some really useful helpless
- [06:47] as the training happens and gives us
- [06:49] a sense of the progress.
- [06:51] It also then prints out the loss and accuracy
- [06:53] at the end of each epoch.
- [06:57] But seeing the accuracy at the end loss at the end of training
- [07:01] isn't nearly as useful as evaluation.
- [07:04] We need to see the accuracy against our actual test
- [07:07] dataset.
- [07:08] So let's call our model.evaluate function
- [07:12] and this time pass in our test_features and test_labels.
- [07:16] This will give us an accuracy, and we can
- [07:18] print that out and take a look.
- [07:20] We can see we got 84.7% accuracy.
- [07:24] And of course, we could certainly
- [07:25] do better than that with increased epochs,
- [07:28] a more sophisticated model, and other approaches.

**On-screen content:**
![Kaggle Kernel code for setting epochs and batch size, and calling model.fit](video-frame://53@06:06)
```python
EPOCHS=2
BATCH_SIZE=128

model.fit(train_features, train_labels, epochs=EPOCHS, batch_size=BATCH_SIZE)
```
![Kaggle Kernel output showing training progress for 2 epochs, including loss and accuracy](video-frame://53@06:44)
![Kaggle Kernel code for evaluating the model on test data](video-frame://53@06:55)
```python
test_loss, test_acc = model.evaluate(test_features, test_labels)
print('test_acc', test_acc)
```
![Kaggle Kernel output showing test accuracy of 0.8475](video-frame://53@07:19)

## [07:31] Conclusion

**Spoken content:**
- [07:31] But this is just an intro to Keras.
- [07:33] And hopefully, this will give you a good starting point
- [07:37] to start playing around with Keras
- [07:39] and seeing all that Keras can do.
- [07:43] Keras has an amazing community and lots
- [07:45] of samples which, when you combine
- [07:48] with Kaggle's community, gives you
- [07:49] a truly epic set of resources to get you started the right way.
- [07:54] Thanks for watching this episode of Cloud AI Adventures.
- [07:57] And if you enjoyed it, please like it
- [07:59] and be sure to subscribe to get all the latest episodes right
- [08:03] when they come out.
- [08:04] Now, what are you waiting for?
- [08:06] Head on over to Kaggle and start playing around with Keras
- [08:09] today.

**On-screen content:**
![Speaker smiling](video-frame://53@07:43)
![Google Cloud AI Adventures title card with "Thank You!" and speaker's Twitter handle @YufengG](video-frame://53@07:52)
