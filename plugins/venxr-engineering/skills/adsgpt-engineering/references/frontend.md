# frontend (React 18 + TS + Vite 7)

Verified 2026-10-01 (branch venxr_v2).

## Layout & conventions
- `src/core/` (auth, layout, onboarding, pages, providers, theme), `src/features/<x>/{api,components,hooks,lib,pages}` (admin, agency, analytics, bulk, chat, dev, flows, knowledge, platforms, projects, qc, reports, settings, skills, tv, usage), `src/shared/{ui,lib,hooks,icons}`, `src/styles/index.css` + `styles/tokens/{brand,semantic}.css`. Alias `@/` → `src`.
- Routing (`App.tsx:119-170`): protected routes under `<ProtectedRoute><AppLayout/>`, owner pages under `OwnerRoute`; pages lazy-loaded; `/:sessionId` catches any single-segment path as a chat session — new top-level routes must be declared before it.
- Naming: components/pages PascalCase `.tsx`; api/lib camelCase `.ts`; `shared/ui` kebab-case (shadcn). Hooks mixed — match the folder.
- TS strict is off; ESLint 9 flat config (raw `<button>`/`<input>` outside `shared/ui` warns; `no-unused-vars` off); Prettier: semi, singleQuote, trailingComma all, printWidth 100.
- State: TanStack Query (`useApiQuery`/`useApiMutation` in `shared/hooks/use-api.ts`) + React Context providers (`core/providers`, ChatContext, AgentSessionContext, ProjectContext, QCRulesContext). No redux/zustand — don't add one.

## UI_CONTRACT.md (enforced in review)
Same concept → same component and tokens; use `@/shared/ui/*` (shadcn/Radix + cva + `cn`); no hex colors or arbitrary `*-[..]` values — use tokens; never hard-code brand values (use `branding.ts`); new component order: reuse → cva variant → new; follow its PR checklist. (Its `src/index.css` path is stale: real file `src/styles/index.css`.)

## API client (`src/shared/lib/api-client.ts`)
Each api module makes `new ApiClient(import.meta.env.VITE_AUTHENTICATION_SERVICE_BASE_URL || '')` (the gateway base; ~26 instances). Sends `Bearer <sessionStorage access_token>` + `X-Impersonation-Log-Id`; blocks mutations in read-only impersonation (:53-61); 401 → clear tokens, redirect `/auth` (no refresh flow); 402 → usage popup. Paths are hard-coded with gateway prefixes (`/llm/...`, `/api/auth/...`, `/api/utility/...`, `/whp/...`).
Env actually read: `VITE_AUTHENTICATION_SERVICE_BASE_URL`, `VITE_APP_NAME/AUTHOR/LOGO/BRAND/VERSION`, `VITE_MODULATE_API_KEY` (all baked at build). `VITE_API_URL`/`VITE_GATEWAY_URL` are documented but unused.

## Chat SSE contract (`features/chat/api/agent.ts`, `hooks/ChatContext.tsx`, `pages/Chat.tsx`)
- `_streamChat` POSTs `/llm/chat/v2/` (300s timeout). Body: `section` ∈ analyze|create|govern (must match llm `chat/serializers.py:34`), `active_context` keys `meta_account_id`, `google_ads_customer_id`, `dv360_advertiser_id`, `amazon_ads_profile_id` with Meta `act_` normalisation (`shared/lib/active-context.ts`, "lockstep" with `chat/serializers.py`/`chat/identity.py`), `skill_slug` = the picked skill's `triggers[0]`, falling back to its name (`Chat.tsx:302,1224`; Tier-1 intercept in the gateway).
- Parser keeps `data: ` lines. Typed frames: `tool_start | tool_end | step_result | snapshot | tool_error | debug_snapshot | trace | error | status`. Untyped response frames: `{step, status ∈ in_progress|completed|waiting_for_user|error, message, next_step, data{plan, form_config, questions, blocks, tokens}, reply_id, turn_no}`.
- Step ids depended on: ThinkingPill `STEP_ORDER` `context, memory, planning, task_N, synthesis, streaming` (`ThinkingPill.tsx:69-79`, matched to `chat/graph_stream.py` `_status_frame`); `response`; `qc_report` (`data.type === "qc_report"`); `v3_skill` with `data.v3_payload`. `tool_end` output is truncated to 500 chars by llm `executor.py`, and governance guided flows parse it.
- Changing any frame type, step id or `data` key = coordinated backend + frontend change.

## Generated create spec
`scripts/generate-meta-create-spec.mjs` (`npm run gen:meta-create-spec`) reads `../venxr_backend-llm_service/features/create/rulebooks/compiled/spec.json` (run `manage.py sync_rulebook` first; compiled dir is gitignored) and writes committed `src/features/chat/lib/metaCreateSpec.generated.ts`; only `STEP_BUCKETS` is hand-written and the script fails if a rulebook field is unclaimed. `features/chat/lib/rulebookExpr.ts` is a hand-port of backend `rulebook/expr.py` — change both together. Never hand-edit the generated file.

## Tests & CI
Vitest (jsdom, globals, `src/test/setup.ts`, `src/**/*.{test,spec}.{ts,tsx}`); one trivial test exists. CI only runs `npm install` + `npm run build`. Verify with `npm run lint`, `npm run build`, and `npm test` for any logic you add tests for; UI changes need a manual check in the browser.
