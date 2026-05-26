---
id: "20"
title: "ATIVIDADE: Pipeline Dinâmico para Classificadores Clássicos"
source_url: "https://scikit-learn.org/stable/"
fetch_url: "https://scikit-learn.org/stable"
resolved_url: "https://scikit-learn.org/stable/"
firecrawl_title: "scikit-learn: machine learning in Python — scikit-learn 1.8.0 documentation"
description: null
fetched_at: "2026-05-12T03:59:51.289768Z"
provider: "firecrawl"
strategy: "standard"
cache_key: "934cddbf32ce11f915590f159cf8155bfb516f165d87576e6c7dd576d44e1e48"
firecrawl_status_code: 200
firecrawl_content_type: "text/html; charset=utf-8"
word_count: 987
char_count: 7640
content_sha256: "5697991cf5278d01a28259ded5211ffe40c15e839fa387e1098e15a18a5607a1"
image_count: 21
link_count: 77
warnings: []
gate_status: "passed"
gate_failures: []
route_notes: []
---

# scikit-learn

#### Machine Learning in Python

- Simple and efficient tools for predictive data analysis
- Accessible to everybody, and reusable in various contexts
- Built on NumPy, SciPy, and matplotlib
- Open source, commercially usable - BSD license

#### [Classification](https://scikit-learn.org/stable/supervised_learning.html)

Identifying which category an object belongs to.

**Applications:** Spam detection, image recognition.

