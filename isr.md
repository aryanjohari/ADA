# Ada ISR frontend (Phase 3.5) — Next.js blueprint

Authoritative **consumer** spec for a Next.js App Router app that reads the same S3 objects Ada’s **`DEPLOY`** step writes. The **normative** API surface for JSON is the Python Pydantic models; this document mirrors them and adds routing, caching, and fetch strategy.

**Normative code (do not drift):** [`src/ada/publish/page_schema_v1.py`](src/ada/publish/page_schema_v1.py) — `PageJsonV1`, `LeadGenV1` — and [`src/ada/publish/s3_publish.py`](src/ada/publish/s3_publish.py) — S3 keys, `manifest.json` parsing. Short summary: [`docs/pseo-isr-contract.md`](docs/pseo-isr-contract.md).

## Product intent (unchanged)

- **Authority:** Long-form, EEAT-style guides (HTML in `content`).
- **Matchmaker:** Lead capture via a native UI driven by `lead_gen` (no untrusted raw HTML forms for the main funnel).
- **Entry traffic:** Landings on guide routes; homepage can be search- or directory-first and minimal.
- **Trust:** Static trust routes (e.g. `/faq`, `/privacy-policy`, `/terms-of-service`), clear footer/legal, minimal motion (optional hover only).

## Brand and configuration

Keep public name, base URL, nav, and legal links in a **single** site module (e.g. `config/site` or `lib/site`). Do not hardcode marketing strings across components.

**Canonical origin:** from `metadataBase` / env (e.g. `NEXT_PUBLIC_SITE_URL`). No subdomain-based canonical split (see Routing).

## S3 key layout (must match Ada)

| Object         | Key pattern |
| -------------- | ----------- |
| `manifest.json` | `/{project_id}/{campaign_id}/manifest.json` |
| `page.json`     | `/{project_id}/{campaign_id}/{slug}/page.json` |

- **`project_id`:** First path segment. Ada treats every **top-level** prefix in the bucket as a project; the app may **merge** all projects it discovers.
- **`campaign_id`:** Second segment. A folder is a **routable campaign** if `manifest.json` exists at the path above. Ada does **not** add discoverable routes by publishing `page.json` alone — **`DEPLOY`** merges the route into `manifest.json` after writing the page.

**Optional:** `AWS_ENDPOINT_URL` for MinIO or S3-compatible storage (see Ada `Settings`).

**IAM (read app):** `s3:ListBucket` on the bucket, plus `s3:GetObject` and `s3:HeadObject` on `/{project_id}/{campaign_id}/*` (tighten to known prefixes if you control them). Ada’s writer may use a narrower key prefix; the bucket name is the same (prefer **`S3_BUCKET_NAME`**, or **`ADA_S3_BUCKET`** in Ada, same value).

## Minimal S3 access strategy

**Goal:** Few calls, predictable behavior at build and request time.

1. **Discovery (build or background):**  
   - List top-level “folders” = `project_id`.  
   - For each `project_id`, list prefixes or probe `HeadObject` / list until each `campaign_id` with a `manifest.json` is known.  
   - **`GetObject` each `manifest.json` once** per revalidation window and normalize entries (see below).

2. **Route index in memory (cached):**  
   - Merge all manifest entries into a **single list of routes**, each record carrying at least: `niche`, `slug`, `title`, and **pointers** `project_id`, `campaign_id` (and optional card fields: `excerpt`, `image_url`, `published_at` if present in JSON).  
   - Use this merged list to:  
     - **Homepage grid** (preview cards).  
     - **`generateStaticParams`** (optional pre-render).  
     - **`sitemap.xml`** (all `{ niche, slug }` public URLs you expose).

3. **Per-page fetch (dynamic ISR):**  
   - After resolving a public URL to `(project_id, campaign_id, slug)` via the index, **`GetObject` only** `/{project_id}/{campaign_id}/{slug}/page.json`.  
   - Do not list the entire campaign folder for normal page loads.

