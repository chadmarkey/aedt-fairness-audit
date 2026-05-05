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
| Audit 1 (VADER + Claim 1 mitigator) | `examples/reference_outputs/audit_1/audit_1_results.json` (point + bootstrap CI); `audit_1_reps1000_perm.json` (pooled bootstrap + permutation); `audit_1_strat_perm.json` (stratified bootstrap + permutation) |
| Audit 2 SBERT | `examples/reference_outputs/audit_2/audit_2_results_sbert.json` (point + bootstrap CI); `audit_2_results_sbert_reps1000_perm.json` (pooled + perm); `audit_2_results_sbert_strat_perm.json` (stratified + perm) |
| Audit 2 LLM | `examples/reference_outputs/audit_2/audit_2_results_llm.json` (point + bootstrap CI); `audit_2_results_llm_reps1000_perm.json` (pooled + perm); `audit_2_results_llm_strat_perm.json` (stratified + perm) |
| Content equivalence | `examples/reference_outputs/content_equivalence/results.json` |
| Counterfactual decomposition | `examples/reference_outputs/counterfactual/counterfactual_decomposition.json` |
| Screening with counterfactual (multi-model) | `examples/reference_outputs/screening_counterfactual/results_multimodel.json` |
| Dilution test | `examples/reference_outputs/dilution_test/dilution_test_results.json` |
| Disclosure-rate sweep | `examples/reference_outputs/disclosure_sweep/results.json` |
| Paragraph audit | `examples/reference_outputs/paragraph_audit/scores.json` |

Each directory also contains the rendered figure (`.png` and `.pdf`)
produced by the corresponding `plots/plot_*.py` script.

Corpus: 384 PSs across 4 content seeds × 4 races × 2 genders × 3 school
tiers × 4 instances. Generated with `tools.generate_ps_corpus` using
`gpt-4o-mini`. The same audit pipeline was also run at n=192 with
gpt-5-mini-generated PSs and gpt-5-mini scoring; results were
direction-consistent and individually underpowered. The n=384 + gpt-4o-mini
configuration is reported here as the primary; the n=192 + gpt-5-mini
configuration is described at the end of this section as a robustness
check.

### Audit 1 — Bias Mitigator efficacy on a VADER pipeline

Top-K = 0.20. Permutation reps = 10,000 (two-sided, under null of
group-selection independence). Bootstrap CIs are computed at 1000 reps
and stored in the JSON output, but are not displayed in this table —
see "Why bootstrap CIs are not displayed" below.

| Axis | Baseline DI | Baseline perm-p | Post-mitigation DI | Post-mitigation perm-p | Δ DI |
|---|---:|:---:|---:|:---:|---:|
| gender | 1.081 | 0.70 | 1.026 | 0.90 | -0.055 |
| race | 1.271 | 0.27 | 1.271 | 0.27 | 0.000 |
| school_tier | 0.875 | 0.59 | 0.828 | 0.50 | -0.047 |

VADER is a sentiment baseline, not the patent's NLP architecture. None
of the Audit 1 cells reach permutation significance at n = 384. The
race baseline point estimate (1.271, just outside the 4/5 upper bound
of 1.25) is the closest, and the mitigator does not move it.
Substantively interpreting Claim 1 efficacy requires a patent-faithful
pipeline; build one yourself per
[`PIPELINE_BUILD_GUIDE.md`](PIPELINE_BUILD_GUIDE.md).

### Audit 2 SBERT — PS four-question extraction

Top-K = 0.30. Permutation reps = 10,000.

#### Per-question DI

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 0.949 (p=0.82) | **0.794** (p=0.25) | 1.054 (p=0.81) |
| refugee | 1.130 (p=0.45) | 1.141 (p=0.45) | 1.054 (p=0.81) |
| major_illness | 0.949 (p=0.83) | 0.865 (p=0.52) | 0.974 (p=0.91) |
| academic_career | 0.885 (p=0.51) | 0.989 (p=1.00) | 1.242 (p=0.18) |

#### Aggregate (patent §530 power-2 sum)

| Axis | DI | perm-p |
|---|---:|:---:|
| gender | 0.855 | 0.37 |
| race | 0.828 | 0.37 |
| school_tier | 1.143 | 0.42 |

The SBERT extractor produces no cells with permutation p < 0.10 at
n = 384. The strongest point estimate (poverty × race = 0.794, just
inside the 4/5 lower bound) reaches p = 0.25. The aggregate gender
finding observed at n = 192 (DI = 0.657, p = 0.12) does not replicate
at n = 384 (aggregate gender = 0.855, p = 0.37) — the n = 192 result
appears to have been a small-corpus artifact.

### Audit 2 LLM (gpt-4o-mini) — PS four-question extraction

Top-K = 0.30. Permutation reps = 10,000.

#### Per-question DI

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 1.130 (p=0.44) | 1.200 (p=0.32) | 1.097 (p=0.63) |
| refugee | 1.130 (p=0.45) | **0.602 (p=0.053)** | 0.938 (p=0.73) |
| major_illness | 1.091 (p=0.58) | **0.558 (p=0.029)** | 0.938 (p=0.72) |
| academic_career | 1.018 (p=0.91) | 0.865 (p=0.53) | 0.723 (p=0.11) |

#### Aggregate

| Axis | DI | perm-p |
|---|---:|:---:|
| gender | 1.018 | 0.91 |
| race | 1.036 | 0.90 |
| school_tier | **0.650** | **0.059** |

**Headline findings (n = 384):**

- **major_illness × race: DI = 0.558, p = 0.029** — significant at
  conventional p < 0.05.
