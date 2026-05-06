# Changelog

A record of substantive methodology revisions made after the initial
public release. Anyone reading the current state of the repo can
reconstruct how it got here without spelunking through git log.

The commit history is not squashed. Every change is recoverable.

## 2026-05-05 — Methodology hardening in response to external critique

The day after the WIRED article ran, an external methodology critique
appeared on a public forum. It made four substantive points:
multiple-comparisons correction, a visible inconsistency between the
displayed point estimate and the displayed bootstrap CI in the
per-cell tables, the reproduction command in the README skipping the
permutation-test step, and the same-model-family confound between
the synthetic corpus generator and the LLM-based PS extractor. I
worked through them over the next 24 hours, with the cross-family
robustness check completing last.

**File-name references in `RESULTS.md` fixed.** Three rows in the
source-artifacts table referenced filenames that no longer existed
after the n=192 to n=384 update renamed the JSON outputs. I replaced
them with the actual filenames in `examples/reference_outputs/`.
Commit `8e85932`.

**Stratified bootstrap is now the default in `audit/screening.py`.**
The old pooled-sample bootstrap drifted away from the observed DI
under imbalanced group sizes. Stratified resampling preserves group
structure within each rep. The pooled variant is still available for
users who want joint-distribution variability; pass `stratified=False`.

There is an important caveat documented in `RESULTS.md`. Under the
LLM extractor, per-question scores are near-discrete (clusters at
0.0 and 1.0 with sparse intermediates). Both pooled and stratified
percentile bootstrap distributions on top-K with near-discrete scores
sit systematically away from the observed DI. The displayed CI does
not bracket the displayed point in either case. Permutation testing
under the null of group-selection independence is the inferential tool
that holds in this regime, and the audit reports per-cell permutation
p-values as the primary inferential output.

**Bootstrap CIs removed from the per-cell tables in `RESULTS.md`.**
They are still computed and stored in JSON for users who want them.
They are no longer displayed alongside the per-cell DI in the visible
tables. The permutation p-value is what gets shown.

**Multiple-comparisons disclosure added to `RESULTS.md`.** Audit 2
reports 30 cells across the two scorers. Under Bonferroni or
Benjamini–Hochberg FDR correction, no observed p-value clears the
corrected threshold. The headline framing was revised to acknowledge
this explicitly. Per-cell significance is no longer the substantive
claim.

**Quickstart updated.** The reproduction sequence in the README now
includes the permutation-test step (`tools/rebootstrap.py` with
`--n-permutations`). Following the prior Quickstart literally would
not have produced the p-values reported in `RESULTS.md`.

**Cross-family scoring run executed and disclosed.** I ran a robustness
check using `claude-haiku-4-5` to score the same n=384 corpus that
was generated with `gpt-4o-mini`. The per-cell race-axis findings
did not transfer. Under claude-haiku scoring, refugee × race inverts
direction (DI = 0.602 under gpt-4o-mini becomes DI = 1.409 under
claude-haiku), major_illness × race moves toward parity (0.558 to
0.903), and the aggregate × school_tier signal disappears (0.650 to
1.013). One borderline finding (academic_career × school_tier) is
shared across scorers at p of about 0.07.

The cross-family results are disclosed in `RESULTS.md` as their own
subsection. The headline framing in both `README.md` and `RESULTS.md`
is rewritten. The substantive claim narrows to "the patent's specified
pipeline produces vendor-dependent demographic outcomes that its
specified mitigation does not close," not per-cell statistical
significance.

**Bias-mitigator code review and audit-1 reframing.** A second pass
of methodology audit (using two parallel reviewer agents focused on
the bias-mitigator implementation and on Audit 1's experimental
design) surfaced four classes of issue:

- Three substitution pairs in `mitigator/semantic_substitution.py`
  changed propositional content rather than just connotation, which
  violates Claim 1's "preserve semantic structure" requirement:
  `voluntary -> approved`, `personal reasons -> approved reasons`,
  `despite -> with`. Plus `completed -> successfully completed`,
  `overcame -> managed`, and `struggled -> worked through` add or
  weaken factual claims. All six pairs were removed. Documentation
  in `DEFAULT_SUBSTITUTIONS` now lists them as deliberately excluded
  with the rationale.
- Five performance-descriptor pairs (`dedicated`, `diligent`,
  `meticulous`, etc.) collapsed to a single token (`high-performing`),
  erasing real semantic distinctions and creating spurious textual
  identity post-substitution. Each is now mapped to a distinct
  neutral term (`committed`, `thorough`, `detail-oriented`, etc.).
- A small case-sensitivity bug in `SCHOOL_PATTERNS` (the only regex
  pass without `re.IGNORECASE`) was fixed.
- A mutable-default-argument pattern in `SemanticSubstituter.__init__`
  was fixed by copying the default dict explicitly.

The audit-1 experiment was reframed in `RESULTS.md` and in the
runner's docstring. The prior framing ("Bias Mitigator efficacy")
overstated what the experiment can test. With `examples/example_pipeline.py`
(VADER) as the `pipeline_fn`, the mitigator's targets (names, schools,
locations, ethnicity terms) are largely invisible to the scoring step,
and a null Delta DI does not establish mitigation efficacy. The
revised framing makes this explicit: Audit 1 is a sanity check that
the mitigator runs end-to-end against any user-supplied
`pipeline_fn`, not a Claim-1 efficacy test. Substantive mitigation
testing lives in `tools/counterfactual_decomposition.py` against the
LLM PS extractor. A new function (`paired_permutation_test_delta_di`)
was added to `audit/screening.py` and wired into `tools/run_audit_1.py`,
which now reports a paired-permutation p-value for the Delta DI per
axis (under the null of pre/post score exchangeability). Audit 1 was
re-run on the n=384 corpus with the revised mitigator; the per-axis
Delta DIs are now 0.000 / 0.000 / -0.092 (gender / race /
school_tier) with paired-perm p-values of 1.00 / 1.00 / 0.52 — i.e.,
no systematic effect of the mitigator on VADER scores at this sample
size, which is the expected outcome for the reasons in the reframed
discussion.

**AI assistance disclosure.** The methodology revisions, code
changes, and prose edits in this iteration cycle were drafted with
Claude (Anthropic) as a coding and writing collaborator. Each commit
carries a `Co-Authored-By: Claude Opus 4.7` trailer. The substantive
decisions, the cross-family check, the framing pivots, the
disclosure choices, and the responses to peer review are mine. The
collaboration pattern is the same one used during the original repo
build (see the README's positioning paragraph).

## 2026-05-04 — Initial public release

Released alongside the WIRED article on algorithmic fairness in
residency screening. The toolkit at release included AIF360-style
fairness metrics, the patent's Claim 1 input-side bias mitigator, the
patent's col. 10 four PS-question extractor (SBERT and LLM variants),
the patent's §530 power-of-2 aggregation, a synthetic stratified PS
corpus generator, audit harnesses for Audit 1, Audit 2, content
equivalence, and counterfactual decomposition, screening simulation
tools, dilution and disclosure sweeps, paragraph audits, and
publication-grade plot scripts for every CLI tool. Reference outputs
from a representative run on a 192-PS corpus generated with
`gpt-5-mini` were committed to `examples/reference_outputs/`.
RESULTS.md framed per-cell findings under one scoring family and
described "direction-consistency across two corpus sizes and two
scoring models," a framing the cross-family check on 2026-05-05
narrowed to "vendor-dependent demographic outcomes." The new framing
is what the repo currently reflects.
