# Workspace map

The workspace folder is **not** a git repo. Every top-level folder is its own GitHub repo in the
`Venh-Analytics-Pvt-Ltd` organisation. A change that spans services is several repos, several commits and a deploy order.

## Deployments and environments
Two deployments, **Venxr** and **Vajra**, each with **dev, staging and prod**: six instances built from the same
code. Each of the ten deployable repos checked (frontend, gateway, auth, llm_service, utility, skill_service, sandbox, whatsapp,
meta_mcp, tv_planner) has all six deploy workflows (`deploy-venxr-dev.yml` through `deploy-vajra-prod.yml`) on `venxr_v2`.
Anything that differs per deployment (product name, admin list, mail sender, storage backend) must come from env.

Branches: `venxr_v2` is **dev** (confirmed). `venxr_v2_staging` and `venxr_v2_main` exist in the repos, but which
environment each one deploys is not recorded here: **confirm and fill in** before anyone relies on it.

| Environment | Branch | Confirmed |
|---|---|---|
| dev | `venxr_v2` | yes |
| staging | _TBD_ (`venxr_v2_staging`?) | no |
| prod | _TBD_ (`venxr_v2_main`?) | no |

## Repos
| Repo | Role | Snapshot branch |
|---|---|---|
| `frontend` | React 18 + TypeScript + Vite app; talks to the gateway; brand via `branding.ts` | venxr_v2 |
| `venxr_backend-gateway_service` | Django ASGI proxy: routes `/api/llm`, `/api/auth`, `/api/utility`, `/whp`; MCP aggregator; Tier-1 skill intercept | venxr_v2 |
| `venxr_backend-authentication_service` | Django: login, OAuth connections, JWT issue, impersonation, sign-up/reset mail | venxr_v2 |
| `venxr_backend-llm_service` | Django + LangGraph agent (orchestrator, domain leads, create/rulebook, QC, reporting, memory) | venxr_v2 |
| `venxr_backend-utility-service` | Django + Celery + utility MCP: governance (campaign groups, alert rules, Default Governance), Drive tools, alert mail | venxr_v2 |
| `skill_service` | FastAPI: Tier-1 analysis skills | venxr_v2 |
| `venxr_backend-sandbox_service` | FastAPI that runs analysis code in a locked-down container | venxr_v2 |
| `venxr_backend-meta_mcp_service` | FastMCP: Meta Ads tools | venxr_v2 |
| `venxr_backend-google_ads_mcp_service` | FastMCP: Google Ads tools | venxr_v2 |
| `venxr_backend-dv360_mcp_service` | FastMCP: DV360 tools | venxr_v2 |
| `venxr_backend-amazon_ads_mcp_service` | FastMCP: Amazon Ads tools | venxr_v2 |
| `venxr_backend-meesho_seller_mcp_service` | FastMCP: Meesho seller tools | venxr_v2 |
| `tv_planner_mcp_service` | FastMCP: TV media planner (GCP/Dataproc) | venxr_v2 |
| `venxr_backend-whatsapp_webhook_service` | Django: WhatsApp Business webhook and agents | venxr_v2 |
| `shared_components` | `jobqueue` (Celery/Redis durable tasks), `mailservice` (SES mail worker) | venxr_v2 |
| `venxr_backend-infra` | docker compose files (build contexts are stale, see the guide) | main |
| `venxr-wiki` | wiki snapshot of 2026-07-18; treat as stale | main |
| `venxr_qa_testing` | QA repo (not reviewed here) | main |

Details, line references and the silent cross-repo couplings are in the plugin's
`skills/adsgpt-engineering/` guide. It was verified by reading code on 2026-10-01; line numbers drift, so grep the
symbol before trusting a number.
