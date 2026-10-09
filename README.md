# venxr-team-context

Shared engineering context for the Venxr team: how the adsgpt/Venxr workspace fits together, a Claude Code plugin that
enforces it, and a snapshot of every service's dependencies so the team can sort them out together.

> **Private.** This holds internal architecture notes and a list of known security issues. Keep the repo private, keep
> the collaborator list short, and never add secrets or customer data.

## What is in here
| Path | What |
|---|---|
| `plugins/venxr-engineering/` | The Claude Code plugin (below) |
| `.claude-plugin/marketplace.json` | Lets the team install the plugin from this repo |
| `requirements/` | Every service's dependency files, an analysis, and a decision table. **Start here for dependency work** |
| `docs/workspace-map.md` | Repos, roles, the two deployments x three environments, branches |
| `docs/product-name-branding.md` | The Venxr/Vajra product-name fix: what changed and the per-instance env checklist |
| `scripts/` | `sync-requirements.sh` (refresh snapshots), `pin_report.py` (classify pins, CI-style check) |
| `NOTICE` | Attribution for the MIT-licensed work this adapts (ponytail, ECC) |

## The plugin: `venxr-engineering`
| Piece | Use it for |
|---|---|
| Skill `adsgpt-engineering` | Rules, architecture map and cross-repo contracts. Load before touching any service. Includes per-area references (llm_service, governance, MCP, edge services, frontend, contracts, known issues) |
| Skill `adsgpt-loop` | The same rules as a **bounded loop**: frame, understand, blast radius, smallest edit, verify, decide, with a visible ledger, a budget, and a hard stop after two failures of one idea. The ponytail "laziest thing that works" ladder is built in |
| Agent `adsgpt-security-reviewer` | **Read-only** security review tuned to this stack (gateway/JWT/service keys, impersonation, tool write-gating, raw SQL, SSRF, sandbox, mail, per-deployment env defaults). Labels findings NEW / KNOWN / UNVERIFIED |
| Skill `adsgpt-branch-flow` | The Git flow for shipping a fix across environments: a bugfix branch cut from `venxr_v2_main`, then `<bugfix branch>_staging` cut from `venxr_v2_staging`, the same commits cherry-picked onto each, verified, pushed. Never pushes to an environment branch or opens/merges PRs unless asked |
| Command `/adsgpt-loop <task>` | Start the loop on a task |
| Command `/adsgpt-security-review [repo or path]` | Run the reviewer on the current diff |
| Command `/adsgpt-branch-flow <bugfix-branch> [shas] [repos]` | Ship a fix to main then staging with the cherry-pick flow |

### Install
Teammates need read access to this repo and `gh auth login` (or an equivalent git credential).
```
/plugin marketplace add prathameshvenxr/venxr-team-context
/plugin install venxr-engineering@venxr-team
```
Then restart the session. The skills are namespaced, e.g. `venxr-engineering:adsgpt-loop`.

The guide refers to the folder that holds all the repos as `<workspace>`; it does not assume any machine's path.

## Status and limits (as of 2026-10-09)
- Manifests are valid JSON, and `sync-requirements.sh` reproduces the snapshots exactly. `pin_report.py` runs and its
  `--fail-on-unpinned` exit code works.
- The skills and agent are written from the existing `adsgpt-engineering` guide (verified by reading code on
  2026-10-01, nothing run), the ponytail skill and ECC's security reviewer. **They have not been exercised on a real
  task yet**, so expect to tune the wording once the team has used them.
- The `adsgpt-engineering` references can be stale. Trust the code over them, and update the date when you verify a fact.
- Branch roles (dev `venxr_v2`, staging `venxr_v2_staging`, prod `venxr_v2_main`) come from the repos' build workflows: see `docs/workspace-map.md`.
