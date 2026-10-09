---
name: adsgpt-engineering
description: Coding rules, architecture map and cross-service guardrails for the adsgpt / Venxr workspace (the folder holding venxr_backend-* services, skill_service, tv_planner_mcp_service, shared_components, frontend/). Use this skill whenever you write, edit, review, plan, debug or estimate the blast radius of a change anywhere in that workspace, even a "one-line" change, and whenever the user asks what breaks if X changes, where something lives, or how a flow works end to end. It covers the llm_service LangGraph agent (graph.py, state.py, ads_orchestrator.py, domain_lead.py, risk_manager.py, mcp_manager.py, prompt registry, create/rulebook lane, deep analysis, reporting replay, QC), governance (campaign groups, alert rules, Default Governance, utility-service Celery), the per-platform MCP services (meta, google_ads, dv360, amazon_ads, meesho, tv_planner), gateway, auth/JWT/impersonation, Tier-1 skills (skill_service + gateway skill_router), the sandbox, and the React frontend (SSE stream, api-client, UI_CONTRACT). Most breakage here comes from silent string couplings between repos, not from the edited lines, so load it before the first edit. Do not use for other projects.
---

# adsgpt engineering rules

Write the code a careful senior engineer would: the smallest change that works, in the right layer, that breaks nothing in any other service. This workspace is full of silent couplings — hand-copied registries, tool names hard-coded in other repos, regex routers, DB rows that override code — so understanding comes before typing.

