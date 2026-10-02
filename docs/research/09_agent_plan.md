# 09 — Agent plan

Access date for every source below: 2026-09-29.

Tags: **POLICY** (a rule this card locks), **METAL** (code this card read: the file, and what the function does), **FEASIBLE** (this origin can host the object). A vendor page selling a content pipeline would be **MARKETING** and is not used as a ranking rule. None of the sources below are that.

The steps are the five in card 04. The inputs and the first yes are card 07. The file contract and the confirm path are card 08. This card names the code, in order, that carries one campaign row through those locks. It writes no product code and no post.

## 1. Question

What code, in what order, makes one confirmed campaign row into one live-ready markdown file on the portfolio, then can delete that file and write the same slug again?

## 2. Short answer

**POLICY.** Six slices, in this order. Store one row. Gather a packet from card 01 only. Draft one local markdown file. A confirm copies that file into a named checkout. A delete confirm removes it and clears the slug so the next draft of the same question may write it again. Git push stays a later confirm.

The test is Ada drafting card 01, the operator confirming, the file landing in the checkout, the operator deleting it, and Ada writing that slug again. This card contains no post body.

## 3. What the earlier cards left open

**POLICY.** The page fields live in a sidecar, `memory/facts/campaign_pages/{id}.yaml`, under the ada-data root. [src/ada/io/paths.py](src/ada/io/paths.py) gains a `DataPaths` property for that directory. Site, audience, source, question, fill, the optional call to action, the packet, and the slug are keys on that file.

**METAL.** [src/ada/memory/open_loops.py](src/ada/memory/open_loops.py). `upsert_loop` stores status, stages, `current_stage`, `next_wake_at`, and `last_receipt` for `kind: campaign`. `CAMPAIGN_STATUSES` includes `waiting_on_aryan`. Cards 07 and 08 leave site, audience, a queue, and links off that file. This card still does not add those keys to `upsert_loop`.

**POLICY.** The checkout path is the environment variable `ADA_PORTFOLIO_CHECKOUT`. It must be an existing git checkout whose origin URL contains `aryanjohari/aryan-portfolio`. An unset variable, a missing directory, or a different remote is a refusal. This card hardcodes no home directory. Card 08 did not name this path.

**METAL.** [src/ada/memory/artifacts.py](src/ada/memory/artifacts.py). `write_artifact` resolves only under `artifacts/`. A relative path that escapes that root is denied. The checkout copy cannot be `artifact_write`.

**METAL.** [src/ada/hud/routes_api.py](src/ada/hud/routes_api.py). `api_confirm` on `POST /api/confirm` re-executes one tool only when the name is in `_CONFIRMABLE_TOOLS`. Any other name returns `confirm_not_wired` and writes nothing. [src/ada/hud/chat_service.py](src/ada/hud/chat_service.py). `confirm_tool` binds the stashed args when `pending_id` is set, sets `confirmed=true`, and calls `gateway.execute`. A `needs_confirm` tool receipt is stashed in `pending_confirms`. [src/ada/hud/static/js/api.js](src/ada/hud/static/js/api.js). `postConfirm` already posts `{ tool, args, pending_id }`. This card adds no button.

**POLICY.** The blog slug is its own function. It lowercases the question, replaces each run of characters outside `a-z` and `0-9` with one hyphen, and strips hyphens at the ends. The result must be one path segment: non-empty, not `.` or `..`, no slash, no leading dot, at most 80 characters. An empty result or a longer result is a refusal. This card does not truncate and does not mint a `-2` suffix.

**METAL.** `_slugify` in `artifacts.py` keeps `.` and `_`, falls back to `note`, and cuts at 80. That function is not the blog slug. Card 08.

**POLICY.** Card 01’s question, the sentence in its §1, slugifies to 146 characters. Storing that sentence as the title is a refusal. The operator types a shorter question. The source on the row stays `docs/research/01_how_discovery_works.md`. The fill is `researched`.

