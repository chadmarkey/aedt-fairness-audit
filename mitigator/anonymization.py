"""Input-side anonymization per US 12,265,502 B1, col. 24, lines 9-14.

Patent text:
> "Anonymization operations: Apply pattern recognition and heuristic rules
> to identify and redact gender identifiers, names, and other identifying
> characteristics that could induce bias (e.g., learned during model
> pre-training) during analysis."

The patent specifies the goal but not the algorithm. This implementation
combines:
  1. spaCy NER for PERSON, ORG, GPE, LOC entities → `[NAME]`, `[ORG]`, `[LOC]`
  2. Curated lists for pronouns and gendered honorifics → `they`, `[HONORIFIC]`
  3. Curated regex for racial/ethnic terms → `[ETHNICITY]`
  4. AAMC medical school name patterns → `[SCHOOL]`

These choices are documented as the implementer's, not the patent's, in
`DEVIATIONS_FROM_PATENT.md`.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Tuple

# Pronouns and gendered honorifics. Substituted with neutral tokens preserving
# syntactic role.
PRONOUN_REPLACEMENTS = {
    r"\bhe\b": "they",
    r"\bshe\b": "they",
    r"\bhim\b": "them",
    # "her" is ambiguous between object pronoun ("I told her") and possessive
    # determiner ("her family"). In narrative residency-applicant text the
    # possessive use dominates by a large margin; we therefore map to "their".
    # This produces grammatically-acceptable singular-they output for the
    # possessive case ("their family") and slightly-marked but acceptable
    # output for the object case ("I told their" — rare in narrative text).
    r"\bher\b": "their",
    r"\bhis\b": "their",
    r"\bhers\b": "theirs",
    r"\bhimself\b": "themself",
    r"\bherself\b": "themself",
}

HONORIFIC_REPLACEMENTS = {
    r"\bMr\.?\b": "[HONORIFIC]",
    r"\bMrs\.?\b": "[HONORIFIC]",
    r"\bMs\.?\b": "[HONORIFIC]",
    r"\bMiss\b": "[HONORIFIC]",
    r"\bDr\.?\b": "[HONORIFIC]",
    r"\bProf\.?\b": "[HONORIFIC]",
    r"\bSir\b": "[HONORIFIC]",
    r"\bMadam\b": "[HONORIFIC]",
}

# Racial / ethnic terms commonly found in narrative documents. Replacement
# with a neutral placeholder preserves the structural role of the term.
ETHNICITY_PATTERNS = [
    r"\b(?:African[- ]American|Black|Caucasian|White|Hispanic|Latino|Latina|Latine|Latinx|Asian|Pacific Islander|Native American|American Indian|Indigenous|Middle Eastern|South Asian|East Asian|Southeast Asian|Native Hawaiian)\b",
]

# AAMC medical school name patterns. The toolkit ships an opt-in heuristic
# regex that catches "X School of Medicine", "X Medical College", etc.
# Users may extend this list with institution-specific patterns.
SCHOOL_PATTERNS = [
    r"\b[A-Z][a-zA-Z]+ (?:School of Medicine|Medical School|Medical College|College of Medicine|School of Osteopathic Medicine|University School of Medicine)\b",
    # A small set of well-known short institution names that the generic
    # regex above does not catch. Users can extend this via custom_patterns.
    r"\bBaylor\b", r"\bColumbia\b", r"\bCornell\b", r"\bDartmouth\b",
    r"\bDuke\b", r"\bHarvard\b", r"\bJohns Hopkins\b", r"\bMayo\b",
    r"\bStanford\b", r"\bUCLA\b", r"\bUCSF\b", r"\bWashington University\b",
    r"\bYale\b",
]


class Anonymizer:
    """Input-side anonymization per patent §532.

    Combines NER-based entity redaction with curated lexical replacements.
    Returns text with biasing identifiers replaced by neutral placeholders.
    """

    def __init__(
        self,
        use_ner: bool = True,
        ner_model: str = "en_core_web_sm",
        redact_pronouns: bool = True,
        redact_honorifics: bool = True,
        redact_ethnicity: bool = True,
        redact_schools: bool = True,
        custom_patterns: Iterable[Tuple[str, str]] | None = None,
    ):
        self.use_ner = use_ner
        self.ner_model_name = ner_model
        self.redact_pronouns = redact_pronouns
        self.redact_honorifics = redact_honorifics
        self.redact_ethnicity = redact_ethnicity
        self.redact_schools = redact_schools
        self.custom_patterns = list(custom_patterns) if custom_patterns else []
        self._nlp = None

    def _ensure_ner(self):
        if self._nlp is None and self.use_ner:
            try:
                import spacy
                try:
                    self._nlp = spacy.load(self.ner_model_name)
                except OSError:
                    raise RuntimeError(
                        f"spaCy model '{self.ner_model_name}' is not installed. "
                        f"Install with: python -m spacy download {self.ner_model_name}"
                    )
            except ImportError:
                raise RuntimeError(
                    "spaCy is not installed. Install with: pip install spacy"
                )

    def __call__(self, text: str) -> str:
        if not text:
            return ""
        out = text

        # 1. NER-based entity redaction (PERSON, ORG, GPE, LOC).
        if self.use_ner:
            self._ensure_ner()
            doc = self._nlp(out)
            spans: List[Tuple[int, int, str]] = []
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    spans.append((ent.start_char, ent.end_char, "[NAME]"))
                elif ent.label_ == "ORG":
                    spans.append((ent.start_char, ent.end_char, "[ORG]"))
                elif ent.label_ in ("GPE", "LOC"):
                    spans.append((ent.start_char, ent.end_char, "[LOC]"))
            # Apply spans in reverse so offsets stay valid
            for start, end, repl in sorted(spans, key=lambda s: -s[0]):
                out = out[:start] + repl + out[end:]

        # 2. Honorific redaction.
        if self.redact_honorifics:
            for pattern, repl in HONORIFIC_REPLACEMENTS.items():
                out = re.sub(pattern, repl, out, flags=re.IGNORECASE)

        # 3. Pronoun normalization (pronouns → singular they).
        if self.redact_pronouns:
            for pattern, repl in PRONOUN_REPLACEMENTS.items():
                out = re.sub(pattern, repl, out, flags=re.IGNORECASE)

        # 4. Racial / ethnic term redaction.
        if self.redact_ethnicity:
            for pattern in ETHNICITY_PATTERNS:
                out = re.sub(pattern, "[ETHNICITY]", out, flags=re.IGNORECASE)

        # 5. Medical school name redaction.
        if self.redact_schools:
            for pattern in SCHOOL_PATTERNS:
                out = re.sub(pattern, "[SCHOOL]", out)

        # 6. Custom user-supplied patterns.
        for pattern, repl in self.custom_patterns:
            out = re.sub(pattern, repl, out, flags=re.IGNORECASE)

        return out
