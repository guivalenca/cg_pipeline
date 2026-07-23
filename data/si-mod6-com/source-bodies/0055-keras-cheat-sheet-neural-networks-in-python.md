---
id: "55"
title: "Keras Cheat Sheet: Neural Networks in Python"
source_url: "https://www.datacamp.com/cheat-sheet/keras-cheat-sheet-neural-networks-in-python"
fetch_url: "https://www.datacamp.com/cheat-sheet/keras-cheat-sheet-neural-networks-in-python"
resolved_url: "https://www.datacamp.com/cheat-sheet/keras-cheat-sheet-neural-networks-in-python"
firecrawl_title: "Keras Cheat Sheet: Neural Networks in Python | DataCamp"
description: "Make your own neural networks with this Keras cheat sheet to deep learning in Python for beginners, with code samples. "
fetched_at: "2026-05-12T03:59:52.202600Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "770370b739541fc24c7112e3787ce3a9d3b3237396f36e9af337acd1d9e50aa0"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 1216
char_count: 9281
content_sha256: "34e24d08d39539a076cd7975c10498f8b13940fed792d635ac6303e6197426a2"
image_count: 8
link_count: 21
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "cheatsheet_or_login_prompt_possible"
---

[Image: Promo | 50% Off](https://media.datacamp.com/cms/languageeng-left.png)

**Build job-ready data + AI skills. Save **50%** today**

[Keras](http://keras.io/) is an easy-to-use and powerful library for Theano and TensorFlow that provides a high-level neural networks API to develop and evaluate deep learning models.

We recently launched one of the first online interactive deep learning course using Keras 2.0, called "[Deep Learning in Python](https://www.datacamp.com/courses/introduction-to-deep-learning-in-python)".

Now, DataCamp has created a Keras cheat sheet for those who have already taken the course and that still want a handy one-page reference or for those who need an extra push to get started.

In no time, this Keras cheat sheet will make you familiar with how you can load datasets from the library itself, preprocess the data, build up a model architecture, and compile, train, and evaluate it. As there is a considerable amount of freedom in how you build up your models, you'll see that the cheat sheet uses some of the simple key code examples of the Keras library that you need to know to get started with building your own neural networks in Python.

Furthermore, you'll also see some examples of how to inspect your model, and how you can save and reload it. Lastly, you’ll also find examples of how you can predict values for test data and how you can fine tune your models by adjusting the optimization parameters and early stopping.

In short, you'll see that this cheat sheet presents you with the six steps that you can go through to make neural networks in Python with the Keras library.

In short, this cheat sheat will boost your journey with deep learning in Python: you'll have preprocessed, created, validated and tuned your deep learning models in no time thanks to the code examples!

Image summary: The image is a Keras cheat sheet organized into sections for a basic example, data loading, preprocessing, model architecture, compiling, training, evaluation, prediction, saving/reloading, and fine-tuning. It shows example code for Sequential models, MLP/CNN/RNN layers, padding and one-hot encoding, train/test splitting, standardization, model inspection, and early stopping. The sheet summarizes the six-step workflow for building and tuning neural networks in Python with Keras. [Original image: Image](https://images.datacamp.com/image/upload/v1675350580/nb7xvoymg182kjkbld8j.png)

## Python For Data Science Cheat Sheet: Keras

`Keras is a powerful and easy-to-use deep learning library for Theano and TensorFlow that provides a high-level neural networks API to develop and evaluate deep learning models.`

### A Basic Example

```python
>>> import numpy as np
>>> from tensorflow.keras.models import Sequential
>>> from tensorflow.keras.layers import Dense
>>> data = np.random.random((1000,100))
>>> labels = np.random.randint(2,size=(1000,1))
>>> model = Sequential()
>>> model.add(Dense(32, activation='relu', input_dim=100))
>>> model.add(Dense(1, activation='sigmoid'))
>>> model.compile(optimizer='rmsprop', loss='binary_crossentropy', metrics=['accuracy'])
>>> model.fit(data,labels,epochs=10,batch_size=32)
>>> predictions = model.predict(data)
```

### Data

Your data needs to be stored as NumPy arrays or as a list of NumPy arrays. Ideally, you split the data in training and test sets, for which you can also resort to the `train_test_split` module of `sklearn.cross_validation`.

#### Keras Data Sets

```python
>>> from tensorflow.keras.datasets import boston_housing, mnist, cifar10, imdb
>>> (x_train,y_train),(x_test,y_test) = mnist.load_data()
>>> (x_train2,y_train2),(x_test2,y_test2) = boston_housing.load_data()
>>> (x_train3,y_train3),(x_test3,y_test3) = cifar10.load_data()
>>> (x_train4,y_train4),(x_test4,y_test4) = imdb.load_data(num_words=20000)
>>> num_classes = 10
```

#### Other

```python
>>> from urllib.request import urlopen
>>> data = np.loadtxt(urlopen("http://archive.ics.uci.edu/ml/machine-learning-databases/pima-indians-diabetes/pima-indians-diabetes.data"),delimiter=",")
>>> X = data[:,0:8]
>>> y = data [:,8]
```

### Preprocessing

#### Sequence Padding

```python
>>> from tensorflow.keras.preprocessing import sequence
>>> x_train4 = sequence.pad_sequences(x_train4,maxlen=80)
>>> x_test4 = sequence.pad_sequences(x_test4,maxlen=80)
```

#### One-Hot Encoding

```python
>>> from tensorflow.keras.utils import to_categorical
>>> Y_train = to_categorical(y_train, num_classes)
>>> Y_test = to_categorical(y_test, num_classes)
>>> Y_train3 = to_categorical(y_train3, num_classes)
>>> Y_test3 = to_categorical(y_test3, num_classes)
```

#### Train And Test Sets

```python
>>> from sklearn.model_selection import train_test_split
>>> X_train5, X_test5, y_train5, y_test5 = train_test_split(X, y, test_size=0.33, random_state=42)
```

### Standardization/Normalization

```python
>>> from sklearn.preprocessing import StandardScaler
>>> scaler = StandardScaler().fit(x_train2)
>>> standardized_X = scaler.transform(x_train2)
>>> standardized_X_test = scaler.transform(x_test2)
```

### Model Architecture

#### Sequential Model

```python
>>> from tensorflow.keras.models import Sequential
>>> model = Sequential()
>>> model2 = Sequential()
>>> model3 = Sequential()
```

#### Multi-Layer Perceptron (MLP)

**Binary Classification**

```python
>>> from tensorflow.keras.layers import Dense
>>> model.add(Dense(12, input_dim=8, kernel_initializer='uniform', activation='relu'))
>>> model.add(Dense(8, kernel_initializer='uniform', activation='relu'))
>>> model.add(Dense(1, kernel_initializer='uniform', activation='sigmoid'))
```

**Multi-Class Classification**

```python
>>> from tensorflow.keras.layers import Dropout
>>> model.add(Dense(512,activation='relu',input_shape=(784,)))
>>> model.add(Dropout(0.2))
>>> model.add(Dense(512,activation='relu'))
>>> model.add(Dropout(0.2))
>>> model.add(Dense(10,activation='softmax'))
```

**Regression**

```python
>>> model.add(Dense(64, activation='relu', input_dim=train_data.shape[1]))
>>> model.add(Dense(1))
```

#### Convolutional Neural Network (CNN)

```python
>>> from tensorflow.keras.layers import Activation, Conv2D, MaxPooling2D, Flatten
>>> model2.add(Conv2D(32, (3,3), padding='same', input_shape=x_train.shape[1:]))
>>> model2.add(Activation('relu'))
>>> model2.add(Conv2D(32, (3,3)))
>>> model2.add(Activation('relu'))
>>> model2.add(MaxPooling2D(pool_size=(2,2)))
>>> model2.add(Dropout(0.25))
>>> model2.add(Conv2D(64, (3,3), padding='same'))
>>> model2.add(Activation('relu'))
>>> model2.add(Conv2D(64, (3, 3)))
>>> model2.add(Activation('relu'))
>>> model2.add(MaxPooling2D(pool_size=(2,2)))
>>> model2.add(Dropout(0.25))
>>> model2.add(Flatten())
>>> model2.add(Dense(512))
>>> model2.add(Activation('relu'))
>>> model2.add(Dropout(0.5))
>>> model2.add(Dense(num_classes))
>>> model2.add(Activation('softmax'))
```

#### Recurrent Neural Network (RNN)

```python
>>> from tensorflow.keras.layers import Embedding,LSTM
>>> model3.add(Embedding(20000,128))
>>> model3.add(LSTM(128,dropout=0.2,recurrent_dropout=0.2))
>>> model3.add(Dense(1,activation='sigmoid'))
```

### Inspect Model

Model output shape

```python
>>> model.output_shape
```

Model summary representation

```python
>>> model.summary()
```

Model configuration

```python
>>> model.get_config()
```

List all weight tensors in the model

```python
>>> model.get_weights()
```

### Compile Model

#### Multi-Layer Perceptron (MLP)

**MLP: Binary Classification**

```python
>>> model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
```

**MLP: Multi-Class Classification**

```python
>>> model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy'])
```

**MLP: Regression**

```python
>>> model.compile(optimizer='rmsprop', loss='mse', metrics=['mae'])
```

#### Recurrent Neural Network (RNN)

```python
>>> model3.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
```

### Model Training

```python
>>> model3.fit(x_train4, y_train4, batch_size=32, epochs=15, verbose=1, validation_data=(x_test4, y_test4))
```

### Evaluate Your Model's Performance

```python
>>> score = model3.evaluate(x_test, y_test, batch_size=32)
```

### Prediction

```python
>>> model3.predict(x_test4, batch_size=32)
>>> model3.predict_classes(x_test4,batch_size=32)
```

### Save/Reload Models

```python
>>> from tensorflow.keras.models import load_models
>>> model3.save('model_file.h5')
>>> my_model = load_model('my_model.h5')
```

### Model Fine-Tuning

#### Optimization Parameters

```python
>>> from tensorflow.keras.optimizers import RMSprop
>>> opt = RMSprop(lr=0.0001, decay=1e-6)
>>> model2.compile(loss='categorical_crossentropy', optimizer=opt, metrics=['accuracy'])
```

#### Early Stopping

```python
>>> from tensorflow.keras.callbacks import EarlyStopping
>>> early_stopping_monitor = EarlyStopping(patience=2)
>>> model3.fit(x_train4, y_train4, batch_size=32, epochs=15, validation_data=(x_test4, y_test4), callbacks=[early_stopping_monitor])
```

### Going Further

Begin with [our Keras tutorial for beginners](https://www.datacamp.com/tutorial/deep-learning-python), in which you'll learn in an easy, step-by-step way how to explore and preprocess the wine quality data set, build up a multi-layer perceptron for classification and regression tasks, compile, fit and evaluate the model and fine-tune the model that you have built.

Also, don't miss out on our [Scikit-Learn cheat sheet](https://www.datacamp.com/cheat-sheet/scikit-learn-cheat-sheet-python-machine-learning), [NumPy cheat sheet](https://www.datacamp.com/cheat-sheet/numpy-cheat-sheet-data-analysis-in-python) and [Pandas cheat sheet](https://www.datacamp.com/cheat-sheet/pandas-cheat-sheet-for-data-science-in-python)!
