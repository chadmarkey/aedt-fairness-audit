# Confirmatory Study Pre-Registration

**Status:** Pre-registration. Data collection has not commenced.
**Pre-registration date:** 2026-05-06
**Pre-registration venue:** Public commit to this repository's `main`
branch. External pre-registration on the Open Science Framework
(`osf.io`) and a Wayback Machine snapshot of this commit's GitHub URL
are recommended supplementary timestamps; both are noted at the end
of this document and are completed by the author after the
pre-registration commit lands.

**Author:** Chad Markey (chad.markey11@gmail.com)

## 1. Purpose

This document specifies, in advance, the design and analysis plan
for a confirmatory follow-up to the v1 audit (toolkit released
2026-05-04 and refined through 2026-05-06; commit history visible
in this repository).

The v1 audit reported a borderline LLM-extractor finding —
academic_career × school_tier at DI ≈ 0.65 (uncorrected p ≈ 0.06)
— that direction-replicated across two LLM scoring families, two
LLM corpus generators, a content-neutral corpus prompt rewrite, and
an independent fresh corpus draw. The finding does not survive
multiple-comparisons correction and was selected post-hoc from a
30+ cell Audit 2 grid. SBERT does not register the signal in either
direction across the two corpus draws.

The v1 audit's substantive interpretation is that the LLM extractor
reads "top-20 medical school" — likely the specific school names
that remain in each PS — and associates those names with academic
content, regardless of corpus prompt design. This interpretation
has not been confirmatorily tested.

This pre-registration commits to a single primary test that
distinguishes the school-name-association hypothesis from
alternatives. The test is implementable on existing data,
statistically pre-specified, and sealed at this commit.

## 2. Hypotheses

**H1 (school-name-association mechanism):** Under the gpt-4o-mini
LLM extractor, the academic_career × school_tier disparate-impact
signal is driven by associations the LLM holds between specific
top-20 medical school names ("Harvard," "Stanford," "Hopkins,"
"UCSF," etc.) and academic-career narrative content. Under H1,
replacing those school names with neutral tier-encoded placeholders
collapses the signal.

**H0 (signal robust to name substitution):** The signal is not
driven by school-name associations. Replacing school names with
tier-encoded placeholders does not substantially move the DI.

## 3. Primary intervention

**School-name substitution.** A deterministic, *symmetric, tier-
aware* mapping is applied to every PS in the locked corpus before
LLM scoring. The substitution preserves each PS's school-tier
signal while removing the specific school name.

The full substitution specification is locked at
[`confirmatory/school_substitution_table.json`](confirmatory/school_substitution_table.json)
(committed alongside this pre-registration). Highlights:

- Per-PS, tier-aware: each PS's `stratum.school_tier` value (from
  the corpus metadata) determines whether the placeholder is
  `[TIER1_SCHOOL]`, `[TIER2_SCHOOL]`, or `[TIER3_SCHOOL]`.
- Two substitution rules:
  1. A generic regex matching any `<Word(s)> School of Medicine /
     Medical College / College of Medicine / School of Osteopathic
     Medicine / University School of Medicine` phrase.
  2. A short-name list (Harvard, Hopkins, Stanford, UCSF, Yale,
     Columbia, Penn, Duke, Michigan, Washington University, Cornell,
     Dartmouth, Mayo, UCLA, Baylor, Tulane, Saint Louis, Albany,
     Wake Forest, Indiana, Iowa, Tennessee, Emory, Pritzker,
     Perelman, Meharry, Morehouse, Miami Miller, Virginia
     Commonwealth, VCU, Louisville, Boonshoft, Wright State, New
     Mexico, Rowan, Toledo, Wayne State, Incarnate Word) anchored
     to a medical-context cue within 80 characters, to avoid
     over-substituting state names like "Iowa" or city names like
     "Columbia" that do not refer to the school.

The substitution preserves the school-tier signal in the placeholder
itself: a top_20 PS still receives `[TIER1_SCHOOL]`, so the LLM
extractor knows the applicant attended a top-20 institution. What
the extractor cannot read after substitution is the specific
institutional identity (the LLM has training-data associations for
"Harvard" but not for "TIER1_SCHOOL"). This isolates whether the
audit's signal depends on the *name* specifically versus the *tier
label* in some other content-driven way.

## 4. Primary endpoint and decision rule

**Locked corpus:** the n=384 fresh-corpus reproduction at
`synthetic/data/ps_corpus_repro.jsonl`, produced 2026-05-06 with
gpt-4o-mini, frozen at this commit.

**Locked extractor:** gpt-4o-mini LLM extractor at temperature 0,
prompt template at `ps_extraction/llm_extractor.py:PROMPT_TEMPLATE`
as of this commit.

**Locked statistical test:** Two-sided permutation test of the
post-substitution DI on academic_career × school_tier under the
null of group-selection independence. **10,000 permutations.**
Top-K = 0.30 selection. Seeded random tie-break at
`tiebreak_seed=0`.

**Significance threshold:** α = 0.05. Single primary test;
no further multiple-comparisons correction needed beyond α=0.05.

**Decision rule:**

- **H1 supported** if post-substitution DI ≥ 0.80 (within EEOC
  four-fifths safe range). The signal collapses under name
  substitution; mechanism is school-name-association.
- **H0 supported** if post-substitution DI < 0.80 *and* permutation
  p ≤ 0.10. The signal substantially persists under name
  substitution; mechanism is something deeper than literal
  school-name association (e.g., a tier-label association, or
  surrounding-content patterns the audit has not isolated).
