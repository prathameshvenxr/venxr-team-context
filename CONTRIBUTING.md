# Contributing

This is a **private** repo. It contains internal architecture notes and a list of known security issues. Do not make it
public, do not paste secrets, tokens, customer data or real account IDs into any file, and keep the collaborator list short.

- **Requirements:** change them in the service's own repo, not here. Then run `scripts/sync-requirements.sh` and
  `python scripts/pin_report.py`, and update the decision table in `requirements/README.md`.
- **The `adsgpt-engineering` guide:** it is only useful while true. When you verify or change a fact, update the date
  in the file you touched. Prefer deleting a stale claim to leaving it. Facts nobody confirmed stay marked unconfirmed.
- **Skill and agent edits:** keep the agent read-only (its `tools` line has no Write or Edit). Keep the loop skill's stop
  rules: two failures of one idea means stop and ask.
- **Commits:** a short conventional message. No generated-by trailers.
- **Before you commit:** `python -m json.tool` the manifests, and check that no file contains a secret.