**METAL.** `aryanjohari/aryan-portfolio` `src/lib/blog.ts`, read 2026-09-29. `readPostFile` takes the slug from the filename without `.md`, refuses an empty slug, `.`, and `..`, and requires `title`, `question`, `description`, `published`, `modified`, `fill` (`build-log`, `lesson`, or `researched`), `source`, and `canonical`. `canonical` must equal `/blog/{slug}`. Dates must be real `YYYY-MM-DD` values. `source` is kept and not rendered. `getBlogPosts` reads `content/blog/*.md`. A file that breaks the contract fails the build. This repo has no `src/lib`. This card does not edit `blog.ts`.

## 4. Slices

One wake still advances one stage of this one item, writes `next_wake_at`, and sleeps. Card 07. The slices below are that order. A later slice refuses to run when the earlier slice has not left its receipt.

### Slice 1 — Store one campaign row

**POLICY.** The row holds site, audience, source, question, fill, and an optional call to action. The call to action is a label and a URL, both present or both absent. Site is `github.com/aryanjohari/aryan-portfolio`. Any other site is refused. Audience is one sentence. Source for this test is `docs/research/01_how_discovery_works.md`. Question is the string the operator types, and it becomes the title. Fill is `researched`. A wake does not supply a missing field. Card 07. Card 08.

**Files.** New [src/ada/memory/campaign_page.py](src/ada/memory/campaign_page.py) reads and writes the sidecar. [src/ada/io/paths.py](src/ada/io/paths.py) gains the directory property. New [src/ada/tools/blog_tools.py](src/ada/tools/blog_tools.py) holds the handler. [src/ada/tools/toolspec.py](src/ada/tools/toolspec.py) registers `blog_page_upsert` with `side_effect` `append_local` and agent mode. [src/ada/tools/gateway.py](src/ada/tools/gateway.py) dispatches that name to the handler.

**Reuse.** `upsert_loop` creates the `kind: campaign` shell: status, stages, `next_wake_at`. The page fields are not arguments to `upsert_loop`. The YAML write uses the existing atomic text write. `CAMPAIGN_STATUSES` is unchanged.

**How you know.** The sidecar reads back with those fields. `open_loops.yaml` has the campaign and does not contain site, audience, source, question, fill, or the call to action. A second site is refused. A question whose slug is longer than 80 characters is refused and is not shortened. Card 01’s §1 question is that refusal.

### Slice 2 — Gather a packet from that card only

**POLICY.** Gather reads the source path on the row and no other file. Each fact is a verbatim span of that file. The fact’s source is that path. A later step adds no fact. Card 04. For this row the path is `docs/research/01_how_discovery_works.md`, and the fill is `researched` because that card already holds its sources. Card 08.

**Files.** New [src/ada/memory/blog_packet.py](src/ada/memory/blog_packet.py). `gather_packet` reads the one path. `gate_packet` refuses a span that is not in the file, a missing field, a fill outside `build-log` | `lesson` | `researched`, or a researched row whose packet is empty. The packet is stored on the sidecar.

**Reuse.** Card 04: gather is the only step that may introduce a fact. No `web_fetch`. No cite-library write. No second source file.

**How you know.** A string that does not occur in `docs/research/01_how_discovery_works.md` is refused. Every stored fact cites that path. The wake writes no web receipt and no cite file.

### Slice 3 — Draft `artifacts/{date}/{slug}.md`

**POLICY.** The local file is the frontmatter `blog.ts` requires, plus a body. `title` and `question` are the question on the row. `description` is the first sentence of that question and adds no word the question did not contain. If the question is one sentence, `description` is that sentence. `source` is the named source. `canonical` is `/blog/{slug}`. Audience and site are not keys. `published` and `modified` on this local file may be present; the checkout copy in slice 4 replaces both. Card 08.

**POLICY.** The body is new sentences. It is an account of the packet, and it is not a paste of the card. A table is built by code from packet spans only. A call to action is emitted by code only when the row has a label and a URL. An image line is refused unless a packet span is already a picture path. Card 01 has no picture path, so the card-01 draft has no image. Card 03. Card 08.

**Files.** New [src/ada/memory/blog_slug.py](src/ada/memory/blog_slug.py) implements the slug in §3. New [src/ada/memory/blog_draft.py](src/ada/memory/blog_draft.py). `compose_markdown` builds the frontmatter, the code-built table, and the call to action, and accepts the new sentences as the prose.

