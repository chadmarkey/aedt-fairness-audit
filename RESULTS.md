# Example Results

This file documents output produced by running the toolkit's CLI tools
on (a) a 192-personal-statement stratified synthetic corpus and (b)
illustrative narrative-tone anchorings. All numbers are reference
output from running the tools, not findings about any deployed AEDT.
Specific values vary across runs.

Two posture sections follow:

- **Toolkit reference output on illustrative anchorings** —
  multi-instrument and multi-architecture sensitivity demonstrations.
  Anchorings are labeled `instrument_a/b/c/d` to keep the methodology
  generic; replace with values from your own sentiment instruments
  when running on your own document.
- **Synthetic-corpus audits** — Audits 1 and 2 plus content-equivalence
  and counterfactual decomposition diagnostics on the 192-PS stratified
  corpus.

---

## Toolkit reference output (illustrative anchorings)

These tables show the kind of output the toolkit produces when run on
four illustrative sentiment-instrument anchorings (a lexicon-class
tool, a transformer-class tool, two LLM-judge variants). The actual
anchoring values are in
[`examples/screening_anchorings_template.json`](examples/screening_anchorings_template.json).

### A. Per-section paragraph audit (multi-instrument)

`tools/run_paragraph_audit.py` scores a sectioned document under
multiple sentiment instruments. The architectural signal a
section-aware extraction pipeline would surface is when one section is
the lowest-scoring section under every instrument simultaneously.
Example output on a generic medical-school evaluation skeleton with a
single low-tone leave-of-absence paragraph: the leave-of-absence
section is rank-lowest under both the VADER lexicon (+0.18 vs +0.55+
elsewhere) and a RoBERTa transformer (+0.04 vs +0.85+ elsewhere). LLM
judges produce similar rank-ordering on the same input.

### B. Excerpt vs full-document scoring (dilution test)

`tools/run_dilution_test.py` compares a low-tone variant against a
high-tone variant of the same content, scored as a standalone excerpt
and as a paragraph embedded in a longer skeleton document. The score
gap typically dilutes to near zero when the variant is buried in a
long surrounding document under lexicon and transformer scoring;
LLM-judge instruments retain more of the gap.

| Instrument class | Excerpt-level gap | Full-document gap | % dilution |
|---|---:|---:|---:|
| Lexicon-class (e.g., VADER) | ~+0.6 | ~0.0 | ~100% |
| Transformer-class (e.g., RoBERTa-sentiment) | ~+0.2 | ~0.0 | ~100% |
| LLM-judge variant A | ~+0.95 | ~+0.16 | ~83% |
| LLM-judge variant B | ~+0.77 | ~+0.05 | ~94% |

Pattern: lexicon and transformer instruments fully dilute under
whole-document scoring; LLM judges retain the gap.

### C. Screening simulation under multiple sentiment anchorings

`tools/run_screening_simulation.py` and
`tools/run_screening_with_counterfactual.py` take a JSON of sentiment
anchorings (one per instrument class), generate stratified synthetic
applicants, fit a screening model, top-K-select, and bootstrap
disparate-impact CIs. The counterfactual variant adds a sentiment-only
intervention: replace the disadvantaged group's narrative-tone score
with the high-anchoring distribution and re-rank under the same
trained model.

Across the four illustrative anchorings, baseline DI sits at
levels outside the EEOC four-fifths range under every scoring method tested (linear,
logistic regression, patent §530 power-of-2 aggregation,
power-of-3 aggregation). Under the sentiment-only counterfactual, DI
recovers to within ±0.05 of parity in every cell. The patent §530
power-of-N aggregation amplifies, rather than mitigates, the baseline
disparity vs. linear scoring on the same anchorings.

### D. Disclosure-rate sweep

`tools/run_disclosure_sweep.py` varies the fraction of disadvantaged-
group applicants whose narrative is overridden with the high-
sentiment distribution (the "vendor protected-class control" trigger
rate) and reports DI at each rate.

