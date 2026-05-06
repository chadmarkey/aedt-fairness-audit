# Deviations from Patent

Implementation record for the patent-derived components of this library.
Documents what U.S. Patent No. 12,265,502 B1 (*Multi-Program Applicant
Review System with Adjustable Parameters*, Medicratic Inc., issued April
1, 2025) specifies, what this library implements, and where the
implementation makes choices the patent does not pin down.

The library's `audit/` module is a generic fairness metrics library and
does not depend on the patent. Only the components that explicitly
implement patent elements are covered here: `mitigator/` and
`ps_extraction/`.

Patent column and line citations refer to the granted U.S. Patent No.
12,265,502 B1 as published.

---

## §532 Bias Mitigator (input-side, Claim 1)

### Architectural placement

§532 is a cross-cutting capability that operates at two architectural
placements per the patent:

1. **Input side.** Anonymization + semantic substitution during document
   pre-processing (col. 24, lines 5–18).
2. **Output side.** Post-aggregation statistical correction after score
   generation (col. 24, lines 19–46).

This module implements only the input-side operation. The output-side
correction is in the spec but discretionary per Claim 1 ("can be
performed again if user directs software to do so" — col. 24, line 22).
The patent does not specify the output-side correction algorithm.

### Claim 1 requirement (verbatim)

> "Bias mitigation operation including:
>   Detecting one or more potentially biasing identifiers from one or more
>   document files;
>   Replacing one or more potentially biasing identifiers with one or more
>   corresponding neutral terms such that semantic structure is maintained."

### Anonymization operations (col. 24, lines 9–14)

> "Apply pattern recognition and heuristic rules to identify and redact
> gender identifiers, names, and other identifying characteristics that
> could induce bias (e.g., learned during model pre-training) during
> analysis."

The patent specifies the goal but not the algorithm. This implementation:

- spaCy NER (`en_core_web_sm`) for PERSON, ORG, GPE, LOC entities →
  `[NAME]`, `[ORG]`, `[LOC]` placeholders preserving structural role
- Curated lists for pronouns (he/she/they/etc.) → singular *they*
- Curated lists for honorifics (Mr./Mrs./Ms./Dr./Sir/Madam) →
  `[HONORIFIC]`
- Curated regex for racial/ethnic terms → `[ETHNICITY]`
- Curated regex for medical school names → `[SCHOOL]`
- User-supplied `(regex, replacement)` pairs via `custom_patterns`

### Semantic substitution operations (col. 24, lines 15–18)

> "Performed during document pre-processing step. Replaces potentially
> biasing terms with neutral alternatives to preserve semantic structure
> of statements (rather than outright removal of potentially biasing
> term)."

The patent specifies the goal but not the algorithm or term inventory.
This implementation provides a default lookup table covering two
substitution categories of connotation-only pairs. The full table is
in `mitigator/semantic_substitution.py:DEFAULT_SUBSTITUTIONS`.

- **Communal/agentic language pairs** (Madera, Hebl, Martin 2009, JAP):
  `caring` → `skilled`, `nurturing` → `competent`,
  `warm` → `professional`, `helpful` → `effective`,
  `pleasant` → `professional`. Each pair preserves a distinct
  semantic neighborhood; multiple distinct adjectives are not
  collapsed onto a single neutral term.
- **Performance-descriptor pairs**: `diligent` → `thorough`,
  `hardworking` → `effective`, `dedicated` → `committed`,
  `conscientious` → `thorough`, `meticulous` → `detail-oriented`.
  Each descriptor maps to a distinct agentic equivalent rather than
  collapsing onto a single shared term.

Three additional categories that appeared in earlier versions of this
table were removed during the 2026-05-06 cleanup pass after a
methodology audit found they violated Claim 1's "preserve semantic
structure" requirement:

- **Leave-of-absence phrasing** (e.g., `voluntary` → `approved`,
  `personal reasons` → `approved reasons`): changes propositional
  content (self-initiated vs. institutionally sanctioned).
- **Hedge / evaluative-language escalations** (e.g., `completed` →
  `successfully completed`, `satisfactory` → `strong`,
  `acceptable` → `strong`, `competent` → `highly competent`): adds
  factual claims or escalates evaluative magnitude.
- **Concession-framing** (e.g., `despite` → `with`, `overcame` →
  `managed`, `struggled` → `worked through`): flips logical
  structure or weakens propositional content.

These removed pairs are documented as "intentionally NOT included" in
the source comment block in `mitigator/semantic_substitution.py`. See
CHANGELOG entries for 2026-05-05 and 2026-05-06 (continued) for the
review that surfaced them.

The default table is the implementer's choice; users may extend or
replace it via the `substitutions` parameter, with the caveat that
substitutions changing propositional content go beyond Claim 1's
"preserve semantic structure" requirement.

### Output-side correction (col. 24, lines 19–46) — not implemented

> "Bias mitigation operations after aggregation step: Quantitative
> analysis after primary sentiment analysis... bias mitigator 532 may
> apply adjustments or corrections to scores to counteract observed
> differences or biases."

The patent describes the operation but does not specify the
recalibration algorithm. Not implemented in this module.

---

## §PS Component (col. 10, lines 1–17)

### Patent text (verbatim)

> "Data files of text including personal statements provided as input.
> Users can apply NLP to read through personal statement of each
> applicant, pulling out major themes. Alternatively, users provide or
> select specific questions for platform to answer:
>
>   "Has the applicant ever experienced poverty?"
>   "Has the applicant ever been a refugee?"
>   "Has the applicant ever experienced major illness?"
>   "Does the applicant seem likely to pursue a career in academia?"
>
> All information identified from personal statement can be included in
> final score calculation."

### Two extractor variants

The patent specifies the four questions but does not specify how the
questions are answered. The library ships two extractor implementations,
both consistent with the patent's allowed scope:

1. **`PSExtractor` (SBERT, in `ps_extraction/extractor.py`)** —
   cosine-similarity scoring against question-exemplar embeddings. Patent
   col. 22 line 31 enumerates Sentence-BERT among permitted embedding
   methods; col. 23 lines 31–47 enumerates cosine similarity among
   permitted scoring metrics.

2. **`LLMPSExtractor` (LLM, in `ps_extraction/llm_extractor.py`)** —
   direct LLM question-answering. Defaults: `gpt-4o-mini` (OpenAI) or
   `gpt-5-mini` if available; `claude-haiku-4-5` (Anthropic). Patent
   col. 10 says "users can apply NLP" without specifying the answering
   mechanism.

Neither extractor is a claim about any specific deployed AEDT's PS
question-answering architecture. Both are reasonable implementations
consistent with the patent's allowed scope.

### SBERT extractor implementation choices

- Embedding model: `all-MiniLM-L6-v2`. Patent col. 22 line 31 enumerates
  Word2Vec, GloVe, BERT, Sentence-BERT.
- Sentence-similarity threshold: 0.35.
- Soft-assignment temperature (β): 8.0.
- Aggregate power: 2.0 (matches patent col. 23 line 53 "raised to power
  of two").

The patent does not specify default values for threshold, β, or
aggregate power.

### Question exemplars

The patent provides only the four question texts. Each question in this
implementation is associated with 3–4 exemplar sentences anchoring the
semantic neighborhood. The exemplar inventory is the implementer's
choice; users may override via `question_exemplars` parameter to
`PSExtractor`.

### Exemplar aggregation: mean-pool vs max-over-exemplars

When multiple exemplars are provided per question, this implementation
mean-pools their embeddings into a single per-question centroid before
cosine scoring (`extractor.py:74`). This is one reasonable choice; the
alternative — taking the maximum cosine similarity across exemplars
before the threshold gate — can yield higher recall when exemplars are
spread across the semantic neighborhood. The patent does not specify
the aggregation rule. Mean-pool is documented here as the implementer's
choice; users running their own audits with a different aggregation
should report it.

### Pipeline order (patent §518 → §520 → §522 → §524 → §526 → §528 → §530)

The SBERT extractor's per-text path is:

```
text → split sentences → SBERT embed →
  cosine sim to question exemplars →
  threshold gate (drop sentences below 0.35) →
  softmax soft-assign across questions →
  per-question score → power-2 aggregation
```

This matches the patent's element ordering.

---

## Method 600 (claim 1 method flow)

| Patent operation | Library equivalent |
|---|---|
| 602 — receive applicant data | `df` parameter to harness functions |
| 604 — receive preference parameters | `cfg` / extractor constructor args |
| 606 — perform ML-based assessment | extractor `score_text` / `score_corpus` |
| 608 — present applicant ranking | `app_df.sort_values("final_score", ascending=False)` in audit harness |

---

## Summary table

| Patent element | Module | Status |
|---|---|---|
| §532 input-side anonymization | `mitigator/anonymization.py` | Implemented; algorithm is implementer's choice (patent unspecified) |
| §532 input-side semantic substitution | `mitigator/semantic_substitution.py` | Implemented; default lookup table is implementer's choice |
| §532 output-side post-aggregation correction | — | Not implemented; patent does not specify algorithm |
| §PS Component four questions | `ps_extraction/questions.py` | Verbatim from col. 10 |
| §PS exemplar sentences (SBERT) | `ps_extraction/questions.py` | Implementer's choice; patent provides questions only |
| §520 SBERT embedding | `ps_extraction/extractor.py` | Patent-enumerated alternative |
| §528 cosine similarity | `ps_extraction/extractor.py` | Patent-enumerated metric |
| §528 zero/one/multi sentence contribution | `ps_extraction/extractor.py` | Direct match |
| §530 power-of-2 aggregation | `ps_extraction/extractor.py` | Direct match (default power=2.0) |
| §PS Component LLM-based answering | `ps_extraction/llm_extractor.py` | Within patent's "users can apply NLP"; code-level default gpt-5-mini for OpenAI / claude-haiku-4-5 for Anthropic. Canonical n=384 reference outputs in `examples/reference_outputs/audit_2/` were generated with `--llm-model gpt-4o-mini`; the n=192 robustness check was generated with gpt-5-mini. |