**Revalidation:** Use one interval (e.g. **2 days** / `172800` seconds) for ISR and for caching manifest discovery, unless overridden by env (e.g. `PSEO_REVALIDATE_SECONDS`). Keep a **numeric literal** `export const revalidate = …` in each ISR route file if required by your Next version. Use `dynamicParams = true` if you pre-render a subset and generate the rest on demand.

**404:** If `page.json` is missing or invalid → `notFound()`.

**Case sensitivity:** Public paths should compare `niche` and `slug` **case-insensitively** for matching. The S3 key segment for the slug is whatever Ada published (the canonical slug string in `page.json` and the folder name).

## Collision policy (merged manifests)

If two campaigns (possibly under different `project_id`s) publish the same `(niche, slug)` (case-insensitive), pick a **deterministic** owner: e.g. sort by `project_id` then `campaign_id` lexicographically; **first wins** for the URL and the `GetObject` target. Log a warning in development when a duplicate is skipped.

## `manifest.json` (Ada-side normalization)

The backend’s **`normalize_manifest_to_entries`** ([`s3_publish.py`](src/ada/publish/s3_publish.py)) accepts:

- A **top-level JSON array** of **objects**; or  
- A **top-level object** with the first non-empty list found on one of: **`entries`**, **`pages`**, **`routes`**, **`items`**.

Each kept row is a `dict` (other shapes are dropped). There is no `slugs` + `default_niche` expander in Ada; prefer explicit `{ "niche", "slug", … }` rows.

**After `DEPLOY`**, a typical row includes at least: **`niche`**, **`slug`**, **`title`**, **`excerpt`** (shortened from `meta_description`). The frontend should tolerate extra keys (e.g. `image_url`, `published_at`) for cards and sitemap.

**Upsert rule (publisher):** v1 is **last-write-wins** on concurrent manifest writers; the Next app is read-only.

## `page.json` — **strict** `PageJsonV1` contract

Source: **`ada.publish.page_schema_v1.PageJsonV1`**. The models use **`model_config = ConfigDict(extra="forbid")`** — **unknown top-level or `lead_gen` keys cause validation failure** in Ada; the Next app should use the same shape when parsing/typing (e.g. Zod with `.strict()`).

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `slug` | `string` | yes | URL segment; S3 path uses this folder name. |
| `title` | `string` | yes | e.g. `metadata.title` |
| `meta_description` | `string` | yes | e.g. `metadata.description` |
| `og_image` | `string \| null` | no | Omitted or `null` in JSON is fine (`Optional` in Pydantic). DRAFT fills a default. |
| `content` | `string` | yes | Semantic **HTML**; sanitize before `dangerouslySetInnerHTML` (e.g. in `prose`). |
| `lead_gen` | **object** (see `LeadGenV1` below) | yes | **Not** an array at the `page.json` top level. |
| `json_ld` | `object` (JSON: arbitrary keys) | yes | Pydantic: `dict[str, Any]`. Emit as JSON-LD in `<head>` (e.g. `application/ld+json` script). |

### `lead_gen` → **`LeadGenV1`**

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `form_fields` | **array** | yes (may be **empty** `[]`) | Pydantic: `list[Any]`. Each item is usually an object (e.g. `name`, `type`, `label`, `options`, etc.). The **array lives here** — if you only saw “lead_gen array” in a checklist, it refers to **`form_fields`**, not `lead_gen` itself. |
| `form_action_url` | `string` | yes | Full POST action URL. |
| `call_display_phone` | `string` | yes | Display string. |
| `call_tel_link` | `string` | yes | e.g. `tel:+1…` |

**UI:** Render native controls from `form_fields` and POST to `form_action_url`; no injected third-party form HTML for the primary funnel unless you add a separate, reviewed path.

**Fixture:** see [`tests/fixtures/pseo_page.json`](tests/fixtures/pseo_page.json) for a round-trippable example.

## Routing (simple — **no** subdomain rewrites)

Use **path-only** URLs on a **single host** (apex or `www` — your choice, one canonical). **Do not** implement `niche.example.com` → path rewrites, **do not** depend on `ROOT_DOMAIN` / `PSEO_SUBDOMAIN_POST_URL` for this version.

