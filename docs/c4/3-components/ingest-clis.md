# Components — Ingest CLIs

Offline / scheduled pulls into local SQLite. Chat does **not** auto-fetch these sources.

## Components

| ID | Role | Evidence |
|----|------|----------|
| `rss` | Fetch registered RSS/Atom feeds into `knowledge_items` | [`ingest/rss.py`](../../../src/ada/ingest/rss.py); CLI `ada ingest-rss` |
| `brand` | HTTP pull of brand / site URLs | [`ingest/brand.py`](../../../src/ada/ingest/brand.py); `ada ingest-brand` |
| `gsc` | Google Search Console ingest | [`ingest/gsc_cli.py`](../../../src/ada/ingest/gsc_cli.py), [`gsc_service.py`](../../../src/ada/ingest/gsc_service.py) |
| `gets` | NZ GETS public index poll | [`ingest/gets.py`](../../../src/ada/ingest/gets.py); default URL in config / `.env.example` |
| `keywords` | DataForSEO keyword volume | [`ingest/keywords.py`](../../../src/ada/ingest/keywords.py); needs `DATAFORSEO_*` |
| `feed-gate` | Scores RSS entries before insert | [`ingest/gate.py`](../../../src/ada/ingest/gate.py) |

Optional embeddings on ingest when `ADA_KNOWLEDGE_EMBEDDINGS` is set ([`knowledge_embeddings.py`](../../../src/ada/knowledge_embeddings.py)).

Daemon `system_jobs` may also run `ingest.run` for some kinds (e.g. GSC) via [`jobs/handlers.py`](../../../src/ada/jobs/handlers.py)—same ingest modules, different entry.
