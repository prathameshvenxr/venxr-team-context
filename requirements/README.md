# Requirements: the team's worklist

Goal: every service builds the same image tomorrow that it built last week. Today it does not, and on
2026-10-09 that broke a real build. This folder holds a snapshot of every service's dependency files so the team
can look at all of them in one place and agree on one approach.

**These are read-only copies.** Real changes land in each service's own repo. Snapshots come from each repo's
`origin/venxr_v2` (dev): see `snapshots/SOURCES.md` for the exact commits. Refresh with
`scripts/sync-requirements.sh`; regenerate the tables below with `python scripts/pin_report.py`.

## What happened on 2026-10-09 (llm_service Docker build)
- Failure: `ImportError: cannot import name 'eval_type_backport' from 'pydantic._internal._typing_extra'`,
  raised while the Dockerfile ran `python manage.py sync_rulebook`.
- Cause: `requirements.txt` pinned `mcp[cli]==1.9.1` but left `pydantic>=2.0` unbounded. A build without cached
  layers resolved `pydantic 2.14.0`, which no longer has the helper that `mcp 1.9.1` imports.
- It was not caused by the Venxr/Vajra branding change (that commit did not touch requirements; the file had
  last changed on 2026-08-03). It surfaced because that push triggered a fresh build.
- Fix on `venxr_v2` (`97f15ae`): `pydantic>=2.0,<2.14`. Evidence: pydantic 2.11, 2.12 and 2.13.0 define the helper
  (checked by reading their wheels); `mcp 1.9.1` + `langchain-mcp-adapters 0.1.6` + `pydantic 2.13.5` import
  cleanly in a fresh Python 3.12 virtualenv.
