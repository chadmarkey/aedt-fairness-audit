# AEDT Fairness Audit Toolkit

Fairness measurement library for automated employment decision tools.

## In plain language (the upshot)

This is software for measuring fairness in the AI tools that screen job
applications.

Some companies sell AI that reads documents (résumés, personal
statements, recommendation letters) and ranks candidates for human
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

These are example numbers from a 384-PS synthetic corpus covering 24
demographic combinations, scored with two LLM families (gpt-4o-mini
and claude-haiku-4-5). Specific values vary across runs.

The honest read of the audit findings:

- **No per-cell finding survives multiple-comparisons correction.**
  Audit 2 reports 30 hypothesis tests across the two scorers (15
  per scorer). Under Bonferroni or Benjamini–Hochberg correction at
  family-wise α = 0.05, the corrected per-cell threshold is ≈ 0.0017.
  The smallest observed p-value is 0.052. No cell clears.
- **A borderline school_tier signal is shared across both LLM
  families.** Under both gpt-4o-mini and claude-haiku-4-5,
  academic_career × school_tier produces a selection-rate ratio of
  about 0.65–0.67 at uncorrected p ≈ 0.06. Top-20 school applicants
  are selected at a higher rate than lower-resource school applicants
  on this question. This is the only cell where both LLMs agree at
  borderline significance. It does not survive multiple-comparisons
  correction.
- **The patent's specified Claim-1 mitigation barely moves the
  school_tier signal.** After applying the patent's input-side
  anonymization, the academic_career × school_tier ratio shifts from
  0.650 to 0.673 — essentially unchanged. The aggregate `_total` ×
  school_tier ratio shifts from 0.673 toward parity at 0.807; mixed
  picture.
- **The school_tier signal may reflect generator-induced content
  correlation rather than scoring bias.** The synthetic corpus was
  generated with gpt-4o-mini. If that generator wrote top-20 PSs with
  more academic-leaning narrative content than lower-tier PSs, both
  LLM scorers would consistently read "more academic" out of the
  top-20 PSs, and the audit would record a school_tier signal that
  has nothing to do with how a real AEDT scores real applicants.
  Disentangling generator confound from real scoring bias would
  require a generator-bias analysis the toolkit does not currently
  ship.

A discrete-statistic / tie-breaking pitfall was discovered and fixed
during a 2026-05-06 validation pass. Earlier versions of the audit
used numpy's stable sort for top-K selection, which preserves
original row order at ties. With near-discrete LLM scores, this
introduced a corpus-row-order bias that produced spurious per-cell DI
findings on the race axis under gpt-4o-mini scoring. Those findings
were artifacts. The current `top_k_selection` uses seeded random
tie-breaking to eliminate the bias. See [`CHANGELOG.md`](CHANGELOG.md)
for the discovery and fix; the methodology section of `RESULTS.md`
documents the issue for any future AEDT auditor working with
near-discrete LLM outputs.

The screening-simulation tool, run on illustrative sentiment
anchorings, produced selection-rate ratios outside the four-fifths
range under every scoring method tested (linear, logistic regression,
patent §530 power-of-2 aggregation, power-of-3 aggregation). When
narrative sentiment alone was held constant across groups in a
sentiment-only counterfactual, the ratios returned to within sampling
noise of parity.

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
  specific deployed AEDT (including any product made by the patent's
  assignee) implements the architecture in the same way the toolkit
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
A running record of substantive methodology revisions made after the
initial public release lives in [`CHANGELOG.md`](CHANGELOG.md),
including a 2026-05-05 cross-family robustness check that narrowed
the audit's substantive claim and is described in full in
[`RESULTS.md`](RESULTS.md).

## Why this is public

This repo is public because there was no other way to do it. I asked
Thalamus, the patent's assignee, for the data and processing details
on their pipeline. The vehicle was a Data Subject Access Request under
New Hampshire's Privacy Act, RSA 507-H. They declined at the 45-day
deadline. The grounds were jurisdictional. RSA 507-H sets volume
thresholds for which companies the law reaches, and the company argued
that too few of New Hampshire's 1.4 million residents use their
products to clear those thresholds. So the privacy law that should
have governed the request did not apply. I appealed under §507-H:4(IV)
on May 4, 2026. That appeal is its own record now.