**Reuse.** `write_artifact` with `relative_path` set to `{UTC date}/{slug}.md`, `source_cites` omitted, and `campaign_id` set. Omitting `source_cites` keeps `write_artifact` from appending `## Cites`. A set `campaign_id` calls `handshake_after_artifact`. The path jail in `_resolve_under_artifacts` stays as it is.

**How you know.** `artifacts/{YYYY-MM-DD}/{slug}.md` exists. The frontmatter has `title`, `question`, `description`, `published`, `modified`, `fill`, `source`, and `canonical` equal to `/blog/{slug}`. The body is not the source file. Every table cell is a packet span. The file has no image line and no `## Cites`. A row with no call to action yields no call-to-action link.

### Slice 4 — `waiting_on_aryan`, then the confirm copies the file

**POLICY.** After the draft, status is `waiting_on_aryan`. The draft path is `last_receipt`. That path is not ship proof. The campaign is not marked `done`. The public URL and the commit receipt in card 04 wait on the later push confirm. Card 08.

**METAL.** `handshake_after_artifact` sets `waiting_on_aryan` and stores the artifact path as `last_receipt` when `artifact_write` is called with `campaign_id`. `is_draft_artifact_receipt` treats an `artifacts/` path as not an operator ship receipt. `due_campaigns` may list the row. That listing is a read. It is not a yes. A wake that finds `waiting_on_aryan` and has no yes does not write the checkout.

**Files.** `blog_checkout_write` in [src/ada/tools/blog_tools.py](src/ada/tools/blog_tools.py). Its `ToolSpec` uses `side_effect` `confirm` and agent mode. [src/ada/tools/gateway.py](src/ada/tools/gateway.py) dispatches it. `_CONFIRMABLE_TOOLS` in [src/ada/hud/routes_api.py](src/ada/hud/routes_api.py) includes the name. [src/ada/cortex/charter.py](src/ada/cortex/charter.py) gains one sentence: the checkout write is `blog_checkout_write`, it needs confirm, and `artifact_write` does not perform it.

**POLICY.** Without `confirmed=true` the tool returns `needs_confirm` and writes nothing. `POST /api/confirm` re-executes the stashed call. On success the same markdown is written once to `{ADA_PORTFOLIO_CHECKOUT}/content/blog/{slug}.md`. On that write, `published` and `modified` are the UTC calendar date of the confirm, and they are equal. The writer does not use a future date and does not copy an event date or the card’s access date `2026-09-29` out of the packet. Card 04. Card 08. While `content/blog/{slug}.md` exists, the write is refused and the bytes stay as they are.

**Reuse.** `api_confirm`, `confirm_tool`, and `pending_confirms`. No new HUD control.

**How you know.** Before the confirm, `content/blog/{slug}.md` is absent in the checkout and the campaign status is `waiting_on_aryan`. After the confirm, the file is there and matches the `readPostFile` contract, with both dates equal to the confirm’s UTC date. A second confirm while the path exists leaves the bytes unchanged. A tool name absent from `_CONFIRMABLE_TOOLS` still returns `confirm_not_wired`.

### Slice 5 — Delete that file, then write the same slug again

**POLICY.** A delete confirm removes `content/blog/{slug}.md` from the checkout and clears the slug on the sidecar. The question, audience, source, and fill stay. The next draft of that question derives the same slug. Because the checkout path is gone, the next `blog_checkout_write` may create it. This card mints no second filename for the same question. Card 08.

**Files.** `blog_checkout_delete` in the same tool module, with a `ToolSpec` of `side_effect` `confirm` and agent mode, a dispatch line in [src/ada/tools/gateway.py](src/ada/tools/gateway.py), and an entry in `_CONFIRMABLE_TOOLS`.

**Reuse.** The same confirm path as slice 4. The slug jail from §3: `..` and a slash refuse, and the only deleted path is `{checkout}/content/blog/{slug}.md`. `upsert_loop` sets the campaign status back to `active`. The local artifact under `artifacts/` may remain.

**POLICY.** If that UTC day’s `artifacts/{date}/{slug}.md` already exists, the next local draft uses the existing `artifact_write` overwrite, which already requires `confirmed=true`. It does not invent another filename.

**How you know.** After the delete confirm, the checkout file is gone and the slug field on the sidecar is empty. The following draft and confirm create `content/blog/{same-slug}.md` again.

