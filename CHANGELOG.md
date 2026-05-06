# Changelog

A record of substantive methodology revisions made after the initial
public release. Anyone reading the current state of the repo can
reconstruct how it got here without spelunking through git log.

The commit history is not squashed. Every change is recoverable.

## 2026-05-06 (OSF registration completed) — External pre-registration timestamp

The confirmatory-study pre-registration committed at `de8c291` was
deposited on the Open Science Framework and made publicly available:

- OSF registration: https://osf.io/vwyjm/
- OSF parent project: https://osf.io/uk6xn/

The full pre-registration document was pasted into the registration
description; the document and the locked substitution table were
also uploaded as registered files. Public release was set to
immediate (no embargo), so the methodology is third-party-timestamped
and publicly accessible from the OSF deposit independent of this
repository.

`CONFIRMATORY_STUDY_PREREG.md` updated with the OSF URLs in the
"External pre-registration" section (was a forward-looking
placeholder; now records actual completion).

This is the closing v1 commit. Execution of the pre-registered
analysis lives in `CONFIRMATORY_RESULTS.md`, not yet created.

## 2026-05-06 (confirmatory study pre-registration) — Phase 2 sealed before data collection

A pre-registration document for the confirmatory follow-up study
is committed at `CONFIRMATORY_STUDY_PREREG.md` alongside the locked
substitution table at `confirmatory/school_substitution_table.json`.

The pre-registration commits, in advance, to a single primary test
of the v1 audit's surviving school_tier × academic_career signal:
a tier-aware school-name substitution applied to the locked n=384
fresh corpus, followed by re-scoring with the gpt-4o-mini LLM
extractor, followed by a two-sided permutation test of the
post-substitution disparate impact at α = 0.05 with 10,000
permutations.

Decision rule (sealed before any data is generated):

- **H1 supported** (signal is school-name-driven) if post-
  substitution DI ≥ 0.80.
- **H0 supported** (signal robust to name substitution) if
  post-substitution DI < 0.80 with permutation p ≤ 0.10.
- **Ambiguous** if post-substitution DI in [0.65, 0.80) with
  permutation p > 0.10. Reported transparently with no claim of
  confirmation.

The substitution table preserves each PS's school_tier signal via
tier-encoded placeholders (`[TIER1_SCHOOL]`, `[TIER2_SCHOOL]`,
`[TIER3_SCHOOL]`), so the LLM extractor still receives tier
information; only the specific institutional name is removed. The
intervention is symmetric across tiers and addresses the asymmetry
in v1's `mitigator/anonymization.py` short-name list.

This pre-registration converts the v1 audit's post-hoc-narrowed
substantive claim into a confirmatorily-testable hypothesis with a
sealed analysis plan. Whatever the result, it will be reported.
External supplementary pre-registration on the Open Science
Framework and a Wayback Machine snapshot of the commit URL are
planned post-commit; the GitHub commit timestamp itself is the
primary registration timestamp.

This is the last v1-repository commit relating to substantive
methodology. Execution of the pre-registered analysis lives in
`CONFIRMATORY_RESULTS.md` (not yet created).

## 2026-05-06 (full fresh-corpus reproduction + provenance appendix) — End-to-end replication and reviewer-suggested follow-ons

A clean fresh-corpus reproduction of the full audit chain was run on
the existing repo state, generating a new n = 384 corpus from scratch
with `gpt-4o-mini` and re-running every audit (Audit 1 VADER + Claim 1
mitigator, Audit 2 SBERT, Audit 2 LLM, rebootstrap with 10,000 perms
on both extractors, counterfactual decomposition with paired-perm,
content equivalence). Total cost ~$3 in API; total wall ~1 hour
46 minutes including a one-hour corpus generation step. Reference
outputs preserved in
[`examples/reference_outputs/audit_2_repro/`](examples/reference_outputs/audit_2_repro/).

**Headline cells, fresh vs canonical:**

| Cell | Canonical | Fresh repro | Direction holds? |
|---|:---:|:---:|:---:|
| LLM × academic_career × school_tier | DI 0.650, p 0.059 | DI 0.698, p 0.069 | yes |
| LLM × `_total` × school_tier | DI 0.673, p 0.062 | DI 0.807, p 0.238 | yes (significance softens) |
| SBERT × academic_career × school_tier | DI 1.242, p 0.176 | DI 1.013, p 1.000 | no |
| Audit 1 (VADER) school_tier Δ DI | −0.092, p 0.518 | −0.143, p 0.170 | yes (null) |
| Content-equivalence ratio | 0.637 | 0.645 | yes |

