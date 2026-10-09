# llm_service (venxr_backend-llm_service)

Verified 2026-10-01 at HEAD e8a984e by reading code (nothing run). Line numbers drift; grep the symbol before trusting a number.

## Contents
1. Request path · 2. Graph · 3. Orchestrator routing · 4. domain_lead spoke · 5. Risk gate & tools · 6. Prompts & config · 7. Deep analysis · 8. Create / rulebook lane · 9. Reporting & QC · 10. Memory · 11. Env flags · 12. Style · 13. Tests & CI · 14. Sync lists

## 1. Request path
FE `POST /llm/chat/v2/` (gateway `/api/llm/` or `/llm/`, prefix stripped) → `chat/urls.py` (`chat/` and `chat/v2/` both → `views.chat_view`, `chat/views.py:~301`) → middleware `JwtIdentityMiddleware` → RateLimit → TokenAllowance (402) (`settings.py:54-56`) → graph → SSE via `chat/graph_stream.py` (`data: {json}\n\n`, `chat/sse.py`).
JWT: HS256 with `AUTHENTICATION_SERVICE_SECRET_KEY` (`settings.py:269-273`, `chat/auth.py`); claims `user_id`/`uid`/`sub`, `email`, `agency_id`. Settings refuse to boot without the key unless DEBUG.

## 2. Graph (`engine/graph.py`, `build_graph_v2` at :651)
Nodes (:663-677): load_context, pre_load_memories, orchestrator, scope_guard, domain_lead, phase_check, qc_check, persist_memories, reflect, self_healer, skill_writer, human_gate, portfolio_audit, create, bulk_create. Compiled with `interrupt_before=["human_gate"]` (:838).
- `_route_after_pre_load_memories` (:70) short-circuits wizard continuations to qc_check / bulk_create.
- `_route_after_orchestrator` (:410): no tasks → scope_guard; qc → qc_check; bulk_create; create; else `_build_domain_sends` (:159) = one `Send("domain_lead", domain_state)` per phase-1 task. portfolio_audit route is commented out (:426) → node currently unreachable.
- `phase_check` (:495-535) pops the next pre-planned phase; later phases rebuild tasks from a narrower dict (:537-548).
- Tail (:746-761): persist_memories → reflect → self_healer → skill_writer → human_gate.
- `_DATA_PRODUCING_DOMAINS` (:238): meta, google, management, utility, governance, transform, tv_planner.
- Governance add guard: `_GOVERNANCE_ADD_RE` (:273), `_guard_governance_add_not_dropped` (:280, called :459).
- State: `AdsAgentState` (pydantic, `engine/state.py:251`), `DomainState` (TypedDict, :538). Fields written by parallel `Send` spokes need reducers (e.g. `subagent_results` :394, `completed_steps` :568). Cross-turn fields keep their `Annotated` reducer.

## 3. Orchestrator (`engine/nodes/ads_orchestrator.py`, ~3.7k lines)
LLM router. Output: intents, phases[], tasks{domain, task, platform}. `_VALID_DOMAINS` (:51-54; comment at :46 says keep in sync with domain_lead routing and config.json). Domain table row for governance ~:83, routing bullets ~:115-117. `_GOVERNANCE_INTENT_RE` (:907) stops the create lane hijacking governance. Existing groups prefetched from Entity Store: `list_entities(user_id, "governance", "campaign_group")` (~:2284). CI asserts the string `"Memory never narrows platform scope"` is in `ORCHESTRATOR_SYSTEM_PROMPT`; don't edit it away.

## 4. domain_lead spoke (`engine/nodes/domain_lead.py`, ~6.5k lines)
`_build_domain_subgraph` (:5930): entry → react_execute or planner → execute (per batch, asyncio.gather inside a batch) → synthesize. `domain_lead_node` at :6216. `_run_task` at :2148, per-tool risk check ~:2265. `DOMAIN_MAX_RETRIES` (settings :380, default 2) = 2 attempts total. `FANOUT_MAX_BRANCHES` (settings :394, default 8) caps one tool fanning out across many entities (:3046), not the orchestrator's Send fan-out.
Governance deterministic guards inside `_run_task`: alert_emails default 2390-2413, name→id resolution 2414-2592, fabricated-group block 2595-2649. Extend them there.
`CREDENTIAL_INJECTION_MAP` (:287). Domain configs loaded once per process by `load_domain_leads()` (:1387). `_upstream_calls` stripped before output reaches the LLM (~:4066-4087).

