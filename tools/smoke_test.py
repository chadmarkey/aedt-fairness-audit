"""End-to-end smoke test for the audit toolkit.

Builds a tiny hand-curated corpus (16 PSs across 2 demographic strata x 4
content seeds x 2 instances), exercises every load-bearing module
(BiasMitigator, PSExtractor, axis_audit), and prints sanity-check output.

No LLM API key required. Verifies that:
  - All imports resolve
  - BiasMitigator runs without errors and produces text
  - PSExtractor runs and produces 4-question scores
  - axis_audit produces per-axis DI metrics
  - End-to-end JSONL → audit-results path works

Note: with only 16 PSs, the DI numbers from this smoke test are not
meaningful findings — they exist to verify the code path. For substantive
audit results, use tools.generate_ps_corpus to produce a real corpus and
then run tools.run_audit_1 / tools.run_audit_2 on it.

Usage:
    python -m tools.smoke_test            # full path (downloads SBERT + spaCy)
    python -m tools.smoke_test --offline  # offline path: no model downloads
                                          # (regex-only mitigator, synthetic
                                          # extractor scores, no SBERT, no VADER)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from audit.screening import axis_audit
from mitigator import BiasMitigator
from mitigator.anonymization import Anonymizer
from ps_extraction import PSExtractor, PATENT_QUESTIONS


# Hand-curated mini corpus: 4 seeds x 2 demographic strata x 2 instances = 16 PSs.
# Each pair within (seed, stratum) varies surface markers but holds the
# core content elements consistent. The two strata used here are
# (White, Female, top_20) and (Black, Male, lower_tier).
MINI_CORPUS = [
    # Seed: control_neutral, Stratum: White/Female/top_20
    {
        "applicant_id": "PS0001", "seed_key": "control_neutral", "instance": 0,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Sarah Mitchell first considered medicine while shadowing her family physician in suburban Connecticut. The experience showed her how meaningful primary care work can be for a community. Her clerkships at her medical school have been consistently strong, and she has earned positive feedback from attending physicians for her clinical reasoning and patient communication. She has worked in a community-based health clinic during preclinical years and finds general internal medicine to be the field that best matches her interests in continuity of care, longitudinal patient relationships, and broad clinical reasoning. She intends to practice in a clinical setting after residency, ideally in a mid-sized community hospital where she can serve diverse patient populations.",
    },
    {
        "applicant_id": "PS0002", "seed_key": "control_neutral", "instance": 1,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Emma Thompson developed her interest in medicine through volunteer work at a local hospital during college. Her time on the medical floors at her university teaching hospital has confirmed her draw to internal medicine — the breadth of the field, the diagnostic puzzles, and the long-term relationships clinicians build with their patients. She has performed solidly in clerkships and has received consistent feedback that her clinical reasoning is strong. She plans to pursue a clinical career in general internal medicine after residency.",
    },
    # Seed: control_neutral, Stratum: Black/Male/lower_tier
    {
        "applicant_id": "PS0003", "seed_key": "control_neutral", "instance": 0,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Marcus Johnson first thought about a medical career after shadowing a family physician in his neighborhood during college. He attended a regional state medical school where he has worked through clerkships steadily, drawing positive feedback for his patient communication and clinical decisions. His preclinical work in a community health clinic confirmed his preference for general internal medicine. He intends to practice clinically in a community setting after residency, where he can take care of patients with continuity over years.",
    },
    {
        "applicant_id": "PS0004", "seed_key": "control_neutral", "instance": 1,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Anthony Williams's interest in medicine grew out of college shadowing experiences with his primary care doctor. His medical school is a regional osteopathic program where he has done well across clerkships. His preclinical experience working at a free clinic shaped his preference for primary care. He plans a clinical career in internal medicine after residency, with a focus on practicing in a community-based setting.",
    },
    # Seed: poverty_signal, Stratum: White/Female/top_20
    {
        "applicant_id": "PS0005", "seed_key": "poverty_signal", "instance": 0,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": True, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Rachel Bennett grew up in a household where money was always tight. Her family experienced periods of food insecurity, and the housing situation was unstable through several moves during her childhood. The public schools she attended had limited resources. She was the first person in her family to attend college, where she found her way to medicine through community health work. At her medical school, her clerkships have been strong, and her work in underserved settings has reinforced her commitment to primary care for low-income communities. She intends to practice in a community health center after residency.",
    },
    {
        "applicant_id": "PS0006", "seed_key": "poverty_signal", "instance": 1,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": True, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Jessica Reed grew up in financial hardship — her family used the local food bank often, and she remembers years where rent was a constant worry. She was the first in her family to graduate from college, working through it largely on her own resources. She found medicine through community health volunteering, and at her medical school she has performed well in clerkships. She intends to practice clinically at a community health center serving low-income patients after residency.",
    },
    # Seed: poverty_signal, Stratum: Black/Male/lower_tier
    {
        "applicant_id": "PS0007", "seed_key": "poverty_signal", "instance": 0,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": True, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Darius Harris grew up in a household where economic instability was the constant background of his childhood. His family used food assistance programs, and his early years involved several moves due to housing instability. He attended public schools with limited resources and was the first in his family to go to college. He found his way to medicine through community health work, and at his regional medical school he has performed solidly in clerkships. After residency, he intends to practice in a community health center serving the same kinds of low-income communities he grew up in.",
    },
    {
        "applicant_id": "PS0008", "seed_key": "poverty_signal", "instance": 1,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": True, "refugee": False, "major_illness": False, "academic_career": False},
        "text": "Jamal Carter's family struggled financially throughout his childhood — food insecurity was ongoing, and they moved several times due to housing issues. He attended under-resourced public schools and became the first in his family to attend college. He came to medicine through community health work, performed steadily in clerkships at his regional school, and intends to practice clinically in a community health setting that serves low-income populations.",
    },
    # Seed: illness_signal, Stratum: White/Female/top_20
    {
        "applicant_id": "PS0009", "seed_key": "illness_signal", "instance": 0,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": True, "academic_career": True},
        "text": "Elizabeth Carter was diagnosed with a serious autoimmune condition in college. The hospitalizations and extended treatment that followed shaped her interest in medicine — specifically in the underlying mechanisms of the condition that affected her. At her highly-ranked medical school she has worked in a research lab studying related immunology, and her clerkships have gone well. She intends to pursue an academic career as a physician-scientist, balancing clinical work with translational research.",
    },
    {
        "applicant_id": "PS0010", "seed_key": "illness_signal", "instance": 1,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": True, "academic_career": True},
        "text": "Catherine Walsh experienced a serious illness during her undergraduate years that required prolonged inpatient treatment. Her recovery and the science she encountered along the way drew her to medicine and to research on the biology of the condition. Her medical school has provided strong research mentorship, and her clerkships have gone well. She plans to pursue an academic career as a physician-scientist after residency.",
    },
    # Seed: illness_signal, Stratum: Black/Male/lower_tier
    {
        "applicant_id": "PS0011", "seed_key": "illness_signal", "instance": 0,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": True, "academic_career": True},
        "text": "Christopher Brooks was diagnosed with a major illness in college that required hospitalization and a long course of treatment. The experience drew him to medicine and to research on the underlying biology of the condition. He has done research at his regional medical school, performed well in clerkships, and plans to pursue an academic career as a physician-scientist after residency.",
    },
    {
        "applicant_id": "PS0012", "seed_key": "illness_signal", "instance": 1,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": False, "refugee": False, "major_illness": True, "academic_career": True},
        "text": "Terrell Washington had a serious illness during college that involved extended inpatient treatment. The experience pulled him toward medicine and toward research on the biology of his condition. At his regional medical school, he has worked with research mentors and has performed well in clerkships. He intends to pursue an academic career as a physician-scientist.",
    },
    # Seed: immigration_signal, Stratum: White/Female/top_20
    {
        "applicant_id": "PS0013", "seed_key": "immigration_signal", "instance": 0,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": False, "refugee": True, "major_illness": False, "academic_career": False},
        "text": "Anna Kowalski's family came to the United States as refugees from political instability in Eastern Europe when she was a child. Adapting to a new country, learning a new language, and navigating an unfamiliar healthcare system shaped her interest in serving immigrant and refugee communities. Her preclinical work has been with refugee health programs, and at her medical school her clerkships have gone well. She intends to practice clinically in family medicine, focused on immigrant and refugee health.",
    },
    {
        "applicant_id": "PS0014", "seed_key": "immigration_signal", "instance": 1,
        "stratum": {"race": "White", "gender": "Female", "school_tier": "top_20"},
        "expected_question_truth": {"poverty": False, "refugee": True, "major_illness": False, "academic_career": False},
        "text": "Mia Petrov came to this country as a child after her family fled political instability. Helping her parents navigate the U.S. healthcare system as a teenager left a lasting impression. Her preclinical work has focused on refugee health, and her medical school clerkships have been strong. She plans a clinical career in family medicine, focused on immigrant and refugee patient populations.",
    },
    # Seed: immigration_signal, Stratum: Black/Male/lower_tier
    {
        "applicant_id": "PS0015", "seed_key": "immigration_signal", "instance": 0,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": False, "refugee": True, "major_illness": False, "academic_career": False},
        "text": "Kwame Asante's family came to the United States as refugees from political instability in West Africa when he was young. Adapting to a new country and helping his family navigate the U.S. healthcare system shaped his interest in serving immigrant and refugee communities. He has worked with refugee-focused health programs in his preclinical years and performed well in clerkships at his regional school. He intends to practice clinically in family medicine focused on immigrant and refugee health.",
    },
    {
        "applicant_id": "PS0016", "seed_key": "immigration_signal", "instance": 1,
        "stratum": {"race": "Black", "gender": "Male", "school_tier": "lower_tier"},
        "expected_question_truth": {"poverty": False, "refugee": True, "major_illness": False, "academic_career": False},
        "text": "Daniel Okonkwo arrived in the U.S. with his family as refugees from his home country's political crisis when he was a child. The early years involved adjusting to a new country and navigating an unfamiliar healthcare system. His preclinical work focused on refugee health programs, and he has performed well in clerkships at his regional medical school. He plans to pursue a clinical family medicine career focused on immigrant and refugee patients.",
    },
]


def write_corpus(path: str):
    with open(path, "w", encoding="utf-8") as fp:
        for rec in MINI_CORPUS:
            fp.write(json.dumps(rec) + "\n")
    return len(MINI_CORPUS)


def smoke_mitigator(offline: bool = False):
    label = "Bias Mitigator (regex-only, offline)" if offline else "Bias Mitigator"
    print(f"\n[1/4] {label} smoke test", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    if offline:
        # Skip spaCy NER; uses only the curated regex passes (pronouns,
        # honorifics, ethnicity, schools) plus semantic substitution.
        # No network needed.
        mitigator = BiasMitigator(anonymizer=Anonymizer(use_ner=False))
    else:
        mitigator = BiasMitigator()
    sample = MINI_CORPUS[4]["text"]  # poverty_signal, white female
    mitigated = mitigator(sample)
    print(f"  Input  ({len(sample)} chars): {sample[:120]}...", file=sys.stderr)
    print(f"  Output ({len(mitigated)} chars): {mitigated[:120]}...", file=sys.stderr)
    print(f"  ✓ Bias Mitigator produced text", file=sys.stderr)
    return mitigator


def _synthetic_score(text: str, q_key: str, expected_truth: bool) -> float:
    """Deterministic synthetic per-question score for the offline smoke path.

    Maps (text hash, question key, expected ground truth) to a stable score
    in roughly [0, 1] without needing SBERT or any LLM. The score is shaped
    so that PSs whose seed says expected=True get a higher score on that
    question than PSs where expected=False, which is enough to exercise the
    axis_audit code path with non-degenerate input.
    """
    h = hashlib.md5(f"{text[:200]}|{q_key}".encode("utf-8")).hexdigest()
    base = (int(h[:8], 16) % 1000) / 1000.0  # uniform in [0, 1)
    return 0.55 + 0.35 * base if expected_truth else 0.10 + 0.25 * base


def smoke_extractor():
    print("\n[2/4] PS Extractor smoke test (downloads SBERT on first run)", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    extractor = PSExtractor()
    extractor._ensure_model()  # eager-load SBERT
    sample = MINI_CORPUS[4]["text"]  # poverty_signal
    scores = extractor.score_text(sample)
    print(f"  Input expected: poverty=True, others=False", file=sys.stderr)
    for q, s in scores.items():
        marker = "★" if q == "poverty" else " "
        print(f"  {marker} {q:<18} = {s:.4f}", file=sys.stderr)
    print(f"  ✓ Extractor produced 4-question scores", file=sys.stderr)
    return extractor


def smoke_audit_2(extractor=None, offline: bool = False):
    if offline:
        print("\n[2-3/4] axis_audit on synthetic deterministic scores "
              "(offline; no SBERT)", file=sys.stderr)
    else:
        print("\n[3/4] Audit 2 (PS extraction) on full mini-corpus", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    rows = []
    for rec in MINI_CORPUS:
        if offline:
            # Deterministic synthetic scores: a hash-based stand-in for
            # what the SBERT extractor would produce. Keeps the code path
            # exercisable without network access.
            scores = {
                q: _synthetic_score(rec["text"], q,
                                    rec["expected_question_truth"][q])
                for q in PATENT_QUESTIONS
            }
        else:
            scores = extractor.score_text(rec["text"])
        rows.append({
            "applicant_id": rec["applicant_id"],
            "stratum_race": rec["stratum"]["race"],
            "stratum_gender": rec["stratum"]["gender"],
            "stratum_school_tier": rec["stratum"]["school_tier"],
            **scores,
        })
    df = pd.DataFrame(rows)
    print(f"  Scored {len(df)} PSs"
          + (" (synthetic offline scores)" if offline else ""),
          file=sys.stderr)

    axis_columns = {
        "gender": "stratum_gender",
        "race": "stratum_race",
        "school_tier": "stratum_school_tier",
    }

    print(f"\n  Per-question DI at top-30% selection (small-n: indicative only):",
          file=sys.stderr)
    for q_key in PATENT_QUESTIONS:
        results = axis_audit(df, q_key, axis_columns, top_frac=0.3, n_bootstrap=50)
        print(f"\n    Question: {q_key}", file=sys.stderr)
        for axis, m in results.items():
            di = m["disparate_impact"]
            di_str = f"{di:.3f}" if not np.isnan(di) else "  N/A"
            print(f"      {axis:<14} DI = {di_str}  "
                  f"(g0={m['n_group0']}, g1={m['n_group1']})", file=sys.stderr)
    print(f"\n  ✓ Audit 2 path executed", file=sys.stderr)
    return df


def smoke_audit_1(mitigator):
    print("\n[4/4] Audit 1 (Bias Mitigator efficacy) on full mini-corpus", file=sys.stderr)
    print("-" * 60, file=sys.stderr)
    try:
        from examples.example_pipeline import score_texts
    except RuntimeError as e:
        print(f"  vaderSentiment not installed; skipping Audit 1.", file=sys.stderr)
        print(f"  Install with: pip install vaderSentiment", file=sys.stderr)
        return

    texts = [r["text"] for r in MINI_CORPUS]
    print(f"  Scoring {len(texts)} raw texts...", file=sys.stderr)
    baseline = score_texts(texts)
    print(f"  Applying Bias Mitigator...", file=sys.stderr)
    mitigated_texts = mitigator.batch(texts)
    print(f"  Scoring {len(texts)} mitigated texts...", file=sys.stderr)
    mitigated = score_texts(mitigated_texts)

    rows = []
    for i, rec in enumerate(MINI_CORPUS):
        rows.append({
            "applicant_id": rec["applicant_id"],
            "stratum_race": rec["stratum"]["race"],
            "stratum_gender": rec["stratum"]["gender"],
            "stratum_school_tier": rec["stratum"]["school_tier"],
            "score_baseline": baseline[i],
            "score_mitigated": mitigated[i],
        })
    df = pd.DataFrame(rows)

    axis_columns = {
        "gender": "stratum_gender",
        "race": "stratum_race",
        "school_tier": "stratum_school_tier",
    }
    base = axis_audit(df, "score_baseline", axis_columns, top_frac=0.3, n_bootstrap=50)
    mit = axis_audit(df, "score_mitigated", axis_columns, top_frac=0.3, n_bootstrap=50)

    print(f"\n  Mitigation effect (baseline DI → post DI per axis):", file=sys.stderr)
    for axis in base:
        b = base[axis]["disparate_impact"]
        m = mit[axis]["disparate_impact"]
        b_str = f"{b:.3f}" if not np.isnan(b) else "  N/A"
        m_str = f"{m:.3f}" if not np.isnan(m) else "  N/A"
        delta = m - b if not (np.isnan(b) or np.isnan(m)) else None
        delta_str = f"{delta:+.3f}" if delta is not None else "    --"
        print(f"    {axis:<14} {b_str} → {m_str}  (Δ = {delta_str})", file=sys.stderr)
    print(f"\n  ✓ Audit 1 path executed", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="AEDT toolkit smoke test")
    ap.add_argument(
        "--offline", action="store_true",
        help=(
            "Skip steps that require network access on first run "
            "(SBERT model download, spaCy NER model download, VADER "
            "lexicon download). Uses regex-only mitigation, synthetic "
            "deterministic scores in place of the SBERT extractor, and "
            "skips the VADER Audit-1 path. Suitable for CI / sandbox "
            "environments without internet access."
        ),
    )
    args = ap.parse_args()

    print("=" * 72, file=sys.stderr)
    title = "AEDT Fairness Audit Toolkit — Smoke Test"
    if args.offline:
        title += " (OFFLINE)"
    print(title, file=sys.stderr)
    print("=" * 72, file=sys.stderr)
    print(f"\nMini-corpus: {len(MINI_CORPUS)} hand-curated PSs", file=sys.stderr)
    print(f"  Demographic strata: 2 (White/Female/top_20, Black/Male/lower_tier)",
          file=sys.stderr)
    print(f"  Content seeds: 4 (control, poverty, illness, immigration)", file=sys.stderr)
    print(f"  Instances per cell: 2", file=sys.stderr)
    print(f"\nNote: with n=16, the DI numbers from this smoke test are not", file=sys.stderr)
    print(f"meaningful findings. They exist to verify the code path. For", file=sys.stderr)
    print(f"substantive results, run tools.generate_ps_corpus then", file=sys.stderr)
    print(f"tools.run_audit_1 / tools.run_audit_2 on the full corpus.", file=sys.stderr)

    if args.offline:
        print(f"\n--offline: skipping SBERT/spaCy/VADER model downloads. "
              f"Mitigator runs regex-only; extractor is replaced with a "
              f"deterministic synthetic stand-in.", file=sys.stderr)

    mitigator = smoke_mitigator(offline=args.offline)
    if args.offline:
        smoke_audit_2(extractor=None, offline=True)
        print("\n[4/4] Audit 1 (VADER) — skipped under --offline "
              "(VADER lexicon download not guaranteed offline).",
              file=sys.stderr)
    else:
        extractor = smoke_extractor()
        smoke_audit_2(extractor)
        smoke_audit_1(mitigator)

    # Also write the mini corpus to /tmp so user can manually run the CLIs
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        path = f.name
        for rec in MINI_CORPUS:
            f.write(json.dumps(rec) + "\n")

    print(f"\n{'=' * 72}", file=sys.stderr)
    print("Smoke test complete. All modules imported and ran without error.", file=sys.stderr)
    print(f"\nMini-corpus written to: {path}", file=sys.stderr)
    print(f"\nTo verify the CLI runners on the same mini-corpus:", file=sys.stderr)
    print(f"  python -m tools.run_audit_2 --corpus {path} --out-dir /tmp/audit_2_smoke",
          file=sys.stderr)
    print(f"  python -m tools.run_audit_1 --corpus {path} \\", file=sys.stderr)
    print(f"      --pipeline examples.example_pipeline:score_texts \\", file=sys.stderr)
    print(f"      --out-dir /tmp/audit_1_smoke", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
