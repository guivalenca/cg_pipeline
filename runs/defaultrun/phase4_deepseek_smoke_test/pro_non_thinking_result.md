# Phase 4 Lesson Reconciliation Smoke-Test Evaluation

## 1. Overall Judgment

The Phase 4 reconciliation generally reduces noise from the initial candidate lists, but the pipeline’s effectiveness is highly inconsistent across the 12 lessons. Lessons L03, L04, L06, and L07 show strong, defensible merges that group related concepts into coherent teachable blocks. However, lessons L01, L02, and L05 reveal a significant, systemic bug: entire clusters of source-backed candidates are deterministically moved to `review` status with an “omitted” explanation, meaning valid, lesson-relevant concepts have been effectively lost and replaced by an empty set. Additionally, several lessons (L01, L04, L05, L08) accept off-topic or ancillary material—such as Bash scripting, GitHub licenses, and environment setup—while pruning or ignoring NLP-specific content. Subject Merge would receive a degraded concept graph with large gaps. A full repair of the reconciliation logic is needed before proceeding.

## 2. Lesson Score Matrix

| Lesson | Concept | Granularity | Evidence | Assignment | Prune/Review | Criteria | Coherence | Net | Flags |
|--------|---------|-------------|----------|------------|--------------|----------|-----------|-----|-------|
| L01 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 1 | off_lesson_acceptance, granularity_loss, under_merge |
| L02 | 2 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | review_needed, under_merge |
| L03 | 2 | 1 | 2 | 2 | 1 | 2 | 2 | 2 | over_merge, questionable_prune |
| L04 | 2 | 2 | 3 | 3 | 3 | 3 | 2 | 3 | off_lesson_acceptance |
| L05 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | over_merge |
| L06 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | strong_improvement |
| L07 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | strong_improvement |
| L08 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | off_lesson_acceptance |
| L09 | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 3 | strong_improvement |
| L10 | 2 | 2 | 2 | 3 | 3 | 2 | 2 | 2 | over_merge |
| L11 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | strong_improvement |
| L12 | 2 | 2 | 3 | 3 | 3 | 2 | 2 | 2 | over_merge |

*Note: Scores above reflect aggregated quality. Specific dimensions like Prune/Review score 1 when no pruning occurred but review queue is abused.*

## 3. High-Confidence Problems

- **L01: Off-lesson acceptance.** The reconciled set includes 9 concepts on Bash scripting (shell, variables, loops), despite the lesson metadata describing NLP. This constitutes a high proportion of irrelevant accepted concepts, lowering Concept Validity and Coherence.  
- **L02, L05: Broken review fallback.** In L02, 48 of 76 input candidates are placed in `review` with explanation “Deterministically added because cluster evaluation omitted this input candidate.” This is a pipeline bug, not a principled review decision. The same pattern repeats in L05 for all regex-related candidates, leaving large thematic gaps.  
- **L03: Over-merge and premature pruning.** 34 candidates are pruned as “near_duplicate” with the rationale that they will be handled in future clusters, but no such clusters appear in the lesson output. Key concepts like BoW pipeline steps, vectorization details, and CountVectorizer usage are lost.  
- **L03: Over-broad concept.** Only 4 reconciled candidates survive for a dedicated BoW lesson, and one of them (“N-gram Extension to BoW”) is merged so aggressively that vocabulary construction and vectorization are completely absent.  
- **L04: Off-topic content accepted.** Concepts on GitHub licensing, copyright, and license pickers are unrelated to NLTK/spaCy lesson metadata but are accepted as 6 distinct concepts.  
- **L05: Imbalanced focus.** Five candidates on Naive Bayes variants from a single source are preserved as separate concepts, while a Python implementation class structure and many text-preprocessing candidates from other sources are merged or pruned, creating a skewed coverage.  
- **L08: Environment/config material.** Seven concepts cover pip package selection, GPU verification, OS support, and Visual C++ Redistributable—these are installation instructions, not NLP or neural network concepts.  

## 4. Strong Transformations

- **L06 (Word2Vec & Gensim):** Clean merges of the Gensim document, corpus, streaming, vector, model, Dictionary, and TF-IDF concepts into just 8 well-scoped, practical concepts. High fidelity to lesson metadata.  
- **L07 (Neural Networks):** Excellent collapse of 67 diverse candidates into 35 focused concepts covering perceptron, activation functions, backpropagation, gradient descent, architectures, and frameworks. Historical and cross-source duplicates were correctly merged.  
- **L09 (Word2Vec + NN):** Well-structured merges for vector similarity, analogies, distributional hypothesis, and Gensim preprocessing pipeline. Metadata candidates that were too broad were correctly pruned with appropriate reasons.  
- **L11 (TF, TF-IDF, LSA):** TF-IDF computation, preprocessing, vectorization, and comparison to BoW are logically grouped. LSA material is accurately synthesized into a two-part concept.  
- **L04 (NLTK/spaCy):** Portuguese text exploration, tokenization, stemming, lemmatization, and spaCy pipelines are well-grouped, with separate concepts for each major step.

## 5. Recommendation

**repair_before_phase5**

**Minimum repair scope:**
1. **Fix the “deterministic omission” review fallback in L02 and L05.** All valid candidates that were omitted by the clustering logic must be reevaluated and assigned to proper accepted or pruned status; the review queue cannot be used as a dumping ground.
2. **Remove off-topic accepted concepts in L01, L04, and L08.** Bash shell scripting, GitHub licensing, and TensorFlow installation/environment steps should be pruned with reason `unrelated` or `low_teaching_value`.
3. **Un-prune critical BoW pipeline concepts in L03.** Vocabulary construction, vectorization steps, CountVectorizer usage, and sparsity should be promoted to accepted status; ensure the lesson’s accepted concept count reflects its metadata scope.
4. **Re-split over-merged concepts in L05 and L12.** In L05, break the oversized “Naive Bayes for Text Classification” into separate algorithm explanation and applied SMS example concepts. In L12, split the monolithic “ISO 25010 Interaction Capability” into at least 2–3 practical sub-groups.
5. **Validate against lesson metadata in L01.** Reconcile accepted concepts such that NLP pipeline steps, lexical similarity metrics, regex techniques, and feature representation form the core; remove the entire Bash subtree.