# Governance (llm_service governance domain + venxr_backend-utility-service)

Verified 2026-10-01 (utility-service HEAD 4ee3015). Paths without a repo prefix are in utility-service.

## Two systems, no shared tables
| | A: chat-driven groups & alert rules | B: Default Governance |
|---|---|---|
| App | `campaign_management/` | `default_governance/` |
| Entry | MCP tools `campaign_group_*` (via llm_service governance domain) | REST `api/default-governance/` + frontend Flows page |
| Rule | per-group metric/operator/threshold config | one `DefaultTemplate` per (platform, account): total daily budget > max daily spend × multiplier |
| Schedule | beat every 120s (`SNAPSHOT_INTERVAL_SECONDS`, `BUDGET_ALERT_INTERVAL_SECONDS`, `settings.py:214-222`) | crontab: syncs `DG_SYNC_MINUTES` (0,30), eval `DG_EVAL_MINUTES` (10,40) (`settings.py:211-264`) |
| Queue | default `celery` | `default_governance` (`CELERY_TASK_ROUTES`, `settings.py:191-195`) |
| Email | direct boto3 SES `helpers/email.py` in task `campaign_management.send_budget_alert_email` | publishes `app.send_task("email.send", queue="email", expires=1800, bcc=…)` (`controllers/evaluation.py:550`) consumed by `shared_components/packages/mailservice` worker (same Redis DB /0) |
| Locks | own `_group_lock` ctxmgr (`tasks.py:25-38`, TTL 5 min, `lock:snapshot:{id}`/`lock:alert:{id}`) | `helpers/redis_lock.RedisLock` |
| Constants | literal task names and `expires=30/60` in `tasks.py`; `constants/task_constants.py` holds Meta URLs, metric sets, email HTML | everything in `default_governance/constants/__init__.py` (task names, TTLs, lock keys, `*_EXPIRES`) |
Only link: DG imports `get_platform_token` from campaign_management. Scheduler: `django_celery_beat` DatabaseScheduler.

**Match the local style of the app you're in** — don't "upgrade" campaign_management to the DG pattern in an unrelated change.

## System A details
- Models (`campaign_management/models.py`): `CampaignGroup` :6, `CampaignGroupItem` :20, `CampaignGroupConfiguration` :47, `CampaignMetricSnapshot` :109, `AdSetBudgetSnapshot` :145.
- Config fields (:79-101): metric, operator, threshold, threshold_type, check_mode, `window_days`, aggregation_type (default "sum"), action (alert|pause), alert_emails, is_paused, last_notified_at, user_intent, budget_field, since_date, until_date.
- `METRIC_CHOICES` (:48-61) = 12 values; `tools.py _SUPPORTED_METRICS` (:17-21) = 16 (adds cpa, conversion_rate, aov, revenue_per_click). No `full_clean`, so extra values save via ORM.
- `ALERT_CURRENCY_METRICS = {spend, cpc, cpm, cpa}` paise (`constants/task_constants.py:52`, comment :46-51); conversion_value, aov, revenue_per_click are rupees.
- Migrations: `0001_initial` is a squash replacing 0001–0019 (choices at :84-104); 0002–0019 are no-ops; `0020` adds `last_notified_at`. New schema change = new `0021_*`.
- Layering: `tools.py` holds CRUD/ORM directly (e.g. ~:510, ~:680); `controllers/` only for snapshot (`metrics_snapshot.py`) and alert (`metrics_alert.py`); `views.py` is an empty stub.
- Flow: snapshot loop calls the platform per item serially (`metrics_snapshot.py:50-79`); evaluation reads snapshots only (`metrics_alert.py:171-232`). On trigger: pause serially (`_pause_campaigns` :708-770) → `is_paused=True` unconditionally (:671; one-shot — never fires again until reset) → SES email (:875). 72h advisory cooldown `ALERT_NOTIFY_COOLDOWN_SECONDS` (:775-783) does not apply to the fire email.
- Platform handlers: `platform_tasks/__init__.py:10-24` Meta + Google only; others `NotImplementedError` (caught).
- MCP exposure: one FastMCP `utility_mcp` (stateless_http) in `utility_service/asgi.py:78-88`; `register(mcp, get_token)` from `tools/google_drive_tools.py` (14 tools) and `campaign_management/tools.py` (11 tools). Starlette mounts `/utility` → MCP (with `HeaderExtractMiddleware`), `/` → Django. User id from `x-user-id` header (`tools.py:107`). Tool bodies are async and wrap ORM in `campaign_management.helpers.db.run_db` (closes old connections, retries once on Interface/OperationalError). llm_service connects to `http://utility-mcp:8000/utility/mcp`.

