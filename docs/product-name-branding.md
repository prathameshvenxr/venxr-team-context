# Product name (Venxr vs Vajra): what changed and what each instance needs

Ticket: BG:SP010 "Sign up mail content is hardcoded for vajra" (ClickUp `14zf25zfjde`) and "Venxr name is displayed in
Vajra Alert notification mail" (`86d42kb9n`). The sign-up and alert mails said "Venxr"/"VenXR" even on Vajra.

## What changed (all on `venxr_v2`, i.e. dev)
| Repo | Commit | Change |
|---|---|---|
| authentication_service | `46d660a` | Sign-up OTP mail, reset-password mail and the internal "New signup" subject use the product name |
| utility-service | `cf8645a` | Campaign alert, budget-paused and advisory mails use the product name (HTML-escaped) |
| llm_service | `500a7af` | `APP_NAME` in `config.py`; used in assistant persona prompts, report titles, Meta rate-limit messages, the limit-request mail subject and the `[<name> capabilities]` header |
| meta_mcp_service | `840d344` | One user-facing error made brand-neutral (this service reads no env) |
| frontend | `35bc315` | TV upload dialogs use `getAppName()` |
| llm_service | `97f15ae` | Unrelated Docker-build fix: `pydantic>=2.0,<2.14` (see `requirements/README.md`) |

## How the switch works
- **Backends (auth, utility, llm_service):** the name is `PRODUCT_NAME` if set; otherwise **`APP_BRAND=vajra` gives
  "Vajra"**; otherwise the original text exactly ("Venxr" in auth, "VenXR" in utility and llm_service). So the
  `APP_BRAND=vajra` the Vajra deployments already set is enough; `PRODUCT_NAME` is only needed for a custom name or
  to override. `APP_BRAND` matches case-insensitively and ignores surrounding spaces; any other value keeps the default.
  (In code the constant is `APP_NAME` on dev and on the main branches, `PRODUCT_NAME` on the staging branches.)
- **Frontend:** `VITE_APP_BRAND=vajra` at build time, or a hostname containing "vajra" (`shared/lib/branding.ts`).
- **Default Governance mail** (utility-service) has always used `APP_BRAND` and shows the "WPP Vajra" lockup. It was
  not changed. The campaign alert mails now follow the same `APP_BRAND=vajra`, but show "Vajra" (not "WPP Vajra").
- The name goes into `.format()` templates and HTML mail, so braces are escaped and the alert mails HTML-escape it.

## Checklist per Vajra instance (dev, staging, prod)
- [ ] `APP_BRAND=vajra` on auth, utility-service (**including the Celery/email workers that send alerts**) and llm_service
      (this alone selects "Vajra"; set `PRODUCT_NAME` only to override the name)
- [ ] Frontend build has `VITE_APP_BRAND=vajra` (the prod workflow sets it; dev and staging rely on the hostname)
- [ ] `SYSTEM_ADMIN_EMAILS`: the code default lists Venxr staff, which would make them system admins on Vajra
- [ ] `LIMIT_REQUEST_NOTIFY_EMAIL`: default is a Venxr address, so Vajra limit requests would go to Venxr
- [ ] `DEFAULT_FROM_EMAIL` (llm_service defaults to a venxr.tech address, auth to a venanalytics.io one) and
      `ALERT_SENDER` / `DG_ALERT_SENDER`: use a sender the mail provider has verified for Vajra
- [ ] Privacy page copy ("Ven Analytics", venanalytics.io contacts) is legal text and was not changed: decide for Vajra

## Not verified (as of 2026-10-09)
- No real mail was sent and nothing was run on a real instance. The mail templates were rendered offline under unset,
  `Vajra`, blank and a hostile name; the unset output equals the original text.
- The llm_service tests did not run, and no Docker build had been confirmed when this was written.

## Known gaps left alone
Admin Usage Analytics copy still says "Venxr"; `skill_service` has a "VenXR Skills API" health message and a hardcoded
developer email used as the token identifier; create-schema descriptions read by the LLM mention "VenXR".
