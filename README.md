# AEDT Fairness Audit Toolkit

Fairness measurement library for automated employment decision tools.

## In plain language (the upshot)

This is software for measuring fairness in the AI tools that screen job
applications.

Some companies sell AI that reads documents — résumés, personal
statements, recommendation letters — and ranks candidates for human
reviewers. A 2025 U.S. patent (No. 12,265,502 B1) describes one such
system in detail, including how it scores the personal statement and
how it tries to remove bias.

This toolkit does two things:

- Implements the patent's bias-removal step and personal-statement
  scoring step in open code that anyone can read and run.
- Provides command-line audits that test whether those implementations
  treat demographic groups equally on synthetic test data.

The legal benchmark used throughout is the U.S. EEOC's **four-fifths
rule**: a selection process is presumed to discriminate when one
group is picked at less than 80% the rate of another (a selection-rate
ratio below 0.80, or above 1.25 in the reverse direction).

### What happens when you run it

These are example numbers from a single run on 192 synthetic personal
statements covering 24 demographic combinations. Specific values vary
across runs; the patterns are what to expect.

- The patent's personal-statement extractor produced selection-rate
  ratios of 0.51–0.66 across demographic groups on three of four
  questions — outside the four-fifths range.
- Running the patent's own bias-removal step, which deletes names,
  schools, and other demographic identifiers, did not close the gap.
  The ratios stayed within ±0.09 of their pre-removal values.
- A simulated 6,000-applicant screen using sentiment scores from real
  text produced selection-rate ratios between 0.00 and 0.45 across
  four sentiment instruments — all outside the four-fifths range.
  When narrative sentiment alone was held constant across groups, the
  ratios returned to approximately 1.0.

The technical results, with confidence intervals and methodology, are
in [`RESULTS.md`](RESULTS.md). The audit code is in `tools/`. The
plotting code is in `plots/`. Everything is reproducible from the
command line.

---

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
feedback. With really any coding agent, particularly Anthropic Opus 4.7
or OpenAI GPT-5.5, you could likely drop this repo's .zip into a project
workspace, and while staying in the loop, build out the pipeline in one
afternoon. I built this out initially with Opus 4.5, and recently tested
handoff to Codex GPT-5.5. Codex rebuilt the four-stage pipeline in one
session without me having to correct the embedding or clustering steps.

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

## Tools

Each tool below has a one-paragraph plain-language description of what
it does, followed by the command line for running it. All tools write
JSON to disk; companion plot scripts in `plots/` render figures from the
JSON output.

### Generate a synthetic corpus — `tools/generate_ps_corpus.py`

**What it does:** Generates a set of fake personal statements that span
different demographic combinations (race, gender, school tier) while
keeping the underlying narrative theme consistent within each group of
applicants. Used as test input for the audits below — actual applicant
text is never needed.

```bash
OPENAI_API_KEY=sk-... python -m tools.generate_ps_corpus \
    --provider openai --model gpt-5-mini \
    --out synthetic/data/ps_corpus.jsonl
```

### Audit 1 — Bias Mitigator efficacy — `tools/run_audit_1.py`

**What it does:** Tests whether the patent's bias-removal step actually
removes bias. Runs the same scoring pipeline twice — once on raw
applicant text, once after applying the patent's input-side
detect-and-replace step — and compares whether the demographic gaps
shrink. Requires a user-supplied scoring function via the `pipeline_fn`
interface; see [`PIPELINE_BUILD_GUIDE.md`](PIPELINE_BUILD_GUIDE.md).

```bash
python -m tools.run_audit_1 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --pipeline my_pipeline:score_texts \
    --out-dir out/audit_1 --bootstrap-reps 1000
```

### Audit 2 — PS four-question extraction — `tools/run_audit_2.py`

**What it does:** Tests the patent's personal-statement scoring
component. The patent specifies four yes/no questions the system asks
of each applicant's personal statement (poverty, refugee status, major
illness, academic career interest). This audit measures whether the
answers come out systematically different for different demographic
groups. Runs in either an SBERT (embedding-similarity) or LLM
(question-answering) variant.

```bash
# SBERT extractor
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor sbert --bootstrap-reps 1000

# LLM extractor
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor llm \
    --llm-provider openai --llm-model gpt-5-mini --bootstrap-reps 1000
```

### Paragraph audit — `tools/run_paragraph_audit.py`

**What it does:** Scores a document one section at a time under
multiple sentiment tools (VADER, RoBERTa, LLM judge), and flags any
section that is the lowest-scoring section under every tool. This is
the signal a "section-aware" AI screener would pick up if a single
section of an otherwise-positive document carries a lower tone — for
example, a paragraph describing a leave of absence in an otherwise
laudatory recommendation letter.

