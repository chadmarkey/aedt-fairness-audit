# Security and Responsible Disclosure

This is a research toolkit, not a production system. The most relevant
"security" concerns for users are:

1. **Privacy of input data.** The toolkit's defaults are designed to
   avoid persisting input text or model outputs to disk. If you change
   defaults to enable persistence, ensure you have authorization to
   retain the data you are processing.

2. **Authentication credentials.** The toolkit does not require API keys
   for its default workflow. If a downstream user adds API-key-dependent
   functionality (e.g., LLM-as-judge variants), that user is responsible
   for managing credentials per `.env` conventions.

## Responsible disclosure

If you discover a privacy bug (e.g., a code path that persists user data
when the user expected it not to), please open a private issue or
contact the maintainer directly rather than disclosing publicly.

If you discover a methodological error that would materially mislead
users (e.g., a fairness metric computed incorrectly, a patent-element
implementation that diverges from the patent in a way not documented in
[`DEVIATIONS_FROM_PATENT.md`](DEVIATIONS_FROM_PATENT.md)), please open
a public issue. Methodology errors should be visible to the community.
