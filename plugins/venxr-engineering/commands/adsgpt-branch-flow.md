---
description: Ship a bug fix to main then staging with the team's cherry-pick branch flow (adsgpt-branch-flow skill)
argument-hint: <bugfix-branch-name> [commit shas] [repos]
---

Use the `adsgpt-branch-flow` skill for this task.

Fix to ship: $ARGUMENTS

Work per repo in a detached worktree. Cut the main branch (named exactly like the bugfix branch) from the current
`origin/venxr_v2_main` and the staging branch (`<bugfix-branch>_staging`) from the current `origin/venxr_v2_staging`.
Cherry-pick the fix commits with `-x`, verify the two-dot diff shows only the bug's files and the branch is 0 behind,
run the repo's checks, then push the branch. Do not push to an environment branch, do not open or merge PRs unless I
ask. Finish with the per-repo report and the compare links.