## Workspace ground rules
- `<workspace>` is **not** a git repo. Every top-level folder is its own GitHub repo (org `Venh-Analytics-Pvt-Ltd`), mostly on branch `venxr_v2` (`main` for `shared_components`, `venxr_backend-infra`, `venxr-wiki`). A change spanning services = several repos, several PRs, and a deploy order. Say so up front.
- Branch roles: `venxr_v2` is **dev** (confirmed by the team), `venxr_v2_staging` is **staging** and `venxr_v2_main` is **prod** (read from the repos' build workflows, which trigger on exactly those branches). A push to one builds and auto-deploys to both Venxr and Vajra for that environment. See `adsgpt-branch-flow` for how fixes reach them.
- Two deployments (Venxr, Vajra) x three environments (dev, staging, prod) = 6 instances, built from the same code. Anything user-visible that names the product must come from config, never a literal (see `references/contracts.md`, "Product name").
- **Read-only by default.** Only write files in the codebase when the user explicitly asked for a code change. Plans, diagrams, notes and analysis go to the session scratchpad (or where the user says), never into a repo tree. Subagents you spawn for analysis must be told they are read-only.
- Commit or push only when asked. Never edit an applied migration.
- Trust code over docs. Many READMEs, docstrings and wiki pages are stale (list at the end).

## Workflow
1. **Understand.** Open the reference for the area you're touching (map below), then trace the real flow in code. Say it back in 3–5 lines. If you can't, you're not ready to edit.
2. **Blast radius.** List every symbol, string, tool name, enum value, URL path, header or JSON key you'll touch. Grep for each across **all** repos, not just the current one: `grep -rn "<name>" <workspace> --include=*.py --include=*.ts --include=*.tsx --include=*.json`. Then run the matching checklist in `references/contracts.md`.
3. **Plan with checks.** `1. [step] -> verify: [command or observable result]`. Bug: reproduce first (failing test where tests exist). Behavior change: tests green before and after.
4. **Minimal diff** in the right layer, matching local style (see the area reference). No speculative flags, config, abstractions or new nodes/domains/queues/tables when a function in the existing layer does it.
5. **Verify** with the check you planned. Be honest: say exactly what ran and what couldn't.
6. **Report:** files changed (per repo), what was verified, what wasn't, rollout order across repos, and unrelated issues noticed but left alone.

If an attempt fails twice, stop editing. Re-read the flow, say what you misunderstood, then fix the understanding or ask. Don't try a third variant of the same idea. Once the check passes and the diff is minimal, stop polishing.

## Behaviour
- State assumptions. If the request has two readings, show both and ask instead of picking silently.
- Every changed line must trace to the request. Don't refactor, reformat or "fix" adjacent code. Mention unrelated bugs; don't touch them. Remove only the imports your change orphaned.
- If a simpler approach exists, say so and push back.

## Reference map — read the one you need
| You are touching… | Read |
|---|---|
| llm_service graph, nodes, state, orchestrator routing, domain_lead, deep analysis, prompts, create/rulebook lane, reporting replay, QC, memory, env flags, tests/CI | `references/llm-service.md` |
| Governance: campaign groups, alert rules, metrics, Default Governance, utility-service Celery/email/REST | `references/governance.md` |
| Any MCP service (meta, google_ads, dv360, amazon_ads, meesho_seller, tv_planner), adding/renaming a tool or arg | `references/mcp-services.md` |
| Gateway, auth/JWT/impersonation/service key, skill_service (Tier-1 skills), sandbox, shared_components | `references/edge-services.md` |
| frontend/ (SSE consumer, api-client, routing, UI_CONTRACT, generated create spec) | `references/frontend.md` |
| Anything that crosses a repo boundary (names, enums, headers, paths, DB schemas) | `references/contracts.md` |
| You hit odd behaviour and wonder "is that a known bug?" | `references/known-issues.md` |

## Facts that most often change how you code
- **Prompts in code may not be live.** `engine/prompt_registry.get_active_prompt` returns the active DB row (`agent_prompt_versions`) over the code constant, including `domain:<d>` prompts from `domains/*/config.json`. Editing a prompt in code can do nothing at runtime until it's published. `VENXR_PROMPTS_FROM_CODE` forces code prompts.
- **`domains/*/config.json` is cached per process** (`load_domain_leads`); config edits need a restart.
- **Write vs read is decided by the tool's name.** `risk_manager.is_write_tool` splits on `_` and checks verbs (create/update/delete/add/…). Write tools are stripped from every domain not in `WRITE_DOMAINS = {management, tv_planner, governance}`. A read tool named `..._add_...` disappears from analyze.
- **No human approval for governance writes.** `campaign_group_*` tools resolve to Tier 1 (`RISK_TIERS.get(name, 1)`, no entry). Don't assume a gate exists.
- **Governance is two unrelated systems:** chat-driven groups/alert rules (`campaign_management`, MCP only, no REST/UI) and Default Governance (`default_governance`, REST + Flows page). They share no tables.
- **Money units differ per metric.** `ALERT_CURRENCY_METRICS = {spend, cpc, cpm, cpa}` are paise; conversion_value, aov, revenue_per_click are rupees. The governance prompt currently says ×100 for those three — a live bug (see known-issues). Any metric change must state its unit at every layer.
- **Tier-1 skills exist in three hand-synced copies:** `skill_service/skills/tier1/*` + `registry.py`, gateway `skill_router.py` `TIER1_SKILLS`/`SLUG_ALIASES` (its `data_contract` is the one actually used at runtime), and llm_service `features/my_skills/migrations/0012_seed_tier1_system_skills.py` (whose `triggers[0]` is what the frontend sends as `skill_slug`).
- **MCP error envelopes are not uniform** (meta `{success,data|error}`, google raw/`{"error": str}`), and QC/name_resolver/frontend parse them by shape. Don't "normalize" one service without updating consumers.
- **Deep analysis** has no classifier node: the LLM `orchestrator` routes, and `_DEEP_ANALYSIS_RE` picks the deep-analysis skill, which is loaded from a DB registry row (`memories`, `memory_type='skill_registry'`) — not something to hunt for on disk. `analysis_tier` is never set by live code (always T1). Phases are pre-planned; answers aren't token-streamed.
- **QC is its own node** (`qc_check`), never called by create or governance; reporting and bulk_create reuse its fetch helpers and tree tools.
- **Background governance handlers support Meta and Google Ads only**; others raise `NotImplementedError` (caught and counted as failed/not_supported).

## Testing reality (don't overclaim)
| Repo | What exists | How to run |
|---|---|---|
| llm_service | ~99 test files in `engine/tests/`; CI `tests.yml` has a **blocking `rulebook` job** (rulebook + field-extraction tests + two prompt-contract string asserts) and an informational `suite` job (baseline 18 failures, needs Postgres+Redis) | `python -m pytest -q -p no:logging engine/tests/<file>` from `venxr_backend-llm_service/` (needs `requirements_test.txt` and `../shared_components`) |
| meta MCP | `tests/test_healing.py`, `tests/test_validators.py` (pytest not in requirements) | `pytest tests/ -v` |
| tv_planner MCP | `tests/test_validators_payload.py` | `pytest tests/ -v` |
| frontend | one trivial vitest file; CI only builds | `npm test`, `npm run lint`, `npm run build` |
| utility-service, gateway, skill_service, sandbox, dv360/google/amazon/meesho MCP | none (stubs only); auth has 3 tests | write one focused test for new logic, or say plainly verification was manual |

For hot-file edits in llm_service run the nearest tests: `test_orchestrator_routing`, `test_risk_gate`, `test_working_set_governance`, `test_wiring`, plus the rulebook gate if you touched create.

## Stale docs — do not trust
`engine/ARCHITECTURE.md` (old CRUD graph, intent_classifier), `docs/CREATE_V2_NATIVE_PLAN.md` diagram (create is a top-level node now), utility-service `README.md`, meta `DOCS.md` (lists tools that don't exist), `frontend/src/MODE_STATE_GUIDE.md` (paths and hook unused), `UI_CONTRACT.md` CSS path (`src/styles/index.css` is real), `shared_components/README.md`, `venxr-wiki/` (snapshot 2026-07-18), docstrings citing `core/…` or `agent/…` paths (real: `infra/`, `engine/`), comments saying `WRITE_DOMAINS={"management"}`, the `default_governance` "every 5 minutes" docstring (real: crontab 10,40), `venxr_backend-infra/docker-compose*.yml` build contexts (old monorepo folder names; no skill_service, no utility Celery workers). `manage.py sync_prompts` is broken (imports deleted modules). Ignore llm_service probe leftovers: `_probe_narration.py`, `probe_cc.py`, `pytest_out.txt`, `dummy-file-2.md`.

## Done means
Plan steps verified, diff holds only requested lines, every matching checklist in `contracts.md` is satisfied in every repo it names, and the reply states what ran, what didn't, the cross-repo rollout order, and unrelated issues noticed but not fixed.

## Related in this plugin
- `adsgpt-loop`: the same rules run as a bounded loop (understand, blast radius, minimal edit, verify, repeat) with the ponytail ladder built in. Use it for any change that needs a verified result.
- `adsgpt-branch-flow`: how a fix is shipped across environments (bugfix branch from `venxr_v2_main`, then `<bugfix branch>_staging` from `venxr_v2_staging`, cherry-picked, verified, pushed). Use it whenever the user asks to put a fix on main or staging.
- `adsgpt-security-reviewer` agent (`/adsgpt-security-review`): read-only security pass tuned to this stack. Run it before finishing changes to auth, gateway, skill_service, sandbox, governance writes, secrets or mail.
