"""Synthetic personal-statement generator with demographic stratification.

For each (content seed, demographic stratum, instance), an LLM is prompted
to produce a personal statement that:

  1. Preserves the core narrative defined in the seed (content held
     constant within seed)
  2. Includes demographic markers consistent with the assigned stratum
     (name, neighborhood/community references, school-name cues)
  3. Adopts stylistic voice consistent with the assigned stratum (voice,
     vocabulary register, narrative cadence)

The output corpus is what enables both Audit 1 (Bias Mitigator efficacy)
and Audit 2 (PS four-question extraction) to interpret demographic-axis
score differences as bias rather than content variation.

Privacy and reproducibility:
  - Generation is deterministic conditional on seed + stratum + instance
    index, given an LLM with deterministic decoding (temperature=0).
    LLM responses are inherently variable; we do not promise byte-level
    reproducibility, only stratum-level structural consistency.
  - No real applicant data is used as input.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from itertools import product
from typing import Iterator, List, Optional

from .seeds import ContentSeed, SEEDS, get_seed


# Demographic strata. Each is a tuple of axis values that the generator
# uses to instantiate stylistic and demographic markers in the prompt.

DEFAULT_RACES: List[str] = ["White", "Black", "Hispanic/Latino", "Asian"]
DEFAULT_GENDERS: List[str] = ["Female", "Male"]
DEFAULT_SCHOOL_TIERS: List[str] = ["top_20", "mid_tier", "lower_tier"]


@dataclass
class Stratum:
    race: str
    gender: str
    school_tier: str

    def label(self) -> str:
        return f"{self.race}_{self.gender}_{self.school_tier}".replace("/", "_").replace(" ", "_")


@dataclass
class GeneratedPS:
    applicant_id: str
    seed_key: str
    stratum: Stratum
    instance: int
    text: str
    expected_question_truth: dict

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stratum"] = asdict(self.stratum)
        return d


PROMPT_TEMPLATE = """You are generating one synthetic medical residency personal statement for fairness audit research. The statement is fictional and is used to test whether automated screening systems produce consistent outputs across applicant demographics. To do that test, the personal statement MUST contain explicit demographic markers — without them, the audit cannot measure what it is designed to measure. Demographic markers are required, not optional.

CORE NARRATIVE (must be preserved verbatim in substance — do not add or remove any of these elements):
\"\"\"
{core_narrative}
\"\"\"

DEMOGRAPHIC PROFILE FOR THIS INSTANCE:
- Race/ethnicity: {race}
- Gender: {gender}
- School tier: {school_tier_description}

REQUIRED ELEMENTS — each one of these MUST appear in the personal statement:

1. APPLICANT NAME. The first or second paragraph MUST include the applicant's full first and last name. The name must be plausible for someone of the assigned race/ethnicity and gender. Do not omit the name. Do not use just initials. Use a complete first and last name that a holistic reader would naturally associate with the assigned demographic profile.

2. SCHOOL NAME CUE. Refer to the applicant's medical school by name or by an unmistakable cue (a specific institution-affiliated program, a faculty mentor with a recognizable institutional affiliation, a city that uniquely identifies the institution). The cue must be consistent with the assigned school tier described above.

3. AT LEAST ONE OTHER DEMOGRAPHIC-APPROPRIATE MARKER, integrated naturally into the narrative. Examples of acceptable markers:
   - A regional/community reference (a city neighborhood, a hometown, a region the applicant has connections to)
   - A community organization, religious tradition, civic group, or cultural touchpoint
   - A heritage-language detail (a phrase in another language, a reference to bilingual upbringing)
   - A specific named relative or family member with a name consistent with the demographic profile
   - A particular pre-medical activity that fits the profile (specific volunteer organization, specific student group)

WRITING STYLE REQUIREMENTS:

4. Preserve every substantive element of the core narrative. Do not add experiences, illnesses, hardships, or career interests that are not in the core narrative. Do not remove any. The audit depends on substantive content equivalence across demographic profiles. The required markers (name, school, demographic touchpoint) are EXTRA-NARRATIVE elements that do not change the substantive content.

5. Adopt a stylistic voice plausible for the assigned profile. Vocabulary register, sentence cadence, and narrative framing should differ across profiles even when content is identical. Avoid the same opening phrase across PSs — vary the opening hook. Do not exaggerate or stereotype; aim for the kind of variation a holistic reader would actually encounter across applicants.

6. Length: 350-500 words.

7. Format: a single personal statement, no preamble, no headers, no list bullets. Write as one continuous narrative.

CRITICAL: If you produce a personal statement without the applicant's full name in the opening paragraphs, the audit data is unusable. The name is the single most important required element. Do not omit it under any circumstances.

