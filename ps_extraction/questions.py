"""The four PS-extraction questions enumerated in US 12,265,502 B1, col. 10.

Patent text (col. 10, lines 1-17):
> "Data files of text including personal statements provided as input. Users
> can apply NLP to read through personal statement of each applicant,
> pulling out major themes. Alternatively, users provide or select specific
> questions for platform to answer:
>
>   "Has the applicant ever experienced poverty?"
>   "Has the applicant ever been a refugee?"
>   "Has the applicant ever experienced major illness?"
>   "Does the applicant seem likely to pursue a career in academia?"
>
> All information identified from personal statement can be included in
> final score calculation."

These four questions are encoded here as named attribute indicators. Each
question is associated with one or more exemplar sentences that provide the
semantic anchor for similarity scoring.
"""
from __future__ import annotations

from typing import Dict, List

# Patent's four enumerated PS questions, indexed by short identifier.
PATENT_QUESTIONS: Dict[str, str] = {
    "poverty": "Has the applicant ever experienced poverty?",
    "refugee": "Has the applicant ever been a refugee?",
    "major_illness": "Has the applicant ever experienced major illness?",
    "academic_career": "Does the applicant seem likely to pursue a career in academia?",
}

# Exemplar sentences anchoring each question's semantic neighborhood.
# Multiple exemplars per question allow the extractor to be more robust to
# lexical variation in the source text.
DEFAULT_EXEMPLARS: Dict[str, List[str]] = {
    "poverty": [
        "I grew up in poverty.",
        "My family struggled financially throughout my childhood.",
        "I experienced economic hardship and food insecurity.",
        "We could not afford basic necessities.",
    ],
    "refugee": [
        "I came to this country as a refugee.",
        "My family fled persecution in our home country.",
        "We were displaced and resettled as refugees.",
        "I am the child of refugees.",
    ],
    "major_illness": [
        "I experienced a serious illness.",
        "I was diagnosed with a major medical condition.",
        "I underwent significant medical treatment.",
        "Illness shaped my path to medicine.",
    ],
    "academic_career": [
        "I plan to pursue an academic career in medicine.",
        "My goal is to become a physician-scientist.",
        "I am committed to a career in academic medicine and research.",
        "I want to work as a faculty member at an academic medical center.",
    ],
}


def build_question_exemplars(
    questions: Dict[str, List[str]] | None = None,
) -> Dict[str, List[str]]:
    """Return the exemplar dictionary, optionally extended or overridden.

    Args:
        questions: optional dict to merge into the defaults; values override
            the default exemplars for matching keys.
    """
    out = {k: list(v) for k, v in DEFAULT_EXEMPLARS.items()}
    if questions:
        for k, v in questions.items():
            out[k] = list(v)
    return out