**What the reproduction confirms.** The headline LLM-extractor finding
(`academic_career × school_tier` at DI ≈ 0.65, uncorrected p ≈ 0.06)
direction-replicates with similar magnitude. Race-axis and gender-axis
cells stay null on the fresh draw, confirming the post-tie-break-fix
picture. Corpus design properties (within-seed cosine drift smaller
than across-seed drift, ratio ≈ 0.64) are essentially identical
across draws. Audit 1 reproduces the expected null effect of the
mitigator on a sentiment-only pipeline.

**What the reproduction softens or dissolves.**

- The `_total` × school_tier aggregate signal moved from borderline
  (canonical p = 0.062) to null (fresh p = 0.238). The per-question
  signal carries; the §530 power-of-2 aggregate is more sensitive to
  corpus draw than the per-question driver.
- The earlier "cross-extractor disagreement" framing rested on
  canonical SBERT showing academic_career × school_tier in the
  *opposite* direction (DI 1.242, p 0.176). The fresh repro shows
  DI 1.013, p 1.000 — no signal at all. Other SBERT cells flip
  direction across the two corpora. SBERT registers corpus-draw
  noise rather than a stable opposite-direction signal. The honest
  reading: SBERT shows no replicating signal on either corpus draw;
  the LLM-extractor signal is the only one that replicates.

The substantive claim narrows further in the same direction it has
been narrowing all along: the surviving finding is bounded to
LLM-extractor architectures, replicates across two LLM scoring
families, two LLM corpus generators, a content-neutral prompt rewrite,
and now two independent corpus draws. It does not appear in SBERT in
either direction. It does not survive multiple-comparisons correction.

**README "Provenance and prior inquiry" subsection added.** External
reviewer feedback during the day suggested making the audit's
documentary provenance explicit in the public README. A new subsection
under `## Why this is public` documents the cooperative-path-first
history: the DSAR submitted under New Hampshire's Privacy Act, two
narrow verbatim quotes of substantive representations made by a
representative of the patent assignee in the resulting correspondence,
the patent assignee's own publicly published Medicratic-integration
roadmap (with cycle-by-cycle targets through the 2027 ERAS season),
and the third-party *JAMA* Viewpoint (Bachina et al., 2026,
doi:10.1001/jama.2026.1993) reporting that Halsted-derived technology
is already deployed in Cortex via the Academic Interest Badge. The
company name is not used in the README body; identification flows
from the patent number and the publicly available citations.

**Limitations consolidated.** The "Known limitations and prospective
follow-ons" section that was hoisted to the top of the README earlier
in the day was merged with the existing end-of-doc Limitations section
into one block titled "Limitations and prospective follow-ons." The
early-placement was a timing artifact of receiving reviewer feedback
mid-flow; structurally the follow-ons belong with the technical
reader at the end of the doc. RESULTS.md "Cross-extractor observation"
section, "Substantive interpretation" subsection, and the README
plain-language section all updated to reflect the post-reproduction
reading.

## 2026-05-06 (content-neutral sensitivity test) — Signal robust to prompt-level intervention

The opt-in content-neutral prompt variant added in commit `9f940d8`
was run end-to-end. A second n = 384 corpus was generated with
gpt-4o-mini under the variant; Audit 2 LLM (gpt-4o-mini scorer) was
run; rebootstrap with 10,000 permutations gave the per-cell perm-p
values.

**Result: the school_tier × academic_career signal persists.**

| Prompt variant | DI (academic_career × school_tier) | perm-p |
|---|---:|:---:|
| original | 0.650 | 0.059 |
| content_neutral | **0.673** | **0.065** |

Essentially identical. The signal does not collapse when the corpus
prompt is rewritten to (a) remove the "research lab / faculty mentor /
institution-specific program" content cue from the top_20 school
description, and (b) explicitly instruct that academic register and
narrative sophistication be held constant across school tiers.

**Token-frequency follow-up.** The same diagnostic that identified
the original prompt-design effect was rerun against the content-
neutral corpus. Academic-register token density (research, lab,
faculty, mentor, scientist, ...) per 100 words by school_tier × seed:

