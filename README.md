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
across runs; the patterns below are what to expect.

- The patent's personal-statement extractor produced selection-rate
  ratios in the range 0.50–0.59 across demographic groups on three of
  four questions — outside the four-fifths range.
- **Running the patent's own bias-removal step did not close the gap.**
  After deleting names, schools, and other demographic identifiers,
  the ratios stayed within ±0.09 of their pre-removal values. The
  patent's specified mitigation does not, on this synthetic test set,
  reach the within-content signal the LLM extractor was reading.
- The screening-simulation tool, run on illustrative sentiment
  anchorings, produced selection-rate ratios outside the four-fifths
  range under every scoring method tested (linear, logistic
  regression, patent §530 power-of-2 aggregation, power-of-3
  aggregation). When narrative sentiment alone was held constant
  across groups in a sentiment-only counterfactual, the ratios
  returned to within sampling noise of parity.

The technical results, with confidence intervals and methodology, are
in [`RESULTS.md`](RESULTS.md). The audit code is in `tools/`. The
plotting code is in `plots/`. Everything is reproducible from the
command line.

## Scope and claims

This repository is a measurement and stress-test framework, not a
reverse-engineered production system or an authoritative finding about
any specific deployed AEDT.

- The audits run on synthetic data, not real applicant text. Results
  are illustrative and sensitivity-based, not population-level claims
  about real-world hiring or screening outcomes.
- The toolkit does not include an AEDT pipeline implementation. Users
  supply their own scoring function via the `pipeline_fn` interface.
  Different reasonable implementations of the patent's architecture
  will produce different absolute selection-rate ratios.
- Findings demonstrate that adverse-impact signals can emerge under
  plausible configurations of the patent's specified architecture on
  synthetic test data. They do not, and cannot, prove that any
  specific deployed AEDT — including any product made by the patent's
  assignee — implements the architecture in the same way the toolkit
  does, uses the same parameters, or produces the same outputs.
- The U.S. EEOC's four-fifths rule (29 C.F.R. § 1607) is a
  regulatory screening heuristic for *adverse impact*, used by
  agencies and compliance teams to flag selection processes that
  warrant further review. It is not, on its own, a determination of
  unlawful discrimination; that determination requires additional
  evidence, regulatory process, and adjudication outside the scope of
  this toolkit.

