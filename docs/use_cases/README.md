# Use-case specs

How to specify Friend / House / Lab features **before** implementation. K0 ships the template and index only — no full use-case specs yet.

**Write a use-case spec before implementing Friend/House/Lab features.**

---

## Lifecycle

1. **Brainstorm** — bucket ([ADA_ENTITY_BUCKETS.md](../ADA_ENTITY_BUCKETS.md)), operator story, out of scope.
2. **Spec** — copy [`_TEMPLATE.md`](_TEMPLATE.md) to `docs/use_cases/<id>.md`; fill all sections.
3. **Implement** — one use case per PR; follow [TOOL_EXTENSION_GUIDE.md](../TOOL_EXTENSION_GUIDE.md) capability ladder.
4. **Smoke** — checklist in spec; Pi paths in [MEMORY_OPS.md](../MEMORY_OPS.md) where relevant.

Add the row to [INDEX.md](INDEX.md) when status moves from `idea` → `spec` → `shipped`.

---

## Capability choice

Use the decision tree in [TOOL_EXTENSION_GUIDE.md](../TOOL_EXTENSION_GUIDE.md) § A. Document the chosen layer (`primitive` | `skill` | `goal` | `workflow`) and why higher layers were rejected.

---

## Bucket docs

| Bucket | Detail doc |
|--------|------------|
| friend | [buckets/FRIEND.md](../buckets/FRIEND.md) |
| house | [buckets/HOUSE.md](../buckets/HOUSE.md) |
| lab | [buckets/LAB.md](../buckets/LAB.md) |

---

## Index

Planned use cases (ideas only): [INDEX.md](INDEX.md).

Template: [_TEMPLATE.md](_TEMPLATE.md).
