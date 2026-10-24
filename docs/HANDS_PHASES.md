# Hands phases

| Phase | Scope | Status |
| ----- | ----- | ------ |
| H0–H9  | Chat surfaces, programme, HUD | Shipped (see repo docs) |
| **J0** | `kernel_boot`, `ada boot`, `base_ops` / `ada_ops` templates, memory examples, persona docs | **Shipped** |
| **J1** | Primitives (`add_task`, `log_memory`, `body_check`, …) | **Shipped** |
| **J2** | `run_primitive` in Chat | **Shipped** |
| **J3** | HUD chips via primitives | **Shipped** |
| **J4** | `ada reload`, ops doc, `jarvis` → `ada` rename sweep, Pi smoke checklist | **Shipped** |
| **K0** | Entity buckets docs, TOOL_EXTENSION_GUIDE, MEMORY_OPS, use_cases template + INDEX | **Shipped** (this PR) |

## J-track references

- [ADA_PERSONA.md](ADA_PERSONA.md) — voice and hats
- [ADA_BIOLOGY.md](ADA_BIOLOGY.md) — kernel metaphor
- [ADA_CORE_OPS.md](ADA_CORE_OPS.md) — autonomic `ada_ops`, deploy ritual, manual smoke
- Templates: `templates/missions/base_ops.yaml`, `templates/missions/ada_ops.yaml`
- Examples: `memory/*.example.md` → copy into profile `memory_dir`

## J-track commands

```bash
ada boot      # idempotent kernel ensure + print ids
ada reload    # kernel_boot + systemd daemon restart (when configured)
```

Chat and daemon call `kernel_boot` on open/start after profile identity check.

## K-track references

- [ADA_ENTITY_BUCKETS.md](ADA_ENTITY_BUCKETS.md) — Friend / House / Lab map
- [TOOL_EXTENSION_GUIDE.md](TOOL_EXTENSION_GUIDE.md) — capability ladder and file touches
- [MEMORY_OPS.md](MEMORY_OPS.md) — entity memory operator guide
- [buckets/FRIEND.md](buckets/FRIEND.md), [buckets/HOUSE.md](buckets/HOUSE.md), [buckets/LAB.md](buckets/LAB.md)
- [use_cases/README.md](use_cases/README.md), [use_cases/INDEX.md](use_cases/INDEX.md)
