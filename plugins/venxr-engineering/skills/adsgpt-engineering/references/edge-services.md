# Gateway, auth, skill_service, sandbox, shared_components

Verified 2026-10-01.

## Gateway (`venxr_backend-gateway_service`, Django ASGI under uvicorn, :8000)
- Routes (`gateway/urls.py:5-32`): `test/` health; `api/llm/*` + legacy `llm/*` → `proxy_llm`; `api/auth/*`, `.well-known/*`, `mcp-oauth/*` → `proxy_auth`; `admin/*`, `static/*` → auth with prefix kept; `whp/*` → whatsapp; `api/utility/*` → utility. The route prefix is stripped before forwarding (`views.py:204-208`) — auth mounts `mcp_oauth.urls` at its root so `.well-known` works.
- `/services` (asgi.py:42-48) = MCP aggregator (`aggregator/mcp.py`, upstreams META/GOOGLE_ADS/UTILITY MCP URLs, descriptions overridden from llm `/tools/`) behind `MCPAuthMiddleware`, which validates via auth `/mcp-oauth/validate/` with `X-Service-Key` and injects `x-user-id` + `x-<platform>-token` (`middleware/constants.py:10-15`).
- **No JWT validation on proxy routes**; `_forward` passes all client headers except host/content-length/transfer-encoding/connection. `proxy_utility` sets `X-Service-Key` on forwarded requests (`views.py:379`).
- Impersonation audit: `_audit_impersonation` (`views.py:55-194`), fire-and-forget, POST/PUT/PATCH/DELETE only, log id from `X-Impersonation-Log-Id` or unverified JWT payload, POSTs to auth `auth-core/impersonation-logs/log-action/`. No gateway models (sqlite unmigrated).
- **Tier-1 skill intercept** (`gateway/skill_router.py`): any POST whose path contains "chat" with a `skill_slug` that resolves via `SLUG_ALIASES` (:81-91; accepts slug, display name, underscore form) → `_build_v3_body` with the gateway's own `data_contract`/`verdict_logic` (:117-138) → skill_service `/api/v1/chat/execute`, falling through cached URL → `SKILLS_SERVICE_URL` (default `http://skill_service:8090`) → hard-coded hosts → localhost (connect errors only; never falls back to llm_service). Then fire-and-forget POST of history to llm `chat/v3-history/`. Tier-1 requests skip impersonation audit. Timeouts 180s/15s.
- Env (`config.py:11-37`): LLM/AUTH/WHP/UTILITY service URLs, three MCP URLs, `*_PROXY_TIMEOUT` (LLM 900s), `INTERNAL_SERVICE_KEY` (default ""), `SERVICE_BASE_URL`; `SKILLS_SERVICE_URL` in skill_router. Tests: none.

## skill_service (FastAPI, :8090)
- `app/main.py`: CORS `*` with credentials; `/`, `/health`; skills router at `/api/v1/skills`; chat router mounted at both `/api/v1/chat` and `/api/v1/skills`. No endpoint auth.
- `api/chat.py`: `ChatRequest` (:37-48); `POST /chart-metric`, `/chart-compare`, `/execute` (dispatch ~:1856-1871 → `execute(daily_rows, aggregate_map, interpretation, skill_def, all_accounts)`). The data contract used comes from the request (i.e. the gateway copy).
- `api/skills.py`: `/preview`, `/confirm`, `/generate`, `GET /` (Tier-1 + Tier-2), CRUD `/{skill_id}`. Tier-2 skills are in-memory only (lost on restart).
- Tier-1 registry `skills/tier1/registry.py`: `register_tier1(slug, def)` (stable uuid5 id), lookup by slug then display name, modules imported by hand in `_load_all_tier1` (~:123-129). Existing slugs: `meta-ads-creative-fatigue`, `google-ads-creative-fatigue`, `audience-saturation-analysis`.
- Platform data: `platforms/meta.py` (Graph v19.0), `platforms/google.py` (API v25). Tokens via raw asyncpg SQL on auth's schema (`db/connection.py`: `oauth_connectedplatform` ⨝ `auth_user`, `search_path=svc_auth`), Google tokens refreshed directly.
- Identity: default user hard-coded, then unverified JWT decode, then `x-user-email`/`x-user-id` header override (`chat.py:1717-1724`).
- LLM: `llm/client.py` AsyncOpenAI gpt-4o; `brain/` pipeline for preview/generate. Env `app/config.py:11-23`. Tests none; README empty; not in infra compose.

