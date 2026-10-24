# Hands baseline

Recorded pytest and catalog drift gates for the Hands refactor.

## H2 (2026-05-21) — single chat execution bus

- Removed `enqueue_workflow` from Gemini chat tool declarations.
- Work chat: `run_skill` + `get_workflow_status` only for workflow surface.
- Catalog: `enqueue_workflow` capability with `chat_declared: false`.

**Drift tests:** `tests/test_h2_single_bus.py`, `tests/test_hands_catalog_drift.py`

**Regenerate catalog:**

```bash
PYTHONPATH=src python3 scripts/generate_hands_catalog.py
PYTHONPATH=src python3 scripts/generate_hands_catalog.py --check
```

**Targeted pytest:**

```bash
pytest tests/test_h2_single_bus.py tests/test_hands_catalog_drift.py tests/test_run_skill.py tests/test_entity_tools.py tests/test_entity_work_regression.py -q
```