| Seed | original prompt (top_20 ÷ lower_tier) | content_neutral prompt |
|---|:---:|:---:|
| control_neutral | 3.6× | 1.0× (essentially flat) |
| immigration_signal | 2.3× | 1.1× |
| poverty_signal | 2.0× | 2.2× |

So the corpus prompt was indeed shaping academic-register density
under the original prompt, and the rewrite successfully flattened it.
But the audit signal persisted unchanged when that density was
flattened. The LLM extractor is therefore reading something other
than literal academic-register token density.

**Most plausible remaining mechanism.** The school name itself
remains in the PS under both prompt variants — top_20 PSs still name
"Harvard," "Stanford," "Hopkins," "UCSF," etc.; the content-neutral
prompt asks the generator to "identify the school by name only." The
LLM extractor's training-data weights presumably associate those
specific names with academic content, and that association would be
unaffected by prompt-level intervention on the surrounding narrative.
This is consistent with the counterfactual decomposition finding
that marker-stripping (which removes school names) does not move the
academic_career × school_tier signal at the per-question level
(paired-perm p = 0.65).

**The substantive claim narrows in a more interesting direction.**
The surviving signal now resists *four* family/prompt-level
interventions:

| sensitivity test | signal survives? |
|---|---|
| cross-family LLM scorer (gpt-4o-mini ↔ claude-haiku-4-5) | ✓ |
| cross-family LLM generator (gpt-4o-mini ↔ claude-haiku-4-5) | ✓ |
| content-neutral prompt (no voice-variation, no research-cue) | ✓ |
| cross-extractor architecture (LLM ↔ SBERT) | ✗ |

It does not survive the architecture-level intervention. Strongest
defensible interpretation: under the patent's specified col. 10 LLM-
extractor architecture, the LLM associates specific top_20 school
names with academic content in a way that produces a borderline
school_tier × academic_career disparity at uncorrected p ≈ 0.06.
That association is robust to prompt-level corpus-design choices.
It does not survive multiple-comparisons correction; it does not
hold under SBERT exemplar-cosine scoring. The disparity is real
LLM-extractor behavior on this corpus, not a same-LLM-family
generator artifact and not a prompt-level voice-variation artifact.

**Independent code-review feedback (acknowledged).** A reviewer
flagged `audit/metrics.py:threshold_sweep` as still using stable-
sort tie-break (the same footgun fixed in `audit/screening.py:top_k_selection`
on 2026-05-06). The function is exported from `audit.__init__` as a
public API but has no internal caller; downstream users could hit
the bug. Now uses seeded random tie-break via `numpy.lexsort`,
matching the screening fix; takes a `tiebreak_seed` parameter.

The same reviewer flagged that `tools.smoke_test` requires
downloading the SBERT model from Hugging Face on first run, and
fails in offline sandbox environments. Addressed in this commit by
adding an offline-only smoke path (`--offline`) that skips the SBERT
load and exercises only the BiasMitigator + axis_audit code paths
(no model download, no API key, deterministic).

## 2026-05-06 (forensic audit batch) — Pre-flip cleanup pass

Three parallel forensic agents reviewed (a) the algorithmic code paths
that had not been audited (`tools/run_dilution_test.py`,
`tools/run_paragraph_audit.py`, `tools/content_equivalence.py`,
`ps_extraction/llm_extractor.py`, `ps_extraction/extractor.py`,
`audit/metrics.py`), (b) doc consistency between RESULTS.md / README.md
and the canonical reference outputs, and (c) operational + risk
surface (smoke test, plot scripts, seeds, secrets, file paths).

### High-severity fixes (public-facing)

- **`RESULTS.md` paragraph audit table sign error**: leave-of-absence
  RoBERTa transformer score was reported as `+0.04`. Canonical JSON
  has `-0.0389` — the value is negative. RESULTS.md now reads `−0.04`.
- **`RESULTS.md` content-equivalence pair count error**: within-seed-
  across-stratum pairs reported as 17,856. Canonical JSON has 17,664
  (the 17,856 figure was the stale n=192 calculation that was never
  refreshed when the corpus grew to n=384). RESULTS.md now reads
  17,664.