- **Ambiguous** if post-substitution DI in [0.65, 0.80) with
  permutation p > 0.10. Partial attenuation; reported transparently
  with no claim of confirmation in either direction.

The primary outcome is reported regardless of which decision-rule
branch the result falls into. There is no stopping for futility,
no adaptation, no re-running with different seeds.

## 5. Sample plan

This study uses the existing n=384 fresh-corpus reproduction. No
new corpus is generated for the primary test. The locked corpus
path and the locked substitution table together define the exact
input to the confirmatory analysis.

A hand-authored or template-based matched corpus to break LLM-on-LLM
dependency entirely is **out of scope** for this pre-registration.
Such a corpus is the natural Phase-2 follow-up and would require its
own separate pre-registration.

## 6. Pre-specified analyses

**Primary (one test):** §4 above.

**Secondary, exploratory (declared up front, not used to confirm
or refute H1):**

- Substitution effect on `_total × school_tier` aggregate.
- Substitution effect on per-question cells other than
  `academic_career`.
- Substitution effect under claude-haiku-4-5 scoring (cross-family
  robustness of whatever the primary test concludes).
- Sensitivity to placeholder design: re-run with placeholders that
  do *not* encode tier (e.g., `[SCHOOL_A]` regardless of tier), to
  test whether the LLM is reading the tier label itself rather than
  the specific name.

These are reported transparently. They are not used as confirmatory
tests of H1.

## 7. Code and methodology lock

The audit toolkit at the pre-registration commit (the commit that
adds this file) is the locked specification for the confirmatory
test.

Locked artifacts:
- `audit/screening.py` (top_k_selection, axis_audit, permutation
  test) at this commit.
- `ps_extraction/llm_extractor.py` (prompt template, parser) at
  this commit.
- `synthetic/data/ps_corpus_repro.jsonl` (the locked corpus). Note:
  this file is gitignored per repo policy on synthetic data, but
  is locally preserved and reproducible by deterministic regeneration
  from the documented seed and parameters in `examples/reference_outputs/audit_2_repro/`.
- `confirmatory/school_substitution_table.json` (the locked
  substitution mapping).

Any deviations between the locked specification and the executed
analysis will be explicitly documented in the eventual results
writeup, with reason for deviation and impact on inference.

## 8. Blinding

The LLM extractor is blinded to school identity by design under
this intervention: post-substitution PSs contain only tier-encoded
placeholders, not specific school names. The extractor receives
the same prompt template used in v1; the only difference is the
input text.

The analyst running the test is not blinded to condition (the
substituted vs. original corpus is known by file name and the
analyst is the author). This is a limitation of the design and is
noted explicitly. A fully blinded protocol would require a third
party to apply substitutions and shuffle ordering before the
analyst sees the data; that protocol is out of scope for this
single-author confirmatory study and would belong with the Phase-2
hand-authored corpus.

## 9. Out of scope (future work)

Listed for transparency. Not confirmatorily tested here:

- Hand-authored or template-based matched corpus (breaks LLM-on-LLM
  dependency entirely).
- Fully blinded analysis with third-party substitution and
  shuffling.
- Independent replication on a different machine and operator.
- Confirmatory tests under additional LLM extractor families.

These are the natural Phase-2 / Phase-3 moves. Each would require
its own pre-registration before execution.

## 10. Stopping rule

The confirmatory analysis is complete after a single execution of
the pre-specified primary test on the locked corpus with the locked
substitution table. Re-running with seed variation is out of scope;
the seeded random tie-break produces deterministic output at fixed
seed.

## 11. Known v1 limitations addressed by this pre-registration

The v1 audit's `mitigator/anonymization.py` short-name list is
asymmetric across tiers (an explicit short-name list for top_20
schools, no analogous list for mid_tier or lower_tier; both rely
on the generic regex pattern). The asymmetry is documented in the
v1 README's Limitations and prospective follow-ons section. The
confirmatory test's substitution table at
`confirmatory/school_substitution_table.json` is symmetric across
all three tiers and supersedes the v1 anonymizer for the purposes
of this study.

## 12. Authorship and commitment

I, Chad Markey, commit to executing this analysis as specified,
reporting all results regardless of outcome, and explicitly noting
any deviations from this pre-registered plan. The actual analysis
runs only after this document is committed to the repository's
public `main` branch.

Contact: chad.markey11@gmail.com.

---

## External pre-registration (completed 2026-05-06)

The pre-registration has been deposited on the Open Science
Framework (`osf.io`) and is publicly accessible:

- **OSF registration:** <https://osf.io/vwyjm/>
- **OSF parent project:** <https://osf.io/uk6xn/>
- **Underlying GitHub commit:** `de8c291` on `main` of
  <https://github.com/chadmarkey/aedt-fairness-audit>

The OSF registration was filed under the "Open-Ended Registration"
template with public release set to immediate (no embargo). The
contents of this document were pasted in full into the registration
description; both this document and `confirmatory/school_substitution_table.json`
were uploaded as registered files.

A Wayback Machine snapshot of the GitHub commit URL has also been
captured for additional third-party-controlled timestamping.

These supplementary timestamps strengthen the public-record
character of the pre-registration; the methodological commitment
itself is established at the public GitHub commit timestamp and the
OSF registration timestamp.

---

*This document is the pre-registration. The corresponding
methodology lock and substitution table are committed in the same
commit. Results from executing the pre-registered test will appear
in a separate `CONFIRMATORY_RESULTS.md` after the analysis is run.*