### Add a Tier-1 skill (4 places, 3 repos)
1. skill_service: new module in `skills/tier1/` calling `register_tier1` (name, description, method_body, data_contract, verdict_logic, priority, async `execute`) + import in `registry.py` `_load_all_tier1`.
2. gateway: `TIER1_SKILLS` entry (this `data_contract` is what runs) + `SLUG_ALIASES` (slug, display name, underscore form).
3. llm_service: new seed migration like `features/my_skills/migrations/0012_seed_tier1_system_skills.py` so it appears in the skill picker. Its `triggers[0]` must equal the slug: the frontend sends `skill_slug = triggers[0] || name` (`Chat.tsx:302,1224`).
4. frontend: verify the picker/`V3SkillRenderer` path handles it (`step: "v3_skill"`, `data.v3_payload`, `Chat.tsx:~2215`).
Deploy order: skill_service → gateway → llm_service migration → frontend. A slug/name missing from any copy silently falls through to llm_service.

## Authentication service (`venxr_backend-authentication_service`, Django)
- Mounts (`authentication/urls.py:20-27`): `admin/`, `oauth/`, `auth-core/`, `onboarding/`, `mcp-oauth/`, plus `mcp_oauth` at root. `client_space` installed but unrouted.
- JWT: simplejwt defaults (HS256, signed with `SECRET_KEY = AUTHENTICATION_SERVICE_SECRET_KEY`), 24h access / 1d refresh, no rotation; custom `email` claim (`login_auth_controller.py:36-37`, `oauth_login_controller.py:109-110`). Default auth `ApprovedJWTAuthentication` gated by `AUTH_ADMIN_APPROVAL`. llm_service and utility-service verify with the same secret; gateway and skill_service don't verify.
- Service key endpoints (`X-Service-Key` = `INTERNAL_SERVICE_KEY`): `GET oauth/token/?platform=&user_id=`, `GET oauth/connected-users/`, `GET mcp-oauth/validate/`. Auth calls utility `api/default-governance/sync-accounts|disconnect-accounts/` on connect/disconnect.
- Impersonation (`auth_core/views.py`): `POST auth-core/impersonate/` (mode write if `can_impersonate_write` else read; `ImpersonationLog`; claims on refresh token), grants are HMAC of user id keyed by `SECRET_KEY`, `manage-impersonate` limited to hard-coded `SYSTEM_ADMIN_EMAILS`; heartbeat every 20s from FE, sessions idle >45s auto-closed. Read-only mode is enforced only in the frontend.
- Tests: 3 in `auth_core/tests.py`.

## Sandbox (`venxr_backend-sandbox_service`)
`POST /run {code, data, timeout=20}` → `{ok, result, stdout}` | `{ok: false, error}` | 429 busy (`app.py`); `SANDBOX_MAX_CONCURRENCY` 4, `SANDBOX_QUEUE_WAIT_SECS` 30. No auth — internal network only, never add `ports:`. Runner container: `--network none --read-only --user 65534 --cap-drop ALL`, 512m, 1 cpu, 64 pids, timeout clamped 1-60s (`executor.py`). Image `venxr-sandbox-runner` (pandas 2.2.2, numpy 1.26.4). Result parsed from first stdout line starting `__RESULT__`. Caller: llm_service `engine/core/sandbox_client.py` (never raises; send only tenant-scoped data). Tests none.

## shared_components
`packages/jobqueue` (venxr-jobqueue: `durable_task`, Celery/Redis primitives; editable-installed by llm_service only via `-e ../shared_components/packages/jobqueue`, Dockerfile `COPY shared_components`, so build context is the parent dir) and `packages/mailservice` (worker `celery -A mailservice.worker worker -Q email`, task `email.send`; utility-service produces it by name). llm_service CI checks it out with `SHARED_COMPONENTS_PAT` and **no ref** → always default branch. A change here is a cross-repo change; check llm_service CI and utility's `email.send` kwargs.