What was left was to rebuild the patent's pipeline from public
components and audit it. Patent text, off-the-shelf libraries,
synthetic test data. That is the toolkit.

Critiques and replication failures are welcome. File them as GitHub
Issues. The repo has already narrowed its substantive claims in
response to one external critique (see [`CHANGELOG.md`](CHANGELOG.md)).
I expect more of that. The work gets better when the methodology
iterates in public.

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
gpt-4o-mini for synthetic-PS generation and LLM-based PS extraction
(the canonical configuration RESULTS.md reports), the cost is roughly
$1–$3 in API credits depending on extractor cache state.

```bash
# 1. Generate the 384-PS stratified synthetic corpus
OPENAI_API_KEY=sk-... python -m tools.generate_ps_corpus \
    --provider openai --model gpt-4o-mini --instances-per-cell 4 \
    --out synthetic/data/ps_corpus.jsonl

# 2. Audit 1: Bias Mitigator effect on a VADER baseline pipeline
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
    --llm-provider openai --llm-model gpt-4o-mini --bootstrap-reps 1000

# 3b. Permutation tests for the inferential p-values
#     (the audit-2 runs above produce point estimates and bootstrap CIs;
#     this step adds the permutation p-values reported in RESULTS.md)
python -m tools.rebootstrap \
    --scores out/audit_2/audit_2_per_applicant_scores_sbert.csv \
    --score-cols poverty refugee major_illness academic_career _total \
    --top-frac 0.3 --bootstrap-reps 1000 --n-permutations 10000 \
    --out out/audit_2/audit_2_results_sbert_perm.json
python -m tools.rebootstrap \
    --scores out/audit_2/audit_2_per_applicant_scores_llm.csv \
    --score-cols poverty refugee major_illness academic_career _total \
    --top-frac 0.3 --bootstrap-reps 1000 --n-permutations 10000 \
    --out out/audit_2/audit_2_results_llm_perm.json

# 4. Content-equivalence validation
python -m tools.content_equivalence \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out out/content_equivalence/results.json

# 5. Counterfactual decomposition (marker-stripping diagnostic).
#    --n-permutations adds the paired-permutation p-value per
#    (question × axis) cell that RESULTS.md reports.
python -m tools.counterfactual_decomposition \
    --corpus synthetic/data/ps_corpus.jsonl \
    --original-scores out/audit_2/audit_2_per_applicant_scores_llm.csv \
    --out-dir out/counterfactual \
    --llm-provider openai --llm-model gpt-4o-mini \
    --n-permutations 10000

# 6. Render figures
python -m plots.plot_audit_1 \
    --input out/audit_1/audit_1_results.json --out-dir out/audit_1
python -m plots.plot_audit_2 \
    --input out/audit_2/audit_2_results_sbert.json --out-dir out/audit_2 \
    --name audit_2_sbert_di_heatmap --title-suffix " (SBERT)"
python -m plots.plot_audit_2 \
    --input out/audit_2/audit_2_results_llm.json --out-dir out/audit_2 \
    --name audit_2_llm_di_heatmap --title-suffix " (LLM, gpt-4o-mini)"
python -m plots.plot_content_equivalence \
    --input out/content_equivalence/results.json --out-dir out/content_equivalence
python -m plots.plot_counterfactual_decomposition \
    --input out/counterfactual/counterfactual_decomposition.json \
    --out-dir out/counterfactual
```

Compare your `out/` figures against
`examples/reference_outputs/` for sanity. Specific numerical values
will not match exactly. Synthetic-PS generation is stochastic, model
outputs vary across API calls, and bootstrap seeds drift. But the
qualitative patterns (which axes raise an adverse-impact flag, which
direction the mitigator moves the ratios, the ordering of the
content-equivalence nesting levels) should reproduce. If they do not,
that is itself an audit-worthy finding.

### Cross-family and cross-generator robustness checks

The headline school_tier × academic_career signal in RESULTS.md rests
on a 2 × 2 (generator × scorer) robustness check, not on a single run.
To reproduce the four cells:

