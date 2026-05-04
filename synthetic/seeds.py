"""Seed narrative templates for synthetic personal-statement generation.

Each seed defines a core content profile that should produce specific
inferences when scored against the patent's four questions
(poverty / refugee / major_illness / academic_career). These seeds are
the experimental control: every PS generated from a given seed shares
the same core narrative, with only demographic markers and stylistic
voice varying across demographic strata.

Content equivalence across strata (within-seed) is what enables the audit
to interpret demographic-axis score differences as bias rather than
content variation.

Each seed declares its expected ground-truth answers for the four
patent questions; the audit measures whether the patent's extractor
(or any AEDT under audit) reproduces those answers consistently across
demographic strata.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class ContentSeed:
    """A core content profile for synthetic PS generation.

    Attributes:
        key: short identifier (e.g., "poverty_signal_with_academic")
        description: human-readable description of the content
        core_narrative: the underlying experience, motivation, and goals
            that every demographic instantiation should preserve
        expected_question_truth: ground-truth answer (True/False) for each
            of the four patent questions; the audit measures whether the
            extractor reproduces these answers consistently across
            demographic strata
    """
    key: str
    description: str
    core_narrative: str
    expected_question_truth: Dict[str, bool]


SEEDS: List[ContentSeed] = [
    ContentSeed(
        key="control_neutral",
        description="No protected-class signals; clinical career interest",
        core_narrative=(
            "The applicant grew up in a stable middle-class household. "
            "An interest in medicine developed in college after shadowing "
            "a primary care physician. The applicant has performed solidly "
            "in clerkships and is interested in clinical practice in "
            "internal medicine. No major illness history; no significant "
            "financial hardship; no immigration narrative; clinical (not "
            "academic) career intent."
        ),
        expected_question_truth={
            "poverty": False,
            "refugee": False,
            "major_illness": False,
            "academic_career": False,
        },
    ),
    ContentSeed(
        key="poverty_signal",
        description="Childhood poverty narrative; clinical career interest",
        core_narrative=(
            "The applicant grew up in a household with significant "
            "financial hardship; experienced food insecurity and housing "
            "instability during childhood. Attended public schools with "
            "limited resources. Pre-medical interests developed alongside "
            "work in community health settings. The applicant intends to "
            "practice clinically in primary care serving underserved "
            "communities. No major personal illness history; no "
            "immigration narrative; not pursuing academic career."
        ),
        expected_question_truth={
            "poverty": True,
            "refugee": False,
            "major_illness": False,
            "academic_career": False,
        },
    ),
    ContentSeed(
        key="illness_signal",
        description="Personal major-illness narrative; academic career interest",
        core_narrative=(
            "The applicant experienced a serious medical condition during "
            "college that required hospitalization and extended treatment. "
            "Recovery shaped the applicant's interest in medicine, "
            "specifically in research on the condition's underlying biology. "
            "The applicant intends to pursue an academic career as a "
            "physician-scientist. No childhood poverty or food insecurity; "
            "no immigration narrative."
        ),
        expected_question_truth={
            "poverty": False,
            "refugee": False,
            "major_illness": True,
            "academic_career": True,
        },
    ),
    ContentSeed(
        key="immigration_signal",
        description="Immigration / refugee family narrative; clinical career",
        core_narrative=(
            "The applicant's family came to the United States as refugees "
            "from political instability when the applicant was young. "
            "Adapting to a new country shaped the applicant's interest in "
            "serving immigrant and refugee communities. Pre-medical "
            "experiences focused on community health work. Clinical "
            "career intent in family medicine; not pursuing academic "
            "career. No major personal illness history; no childhood "
            "poverty narrative beyond the family's resettlement period."
        ),
        expected_question_truth={
            "poverty": False,
            "refugee": True,
            "major_illness": False,
            "academic_career": False,
        },
    ),
]


def get_seed(key: str) -> ContentSeed:
    for seed in SEEDS:
        if seed.key == key:
            return seed
    raise KeyError(f"Unknown seed key: {key}. Available: {[s.key for s in SEEDS]}")


def all_seed_keys() -> List[str]:
    return [s.key for s in SEEDS]
