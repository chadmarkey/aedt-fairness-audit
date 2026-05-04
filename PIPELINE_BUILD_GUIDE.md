# Pipeline Notes

This library does not ship an AEDT pipeline implementation. Pipelines
live in users' own workspaces.

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

## Building a pipeline

The library expects a callable that scores a list of texts:

```python
import numpy as np
from typing import List, Optional

def score_texts(
    texts: List[str],
    metadata: Optional[List[dict]] = None,
) -> np.ndarray:
    """Returns shape (len(texts),) float scores. Higher = more favorable."""
    ...
```

If your pipeline exposes `score_texts` as a module-level function, the
audit harness will run on it via the `module:function` spec:

```bash
python -m tools.run_audit_1 \
    --corpus your_corpus.jsonl \
    --pipeline my_pipeline:score_texts \
    --out-dir out/audit_1
```

## Resources for replication

The architecture disclosed in
[U.S. Patent No. 12,265,502 B1](https://patents.google.com/patent/US12265502B1)
is built from off-the-shelf parts: `sentence-transformers`,
`scikit-learn`, `hdbscan`, `numpy`. AIF360 metrics are at
[github.com/Trusted-AI/AIF360](https://github.com/Trusted-AI/AIF360).

A modern coding agent (Claude Code, Codex, or equivalent) with access
to the patent PDF and these libraries will assemble a working pipeline
in an afternoon. No pipeline source code here; just the public resources.