- **refugee × race: DI = 0.602, p = 0.053** — borderline significant.
- **aggregate `_total` × school_tier: DI = 0.650, p = 0.059** — borderline
  significant; new at n = 384 (was DI = 0.950, p = 0.87 at n = 192).
- The two race-axis findings are direction-consistent with the n = 192
  result (refugee 0.507/p=0.07, major_illness 0.545/p=0.08): same
  direction, similar magnitude, with significance tightening at the
  larger sample. Robustness across two corpus sizes (n = 192, n = 384)
  *and* two scoring models (gpt-5-mini, gpt-4o-mini) is the strongest
  empirical claim the audit makes.

The aggregate `_total` row largely cancels the per-question race
disparities under §530's power-2 aggregation; the school_tier
aggregate signal is driven by academic_career × school_tier (DI = 0.723,
p = 0.11).

**Why bootstrap CIs are not displayed alongside the per-cell DI.** The
audit harness computes percentile bootstrap CIs (both pooled and
stratified-by-group variants are implemented) and stores them in the
JSON output for users who want them. They are not displayed in the
tables above because the LLM extractor produces near-discrete
per-question scores (each question's score clusters at 0.0 and 1.0
with sparse intermediate values), and under top-K selection on
near-discrete scores at n = 384 with imbalanced groups, both pooled
and stratified percentile bootstrap distributions are systematically
biased away from the observed sample DI — the displayed CI would not
bracket the displayed point estimate. Permutation testing under the
null of group-selection independence is the appropriate inferential
tool in this regime; it does not depend on the bootstrap distribution
and is reported above as the per-cell p-value.

**Multiple comparisons.** Audit 2 reports 12 per-question hypothesis
tests (4 questions × 3 axes) plus 3 per-axis aggregates per extractor,
i.e., 15 cells. Under Bonferroni correction at family-wise α = 0.05,
the corrected per-cell threshold is 0.05 / 15 ≈ 0.0033 — none of the
observed p-values clear that threshold. Under Benjamini–Hochberg FDR
control at q = 0.05, the rank-1 cell (major_illness × race, p = 0.029)
is compared against (1/15) × 0.05 ≈ 0.0033 and again does not clear.
**The substantive evidence in this audit is therefore the
direction-consistency of three race-axis cells around DI ≈ 0.55–0.60
across two corpus sizes (n = 192, n = 384) and two scoring models
(gpt-5-mini, gpt-4o-mini), not the conventional p-value of any single
cell.** Users running confirmatory rather than exploratory analyses
should pre-register specific cells of interest or apply standard
multiple-comparisons corrections.

### Cross-extractor observation

The SBERT and LLM extractors produce different per-cell findings on
the same corpus. SBERT shows no individual cell with p < 0.10 at
n = 384; LLM shows two race-axis cells (refugee, major_illness) at
p ≤ 0.053 plus an aggregate school_tier finding at p = 0.059. The
extractor architecture is an implementer's choice the patent does not
specify; both implementations are within col. 10's "users can apply
NLP" scope.

---

## Validation

### Content equivalence

Pairwise SBERT cosine distance over the 384-PS corpus at three nesting
levels:

| Nesting level | n pairs | mean | median | p10 | p90 |
|---|---:|---:|---:|---:|---:|
| within seed, within stratum | 576 | 0.166 | 0.160 | 0.111 | 0.225 |
| within seed, across stratum | 17,856 | 0.215 | 0.210 | 0.153 | 0.285 |
| across seed | 55,296 | 0.337 | 0.336 | 0.259 | 0.418 |

Ratio (within-seed-across-stratum / across-seed) = **0.637**.

Mean within-seed-across-stratum cosine distance (0.215) is 63.7% of
mean across-seed cosine distance (0.337). The ordering of the three
levels (within-stratum < across-stratum < across-seed) is preserved
from n = 192 (where the ratio was 0.615), and the relative gap between
demographic-marker drift and seed-level content drift is essentially
unchanged.

### Counterfactual decomposition

Apply the Claim 1 BiasMitigator (input-side anonymization: spaCy NER for
names, schools, locations + curated regex for pronouns, honorifics,
ethnicity, school names) to each PS. Re-score the marker-stripped PS
with the same LLM extractor (gpt-4o-mini). Compare DI on stripped vs.
original scores per question. Tests whether the LLM extractor's
per-question race DI is driven by demographic markers (names, schools,
identity phrases) or by within-seed content variation.

#### Race-axis decomposition (the cells with significant or borderline-significant findings)

| Question | DI(original) | DI(marker-stripped) | Δ | Interpretation |
|---|---:|---:|---:|---|
| refugee | 0.602 | 0.538 | -0.064 | content-driven; gap *widens* post-strip |
| major_illness | 0.558 | 0.558 | 0.000 | content-driven; *no movement* |
| academic_career | 0.865 | 0.903 | +0.039 | content-driven |
| _total (school_tier) | 0.650 | 0.750 | +0.100 | content-driven |

The two findings that reach permutation significance at n = 384
(major_illness × race at p = 0.029, refugee × race at p = 0.053) are
**not affected** by the patent's specified bias-removal step. Stripping
all detectable identifying tokens leaves the major_illness disparity
exactly unchanged and *increases* the refugee disparity. The aggregate
school_tier signal also persists post-strip (0.650 → 0.750). The
patent's input-side anonymization, applied as written, does not reach
the within-content signal the LLM extractor is reading.

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
# 1. Generate corpus (~$2-3 in API credits with gpt-4o-mini, n=384)
OPENAI_API_KEY=sk-... python -m tools.generate_ps_corpus \
    --provider openai --model gpt-4o-mini --instances-per-cell 4 \
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