- **`RESULTS.md` reproduction commands using stale model**: the n=384
  reproduction block at the end of RESULTS.md still passed
  `--llm-model gpt-5-mini` for both Audit 2 LLM and counterfactual
  decomposition. The canonical n=384 reference outputs were generated
  with `gpt-4o-mini`. Following RESULTS.md literally would not have
  reproduced the numbers it reports. Both commands now pass
  `gpt-4o-mini`. The counterfactual reproduction command also now
  passes `--n-permutations 10000` so it produces the paired-perm
  cells RESULTS.md cites.
- **`README.md` Limitations section using stale n=192 cosine numbers**:
  the synthetic-corpus content-equivalence numbers (0.253 / 0.411 /
  0.615) were from the n=192 robustness check. Canonical n=384 values
  are 0.215 / 0.337 / 0.637; README now uses those.
- **`DEVIATIONS_FROM_PATENT.md` substitution table out of date**: the
  doc still listed five substitution categories (communal/agentic,
  performance-descriptor, leave-of-absence, hedge-language,
  concession-framing), with the performance-descriptor pairs all
  collapsing onto `→ high-performing`. The current
  `DEFAULT_SUBSTITUTIONS` table has TWO categories with ten distinct
  connotation-only pairs; the three removed categories were excised
  on 2026-05-05 / 2026-05-06 after the methodology audit found they
  changed propositional content rather than just connotation, and the
  performance-descriptor mappings were remapped to distinct neutral
  terms (`→ thorough`, `→ committed`, `→ detail-oriented`,
  `→ effective`). The doc is rewritten to match current code; the
  removed categories are explicitly listed as "intentionally NOT
  included" with the rationale.
- **`examples/reference_outputs/dilution_test/dilution_test_results.json`
  contained the literal token `NaN`** — invalid per RFC 8259, rejected
  by strict JSON parsers (including Python's `json.loads` if `parse_constant`
  isn't customized). The committed reference file was stale; manually
  replaced with `null`. (The tool itself was *not* serializing NaN as
  null correctly — `json.dump` defaults emit the literal `NaN` token.
  That tool-level bug was fixed in the 2026-05-06 Phase-4 commit
  below; both the canonical reference file and any future dilution-
  test runs are now strict-JSON-compliant.)

### Medium- and low-severity fixes

- `audit/metrics.py:model_suite_summary` was reading the key
  `disparate_impact` from the nested metrics dict, but
  `disparity_summary` emits `selection_rate_ratio_group0_over_group1`.
  Every call returned None for every DI field. Function now reads the
  emitted key with a fallback for callers that pass a different shape.
- `tools/run_dilution_test.py` multi-Anthropic-instrument config bug:
  `inst.startswith("llm_judge_anthropic")` resolved to a single shared
  `llm_judge_anthropic_model` config slot, making it impossible to
  configure two Anthropic instruments at different models in one run.
  Fixed with per-instrument-name lookup that falls back to the
  provider-level default. Same fix for the OpenAI variant.
- `tools/run_paragraph_audit.py:unanimous_lowest` was returning True
  for single-instrument runs (one instrument cannot be unanimous
  across instruments). Now requires `len(instruments) >= 2`.
- `ps_extraction/__init__.py` and `ps_extraction/extractor.py`
  module docstrings claimed SBERT extractor scores were in `[0, 1]`.
  The actual range is `[0, ∞)`. Corrected; LLM extractor's [0, 1]
  range is also documented for contrast.
- `DEVIATIONS_FROM_PATENT.md` line 216 internal inconsistency
  (gpt-5-mini default vs gpt-4o-mini in line 135) clarified: the
  code-level default is gpt-5-mini, but the canonical n=384 reference
  outputs were generated with `--llm-model gpt-4o-mini` (the n=192
  robustness check used gpt-5-mini).

### Operational / risk surface — clean

- `.env.example` is a template (no real keys committed); repo-wide
  grep finds no leaked API keys, tokens, or credentials.
- Seeds are plumbed throughout (`tiebreak_seed`, `bootstrap_seed`,
  `permutation_seed`); deterministic given a fixed seed.
- Plot scripts contain no stale `gpt-5-mini` references that would
  appear in figure titles.
- `tools/smoke_test.py` runs end-to-end and exits 0.
- All `examples/reference_outputs/*` paths referenced in RESULTS.md
  resolve on disk.

### Findings that turned out to be wrong on re-verification

- An agent flagged `tools/content_equivalence.py:186-192` as having
  "two independent if blocks rather than if/elif/else" with broken
  boundary behavior. The code is actually a chained ternary; boundary
  behavior is intentional (ratio = 0.7 and 0.9 both fall in the
  "Marginal" gray zone). No fix.
- An agent flagged `ps_extraction/extractor.py:96` docstring as
  saying `[0, 1]`. The function docstring already says `[0, ∞)`.
  The stale claim was at the module-level docstring (line 3 of the
  same file) and at `ps_extraction/__init__.py:14`; those were the
  ones fixed.

## 2026-05-06 (continued) — Prompt-design diagnostic, cross-extractor disagreement, doc freshness

After the cross-generator validation landed, a closer audit of the
corpus generator surfaced that the corpus prompt itself is encoding
school-tier-correlated content beyond the school name. Two locations
in `synthetic/ps_generator.py`:

- `SCHOOL_TIER_DESCRIPTIONS["top_20"]` (lines 109–115): includes the
  directive "the school cue should be subtle (a research lab, a
  faculty mentor, an institution-specific program), not a brag." The
  mid_tier and lower_tier descriptions don't have an analogous content
  directive.
