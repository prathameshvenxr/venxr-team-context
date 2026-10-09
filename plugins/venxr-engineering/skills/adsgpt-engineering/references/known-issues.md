# Known issues (found 2026-10-01 by code reading; not fixed)

Use this to recognise odd behaviour, not as a to-do list. Don't fix any of these inside an unrelated change — mention them and let the user decide. Re-verify before citing; code moves.

## Correctness
- **Governance money units:** governance `config.json` prompt tells the LLM to ×100 aov, conversion_value, revenue_per_click, but utility stores/compares them in rupees (`ALERT_CURRENCY_METRICS = {spend,cpc,cpm,cpa}` only) → thresholds 100× too high.
- **Meta conversions over-counted:** utility `controllers/metrics_alert.py` `_extract_conversions` sums every Meta `actions` entry (link clicks, engagement, video views…), so Meta CPA is far too low and conversions/conversion_rate/aov are inflated; conversion value is summed the same way. Fixing it changes when existing rules fire, and which action types count is a product decision.
- The ×100 instruction for aov/conversion_value/revenue_per_click also appears in frontend `guidedFlows.ts`; the utility tool description says the opposite (pass as-is).
- **Metric enum drift:** `_SUPPORTED_METRICS` (16) vs `METRIC_CHOICES`/migration (12); extras save without validation.
- **Retries that never happen:** CM `snapshot_campaign_group`, `check_budget_alert_group`, DG `sync_*` set `max_retries` but never call `self.retry`; `send_budget_alert_email` can't fail (EmailService swallows errors).
- `RedisLock.__exit__` deletes the key without an ownership check.
- `manage.py sync_prompts` imports deleted modules.
- `portfolio_audit` graph node is unreachable (route commented out).
- `VENXR_V2_ACTIVE` and `_DEFAULT_RULEBOOK_CREATE` are effectively dead.
- amazon_ads: llm sends `Authorization`/`Amazon-Ads-ClientId`, MCP reads `x-amazon-ads-token`; amazon_ads not in `_get_mcp_servers`.
- Google MCP `upstream_trace.reset()` never called → `_upstream_calls` capture inert.
- `RiskManager.assess_dag_risk`/`get_tool_tier` exact lookup vs suffix-matched `RISK_TIERS` keys → prefixed write tools read as tier 1 there.
- Gateway `skill_router` `reply_id` in stream differs from saved history payload.
- Frontend: no refresh-token flow (401 → logout); `MODE_STATE_GUIDE.md` hook unused; `VITE_API_URL`/`VITE_GATEWAY_URL` unused.
- Auth impersonation: claims set on `refresh.access_token` are discarded (property builds a new token).

## Security (flag to the user; never silently "fix" in passing)
- Gateway does not validate JWTs on proxy routes and forwards client headers unchanged; it injects `X-Service-Key` on `/api/utility/*`, and utility `InternalServiceView` trusts the key alone (whether the header is actually forwarded is unverified).
- skill_service: no endpoint auth; identity from unverified JWT decode then `x-user-email`/`x-user-id` header override; hard-coded default user; CORS `*` with credentials.
- Auth: `stop-impersonate`, `impersonation-logs/log-action`, `heartbeat` are `AllowAny` and act on any `log_id`; read-only impersonation enforced only in the frontend; service-key comparisons use `==` not `compare_digest`; `SYSTEM_ADMIN_EMAILS` hard-coded.
- Gateway `SECRET_KEY` hard-coded and `DEBUG=True` in settings.
- Sandbox service mounts the host Docker socket; `__RESULT__` stdout channel may be spoofable via `sys.__stdout__` (unverified).
- Reporting public share: UUID link, no auth, no expiry, replays as the owner.