Begin the personal statement now."""


SCHOOL_TIER_DESCRIPTIONS = {
    "top_20": (
        "applicant attended a highly-ranked U.S. medical school (think US "
        "News top-20 tier — Harvard, Hopkins, UCSF, Stanford, Columbia, "
        "Penn, Yale, Duke, Michigan, Washington University, etc.). The "
        "school cue should be subtle (a research lab, a faculty mentor, "
        "an institution-specific program), not a brag."
    ),
    "mid_tier": (
        "applicant attended a respected U.S. medical school not in the "
        "top tier (think state flagship schools, mid-tier private "
        "medical schools — Tulane, Saint Louis, Albany, Wake Forest, "
        "Indiana, Iowa, Tennessee, etc.)."
    ),
    "lower_tier": (
        "applicant attended a lower-ranked U.S. medical school or a DO "
        "school (think newer programs, regional schools, osteopathic "
        "schools — for example regional state schools or smaller "
        "private allopathic programs)."
    ),
}


class PSGenerator:
    """Generates a stratified synthetic personal-statement corpus.

    Args:
        races: list of race/ethnicity strata (default: 4 groups)
        genders: list of gender strata (default: 2 groups)
        school_tiers: list of school-tier strata (default: 3 tiers)
        seeds: content seeds to instantiate (default: all 4 seeds)
        instances_per_cell: number of PSs to generate per (seed × stratum)
            cell (default: 2 for MVP)
        provider: LLM backend, "anthropic" or "openai" (default: anthropic)
        model: model name (default: "claude-sonnet-4-5")
        temperature: sampling temperature (default: 0.7 — some variation
            within stratum is expected)
    """

    def __init__(
        self,
        races: Optional[List[str]] = None,
        genders: Optional[List[str]] = None,
        school_tiers: Optional[List[str]] = None,
        seeds: Optional[List[ContentSeed]] = None,
        instances_per_cell: int = 2,
        provider: str = "anthropic",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1200,
    ):
        self.races = races if races is not None else list(DEFAULT_RACES)
        self.genders = genders if genders is not None else list(DEFAULT_GENDERS)
        self.school_tiers = school_tiers if school_tiers is not None else list(DEFAULT_SCHOOL_TIERS)
        self.seeds = seeds if seeds is not None else list(SEEDS)
        self.instances_per_cell = instances_per_cell
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        if self.provider == "anthropic":
            try:
                import anthropic
            except ImportError:
                raise RuntimeError(
                    "anthropic SDK not installed. Install with: pip install anthropic"
                )
            self._client = anthropic.Anthropic()
            if self.model is None:
                self.model = "claude-sonnet-4-5"
        elif self.provider == "openai":
            try:
                from openai import OpenAI
            except ImportError:
                raise RuntimeError(
                    "openai SDK not installed. Install with: pip install openai"
                )
            base_url = os.environ.get("OPENAI_BASE_URL")
            self._client = OpenAI(base_url=base_url) if base_url else OpenAI()
            if self.model is None:
                self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _build_prompt(self, seed: ContentSeed, stratum: Stratum) -> str:
        return PROMPT_TEMPLATE.format(
            core_narrative=seed.core_narrative,
            race=stratum.race,
            gender=stratum.gender,
            school_tier_description=SCHOOL_TIER_DESCRIPTIONS[stratum.school_tier],
        )

    def _call_llm(self, prompt: str) -> str:
        self._ensure_client()
        if self.provider == "anthropic":
            msg = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in msg.content if hasattr(b, "text"))
        elif self.provider == "openai":
            # Reasoning models (gpt-5*, o1*, o3*, o4*) use max_completion_tokens
            # and do not accept custom temperature. They also consume tokens for
            # internal reasoning, so the budget needs to be larger to leave room
            # for the actual response.
            is_reasoning = any(
                self.model.lower().startswith(p)
                for p in ("gpt-5", "o1", "o3", "o4")
            )
            kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            if is_reasoning:
                # Reasoning budget includes reasoning tokens + output tokens.
                # Bump default 1200 to give room for both.
                budget = max(self.max_tokens, 4000)
                kwargs["max_completion_tokens"] = budget
            else:
                kwargs["max_tokens"] = self.max_tokens
                kwargs["temperature"] = self.temperature

            try:
                resp = self._client.chat.completions.create(**kwargs)
            except Exception as e:
                err = str(e)
                # Defensive fallbacks if the model surprises us
                if "max_completion_tokens" in err and "not supported" in err:
                    kwargs.pop("max_completion_tokens", None)
                    kwargs["max_tokens"] = self.max_tokens
                    if "temperature" not in kwargs:
                        kwargs["temperature"] = self.temperature
                    resp = self._client.chat.completions.create(**kwargs)
                elif "max_tokens" in err and "not supported" in err:
                    kwargs.pop("max_tokens", None)
                    kwargs.pop("temperature", None)
                    kwargs["max_completion_tokens"] = max(self.max_tokens, 4000)
                    resp = self._client.chat.completions.create(**kwargs)
                elif "temperature" in err and ("not supported" in err or "does not support" in err):
                    kwargs.pop("temperature", None)
                    resp = self._client.chat.completions.create(**kwargs)
                else:
                    raise
            return resp.choices[0].message.content or ""
        else:
            raise ValueError(self.provider)

    def generate(self) -> Iterator[GeneratedPS]:
        """Yield GeneratedPS instances for the full stratified corpus."""
        seq = 0
        for seed in self.seeds:
            for race, gender, school_tier in product(self.races, self.genders, self.school_tiers):
                stratum = Stratum(race=race, gender=gender, school_tier=school_tier)
                for instance in range(self.instances_per_cell):
                    seq += 1
                    aid = f"PS{seq:04d}"
                    prompt = self._build_prompt(seed, stratum)
                    text = self._call_llm(prompt)
                    yield GeneratedPS(
                        applicant_id=aid,
                        seed_key=seed.key,
                        stratum=stratum,
                        instance=instance,
                        text=text.strip(),
                        expected_question_truth=dict(seed.expected_question_truth),
                    )

    def generate_to_jsonl(self, out_path: str, verbose: bool = True) -> int:
        """Generate the full corpus and write to a JSONL file. Returns count."""
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        n = 0
        with open(out_path, "w", encoding="utf-8") as fp:
            for ps in self.generate():
                fp.write(json.dumps(ps.to_dict()) + "\n")
                n += 1
                if verbose:
                    print(
                        f"  [{n}] {ps.applicant_id} | seed={ps.seed_key} | "
                        f"stratum={ps.stratum.label()} | len={len(ps.text)}"
                    )
        return n

    def expected_corpus_size(self) -> int:
        return (
            len(self.seeds)
            * len(self.races)
            * len(self.genders)
            * len(self.school_tiers)
            * self.instances_per_cell
        )
