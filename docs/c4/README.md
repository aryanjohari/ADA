# C4 diagrams — ADA

Official-style C4 maps built **bottom-up from this repo**. Source of truth for architecture diagrams.

| Level | Files | What it shows |
|-------|-------|---------------|
| **1 — Context** | [`1-context.mmd`](1-context.mmd) · [`1-context.md`](1-context.md) | ADA as one system, the operator, external systems |
| **2 — Containers** | [`2-containers.mmd`](2-containers.mmd) · [`2-containers.md`](2-containers.md) | Runnable processes, in-process libraries, local stores, publish sink |
| **3 — Components** | [`3-components/`](3-components/) | Internals per container that needs a zoom |
| **Zoom index** | [`portfolio-map.json`](portfolio-map.json) | Machine map for Context → Containers → Components |

There is **no Code level** (class diagrams) in this set.

## How to read (zoom path)

1. **Context** — who uses ADA and which external systems it talks to.
2. **Containers** — what actually runs on the operator’s machine (default portfolio view).
3. **Components** — open only when you need internals of one container (agent core, daemon, ingest, graph-lite, publish, HUD).

Visitor labels are plain English; machine IDs are stable kebab-case (see `portfolio-map.json`).

## Portfolio fetch

Root [`portfolio.yaml`](../../portfolio.yaml):

- `c4:` → [`portfolio-map.json`](portfolio-map.json) (preferred for zoom UI)
- `diagram:` → [`2-containers.mmd`](2-containers.mmd)
- Sync’d GitHub overview alias: [`docs/architecture.mmd`](../architecture.mmd) (same shape as Containers; not a second source of truth)

Case study prose: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).

Old portfolio flowchart IR: [`docs/archive/architecture.graph.json`](../archive/architecture.graph.json) (retired).
