---
name: adsgpt-branch-flow
description: The team's Git/GitHub flow for shipping one bug fix across environments in the adsgpt/Venxr workspace. Cut a bugfix branch from venxr_v2_main, cherry-pick the fix commits and push; then fork `<bugfix branch>_staging` from venxr_v2_staging, cherry-pick the same commits and push. Use whenever the user asks to put a fix on main/prod or staging, "fork a branch", "cherry pick", "make a bugfix branch", "push the changes", "name it like the bugfix + _staging", or to prepare a PR for venxr_v2_main or venxr_v2_staging, in any venxr repo (frontend, auth, llm_service, utility, MCP services, skill_service, ...).
---

# adsgpt branch flow

The workspace folder is not a git repo: every top-level folder is its own repo. A fix that touches several repos
repeats this flow in each one.

## Environment branches
| Branch | Environment | What a push does |
|---|---|---|
| `venxr_v2` | dev | builds and auto-deploys to Venxr dev and Vajra dev |
| `venxr_v2_staging` | staging | builds and auto-deploys to Venxr staging and Vajra staging |
| `venxr_v2_main` | prod | builds and auto-deploys to Venxr prod and Vajra prod |

Builds fire only on those exact branch names. Pushing a bugfix branch deploys nothing; **merging** into an environment
branch does. (The llm_service repo also posts a Teams notification on any push; that is expected.)

## The idea
One fix, written once as commits on a bugfix branch. Each environment gets its own branch cut from **that
environment's current tip**, and the **same commits are cherry-picked** onto it. The branch then differs from its
base by the fix and nothing else.

## Names
- `<bugfix-branch>`: the fix's name, in the team pattern `bugfix/<area>/<author>/<topic>`.
- The branch cut from `venxr_v2_main` is named **`<bugfix-branch>`**.
- The branch cut from `venxr_v2_staging` is named **`<bugfix-branch>_staging`**.
- If the user gives a different name, use theirs exactly. If the base name is unclear, ask once. Do not invent
  per-environment prefixes.

## Steps (per repo)
**0. Know the source commits.** They are the fix commits on the bugfix branch: `git log --reverse origin/<base>..<bugfix-branch>`
or a list of SHAs from the user. If the fix does not exist yet, write it once on the bugfix branch first.

**1. Main (prod)**
```bash
git fetch origin venxr_v2_main
git switch -c <bugfix-branch> origin/venxr_v2_main      # cut from main's CURRENT tip
git cherry-pick -x <sha> [<sha> ...]                    # the fix commits, oldest first
# verify (below), then
git push -u origin <bugfix-branch>
```

**2. Staging**
```bash
git fetch origin venxr_v2_staging
git switch -c <bugfix-branch>_staging origin/venxr_v2_staging
git cherry-pick -x <the same commits from the bugfix branch>
# verify (below), then
git push -u origin <bugfix-branch>_staging
```

**3. Dev (`venxr_v2`)** only when the user asks. Same cut-from-tip and cherry-pick. Push to `venxr_v2` itself only
if the user says to merge straight into dev; otherwise stop at the branch.

**4. Pull requests.** The user raises PRs manually (compare view). Give them the compare link, a title and a
description. Do not open a PR unless asked. Never merge.
`https://github.com/<org>/<repo>/compare/<base>...<branch>?expand=1`

Do this in a **detached worktree in a scratch directory** (`git worktree add --detach <dir> origin/<base>`) so the
user's own checkout and uncommitted work are never touched. Remove the worktree afterwards (no `--force` needed when
clean) and leave no temporary local branches behind.

## Verify before every push (all must hold)
- **Ahead/behind:** `git rev-list --left-right --count origin/<base>...HEAD` prints `0  N`: 0 behind, N = the number of
  fix commits.
- **Only the bug's files:** `git diff --stat origin/<base> HEAD` (two-dot, which is what a manual compare shows) lists
  just the fix's files, and matches the three-dot diff `origin/<base>...HEAD`.
- **Each environment has its own code.** Search *that* environment's tree for the same problem: a file or feature
  that exists only on staging or only on main may need its own change. Put it in a **separate, clearly named commit**
  and say so in the description. Do not fold it into the cherry-picked one.
- **Conflicts:** resolve minimally and keep that environment's existing code (for example its own config class)
  rather than overwriting it. Say in the commit message that it was adapted from `<sha>`.
- **Run the repo's checks on that branch's tree** (tests, compile, type-check, build). Report exactly what ran and
  what did not. Never claim a check that was not run.
- **Judge CI against its baseline.** Compare with other recent PRs on the same base before blaming the change.

## Never
- Never cut from an old branch or reopen an old PR whose base is stale. It shows as "behind" and looks like it changed
  every file. Always cut a fresh branch from the **current** tip.
- Never push to `venxr_v2`, `venxr_v2_staging` or `venxr_v2_main` unless the user explicitly says so for that environment.
- Never force-push or rewrite pushed history. Add a follow-up commit instead.
- Never merge a PR, and do not open one unless asked.
- Never put a fix directly on a PR branch after it has merged; make a new branch from the current tip.

## After the user says it is merged
Check the `Build <Env>` run in each repo: the build job and **both** deploys (Venxr and Vajra). If something fails,
read the failing step's log first and decide whether the change caused it. Common causes seen here that are *not*
the change: unpinned dependencies drifting (an image build breaking), and SSH/SSM steps on a server failing. Fix a
real problem with a **new** branch from the current tip, using this same flow.

## Commit and PR text
- Commit and PR title: `type(scope): imperative summary`, for example `fix(tv): use the runtime product name in the TV upload dialogs`.
- Description sections: **Ticket**, **What**, **Notes specific to this environment**, **Verification** (the checks that
  actually ran), **Not verified**, **Deploy** (env vars per deployment and anything to restart).
- Only verified facts. No AI attribution lines, no secrets. Do not mention a local Docker build in descriptions.

## Final report (per repo)
| Repo | Branch | Cut from | Ahead / behind | Files | Checks run |
|---|---|---|---|---|---|

Then list anything that differs per environment, what was not verified, and the compare links.

## Ask the user if unclear
The exact bugfix base name, and whether dev should get the same treatment. Do not guess.
