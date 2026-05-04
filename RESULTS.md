# Example Results

This file documents two bodies of work produced with this toolkit:

1. Headline MSPE-anchored findings (December 2025 – January 2026) on a
   single MSPE document. Reproducible via the toolkit's CLI templates
   (`tools/run_paragraph_audit.py`, `tools/run_dilution_test.py`,
   `tools/run_screening_simulation.py`) on any document a user supplies.
2. Synthetic-corpus audits (May 2026) on a 192-PS stratified corpus
   exercising the patent's Personal Statement Component (col. 10) and
   the Claim 1 Bias Mitigator.

These are not findings about any deployed AEDT. They are reference
numbers showing the kind of output the toolkit produces when run
end-to-end. Run on your own corpus and compare.

---

## Part 1 — Headline MSPE findings (December 2025 – January 2026)

Anchor document: a single 3,245-word MSPE produced by an accredited U.S.
medical school, describing approved medical leaves of absence in AAMC
template language ("voluntary," "personal reasons"). The actual MSPE is
gitignored; only aggregate scores are public.

### A. Four-instrument excerpt-level sentiment gap

| Instrument | Original wording | Recovery-affirming counterfactual | Gap |
|---|---:|---:|---:|
| VADER (lexicon) | +0.18 | +0.78 | +0.60 |
| RoBERTa (transformer) | +0.02 | +0.23 | +0.22 |
| Claude (LLM judge) | -0.40 | +0.55 | +0.95 |
| GPT-5 (LLM judge) | -0.22 | +0.55 | +0.77 |

Same dates, same diagnoses, same outcomes; wording differs. Every
instrument detects the gap. The most sophisticated instruments detect
the largest ones.

### B. Per-section paragraph-by-paragraph audit

13 substantive sections of the MSPE (≥50 words), scored independently
under the four instruments. The leave-of-absence-containing
"ACADEMIC HISTORY" section is rank-lowest under every instrument:
RoBERTa and GPT-5 score it net negative, Claude zero, VADER +0.42.
The next-lowest substantive section sits at +0.55 or above on all four
scales. Four instruments, no awareness of each other or the case,
unanimous.

The CLI template for this audit is `tools/run_paragraph_audit.py`:

```bash
python -m tools.run_paragraph_audit \
    --document /path/to/document.txt \
    --instruments vader transformer llm \
    --llm-provider openai --llm-model gpt-5-mini \
    --out out/paragraph_audit/scores.json
```

Reports per-section scores per instrument and flags any section that
is rank-lowest unanimously across all instruments — the architectural
signal that section-aware extraction would surface.

### C. Top-quantile screening simulation, n=6,000

Stratified synthetic applicants under the four-instrument-anchored
sentiment gap, every other applicant feature held constant, top-K
selection at the 12% invite rate.

| Metric | Value |
|---|---:|
| Disparate impact (group_0 / group_1) | **0.019** |
| Statistical parity difference | -0.235 |
| Equal opportunity difference | -0.267 |
| False positive rate difference | -0.157 |
| EEOC 4/5 threshold | 0.80 |
| Multiple of failure | **42×** |

Sentiment-only counterfactual at fixed threshold: **DI ≈ 1.000**
(parity within sampling noise). 23% of disadvantaged-group applicants
who were rejected at baseline cross the algorithmic bar with wording
substitution alone.

### D. Eight-anchoring architectural sensitivity sweep

DI under eight production-plausible scoring architectures (excerpt vs.
whole-document × four instruments). Range: **0.000–0.436**. The
strongest finding (DI = 0.019) is excerpt-level under section-aware
extraction. The weakest finding (DI = 0.436, 95% CI [0.263, 0.658]) is
whole-document Claude on a synthetic MSPE skeleton — and still fails
EEOC 4/5 at point estimate.

### E. Dilution from excerpt-level to full-document scoring

| Instrument | Excerpt gap | Full-document gap | % dilution |
|---|---:|---:|---:|
| VADER | +0.60 | 0.00 | 100% |
| RoBERTa | +0.22 | 0.00 | 100% |
| Claude | +0.95 | +0.16 | 83% |
| GPT-5 | +0.77 | +0.05 | 94% |

