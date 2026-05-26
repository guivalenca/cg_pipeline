---
id: "61"
title: "Understanding word vectors"
source_url: "https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469"
fetch_url: "https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469"
resolved_url: "https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469"
firecrawl_title: "Understanding word vectors: A tutorial for \"Reading and Writing Electronic Text,\" a class I teach at ITP. (Python 2.7) Code examples released under CC0 https://creativecommons.org/choose/zero/, other text released under CC BY 4.0 https://creativecommons.org/licenses/by/4.0/ · GitHub"
description: "Understanding word vectors: A tutorial for \"Reading and Writing Electronic Text,\" a class I teach at ITP. (Python 2.7) Code examples released under CC0 https://creativecommons.org/choose/zero/, other text released under CC BY 4.0 https://creativecommons.org/licenses/by/4.0/ - understanding-word-vectors.ipynb"
fetched_at: "2026-05-12T03:59:52.620280Z"
provider: "firecrawl"
strategy: "app_ui"
cache_key: "0cceab1d0bef8ebba70ea003fcdce88351a278092753bcfdc8da9c010431866d"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 10223
char_count: 69117
content_sha256: "32856e127cbaf091a37b5e8f625936e421c115c28d61ff53970a838dd2b6577e"
image_count: 32
link_count: 116
warnings: []
gate_status: "passed"
gate_failures: []
route_notes:
  - "github_app_ui_or_wrapper_page"
---

