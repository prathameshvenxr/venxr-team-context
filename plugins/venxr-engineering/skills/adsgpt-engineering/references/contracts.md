# Cross-repo contracts (silent couplings)

Nothing below fails at import or migration time; it fails at runtime, often silently. Before changing any of these strings, grep all repos (`grep -rn "<string>" <workspace>`) and plan the rollout order (producer adds new form → consumers switch → producer drops old form).

## Names & registries
| Contract | Copies to keep in sync |
|---|---|
| MCP tool names & args | MCP `server.py` ↔ llm `REPLAYABLE_TOOLS`, `META_DETAIL_TOOL_BY_LEVEL`, QC fetchers, reporting `campaign_tree.py`, bulk_create `copy_existing.py`, `RISK_TIERS`, `domains/*/config.json` prompts (+ DB prompt rows), saved `AnalysisSpec` rows, `ToolConfig` stubs ↔ frontend `guidedFlows.ts`, `useGuidedFlows.ts`, `metaCreateSpec.generated.ts` |
| Tool name verbs | `risk_manager.is_write_tool` classifies by name → read/write availability per domain |
| Tool prefixes ↔ domains | `config.json tool_allow_prefixes` ↔ `mcp_tool_sync._SERVER_PREFIX_OVERRIDES` |
| Tier-1 skills | skill_service `skills/tier1/*` + `registry.py` ↔ gateway `TIER1_SKILLS` + `SLUG_ALIASES` (runtime data_contract) ↔ llm `my_skills` seed migration (`triggers[0]` = slug) ↔ frontend `skill_slug = triggers[0] || name` |
| Governance enums | utility `tools.py _SUPPORTED_METRICS` ↔ model `METRIC_CHOICES` + migration ↔ `ALERT_CURRENCY_METRICS` ↔ governance `config.json` prompt (+DB row) |
| Entity Store keys | `list_entities(user_id, "governance", "campaign_group")` — domain/entity_type strings |
| Create rulebook | llm `rulebooks/sources/*.json` → compiled `spec.json` → frontend generated spec; `rulebook/expr.py` ↔ frontend `rulebookExpr.ts` |
| Celery task names | utility `"email.send"` on queue `"email"` ↔ shared_components mailservice; DG task-name constants ↔ `CELERY_TASK_ROUTES` pattern `default_governance.*` |
| Product name (Venxr vs Vajra) | env `PRODUCT_NAME` (wins when set) else `APP_BRAND=vajra` -> "Vajra", read by auth `auth_core/constants/constants.py`, utility `campaign_management/constants/task_constants.py`, llm `config.py` (`APP_NAME`) ↔ frontend `branding.ts` (`VITE_APP_BRAND` or hostname containing "vajra") ↔ Default Governance mail (`APP_BRAND`, shows "WPP Vajra") ↔ llm `engine/capabilities.py` header `[<name> capabilities ...]` must match the orchestrator prompt that cites it. Unset keeps the Venxr text. The meta MCP service reads no env, so its messages stay brand-neutral |
| CI string asserts | `"evidence"` in `_EXTRACT_SYSTEM`, `"Memory never narrows platform scope"` in orchestrator prompt |

## Shapes
| Contract | Producer → consumers |
|---|---|
| MCP result envelopes | meta `{success,data|error}` / google raw / others `{"error": str}` → QC fetchers, name_resolver, context_offload, portfolio, frontend `parseToolOutput` |
| SSE frames | llm `chat/graph_stream.py`, `qc_store.py`, gateway `skill_router` → frontend `agent.ts`, `ChatContext.tsx`, `Chat.tsx`, `ThinkingPill.tsx` (types, step ids, `data` keys, 500-char `tool_end`) |
| Chat request body | frontend `section`, `active_context` keys, `skill_slug` → llm `chat/serializers.py`, `chat/identity.py`; gateway skill intercept |
| v3 history | gateway → llm `chat/v3-history/` (`step="v3_skill"`, `data.v3_payload`) → frontend |

## Identity, secrets, headers
- `AUTHENTICATION_SERVICE_SECRET_KEY` = auth Django `SECRET_KEY`: signs all JWTs (HS256), verified by llm_service and utility-service, and keys impersonation-grant HMACs. Rotating it logs everyone out and revokes grants.
- JWT claims read downstream: `user_id`, `email`, `agency_id`, `impersonated`, `impersonation_log_id`.
- `INTERNAL_SERVICE_KEY` / `X-Service-Key`: one value across gateway, auth, llm, utility.
- Headers: `x-user-id`, `x-user-email` (trusted for identity by skill_service; fallback in llm v3-history), `X-Impersonation-Log-Id`, `x-<platform>-token` (MCP), `x-meesho-email/password`. Gateway passes client headers through unchanged.

## DB schemas read across services
`svc_auth` tables `oauth_connectedplatform` (`access_token`, `refresh_token`, `platform` ∈ 'meta'/'google_ads'…, `user_id`) and `auth_user` (`email`, `id`) are read with raw SQL by skill_service and whatsapp_webhook. Renaming a table/column/schema or a platform value breaks them with no migration error. utility schema default `svc_utility`.

## URL paths
Gateway strips route prefixes; it hard-codes auth `auth-core/impersonation-logs/log-action/`, skill_service `/api/v1/chat/execute`, llm `chat/v3-history/`. Frontend hard-codes many `/llm/*`, `/api/auth/*`, `/api/utility/api/default-governance/*`, `/whp/*` paths and `/platforms` (named in MCP "not connected" error strings). TV MCP returns `/api/llm/tv-plans/<job_id>/export.xlsx`.

## Versions & infra
Meta Graph v21/v22 (meta MCP), v25/v21 (utility apps), v19 (skill_service); google-ads unpinned; shared_components checked out unpinned in llm CI; infra compose uses old monorepo folder names and lacks skill_service and utility Celery workers.