Pattern across illustrative anchorings: DI is approximately linear in
disclosure rate. At realistic protected-class disclosure rates (5–15%
in many medical-education settings), DI sits well below the 0.80
EEOC threshold. The threshold typically crosses around 75–90%
disclosure depending on the anchoring's gap magnitude.

| Disclosure rate | DI (lexicon-class anchoring) | DI status |
|---:|---:|---|
| 0% | ~0.10 | outside 4/5 by ~8× |
| 5% | ~0.15 | outside 4/5 by ~5× |
| 10% | ~0.19 | outside 4/5 by ~4× |
| 25% | ~0.34 | outside 4/5 |
| 50% | ~0.58 | outside 4/5 |
| 75% | ~0.78 | borderline |
| 90% | ~0.91 | passes |
| 100% | ~0.97 | passes |

---

## Synthetic-corpus audits

Source artifacts. The `examples/reference_outputs/` paths are
committed reference output sets; running the tools yourself writes
fresh JSON + PNG/PDF figures to user-supplied `--out-dir` paths.

| Artifact | Reference output path |
|---|---|
| Corpus generator | `tools/generate_ps_corpus.py` |
| Audit 1 (VADER + Claim 1 mitigator) | `examples/reference_outputs/audit_1/audit_1_reps1000.json` |
| Audit 2 SBERT | `examples/reference_outputs/audit_2/audit_2_results_sbert_reps1000.json` |
| Audit 2 LLM (small open-weights or LLM-judge model) | `examples/reference_outputs/audit_2/audit_2_results_llm_reps1000.json` |
| Content equivalence | `examples/reference_outputs/content_equivalence/results.json` |
| Counterfactual decomposition | `examples/reference_outputs/counterfactual/counterfactual_decomposition.json` |
| Screening with counterfactual (multi-model) | `examples/reference_outputs/screening_counterfactual/results_multimodel.json` |
| Dilution test | `examples/reference_outputs/dilution_test/dilution_test_results.json` |
| Disclosure-rate sweep | `examples/reference_outputs/disclosure_sweep/results.json` |
| Paragraph audit | `examples/reference_outputs/paragraph_audit/scores.json` |

Each directory also contains the rendered figure (`.png` and `.pdf`)
produced by the corresponding `plots/plot_*.py` script.

Corpus: 192 PSs across 4 content seeds × 4 races × 2 genders × 3 school
tiers × 2 instances. Generated with `tools.generate_ps_corpus` using
`gpt-5-mini`.

### Audit 1 — Bias Mitigator efficacy on a VADER pipeline

Top-K = 0.20, bootstrap reps = 1000, permutation reps = 10,000.

| Axis | Baseline DI [95% CI] perm-p | Post-mitigation DI [95% CI] perm-p | Δ DI |
|---|:---:|:---:|---:|
| gender | 1.111 [0.542, 2.034] p=0.72 | 1.000 [0.523, 1.795] p=1.00 | -0.111 |
| race | 1.074 [0.525, 2.389] p=0.84 | 0.933 [0.484, 2.063] p=1.00 | -0.141 |
| school_tier | 1.611 [0.837, 3.960] p=0.11 | 1.400 [0.714, 3.225] p=0.24 | -0.211 |

None of the Audit 1 baseline cells reach permutation significance at
n = 192. The school_tier baseline point estimate (1.611, outside the
4/5 upper bound of 1.25) is the closest to significance (p = 0.11) and
moves toward parity post-mitigation, but the sample is underpowered
to confirm the effect inferentially.

VADER is a sentiment baseline, not the patent's NLP architecture. All
three axes drift toward parity post-mitigation; baselines are within
EEOC bounds. Substantively interpreting Claim 1 efficacy requires a
patent-faithful pipeline; build one yourself per
[`PIPELINE_BUILD_GUIDE.md`](PIPELINE_BUILD_GUIDE.md).

### Audit 2 SBERT — PS four-question extraction

Top-K = 0.30, bootstrap reps = 1000, permutation reps = 10,000.

