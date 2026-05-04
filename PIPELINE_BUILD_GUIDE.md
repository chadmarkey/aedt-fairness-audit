# Building an AEDT Pipeline for Audit Use

This guide walks through implementing the architecture disclosed in
[U.S. Patent No. 12,265,502 B1](https://patents.google.com/patent/US12265502B1)
from off-the-shelf libraries. The result is a `score_texts` function
that the audit harness can call.

The library does not ship a patent-replicated pipeline. The pipeline
lives in the user's workspace.

Estimated build time: 4–6 hours for someone familiar with
`sentence-transformers`, `scikit-learn`, and `hdbscan`.

## A note on building from a public patent

Building a working implementation of an architecture disclosed in a
public patent, for non-commercial research purposes, is the kind of
activity patents are designed to enable. The disclosure is published
specifically so the field can study and replicate it.

This is no different from going to a museum and sketching a sculpture
into a notebook, or following an instruction sheet to snap five Lego
bricks together. The work and the recipe are on public display so the
public can engage with them; that engagement is the disclosure's
intended use.

## Pipeline elements

The patent's machine learning framework (col. 22, lines 1–7;
specification's FIG. 5) consists of these elements:

| Element | Patent col./line | Function | Suggested library |
|---|---|---|---|
| §518 | col. 22 ll. 8–25 | Document pre-processing: split into sentences, normalize text, optional bias-mitigation blinding | `spacy` or stdlib `re` |
| §520 | col. 22 ll. 26–35 | Semantic embedding (Word2Vec, GloVe, BERT, or Sentence-BERT) | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| §522 | col. 22 ll. 36–47 | Dimensionality reduction (t-SNE, PCA, or UMAP) | `sklearn.decomposition.PCA` |
| §524 | col. 22 ll. 48–66 | Unsupervised clustering (K-means, DBSCAN, HDBSCAN) | `hdbscan` (or `sklearn.cluster.OPTICS` as fallback) |
| §526 | col. 22 l. 67 – col. 23 l. 30 | Attribute indicator selection: cluster anchors + per-cluster weighting | `numpy` |
| §528 | col. 23 ll. 31–47 | Score generation: per-sentence similarity (Euclidean, cosine, or density-based) | `sklearn.metrics.pairwise.cosine_similarity` |
| §530 | col. 23 ll. 48 – col. 24 l. 4 | Aggregation: threshold-gated soft-assignment, raised to power 2, weighted sum | `numpy` |
| §532 | col. 24 ll. 5–46 | Bias mitigation: input-side anonymization + semantic substitution, optional output-side correction | This library's `mitigator/` module |

§532 is provided in this library (`from mitigator import BiasMitigator`).
The other elements are the user's to implement.

## Interface contract

Your pipeline must expose:

```python
import numpy as np
from typing import List, Optional

def score_texts(
    texts: List[str],
    metadata: Optional[List[dict]] = None,
) -> np.ndarray:
    """Returns shape (len(texts),) float scores. Higher = more favorable.

    The audit harness performs its own top-K selection, so absolute scale
    does not matter — only relative ranking and distribution.
    """
    ...
```

If your pipeline implements §518–§530 and exposes `score_texts`, the
audit harness will run on it.

## Worked example shape

The structural shape of a minimal patent replication. Each element is a
straightforward call into the suggested library; the spec
(col. 22 line 1 – col. 24 line 46) walks through the data flow.

```python
# my_pipeline.py — your private workspace
import numpy as np
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
import hdbscan
import re


class PatentPipeline:
    def __init__(self, top_k=12, threshold=0.35, beta=8.0, power=2.0):
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.top_k = top_k
        self.threshold = threshold
        self.beta = beta
        self.power = power
        self._fit_done = False

    def _split_sentences(self, text: str) -> List[str]:
        # §518
        ...

    def _embed(self, sentences: List[str]) -> np.ndarray:
        # §520
        ...

    def _reduce(self, embeddings: np.ndarray) -> np.ndarray:
        # §522
        ...

    def _cluster(self, reduced: np.ndarray) -> np.ndarray:
        # §524
        ...

    def _select_indicators(self, labels, embeddings, sentences):
        # §526
        ...

    def _score(self, sent_embeddings, indicator_vectors):
        # §528
        ...

    def _aggregate(self, similarity_matrix, indicator_weights):
        # §530
        ...

    def fit_corpus(self, texts: List[str]):
        # Cluster fitting on the input corpus before per-text scoring
        ...

    def score_texts(self, texts: List[str], metadata=None) -> np.ndarray:
        if not self._fit_done:
            self.fit_corpus(texts)
            self._fit_done = True
        scores = np.zeros(len(texts))
        for i, text in enumerate(texts):
            ...
            scores[i] = aggregated_score
        return scores


_pipeline = PatentPipeline()
def score_texts(texts, metadata=None):
    return _pipeline.score_texts(texts, metadata)
```

This is a sketch, not a working implementation.
[`DEVIATIONS_FROM_PATENT.md`](DEVIATIONS_FROM_PATENT.md) documents one
set of reasonable parameter choices.

## Using the audit harness with your pipeline

```bash
python -m tools.run_audit_1 \
    --corpus your_corpus.jsonl \
    --pipeline my_pipeline:score_texts \
    --out-dir out/audit_1
```

`my_pipeline.py` must be on the Python import path. If it's in your
private workspace outside the library, set `PYTHONPATH`:

```bash
PYTHONPATH=/path/to/your/workspace python -m tools.run_audit_1 ...
```

## Estimated build time

| Phase | Time |
|---|---|
| Reading patent col. 22 line 1 – col. 24 line 46 | 1.5 hours |
| §518 sentence splitting and normalization | 30 min |
| §520 SBERT embedding | 15 min |
| §522 PCA reduction | 15 min |
| §524 HDBSCAN clustering | 30 min |
| §526 indicator selection from cluster centroids | 45 min |
| §528 cosine similarity scoring | 15 min |
| §530 soft-assignment + power-2 aggregation | 45 min |
| Wiring into the `score_texts` interface | 30 min |
| Testing on a small corpus | 1 hour |
| **Total** | **~6 hours** |

## Patent under-specifications

[`DEVIATIONS_FROM_PATENT.md`](DEVIATIONS_FROM_PATENT.md) documents
implementation-specific choices made in this library's components. A
custom pipeline will need to make analogous choices. The patent does not
pin down:

- HDBSCAN `min_cluster_size` / `min_samples`
- §526 cluster-ranking strategy (size, rarity, other)
- §526 indicator anchor type (centroid vs. exemplar)
- §528 / §530 threshold and soft-assignment temperature
- §532 semantic-substitution table

Document the choices made in your implementation alongside your audit
results.