Choose **one** App Router pattern and stick to it:

| Pattern | File | Resolving `page.json` |
| -------- | ---- | --------------------- |
| **`/[niche]/[slug]`** | e.g. `app/[niche]/[slug]/page.tsx` | Look up `(niche, slug)` in the merged manifest index → `project_id`, `campaign_id` → S3 `GetObject` as above. Best match for pSEO and Ada’s `niche`+`slug` manifest rows. |
| **`/[campaign_id]/[slug]`** | e.g. `app/[campaign_id]/[slug]/page.tsx` | Look up `(campaign_id, slug)` in the index (you must have discovered `project_id` + `campaign_id` + `slug` per row). Niche is not in the URL; still available from manifest for breadcrumbs/copy. If `campaign_id` is ambiguous across projects, use the **collision** rule or namespace with a static prefix (e.g. `/c/[campaign_id]/[slug]`). |

**Breadcrumbs (example):** home → human label for niche (or campaign) → `title` from `page.json`.

**Static pages:** same as before: `/`, `/recent-posts` (if you want a full list), trust routes — adjust to your sitemap.

## ISR, sitemap, robots

- **ISR route:** `revalidate` aligned with manifest cache; `generateStaticParams` from merged index if you pre-build known pairs.  
- **`sitemap.ts`:** Emit homepage, static trust routes, and every public guide URL derived from the merged index. If S3 is down at build, still emit non-dynamic URLs if you can.  
- **`robots.ts`:** Index production only; previews/staging `Disallow: /` unless you intentionally override. No subdomain-specific rules.

**Canonical URLs for guides:** always `https://{canonical host}/{path}` with the path style you chose (niche- or campaign-based). `metadataBase` + `alternates` as usual.

## Layout notes (implementation checklist)

- **Article:** `prose` (e.g. Tailwind Typography), sanitized HTML for `content`.  
- **Aside:** Sticky lead column with the component that reads `lead_gen`.  
- **Homepage:** Card grid from manifest entries (image from manifest `image_url` when present, else load `page.json.og_image`).  
- **No animation requirement** in v1; optional subtle hover.

## Environment variables (read-side Next app)

| Variable | Purpose |
| -------- | ------- |
| `S3_BUCKET_NAME` | Same bucket Ada publishes to (align with [`ADA_S3_BUCKET`](src/ada/config.py) if used there). |
| `AWS_REGION` | Region. |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Or instance role. |
| `AWS_ENDPOINT_URL` | Optional; S3-compatible / local. |
| `NEXT_PUBLIC_SITE_URL` | Canonical site origin, `metadataBase`, sitemap. |
| `PSEO_REVALIDATE_SECONDS` | Optional; override default revalidate. |
| `PSEO_DEBUG` / `NODE_ENV` | Verbose server logging in dev. |
| `FORCE_INDEXING` / `ROBOTS_NOINDEX` | Robots edge cases (optional). |

**Removed from this v1 spec:** `ROOT_DOMAIN`, `PSEO_SUBDOMAIN_POST_URL`, and all middleware that rewrites subdomains to path segments.

## Local dev

- Without S3 config, manifest index is empty: dynamic routes 404, homepage list empty.  
- Use a real bucket or `AWS_ENDPOINT_URL` + MinIO and sample keys matching Ada.

## Quick reference: backend files

| Area | File |
| ---- | ---- |
| Page JSON schema | [`src/ada/publish/page_schema_v1.py`](src/ada/publish/page_schema_v1.py) |
| S3 keys + manifest | [`src/ada/publish/s3_publish.py`](src/ada/publish/s3_publish.py) |
| One-page contract | [`docs/pseo-isr-contract.md`](docs/pseo-isr-contract.md) |
| Golden roundtrip test | [`tests/test_publish_page_schema.py`](tests/test_publish_page_schema.py), [`tests/fixtures/pseo_page.json`](tests/fixtures/pseo_page.json) |

If `PageJsonV1` in code gains fields, **update this file and the Zod (or similar) types in the Next app in the same commit** as the Pydantic change.
