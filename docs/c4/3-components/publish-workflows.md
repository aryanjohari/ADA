# Components — Publish workflows

Deterministic pipelines advanced by `ada daemon` (or workflow CLI helpers). Templates live in [`src/ada/workflow/templates.py`](../../../src/ada/workflow/templates.py).

## Tracks

| Kind | Steps |
|------|--------|
| `publish_entity_v1` | ENRICH → **GATE** → DRAFT → DEPLOY |
| `publish_keyword_v1` | ENRICH → DRAFT → DEPLOY (no GATE) |

## Components

| ID | Role |
|----|------|
| **ENRICH** | Builds publish context from local graph / knowledge |
| **GATE** | Requires enough **distinct** canonical HTTPS `source_url` facts (default `ADA_PUBLISH_MIN_UNIQUE_FACTS=3`); repeating one URL does not help |
| **DRAFT** | Emits Pydantic `PageJsonV1` (`extra="forbid"`) |
| **DEPLOY** | Writes S3 `/{project_id}/{campaign_id}/{slug}/page.json` and merges `manifest.json` |

Optional approval flags can require operator approval before enqueue or DEPLOY. Delivery modes include `isr_s3`, `none`, and `wordpress_csv_s3` (see templates).

Contract for the out-of-repo Next.js consumer: [`pseo-isr-contract.md`](../../pseo-isr-contract.md).
