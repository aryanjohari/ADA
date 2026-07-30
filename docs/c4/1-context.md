# System Context (C1)

ADA is one local system on the operator’s machine. There is no hosted multi-tenant API in this repository.

## Elements

| ID | Role |
|----|------|
| **Operator** | Person who runs `ada` CLI, schedules cron/systemd jobs, and optionally opens the Streamlit HUD on localhost |
| **ADA** | Headless Python package: chat, daemon, offline ingest/graph, publish workflows |
| **Google Gemini** | Required for model turns (chat, daemon goals, dream, triage, graph extract/enrich) |
| **Content sources** | RSS / brand / GSC / GETS — pulled by ingest CLIs, not auto-fetched by chat |
| **Optional web tools** | Serper and Jina when API keys are set; DataForSEO / Unsplash / Apprise are also env-gated (collapsed here) |
| **AWS S3** | Publish sink for `page.json` and campaign `manifest.json` |
| **ISR frontend** | Separate codebase; reads S3 under a documented contract ([`pseo-isr-contract.md`](../pseo-isr-contract.md)) |

## Non-goals at this level

- No public demo URL claimed
- No Docker Compose or in-repo HTTP agent API
