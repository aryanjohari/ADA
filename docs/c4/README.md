# C4 diagrams — ADA

C4 maps for this repository. **Containers** (level 2) is the default visitor / portfolio map.

| Level | Files | What it shows |
|-------|-------|---------------|
| **1 — Context** | [`1-context.mmd`](1-context.mmd) · [`1-context.md`](1-context.md) | ADA as one system, the operator, and external systems |
| **2 — Containers** | [`2-containers.mmd`](2-containers.mmd) · [`2-containers.md`](2-containers.md) | Runnable processes, local stores, publish sink |
| **3 — Components** | [`3-components/`](3-components/) | Internals for agent core, daemon, and publish workflows only |

There is **no Code level** (class diagrams) in this set.

## How to read

1. Start at **Context** if you need “what talks to what outside ADA.”
2. Use **Containers** as the mental model for day-to-day ops and for the portfolio site.
3. Open a **Component** diagram only when you need internals of one container.

IDs are stable kebab-case for machines; diagram labels stay plain English.

## Portfolio fetch

Root [`portfolio.yaml`](../../portfolio.yaml) points at:

- Mermaid fallback: [`docs/architecture.mmd`](../architecture.mmd) (aligned with Containers)
- Preferred map IR: [`docs/architecture.graph.json`](../architecture.graph.json) (built from Containers, not from C3)

Case study prose: [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).