## 5. Risk gate & tools
- `infra/risk_manager.py`: `RISK_TIERS` short names (:25-56) matched by suffix; `WRITE_DOMAINS = {management, tv_planner, governance}` (:96); `is_write_tool` = name split on `_` vs `_WRITE_VERBS` (:99-139); `tool_tier` (:142-157) sends unlisted writes to tier 3/2; `get_tool_tier` exact lookup `RISK_TIERS.get(name, 1)` (:191-193) and `assess_dag_risk` (:178-187) also exact → prefixed names are tier 1 there.
- `infra/mcp_manager.py`: `_get_mcp_servers` (:389-411, streamable_http), `_SERVER_TO_PLATFORM` (:415), `DOMAIN_TO_SERVER` (:425-434), offline stub tools from `ToolConfig` rows (:444-516; `manage.py seed_tools`), live tool cache TTL (:476-484), `_filter_tools_for_domain` (:556-607: prefix allowlist + strip writes for read-only domains).
- `infra/mcp_tool_sync.py`: registers all servers' tools into `SkillRegistry` (pgvector, `infra/registry.py`) at boot (`memory_app/apps.py:145,170`) or `manage.py sync_mcp_tools`. `_SERVER_CANONICAL_DOMAIN` (:43-50, utility default → analytics), `_SERVER_PREFIX_OVERRIDES` (:55-60: `drive_`→utility, `campaign_group_`→governance).
- `mcp_client/client.py`: platform → token header map (:31-37), no-token platforms (:51), service-key token fetch (:55-70).
- MCP URLs: `settings.py:215-228` (`MCP_URLS`). amazon_ads is in `MCP_URLS` but not in `_get_mcp_servers`; meesho isn't in `MCP_URLS`.

## 6. Prompts & config
- `engine/prompt_registry.py`: `get_active_prompt(entry_key, fallback)` (:83) → active row in `agent_prompt_versions` beats code (60s cache), including `domain:<d>` (`domain_lead.py:~4273`). `VENXR_PROMPTS_FROM_CODE` (:72) ignores DB prompts (recommended on the shared dev DB).
- `manage.py sync_prompts` is broken: `_registry()` (`llm/management/commands/sync_prompts.py:59-66`) imports deleted modules. Don't rely on `--check`.
- `domains/<d>/config.json` keys: `system_prompt`, `mcp_server`, optional `tool_allow_prefixes` (governance `campaign_group_`, tv_planner `tv_`, utility `drive_`). No per-tool lists, but some prompts name tools.

## 7. Deep analysis
Code in `features/analysis/` (planner `nodes/planner.py`, `apply_recipe_requires` :1233, `dag_executor`, `analyzers/skill_select.py`, `analyzers/skill_gate.py`). `_DEEP_ANALYSIS_RE` (skill_select.py:52) → deep skill with `intensity="deep"` (:380-386), resolved from a `memories` row `memory_type='skill_registry'` (`_registry_deep_analysis_skill` :138). Global gate `SYSTEM_DEFINED_SKILLS_ENABLED` (settings :246, default true). `analysis_tier` default only (state.py:377). To fetch different data, change the planner/recipe, not the graph. Sandbox calls: `engine/core/sandbox_client.py` (never raises; data must be tenant-scoped), used by `step_ops.py:382` and `dag_executor.py:268`.

## 8. Create / rulebook lane
`create` is a top-level graph node (`features/create/create_node.py`), not inside domain_lead. Engine in `features/create/rulebook/` (engine, registry, resolvers, shadow, lane, expr.py, compile_meta/google). Sources `features/create/rulebooks/sources/*.json` → `manage.py sync_rulebook [--check|--dry-run]` → `rulebooks/compiled/spec.json` (gitignored; the frontend generator reads it). `VENXR_RULEBOOK_CREATE` default true (create_node.py:93-100; its args are ignored). `VENXR_CREATE_PAUSED` default true (lane.py:116). CI asserts `"evidence" in _EXTRACT_SYSTEM` (`engine/nodes/field_collector.py:~871`). bulk_create: `features/bulk_create/` (`@durable_task(max_retries=0)` because publishing spends money).

## 9. Reporting & QC
- Reporting: chat saves `AnalysisSpec{tool,args}` (domain_lead.py:53-176); templates replay through `features/reporting/controllers/replay_controller.py`; only tools in `REPLAYABLE_TOOLS` (`features/reporting/constants.py:25-42`) replay — unknown tools are skipped with a log warning; blocks run sequentially; public share = UUID, no auth, no expiry, replays as owner. `META_DETAIL_TOOL_BY_LEVEL` (:66-70).
- QC: `features/qc/qc_node.py`; Celery queues `llm_qc_run/merge/upload`; rules user-uploaded, LLM-judged; stored as `ChatMessage(step="qc_report")` (`qc_store.py:142-146`). Fetchers call tools by hard-coded names (`qc_data_fetcher.py`, `qc_data_fetcher_google.py`) and assume each service's envelope shape. `GuidedFlowRun/Step` shared by QC and governance flows.

