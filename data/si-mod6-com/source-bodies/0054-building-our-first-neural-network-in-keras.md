---
id: "54"
title: "Building our first neural network in keras"
source_url: "https://medium.com/@akashgopalgs/building-your-first-neural-network-a-practical-guide-ecf1a936bc47"
fetch_url: "https://medium.com/@akashgopalgs/building-your-first-neural-network-a-practical-guide-ecf1a936bc47"
resolved_url: "https://medium.com/@akashgopalgs/building-your-first-neural-network-a-practical-guide-ecf1a936bc47"
firecrawl_title: "Building Your First Neural Network: A Practical Guide | by Akash Gopal GS | Medium"
description: "Building Your First Neural Network: A Practical Guide Neural networks are the backbone of modern artificial intelligence, powering applications like handwriting recognition, image classification, and …"
fetched_at: "2026-05-12T03:59:52.136984Z"
provider: "firecrawl"
strategy: "static_with_actions"
cache_key: "3db718de94da45630ab64bbd78d6401a1449805d528ede74b56585b415006279"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 737
char_count: 5374
content_sha256: "2f59448cd1580797322504462a6f3c90dc300ca3155c9ab536aa961d542505f6"
image_count: 59
link_count: 60
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "medium_can_return_deleted_or_member_wall"
---

# Building Your First Neural Network: A Practical Guide

Neural networks are the backbone of modern artificial intelligence, powering applications like handwriting recognition, image classification, and natural language processing. If you're new to the field, there's no better way to start than by building a simple neural network.

In this guide, we'll walk you through creating your first neural network using Python, TensorFlow, and Keras. We'll use the MNIST dataset, a collection of 28x28 grayscale images of handwritten digits (0–9). It's the "Hello World" of deep learning, perfect for beginners to grasp the basics.

## About the dataset

- Handwritten digits
- 28x28 pixel
- 10 categories (0–9)
- MNIST (National Institute of Standards and Technology-1980s)
- Hello World of Deep Learning
- Sample >> label

Python > Tensorflow > Keras

Image summary: A sample MNIST image shows handwritten digit examples from the dataset, illustrating the kind of 28x28 grayscale inputs the model will classify. The article uses these digit images as the training and test data for recognizing numbers 0 through 9. [Original image: MNIST Sample Image](https://miro.medium.com/v2/resize:fit:700/1*1C6EN5UCbO7kBED4gIpu3w.png)

## Loading Dataset from Keras
```python
from tensorflow.keras.datasets import mnist
import numpy as np
```

```python
(train_images, train_labels), (test_images, test_labels) = mnist.load_data()
train_images[1]
```

```python
array([[  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0,   
          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0],
       [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0,   
          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0],
       [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0,   
          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0],
       ...
       [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0,   
          0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,  0]], dtype=uint8)
```

```python
plt.matshow(train_images[1], cmap='gray')
plt.show()
```

Image summary: A grayscale MNIST digit is shown as a 28×28 pixel image with axes labeled roughly 0 to 25. The displayed sample is the handwritten digit 0, illustrating the kind of input the neural network will classify. [Original image: MNIST Image Visualization](https://miro.medium.com/v2/resize:fit:543/1*QM_Ts-PCMlmxri0nkD-uIw.png)

```python
print(train_labels[1])
print(train_images.shape)
print(len(train_labels))
print(train_labels.shape)
```

```python
0
(60000, 28, 28)
60000
(60000,)
```

```python
print(train_labels)
print(test_images.shape)
print(test_labels.shape)
print(test_labels)
```

```python
array([5, 0, 4, ..., 5, 6, 8], dtype=uint8)
(10000, 28, 28)
(10000,)
array([7, 2, 1, ..., 4, 5, 6], dtype=uint8)
```

## Building our first Network

```python
from tensorflow import keras
from tensorflow.keras import layers
```

```python
model = keras.Sequential([
    layers.Dense(512, activation='relu'),  # MLP MultiLayer PERCEPTRON
    layers.Dense(10, activation='softmax')
])

# Dense layers or fully connected layers
```

- Output layer will return 10 probability scores for 0–9 (summing to 1)  
- An optimizer (updater)  
- A loss function (how the model will evaluate its performance)  
- Metrics to monitor during training and testing – accuracy score (the fraction of correctly classified images)  

```python
model.compile(optimizer='rmsprop', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
```

```python
print(train_images.shape)
print(train_images.dtype)
print(train_images.ndim)
```

```python
(60000, 28, 28)
dtype('uint8')
3
```

Dense layer expects one-dimensional data:

```python
train_images = train_images.reshape((60000, 28*28))
train_images = train_images.astype('float32') / 255
test_images = test_images.reshape((10000, 28*28))
test_images = test_images.astype('float32') / 255
```

Instead of this step, we can use a Flatten layer inside the model when layers defining:

```python
train_images.ndim
```

```python
2
```

## Fitting the model

```python
model.fit(train_images, train_labels, epochs=5, batch_size=128)
```

```
Epoch 1/5
469/469 [==============================] - 3s 5ms/step - loss: 0.2521 - accuracy: 0.9274
Epoch 2/5
469/469 [==============================] - 4s 8ms/step - loss: 0.1019 - accuracy: 0.9704
Epoch 3/5
469/469 [==============================] - 4s 8ms/step - loss: 0.0672 - accuracy: 0.9804
Epoch 4/5
469/469 [==============================] - 4s 8ms/step - loss: 0.0494 - accuracy: 0.9853
Epoch 5/5
469/469 [==============================] - 4s 8ms/step - loss: 0.0363 - accuracy: 0.9892
```

```python
test_digits = test_images[0:10]

predictions = model.predict(test_digits)
```

```python
1/1 [==============================] - 0s 87ms/step
```

```python
predictions[0]
```

```python
array([8.3242071e-09, 1.0642919e-09, 9.3442068e-06, 7.0566508e-05,
       4.3198885e-11, 1.4322802e-07, 3.0529613e-13, 9.9991727e-01,
       3.5945330e-08, 2.6615091e-06], dtype=float32)
```

```python
np.argmax(predictions[0])
```

```python
7
```

```python
test_labels[0]
```

```python
7
```

The predicted output and its actual value are the same.

## Performance measuring

```python
test_loss, test_acc = model.evaluate(test_images, test_labels)
```

```
313/313 [==============================] - 3s 10ms/step - loss: 0.0685 - accuracy: 0.9788
```

```python
print(test_loss)
print(test_acc)
```

```python
0.06846360117197037
0.9787999987602234
```

## Conclusion

This guide outlines building a simple neural network for MNIST digit classification, including loading the dataset, preprocessing, defining the model, training, and making predictions. It serves as an excellent "Hello World" for understanding deep learning.
