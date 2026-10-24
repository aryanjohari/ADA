# Hands catalog

Machine-readable catalog: [`hands_catalog.json`](hands_catalog.json).

Regenerate after tool or ingress changes:

```bash
PYTHONPATH=src python scripts/generate_hands_catalog.py
PYTHONPATH=src python scripts/generate_hands_catalog.py --check
```

Capability rows include per-surface availability: `chat`, `plan`, `agent`, `setup`.