```bash
# Cross-family scoring (vary scorer, hold generator at gpt-4o-mini)
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2_crossfam --extractor llm \
    --llm-provider anthropic --llm-model claude-haiku-4-5 \
    --bootstrap-reps 1000

python -m tools.rebootstrap \
    --scores out/audit_2_crossfam/audit_2_per_applicant_scores_llm.csv \
    --score-cols poverty refugee major_illness academic_career _total \
    --top-frac 0.3 --bootstrap-reps 1000 --n-permutations 10000 \
    --out out/audit_2_crossfam/audit_2_results_llm_perm.json

# Cross-generator (regenerate with claude-haiku-4-5, score with both)
ANTHROPIC_API_KEY=... python -m tools.generate_ps_corpus \
    --provider anthropic --model claude-haiku-4-5 \
    --instances-per-cell 4 \
    --out synthetic/data/ps_corpus_haiku_gen.jsonl

# (Then run Audit 2 LLM with each scorer against the haiku-generated
#  corpus, and rebootstrap, exactly as in the standard reproduction
#  block above. Reference outputs at examples/reference_outputs/
#  audit_2_crossgen/.)
```

A content-neutral prompt variant (`--prompt-variant content_neutral`
on `tools.generate_ps_corpus`) generates a corpus under a prompt that
strips school-tier-correlated voice and content cues from the
generator's instruction. Comparing audits run against the standard
corpus vs. a content-neutral corpus tests whether the school_tier
signal is a corpus-prompt design effect or robust to prompt design.

### Screener-model simulation

The screener-model tools do not require the synthetic-PS corpus. They
take a JSON of sentiment-instrument anchorings (one entry per
sentiment instrument, naming the score it produces on a low-tone vs. a
high-tone variant of the same content) and use those anchorings to
generate stratified synthetic applicants for a top-K invite
simulation. The example anchorings live in
[`examples/screening_anchorings_template.json`](examples/screening_anchorings_template.json);
replace with your own sentiment scores when running on your own
document.

```bash
# 1. Multi-instrument × multi-scoring-method screen + sentiment-only
#    counterfactual. Reports baseline DI and counterfactual DI under
#    linear, logistic-regression, patent §530 power-of-2 (quadratic),
#    and power-of-3 (cubic) scoring rules across all anchorings.
python -m tools.run_screening_with_counterfactual \
    --anchorings examples/screening_anchorings_template.json \
    --n 6000 --invite-rate 0.12 --narrative-sd 0.10 \
    --bootstrap-reps 50 \
    --models logistic_regression linear_score quadratic_aggregation cubic_aggregation \
    --out out/screening_counterfactual/results_multimodel.json

# 2. Disclosure-rate sweep — DI as a function of the rate at which
#    disadvantaged-group applicants disclose protected-class language
#    a vendor's control would trigger on
python -m tools.run_disclosure_sweep \
    --anchoring "lexicon:0.18:0.78" \
    --rates 0 0.05 0.10 0.25 0.50 0.75 0.90 1.00 \
    --n 6000 --invite-rate 0.12 --bootstrap-reps 100 \
    --out out/disclosure_sweep/results.json

# 3. Dilution test — excerpt vs full-document gap per instrument
python -m tools.run_dilution_test \
    --config examples/dilution_test_template.json \
    --out-dir out/dilution_test

# 4. Paragraph audit — section-aware multi-instrument scoring of a
#    single user-supplied document
python -m tools.run_paragraph_audit \
    --document /path/to/document.txt \
    --instruments vader transformer \
    --out out/paragraph_audit/scores.json

# 5. Render figures
python -m plots.plot_screening_counterfactual \
    --input out/screening_counterfactual/results_multimodel.json \
    --out-dir out/screening_counterfactual --name screening_counterfactual_multimodel
python -m plots.plot_disclosure_sweep \
    --input out/disclosure_sweep/results.json --out-dir out/disclosure_sweep
python -m plots.plot_dilution_test \
    --input out/dilution_test/dilution_test_results.json --out-dir out/dilution_test
python -m plots.plot_paragraph_audit \
    --input out/paragraph_audit/scores.json --out-dir out/paragraph_audit
```

Reference output set lives at
`examples/reference_outputs/{screening_counterfactual, disclosure_sweep, dilution_test, paragraph_audit}/`.

## Tools

Each tool below has a one-paragraph plain-language description of what
it does, followed by the command line for running it. All tools write
JSON to disk; companion plot scripts in `plots/` render figures from the
JSON output.