VADER and RoBERTa fully dilute; the gap survives whole-document scoring
under both LLM judges — the architecture class Thalamus's published
materials describe for Cortex's AI features.

### F. Disclosure-rate sweep

Disparate impact as a function of the rate at which the
disadvantaged-group MSPE uses ADA/504-protected language a vendor
control would trigger on.

| Disclosure rate | DI | Status |
|---:|---:|---|
| 5% | 0.067 | Fails 4/5 by 12× |
| 10% | 0.119 | Fails 4/5 by 7× |
| 25% | 0.243 | Fails 4/5 |
| 50% | 0.479 | Fails 4/5 |
| 75% | 0.701 | Fails 4/5 |
| 90% | 0.844 | Mostly passes |
| 100% | 0.922 | Passes |

DI is approximately linear in disclosure rate; the four-fifths threshold
crosses at ~85% disclosure. Realistic disclosure rates among medical
students with ADA-protected conditions are 5–15%. At that range, DI
sits between 0.067 and 0.119 — failing four-fifths by a factor of 7 to
12, regardless of any vendor protected-class control.

### Reproducing the screening simulation (code template)

The simulation harness is `tools/run_screening_simulation.py`; the input
template is `examples/screening_anchorings_template.json`. Users supply
their own per-instrument sentiment anchorings; the harness generates
synthetic applicants, fits a screening model, top-K selects, and reports
DI with bootstrap CIs.

```bash
python -m tools.run_screening_simulation \
    --anchorings examples/screening_anchorings_template.json \
    --out-dir out/screening_simulation \
    --n 6000 --invite-rate 0.30 --bootstrap-reps 1000
```

The dilution test harness is `tools/run_dilution_test.py`; the input
template is `examples/dilution_test_template.json`, with a generic
MSPE-style skeleton at `examples/mspe_skeleton_template.txt`.

```bash
python -m tools.run_dilution_test \
    --config examples/dilution_test_template.json \
    --out-dir out/dilution_test
```

Numerical results will not match exactly — sampling is stochastic,
synthetic populations differ, vendor architectures evolve. The stable
patterns: (1) sentiment gaps survive whole-document scoring under LLM
judges and dilute under VADER/RoBERTa, (2) realistic protected-class
disclosure rates leave most disadvantaged-group applicants unprotected
by any vendor control, (3) excerpt-anchored DI under section-aware
extraction sits orders of magnitude below 4/5.

---

## Part 2 — Synthetic-corpus audits (May 2026)

Source artifacts (paths relative to repo root):

| Artifact | Path |
|---|---|
| Corpus generator | `tools/generate_ps_corpus.py` |
| Audit 1 (VADER + Claim 1 mitigator) | `out/audit_1/audit_1_reps1000.json` |
| Audit 2 SBERT | `out/audit_2/audit_2_results_sbert_reps1000.json` |
| Audit 2 LLM (gpt-5-mini) | `out/audit_2/audit_2_results_llm_reps1000.json` |
| Content equivalence | `out/content_equivalence/results.json` |
| Counterfactual decomposition | `out/counterfactual/counterfactual_decomposition.json` |

Corpus: 192 PSs across 4 content seeds × 4 races × 2 genders × 3 school
tiers × 2 instances. Generated with `tools.generate_ps_corpus` using
`gpt-5-mini`.

### Audit 1 — Bias Mitigator efficacy on a VADER pipeline

Top-K = 0.20, bootstrap reps = 1000.

| Axis | Baseline DI | 95% CI | Post-mitigation DI | 95% CI | Δ DI |
|---|---:|:---:|---:|:---:|---:|
| gender | 1.111 | [0.542, 2.034] | 1.000 | [0.523, 1.795] | -0.111 |
| race | 1.074 | [0.525, 2.389] | 0.933 | [0.484, 2.063] | -0.141 |
| school_tier | 1.611 | [0.837, 3.960] | 1.400 | [0.714, 3.225] | -0.211 |