- The `PROMPT_TEMPLATE` writing-style instruction (line 97) tells the
  generating LLM to "Adopt a stylistic voice plausible for the
  assigned profile. Vocabulary register, sentence cadence, and
  narrative framing should differ across profiles even when content
  is identical."

A token-frequency diagnostic on the existing gpt-4o-mini and
claude-haiku-4-5 corpora confirms the hypothesis. In seeds where
ground truth says NOT pursuing academic career (control_neutral,
immigration_signal, poverty_signal), top_20 PSs contain academic-
register tokens (research, lab, faculty, mentor, scientist, PhD,
manuscript, …) **1.4× to 3.6× more often** than lower_tier PSs.
The illness_signal seed is balanced across tiers because the seed
itself dictates academic content. Ratio summary by (generator × seed):

| generator | seed | top_20 / lower_tier density ratio |
|---|---|---:|
| gpt-4o-mini | control_neutral | 3.6× |
| gpt-4o-mini | immigration_signal | 2.3× |
| gpt-4o-mini | poverty_signal | 2.0× |
| claude-haiku-4-5 | control_neutral | 1.9× |
| claude-haiku-4-5 | immigration_signal | 1.4× |
| claude-haiku-4-5 | poverty_signal | 1.9× |

Both generators comply with the prompt's voice-variation directive in
roughly the same direction (top_20 voice = more academic register).
The cross-generator survival of the academic_career × school_tier
audit signal is consistent with this design effect: both generators
write the content the LLM extractor then reads.

The audit's substantive claim about the surviving signal is narrowed
again. From "real LLM behavior on academic-narrative content" the
framing becomes "the LLM extractor is reading academic-register
content the corpus generator wrote in response to the audit prompt's
voice-variation directive."

**Sensitivity test in flight.** A new opt-in
`--prompt-variant content_neutral` flag was added to
`tools/generate_ps_corpus.py` (commit `9f940d8`). The variant uses
parallel school-name-only descriptions across tiers, removes the
research-lab content cue from top_20, and explicitly forbids
academic-register variation across school tiers. Generating a
content-neutral corpus with gpt-4o-mini and re-running Audit 2 LLM
will determine whether the school_tier × academic_career signal is a
prompt-design artifact (predicted: DI moves toward parity) or robust
to prompt design.

**Cross-extractor disagreement on the surviving cell.** Cross-
referencing the canonical Audit 2 outputs surfaces a previously
unhighlighted finding: SBERT and the LLM extractor disagree on
*direction* on the only cell that comes close to significance under
either:

| extractor | academic_career × school_tier DI | perm-p |
|---|---:|---:|
| LLM (gpt-4o-mini) | 0.650 | 0.059 |
| SBERT | 1.242 | 0.18 |

LLM reads top_20 PSs as more academic_career-leaning; SBERT reads
the lower-resource group (combined lower_tier + mid_tier) as more
academic_career-leaning. Same corpus, opposite directions. RESULTS.md
"Cross-extractor observation" section is rewritten to surface this
explicitly. The audit's surviving claim is now bounded to LLM-
extractor architectures specifically.

**Doc freshness pass:**

