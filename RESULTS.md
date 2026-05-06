# Example Results

This file documents output produced by running the toolkit's CLI tools
on (a) a 384-personal-statement stratified synthetic corpus and (b)
illustrative narrative-tone anchorings. All numbers are reference
output from running the tools, not findings about any deployed AEDT.
Specific values vary across runs.

Two posture sections follow:

- **Toolkit reference output on illustrative anchorings** —
  multi-instrument and multi-architecture sensitivity demonstrations.
  Anchorings are labeled `instrument_a/b/c/d` to keep the methodology
  generic. Replace with values from your own sentiment instruments
  when running on your own document.
- **Synthetic-corpus audits** — Audits 1 and 2 plus content-equivalence
  and counterfactual decomposition diagnostics on the 384-PS stratified
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

Illustrative output, on a lexicon-class anchoring (low = 0.18, high =
0.78). The numbers below are from one representative run committed
in `examples/reference_outputs/disclosure_sweep/`. Values vary with
seed and anchoring; the linear-in-disclosure pattern is what to
expect.

| Disclosure rate | DI | DI status |
|---:|---:|---|
| 0% | ~0.10 | outside 4/5 by ~8× |
| 5% | ~0.15 | outside 4/5 by ~5× |
| 10% | ~0.19 | outside 4/5 by ~4× |
| 25% | ~0.34 | outside 4/5 |
| 50% | ~0.58 | outside 4/5 |
| 75% | ~0.78 | borderline |
| 90% | ~0.91 | passes |
| 100% | ~0.97 | passes |

At realistic protected-class disclosure rates (5–15% in many medical-
education settings), DI sits well below the 0.80 EEOC threshold. The
threshold typically crosses around 75–90% disclosure depending on
the anchoring's gap magnitude.

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

### Audit 1 — Bias Mitigator effect on a VADER baseline pipeline

Top-K = 0.20. Bootstrap reps = 1000. Paired-permutation reps = 10,000
(under null of pre/post score exchangeability — i.e., "the mitigator
has no systematic effect on the scores"). Bootstrap CIs are computed
and stored in the JSON output but are not displayed in this table.

| Axis | Baseline DI | Post-mitigation DI | Δ DI | paired-perm-p |
|---|---:|---:|---:|:---:|
| gender | 1.081 | 1.081 | +0.000 | 1.00 |
| race | 1.271 | 1.271 | +0.000 | 1.00 |
| school_tier | 0.875 | 0.783 | −0.092 | 0.52 |

**What this audit can and cannot test.** Audit 1 measures whether the
patent's specified bias-mitigation step changes a user-supplied
`pipeline_fn`'s output in a way that moves disparate impact. The
interpretive value of the result depends entirely on whether the
`pipeline_fn` reads the markers the mitigator strips. The example
pipeline shipped with the toolkit (`examples/example_pipeline.py`)
is VADER, a sentiment-lexicon scorer that is largely insensitive to
names, school names, locations, and ethnicity terms. Under VADER,
the mitigator's actions on those markers are mostly invisible to the
score. The reported Δ DI of zero on gender and race is therefore
consistent with "VADER doesn't read the markers the mitigator strips,"
not with "the mitigator effectively reduces disparity on a real
LLM-based AEDT." The school_tier Δ of −0.092 has a paired-permutation
p of 0.52 and is not distinguishable from chance at this sample size.

**Substantive mitigation testing lives in the counterfactual
decomposition (see Validation below)**, run against the LLM PS
extractor that does read the markers and the surrounding content. That
experiment is the one that addresses Claim 1 efficacy in any
substantive sense. Audit 1 is included as a sanity check that the
mitigator runs end-to-end against any user-supplied pipeline_fn, plus
a template anyone can adapt by replacing `pipeline_fn` with their own
AEDT scorer; it is not a finding about Claim 1 in general.

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
at n = 384 (aggregate gender = 0.855, p = 0.37). The n = 192 result
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

**Per-cell findings under gpt-4o-mini scoring (n = 384):**

- major_illness × race: DI = 0.558, p = 0.029 (uncorrected).
- refugee × race: DI = 0.602, p = 0.053 (uncorrected).
- aggregate `_total` × school_tier: DI = 0.650, p = 0.059 (uncorrected).
- These cells are direction-consistent with the n = 192 result
  scored with gpt-5-mini (refugee 0.507/p=0.07, major_illness
  0.545/p=0.08): same direction, similar magnitude. Both gpt-5-mini
  and gpt-4o-mini are OpenAI models, so this is not a cross-family
  robustness check. The cross-family check with claude-haiku-4-5 is
  reported below and **does not** reproduce these per-cell findings.

The aggregate `_total` row largely cancels the per-question race
disparities under §530's power-2 aggregation under gpt-4o-mini scoring.
The school_tier aggregate signal is driven by academic_career ×
school_tier (DI = 0.723, p = 0.11).

### Audit 2 LLM cross-family robustness check (claude-haiku-4-5 scoring)

The same n = 384 corpus, scored with `claude-haiku-4-5` instead of
`gpt-4o-mini`, produces a different per-cell pattern. This is an
important methodological caveat: LLM-based PS-question scoring is
vendor-dependent.

#### Per-question DI

| Question | gender | race | school_tier |
|---|:---:|:---:|:---:|
| poverty | 1.054 (p=0.74) | 1.141 (p=0.46) | 0.902 (p=0.56) |
| refugee | 1.130 (p=0.44) | **1.409 (p=0.052)** | 1.097 (p=0.63) |
| major_illness | 0.983 (p=1.00) | 0.903 (p=0.60) | 1.013 (p=1.00) |
| academic_career | 1.054 (p=0.75) | 0.903 (p=0.61) | **0.698 (p=0.070)** |

#### Aggregate

| Axis | DI | perm-p |
|---|---:|:---:|
| gender | 0.949 | 0.82 |
| race | 1.200 | 0.32 |
| school_tier | 1.013 | 1.00 |

**What changes under cross-family scoring:**

- **major_illness × race** moves from DI = 0.558 (gpt-4o-mini) to
  DI = 0.903 (claude-haiku). The disparity is essentially absent
  under the second scorer.
- **refugee × race** moves from DI = 0.602 to DI = 1.409. The
  direction inverts. Under claude-haiku, the non-White stratum is
  selected at a *higher* rate than the White stratum on this question.
- **aggregate × school_tier** moves from DI = 0.650 to DI = 1.013.
  The school_tier signal disappears entirely.
- **academic_career × school_tier** moves from DI = 0.723 to
  DI = 0.698. This one cell is similar across families and is the
  only borderline finding (p of about 0.07) shared between scorers.

**What this means.** The audit's per-cell numerical findings on
race-axis disparity under LLM-based PS scoring **do not transfer**
across LLM families. The same patent-specified pipeline, run on the
same synthetic corpus with the same patent-specified mitigation,
produces materially different per-cell demographic outcomes depending
on which LLM answers the four PS questions. The patent does not
specify which LLM. The cross-family check shows that choice is
load-bearing.

This is consistent with a peer-review critique that same-family
generation and scoring confounds "the patent's pipeline produces a
bias signal" with "the model family encodes stereotypes that surface
in both generation and scoring." Under cross-family scoring, the
stereotype-confound explanation is more parsimonious for at least
some cells. The audit's substantive claim therefore narrows.

- **Original framing (n = 384, single scoring family):** "Three
  race-axis cells fail the four-fifths range at DI ≈ 0.55–0.60 with
  direction-consistency across two corpus sizes."
- **Revised framing (after cross-family check):** "The patent's
  LLM-based PS-extraction pipeline produces vendor-dependent
  demographic outcomes. Different LLM families produce different
  per-cell findings, in some cases on opposite axes or in opposite
  directions. The patent's specified bias-mitigation step (Claim 1
  input-side anonymization) does not close the per-cell gaps observed
  under gpt-4o-mini scoring; cross-family verification of the
  mitigation step is pending. Applicants are subject to a vendor's
  undocumented LLM choice, and the patent's specified mitigation
  does not, on the configurations tested, address that choice."

