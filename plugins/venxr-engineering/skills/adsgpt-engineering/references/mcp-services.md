# MCP services

Repos: `venxr_backend-meta_mcp_service`, `venxr_backend-google_ads_mcp_service`, `venxr_backend-dv360_mcp_service`, `venxr_backend-amazon_ads_mcp_service`, `venxr_backend-meesho_seller_mcp_service`, `tv_planner_mcp_service`. Verified 2026-10-01.

## Shared pattern
- One `server.py`: `FastMCP(name, stateless_http=True, transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False))`; tools are `@mcp.tool()` `async def … -> dict`; run as `streamable_http_app()` under uvicorn on 0.0.0.0:8080 (`CMD python server.py`).
- Layering: tool in `server.py` reads token → validates args → calls `platforms/<platform>.py` (real API logic). Sync SDKs run via `asyncio.to_thread` (dv360).
- A pure-ASGI `HeaderExtractMiddleware` copies lower-cased headers into a contextvar; tools read tokens from it.
- Naming: snake_case with platform prefix `meta_`, `google_ads_`, `dv360_`, `amazon_ads_`, `meesho_seller_`, `tv_`; verbs get/list/search/create/update/bulk_get. Exception: `fetch_meta_qc_details` (called by name from llm_service reporting `campaign_tree.py:80` and `bulk_create/copy_existing.py:16`).
- Tool counts: meta 79, google 88, dv360 14, amazon 15, meesho 7, tv 3.

| Service | Token header | Env | Error shape |
|---|---|---|---|
| meta | `x-meta-token` | — | `_err()` → `{"success": False, "error": {message, code, type}}`; `_wrap()` → `{success: True, data, _healed?, _upstream_calls?}`. Exceptions: bare `{"error": _NO_META}` at ~:798, :1153, :1277, :4005 and unwrapped returns for `meta_update_campaign`, `meta_get_campaigns_budget`, bulk tools |
| google_ads | `x-google-ads-token` (refresh token) | developer token, app id/secret (`config.py`) | raw payload or `{"error": str}`; no envelope |
| dv360 | `x-dv360-token` | — | `{"error": str}` |
| amazon_ads | `x-amazon-ads-token` | `AMAZON_ADS_CLIENT_ID`, `AMAZON_ADS_API_BASE` | `{"error": str}` |
| meesho_seller | `x-meesho-email`, `x-meesho-password` | — | — |
| tv_planner | `x-user-id` (attribution) | GCP config | `{"success": False, "error": {message, code}}` |

Consumers depend on these shapes: meta QC fetcher needs `success`/`data` (`qc_data_fetcher.py:141-160`), google QC fetcher assumes no envelope (`qc_data_fetcher_google.py:47-60`), plus `engine/name_resolver.py`, context_offload, portfolio, and frontend `parseToolOutput` (`guidedFlows.ts:805-815`). **Keep the service's existing shape for new tools.**

## Meta specifics
- `validators.py` is the single source of truth for allowed enums (`_VALID_*` frozensets ~:176-326, imported in server.py ~:129-146) and compat checks (`validate_targeting`, `validate_goal_billing_compat`, `validate_objective_goal_compat`, `validate_promoted_object`, `validate_budget_schedule`, `validate_bid_strategy_constraints`). Per-arg `_check_*` helpers in server.py ~:211-278.
- `healing.py`: `normalize_inputs` before the call, `heal_api_error` after (token-expired codes 102/190/463/467; rate-limit 4/17/341/80000-80005).
- Retries live in `platforms/meta.py` (3 tries, 1/2/4s; HTTP 429/5xx and codes 1/2/4/17/341). Pagination capped at 2000 rows server-side.
- Graph API v21.0 (`constants/constant.py:1`); ad-creative calls use v22.0 (`platforms/meta.py:32-40`). (utility-service uses v25.0 and v21.0 in different apps; skill_service v19.0.)
- `upstream_trace.py` records calls (tokens redacted) → `_upstream_calls` → llm_service `MCPCallLog.upstream_calls`.

## Google specifics
- server.py ~:47-86 auto-wraps every public coroutine in `platforms.google_ads` with numeric-id validation (`ID_FIELDS_TO_VALIDATE`) and `_upstream_calls` — a new function gets both for free.
- `google-ads` library unpinned (requirements.txt:4); code assumes v24 behaviour. No generic retry/backoff.
- `upstream_trace.reset()` is never called, so capture appears inert.

## Add a tool end-to-end
1. **MCP service:** `@mcp.tool()` in `server.py` with the platform prefix; token check first; validate (meta: `_check_*` + validators.py set; add new enums there); call `platforms/<p>.py`; return through the service's existing envelope (`_wrap` in meta). Add tests where the service has them (meta, tv).
2. **Name it deliberately:** a create/update/delete/add/rename/... verb anywhere in the name makes it a write tool → stripped from every non-`WRITE_DOMAINS` domain and tiered by `risk_manager.tool_tier`. Decide its tier in `RISK_TIERS` if it's a write.
3. **Discovery is automatic** at llm_service boot (`mcp_tool_sync`) — restart or `manage.py sync_mcp_tools`. Edit `domains/*/config.json` only if it needs a new prefix/domain, or if the prompt should mention it (prompts may also live in DB rows).
4. Add to `REPLAYABLE_TOOLS` only if it's an insights read that should replay in reports.
5. If QC, reporting tree, bulk_create or the frontend guided flows should call it, they call by hard-coded name — add it there explicitly.
6. Optional offline stub: `ToolConfig` row via `manage.py seed_tools`.

## Rename a tool or arg (the dangerous one)
Grep the old name/arg across **all** repos and update: `REPLAYABLE_TOOLS` and `META_DETAIL_TOOL_BY_LEVEL` (reporting), saved `AnalysisSpec{tool,args}` rows in the DB (report templates replay old names → silently skipped), QC fetchers, `fetch_meta_qc_details` callers, bulk_create `copy_existing`, `domains/*/config.json` prompts and any DB prompt rows, `RISK_TIERS` suffix keys, frontend `guidedFlows.ts`/`useGuidedFlows.ts` and `metaCreateSpec.generated.ts`, `ToolConfig` stubs. Safe rollout: add the new name/arg alongside the old one (alias) in the MCP service, deploy it, migrate consumers + data, then remove the old name.

## New platform / MCP service
llm_service: `MCP_URLS` (settings.py:215), `_get_mcp_servers` (mcp_manager.py:389-411), `_SERVER_TO_PLATFORM`/`DOMAIN_TO_SERVER` (:415-434), `PLATFORM_TOKEN_HEADER` (mcp_client/client.py:31), `_SERVER_CANONICAL_DOMAIN` (mcp_tool_sync.py:43), a domain (see llm-service.md §14), auth service `ConnectedPlatform` platform choice + OAuth, frontend `active_context` key, gateway aggregator if it should be exposed via `/services`. Note: amazon_ads header mismatch today (llm sends `Authorization: Bearer` + `Amazon-Ads-ClientId`, server reads `x-amazon-ads-token`).

## Tests
meta: `pytest tests/ -v` (test_healing 44, test_validators 65; tests add repo root to sys.path; pytest not in requirements). tv: `pytest tests/ -v` (8). Others: none. CI for all MCP repos = build + deploy only.