- `RESULTS.md`: SBERT section wording bug at line 217 fixed (DI
  0.794 is just *outside* the 4/5 lower bound, not inside).
- `RESULTS.md`: cross-extractor section rewritten to reflect the
  post-tie-break-fix LLM findings (was still citing the stale
  pre-fix major_illness × race / refugee × race cells).
- `RESULTS.md`: substantive interpretation extended to note that
  the surviving signal is architecture-dependent and only holds
  under the LLM extractor.
- `README.md`: plain-language section's "what happens when you run
  it" bullets updated for paired-perm framing on the mitigator,
  the cross-extractor disagreement, and the prompt-design effect.
- `README.md`: screening-simulation paragraph rewritten to
  distinguish fitted from oracle scoring rules (matching the
  RESULTS.md fix from earlier today).
- `tools/run_disclosure_sweep.py`: `--model` argparse now has a
  `choices=` constraint to match the screening-counterfactual
  runner; `--narrative-sd` help text clarifies that this tool's
  default 0.3 differs from the screening-counterfactual default
  0.10.

## 2026-05-06 (end of day) — Cross-generator validation of the school_tier signal

The cross-family scoring check from 2026-05-05 varied the scorer
(gpt-4o-mini vs claude-haiku-4-5) but held the generator constant at
gpt-4o-mini. The "possible generator confound" caveat in RESULTS.md
flagged this gap explicitly. To close it, a second n = 384 corpus was
generated with claude-haiku-4-5 using the same stratified design,
then audited with both scorers. The full 2 × 2 generator × scorer
table for academic_career × school_tier:

| Generator | Scorer | DI | perm-p |
|---|---|---:|:---:|
| gpt-4o-mini | gpt-4o-mini | 0.650 | 0.059 |
| gpt-4o-mini | claude-haiku-4-5 | 0.673 | 0.062 |
| claude-haiku-4-5 | gpt-4o-mini | 0.698 | 0.071 |
| claude-haiku-4-5 | claude-haiku-4-5 | 0.750 | 0.131 |

Direction-consistent across all four cells. Magnitudes weaken under
the haiku-generated corpus (0.70/0.75 vs 0.65/0.67) and uncorrected
significance softens to borderline at the both-flipped cell, but the
qualitative pattern is robust. A pure generator confound would have
predicted the signal disappears when the generator changes; it does
not.

The narrowed interpretation in RESULTS.md: both LLM families write
more academic narrative into top-20 PSs *and* both LLM families read
it. This is real LLM behavior on academic-narrative content, not an
artifact of who generated the corpus. The audit still cannot
distinguish "shared LLM tendency learned from real-world
correlations in training data" from "authentic content variation the
LLMs are reading"; for that the corpus would need to be generated
without LLM involvement at all.

The `_total` (§530 power-of-2 aggregation) signal does not transfer
across families: it appears only in the same-family gpt-4o-mini gen
+ gpt-4o-mini scorer cell (DI 0.673, p 0.062) and is at parity in
all three cross-family cells. The aggregate finding was over-stated;
the per-question finding carries.

Reference outputs:
`examples/reference_outputs/audit_2_crossgen/audit_2_haikugen_gptscore.json`
and `audit_2_haikugen_haikuscore.json`. The new corpus
(`synthetic/data/ps_corpus_haiku_gen.jsonl`) is gitignored along
with the gpt-4o-mini corpus per the existing repo policy; both are
regenerable from the seeds.

## 2026-05-06 (later that day) — Post-fix validation pass and follow-on cleanup

A multi-agent validation pass on the post-tie-break-fix repo confirmed
the three remaining headline claims (school_tier × academic_career
cross-family signal, mitigation-failure observation, screening-
simulation findings). The pass surfaced a small set of follow-on
issues — none dissolved any finding, and several documentation gaps
between RESULTS.md and the published reference outputs were closed.

**Framing fix on the screening-simulation table.** RESULTS.md
previously said baseline DI sat outside the EEOC four-fifths range
"under every scoring method tested (linear, logistic regression,
patent §530 power-of-2 aggregation, power-of-3 aggregation)" and
that power-of-N "amplifies, rather than mitigates, the baseline
disparity vs. linear scoring." The first claim conflated the fitted
logistic-regression model with three oracle baselines that apply
the data-generating betas at inference; for those three, the DI is
arithmetic about the DGP assumptions, not an empirical algorithm
test. The second claim is also wrong for `instrument_b_transformer`,
where cubic DI = 0.439 is *less* disparate than linear DI = 0.302.
RESULTS.md now distinguishes fitted from oracle scoring rules and
reports the actual baseline-DI range (0.000 to 0.303 across cells).

