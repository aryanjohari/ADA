# Components — Publish workflows

Deterministic pipelines advanced by `ada daemon` (or workflow CLI helpers). Templates live in [`src/ada/workflow/templates.py`](../../../src/ada/workflow/templates.py).

## Tracks

| Kind | Steps |
|------|--------|
| `publish_entity_v1` | ENRICH → **GATE** → DRAFT → DEPLOY |
| `publish_keyword_v1` | ENRICH → DRAFT → DEPLOY (no GATE) |
| `rss_fetch_then_graph_then_synth` | FETCH → EXTRACT → SYNTHESIZE (non-publish; same template registry) |

## Components

| ID | Role | Evidence |
|----|------|----------|
| `enrich` | Builds publish context from local graph / knowledge | [`publish/enrich.py`](../../../src/ada/publish/enrich.py), [`workflow/publish_enrich_step.py`](../../../src/ada/workflow/publish_enrich_step.py) |
| `gate` | Requires enough **distinct** canonical HTTPS `source_url` facts (default `ADA_PUBLISH_MIN_UNIQUE_FACTS=3`) | [`workflow/runner.py`](../../../src/ada/workflow/runner.py); repeating one URL does not help |
| `draft` | Emits page body; optional Unsplash hero | [`publish/draft.py`](../../../src/ada/publish/draft.py) |
| `page-schema` | Pydantic `PageJsonV1` (`extra="forbid"`) | [`publish/page_schema_v1.py`](../../../src/ada/publish/page_schema_v1.py) |
| `deploy` | Writes S3 `/{project_id}/{campaign_id}/{slug}/page.json` and merges `manifest.json` | [`publish/s3_publish.py`](../../../src/ada/publish/s3_publish.py) |

Delivery modes include `isr_s3`, `none`, and `wordpress_csv_s3` ([`templates.py`](../../../src/ada/workflow/templates.py)). Optional approval flags can require operator approval before enqueue or DEPLOY.

Out-of-repo Next.js consumer: [`isr.md`](../../../isr.md).