#### Per-question DI

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 0.812 [0.544, 1.359] | 1.048 [0.637, 1.913] | 1.026 [0.674, 1.764] |
| refugee | 0.933 [0.584, 1.465] | 1.048 [0.691, 2.041] | 1.206 [0.799, 2.289] |
| major_illness | 1.231 [0.830, 1.981] | 1.048 [0.654, 1.969] | 1.111 [0.660, 1.804] |
| **academic_career** | **0.758** [0.457, 1.174] | 1.278 [0.717, 2.230] | 0.950 [0.611, 1.579] |

#### Per-question permutation p-values

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 0.434 | 0.867 | 1.000 |
| refugee | 0.871 | 0.862 | 0.415 |
| major_illness | 0.346 | 0.855 | 0.742 |
| academic_career | 0.269 | 0.314 | 0.867 |

#### Aggregate (patent §530 power-2 sum)

| Axis | DI | 95% CI | perm-p |
|---|---:|:---:|:---:|
| **gender** | **0.657** | [0.432, 1.117] | 0.121 |
| race | 1.048 | [0.595, 1.737] | 0.860 |
| school_tier | 1.026 | [0.644, 1.683] | 1.000 |

Aggregate gender DI = 0.657 is the SBERT extractor's strongest signal
at point estimate and reaches p = 0.12 under permutation testing —
suggestive but not conventionally significant at n = 192. The
academic_career question is the per-question driver (DI = 0.758,
p = 0.27).

### Audit 2 LLM (gpt-5-mini) — PS four-question extraction

Top-K = 0.30, bootstrap reps = 1000, permutation reps = 10,000.

#### Per-question DI (point + 95% bootstrap CI)

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 1.000 [0.611, 1.522] | 0.956 [0.640, 1.804] | 1.026 [0.660, 1.701] |
| refugee | 1.071 [0.668, 1.637] | **0.507** [0.610, 1.645] | 1.026 [0.692, 1.785] |
| major_illness | 1.148 [0.682, 1.554] | **0.545** [0.592, 1.690] | 0.881 [0.611, 1.537] |
| academic_career | 1.071 [0.630, 1.491] | **0.587** [0.592, 1.645] | 0.950 [0.613, 1.506] |

#### Per-question two-sided permutation p-values

p-value tests the null that group assignment is independent of
top-K selection (n_perms = 10,000):

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 1.000 | 1.000 | 1.000 |
| refugee | 0.748 | **0.071** | 1.000 |
| major_illness | 0.532 | **0.083** | 0.618 |
| academic_career | 0.752 | 0.157 | 0.871 |

#### Aggregate

| Axis | DI | 95% CI | perm-p |
|---|---:|:---:|:---:|
| gender | 1.000 | [0.649, 1.522] | 1.000 |
| race | 0.875 | [0.615, 1.667] | 0.720 |
| school_tier | 0.950 | [0.601, 1.571] | 0.872 |

Three of four race-axis questions sit at DI ≈ 0.51–0.59 — point estimates
outside the four-fifths range. Two of those three (refugee, major_illness)
reach marginal permutation significance (p ≈ 0.07–0.08); academic_career
shows the same direction at p = 0.16. The aggregate `_total` row masks
the per-question pattern because the four questions partially cancel
when summed under §530's power-2 aggregation.

**Reading the bootstrap CIs alongside the permutation p-values.** With
n = 192, group sizes ~96, and binary top-K selection, the disparate-
impact ratio is a discrete-valued statistic. Several percentile CIs
(refugee/illness/academic_career race) sit *above* the point estimate
they bracket — a known pathology of bootstrap percentile intervals on
small-n discrete statistics. The permutation p-values are the
appropriate inferential complement here: at this sample size, the
point estimates are descriptively striking but individually
underpowered. The substantive finding is the *direction-consistency*
across three race-axis questions despite limited per-question power,
not any single cell's significance.

### Cross-extractor observation

On the same corpus, the SBERT and LLM extractors raise adverse-impact
flags under EEOC's four-fifths heuristic on different demographic axes:

- SBERT: aggregate gender DI = 0.657
- LLM: per-question race DI = 0.51–0.59 on three of four questions

The axis depends on architectural choices the patent does not specify.

---

## Validation

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