### Slice 6 — Git push, Search Console, other sites, and a JSON writer stay out

**POLICY.** This slice touches no files. Git push is a later confirm. `blog_checkout_write` does not run git. Search Console stays unconnected. [src/ada/analytics/keyword_select.py](src/ada/analytics/keyword_select.py) and [src/ada/analytics/planner.py](src/ada/analytics/planner.py) stay unused. A site other than `github.com/aryanjohari/aryan-portfolio` is refused in slice 1. Nothing in these slices writes JSON, Open Graph tags, or HTML. Nothing edits portfolio `blog.ts`. Nothing adds a route, an image generator, a queue walk, or a CLI for the five fields. Card 08.

**How you know.** The checkout tool does not invoke git. A non-portfolio site never stores. No step writes `page.json`.

## 5. The test

**POLICY.** Ada stores the row with source `docs/research/01_how_discovery_works.md` and fill `researched`, gathers that card, and drafts `artifacts/{date}/{slug}.md`. The operator confirms. The file is `{ADA_PORTFOLIO_CHECKOUT}/content/blog/{slug}.md`. The operator delete-confirms. Ada drafts the same question again and the confirm writes that slug again. No person writes the post. This card does not include one.

**POLICY.** Each slice’s check is a pytest. Tests set `ADA_DATA_ROOT` and use a temporary checkout. They do not touch a live portfolio checkout. The portfolio build and the public HTML URL wait on the later push confirm. Card 04. Card 08.

## 6. In / out

**In.** The six slices. The sidecar for the page fields. The slug function. The two confirm tools and the one charter sentence. The test in §5.

**Out.** Product code in this card. A hand-written post. Git push. Search Console. A second site. A JSON writer. A new HUD control. An edit to `blog.ts` or to `upsert_loop`’s keys.

## 7. Won't-chase

- Putting site, audience, source, question, fill, or the call to action onto `upsert_loop`.
- Using `_slugify` as the blog slug, truncating a long slug, or minting a `-2` filename.
- A fact that is not a verbatim span of the named source. A `web_fetch` during gather. A `## Cites` block.
- An image when the packet has no picture path. A call to action the row does not hold.
- Overwriting `content/blog/{slug}.md` while it exists.
- Marking the campaign `done` from the checkout copy. Treating the `artifacts/` receipt as ship proof.
- Git push, Search Console, another origin, or a JSON writer inside these slices.

## 8. What would prove this wrong

1. `blog.ts` no longer requires the frontmatter in §3, or `canonical` is not `/blog/{slug}`.
2. Cards 07 and 08 require site, audience, and the queue on `open_loops.yaml`, where this card keeps them on the sidecar.
3. `POST /api/confirm` writes `content/blog/{slug}.md` when the operator has not confirmed, or it re-executes a tool that is not in `_CONFIRMABLE_TOOLS`.
4. A second confirm replaces an existing `content/blog/{slug}.md`, or a delete still leaves that slug blocked.
5. `blog_checkout_write` pushes git, writes JSON, or accepts a site other than `github.com/aryanjohari/aryan-portfolio`.

## 9. Source list

All accessed 2026-09-29.

1. Repository `aryanjohari/aryan-portfolio`. `src/lib/blog.ts`. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/lib/blog.ts
2. This repo. "04 — Pipeline steps." `docs/research/04_pipeline_steps.md`
3. This repo. "07 — Campaign." `docs/research/07_campaign.md`
4. This repo. "08 — Blog implement." `docs/research/08_blog_implement.md`
5. This repo. "01 — How discovery works." `docs/research/01_how_discovery_works.md`
6. This repo, this branch. `src/ada/memory/open_loops.py`. `upsert_loop`, `CAMPAIGN_STATUSES`, `handshake_after_artifact`, `is_draft_artifact_receipt`.
7. This repo, this branch. `src/ada/memory/artifacts.py`. `write_artifact` is jailed to `artifacts/`. `_slugify` is not the blog slug.
8. This repo, this branch. `src/ada/hud/routes_api.py`. `api_confirm`, `_CONFIRMABLE_TOOLS`.
9. This repo, this branch. `src/ada/hud/chat_service.py`. `confirm_tool`, `pending_confirms`.