[Skip to content](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469#start-of-content)

[Gist Homepage ](https://gist.github.com/)

[Gist Homepage ](https://gist.github.com/)

[Sign in](https://gist.github.com/auth/github?return_to=https%3A%2F%2Fgist.github.com%2Faparrish%2F2f562e3737544cf29aaf1af30362f469) [Sign up](https://gist.github.com/join?return_to=https%3A%2F%2Fgist.github.com%2Faparrish%2F2f562e3737544cf29aaf1af30362f469&source=header-gist)

You signed in with another tab or window. [Reload](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469) to refresh your session.You signed out in another tab or window. [Reload](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469) to refresh your session.You switched accounts on another tab or window. [Reload](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469) to refresh your session.Dismiss alert

{{ message }}

Instantly share code, notes, and snippets.


[![@aparrish](https://avatars.githubusercontent.com/u/125839?s=64&v=4)](https://gist.github.com/aparrish)

# [aparrish](https://gist.github.com/aparrish)/ **[understanding-word-vectors.ipynb](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469)**

Last active
2 weeks agoApril 30, 2026 09:31

Show Gist options

- [Download ZIP](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/archive/ddcd14198283486fe6f2707125f53477fbd42095.zip)

- [Star1,454(1,454)](https://gist.github.com/login?return_to=https%3A%2F%2Fgist.github.com%2Faparrish%2F2f562e3737544cf29aaf1af30362f469) You must be signed in to star a gist
- [Fork359(359)](https://gist.github.com/login?return_to=https%3A%2F%2Fgist.github.com%2Faparrish%2F2f562e3737544cf29aaf1af30362f469) You must be signed in to fork a gist

- Embed








# Select an option





























  - Embed
    Embed this gist in your website.
  - Share
    Copy sharable link for this gist.
  - Clone via HTTPS
    Clone using the web URL.

## No results found

[Learn more about clone URLs](https://docs.github.com/articles/which-remote-url-should-i-use)

Clone this repository at &lt;script src=&quot;https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469.js&quot;&gt;&lt;/script&gt;

- Save aparrish/2f562e3737544cf29aaf1af30362f469 to your computer and use it in GitHub Desktop.

Embed

# Select an option

- Embed
Embed this gist in your website.
- Share
Copy sharable link for this gist.
- Clone via HTTPS
Clone using the web URL.

## No results found

[Learn more about clone URLs](https://docs.github.com/articles/which-remote-url-should-i-use)

Clone this repository at &lt;script src=&quot;https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469.js&quot;&gt;&lt;/script&gt;

Save aparrish/2f562e3737544cf29aaf1af30362f469 to your computer and use it in GitHub Desktop.

[Download ZIP](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/archive/ddcd14198283486fe6f2707125f53477fbd42095.zip)

Understanding word vectors: A tutorial for "Reading and Writing Electronic Text," a class I teach at ITP. (Python 2.7) Code examples released under CC0 [https://creativecommons.org/choose/zero/](https://creativecommons.org/choose/zero/), other text released under CC BY 4.0 [https://creativecommons.org/licenses/by/4.0/](https://creativecommons.org/licenses/by/4.0/)

Display the source blob

Display the rendered blob

[Raw](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/raw/ddcd14198283486fe6f2707125f53477fbd42095/understanding-word-vectors.ipynb)

[**understanding-word-vectors.ipynb**](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469#file-understanding-word-vectors-ipynb)

Loading

Sorry, something went wrong. [Reload?](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469)

Sorry, we cannot display this file.

Sorry, this file is invalid so it cannot be displayed.

Notebooks

# Understanding word vectors [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Understanding-word-vectors)

... for, like, actual poets. By [Allison Parrish](http://www.decontextualize.com/)

In this tutorial, I'm going to show you how word vectors work. This tutorial assumes a good amount of Python knowledge, but even if you're not a Python expert, you should be able to follow along and make small changes to the examples without too much trouble.

This is a " [Jupyter Notebook](https://jupyter-notebook-beginner-guide.readthedocs.io/en/latest/)," which consists of text and "cells" of code. After you've loaded the notebook, you can execute the code in a cell by highlighting it and hitting Ctrl+Enter. In general, you need to execute the cells from top to bottom, but you can usually run a cell more than once without messing anything up. Experiment!

If things start acting strange, you can interrupt the Python process by selecting "Kernel > Interrupt"—this tells Python to stop doing whatever it was doing. Select "Kernel > Restart" to clear all of your variables and start from scratch.

## Why word vectors? [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Why-word-vectors?)

Poetry is, at its core, the art of identifying and manipulating linguistic similarity. I have discovered a truly marvelous proof of this, which this notebook is too narrow to contain. (By which I mean: I will elaborate on this some other time)

## Animal similarity and simple linear algebra [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Animal-similarity-and-simple-linear-algebra)

We'll begin by considering a small subset of English: words for animals. Our task is to be able to write computer programs to find similarities among these words and the creatures they designate. To do this, we might start by making a spreadsheet of some animals and their characteristics. For example:

![Animal spreadsheet](https://camo.githubusercontent.com/9ba7eba6d1a80c1295b6776e57781e02d637d82dd2d9152ae5e2db3258174c90/687474703a2f2f7374617469632e6465636f6e7465787475616c697a652e636f6d2f736e6170732f616e696d616c2d73707265616473686565742e706e67)

This spreadsheet associates a handful of animals with two numbers: their cuteness and their size, both in a range from zero to one hundred. (The values themselves are simply based on my own judgment. Your taste in cuteness and evaluation of size may differ significantly from mine. As with all data, these data are simply a mirror reflection of the person who collected them.)

These values give us everything we need to make determinations about which animals are similar (at least, similar in the properties that we've included in the data). Try to answer the following question: Which animal is most similar to a capybara? You could go through the values one by one and do the math to make that evaluation, but visualizing the data as points in 2-dimensional space makes finding the answer very intuitive:

![Animal space](https://camo.githubusercontent.com/7e1a0cef23b8f2e19e15a3cbee698d75bf81b511a98036d02b4d9d25fbe5777b/687474703a2f2f7374617469632e6465636f6e7465787475616c697a652e636f6d2f736e6170732f616e696d616c2d73706163652e706e67)

The plot shows us that the closest animal to the capybara is the panda bear (again, in terms of its subjective size and cuteness). One way of calculating how "far apart" two points are is to find their _Euclidean distance_. (This is simply the length of the line that connects the two points.) For points in two dimensions, Euclidean distance can be calculated with the following Python function:

In \[325\]:

```
import math
def distance2d(x1, y1, x2, y2):
    return math.sqrt((x1 - x2)**2 + (y1 - y2)**2)
```

(The `**` operator raises the value on its left to the power on its right.)

So, the distance between "capybara" (70, 30) and "panda" (74, 40):

In \[327\]:

```
distance2d(70, 30, 75, 40) # panda and capybara
```

Out\[327\]:

```
11.180339887498949
```

... is less than the distance between "tarantula" and "elephant":

In \[328\]:

```
distance2d(8, 3, 65, 90) # tarantula and elephant
```

Out\[328\]:

```
104.0096149401583
```

Modeling animals in this way has a few other interesting properties. For example, you can pick an arbitrary point in "animal space" and then find the animal closest to that point. If you imagine an animal of size 25 and cuteness 30, you can easily look at the space to find the animal that most closely fits that description: the chicken.

Reasoning visually, you can also answer questions like: what's halfway between a chicken and an elephant? Simply draw a line from "elephant" to "chicken," mark off the midpoint and find the closest animal. (According to our chart, halfway between an elephant and a chicken is a horse.)

You can also ask: what's the _difference_ between a hamster and a tarantula? According to our plot, it's about seventy five units of cute (and a few units of size).

The relationship of "difference" is an interesting one, because it allows us to reason about _analogous_ relationships. In the chart below, I've drawn an arrow from "tarantula" to "hamster" (in blue):

![Animal analogy](https://camo.githubusercontent.com/fcceb531366fede09d8970137d4d8bcf8a82fea3be822fb716bb4f83fc46bcb8/687474703a2f2f7374617469632e6465636f6e7465787475616c697a652e636f6d2f736e6170732f616e696d616c2d73706163652d616e616c6f67792e706e67)

You can understand this arrow as being the _relationship_ between a tarantula and a hamster, in terms of their size and cuteness (i.e., hamsters and tarantulas are about the same size, but hamsters are much cuter). In the same diagram, I've also transposed this same arrow (this time in red) so that its origin point is "chicken." The arrow ends closest to "kitten." What we've discovered is that the animal that is about the same size as a chicken but much cuter is... a kitten. To put it in terms of an analogy:

```
Tarantulas are to hamsters as chickens are to kittens.
```

A sequence of numbers used to identify a point is called a _vector_, and the kind of math we've been doing so far is called _linear algebra._ (Linear algebra is surprisingly useful across many domains: It's the same kind of math you might do to, e.g., simulate the velocity and acceleration of a sprite in a video game.)

A set of vectors that are all part of the same data set is often called a _vector space_. The vector space of animals in this section has two _dimensions_, by which I mean that each vector in the space has two numbers associated with it (i.e., two columns in the spreadsheet). The fact that this space has two dimensions just happens to make it easy to _visualize_ the space by drawing a 2D plot. But most vector spaces you'll work with will have more than two dimensions—sometimes many hundreds. In those cases, it's more difficult to visualize the "space," but the math works pretty much the same.

## Language with vectors: colors [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Language-with-vectors:-colors)

So far, so good. We have a system in place—albeit highly subjective—for talking about animals and the words used to name them. I want to talk about another vector space that has to do with language: the vector space of colors.

Colors are often represented in computers as vectors with three dimensions: red, green, and blue. Just as with the animals in the previous section, we can use these vectors to answer questions like: which colors are similar? What's the most likely color name for an arbitrarily chosen set of values for red, green and blue? Given the names of two colors, what's the name of those colors' "average"?

We'll be working with this [color data](https://github.com/dariusk/corpora/blob/master/data/colors/xkcd.json) from the [xkcd color survey](https://blog.xkcd.com/2010/05/03/color-survey-results/). The data relates a color name to the RGB value associated with that color. [Here's a page that shows what the colors look like](https://xkcd.com/color/rgb/). Download the color data and put it in the same directory as this notebook.

A few notes before we proceed:

- The linear algebra functions implemented below (`addv`, `meanv`, etc.) are slow, potentially inaccurate, and shouldn't be used for "real" code—I wrote them so beginner programmers can understand how these kinds of functions work behind the scenes. Use [numpy](http://www.numpy.org/) for fast and accurate math in Python.
- If you're interested in perceptually accurate color math in Python, consider using the [colormath library](http://python-colormath.readthedocs.io/en/latest/).

Now, import the `json` library and load the color data:

In \[329\]:

```
import json
```

In \[330\]:

```
color_data = json.loads(open("xkcd.json").read())
```

The following function converts colors from hex format (`#1a2b3c`) to a tuple of integers:

In \[331\]:

```
def hex_to_int(s):
    s = s.lstrip("#")
    return int(s[:2], 16), int(s[2:4], 16), int(s[4:6], 16)
```

And the following cell creates a dictionary and populates it with mappings from color names to RGB vectors for each color in the data:

In \[332\]:

```
colors = dict()
for item in color_data['colors']:
    colors[item["color"]] = hex_to_int(item["hex"])
```

Testing it out:

In \[338\]:

```
colors['olive']
```

Out\[338\]:

```
(110, 117, 14)
```

In \[339\]:

```
colors['red']
```

Out\[339\]:

```
(229, 0, 0)
```

In \[340\]:

```
colors['black']
```

Out\[340\]:

```
(0, 0, 0)
```

### Vector math [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Vector-math)

Before we keep going, we'll need some functions for performing basic vector "arithmetic." These functions will work with vectors in spaces of any number of dimensions.

The first function returns the Euclidean distance between two points:

In \[341\]:

```
import math
def distance(coord1, coord2):
    # note, this is VERY SLOW, don't use for actual code
    return math.sqrt(sum([(i - j)**2 for i, j in zip(coord1, coord2)]))
distance([10, 1], [5, 2])
```

Out\[341\]:

```
5.0990195135927845
```

The `subtractv` function subtracts one vector from another:

In \[342\]:

```
def subtractv(coord1, coord2):
    return [c1 - c2 for c1, c2 in zip(coord1, coord2)]
subtractv([10, 1], [5, 2])
```

Out\[342\]:

```
[5, -1]
```

The `addv` vector adds two vectors together:

In \[343\]:

```
def addv(coord1, coord2):
    return [c1 + c2 for c1, c2 in zip(coord1, coord2)]
addv([10, 1], [5, 2])
```

Out\[343\]:

```
[15, 3]
```

And the `meanv` function takes a list of vectors and finds their mean or average:

In \[344\]:

```
def meanv(coords):
    # assumes every item in coords has same length as item 0
    sumv = [0] * len(coords[0])
    for item in coords:
        for i in range(len(item)):
            sumv[i] += item[i]
    mean = [0] * len(sumv)
    for i in range(len(sumv)):
        mean[i] = float(sumv[i]) / len(coords)
    return mean
meanv([[0, 1], [2, 2], [4, 3]])
```

Out\[344\]:

```
[2.0, 2.0]
```

Just as a test, the following cell shows that the distance from "red" to "green" is greater than the distance from "red" to "pink":

In \[345\]:

```
distance(colors['red'], colors['green']) > distance(colors['red'], colors['pink'])
```

Out\[345\]:

```
True
```

### Finding the closest item [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Finding-the-closest-item)

Just as we wanted to find the animal that most closely matched an arbitrary point in cuteness/size space, we'll want to find the closest color name to an arbitrary point in RGB space. The easiest way to find the closest item to an arbitrary vector is simply to find the distance between the target vector and each item in the space, in turn, then sort the list from closest to farthest. The `closest()` function below does just that. By default, it returns a list of the ten closest items to the given vector.

> Note: Calculating "closest neighbors" like this is fine for the examples in this notebook, but unmanageably slow for vector spaces of any appreciable size. As your vector space grows, you'll want to move to a faster solution, like SciPy's [kdtree](https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.spatial.KDTree.html) or [Annoy](https://pypi.python.org/pypi/annoy).

In \[347\]:

```
def closest(space, coord, n=10):
    closest = []
    for key in sorted(space.keys(),
                        key=lambda x: distance(coord, space[x]))[:n]:
        closest.append(key)
    return closest
```

Testing it out, we can find the ten colors closest to "red":

In \[349\]:

```
closest(colors, colors['red'])
```

Out\[349\]:

```
[u'red',\
 u'fire engine red',\
 u'bright red',\
 u'tomato red',\
 u'cherry red',\
 u'scarlet',\
 u'vermillion',\
 u'orangish red',\
 u'cherry',\
 u'lipstick red']
```

... or the ten colors closest to (150, 60, 150):

In \[350\]:

```
closest(colors, [150, 60, 150])
```

Out\[350\]:

```
[u'warm purple',\
 u'medium purple',\
 u'ugly purple',\
 u'light eggplant',\
 u'purpleish',\
 u'purplish',\
 u'purply',\
 u'light plum',\
 u'purple',\
 u'muted purple']
```

### Color magic [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Color-magic)

The magical part of representing words as vectors is that the vector operations we defined earlier appear to operate on language the same way they operate on numbers. For example, if we find the word closest to the vector resulting from subtracting "red" from "purple," we get a series of "blue" colors:

In \[352\]:

```
closest(colors, subtractv(colors['purple'], colors['red']))
```

Out\[352\]:

```
[u'cobalt blue',\
 u'royal blue',\
 u'darkish blue',\
 u'true blue',\
 u'royal',\
 u'prussian blue',\
 u'dark royal blue',\
 u'deep blue',\
 u'marine blue',\
 u'deep sea blue']
```

This matches our intuition about RGB colors, which is that purple is a combination of red and blue. Take away the red, and blue is all you have left.

You can do something similar with addition. What's blue plus green?

In \[353\]:

```
closest(colors, addv(colors['blue'], colors['green']))
```

Out\[353\]:

```
[u'bright turquoise',\
 u'bright light blue',\
 u'bright aqua',\
 u'cyan',\
 u'neon blue',\
 u'aqua blue',\
 u'bright cyan',\
 u'bright sky blue',\
 u'aqua',\
 u'bright teal']
```

That's right, it's something like turquoise or cyan! What if we find the average of black and white? Predictably, we get gray:

In \[355\]:

```
# the average of black and white: medium grey
closest(colors, meanv([colors['black'], colors['white']]))
```

Out\[355\]:

```
[u'medium grey',\
 u'purple grey',\
 u'steel grey',\
 u'battleship grey',\
 u'grey purple',\
 u'purplish grey',\
 u'greyish purple',\
 u'steel',\
 u'warm grey',\
 u'green grey']
```

Just as with the tarantula/hamster example from the previous section, we can use color vectors to reason about relationships between colors. In the cell below, finding the difference between "pink" and "red" then adding it to "blue" seems to give us a list of colors that are to blue what pink is to red (i.e., a slightly lighter, less saturated shade):

In \[354\]:

```
# an analogy: pink is to red as X is to blue
pink_to_red = subtractv(colors['pink'], colors['red'])
closest(colors, addv(pink_to_red, colors['blue']))
```

Out\[354\]:

```
[u'neon blue',\
 u'bright sky blue',\
 u'bright light blue',\
 u'cyan',\
 u'bright cyan',\
 u'bright turquoise',\
 u'clear blue',\
 u'azure',\
 u'dodger blue',\
 u'lightish blue']
```

Another example of color analogies: Navy is to blue as true green/dark grass green is to green:

In \[358\]:

```
# another example:
navy_to_blue = subtractv(colors['navy'], colors['blue'])
closest(colors, addv(navy_to_blue, colors['green']))
```

Out\[358\]:

```
[u'true green',\
 u'dark grass green',\
 u'grassy green',\
 u'racing green',\
 u'forest',\
 u'bottle green',\
 u'dark olive green',\
 u'darkgreen',\
 u'forrest green',\
 u'grass green']
```

The examples above are fairly simple from a mathematical perspective but nevertheless _feel_ magical: they're demonstrating that it's possible to use math to reason about how people use language.

### Interlude: A Love Poem That Loses Its Way [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Interlude:-A-Love-Poem-That-Loses-Its-Way)

In \[378\]:

```
import random
red = colors['red']
blue = colors['blue']
for i in range(14):
    rednames = closest(colors, red)
    bluenames = closest(colors, blue)
    print "Roses are " + rednames[0] + ", violets are " + bluenames[0]
    red = colors[random.choice(rednames[1:])]
    blue = colors[random.choice(bluenames[1:])]
```

```
Roses are red, violets are blue
Roses are tomato red, violets are electric blue
Roses are deep orange, violets are deep sky blue
Roses are burnt orange, violets are bright blue
Roses are brick orange, violets are cerulean
Roses are dark orange, violets are turquoise blue
Roses are orange brown, violets are teal blue
Roses are brown orange, violets are peacock blue
Roses are dirty orange, violets are deep aqua
Roses are pumpkin, violets are dark cyan
Roses are orange, violets are ocean
Roses are deep orange, violets are greenish blue
Roses are rusty orange, violets are dark cyan
Roses are burnt orange, violets are sea blue
```

### Doing bad digital humanities with color vectors [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Doing-bad-digital-humanities-with-color-vectors)

With the tools above in hand, we can start using our vectorized knowledge of language toward academic ends. In the following example, I'm going to calculate the average color of Bram Stoker's _Dracula_.

(Before you proceed, make sure to [download the text file from Project Gutenberg](http://www.gutenberg.org/cache/epub/345/pg345.txt) and place it in the same directory as this notebook.)

First, we'll load [spaCy](https://spacy.io/):

In \[359\]:

```
import spacy
nlp = spacy.load('en')
```

To calculate the average color, we'll follow these steps:

1. Parse the text into words
2. Check every word to see if it names a color in our vector space. If it does, add it to a list of vectors.
3. Find the average of that list of vectors.
4. Find the color(s) closest to that average vector.

The following cell performs steps 1-3:

In \[370\]:

```
doc = nlp(open("pg345.txt").read().decode('utf8'))
# use word.lower_ to normalize case
drac_colors = [colors[word.lower_] for word in doc if word.lower_ in colors]
avg_color = meanv(drac_colors)
print avg_color
```

```
[147.44839067702551, 113.65371809100999, 100.13540510543841]
```

Now, we'll pass the averaged color vector to the `closest()` function, yielding... well, it's just a brown mush, which is kinda what you'd expect from adding a bunch of colors together willy-nilly.

In \[371\]:

```
closest(colors, avg_color)
```

Out\[371\]:

```
[u'reddish grey',\
 u'brownish grey',\
 u'brownish',\
 u'brown grey',\
 u'mocha',\
 u'grey brown',\
 u'puce',\
 u'dull brown',\
 u'pinkish brown',\
 u'dark taupe']
```

On the other hand, here's what we get when we average the colors of Charlotte Perkins Gilman's classic _The Yellow Wallpaper_. ( [Download from here](http://www.gutenberg.org/cache/epub/1952/pg1952.txt) and save in the same directory as this notebook if you want to follow along.) The result definitely reflects the content of the story, so maybe we're on to something here.

In \[369\]:

```
doc = nlp(open("pg1952.txt").read().decode('utf8'))
wallpaper_colors = [colors[word.lower_] for word in doc if word.lower_ in colors]
avg_color = meanv(wallpaper_colors)
closest(colors, avg_color)
```

Out\[369\]:

```
[u'sickly yellow',\
 u'piss yellow',\
 u'puke yellow',\
 u'vomit yellow',\
 u'dirty yellow',\
 u'mustard yellow',\
 u'dark yellow',\
 u'olive yellow',\
 u'macaroni and cheese',\
 u'pea']
```

Exercise for the reader: Use the vector arithmetic functions to rewrite a text, making it...

- more blue (i.e., add `colors['blue']` to each occurrence of a color word); or
- more light (i.e., add `colors['white']` to each occurrence of a color word); or
- darker (i.e., attenuate each color. You might need to write a vector multiplication function to do this one right.)

## Distributional semantics [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Distributional-semantics)

In the previous section, the examples are interesting because of a simple fact: colors that we think of as similar are "closer" to each other in RGB vector space. In our color vector space, or in our animal cuteness/size space, you can think of the words identified by vectors close to each other as being _synonyms_, in a sense: they sort of "mean" the same thing. They're also, for many purposes, _functionally identical_. Think of this in terms of writing, say, a search engine. If someone searches for "mauve trousers," then it's probably also okay to show them results for, say,

In \[380\]:

```
for cname in closest(colors, colors['mauve']):
    print cname + " trousers"
```

```
mauve trousers
dusty rose trousers
dusky rose trousers
brownish pink trousers
old pink trousers
reddish grey trousers
dirty pink trousers
old rose trousers
light plum trousers
ugly pink trousers
```

That's all well and good for color words, which intuitively seem to exist in a multidimensional continuum of perception, and for our animal space, where we've written out the vectors ahead of time. But what about... arbitrary words? Is it possible to create a vector space for all English words that has this same "closer in space is closer in meaning" property?

To answer that, we have to back up a bit and ask the question: what does _meaning_ mean? No one really knows, but one theory popular among computational linguists, computer scientists and other people who make search engines is the [Distributional Hypothesis](https://en.wikipedia.org/wiki/Distributional_semantics), which states that:

```
Linguistic items with similar distributions have similar meanings.
```

What's meant by "similar distributions" is _similar contexts_. Take for example the following sentences:

```
It was really cold yesterday.
It will be really warm today, though.
It'll be really hot tomorrow!
Will it be really cool Tuesday?
```

According to the Distributional Hypothesis, the words `cold`, `warm`, `hot` and `cool` must be related in some way (i.e., be close in meaning) because they occur in a similar context, i.e., between the word "really" and a word indicating a particular day. (Likewise, the words `yesterday`, `today`, `tomorrow` and `Tuesday` must be related, since they occur in the context of a word indicating a temperature.)

In other words, according to the Distributional Hypothesis, a word's meaning is just a big list of all the contexts it occurs in. Two words are closer in meaning if they share contexts.

## Word vectors by counting contexts [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Word-vectors-by-counting-contexts)

So how do we turn this insight from the Distributional Hypothesis into a system for creating general-purpose vectors that capture the meaning of words? Maybe you can see where I'm going with this. What if we made a _really big_ spreadsheet that had one column for every context for every word in a given source text. Let's use a small source text to begin with, such as this excerpt from Dickens:

```
It was the best of times, it was the worst of times.
```

Such a spreadsheet might look something like this:

![dickens contexts](https://camo.githubusercontent.com/db601e39bb94a72737182707b0914ae694cbd23cd1c879b1e74df5bd199e3252/687474703a2f2f7374617469632e6465636f6e7465787475616c697a652e636f6d2f736e6170732f626573742d6f662d74696d65732e706e67)

The spreadsheet has one column for every possible context, and one row for every word. The values in each cell correspond with how many times the word occurs in the given context. The numbers in the columns constitute that word's vector, i.e., the vector for the word `of` is

```
[0, 0, 0, 0, 1, 0, 0, 0, 1, 0]
```

Because there are ten possible contexts, this is a ten dimensional space! It might be strange to think of it, but you can do vector arithmetic on vectors with ten dimensions just as easily as you can on vectors with two or three dimensions, and you could use the same distance formula that we defined earlier to get useful information about which vectors in this space are similar to each other. In particular, the vectors for `best` and `worst` are actually the same (a distance of zero), since they occur only in the same context (`the ___ of`):

```
[0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
```

Of course, the conventional way of thinking about "best" and "worst" is that they're _antonyms_, not _synonyms_. But they're also clearly two words of the same kind, with related meanings (through opposition), a fact that is captured by this distributional model.

### Contexts and dimensionality [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Contexts-and-dimensionality)

Of course, in a corpus of any reasonable size, there will be many thousands if not many millions of possible contexts. It's difficult enough working with a vector space of ten dimensions, let alone a vector space of a million dimensions! It turns out, though, that many of the dimensions end up being superfluous and can either be eliminated or combined with other dimensions without significantly affecting the predictive power of the resulting vectors. The process of getting rid of superfluous dimensions in a vector space is called [dimensionality reduction](https://en.wikipedia.org/wiki/Dimensionality_reduction), and most implementations of count-based word vectors make use of dimensionality reduction so that the resulting vector space has a reasonable number of dimensions (say, 100—300, depending on the corpus and application).

The question of how to identify a "context" is itself very difficult to answer. In the toy example above, we've said that a "context" is just the word that precedes and the word that follows. Depending on your implementation of this procedure, though, you might want a context with a bigger "window" (e.g., two words before and after), or a non-contiguous window (skip a word before and after the given word). You might exclude certain "function" words like "the" and "of" when determining a word's context, or you might [lemmatize](https://en.wikipedia.org/wiki/Lemmatisation) the words before you begin your analysis, so two occurrences with different "forms" of the same word count as the same context. These are all questions open to research and debate, and different implementations of procedures for creating count-based word vectors make different decisions on this issue.

### GloVe vectors [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#GloVe-vectors)

But you don't have to create your own word vectors from scratch! Many researchers have made downloadable databases of pre-trained vectors. One such project is Stanford's [Global Vectors for Word Representation (GloVe)](https://nlp.stanford.edu/projects/glove/). These 300-dimensional vectors are included with spaCy, and they're the vectors we'll be using for the rest of this tutorial.

## Word vectors in spaCy [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Word-vectors-in-spaCy)

Okay, let's have some fun with real word vectors. We're going to use the GloVe vectors that come with spaCy to creatively analyze and manipulate the text of Bram Stoker's _Dracula_. First, make sure you've got `spacy` imported:

In \[381\]:

```
from __future__ import unicode_literals
import spacy
```

The following cell loads the language model and parses the input text:

In \[382\]:

```
nlp = spacy.load('en')
doc = nlp(open("pg345.txt").read().decode('utf8'))
```

And the cell below creates a list of unique words (or tokens) in the text, as a list of strings.

In \[383\]:

```
# all of the words in the text file
tokens = list(set([w.text for w in doc if w.is_alpha]))
```

You can see the vector of any word in spaCy's vocabulary using the `vocab` attribute, like so:

In \[385\]:

```
nlp.vocab['cheese'].vector
```

Out\[385\]:

```
array([ -5.52519977e-01,   1.88940004e-01,   6.87370002e-01,\
        -1.97889999e-01,   7.05749989e-02,   1.00750005e+00,\
         5.17890006e-02,  -1.56029999e-01,   3.19409996e-01,\
         1.17019999e+00,  -4.72479999e-01,   4.28669989e-01,\
        -4.20249999e-01,   2.48030007e-01,   6.81940019e-01,\
        -6.74880028e-01,   9.24009979e-02,   1.30890000e+00,\
        -3.62779982e-02,   2.00979993e-01,   7.60049999e-01,\
        -6.67179972e-02,  -7.77940005e-02,   2.38440007e-01,\
        -2.43509993e-01,  -5.41639984e-01,  -3.35399985e-01,\
         2.98049986e-01,   3.52690011e-01,  -8.05939972e-01,\
        -4.36109990e-01,   6.15350008e-01,   3.42119992e-01,\
        -3.36030006e-01,   3.32819998e-01,   3.80650014e-01,\
         5.74270003e-02,   9.99180004e-02,   1.25249997e-01,\
         1.10389996e+00,   3.66780013e-02,   3.04899991e-01,\
        -1.49419993e-01,   3.29120010e-01,   2.32999995e-01,\
         4.33950007e-01,   1.56660005e-01,   2.27779999e-01,\
        -2.58300006e-02,   2.43340001e-01,  -5.81360012e-02,\
        -1.34859994e-01,   2.45210007e-01,  -3.34589988e-01,\
         4.28389996e-01,  -4.81810004e-01,   1.34029999e-01,\
         2.60490000e-01,   8.99330005e-02,  -9.37699974e-02,\
         3.76720011e-01,  -2.95579992e-02,   4.38410014e-01,\
         6.12119973e-01,  -2.57200003e-01,  -7.85059988e-01,\
         2.38800004e-01,   1.33990005e-01,  -7.93149993e-02,\
         7.05820024e-01,   3.99679989e-01,   6.77789986e-01,\
        -2.04739999e-03,   1.97850000e-02,  -4.20590013e-01,\
        -5.38580000e-01,  -5.21549992e-02,   1.72519997e-01,\
         2.75469989e-01,  -4.44819987e-01,   2.35949993e-01,\
        -2.34449998e-01,   3.01030010e-01,  -5.50960004e-01,\
        -3.11590005e-02,  -3.44330013e-01,   1.23860002e+00,\
         1.03170002e+00,  -2.27280006e-01,  -9.52070020e-03,\
        -2.54319996e-01,  -2.97919989e-01,   2.59339988e-01,\
        -1.04209997e-01,  -3.38759989e-01,   4.24699992e-01,\
         5.83350018e-04,   1.30930007e-01,   2.87860006e-01,\
         2.34740004e-01,   2.59050000e-02,  -6.43589973e-01,\
         6.13300018e-02,   6.38419986e-01,   1.47049993e-01,\
        -6.15939975e-01,   2.50970006e-01,  -4.48720008e-01,\
         8.68250012e-01,   9.95550007e-02,  -4.47340012e-02,\
        -7.42389977e-01,  -5.91470003e-01,  -5.49290001e-01,\
         3.81080002e-01,   5.51769994e-02,  -1.04869999e-01,\
        -1.28380001e-01,   6.05210010e-03,   2.87429988e-01,\
         2.15920001e-01,   7.28709996e-02,  -3.16439986e-01,\
        -4.33209985e-01,   1.86820000e-01,   6.72739968e-02,\
         2.81150013e-01,  -4.62220013e-02,  -9.68030021e-02,\
         5.60909986e-01,  -6.77619994e-01,  -1.66449994e-01,\
         1.55530006e-01,   5.23010015e-01,  -3.00579995e-01,\
        -3.72909993e-01,   8.78949985e-02,  -1.79629996e-01,\
        -4.41929996e-01,  -4.46069986e-01,  -2.41219997e+00,\
         3.37379992e-01,   6.24159992e-01,   4.27870005e-01,\
        -2.53859997e-01,  -6.16829991e-01,  -7.00969994e-01,\
         4.93030012e-01,   3.69159997e-01,  -9.74989980e-02,\
         6.14109993e-01,  -4.75719990e-03,   4.39159989e-01,\
        -2.15509996e-01,  -5.67449987e-01,  -4.02779996e-01,\
         2.94589996e-01,  -3.08499992e-01,   1.01030000e-01,\
         7.97410011e-02,  -6.38109982e-01,   2.47810006e-01,\
        -4.45459992e-01,   1.08280003e-01,  -2.36240000e-01,\
        -5.08379996e-01,  -1.70010000e-01,  -7.87349999e-01,\
         3.40730011e-01,  -3.18300009e-01,   4.52859998e-01,\
        -9.51180011e-02,   2.07719997e-01,  -8.01829994e-02,\
        -3.79819989e-01,  -4.99489993e-01,   4.07590009e-02,\
        -3.77240002e-01,  -8.97049978e-02,  -6.81869984e-01,\
         2.21059993e-01,  -3.99309993e-01,   3.23289990e-01,\
        -3.61799985e-01,  -7.20929980e-01,  -6.34039998e-01,\
         4.31250006e-01,  -4.97429997e-01,  -1.73950002e-01,\
        -3.87789994e-01,  -3.25560004e-01,   1.44229993e-01,\
        -8.34010020e-02,  -2.29939997e-01,   2.77929991e-01,\
         4.91120011e-01,   6.45110011e-01,  -7.89450034e-02,\
         1.11709997e-01,   3.72640014e-01,   1.30700007e-01,\
        -6.16069995e-02,  -4.35009986e-01,   2.89990008e-02,\
         5.62240005e-01,   5.80120012e-02,   4.70779985e-02,\
         4.27700013e-01,   7.32450008e-01,  -2.11500004e-02,\
         1.19879998e-01,   7.88230002e-02,  -1.91060007e-01,\
         3.52779999e-02,  -3.11019987e-01,   1.32090002e-01,\
        -2.86060005e-01,  -1.56489998e-01,  -6.43390000e-01,\
         4.45989996e-01,  -3.09119999e-01,   4.45199996e-01,\
        -3.67740005e-01,   2.73270011e-01,   6.78330004e-01,\
        -8.38299990e-02,  -4.51200008e-01,   1.07539997e-01,\
        -4.59080011e-01,   1.50950000e-01,  -4.58559990e-01,\
         3.44650000e-01,   7.80130029e-02,  -2.83190012e-01,\
        -2.81489994e-02,   2.44039997e-01,  -7.13450015e-01,\
         5.28340004e-02,  -2.80849993e-01,   2.53439993e-02,\
         4.29789983e-02,   1.56629995e-01,  -7.46469975e-01,\
        -1.13010001e+00,   4.41350013e-01,   3.14440012e-01,\
        -1.00180000e-01,  -5.35260022e-01,  -9.06009972e-01,\
        -6.49540007e-01,   4.26639989e-02,  -7.99269974e-02,\
         3.29050004e-01,  -3.07969987e-01,  -1.91900004e-02,\
         4.27650005e-01,   3.14599991e-01,   2.90509999e-01,\
        -2.73860008e-01,   6.84830010e-01,   1.93949994e-02,\
        -3.28839988e-01,  -4.82389987e-01,  -1.57470003e-01,\
        -1.60359994e-01,   4.91640002e-01,  -7.03520000e-01,\
        -3.55910003e-01,  -7.48870015e-01,  -5.28270006e-01,\
         4.49829996e-02,   5.92469983e-02,   4.62240010e-01,\
         8.96970034e-02,  -7.56179988e-01,   6.36820018e-01,\
         9.06800032e-02,   6.88299984e-02,   1.82960004e-01,\
         1.07539997e-01,   6.78110003e-01,  -1.47159994e-01,\
         1.70289993e-01,  -5.26300013e-01,   1.92680001e-01,\
         9.31299984e-01,   8.03629994e-01,   6.13240004e-01,\
        -3.04939985e-01,   2.02360004e-01,   5.85200012e-01,\
         2.64840007e-01,  -4.58629996e-01,   2.10350007e-03,\
        -5.69899976e-01,  -4.90920007e-01,   4.25110012e-01,\
        -1.09539998e+00,   1.71240002e-01,   2.24950001e-01], dtype=float32)
```

For the sake of convenience, the following function gets the vector of a given string from spaCy's vocabulary:

In \[384\]:

```
def vec(s):
    return nlp.vocab[s].vector
```

### Cosine similarity and finding closest neighbors [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Cosine-similarity-and-finding-closest-neighbors)

The cell below defines a function `cosine()`, which returns the [cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity) of two vectors. Cosine similarity is another way of determining how similar two vectors are, which is more suited to high-dimensional spaces. [See the Encyclopedia of Distances for more information and even more ways of determining vector similarity.](http://www.uco.es/users/ma1fegan/Comunes/asignaturas/vision/Encyclopedia-of-distances-2009.pdf)

(You'll need to install `numpy` to get this to work. If you haven't already: `pip install numpy`. Use `sudo` if you need to and make sure you've upgraded to the most recent version of `pip` with `sudo pip install --upgrade pip`.)

In \[387\]:

```
import numpy as np
from numpy import dot
from numpy.linalg import norm

# cosine similarity
def cosine(v1, v2):
    if norm(v1) > 0 and norm(v2) > 0:
        return dot(v1, v2) / (norm(v1) * norm(v2))
    else:
        return 0.0
```

The following cell shows that the cosine similarity between `dog` and `puppy` is larger than the similarity between `trousers` and `octopus`, thereby demonstrating that the vectors are working how we expect them to:

In \[389\]:

```
cosine(vec('dog'), vec('puppy')) > cosine(vec('trousers'), vec('octopus'))
```

Out\[389\]:

```
True
```

The following cell defines a function that iterates through a list of tokens and returns the token whose vector is most similar to a given vector.

In \[390\]:

```
def spacy_closest(token_list, vec_to_check, n=10):
    return sorted(token_list,
                  key=lambda x: cosine(vec_to_check, vec(x)),
                  reverse=True)[:n]
```

Using this function, we can get a list of synonyms, or words closest in meaning (or distribution, depending on how you look at it), to any arbitrary word in spaCy's vocabulary. In the following example, we're finding the words in _Dracula_ closest to "basketball":

In \[391\]:

```
# what's the closest equivalent of basketball?
spacy_closest(tokens, vec("basketball"))
```

Out\[391\]:

```
[u'tennis',\
 u'coach',\
 u'game',\
 u'teams',\
 u'Junior',\
 u'junior',\
 u'Team',\
 u'school',\
 u'boys',\
 u'leagues']
```

### Fun with spaCy, Dracula, and vector arithmetic [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Fun-with-spaCy,-Dracula,-and-vector-arithmetic)

Now we can start doing vector arithmetic and finding the closest words to the resulting vectors. For example, what word is closest to the halfway point between day and night?

In \[393\]:

```
# halfway between day and night
spacy_closest(tokens, meanv([vec("day"), vec("night")]))
```

Out\[393\]:

```
[u'night',\
 u'day',\
 u'Day',\
 u'evening',\
 u'Evening',\
 u'Morning',\
 u'morning',\
 u'afternoon',\
 u'Nights',\
 u'nights']
```

Variations of `night` and `day` are still closest, but after that we get words like `evening` and `morning`, which are indeed halfway between day and night!

Here are the closest words in _Dracula_ to "wine":

In \[395\]:

```
spacy_closest(tokens, vec("wine"))
```

Out\[395\]:

```
[u'wine',\
 u'beer',\
 u'bottle',\
 u'Drink',\
 u'drink',\
 u'fruit',\
 u'bottles',\
 u'taste',\
 u'coffee',\
 u'tasted']
```

If you subtract "alcohol" from "wine" and find the closest words to the resulting vector, you're left with simply a lovely dinner:

In \[397\]:

```
spacy_closest(tokens, subtractv(vec("wine"), vec("alcohol")))
```

Out\[397\]:

```
[u'wine',\
 u'Dinner',\
 u'dinner',\
 u'lovely',\
 u'delicious',\
 u'salad',\
 u'treasure',\
 u'wonderful',\
 u'Wonderful',\
 u'cheese']
```

The closest words to "water":

In \[398\]:

```
spacy_closest(tokens, vec("water"))
```

Out\[398\]:

```
[u'water',\
 u'waters',\
 u'salt',\
 u'Salt',\
 u'dry',\
 u'liquid',\
 u'ocean',\
 u'boiling',\
 u'heat',\
 u'sand']
```

But if you add "frozen" to "water," you get "ice":

In \[400\]:

```
spacy_closest(tokens, addv(vec("water"), vec("frozen")))
```

Out\[400\]:

```
[u'water',\
 u'cold',\
 u'ice',\
 u'salt',\
 u'Salt',\
 u'dry',\
 u'fresh',\
 u'liquid',\
 u'boiling',\
 u'milk']
```

You can even do analogies! For example, the words most similar to "grass":

In \[401\]:

```
spacy_closest(tokens, vec("grass"))
```

Out\[401\]:

```
[u'grass',\
 u'lawn',\
 u'trees',\
 u'garden',\
 u'GARDEN',\
 u'sand',\
 u'tree',\
 u'soil',\
 u'Green',\
 u'green']
```

If you take the difference of "blue" and "sky" and add it to grass, you get the analogous word ("green"):

In \[280\]:

```
# analogy: blue is to sky as X is to grass
blue_to_sky = subtractv(vec("blue"), vec("sky"))
spacy_closest(tokens, addv(blue_to_sky, vec("grass")))
```

Out\[280\]:

```
[u'grass',\
 u'Green',\
 u'green',\
 u'GREEN',\
 u'yellow',\
 u'red',\
 u'Red',\
 u'purple',\
 u'lawn',\
 u'pink']
```

## Sentence similarity [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Sentence-similarity)

To get the vector for a sentence, we simply average its component vectors, like so:

In \[303\]:

```
def sentvec(s):
    sent = nlp(s)
    return meanv([w.vector for w in sent])
```

Let's find the sentence in our text file that is closest in "meaning" to an arbitrary input sentence. First, we'll get the list of sentences:

In \[304\]:

```
sentences = list(doc.sents)
```

The following function takes a list of sentences from a spaCy parse and compares them to an input sentence, sorting them by cosine similarity.

In \[402\]:

```
def spacy_closest_sent(space, input_str, n=10):
    input_vec = sentvec(input_str)
    return sorted(space,
                  key=lambda x: cosine(np.mean([w.vector for w in x], axis=0), input_vec),
                  reverse=True)[:n]
```

Here are the sentences in _Dracula_ closest in meaning to "My favorite food is strawberry ice cream." (Extra linebreaks are present because we didn't strip them out when we originally read in the source text.)

In \[315\]:

```
for sent in spacy_closest_sent(sentences, "My favorite food is strawberry ice cream."):
    print sent.text
    print "---"
```

```
This, with some cheese
and a salad and a bottle of old Tokay, of which I had two glasses, was
my supper.
---
I got a cup of tea at the Aërated Bread Company
and came down to Purfleet by the next train.

---
We get hot soup, or coffee, or tea; and
off we go.
---
There is not even a toilet glass on my
table, and I had to get the little shaving glass from my bag before I
could either shave or brush my hair.
---
My own heart grew cold as ice,
and I could hear the gasp of Arthur, as we recognised the features of
Lucy Westenra.
---
I dined on what they
called "robber steak"--bits of bacon, onion, and beef, seasoned with red
pepper, and strung on sticks and roasted over the fire, in the simple
style of the London cat's meat!
---
I believe they went to the trouble of putting an
extra amount of garlic into our food; and I can't abide garlic.
---
Drink it off, like a good
child.
---
I had for dinner, or
rather supper, a chicken done up some way with red pepper, which was
very good but thirsty.
---
I left Quincey lying down
after having a glass of wine, and told the cook to get ready a good
breakfast.
---
```

## Further resources [¶](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469/blob/ddcd14198283486fe6f2707125f53477fbd42095//\#Further-resources)

- [Word2vec](https://en.wikipedia.org/wiki/Word2vec) is another procedure for producing word vectors which uses a predictive approach rather than a context-counting approach. [This paper](http://clic.cimec.unitn.it/marco/publications/acl2014/baroni-etal-countpredict-acl2014.pdf) compares and contrasts the two approaches. (Spoiler: it's kind of a wash.)
- If you want to train your own word vectors on a particular corpus, the popular Python library [gensim](https://radimrehurek.com/gensim/) has an implementation of Word2Vec that is relatively easy to use. [There's a good tutorial here.](https://rare-technologies.com/word2vec-tutorial/)
- When you're working with vector spaces with high dimensionality and millions of vectors, iterating through your entire space calculating cosine similarities can be a drag. I use [Annoy](https://pypi.python.org/pypi/annoy) to make these calculations faster, and you should consider using it too.

[![@jordantkohn](https://avatars.githubusercontent.com/u/39426842?s=80&v=4)](https://gist.github.com/jordantkohn)


Copy link


Copy Markdown

### **[jordantkohn](https://gist.github.com/jordantkohn)**     commented    [on Jul 1, 2019Jul 1, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=2959166\#gistcomment-2959166)

For the Dracula and Wallpaper examples, isn't the code only checking for one-word colors (e.g. blue, yellow, red) and not for two-word colors as well (e.g. burnt orange, tomato red, sunflower yellow)??

[![@girgop](https://avatars.githubusercontent.com/u/53112859?s=80&v=4)](https://gist.github.com/girgop)


Copy link


Copy Markdown

### **[girgop](https://gist.github.com/girgop)**     commented    [on Jul 20, 2019Jul 20, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=2975789\#gistcomment-2975789)

Thanks! Helped me to get ground on word vectors.

[![@aafreenrah](https://avatars.githubusercontent.com/u/37484382?s=80&v=4)](https://gist.github.com/aafreenrah)


Copy link


Copy Markdown

### **[aafreenrah](https://gist.github.com/aafreenrah)**     commented    [on Aug 31, 2019Aug 31, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3013460\#gistcomment-3013460)

Best explanation. Thank you very much.

[![@lschomp](https://avatars.githubusercontent.com/u/40773453?s=80&v=4)](https://gist.github.com/lschomp)


Copy link


Copy Markdown

### **[lschomp](https://gist.github.com/lschomp)**     commented    [on Sep 7, 2019Sep 7, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3019311\#gistcomment-3019311)

this looks super exciting and I'm eager to explore but right off this line isn't working for me? color\_data = json.loads(open("xkcd.json").read()) in the notebook?

* * *

FileNotFoundError Traceback (most recent call last)

in

----\> 1 color\_data = json.loads(open("xkcd.json").read())

FileNotFoundError: \[Errno 2\] No such file or directory: 'xkcd.json'

[![@Mayar2009](https://avatars.githubusercontent.com/u/38237790?s=80&v=4)](https://gist.github.com/Mayar2009)


Copy link


Copy Markdown

### **[Mayar2009](https://gist.github.com/Mayar2009)**     commented    [on Sep 29, 2019Sep 29, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3040382\#gistcomment-3040382)

[@lschomp](https://github.com/lschomp) you should install the file in the same path with notebook to work

[![@Mayar2009](https://avatars.githubusercontent.com/u/38237790?s=80&v=4)](https://gist.github.com/Mayar2009)


Copy link


Copy Markdown

### **[Mayar2009](https://gist.github.com/Mayar2009)**     commented    [on Sep 29, 2019Sep 29, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3040423\#gistcomment-3040423)•   edited      Loading          \#\#\# Uh oh!        There was an error while loading. [Please reload this page](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469).

> One of the best tutorials on word to vec. Nevertheless there is a "quantum-leap" in the explanation when it comes to "Word vectors in spaCy". Suddenly we have vectors associated to any word, of a predetermined dimension. Why? Where are those vectors coming from? how are they calculated? Based on which texts? Since wordtovec takes into account context the vector representations are going to be very different in technical papers, in literature, poetry, facebook posts etc. How do you create your own vectors related to a particular collection of concepts over a particular set of documents? I observed this problematic in many many word2vec tutorials. The explanation starts very smoothly, basic, very well explained up to details; and suddenly there is a big hole in the explanation. In any case this is one of the best explanations I have found on wordtovec theory. thanks

I agree

for color example

what if there where another colors but they are not in the colors dictionary how to discover them

how to use this technique in recommender systems for example?

[![@imkhubaibraza](https://avatars.githubusercontent.com/u/22439327?s=80&v=4)](https://gist.github.com/imkhubaibraza)


Copy link


Copy Markdown

### **[imkhubaibraza](https://gist.github.com/imkhubaibraza)**     commented    [on Dec 3, 2019Dec 3, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3099048\#gistcomment-3099048)

Great explanation, Thank you for sharing

[![@john77eipe](https://avatars.githubusercontent.com/u/1938453?s=80&v=4)](https://gist.github.com/john77eipe)


Copy link


Copy Markdown

### **[john77eipe](https://gist.github.com/john77eipe)**     commented    [on Dec 19, 2019Dec 19, 2019](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3115932\#gistcomment-3115932)

The whole code has been updated for the latest versions of python and spacy.

Available here as a notebook: [https://www.kaggle.com/john77eipe/understanding-word-vectors](https://www.kaggle.com/john77eipe/understanding-word-vectors)

[![@DouglasLapsley](https://avatars.githubusercontent.com/u/15831662?s=80&v=4)](https://gist.github.com/DouglasLapsley)


Copy link


Copy Markdown

### **[DouglasLapsley](https://gist.github.com/DouglasLapsley)**     commented    [on Feb 17, 2020Feb 17, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3180123\#gistcomment-3180123)

Fantastic article thank you. How could I scale this to compare a single sentence with around a million other sentences to find the most similar ones though? I’m thinking that iteration wouldn’t be an option? Thanks!

[![@zetadaro](https://avatars.githubusercontent.com/u/6061279?s=80&v=4)](https://gist.github.com/zetadaro)


Copy link


Copy Markdown

### **[zetadaro](https://gist.github.com/zetadaro)**     commented    [on Feb 17, 2020Feb 17, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3180266\#gistcomment-3180266)

> Fantastic article thank you. How could I scale this to compare a single sentence with around a million other sentences to find the most similar ones though? I’m thinking that iteration wouldn’t be an option? Thanks!

I have the same problem and I was thinking about the non performance of iterate over so many sentences. If you get something interesting related to this it will be great to share it, I will do the same.

[![@DouglasLapsley](https://avatars.githubusercontent.com/u/15831662?s=80&v=4)](https://gist.github.com/DouglasLapsley)


Copy link


Copy Markdown

### **[DouglasLapsley](https://gist.github.com/DouglasLapsley)**     commented    [on Feb 17, 2020Feb 18, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3180424\#gistcomment-3180424)

> > Fantastic article thank you. How could I scale this to compare a single sentence with around a million other sentences to find the most similar ones though? I’m thinking that iteration wouldn’t be an option? Thanks!
>
> I have the same problem and I was thinking about the non performance of iterate over so many sentences. If you get something interesting related to this it will be great to share it, I will do the same.

Will do. I've looked at a number of text similarity approaches and they all seem to either rely on iteration or semantic word graphs with a pre-calculated one to one similarity relationship between all the nodes which means 1M nodes = 1M x 1M relationships which is also clearly untennable and very slow to process. I'm sure I must be missing something obvious, but I'm not sure what!

The only thing I can think of at the moment is pre-processing the similarity by saving the vectors for each sentence against their database record, then iterating for each sentence against each other sentence in the way described in this article (or any other similarity distance function), and then saving a one to one graph similarity relationship only for items that are highly similar (to reduce the number of similarity relationships created only to relevent ones). i.e. don't do the iteration at run-time, but rather do the iteration once and save the resulting similarities where of high similarity in node relationships which would be quick to query at runtime.

I'd welcome any guidance from others on this though! Has anyone tried this approach?

[![@DouglasLapsley](https://avatars.githubusercontent.com/u/15831662?s=80&v=4)](https://gist.github.com/DouglasLapsley)


Copy link


Copy Markdown

### **[DouglasLapsley](https://gist.github.com/DouglasLapsley)**     commented    [on Feb 18, 2020Feb 19, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3181581\#gistcomment-3181581)

> > Fantastic article thank you. How could I scale this to compare a single sentence with around a million other sentences to find the most similar ones though? I’m thinking that iteration wouldn’t be an option? Thanks!
>
> I have the same problem and I was thinking about the non performance of iterate over so many sentences. If you get something interesting related to this it will be great to share it, I will do the same.

It looks like a pre-trained approximate nearest neighbour approach may be a good option where you have large numbers of vectors. I've not yet tried this, but here is the logic [https://erikbern.com/2015/09/24/nearest-neighbor-methods-vector-models-part-1.html](https://erikbern.com/2015/09/24/nearest-neighbor-methods-vector-models-part-1.html) and here is an implementation [https://medium.com/@kevin\_yang/simple-approximate-nearest-neighbors-in-python-with-annoy-and-lmdb-e8a701baf905](https://medium.com/@kevin_yang/simple-approximate-nearest-neighbors-in-python-with-annoy-and-lmdb-e8a701baf905)

Using the Annoy library, essentially the approach here is to create an lmdb map and an Annoy index with the word embeddings. Then save those to disk. At runtime, load these, vectorise your query text and use Annoy to look up n nearest neighbours and return their IDs.

Anyone have experience of this with sentences rather than just words?

[![@juhanishen](https://avatars.githubusercontent.com/u/8583850?s=80&v=4)](https://gist.github.com/juhanishen)


Copy link


Copy Markdown

### **[juhanishen](https://gist.github.com/juhanishen)**     commented    [on Jun 16, 2020Jun 16, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3343111\#gistcomment-3343111)

Awesome good!

[![@juliansteam](https://avatars.githubusercontent.com/u/27698944?s=80&v=4)](https://gist.github.com/juliansteam)


Copy link


Copy Markdown

### **[juliansteam](https://gist.github.com/juliansteam)**     commented    [on Aug 14, 2020Aug 14, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3417344\#gistcomment-3417344)

Vey intuitive tutorial. Thank you!

[![@erkekin](https://avatars.githubusercontent.com/u/701481?s=80&v=4)](https://gist.github.com/erkekin)


Copy link


Copy Markdown

### **[erkekin](https://gist.github.com/erkekin)**     commented    [on Aug 25, 2020Aug 25, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3430100\#gistcomment-3430100)

> Not sure why I'm getting the following error, working on macOS with Jupyter Lab, Python 2.7 and Spacy 2.0.9:
>
> ```
> ---------------------------------------------------------------------------
> ValueError                                Traceback (most recent call last)
> <ipython-input-2-090b6e832a74> in <module>()
>       3 # It creates a list of unique words in the text
>       4 tokens = list(set([w.text for w in doc if w.is_alpha]))
> ----> 5 print nlp.vocab['cheese'].vector
>
> lexeme.pyx in spacy.lexeme.Lexeme.vector.__get__()
>
> ValueError: Word vectors set to length 0. This may be because you don't have a model installed or loaded, or because your model doesn't include word vectors. For more info, see the documentation:
> https://spacy.io/usage/models
> ```

replace `nlp.vocab['cheese'].vector` with `nlp('cheese').vector`

and

```
def vec(s):
    return nlp.vocab[s].vector
```

with

```
def vec(s):
    return nlp(s).vector
```

[![@motahher](https://avatars.githubusercontent.com/u/75749503?s=80&v=4)](https://gist.github.com/motahher)


Copy link


Copy Markdown

### **[motahher](https://gist.github.com/motahher)**     commented    [on Dec 10, 2020Dec 10, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3556532\#gistcomment-3556532)

very good explanation

[![@JenPink25](https://avatars.githubusercontent.com/u/67128562?s=80&v=4)](https://gist.github.com/JenPink25)


Copy link


Copy Markdown

### **[JenPink25](https://gist.github.com/JenPink25)**     commented    [on Dec 17, 2020Dec 18, 2020](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3565491\#gistcomment-3565491)

Enjoyed reading this. Thank you!

[![@lewiuberg](https://avatars.githubusercontent.com/u/43423020?s=80&v=4)](https://gist.github.com/lewiuberg)


Copy link


Copy Markdown

### **[lewiuberg](https://gist.github.com/lewiuberg)**     commented    [on Jan 4, 2021Jan 4, 2021](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3581788\#gistcomment-3581788)

> One of the best tutorials on word to vec. Nevertheless there is a "quantum-leap" in the explanation when it comes to "Word vectors in spaCy". Suddenly we have vectors associated to any word, of a predetermined dimension. Why? Where are those vectors coming from? how are they calculated? Based on which texts? Since wordtovec takes into account context the vector representations are going to be very different in technical papers, in literature, poetry, facebook posts etc. How do you create your own vectors related to a particular collection of concepts over a particular set of documents? I observed this problematic in many many word2vec tutorials. The explanation starts very smoothly, basic, very well explained up to details; and suddenly there is a big hole in the explanation. In any case this is one of the best explanations I have found on wordtovec theory. thanks

I agree! I thought I had deleted many cells and downloaded it again looking for the gap.

[![@jdmedenilla](https://avatars.githubusercontent.com/u/78578577?s=80&v=4)](https://gist.github.com/jdmedenilla)


Copy link


Copy Markdown

### **[jdmedenilla](https://gist.github.com/jdmedenilla)**     commented    [on Feb 12, 2021Feb 12, 2021](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3629147\#gistcomment-3629147)•   edited      Loading          \#\#\# Uh oh!        There was an error while loading. [Please reload this page](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469).

When I ran snippets of code that access a library, it gave me errors like this: "FileNotFoundError: \[Errno 2\] No such file or directory: 'pg345.txt'". And same thing with the color file: "FileNotFoundError: \[Errno 2\] No such file or directory: 'xkcd.json'"

I ran those on jupyter notebook. Do you know what's wrong?

Note: I tried doing it in Visual Code but it gave me the same problem, even after saving it in the same directory. Also i've read online to use the absolute path, but it still would not work.

[![@Zaravanon](https://avatars.githubusercontent.com/u/65016991?s=80&v=4)](https://gist.github.com/Zaravanon)


Copy link


Copy Markdown

### **[Zaravanon](https://gist.github.com/Zaravanon)**     commented    [on Mar 4, 2021Mar 4, 2021](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3653197\#gistcomment-3653197)

Great, Thank You!

[![@tugcekizilltepe](https://avatars.githubusercontent.com/u/56649386?s=80&v=4)](https://gist.github.com/tugcekizilltepe)


Copy link


Copy Markdown

### **[tugcekizilltepe](https://gist.github.com/tugcekizilltepe)**     commented    [on Apr 28, 2021Apr 28, 2021](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3723775\#gistcomment-3723775)

Great, well-explained tutorial, thank you!

[![@prakashr7d](https://avatars.githubusercontent.com/u/61550525?s=80&v=4)](https://gist.github.com/prakashr7d)


Copy link


Copy Markdown

### **[prakashr7d](https://gist.github.com/prakashr7d)**     commented    [on May 28, 2021May 28, 2021](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3761237\#gistcomment-3761237)

> Not sure why I'm getting the following error, working on macOS with Jupyter Lab, Python 2.7 and Spacy 2.0.9:
>
> ```
> ---------------------------------------------------------------------------
> ValueError                                Traceback (most recent call last)
> <ipython-input-2-090b6e832a74> in <module>()
>       3 # It creates a list of unique words in the text
>       4 tokens = list(set([w.text for w in doc if w.is_alpha]))
> ----> 5 print nlp.vocab['cheese'].vector
>
> lexeme.pyx in spacy.lexeme.Lexeme.vector.__get__()
>
> ValueError: Word vectors set to length 0. This may be because you don't have a model installed or loaded, or because your model doesn't include word vectors. For more info, see the documentation:
> https://spacy.io/usage/models
> ```

You want to download 'en\_core\_web\_lg' model

[![@saiankit](https://avatars.githubusercontent.com/u/50326918?s=80&v=4)](https://gist.github.com/saiankit)


Copy link


Copy Markdown

### **[saiankit](https://gist.github.com/saiankit)**     commented    [on Aug 31, 2021Aug 31, 2021](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3877744\#gistcomment-3877744)

OMG !! Really had a great time reading this beautiful gist. Very well explained.

[![@DavidHarar](https://avatars.githubusercontent.com/u/54071003?s=80&v=4)](https://gist.github.com/DavidHarar)


Copy link


Copy Markdown

### **[DavidHarar](https://gist.github.com/DavidHarar)**     commented    [on Sep 4, 2021Sep 5, 2021](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=3882615\#gistcomment-3882615)

Thanks!

[![@mikeolubode](https://avatars.githubusercontent.com/u/86394385?s=80&v=4)](https://gist.github.com/mikeolubode)


Copy link


Copy Markdown

### **[mikeolubode](https://gist.github.com/mikeolubode)**     commented    [on Feb 4, 2022Feb 4, 2022](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=4053867\#gistcomment-4053867)

I was led here by a tutorial on word vectors from youtube. Thanks for the simplicity!

[![@yishairasowsky](https://avatars.githubusercontent.com/u/39579959?s=80&v=4)](https://gist.github.com/yishairasowsky)


Copy link


Copy Markdown

### **[yishairasowsky](https://gist.github.com/yishairasowsky)**     commented    [on Mar 14, 2022Mar 14, 2022](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=4096899\#gistcomment-4096899)

very good

[![@robertocsa](https://avatars.githubusercontent.com/u/3252597?s=80&v=4)](https://gist.github.com/robertocsa)


Copy link


Copy Markdown

### **[robertocsa](https://gist.github.com/robertocsa)**     commented    [on Sep 14, 2022Sep 15, 2022](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=4301976\#gistcomment-4301976)

Thank you for sharing this. Excelent job!

[![@avneesh91](https://avatars.githubusercontent.com/u/5255331?s=80&v=4)](https://gist.github.com/avneesh91)


Copy link


Copy Markdown

### **[avneesh91](https://gist.github.com/avneesh91)**     commented    [on May 5, 2023May 5, 2023](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=4559349\#gistcomment-4559349)

this is amazing, thank you for explanation!!

[![@prateekcaire](https://avatars.githubusercontent.com/u/2161006?s=80&v=4)](https://gist.github.com/prateekcaire)


Copy link


Copy Markdown

### **[prateekcaire](https://gist.github.com/prateekcaire)**     commented    [on Jun 12, 2023Jun 12, 2023](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=4596715\#gistcomment-4596715)

Thanks!!

[![@adebiasi](https://avatars.githubusercontent.com/u/22911963?s=80&v=4)](https://gist.github.com/adebiasi)


Copy link


Copy Markdown

### **[adebiasi](https://gist.github.com/adebiasi)**     commented    [on Nov 29, 2023Nov 29, 2023](https://gist.github.com/aparrish/2f562e3737544cf29aaf1af30362f469?permalink_comment_id=4776631\#gistcomment-4776631)

Very nice tutorial!

One question:

A word near the origin (0,0,0 ...) in the n-space has less possibility to be the result of an addition among words. As opposite, a word very distant of the origin could be the result of many possible additions among many words. Does this mean that complex concepts are far for the origin and basic concepts are near?

[Sign up for free](https://gist.github.com/join?source=comment-gist) **to join this conversation on GitHub**.
Already have an account?
[Sign in to comment](https://gist.github.com/login?return_to=https%3A%2F%2Fgist.github.com%2Faparrish%2F2f562e3737544cf29aaf1af30362f469)

You can’t perform that action at this time.
