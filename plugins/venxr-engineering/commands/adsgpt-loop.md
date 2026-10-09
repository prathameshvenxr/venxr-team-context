---
description: Run a change in the adsgpt/Venxr workspace as a bounded, evidence-driven loop (adsgpt-loop skill)
argument-hint: <what to change or fix, and how we will know it worked>
---

Use the `adsgpt-loop` skill for this task, loading `adsgpt-engineering` first for the area-specific rules.

Task: $ARGUMENTS

Start with step 0 (goal, done check, budget, repos in play) and show it before editing anything. If no done check
exists, define one first. Follow the loop, keep the ledger visible, stop after two failures of the same idea, and
finish with the report format from the skill. Read-only until the user has asked for code changes; never commit or
push unless asked.