### Generate a synthetic corpus — `tools/generate_ps_corpus.py`

**What it does:** Generates a set of fake personal statements that span
different demographic combinations (race, gender, school tier) while
keeping the underlying narrative theme consistent within each group of
applicants. Used as test input for the audits below. Actual applicant
text is never needed.

```bash
OPENAI_API_KEY=sk-... python -m tools.generate_ps_corpus \
    --provider openai --model gpt-4o-mini \
    --out synthetic/data/ps_corpus.jsonl
```

### Audit 1 — Bias Mitigator effect on a user-supplied pipeline_fn — `tools/run_audit_1.py`

**What it does:** Runs a user-supplied `pipeline_fn` twice. Once on raw
applicant text. Once after applying the patent's input-side
detect-and-replace bias mitigator. Compares whether the demographic gaps
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
    --llm-provider openai --llm-model gpt-4o-mini --bootstrap-reps 1000
```

### Paragraph audit — `tools/run_paragraph_audit.py`

**What it does:** Scores a document one section at a time under
multiple sentiment tools (VADER, RoBERTa, LLM judge), and flags any
section that is the lowest-scoring section under every tool. This is
the signal a "section-aware" AI screener would pick up if a single
section of an otherwise-positive document carries a lower tone, for
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

**What it does:** Compares two narrative variants (a low-tone version
and a high-tone version of the same content) when scored as standalone
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
    --llm-provider openai --llm-model gpt-4o-mini \
    --n-permutations 10000
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
dependency. The metrics are reimplemented here in numpy/pandas to keep
installation light. The mathematical definitions and naming follow
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
here, the metric definitions are bytewise compatible. Substitute
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

**Bootstrap CIs behave poorly on discrete top-K selection; permutation
tests are reported as the inferential complement.** Even at moderate
group sizes (~192 per group at n = 384), binary top-K selection
produces a discrete-valued disparate-impact statistic, and percentile
bootstrap intervals can sit above the point estimate or fail to
bracket it cleanly. The audit runners support a two-sided permutation
test under the null of group-selection independence (`--n-permutations`
flag on `tools/rebootstrap.py`); RESULTS.md reports those p-values
alongside the bootstrap CIs at 10,000 permutations. After the
tie-break fix on 2026-05-06 (see CHANGELOG), at n = 384 no race-axis
or gender-axis cell reaches conventional significance under any single
LLM scorer; one school_tier-axis cell (academic_career × school_tier)
sits at borderline uncorrected significance (p ≈ 0.06–0.07) and is
direction-consistent across both LLM scorer families and both LLM
generator families in a 2×2 cross-family check. It does not survive
multiple-comparisons correction. Users running on smaller corpora
should expect the percentile bootstrap to be a stability indicator
rather than a significance test.

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
Other architectures consistent with the patent (hybrid
retrieval-augmented systems, fine-tuned classifiers, ensemble
approaches) are not tested. Findings that hold across SBERT and LLM
extractors are more robust than findings that appear in only one.

**The bias mitigator's effect on the surviving school_tier signal is
mixed.** Audit 1 (VADER + Claim 1 mitigator) shows no systematic
mitigator effect on a sentiment-only pipeline (paired-permutation
p > 0.5 on all three demographic axes), which is the expected result
when the pipeline is largely insensitive to the markers the mitigator
strips. The counterfactual decomposition (LLM extractor scored on
marker-stripped PSs) shows that the academic_career × school_tier
signal is statistically unmoved by marker-stripping (paired-permutation
p = 0.65), while the `_total` × school_tier aggregate signal does move
toward parity (p = 0.015). The single-question signal is content-driven
in a sense the patent's specified anonymization step cannot reach; the
aggregate dilutes when school markers are removed but the underlying
academic-narrative variation remains. Output-side recalibration
(col. 24, lines 19–46) is in the patent spec but discretionary under
Claim 1, with no algorithm specified, and is not implemented here.
Users designing their own mitigations may find approaches that perform
differently.

**Findings are about an architecture class, not a specific product.**
This toolkit tests the architecture disclosed in U.S. Patent No.
12,265,502 B1 as implemented from public components. It does not, and
cannot, claim that any specific deployed AEDT (including any product
made by the patent's assignee) implements the architecture in the
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