**Counterfactual decomposition rebuilt with paired-permutation
support.** The `paired_permutation_test_delta_di` function existed
in `audit/screening.py` and was wired into Audit 1, but
`tools/counterfactual_decomposition.py` never called it; the
"barely moves" / "moves notably toward parity" framing had no
inferential backing. The tool now computes a paired-permutation
p-value per (question × axis) cell under the null of pre/post
score exchangeability per applicant. The reference output JSON was
recomputed from cached scores (no fresh LLM extraction needed) under
the post-fix tie-break and now ships with paired-perm p-values.

The new numbers give the surviving framing real support:
- academic_career × school_tier: DI 0.650 → 0.673, paired-perm
  p = 0.65 (not statistically distinguishable from no effect — the
  signal is content-driven, marker-stripping does not move it).
- `_total` × school_tier: DI 0.673 → 0.807, paired-perm p = 0.015
  (the aggregate signal does mitigate at conventional significance,
  even though its single-question driver does not).

**Public reference-output JSON normalization.** Both
`examples/reference_outputs/audit_1/audit_1_results.json` and
`examples/reference_outputs/counterfactual/counterfactual_decomposition.json`
were silently overwritten in an earlier session with `rebootstrap.py`-
style outputs that lack the paired-permutation results those tools
produce. The published canonical files now contain the full
run-tool outputs (including paired-perm cells); the prior
rebootstrap-style schema can still be regenerated by anyone who
runs `tools/rebootstrap.py`. Figures regenerated to match.

**Three remaining evaluative-escalation substitutions removed from
the default mitigator table.** The 2026-05-05 cleanup removed six
substitution pairs that changed propositional content. A second
pass identified three more in the same structural category:
`satisfactory → strong`, `acceptable → strong`,
`competent → highly competent`. Each escalates the evaluative
magnitude of the source text. Removed and documented in the
"intentionally NOT included" comment block alongside the prior six.
The cached counterfactual scores predate this removal; the
school_tier × academic_career and `_total` × school_tier headline
numbers above are unchanged because these substitutions affect
performance-evaluation language, not the academic-narrative content
the LLM extractor reads. A fresh LLM-extractor pass would produce
slightly different stripped scores; users who care can re-run.

**SCHOOL_PATTERNS character-class fix.** The leading character class
in the generic `[A-Z][a-zA-Z]+ (?:School of Medicine|...)` pattern
in `mitigator/anonymization.py` did not honor `re.IGNORECASE`;
sentence-initial lowercase institution prefixes survived the strip
pass. Changed to `[A-Za-z]` with an inline comment.

**`_percentile_ci` documentation.** `audit/screening_simulation.py`
and `audit/bootstrap.py` use `np.median` for the displayed point
estimate and `np.quantile` for percentile CI bounds. For highly
skewed bootstrap distributions this can in principle put the
displayed point outside the displayed CI; in practice no cell in
the canonical screening-simulation reference output has this
property. Docstrings now explain the choice and direct users
handling skewed distributions to the alongside `mean` field.

**Tie-break safety comments.** Both `audit/screening_simulation.py`
and `tools/run_screening_with_counterfactual.py` retain
`np.argsort(-proba, kind="stable")`. The comment now records the
argument that this is safe in the simulation context (group is
randomly assigned via `rng.integers(0, 2)` so corpus order is
uncorrelated with group membership), distinguishing it from the
bug fixed in `audit/screening.py` where the corpus was
stratum-blocked.

**`run_screening_simulation.py` now exposes
`quadratic_aggregation` and `cubic_aggregation`** as `--model`
choices, matching `run_screening_with_counterfactual.py`. CLI help
flags them as oracle baselines that apply DGP betas at inference,
not fitted models.

**Silent NaN-merge guard in `counterfactual_decomposition.py`.**
If `--original-scores` applicant IDs do not match the corpus,
the left-join now warns to stderr with the count of unmatched
rows rather than silently propagating NaN through the audit.

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
