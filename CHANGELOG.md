# Changelog

A record of substantive methodology revisions made after the initial
public release. Anyone reading the current state of the repo can
reconstruct how it got here without spelunking through git log.

The commit history is not squashed. Every change is recoverable.

## 2026-05-06 — Tie-break bug discovered and fixed; substantive claims narrowed

A second-round validation pass on the surviving headline claims
(vendor-dependence, mitigation-failure observation, screening-
simulation findings) surfaced a real bug in the audit's selection
function. The bug had been silently inflating the gpt-4o-mini per-cell
race-axis findings.

**The bug.** `top_k_selection` in `audit/screening.py` used
`numpy.argsort(..., kind="stable")` to pick the top fraction of
applicants by score. Stable sort preserves original array order at
ties. When the LLM extractor produces near-discrete scores (under
gpt-4o-mini, the major_illness question takes only the values 0.0
and 1.0; refugee takes four values), top-K=0.30 selection at n=384
forces the threshold inside a tied block at the boundary. The 19
zero-scoring applicants who get selected as ties are pulled in
original corpus order, which on a stratum-blocked corpus biases the
tie-break toward whichever stratum the corpus happens to list first.

**The empirical effect.** For the major_illness question, all 24
illness-seed PSs in each race stratum scored 1.0 and all 72
non-illness PSs in each race stratum scored 0.0. Selection rates per
race were perfectly balanced at 0.250 by content. The 19 tie-broken
zero-scorers all came from the White stratum because White was
listed first in the non-illness seeds. White selection rate became
(24+19)/96 = 0.448; non-White stayed at 24/96 = 0.250. Reported DI:
0.558. Reported permutation p-value: 0.029. Under random shuffle of
the same data, DI ranges 0.83–1.09 (mean 0.97). The "finding" was an
artifact of corpus row order interacting with stable-sort
tie-breaking.

**The fix.** `top_k_selection` now uses seeded random tie-breaking
(`numpy.lexsort` with a deterministic random secondary key from
`np.random.default_rng(tiebreak_seed)`). Documented inline. All
audit harnesses pick up the fix transparently.

**Headline claims that did not survive the fix.**

- The "vendor-dependence" framing introduced on 2026-05-05 was built
  on race-axis cells whose magnitudes were largely artifactual.
  Under fixed tie-break, gpt-4o-mini shows no race-axis cell at
  uncorrected p < 0.10 (highest p among race cells = 0.20 for refugee
  × race, DI = 0.762). The cross-family non-replication is therefore
  not a real LLM-disagreement finding; the prior gpt-4o-mini cells
  were mostly noise sitting in tie-break artifact.
- "The patent's mitigation does not close the gap" remains
  *partially* supported under the fix (academic_career × school_tier
  barely moves after marker-stripping; `_total` × school_tier moves
  notably toward parity), but the strong race-axis version of the
  claim that appeared in the 2026-05-05 commit history was based on
  artifact cells.

**Headline claims that survive the fix.**

- A borderline cross-family-consistent school_tier finding:
  academic_career × school_tier under gpt-4o-mini DI = 0.650
  (p = 0.059); under claude-haiku-4-5 DI = 0.673 (p = 0.062). Both
  LLMs assign higher academic_career scores to top-20 school
  applicants than to lower-resource ones, at very similar
  magnitudes. This is the only cell shared at borderline significance
  across both scorers. It does not survive multiple-comparisons
  correction. It may reflect a generator confound: the corpus was
  generated with gpt-4o-mini, and if that generator wrote top-20 PSs
  with more academic-leaning narrative content, both scorers would
  consistently pick that up.
- The screening-simulation findings (synthetic n = 6,000 applicants
  with sentiment-anchored disparities, recovery-to-parity under
  sentiment-only counterfactual) are unaffected by the bug because
  the simulation uses logistic-regression / linear / quadratic /
  cubic scoring on continuous features, not near-discrete LLM
  outputs.
- Audit 1 (VADER pipeline + Claim 1 mitigator) is unaffected because
  VADER produces continuous scores. Audit 2 SBERT is unaffected for
  the same reason.

**The methodological-pitfall finding itself**, surfaced and fixed
publicly, is its own contribution. Any AEDT audit using top-K
selection on LLM-extractor outputs that cluster at endpoints needs to
account for tie-break behavior. Stable sort plus stratum-blocked
corpus row order plus near-discrete scores produces spurious DI
findings.

`RESULTS.md` was rewritten to reflect the corrected picture:
restated Audit 2 LLM tables with FIXED numbers, restated the
cross-family section with the corrected interpretation, added a
"discrete-score tie-break" methodological note. README plain-language
"What happens when you run it" was rewritten to drop the
"vendor-dependent demographic outcomes" headline and to acknowledge
the generator-confound risk on the surviving school_tier signal.
`examples/reference_outputs/` JSONs and figures refreshed.

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
