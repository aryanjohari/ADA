# PSEO / ISR contract: `page.json` v1 and S3 layout

**Normative source code:** [`src/ada/publish/page_schema_v1.py`](../src/ada/publish/page_schema_v1.py) — `PageJsonV1`, `LeadGenV1` use `ConfigDict(extra="forbid")`. **Unknown keys fail validation** in Ada and must not be added casually.

**Deploy / keys:** [`src/ada/publish/s3_publish.py`](../src/ada/publish/s3_publish.py) — S3 object layout and `manifest.json` merge behavior.

**Narrative Next.js blueprint:** [`isr.md`](../isr.md) (routing, caching, product intent). The **Next.js app is out of this repository**; treat this document plus the Pydantic models as the **stable contract** for ISR consumers.

---

## S3 key layout (must match Ada)

| Object | Key pattern |
|--------|-------------|
| `manifest.json` | `/{project_id}/{campaign_id}/manifest.json` |
| `page.json` | `/{project_id}/{campaign_id}/{slug}/page.json` |

- **`project_id`** / **`campaign_id`** come from workflow params and env defaults (`ADA_PROJECT_ID`, `ADA_CAMPAIGN_ID`).
- A route is discoverable to a reader app after **`DEPLOY`** merges the slug into **`manifest.json`** (see `s3_publish.py`).

---

## `page.json` v1 top-level shape

| Field | Notes |
|-------|--------|
| `slug` | URL segment; required |
| `title` | Required |
| `meta_description` | Required |
| `og_image` | Optional in model; **DEPLOY** may require non-empty (see workflow runner) |
| `content` | HTML string |
| `lead_gen` | Object: `form_fields`, `form_action_url`, `call_display_phone`, `call_tel_link` — **no extra keys** |
| `json_ld` | JSON-LD object |

**Stability rule:** Any change to field names, nesting, or requiredness must be reflected in **`page_schema_v1.py`**, golden tests under `tests/test_publish_page_schema.py` and `tests/fixtures/pseo_page.json`, and coordinated with the **ISR Next** consumer (Zod / strict parse recommended).

---

## GATE vs keyword-led pages

- **Fact GATE** (`ADA_PUBLISH_MIN_UNIQUE_FACTS`, distinct `source_url` on graph edges) applies only to **`publish_entity_v1`** workflows.
- **`publish_keyword_v1`** still produces **`PageJsonV1`** for **DRAFT** / **DEPLOY** but does **not** run the graph GATE step. **Publish approval** (`ADA_REQUIRE_APPROVAL_FOR_PUBLISH`) applies to **DEPLOY** for both template kinds when enabled.

See [`docs/operator-runbook-raspberry-pi.md`](operator-runbook-raspberry-pi.md) for operator pacing (cron / matrix caps / approvals), not autonomous revenue logic.
