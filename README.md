# AEDT Fairness Audit Toolkit

Fairness measurement library for automated employment decision tools.

Implements:

- AIF360-style fairness metrics: disparate impact, statistical parity,
  threshold sweep, calibration, counterfactual flips, bootstrap CIs
- The bias mitigation operation specified by Claim 1 of U.S. Patent No.
  12,265,502 B1: input-side detection-and-replacement of biasing
  identifiers
- The four Personal Statement questions enumerated at column 10 of U.S.
  Patent No. 12,265,502 B1, with both an SBERT cosine-similarity extractor
  and an LLM question-answering extractor

The library does not include an AEDT pipeline implementation. Users supply
their own scoring function via the `pipeline_fn` interface. See
[`PIPELINE_BUILD_GUIDE.md`](PIPELINE_BUILD_GUIDE.md) for how to build a
pipeline replicating the architecture disclosed in U.S. Patent No.
12,265,502 B1 from off-the-shelf libraries.

## Components

| Module | Function |
|---|---|
| `audit/` | Fairness metrics, bootstrap CIs, per-axis screening |
| `mitigator/` | Bias Mitigator (Claim 1, input-side anonymization + semantic substitution) |
| `ps_extraction/` | Four PS-question extractor (SBERT and LLM variants) |
| `synthetic/` | Demographically stratified synthetic PS generator |
| `examples/` | Reference `pipeline_fn` (VADER baseline) |
| `tools/` | CLI runners for end-to-end audits |

Patent-element to module mapping is documented in
[`DEVIATIONS_FROM_PATENT.md`](DEVIATIONS_FROM_PATENT.md).

## Installation

```bash
cd aedt-fairness-audit
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# For SBERT extractor:
pip install sentence-transformers

# For mitigator (NER-based anonymization):
pip install spacy
python -m spacy download en_core_web_sm

# For LLM extractor:
pip install openai          # OpenAI / Dartmouth-compatible endpoints
pip install anthropic       # Anthropic
```

## Usage

### Generate a synthetic stratified corpus

```bash
OPENAI_API_KEY=sk-... python -m tools.generate_ps_corpus \
    --provider openai --model gpt-5-mini \
    --out synthetic/data/ps_corpus.jsonl
```

### Audit 1 — Bias Mitigator efficacy

Compares disparate impact before and after applying the Claim 1 bias
mitigator. Requires a `pipeline_fn` callable. See
[`PIPELINE_BUILD_GUIDE.md`](PIPELINE_BUILD_GUIDE.md) for the interface.

```bash
python -m tools.run_audit_1 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --pipeline my_pipeline:score_texts \
    --out-dir out/audit_1
```

### Audit 2 — PS four-question extraction

Computes per-question and aggregate disparate impact across demographic
strata. The PSExtractor is the audit target; no external pipeline
required.

```bash
# SBERT extractor (patent col. 22 line 31 enumerates SBERT)
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor sbert

# LLM extractor (patent col. 10 says "users can apply NLP")
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor llm \
    --llm-provider openai --llm-model gpt-5-mini
```

### Library use

```python
import pandas as pd, numpy as np
from audit.metrics import group_outcome_summary, disparity_summary
from mitigator import BiasMitigator
from ps_extraction import PSExtractor

# Fairness metrics on any binary-group prediction
metrics = group_outcome_summary(df, yhat, proba)
disparity = disparity_summary(metrics)

# Bias mitigator
mitigator = BiasMitigator()
mitigated_text = mitigator(text)

# PS extractor
extractor = PSExtractor()
scores = extractor.score_text(text)
# {"poverty": 0.42, "refugee": 0.08, "major_illness": 0.61, "academic_career": 0.34, "_total": ...}
```

## Inputs and outputs

The pipeline expects a pandas DataFrame with these columns:

- `applicant_id` (str)
- `mspe`, `lor`, `ps` (str) — narrative document fields; any may be empty
- structured features (numeric) — combined with narrative score by user-supplied `pipeline_fn`
- `prot_*` (str) — protected attribute columns; the stage audit runs
  fairness metrics across any column whose name begins with `prot_`

When `out_dir` is supplied, the audit harnesses write:

- `audit_1_results.json` / `audit_2_results_{sbert,llm}.json` — metrics
- `audit_*_per_applicant_scores.csv` — applicant-level scores

## Privacy defaults

The library produces no disk artifacts unless the user explicitly writes
them. Audit metrics return Python dicts; the caller decides whether and
where to persist results. The PSExtractor's `store_anchor_text` defaults
to `False`; cluster exemplars are not serialized to manifests.

## Smoke test

```bash
python -m tools.smoke_test
```

Runs a 16-document hand-curated corpus through the BiasMitigator,
PSExtractor, and per-axis fairness metrics. ~1 minute end to end.

## Citation

```
Markey, C. (2026). AEDT Fairness Audit Toolkit.
https://github.com/[username]/aedt-fairness-audit
```

A `CITATION.cff` file is provided for automatic citation generation.

## License

MIT. See [`LICENSE`](LICENSE).