For a fuller account of methodological boundaries, see
[Limitations](#limitations) at the end of this file.

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

The library does not include an AEDT pipeline implementation. Users
supply their own scoring function via the `pipeline_fn` interface. See
[`PIPELINE_BUILD_GUIDE.md`](PIPELINE_BUILD_GUIDE.md) for how to build a
pipeline replicating the architecture disclosed in U.S. Patent No.
12,265,502 B1 from off-the-shelf libraries.

Contributions and critiques are welcome via Issues and pull requests.

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
pip install openai          # OpenAI or any OpenAI-compatible endpoint
pip install anthropic       # Anthropic
```

## Quickstart — reproduce the reference outputs

A committed reference output set lives in
[`examples/reference_outputs/`](examples/reference_outputs/). It
contains one representative run of every CLI tool, in JSON plus
rendered PNG/PDF figures. Use it as a known-good baseline to diff your
own runs against.

The full synthetic-corpus audit set reproduces in five commands. With
gpt-5-mini for synthetic-PS generation and LLM-based PS extraction,
the cost is roughly $1–$2 in API credits.

```bash
# 1. Generate the 192-PS stratified synthetic corpus
OPENAI_API_KEY=sk-... python -m tools.generate_ps_corpus \
    --provider openai --model gpt-5-mini \
    --out synthetic/data/ps_corpus.jsonl

# 2. Audit 1 — Bias Mitigator efficacy on a VADER baseline pipeline
python -m tools.run_audit_1 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --pipeline examples.example_pipeline:score_texts \
    --out-dir out/audit_1 --bootstrap-reps 1000

# 3. Audit 2 — PS four-question extraction (SBERT + LLM variants)
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor sbert --bootstrap-reps 1000

python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor llm \
    --llm-provider openai --llm-model gpt-5-mini --bootstrap-reps 1000

# 4. Content-equivalence validation
python -m tools.content_equivalence \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out out/content_equivalence/results.json

# 5. Counterfactual decomposition (marker-stripping diagnostic)
python -m tools.counterfactual_decomposition \
    --corpus synthetic/data/ps_corpus.jsonl \
    --original-scores out/audit_2/audit_2_per_applicant_scores_llm.csv \
    --out-dir out/counterfactual \
    --llm-provider openai --llm-model gpt-5-mini

# 6. Render figures
python -m plots.plot_audit_1 \
    --input out/audit_1/audit_1_results.json --out-dir out/audit_1
python -m plots.plot_audit_2 \
    --input out/audit_2/audit_2_results_sbert.json --out-dir out/audit_2 \
    --name audit_2_sbert_di_heatmap --title-suffix " (SBERT)"
python -m plots.plot_audit_2 \
    --input out/audit_2/audit_2_results_llm.json --out-dir out/audit_2 \
    --name audit_2_llm_di_heatmap --title-suffix " (LLM, gpt-5-mini)"
python -m plots.plot_content_equivalence \
    --input out/content_equivalence/results.json --out-dir out/content_equivalence
python -m plots.plot_counterfactual_decomposition \
    --input out/counterfactual/counterfactual_decomposition.json \
    --out-dir out/counterfactual
```

Compare your `out/` figures against
`examples/reference_outputs/` for sanity. Specific numerical values
will not match exactly — synthetic-PS generation is stochastic, model
outputs vary across API calls, and bootstrap seeds drift — but the
qualitative patterns (which axes raise an adverse-impact flag, which
direction the mitigator moves the ratios, the ordering of the
content-equivalence nesting levels) should reproduce. If they do not,
that is itself an audit-worthy finding.

The screening-simulation, dilution, disclosure-sweep, and
paragraph-audit tools are documented under [Tools](#tools) below;
their reference outputs are in `examples/reference_outputs/`
alongside the synthetic-corpus runs above.

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

## Limitations

This toolkit is a measurement instrument, not an authoritative finding
about any specific deployed AEDT. Several caveats apply to how its
outputs should be read.

**Synthetic corpus, not real applicant data.** The audits run on
LLM-generated personal statements stratified across demographic
combinations. The corpus is designed so within-seed content is held
approximately constant across demographic strata; this is validated by
pairwise SBERT distance (within-seed-across-stratum mean cosine 0.253
vs. across-seed mean 0.411, ratio 0.615). The separation is meaningful
but not overwhelming. The generator may leak content along with
demographic markers in ways the cosine check does not catch. Findings
should be read as "this is what happens when the patent's architecture
is run on a corpus designed to isolate demographic markers from
content," not as a population-level claim about real applicant text.

**Bootstrap CIs behave poorly on discrete top-K selection.** With
group sizes near 96 and binary top-K decisions, the disparate-impact
ratio is a discrete-valued statistic. Percentile bootstrap intervals
can sit above the point estimate or fail to bracket it cleanly. The
point DI is the substantive fairness measurement; the CI characterizes
resampling stability rather than providing standard inferential
coverage. Users running this on their own corpora should consider BCa
intervals, permutation tests against the null of group exchangeability,
or larger group sizes.

**No ground truth for the four PS questions.** Audit 2 measures
whether the patent's four-question extractor produces systematically
different yes-rates across demographic groups. It does not measure
whether those answers are *correct*; the synthetic corpus does not
carry verified ground-truth labels for poverty / refugee / illness /
academic-career status independent of what the generator was prompted
to encode. Group-rate disparities are the measurand; calibration
against truth is not.

**The pipeline implementation is the user's, not the toolkit's.** The
library does not ship an AEDT pipeline. Audit 1 requires the user to
supply their own `pipeline_fn`. Different reasonable implementations of
the patent's architecture will produce different absolute DI values.
The toolkit's role is to provide a consistent measurement framework,
not to certify that any one implementation is the patent's "true"
implementation.

**Default extractor parameters are implementer's choices.** The SBERT
extractor's threshold (0.35), softmax temperature (8.0), aggregate
power (2.0), and exemplar inventory are documented in
[`DEVIATIONS_FROM_PATENT.md`](DEVIATIONS_FROM_PATENT.md) as
implementation choices the patent does not specify. Changing these can
shift per-question DI values. Robust findings should reproduce across
reasonable parameter ranges; users running audits should report the
parameters used.

**Two extractor variants are not exhaustive.** The SBERT and LLM
extractors represent two reasonable instantiations of "users can apply
NLP to read through personal statement of each applicant" (col. 10).
Other architectures consistent with the patent — hybrid
retrieval-augmented systems, fine-tuned classifiers, ensemble
approaches — are not tested. Findings that hold across SBERT and LLM
extractors are more robust than findings that appear in only one.

**The bias mitigator's failure to close gaps is a result, not a bug.**
Audit 1 and the counterfactual decomposition both find that input-side
anonymization (Claim 1's specified operation) does not substantially
reduce demographic disparity in the conditions tested. This is the
toolkit reporting what the patent's specified mitigation does on the
synthetic corpus; it is not a proof that no mitigation could close the
gap. Output-side recalibration (col. 24, lines 19–46) is in the patent
spec but discretionary under Claim 1, with no algorithm specified, and
is not implemented here. Users designing their own mitigations may
find approaches that perform differently.

**Findings are about an architecture class, not a specific product.**
This toolkit tests the architecture disclosed in U.S. Patent No.
12,265,502 B1 as implemented from public components. It does not, and
cannot, claim that any specific deployed AEDT — including any product
made by the patent's assignee — implements the architecture in the
same way the toolkit does, uses the same parameters, or produces the
same outputs. Inference from toolkit results to specific deployed
products requires independent evidence about those products.

**Demographic axes are limited to those the synthetic generator
stratifies.** The shipped corpus stratifies on race (4 categories),
gender (binary), and school tier (3 levels). Disability status, age,
sexual orientation, geographic origin, language background, and
intersectional combinations beyond the three axes are not separately
tested. Users investigating those axes should extend the generator and
re-run.

## Citation

```
Markey, C. (2026). AEDT Fairness Audit Toolkit.
https://github.com/[username]/aedt-fairness-audit
```

A `CITATION.cff` file is provided for automatic citation generation.

## License

MIT. See [`LICENSE`](LICENSE).