The counterfactual-decomposition finding (the patent's mitigation
does not close the gap; see *Counterfactual decomposition* in
Validation below) was tested under gpt-4o-mini scoring at n = 384.
The qualitative result (the mitigator does not move per-cell DI) is
the strongest single finding in the audit at present, and it has not
been verified under the claude-haiku-4-5 scoring run. That follow-up
test is a planned next step.

**Why bootstrap CIs are not displayed alongside the per-cell DI.** The
audit harness computes percentile bootstrap CIs in two variants
(pooled and stratified-by-group). It stores them in the JSON output
for users who want them. They are not displayed in the tables above
for a specific reason. The LLM extractor produces near-discrete
per-question scores. Each question's score clusters at 0.0 and 1.0
with sparse intermediate values. Under top-K selection on
near-discrete scores at n = 384 with imbalanced groups, both pooled
and stratified percentile bootstrap distributions sit systematically
away from the observed sample DI. The displayed CI does not bracket
the displayed point estimate in either case. Permutation testing
under the null of group-selection independence is the inferential
tool that holds in this regime. It does not depend on the bootstrap
distribution. It is reported above as the per-cell p-value.

**Multiple comparisons.** Audit 2 reports 15 hypothesis tests per
extractor (12 per-question plus 3 aggregate). Across two scorers
that is 30 tests. Under Bonferroni correction at family-wise α = 0.05,
the corrected per-cell threshold is α / k. Under Benjamini–Hochberg
FDR at q = 0.05, the rank-1 threshold is the same. None of the
observed p-values clear either correction. **The substantive evidence
in this audit is not any individual cell's significance.** It is two
qualitative observations. First, under at least one LLM scoring
family, the patent's pipeline produces per-cell DIs outside the 4/5
range. Second, the cross-family check shows those per-cell findings
do not stably transfer across LLM families. Different families
produce different patterns. Users running confirmatory rather than
exploratory analyses should pre-register specific cells of interest,
apply standard multiple-comparisons corrections, and run cross-family
robustness checks before drawing inferential conclusions.

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
register. Those carry the residual demographic signal the LLM picks
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
