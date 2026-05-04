# Post-Public-Flip Commands

Run these after `gh repo edit chadmarkey/aedt-fairness-audit --visibility public --accept-visibility-change-consequences`.

Several settings (private vulnerability reporting, secret scanning, Dependabot,
auto-merge) require a public repo and were not enabled during the private setup.
Run these commands once after flipping public.

```bash
# Private vulnerability reporting (security issues come in privately)
gh api -X PUT /repos/chadmarkey/aedt-fairness-audit/private-vulnerability-reporting

# Secret scanning + push protection
gh api -X PATCH /repos/chadmarkey/aedt-fairness-audit \
    -f "security_and_analysis[secret_scanning][status]=enabled" \
    -f "security_and_analysis[secret_scanning_push_protection][status]=enabled"

# Dependabot security updates
gh api -X PATCH /repos/chadmarkey/aedt-fairness-audit \
    -f "security_and_analysis[dependabot_security_updates][status]=enabled"

# Auto-merge (didn't take while private; retry once public)
gh api -X PATCH /repos/chadmarkey/aedt-fairness-audit -F allow_auto_merge=true

# CodeQL default setup (free for public repos)
gh api -X PATCH /repos/chadmarkey/aedt-fairness-audit/code-scanning/default-setup \
    -f state=configured -f query_suite=default \
    -f "languages[]=python"

# v0.1.0 release (the tag is already pushed; this creates the GitHub release)
gh release create v0.1.0 \
    --repo chadmarkey/aedt-fairness-audit \
    --title "v0.1.0 — initial public release" \
    --notes "Fairness measurement library for automated employment decision tools. Implements Claim 1 input-side bias mitigation and column 10 four PS-question extraction (SBERT and LLM variants) of U.S. Patent No. 12,265,502 B1, plus auditing tools, validation diagnostics, and publication-grade plot scripts. See RESULTS.md for example reference outputs."
```

If a coordinated brigade hits the issue tracker in the first 24-48 hours, flip
interaction limits temporarily:

```bash
gh api -X PUT /repos/chadmarkey/aedt-fairness-audit/interaction-limits \
    -f limit=existing_users -f expiry=one_week
```
