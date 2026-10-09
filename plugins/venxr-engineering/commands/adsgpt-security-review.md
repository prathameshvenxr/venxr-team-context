---
description: Read-only security review of a change in the adsgpt/Venxr workspace (adsgpt-security-reviewer agent)
argument-hint: [repo or path] (default: the uncommitted diff and the branch diff against venxr_v2)
---

Launch the `adsgpt-security-reviewer` agent on: $ARGUMENTS

If nothing was given, review the uncommitted changes and the branch diff against `venxr_v2` in the repo you are
currently in. Tell the agent it is read-only. Relay its report as written: the severity counts, which findings are
NEW versus KNOWN (already in `known-issues.md`) versus UNVERIFIED, the env/deploy items per deployment, and what it
did not check. Do not fix anything as part of this command.