```bash
python -m tools.run_paragraph_audit \
    --document /path/to/document.txt \
    --instruments vader transformer llm \
    --llm-provider openai --llm-model gpt-5-mini \
    --out out/paragraph_audit/scores.json
```

### Dilution test — `tools/run_dilution_test.py`

**What it does:** Compares two narrative variants — a low-tone version
and a high-tone version of the same content — when scored as standalone
excerpts vs when embedded in a longer surrounding document. Tests
whether the score difference disappears when the variant is buried in
context. The dilution percentage depends on which sentiment tool is
used; lexicon and transformer tools tend to fully dilute, while LLM
judges retain more of the gap.

```bash
python -m tools.run_dilution_test \
    --config examples/dilution_test_template.json \
    --out-dir out/dilution_test
```

The included `examples/mspe_skeleton_template.txt` is a generic
medical-school document skeleton with placeholders for student name,
school, and dates.

### Screening simulation — `tools/run_screening_simulation.py`

**What it does:** Simulates a residency-style screening process with
thousands of synthetic applicants. The user supplies sentiment scores
(the score the audited document gets under different tools) as
"anchorings"; the simulation generates applicants where the
disadvantaged group's narratives carry the low score and the favored
group's carry the high score, trains a screening model on the
combined applicant pool, and reports how often each group gets
selected.

```bash
python -m tools.run_screening_simulation \
    --anchorings examples/screening_anchorings_template.json \
    --out-dir out/screening_simulation \
    --n 6000 --invite-rate 0.12 --bootstrap-reps 100
```

### Screening with counterfactual — `tools/run_screening_with_counterfactual.py`

**What it does:** Runs the simulation above, then runs an "intervention"
version: what if the disadvantaged group's narratives suddenly carried
the high-tone scores instead? The intervention re-scores the same
applicants under the same trained model with only the narrative-tone
feature changed. Comparing the two reports how much of the disparity is
driven by narrative tone alone. Supports multiple screening models
including the patent's specified power-of-2 aggregation
(`quadratic_aggregation`) from §530.

```bash
python -m tools.run_screening_with_counterfactual \
    --anchorings examples/screening_anchorings_template.json \
    --n 6000 --invite-rate 0.12 --narrative-sd 0.10 \
    --bootstrap-reps 50 \
    --models logistic_regression linear_score quadratic_aggregation cubic_aggregation \
    --out out/screening_counterfactual/results.json
```

### Disclosure-rate sweep — `tools/run_disclosure_sweep.py`

**What it does:** Tests how much an AI vendor's "protected-class
control" (a feature that suppresses sentiment scoring when ADA/504
disclosure language is detected in the document) actually helps. The
control only triggers when the applicant's text contains the
disclosure language. The sweep varies what percentage of disadvantaged-
group applicants disclose, and reports the resulting disparity at each
rate.

```bash
python -m tools.run_disclosure_sweep \
    --anchoring "vader_excerpt:0.18:0.78" \
    --rates 0 0.05 0.10 0.25 0.50 0.75 0.90 1.00 \
    --n 6000 --invite-rate 0.12 --bootstrap-reps 100 \
    --out out/disclosure_sweep/results.json
```

### Content-equivalence validation — `tools/content_equivalence.py`

**What it does:** Validates the synthetic corpus. Measures whether two
synthetic applications from different demographic groups but the same
narrative theme are more similar to each other than two applications
from different themes. If the within-theme distance is meaningfully
smaller than the across-theme distance, the corpus held content
constant across demographic groups; if not, the audits' premise is
suspect.

```bash
python -m tools.content_equivalence \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out out/content_equivalence/results.json
```

### Counterfactual decomposition — `tools/counterfactual_decomposition.py`

**What it does:** When the audits show demographic disparity, this
diagnostic asks: is the disparity driven by demographic markers
(names, schools, identity phrases) or by deeper content patterns?
Removes the markers using the patent's bias-removal step, re-scores
the marker-stripped applications with the same scoring tool, and
compares the results.

```bash
python -m tools.counterfactual_decomposition \
    --corpus synthetic/data/ps_corpus.jsonl \
    --original-scores out/audit_2/audit_2_per_applicant_scores_llm.csv \
    --out-dir out/counterfactual \
    --llm-provider openai --llm-model gpt-5-mini
```

### Re-bootstrap — `tools/rebootstrap.py`

**What it does:** Re-runs the statistical confidence-interval
calculation from a prior audit's per-applicant scores at a higher
bootstrap-replicate count, without re-running the expensive scoring
step. Used to tighten error bars to publication-grade levels.

```bash
python -m tools.rebootstrap \
    --scores out/audit_2/audit_2_per_applicant_scores_llm.csv \
    --score-cols poverty refugee major_illness academic_career _total \
    --top-frac 0.3 --bootstrap-reps 1000 \
    --out out/audit_2/audit_2_results_llm_reps1000.json
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
