# Contributing

Contributions welcome.

## Useful contribution areas

- Alternative Bias Mitigator implementations (transformer-based NER,
  alternative substitution inventories, multilingual support)
- Synthetic data generators with explicit content-equivalence validation
- Sentiment-instrument harnesses (VADER, RoBERTa, Claude, GPT-class
  wrappers) for cross-instrument robustness checks
- Plotting utilities (DI bar plots, threshold sweeps, counterfactual
  flip diagrams)
- Unit tests on canonical examples for each module
- Documentation: README clarifications, additional usage examples,
  notebook tutorials

## Process

1. Open an issue describing the proposed change before writing code.
2. Submit a pull request that:
   - Maintains privacy-safe defaults (no disk persistence by default,
     no PII in tests or examples)
   - Updates [`DEVIATIONS_FROM_PATENT.md`](DEVIATIONS_FROM_PATENT.md) if
     the change affects fidelity to the patent
   - Includes any new dependencies in `requirements.txt`
3. PRs that introduce vendor-specific behavior (i.e., behavior tuned to
   match a specific deployed system rather than the patent's
   disclosure) will be declined.

## Privacy expectations

Do not commit:

- Real applicant data of any kind
- API keys, credentials, or environment files containing secrets
- Output artifacts from runs on real data
- Information obtained through unauthorized access to any system

Datasets useful for testing should be described in an issue rather than
committed; we will help work out a synthetic-equivalent or a
reference-by-pointer arrangement.