VADER is a sentiment baseline, not the patent's NLP architecture. All
three axes drift toward parity post-mitigation; baselines are within
EEOC bounds. Substantively interpreting Claim 1 efficacy requires a
patent-faithful pipeline; build one yourself per
[`PIPELINE_BUILD_GUIDE.md`](PIPELINE_BUILD_GUIDE.md).

### Audit 2 SBERT — PS four-question extraction

Top-K = 0.30, bootstrap reps = 1000.

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 0.812 [0.544, 1.359] | 1.048 [0.637, 1.913] | 1.026 [0.674, 1.764] |
| refugee | 0.933 [0.584, 1.465] | 1.048 [0.691, 2.041] | 1.206 [0.799, 2.289] |
| major_illness | 1.231 [0.830, 1.981] | 1.048 [0.654, 1.969] | 1.111 [0.660, 1.804] |
| **academic_career** | **0.758** [0.457, 1.174] | 1.278 [0.717, 2.230] | 0.950 [0.611, 1.579] |

Aggregate (patent §530 power-2 sum):

| Axis | DI | 95% CI |
|---|---:|:---:|
| **gender** | **0.657** | [0.432, 1.117] |
| race | 1.048 | [0.595, 1.737] |
| school_tier | 1.026 | [0.644, 1.683] |

Aggregate gender DI fails EEOC 4/5 at point estimate; CI crosses 1.0 at
n=192. Driver: academic_career question (women selected at 76% rate of
men).

### Audit 2 LLM (gpt-5-mini) — PS four-question extraction

Top-K = 0.30, bootstrap reps = 1000.

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 1.000 [0.611, 1.522] | 0.956 [0.640, 1.804] | 1.026 [0.660, 1.701] |
| refugee | 1.071 [0.668, 1.637] | **0.507** [0.610, 1.645] | 1.026 [0.692, 1.785] |
| major_illness | 1.148 [0.682, 1.554] | **0.545** [0.592, 1.690] | 0.881 [0.611, 1.537] |
| academic_career | 1.071 [0.630, 1.491] | **0.587** [0.592, 1.645] | 0.950 [0.613, 1.506] |

Aggregate:

| Axis | DI | 95% CI |
|---|---:|:---:|
| gender | 1.000 | [0.649, 1.522] |
| race | 0.875 | [0.615, 1.667] |
| school_tier | 0.950 | [0.601, 1.571] |

Three of four questions show race DI well below 4/5 at point estimate.
Aggregate masks this because per-question disparities partially cancel.

**Bootstrap CI artifact.** Several CI intervals (refugee/illness/
academic_career race) sit *above* the point estimate. With binary top-K
selection at n=192 and group sizes ~96, single-applicant reshuffles
move the DI ratio in chunks; the bootstrap distribution does not
bracket the actual sample DI cleanly. The point DI is the relevant
fairness measurement; the CI characterizes resampling stability.

### Cross-extractor observation

On the same corpus, the SBERT and LLM extractors fail EEOC 4/5 on
different demographic axes:

- SBERT: aggregate gender DI = 0.657
- LLM: per-question race DI = 0.51–0.59 on three of four questions

The axis depends on architectural choices the patent does not specify.

---

## Part 3 — Validation

### Content equivalence

Pairwise SBERT cosine distance over the 192-PS corpus at three nesting
levels:

| Nesting level | n pairs | mean | median | p10 | p90 |
|---|---:|---:|---:|---:|---:|
| within seed, within stratum | 96 | 0.209 | 0.197 | 0.138 | 0.278 |
| within seed, across stratum | 4,416 | 0.253 | 0.241 | 0.182 | 0.326 |
| across seed | 13,824 | 0.411 | 0.405 | 0.303 | 0.523 |

Ratio (within-seed-across-stratum / across-seed) = **0.615**.

Mean within-seed-across-stratum cosine distance (0.253) is 61.5% of
mean across-seed cosine distance (0.411). Within-seed-within-stratum
distance (0.209) is the smallest of the three.

