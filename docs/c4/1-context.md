# System Context (C1)

ADA is one local system on the operator’s machine. There is **no** hosted multi-tenant API and **no** Docker Compose stack in this repository.

## Elements

| ID | Role | Evidence |
|----|------|----------|
| `operator` | Person who runs `ada` CLI, schedules cron/systemd, optionally opens Streamlit HUD on localhost | [`src/ada/__main__.py`](../../src/ada/__main__.py), [`ops/schedule.md`](../../ops/schedule.md) |
| `ada` | Headless Python package: chat, daemon, offline ingest/graph, publish workflows | [`pyproject.toml`](../../pyproject.toml) entry `ada` |
| `gemini` | Required for model turns (chat, daemon goals, dream, triage, graph extract/enrich) | [`src/ada/adapters/gemini_stream.py`](../../src/ada/adapters/gemini_stream.py), `GEMINI_API_KEY` |
| `sources` | RSS / brand / GSC / GETS / DataForSEO keywords — pulled by ingest CLIs, not auto-fetched by chat | [`src/ada/ingest/`](../../src/ada/ingest/) |
| `webtools` | Serper + Jina when API keys set | [`src/ada/tools/web_runtime.py`](../../src/ada/tools/web_runtime.py) |
| `s3` | Publish sink for `page.json` and campaign `manifest.json` (boto3; optional `AWS_ENDPOINT_URL`) | [`src/ada/publish/s3_publish.py`](../../src/ada/publish/s3_publish.py) |
| `isr` | Separate codebase; reads S3 under a documented contract | [`isr.md`](../../isr.md); contract doc often local-only under `docs/` |

## Collapsed into notes (not separate C1 boxes)

| Item | Where it lives |
|------|----------------|
| Unsplash (hero images on DRAFT) | Publish path; env-gated in draft code |
| Apprise notifications | Optional import in [`notifications.py`](../../src/ada/notifications.py); **not** in `pyproject.toml` |
| Gemini embeddings | Optional `ADA_KNOWLEDGE_EMBEDDINGS` / `gemini-embedding-001` |

## Non-goals at this level

- No public demo URL claimed
- No Docker Compose or in-repo HTTP agent API
- No inventing users, metrics, or hosted SaaS tenants
