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
12,265,502 B1 from off-the-shelf libraries. This is no different than
going to the museum and sketching an image of a sculpture into a
notebook, or asking someone to put six different Lego blocks together.
This is publicly available information sanctioned by the Federal
government with stress tests modeled after fairness methods cited and
endorsed by the AAMC. Feel free to contribute and/or offer critiques and
feedback.

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

### Dilution test — multi-instrument narrative-tone audit

Scores user-supplied narrative variants under multiple sentiment
instruments (VADER, transformer, LLM judge), at excerpt level and at
full-document level via a skeleton template with a
`{VARIANT_PARAGRAPH}` placeholder.

```bash
python -m tools.run_dilution_test \
    --config examples/dilution_test_template.json \
    --out-dir out/dilution_test
```

The template format declares variants, instruments, the skeleton
document path, and the variant pairs to compute gaps for. The
included `examples/mspe_skeleton_template.txt` is a generic
MSPE-style skeleton with placeholders for student name, school, and
dates. Output: per-instrument per-variant compound scores, pairwise
gaps, and dilution ratios.

### Screening simulation — DI under sentiment-instrument anchorings

Generates n synthetic applicants under each user-supplied sentiment
anchoring, trains a screening model, ranks at top-K, and reports
disparate impact with bootstrap CIs. The user supplies sentiment
anchorings (one per sentiment instrument they tested) — actual narrative
text is not required.

```bash
python -m tools.run_screening_simulation \
    --anchorings examples/screening_anchorings_template.json \
    --out-dir out/screening_simulation \
    --n 6000 --invite-rate 0.30 --bootstrap-reps 1000
```

The template format expects one entry per sentiment instrument with
`{label, low_sentiment, high_sentiment}`. Output: per-anchoring DI
metrics with 95% bootstrap CIs, written to
`screening_simulation_results.json`.

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

## Methodology references

### AAMC alignment

The AAMC's published principles for the responsible use of AI in medical
education explicitly recommend the kind of audit this library supports
and name AI Fairness 360 (AIF360) by name as a recommended tool:

> "Audit AI systems regularly. Schedule and conduct an annual audit of
> the AI system and its output to identify AI-related biases and other
> problems in the selection process. Collaborate with a dedicated team
> of experts to analyze the findings and develop strategies for
> continuous improvement to be implemented for the next cycle. Consult
> recent and relevant journal articles and technical reports that have
> used AI in selection processes, explore tools used to examine the
> potential for bias like Admissible ML or **AI Fairness 360**, and
> consult legal counsel when appropriate."

Source: AAMC, *Principles for the Responsible Use of Artificial
Intelligence in and for Medical Education — Protect Against
Algorithmic Bias*,
[aamc.org/about-us/mission-areas/medical-education/principles-ai/protect-against-algorithmic-bias](https://www.aamc.org/about-us/mission-areas/medical-education/principles-ai/protect-against-algorithmic-bias).

The AAMC also recommends not changing the process mid-cycle and
tracking all changes when they occur. The toolkit's manifest output
(SHA-256 hashes of stage artifacts, full config dump, run timestamps)
is designed to make process-version tracking auditable.

### AI Fairness 360 (AIF360)

The fairness-metric definitions implemented in `audit/` follow the AI
Fairness 360 (AIF360) conventions. AIF360 itself is *not* a runtime
dependency — the metrics are reimplemented here in numpy/pandas to keep
installation light — but the mathematical definitions and naming follow
AIF360's `ClassificationMetric` class.

Specifically, this library replicates:

- `disparate_impact` — selection-rate ratio between protected groups (the
  EEOC four-fifths rule metric)
- `statistical_parity_difference` — selection-rate difference
- `equal_opportunity_difference` — true-positive-rate difference
- `false_positive_rate_difference` — false-positive-rate difference
- `accuracy` — overall classification accuracy

Source for the AIF360 definitions:
[github.com/Trusted-AI/AIF360/blob/master/aif360/metrics/classification_metric.py](https://github.com/Trusted-AI/AIF360/blob/master/aif360/metrics/classification_metric.py)

Citation: Bellamy, R. K. E., Dey, K., Hind, M., Hoffman, S. C., Houde, S.,
Kannan, K., et al. (2018). *AI Fairness 360: An Extensible Toolkit for
Detecting, Understanding, and Mitigating Unwanted Algorithmic Bias.*
arXiv:1810.01943. [github.com/Trusted-AI/AIF360](https://github.com/Trusted-AI/AIF360)

If you prefer to use AIF360 directly rather than the reimplementations
here, the metric definitions are bytewise compatible — substitute
`aif360.metrics.ClassificationMetric` calls in your own code where this
library uses its functions of the same names.

Other methodology references:

- VADER sentiment: Hutto, C. J. & Gilbert, E. (2014). *VADER: A
  Parsimonious Rule-based Model for Sentiment Analysis of Social Media
  Text.* ICWSM.
- Sentence-BERT: Reimers, N. & Gurevych, I. (2019). *Sentence-BERT:
  Sentence Embeddings using Siamese BERT-Networks.* EMNLP.
- HDBSCAN: Campello, R. J. G. B., Moulavi, D., & Sander, J. (2013).
  *Density-based clustering based on hierarchical density estimates.*
  PAKDD.

## Citation

```
Markey, C. (2026). AEDT Fairness Audit Toolkit.
https://github.com/[username]/aedt-fairness-audit
```

A `CITATION.cff` file is provided for automatic citation generation.

## License

MIT. See [`LICENSE`](LICENSE).
