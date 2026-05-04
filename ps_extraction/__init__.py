"""Personal Statement attribute extractor per US 12,265,502 B1, col. 10.

The patent's Personal Statement Component (col. 10, lines 1-17) describes
NLP-based extraction of major themes plus user-selectable specific
questions. The patent enumerates four example questions:

  1. "Has the applicant ever experienced poverty?"
  2. "Has the applicant ever been a refugee?"
  3. "Has the applicant ever experienced major illness?"
  4. "Does the applicant seem likely to pursue a career in academia?"

This module implements the four-question extractor as semantic-similarity
attribute indicators against an SBERT embedding space. For each PS, each
question receives a score in [0, 1] reflecting semantic closeness to the
question's exemplar(s).

The four questions are themselves discriminatory in framing — they probe
protected-class proxies (poverty correlates with race/SES; refugee status
correlates with national origin; major illness correlates with disability
status). The audit framing therefore has two layers:

  - The questions themselves may be unlawful as inputs to an employment
    decision regardless of inference accuracy
  - Inference-level bias may produce systematically different scores for
    demographically varied PS samples even when content is held constant

Both layers are testable using this extractor + the audit metrics module.
"""
from .questions import PATENT_QUESTIONS, build_question_exemplars
from .extractor import PSExtractor
from .llm_extractor import LLMPSExtractor

__all__ = ["PATENT_QUESTIONS", "build_question_exemplars", "PSExtractor", "LLMPSExtractor"]