- **Not yet confirmed:** a real dev Docker build with the fix. Not tested on Python 3.11 (the image's version).
  Other unbounded packages in that build (`starlette`, `httpx2`, `httpcore2`, `django 5.0.14`) could break the
  same step with a different error. Update this section when the dev build result is known.

## The numbers
## Pin status per service

| Service | pinned | bounded | lower-only | unpinned |
|---|---:|---:|---:|---:|
| amazon_ads_mcp_service | 0 | 1 | 0 | 3 |
| authentication_service | 28 | 0 | 4 | 1 |
| dv360_mcp_service | 0 | 1 | 0 | 5 |
| gateway_service | 4 | 1 | 3 | 1 |
| google_ads_mcp_service | 2 | 0 | 0 | 2 |
| llm_service | 1 | 6 | 24 | 0 |
| meesho_seller_mcp_service | 0 | 1 | 0 | 3 |
| meta_mcp_service | 37 | 1 | 0 | 0 |
| sandbox | 2 | 2 | 0 | 0 |
| shared_components | 0 | 0 | 3 | 0 |
| skill_service | 0 | 0 | 7 | 0 |
| tv_planner_mcp_service | 0 | 0 | 0 | 5 |
| utility-service | 83 | 0 | 0 | 0 |
| whatsapp_webhook_service | 0 | 15 | 0 | 0 |
| **total** | **157** | **28** | **41** | **20** |

## Unpinned (no version at all)

- **amazon_ads_mcp_service**: httpx, mcp, uvicorn
- **authentication_service**: dotenv
- **dv360_mcp_service**: google-api-python-client, google-auth, google-auth-httplib2, mcp, uvicorn
- **gateway_service**: mcp
- **google_ads_mcp_service**: httpx, uvicorn
- **meesho_seller_mcp_service**: mcp, playwright, uvicorn
- **tv_planner_mcp_service**: google-cloud-dataproc, google-cloud-storage, mcp, openpyxl, uvicorn

## Specified differently across services

| Package | Specs by service |
|---|---|
| `asgiref` | authentication_service: `==3.11.1`; gateway_service: `==3.11.1`; utility-service: `==3.12.1` |
| `boto3` | authentication_service: `>=1.35.0`; llm_service: `>=1.34`; shared_components: `>=1.28`; utility-service: `==1.43.49` |
| `celery` | llm_service: `>=5.3`; shared_components: `>=5.3`; utility-service: `==5.4.0`; whatsapp_webhook_service: `>=5.3,<6.0` |
| `certifi` | authentication_service: `==2026.1.4`; meta_mcp_service: `==2026.6.17`; utility-service: `==2026.6.17` |
| `charset-normalizer` | authentication_service: `==3.4.4`; utility-service: `==3.4.9` |
| `django` | authentication_service: `==5.2.11`; gateway_service: `==5.2.11`; llm_service: `>=4.2,<5.1`; utility-service: `==5.2.11`; whatsapp_webhook_service: `>=5.2,<6.0` |
| `djangorestframework` | authentication_service: `==3.16.1`; gateway_service: `==3.16.1`; llm_service: `>=3.14`; utility-service: `==3.16.1` |
| `dotenv` | authentication_service: `(none)`; utility-service: `==0.9.9` |
| `fastapi` | skill_service: `>=0.111.0`; sandbox: `==0.115.*` |
| `google-auth` | dv360_mcp_service: `(none)`; utility-service: `==2.56.0` |
| `google-cloud-storage` | llm_service: `>=2.0`; tv_planner_mcp_service: `(none)` |
| `gunicorn` | authentication_service: `>=21.0`; gateway_service: `>=21.0`; whatsapp_webhook_service: `>=21.2,<24.0` |
| `httpx` | amazon_ads_mcp_service: `(none)`; gateway_service: `>=0.27.0`; google_ads_mcp_service: `(none)`; llm_service: `>=0.27`; meta_mcp_service: `==0.28.1`; skill_service: `>=0.27.0`; utility-service: `==0.28.1` |
| `idna` | authentication_service: `==3.11`; meta_mcp_service: `==3.18`; utility-service: `==3.18` |
| `jsonschema` | llm_service: `>=4.0`; meta_mcp_service: `==4.26.0`; utility-service: `==4.26.0` |
| `langchain-core` | llm_service: `>=0.3`; whatsapp_webhook_service: `>=0.3.0,<1.0` |
| `langchain-openai` | llm_service: `>=0.2`; whatsapp_webhook_service: `>=0.1,<1.0` |
| `langgraph` | llm_service: `>=0.3,<0.4`; whatsapp_webhook_service: `>=0.2,<1.0` |
| `mcp` | amazon_ads_mcp_service: `(none)`; amazon_ads_mcp_service: `>=0.9,<2.0`; dv360_mcp_service: `(none)`; dv360_mcp_service: `>=0.9,<2.0`; gateway_service: `(none)`; gateway_service: `>=0.9,<2.0`; google_ads_mcp_service: `==1.28.1`; llm_service: `==1.9.1`; llm_service: `>=0.9,<2.0`; meesho_seller_mcp_service: `(none)`; meesho_seller_mcp_service: `>=0.9,<2.0`; meta_mcp_service: `==1.28.1`; meta_mcp_service: `>=0.9,<2.0`; tv_planner_mcp_service: `(none)`; utility-service: `==1.28.1` |
| `openai` | skill_service: `>=1.35.3`; whatsapp_webhook_service: `>=1.0,<2.0` |
| `openpyxl` | llm_service: `>=3.1`; tv_planner_mcp_service: `(none)` |
| `psycopg2-binary` | authentication_service: `==2.9.11`; utility-service: `==2.9.11`; whatsapp_webhook_service: `>=2.9,<3.0` |
| `pydantic` | llm_service: `>=2.0,<2.14`; meta_mcp_service: `==2.13.4`; skill_service: `>=2.7.4`; utility-service: `==2.13.4` |
| `pydantic-settings` | meta_mcp_service: `==2.14.2`; skill_service: `>=2.3.4`; utility-service: `==2.14.2` |
| `pyjwt` | authentication_service: `==2.11.0`; llm_service: `>=2.8`; meta_mcp_service: `==2.13.0`; utility-service: `==2.13.0` |
| `pypdf` | llm_service: `>=4.0`; whatsapp_webhook_service: `>=4.0,<5.0` |
| `python-docx` | llm_service: `>=1.1`; whatsapp_webhook_service: `>=1.1,<2.0` |
| `python-dotenv` | llm_service: `>=1.0`; meta_mcp_service: `==1.2.2`; utility-service: `==1.2.2`; whatsapp_webhook_service: `>=1.0,<2.0` |
| `redis` | llm_service: `>=5.0`; shared_components: `>=5.0`; utility-service: `==5.2.1`; whatsapp_webhook_service: `>=5.0,<6.0` |
| `requests` | authentication_service: `==2.32.5`; utility-service: `==2.34.2`; whatsapp_webhook_service: `>=2.32,<3.0` |
| `typing-extensions` | authentication_service: `==4.15.0`; meta_mcp_service: `==4.16.0`; utility-service: `==4.16.0` |
| `tzdata` | authentication_service: `==2025.3`; utility-service: `==2026.3` |
| `urllib3` | authentication_service: `==2.6.3`; utility-service: `==2.7.0` |
| `uvicorn` | amazon_ads_mcp_service: `(none)`; dv360_mcp_service: `(none)`; gateway_service: `>=0.29.0`; google_ads_mcp_service: `(none)`; llm_service: `>=0.30`; meesho_seller_mcp_service: `(none)`; meta_mcp_service: `==0.51.0`; skill_service: `>=0.30.1`; tv_planner_mcp_service: `(none)`; utility-service: `==0.51.0`; sandbox: `==0.30.*` |


## What stands out
1. **Only `utility-service` and `meta_mcp_service` are fully pinned.** They are the model to copy.
2. **`llm_service` has the most lower-bound-only specs and is the one that just broke.** It also has duplicate
   `mcp` lines (`mcp[cli]==1.9.1` and `mcp>=0.9,<2.0`).
3. **The five small MCP services and `tv_planner` have unpinned `mcp` and `uvicorn`.** `dv360` also has unpinned
   Google client libraries; `meesho` has an unpinned `playwright`.
4. **`mcp` is `==1.9.1` in llm_service but `==1.28.1` in meta, google_ads and utility.** The 1.9.1 pin was added
   on purpose on 2026-07-29 ("match `langchain-mcp-adapters<0.2` compatibility"). Whether llm_service can move to
   1.28.1 is an open question: it needs a compatible `langchain-mcp-adapters`, and nobody has tested that here.
5. **`pydantic` is `==2.13.4` wherever it is pinned** (meta, utility), which supports the `<2.14` cap.
6. **Django differs:** `==5.2.11` in auth, gateway and utility; `>=4.2,<5.1` in llm_service (5.0.14 in the failed
   build); `>=5.2,<6.0` in whatsapp. These services share JWTs and a database.
7. **Check `authentication_service`: it lists `dotenv`, not `python-dotenv`.** They are different packages
   (utility-service also pins `dotenv==0.9.9`). Probably a typo that happens to install.
8. **Sandbox has no requirements file**: pins live inline in two Dockerfiles. `gateway_service` has an unpinned `mcp`.
9. `shared_components` is installed editable by llm_service only, and llm_service CI checks it out with no ref
   (always the default branch). A change there is a change to llm_service's build.

## Proposal (needs a team decision, nothing here is agreed yet)
- Give every service a compiled constraints file (`uv pip compile` or `pip-compile`), commit it, and make the
  Dockerfile install with `-c constraints.txt`. Keep `requirements.txt` as the human-edited intent.
- Order of work: (P0) llm_service, the only one that has broken; (P1) the MCP services and `tv_planner`, which
  are unpinned; (P2) bring Django, `mcp`, `pydantic` and `boto3` to one version across services where they share
  code or data.
- Add a CI step that fails on any dependency with no version (`python scripts/pin_report.py --fail-on-unpinned`
  is the same check, over these snapshots).
- Test on the Python version the image uses (3.11), and run a real image build per service before merging.

## Decisions and owners (fill in as a team)
| # | Question | Options | Decision | Owner | Date |
|---|---|---|---|---|---|
| 1 | Constraints files vs fully pinned `requirements.txt` | constraints / pin in place | _open_ | _TBD_ | |
| 2 | Can llm_service move to `mcp 1.28.1`? | test newer `langchain-mcp-adapters` / keep 1.9.1 | _open_ | _TBD_ | |
| 3 | One Django version across services? | 5.2.x everywhere / leave | _open_ | _TBD_ | |
| 4 | `dotenv` vs `python-dotenv` in auth | fix / leave | _open_ | _TBD_ | |
| 5 | CI check for unpinned deps | add to each repo / central | _open_ | _TBD_ | |

## Files
- `snapshots/<service>/requirements.txt` (and `package.json` for the frontend, `pyproject.toml` for shared_components)
- `snapshots/SOURCES.md`: which commit each snapshot came from
- `snapshots/sandbox/inline-pins.txt`: the sandbox's inline pins (hand-maintained)