## System B details
- REST (`default_governance/urls.py`, mounted at `api/default-governance/`): `sync-accounts/`, `disconnect-accounts/` (POST, `X-Service-Key`, `InternalServiceView` `views.py:51-64`, called by auth service `oauth/constants/constants.py:82,88`); `templates/` GET, `templates/<uuid>/` PATCH, `templates/<uuid>/campaigns/<id>/activate|deactivate/` POST (`UserScopedView`, JWT via `middleware/jwt_identity.py`). Frontend calls `/api/utility/api/default-governance/templates/` (`frontend/src/features/flows/api/defaultGovernance.ts:21`).
- Dedup `_breach_start()` + `RENOTIFY_AFTER_HOURS` (24, env `DG_RENOTIFY_AFTER_HOURS`) (`evaluation.py:270-432`).
- Pause via `app.send_task(TASK_PAUSE_ACCOUNT_CAMPAIGNS, …)` (`evaluation.py:458`); `pause_account_campaigns` is the only task that binds and calls `self.retry`.
- Kill switches default off: `DG_PAUSE_ENABLED`, `DG_NOTIFY_ENABLED` (re-checked inside the task). `DG_ALERT_EMAILS` can only narrow recipients; `DG_DEV_ONLY_ACCOUNT_IDS` restricts evaluated accounts.
- Fetchers registered for meta and google_ads only (`fetchers/__init__.py:37-60`).

## Celery conventions (what's actually true)
- `@shared_task(name=..., max_retries=...)`. `max_retries` alone does nothing: only `self.retry` retries; log-and-re-raise does not. `send_budget_alert_email` can never retry because `EmailService.send` swallows exceptions and returns False.
- Coordinators log then re-raise and fan out per item with `apply_async(..., expires=...)`; per-item tasks take a lock and skip if not acquired.
- Where Celery worker/beat/dg-worker actually run is not in the workspace compose (only `utility-mcp` uvicorn); `settings.py:186-187` expects a `utility-dg-worker -Q default_governance`. Commands: `celery -A utility_service worker`, `celery -A utility_service beat --scheduler django_celery_beat.schedulers:DatabaseScheduler`.

## Env
`config.py:8-23` (AUTH_SERVICE_URL, LLM_SERVICE_URL, INTERNAL_SERVICE_KEY, CELERY_BROKER_URL, GOOGLE_ADS_*, AWS_*, ALERT_SENDER, DEFAULT_ALERT_CC_EMAIL) **plus** `utility_service/settings.py` (DB_*, schema default `svc_utility`, AUTHENTICATION_SERVICE_SECRET_KEY, DG_*_MINUTES, *_INTERVAL_SECONDS), `default_governance/constants/__init__.py` (DG_* flags), `metrics_alert.py:778`. Put a new env read next to its siblings.

## llm_service side of governance
- `domains/governance/config.json`: `mcp_server: utility`, `tool_allow_prefixes: ["campaign_group_"]`, metric list + money-unit rule inside `system_prompt`. May be overridden by a DB prompt row (see llm-service.md §6).
- `"governance"` in `_VALID_DOMAINS`, in `WRITE_DOMAINS`, in `_DATA_PRODUCING_DOMAINS`; `mcp_tool_sync` override `campaign_group_`→governance.
- Deterministic guards in `domain_lead._run_task` (~2390-2649): alert_emails default, name→id resolution via Entity Store, fabricated-group block. Routing guards `_GOVERNANCE_ADD_RE` (graph.py) and `_GOVERNANCE_INTENT_RE` (orchestrator).
- `campaign_group_*` are Tier 1 → no human approval for pause rules or deletes.
- Frontend references governance tool names in `features/chat/lib/guidedFlows.ts:378-393` and `hooks/useGuidedFlows.ts:606`, parsing `tool_end` output truncated to 500 chars.

## Before "adding support" for something
Check whether the code already supports it on the current branch (grep the enum/metric across utility, llm `config.json`, frontend). If it does, the user-visible failure is usually runtime: a stale DB prompt row (`agent_prompt_versions`, `domain:governance`), an old deployed image, or routing. Diagnose from a chat trace (was the tool called? what did it return?) before planning code.

## Checklists
- **New/changed governance metric:** `tools.py _SUPPORTED_METRICS` + model `METRIC_CHOICES` + new migration + evaluator in `controllers/metrics_alert.py` + unit decision (`ALERT_CURRENCY_METRICS` if paise) + tool description text + governance `config.json` prompt (and its DB prompt row) with the same unit + snapshot fields if the metric needs new raw data.
- **New/changed governance MCP tool:** keep the `campaign_group_` prefix; check `is_write_tool` classification by name; risk tier decision in `risk_manager.py`; `config.json` prompt/enums; `mcp_tool_sync` overrides; frontend guided-flow tool names; enums mirrored in `tools.py`, model choices, migration.
