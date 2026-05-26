---
id: "51"
title: "ATIVIDADE: Implementação de uma rede neural com Python"
source_url: "https://machinelearningmastery.com/tutorial-first-neural-network-python-keras/"
fetch_url: "https://machinelearningmastery.com/tutorial-first-neural-network-python-keras"
resolved_url: "https://machinelearningmastery.com/tutorial-first-neural-network-python-keras/"
firecrawl_title: "Your First Deep Learning Project in Python with Keras Step-by-Step - MachineLearningMastery.com"
description: "Keras Tutorial: Keras is a powerful easy-to-use Python library for developing and evaluating deep learning models. Develop Your First Neural Network in Python With this step by step Keras Tutorial!"
fetched_at: "2026-05-12T03:59:52.069694Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "a6dffcb378b76680acf98c1fd97573389e23e6dacf98d5e62974e32f8696759e"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=UTF-8"
word_count: 2766
char_count: 16711
content_sha256: "4cdef74c3dc13f5301ae6f444da7ca7315253b9317988b393d2d8b9bf6fa6333"
image_count: 7
link_count: 45
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "separate_screenshot"
  - "template_heavy_blog_domain_scoped_main_content"
---

**Keras** is a powerful and easy-to-use free open source Python library for developing and evaluating _**[deep learning](https://machinelearningmastery.com/what-is-deep-learning/) models**_.

It is part of the [TensorFlow](https://machinelearningmastery.com/tensorflow-tutorial-deep-learning-with-tf-keras/) library and allows you to define and train neural network models in just a few lines of code.

In this tutorial, you will discover how to create your first deep learning neural network model in Python using Keras.

**Kick-start your project** with my new book [Deep Learning With Python](https://machinelearningmastery.com/deep-learning-with-python/), including _step-by-step tutorials_ and the _Python source code_ files for all examples.

_Let’s get started._

- **Update Feb/2017**: Updated prediction example, so rounding works in Python 2 and 3.
- **Update Mar/2017**: Updated example for the latest versions of Keras and TensorFlow.
- **Update Mar/2018**: Added alternate link to download the dataset.
- **Update Jul/2019**: Expanded and added more useful resources.
- **Update Sep/2019**: Updated for Keras v2.2.5 API.
- **Update Oct/2019**: Updated for Keras v2.3.0 API and TensorFlow v2.0.0.
- **Update Aug/2020**: Updated for Keras v2.4.3 and TensorFlow v2.3.
- **Update Oct/2021**: Deprecated predict_class syntax
- **Update Jun/2022**: Updated to modern TensorFlow syntax

![Tour of Deep Learning Algorithms](https://machinelearningmastery.com/wp-content/uploads/2016/04/Tour-of-Deep-Learning-Algorithms.jpg)

Develop your first neural network in Python with Keras step-by-step

Photo by Phil Whitehouse, some rights reserved.

## Keras Tutorial Overview

There is not a lot of code required, but we will go over it slowly so that you will know how to create your own models in the future.

_The steps you will learn in this tutorial are as follows:_

1. Load Data
2. Define Keras Model
3. Compile Keras Model
4. Fit Keras Model
5. Evaluate Keras Model
6. Tie It All Together
7. Make Predictions

**This Keras tutorial makes a few assumptions. You will need to have:**

1. Python 2 or 3 installed and configured
2. SciPy (including NumPy) installed and configured
3. Keras and a backend (Theano or TensorFlow) installed and configured

If you need help with your environment, see the tutorial:

- [How to Setup a Python Environment for Deep Learning](https://machinelearningmastery.com/setup-python-environment-machine-learning-deep-learning-anaconda/)

Create a new file called **keras_first_network.py** and type or copy-and-paste the code into the file as you go.

## 1. Load Data

The first step is to define the functions and classes you intend to use in this tutorial.

You will use the [NumPy library](https://www.numpy.org/) to load your dataset and two classes from the [Keras library](https://www.tensorflow.org/api_docs/python/tf/keras) to define your model.

The imports required are listed below.

```python
# first neural network with keras tutorial
from numpy import loadtxt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
...
```

You can now load our dataset.

In this Keras tutorial, you will use the Pima Indians onset of diabetes dataset. This is a standard machine learning dataset from the UCI Machine Learning repository. It describes patient medical record data for Pima Indians and whether they had an onset of diabetes within five years.

As such, it is a binary classification problem (onset of diabetes as 1 or not as 0). All of the input variables that describe each patient are numerical. This makes it easy to use directly with neural networks that expect numerical input and output values and is an ideal choice for our first neural network in Keras.

The dataset is available here:

- [Dataset CSV File (pima-indians-diabetes.csv)](https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.data.csv)
- [Dataset Details](https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.names)

Download the dataset and place it in your local working directory, the same location as your Python file.

Save it with the filename:

|     |     |
| --- | --- |
| 1 | pima-indians-diabetes.csv |

Take a look inside the file; you should see rows of data like the following:

```text
6,148,72,35,0,33.6,0.627,50,1
1,85,66,29,0,26.6,0.351,31,0
8,183,64,0,0,23.3,0.672,32,1
1,89,66,23,94,28.1,0.167,21,0
0,137,40,35,168,43.1,2.288,33,1
...
```

You can now load the file as a matrix of numbers using the NumPy function [loadtxt()](https://docs.scipy.org/doc/numpy/reference/generated/numpy.loadtxt.html).

There are eight input variables and one output variable (the last column). You will be learning a model to map rows of input variables (X) to an output variable (y), which is often summarized as _y = f(X)_.

The variables can be summarized as follows:

Input Variables (X):

1. Number of times pregnant
2. Plasma glucose concentration at 2 hours in an oral glucose tolerance test
3. Diastolic blood pressure (mm Hg)
4. Triceps skin fold thickness (mm)
5. 2-hour serum insulin (mu U/ml)
6. Body mass index (weight in kg/(height in m)^2)
7. Diabetes pedigree function
8. Age (years)

Output Variables (y):

1. Class variable (0 or 1)

Once the CSV file is loaded into memory, you can split the columns of data into input and output variables.

The data will be stored in a 2D array where the first dimension is rows and the second dimension is columns, e.g., \[rows, columns\].

You can split the array into two arrays by selecting subsets of columns using the standard NumPy [slice operator](https://machinelearningmastery.com/index-slice-reshape-numpy-arrays-machine-learning-python/) or “:”. You can select the first eight columns from index 0 to index 7 via the slice 0:8. We can then select the output column (the 9th variable) via index 8.

```python
...
# load the dataset
dataset=loadtxt('pima-indians-diabetes.csv',delimiter=',')
# split into input (X) and output (y) variables
X=dataset[:,0:8]
y=dataset[:,8]
...
```

You are now ready to define your neural network model.

**Note:** The dataset has nine columns, and the range 0:8 will select columns from 0 to 7, stopping before index 8. If this is new to you, then you can learn more about array slicing and ranges in this post:

- [How to Index, Slice, and Reshape NumPy Arrays for Machine Learning in Python](https://machinelearningmastery.com/index-slice-reshape-numpy-arrays-machine-learning-python/)

## 2. Define Keras Model

Models in Keras are defined as a sequence of layers.

We create a _[Sequential model](https://keras.io/models/sequential/)_ and add layers one at a time until we are happy with our network architecture.

The first thing to get right is to ensure the input layer has the correct number of input features. This can be specified when creating the first layer with the **input_shape** argument and setting it to `(8,)` for presenting the eight input variables as a vector.

How do we know the number of layers and their types?

This is a tricky question. There are heuristics that you can use, and often the best network structure is found through a process of trial and error experimentation ( [I explain more about this here](https://machinelearningmastery.com/how-to-configure-the-number-of-layers-and-nodes-in-a-neural-network/)). Generally, you need a network large enough to capture the structure of the problem.

In this example, let’s use a fully-connected network structure with three layers.

Fully connected layers are defined using the [Dense class](https://keras.io/layers/core/). You can specify the number of neurons or nodes in the layer as the first argument and the activation function using the **activation** argument.

Also, you will use the [rectified linear unit activation function](https://machinelearningmastery.com/rectified-linear-activation-function-for-deep-learning-neural-networks/) referred to as ReLU on the first two layers and the Sigmoid function in the output layer.

It used to be the case that Sigmoid and Tanh activation functions were preferred for all layers. These days, better performance is achieved using the ReLU activation function. Using a sigmoid on the output layer ensures your network output is between 0 and 1 and is easy to map to either a probability of class 1 or snap to a hard classification of either class with a default threshold of 0.5.

You can piece it all together by adding each layer:

- The model expects rows of data with 8 variables (the _input_shape=(8,)_ argument).
- The first hidden layer has 12 nodes and uses the relu activation function.
- The second hidden layer has 8 nodes and uses the relu activation function.
- The output layer has one node and uses the sigmoid activation function.

```python
...
# define the keras model
model=Sequential()
model.add(Dense(12,input_shape=(8,),activation='relu'))
model.add(Dense(8,activation='relu'))
model.add(Dense(1,activation='sigmoid'))
...
```

**Note:** The most confusing thing here is that the shape of the input to the model is defined as an argument on the first hidden layer. This means that the line of code that adds the first Dense layer is doing two things, defining the input or visible layer and the first hidden layer.

## 3. Compile Keras Model

Now that the model is defined, _you can compile it_.

Compiling the model uses the efficient numerical libraries under the covers (the so-called backend) such as Theano or TensorFlow. The backend automatically chooses the best way to represent the network for training and making predictions to run on your hardware, such as CPU, GPU, or even distributed.

When compiling, you must specify some additional properties required when training the network. Remember training a network means finding the best set of weights to map inputs to outputs in your dataset.

You must specify the loss function to use to evaluate a set of weights, the optimizer used to search through different weights for the network, and any optional metrics you want to collect and report during training.

In this case, use cross entropy as the **loss** argument. This loss is for a binary classification problem and is defined in Keras as “ **binary_crossentropy**“. You can learn more about choosing loss functions based on your problem here:

- [How to Choose Loss Functions When Training Deep Learning Neural Networks](https://machinelearningmastery.com/how-to-choose-loss-functions-when-training-deep-learning-neural-networks/)

We will define the **optimizer** as the efficient stochastic gradient descent algorithm “ **adam**“. This is a popular version of gradient descent because it automatically tunes itself and gives good results in a wide range of problems. To learn more about the Adam version of stochastic gradient descent, see the post:

- [Gentle Introduction to the Adam Optimization Algorithm for Deep Learning](https://machinelearningmastery.com/adam-optimization-algorithm-for-deep-learning/)

Finally, because it is a classification problem, you will collect and report the classification accuracy defined via the **metrics** argument.

```python
...
# compile the keras model
model.compile(loss='binary_crossentropy',optimizer='adam',metrics=['accuracy'])
...
```

## 4. Fit Keras Model

You have defined your model and compiled it to get ready for efficient computation.

Now it is time to execute the model on some data.

You can train or fit your model on your loaded data by calling the **fit()** function on the model.

Training occurs over epochs, and each epoch is split into batches.

- **Epoch**: One pass through all of the rows in the training dataset
- **Batch**: One or more samples considered by the model within an epoch before weights are updated

One epoch comprises one or more batches, based on the chosen batch size, and the model is fit for many epochs. For more on the difference between epochs and batches, see the post:

- [What is the Difference Between a Batch and an Epoch in a Neural Network?](https://machinelearningmastery.com/difference-between-a-batch-and-an-epoch/)

The training process will run for a fixed number of epochs (iterations) through the dataset that you must specify using the **epochs** argument. You must also set the number of dataset rows that are considered before the model weights are updated within each epoch, called the batch size, and set using the **batch_size** argument.

This problem will run for a small number of epochs (150) and use a relatively small batch size of 10.

These configurations can be chosen experimentally by trial and error. You want to train the model enough so that it learns a good (or good enough) mapping of rows of input data to the output classification. The model will always have some error, but the amount of error will level out after some point for a given model configuration. This is called model convergence.

```python
...
# fit the keras model on the dataset
model.fit(X,y,epochs=150,batch_size=10)
...
```

This is where the work happens on your CPU or GPU.

## 5. Evaluate Keras Model

You have trained our neural network on the entire dataset, and you can evaluate the performance of the network on the same dataset.

This will only give you an idea of how well you have modeled the dataset (e.g., train accuracy), but no idea of how well the algorithm might perform on new data. This was done for simplicity, but ideally, you could separate your data into train and test datasets for training and evaluation of your model.

You can evaluate your model on your training dataset using the **evaluate()** function and pass it the same input and output used to train the model.

This will generate a prediction for each input and output pair and collect scores, including the average loss and any metrics you have configured, such as accuracy.

The **evaluate()** function will return a list with two values. The first will be the loss of the model on the dataset, and the second will be the accuracy of the model on the dataset. You are only interested in reporting the accuracy so ignore the loss value.

```python
...
# evaluate the keras model
_,accuracy=model.evaluate(X,y)
print('Accuracy: %.2f'%(accuracy*100))
```

## 6. Tie It All Together

You have just seen how you can easily create your first neural network model in Keras.

Let’s tie it all together into a complete code example.

```python
# first neural network with keras tutorial
from numpy import loadtxt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
# load the dataset
dataset=loadtxt('pima-indians-diabetes.csv',delimiter=',')
# split into input (X) and output (y) variables
X=dataset[:,0:8]
y=dataset[:,8]
# define the keras model
model=Sequential()
model.add(Dense(12,input_shape=(8,),activation='relu'))
model.add(Dense(8,activation='relu'))
model.add(Dense(1,activation='sigmoid'))
# compile the keras model
model.compile(loss='binary_crossentropy',optimizer='adam',metrics=['accuracy'])
# fit the keras model on the dataset
model.fit(X,y,epochs=150,batch_size=10)
# evaluate the keras model
_,accuracy=model.evaluate(X,y)
print('Accuracy: %.2f'%(accuracy*100))
```

You can copy all the code into your Python file and save it as “ **keras_first_network.py**” in the same directory as your data file “ **pima-indians-diabetes.csv**”. You can then run the Python file as a script from your command line (command prompt) as follows:

|     |     |
| --- | --- |
| 1 | python keras_first_network.py |

Running this example, you should see a message for each of the 150 epochs, printing the loss and accuracy, followed by the final evaluation of the trained model on the training dataset.

## 7. Make Predictions

The number one question I get asked is:

> “After I train my model, how can I use it to make predictions on new data?”

Great question.

You can adapt the above example and use it to generate predictions on the training dataset, pretending it is a new dataset you have not seen before.

Making predictions is as easy as calling the **predict()** function on the model. You are using a sigmoid activation function on the output layer, so the predictions will be a probability in the range between 0 and 1. You can easily convert them into a crisp binary prediction for this classification task by rounding them.

For example:

```python
...
# make probability predictions with the model
predictions=model.predict(X)
# round predictions
rounded=[round(x[0])forx in predictions]
```

You can see that most rows are correctly predicted. In fact, you can expect about 76.9% of the rows to be correctly predicted based on your estimated performance of the model in the previous section.