## 10. Memory
`memory/` (core.py layers with TTLs, entity_store.py, retriever.py); nodes `pre_load_memories`/`persist_memories` in `engine/nodes/memory_manager.py:171,279`; admin commands in `memory_app/management/commands/`. Entity Store keys (domain, entity_type) are strings other code queries by.

## 11. Env flags (verified readers)
`VENXR_V2_ACTIVE` (settings :476, effectively dead), `VENXR_RULEBOOK_CREATE`, `VENXR_CREATE_PAUSED`, `VENXR_RULEBOOK_SHADOW` (shadow.py:49), `VENXR_WORKING_SET` (default off), `VENXR_SKILLS_DB_SOURCE` (default off), `VENXR_PROMPTS_FROM_CODE`, `VENXR_REACT_DOMAINS`/`VENXR_REACT_FORCE_ALL` (lane_policy.py:35,40), `VENXR_SESSION_LEDGER` (default on), `VENXR_CONTEXT_OFFLOAD` (engine/core/base_lead.py:39), `VENXR_DRY_RUN` (state.py:516), `LANGGRAPH_USE_MEMORY_SAVER` (graph.py:789), `TV_PLANNER_ENABLED`, `SANDBOX_URL`, `SYSTEM_DEFINED_SKILLS_ENABLED`.

## 12. Style
- `logger = logging.getLogger(__name__)`, lazy `%s`, prefix with node (`"executor[governance]: ..."`).
- Engine/MCP code is async; ORM from async via `infra.db_async.db_sync_to_async` (:41, `thread_sensitive=False`).
- Executor guards return `[tool=... status=blocked]` text instead of raising; optional pre-fetches are swallowed with `logger.warning`.
- Long jobs: `@durable_task` from `jobqueue` (shared_components) with an explicit queue; re-raise.
- Modern hints (`dict | None`). Comments explain why and cite incidents/dates for non-obvious guards — keep that habit.

## 13. Tests & CI
- `pytest.ini`: `asyncio_mode=auto`, ignores `features/analysis/analyzers/test_flow.py`. `engine/tests/conftest.py` setdefaults `llm_service.settings_test` (SQLite /tmp, no migrations, MemorySaver, `SKIP_SKILL_SYNC`), fixtures `emit_mock`, `state` (make_state), meta/google schemas. Mock LLM/MCP with `unittest.mock.AsyncMock`.
- Install: `pip install -r requirements.txt -r requirements_test.txt` with `../shared_components` beside the repo (editable `jobqueue`).
- `.github/workflows/tests.yml` (push to main/master/venxr_v2_merge/feature/**, all PRs; Python 3.11; `DJANGO_SETTINGS_MODULE=llm_service.settings`, `OPENAI_API_KEY=dummy`):
  - **blocking `rulebook`**: `python -m pytest -q -p no:logging engine/tests/test_rulebook_{expr,schema,meta_coverage,registry,engine,shadow}.py`, then `engine/tests/test_field_extraction_evidence.py`, a resolver check (continue-on-error), and the two prompt-string asserts above.
  - informational `suite`: `python -m pytest engine/tests/ -q -p no:logging --ignore=engine/tests/debug_e2e.py` with Postgres+Redis; fails only if FAILED count > 18.
- Nearest tests for hot files: `test_orchestrator_routing` (pure functions, no Django), `test_risk_gate`, `test_working_set_governance`, `test_wiring`.

## 14. Lists to keep in sync (llm_service-internal)
- New domain: `domains/<d>/config.json`, `_VALID_DOMAINS`, orchestrator prompt table + routing bullets, `WRITE_DOMAINS` if it writes (else write tools are silently stripped), `_DATA_PRODUCING_DOMAINS` if it produces data, `DOMAIN_TO_SERVER`, `_SERVER_TO_PLATFORM`, `CREDENTIAL_INJECTION_MAP` if credentials are injected, `mcp_tool_sync` mappings, and a prompt-registry row if prompts are DB-managed.
- New graph node / state field: node + edges with a `_route_after_*`; every `add_conditional_edges` path_map lists every string its router returns (:687-760); field in `AdsAgentState` **and** `DomainState` **and** the `domain_state` dict in `_build_domain_sends` (:190-231) if spokes need it; reducer for Send-written fields.
- Routing wording ("governance" phrases, "deep analysis"): `_GOVERNANCE_ADD_RE`, `_GOVERNANCE_INTENT_RE`, `_DEEP_ANALYSIS_RE`, orchestrator prompt and executor guards change together; run `test_orchestrator_routing`.
- SSE frame/status change: see `frontend.md` (ThinkingPill `STEP_ORDER`, `response`, `qc_report`).