### Counterfactual decomposition

Apply the Claim 1 BiasMitigator (input-side anonymization: spaCy NER for
names, schools, locations + curated regex for pronouns, honorifics,
ethnicity, school names) to each PS. Re-score the marker-stripped PS
with the same LLM extractor. Compare DI on stripped vs. original scores
per question. Tests whether the LLM extractor's per-question race DI of
0.51–0.59 is driven by demographic markers (names, schools, identity
phrases) or by within-seed content variation.

#### Race-axis decomposition (the questions that produced original DI)

| Question | DI(original) | DI(marker-stripped) | Δ | Interpretation |
|---|---:|---:|---:|---|
| refugee | 0.507 | 0.545 | +0.038 | content-driven |
| major_illness | 0.545 | 0.633 | +0.088 | content-driven |
| academic_career | 0.587 | 0.587 | 0.000 | content-driven |
| _total | 0.875 | 1.278 | +0.403 | content-driven |

After Claim 1 input-side anonymization (NER + curated identifier
substitution), the three race-axis per-question DIs that failed EEOC
4/5 in the original run (refugee, major_illness, academic_career)
remain at 0.55–0.63 within ±0.09 of their original values. The
aggregate `_total` row moves from 0.875 to 1.278; the magnitude is
preserved, the direction reverses.

For reference, the patent's Claim 1 specifies the mitigation as
detect-and-replace on identifying tokens with semantic structure
maintained:

> "Bias mitigation operation including: Detecting one or more
> potentially biasing identifiers from one or more document files;
> Replacing one or more potentially biasing identifiers with one or more
> corresponding neutral terms such that semantic structure is
> maintained." — U.S. Patent No. 12,265,502 B1, claim 1.

#### Sample mitigator output

For transparency on what "marker-stripped" actually means, three
example PS openings before and after the BiasMitigator:

> **[PS0001] BEFORE:** "I grew up in a stable middle-class household
> in suburban Concord, New Hampshire, where family dinners with my
> mother, Linda Carter, and weekend volunteer shifts at the local
> community center taught me the value of stability..."
>
> **[PS0001] AFTER:** "I grew up in a stable middle-class household
> in suburban [LOC], [LOC], where family dinners with my mother,
> [NAME], and weekend volunteer shifts at the local community center
> taught me the value of stability..."

The mitigator removes person names, locations, school names, and
pronouns. It does not remove the narrative arc, the family
configuration, the kinds of activities described, or the sentence-level
register — those carry the residual demographic signal the LLM picks
up.

---

## Reproducing the synthetic-corpus audits

```bash
# 1. Generate corpus (~$1 in API credits with gpt-5-mini)
OPENAI_API_KEY=sk-... python -m tools.generate_ps_corpus \
    --provider openai --model gpt-5-mini \
    --out synthetic/data/ps_corpus.jsonl

# 2. Audit 1 — VADER baseline + Claim 1 mitigator
python -m tools.run_audit_1 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --pipeline examples.example_pipeline:score_texts \
    --out-dir out/audit_1 --bootstrap-reps 1000

# 3. Audit 2 — SBERT extractor
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor sbert --bootstrap-reps 1000

# 4. Audit 2 — LLM extractor
python -m tools.run_audit_2 \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out-dir out/audit_2 --extractor llm \
    --llm-provider openai --llm-model gpt-5-mini --bootstrap-reps 1000

# 5. Content equivalence
python -m tools.content_equivalence \
    --corpus synthetic/data/ps_corpus.jsonl \
    --out out/content_equivalence/results.json

# 6. Counterfactual decomposition
python -m tools.counterfactual_decomposition \
    --corpus synthetic/data/ps_corpus.jsonl \
    --original-scores out/audit_2/audit_2_per_applicant_scores_llm.csv \
    --out-dir out/counterfactual \
    --llm-provider openai --llm-model gpt-5-mini
```

The corpus and `out/` are gitignored. Users running the harness see the
same file structure on disk after each run.
