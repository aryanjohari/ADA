# Components — Graph-lite

CLI pipeline that turns ingested knowledge into a local entity/edge graph used by publish GATE and DRAFT.

## Components

| ID | Role | Evidence |
|----|------|----------|
| `triage` | LLM scores unscored `knowledge_items` (NZ-relevant impact 1–10 + taxonomy) | [`triage/run.py`](../../../src/ada/triage/run.py); CLI `ada triage` |
| `extract-graph-lite` | LLM extracts a small graph; server upserts entities/edges | [`extract/graph_lite.py`](../../../src/ada/extract/graph_lite.py); `ada extract-graph-lite` |
| `enrich-graph` | Batch widen entity facts for publish DRAFT inputs | [`cli.py`](../../../src/ada/cli.py) `run_enrich_graph_cli`, [`publish/batch_enrich_context.py`](../../../src/ada/publish/batch_enrich_context.py) |
| `entity-types` | Canonical entity type set + aliases | [`graph/entity_types.py`](../../../src/ada/graph/entity_types.py) |

Requires `GEMINI_API_KEY` (unlike pure HTTP RSS ingest). Related: `ada matrix-scan` plans publish subjects from the graph ([`publish/matrix*.py`](../../../src/ada/publish/))—scheduled separately, not a fourth graph CLI box.