**Algorithms:** [Gradient boosting](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting), [nearest neighbors](https://scikit-learn.org/stable/modules/neighbors.html#classification), [random forest](https://scikit-learn.org/stable/modules/ensemble.html#forest), [logistic regression](https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression), and [more...](https://scikit-learn.org/stable/supervised_learning.html)

Image summary: A side-by-side classifier comparison on the same 2D dataset shows different decision boundaries and prediction regions for several algorithms, illustrating that methods such as nearest neighbors, linear SVM, RBF SVM, Gaussian process, decision tree, random forest, neural net, AdaBoost, naive Bayes, and QDA can produce very different fits to the same data. [Original image: Classifier comparison](https://scikit-learn.org/stable/_images/sphx_glr_plot_classifier_comparison_001_carousel.png)

[Examples](https://scikit-learn.org/stable/auto_examples/classification/index.html)

#### [Regression](https://scikit-learn.org/stable/supervised_learning.html)

Predicting a continuous-valued attribute associated with an object.

**Applications:** Drug response, stock prices.

**Algorithms:** [Gradient boosting](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting), [nearest neighbors](https://scikit-learn.org/stable/modules/neighbors.html#regression), [random forest](https://scikit-learn.org/stable/modules/ensemble.html#forest), [ridge](https://scikit-learn.org/stable/modules/linear_model.html#ridge-regression-and-classification), and [more...](https://scikit-learn.org/stable/supervised_learning.html)

Image summary: A line chart titled "Predicted average energy transfer during the week" compares three series: recorded average, max_iter=5, and max_iter=50. The x-axis is Time of the week from Sun to Sat, and the y-axis is Normalized energy transfer. The plot shows that the two model settings track the recorded average with different levels of smoothness and variation. [Original image: Decision Tree Regression with HGBT](https://scikit-learn.org/stable/_images/sphx_glr_plot_hgbt_regression_002.png)

[Examples](https://scikit-learn.org/stable/auto_examples/index.html)

#### [Clustering](https://scikit-learn.org/stable/modules/clustering.html)

Automatic grouping of similar objects into sets.

**Applications:** Customer segmentation, grouping experiment outcomes.

**Algorithms:** [k-Means](https://scikit-learn.org/stable/modules/clustering.html#k-means), [HDBSCAN](https://scikit-learn.org/stable/modules/clustering.html#hdbscan), [hierarchical clustering](https://scikit-learn.org/stable/modules/clustering.html#hierarchical-clustering), and [more...](https://scikit-learn.org/stable/modules/clustering.html)

Image summary: A k-means clustering example on the handwritten digits dataset after PCA reduction. The plot shows colored cluster regions, scattered digit points, and white cross markers indicating the centroids of each cluster. [Original image: A demo of K-Means clustering on the handwritten digits data](https://scikit-learn.org/stable/_images/sphx_glr_plot_kmeans_digits_thumb.png)

[Examples](https://scikit-learn.org/stable/auto_examples/cluster/index.html)

#### [Dimensionality reduction](https://scikit-learn.org/stable/modules/decomposition.html)

Reducing the number of random variables to consider.

**Applications:** Visualization, increased efficiency.

**Algorithms:** [PCA](https://scikit-learn.org/stable/modules/decomposition.html#pca), [feature selection](https://scikit-learn.org/stable/modules/feature_selection.html#feature-selection), [non-negative matrix factorization](https://scikit-learn.org/stable/modules/decomposition.html#nmf), and [more...](https://scikit-learn.org/stable/modules/decomposition.html)

Image summary: The image shows a pairwise scatterplot matrix for the Iris dataset, with points colored by species. It visualizes how the four measurements relate to one another and how the classes separate across feature pairs, motivating dimensionality reduction with PCA. [Original image: PCA example with Iris Data-set](https://scikit-learn.org/stable/_images/sphx_glr_plot_pca_iris_thumb.png)

[Examples](https://scikit-learn.org/stable/auto_examples/decomposition/index.html)

#### [Model selection](https://scikit-learn.org/stable/model_selection.html)

Comparing, validating and choosing parameters and models.

**Applications:** Improved accuracy via parameter tuning.

**Algorithms:** [Grid search](https://scikit-learn.org/stable/modules/grid_search.html), [cross validation](https://scikit-learn.org/stable/modules/cross_validation.html), [metrics](https://scikit-learn.org/stable/modules/model_evaluation.html), and [more...](https://scikit-learn.org/stable/model_selection.html)

Image summary: The plot titled “GridSearchCV evaluating using multiple scorers simultaneously” compares several metrics across values of `n_estimators`. It shows separate curves for AUC, accuracy, and precision, with shaded variability bands and a marked best setting around 100 estimators. [Original image: Demonstration of multi-metric evaluation on cross_val_score and GridSearchCV](https://scikit-learn.org/stable/_images/sphx_glr_plot_multi_metric_evaluation_thumb.png)

[Examples](https://scikit-learn.org/stable/auto_examples/model_selection/index.html)

#### [Preprocessing](https://scikit-learn.org/stable/modules/preprocessing.html)

Feature extraction and normalization.

**Applications:** Transforming input data such as text for use with machine learning algorithms.

**Algorithms:** [Preprocessing](https://scikit-learn.org/stable/modules/preprocessing.html), [feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html), and [more...](https://scikit-learn.org/stable/modules/preprocessing.html)

Image summary: The image compares KBinsDiscretizer binning strategies on sample data. It shows the input data alongside three discretization methods labeled uniform, quantile, and k-means, illustrating how each strategy partitions the feature space differently. [Original image: Demonstrating the different strategies of KBinsDiscretizer](https://scikit-learn.org/stable/_images/sphx_glr_plot_discretization_strategies_thumb.png)

[Examples](https://scikit-learn.org/stable/auto_examples/preprocessing/index.html)

#### News

- **On-going development:** [scikit-learn 1.9 (Changelog)](https://scikit-learn.org/dev/whats_new/v1.9.html#version-1-9-0).
- **December 2025.** scikit-learn 1.8.0 is available for download ( [Changelog](https://scikit-learn.org/stable/whats_new/v1.8.html#version-1-8-0)).
- **September 2025.** scikit-learn 1.7.2 is available for download ( [Changelog](https://scikit-learn.org/stable/whats_new/v1.7.html#version-1-7-2)).
- **July 2025.** scikit-learn 1.7.1 is available for download ( [Changelog](https://scikit-learn.org/stable/whats_new/v1.7.html#version-1-7-1)).
- **June 2025.** scikit-learn 1.7.0 is available for download ( [Changelog](https://scikit-learn.org/stable/whats_new/v1.7.html#version-1-7-0)).
- **January 2025.** scikit-learn 1.6.1 is available for download ( [Changelog](https://scikit-learn.org/stable/whats_new/v1.6.html#version-1-6-1)).
- **December 2024.** scikit-learn 1.6.0 is available for download ( [Changelog](https://scikit-learn.org/stable/whats_new/v1.6.html#version-1-6-0)).
- **All releases:** [**What's new** (Changelog)](https://scikit-learn.org/dev/whats_new.html).

#### Who uses scikit-learn?

[Image: inria](https://scikit-learn.org/stable/_images/inria.png)  _"We use scikit-learn to support leading-edge basic research [...]"_

[Image: spotify](https://scikit-learn.org/stable/_images/spotify.png)  _"I think it's the most well-designed ML package I've seen so far."_

[Image: change-logo](https://scikit-learn.org/stable/_images/change-logo.png)  _"scikit-learn's ease-of-use, performance and overall variety of algorithms implemented has proved invaluable [...]"_

[Image: telecomparistech](https://scikit-learn.org/stable/_images/telecomparistech.jpg)  _"The great benefit of scikit-learn is its fast learning curve [...]"_

[Image: aweber](https://scikit-learn.org/stable/_images/aweber.png)  _"It allows us to do AWesome stuff we would not otherwise accomplish."_

[Image: yhat](https://scikit-learn.org/stable/_images/yhat.png)  _"scikit-learn makes doing advanced analysis in Python accessible to anyone."_

[More testimonials...](https://scikit-learn.org/stable/testimonials/testimonials.html)
