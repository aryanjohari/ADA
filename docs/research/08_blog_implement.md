# 08 — Blog implement

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established), **METAL** (code this card read: the file, and what the function does). A vendor page selling a content pipeline would be **MARKETING** and is not a ranking rule. None of the sources below are that.

The steps are the five in card 04. The inputs, the one wake, and the first yes are card 07. Cards 04 and 07 left the path on the origin unknown and refused to add a route. This card does not add one. It writes the one markdown file the portfolio already reads.

## 1. Question

How does one confirmed input become one `content/blog/{slug}.md` that the portfolio can build?

## 2. Short answer

**POLICY.** Input, draft, yes, file. The person types the five fields. Gather and the gate run on the named source only. Draft writes one local markdown file and the status becomes `waiting_on_aryan`. The yes is the existing HUD confirm. That confirm writes one file into a checkout of `aryanjohari/aryan-portfolio` at `content/blog/{slug}.md`. Git push is a second confirm.

## 3. Input

**POLICY.** This slice uses the HUD. The person types site, audience, source, question, and fill in the existing composer, the `textarea` `chat-input` in `src/ada/hud/templates/index.html`. That message is posted to `POST /api/chat`. This slice adds no form and no new control. The CLI is later. `ada campaigns status` and `ada campaigns check` read disk and call no model. They do not take these five fields.

**METAL.** `src/ada/hud/templates/index.html`. The composer is `textarea#chat-input`. `src/ada/hud/static/js/api.js`. `openChatStream` posts that message to `/api/chat`. `src/ada/hud/routes_api.py`. The router prefix is `/api`, and `api_chat` handles `POST /chat`.

**POLICY.** The yes this slice uses is `POST /api/confirm`, handler `api_confirm`. It re-executes one gateway tool with `confirmed=true` only after the operator confirms. The existing confirm card calls `postConfirm`, which posts that route. This card does not add a button.

**METAL.** `src/ada/hud/routes_api.py`. `api_confirm` rejects a tool that is not in `_CONFIRMABLE_TOOLS` with `confirm_not_wired` and does not report success. `src/ada/hud/chat_service.py`. `confirm_tool` binds the stashed args when `pending_id` is set, sets `confirmed=true`, and calls `gateway.execute`. `src/ada/hud/static/js/api.js`. `postConfirm` posts `{ tool, args, pending_id }` to `/api/confirm`.

**POLICY.** The five fields are the ones card 07 named. Site is `github.com/aryanjohari/aryan-portfolio`. Any other site is refused. Audience is one sentence and is not written into the file. Source is the name the person typed. Question becomes the title. Fill is `build-log`, `lesson`, or `researched`. A researched fill is refused unless its sources are already in the packet. A wake does not supply a missing field.

**METAL.** `src/ada/memory/open_loops.py`. `CAMPAIGN_STATUSES` includes `waiting_on_aryan`. `upsert_loop` rejects `next_wake_at` on a todo. The file stores `stages`, `current_stage`, and `next_wake_at`. It does not store site, audience, a queue, or links already published. This card does not add those keys.

**UNKNOWN.** Which columns hold the five fields between the composer message and the wake. The durable page is the markdown file.

## 4. File

**METAL.** `aryanjohari/aryan-portfolio` `src/lib/blog.ts`, read 2026-09-29. `readPostFile` takes the slug from the filename without `.md`, refuses an empty slug, `.`, and `..`, and requires this frontmatter: `title`, `question`, `description`, `published`, `modified`, `fill` (`build-log`, `lesson`, or `researched`), `source`, `canonical`. `canonical` must equal `/blog/{slug}`. Dates must be real `YYYY-MM-DD` values. `source` is kept and not rendered. The body is the markdown after the frontmatter. `getBlogPosts` reads `content/blog/*.md` and skips names that start with `.`. A file that breaks the contract fails the build. A missing directory is an empty blog.

**POLICY.** The writer emits this file and nothing else. No HTML, no JSON, no Open Graph tags. The portfolio build is what turns the file into the page.

```yaml
---
title: "<the question>"
question: "<the question>"
description: "<one sentence from the question>"
published: YYYY-MM-DD
modified: YYYY-MM-DD
fill: build-log
source: "<the named source>"
canonical: /blog/{slug}
---
```

**POLICY.** `title` and `question` are the same string: the question the person typed. `description` is one sentence taken from that question. If the question is one sentence, `description` is that sentence. If it contains more than one sentence, `description` is the first sentence and no words after it. It adds no word the question did not contain.

**POLICY.** On the file written into the checkout, `published` and `modified` are the UTC calendar date of the confirm. They are equal on that first write. The writer does not use a future date and does not copy an event date out of the packet. Card 04.

**POLICY.** `source` is the named source the person typed. For a build log that string is the shipped work. It is not an external citation, and card 04 does not require one.

**POLICY.** The slug is derived from the question only. Lowercase it. Replace each run of characters outside `a-z` and `0-9` with one hyphen. Strip hyphens at the ends. The result is one path segment: non-empty, not `.` or `..`, no slash, no leading dot. An empty result is a refusal. This slice does not substitute another word. A slug longer than 80 characters is a refusal. That cap is this slice's gate. `blog.ts` states no length. The filename is `{slug}.md`. `canonical` is `/blog/{slug}`.

**HUNCH.** The 80-character cap is taken from the artifact slug limit so two questions are not folded into one filename by truncation. It is not a rule in `blog.ts`.

**POLICY.** Audience and site are not keys in the file.

**UNKNOWN.** Whether the portfolio paints `title` as the visible heading. This writer does not add a heading to find out.

## Open, now locked

**POLICY.** New sentences are allowed. New facts are not. Every fact in the body is already in the gather packet. The page is an account of the source, not a paste of it.

**POLICY.** A table may be arranged from facts already in the packet. It need not appear as a table in the source.

**POLICY.** Call to action is an input on the campaign row: a label and a URL the person typed. The writer may use it and may not invent one. If the row has none, the page has none.

**POLICY.** An image stays optional. This slice does not generate one.

**POLICY.** While `content/blog/{slug}.md` exists, refuse to overwrite it. After that file is deleted, the same slug may be written again.

**POLICY.** The first implementation test source is `docs/research/01_how_discovery_works.md`, fill `researched`, because that card already holds its sources. Ada writes the file. A person does not.

## 5. Steps

**POLICY.** One wake advances one stage of this one item, writes `next_wake_at`, and sleeps. It writes at most one file. It does not walk a queue of posts and it does not open a second question. Card 07.

1. Gather reads the named source only and writes the packet. A later step adds no fact. A build log's facts carry the operator receipt for that shipped work. A researched fill whose sources are not already in the packet is not gathered into a page.
2. Gate passes that packet unchanged or refuses it. The refusals are the card-04 lines, plus a missing field, a fill outside `build-log` | `lesson` | `researched`, a researched packet with no sources, an unusable slug, and a slug that already names a file.
3. Draft writes one local file at `artifacts/{YYYY-MM-DD}/{slug}.md`. That file is the frontmatter in §4 and a body under Open, now locked. `source_cites` is not passed, so the writer does not append a `## Cites` section.
4. Status becomes `waiting_on_aryan`. The draft path is the receipt on the campaign. It is not ship proof. The wake then sleeps.
5. The yes is `POST /api/confirm`. It re-executes one tool in `_CONFIRMABLE_TOOLS` with `confirmed=true`. A tool that is not in that set returns `confirm_not_wired` and writes nothing.
6. After that confirm succeeds, the same markdown is written once, into a checkout of `aryanjohari/aryan-portfolio`, at `content/blog/{slug}.md`. While that path exists, the write is refused. After that file is deleted, the same slug may be written again.
7. Git push is a second confirm. It is not part of the draft and not part of this yes.

**METAL.** `src/ada/memory/artifacts.py`. `write_artifact` writes only under `artifacts/`. With `relative_path` omitted, the name comes from `_slugify`, which falls back to `note` and keeps `.` and `_`. This slice passes `relative_path` so the filename is the blog slug. When `source_cites` is non-empty and the body has no cite block, `write_artifact` appends `## Cites`. This slice does not pass `source_cites`. `src/ada/memory/open_loops.py`. `handshake_after_artifact` sets `waiting_on_aryan` and stores the artifact path as `last_receipt` when `artifact_write` is called with `campaign_id`. `is_draft_artifact_receipt` treats an `artifacts/` path as not an operator ship receipt. `due_campaigns` lists a row in `waiting_on_aryan` as due. That listing is a read. It is not a yes.

**METAL.** `src/ada/hud/routes_api.py`. `_CONFIRMABLE_TOOLS` includes `artifact_write` and `memory_open_loops_upsert`. It does not include a tool that writes `content/blog/` or a tool that pushes git. `artifact_write` cannot be the checkout write: `write_artifact` refuses a path that escapes `artifacts/`.

**POLICY.** A wake that finds `waiting_on_aryan` and has no yes does not write the checkout. The 48-hour stale mark in `due_campaigns` is not a yes. Card 07.

**FEASIBLE.** The portfolio repo can hold `content/blog/{slug}.md`, because `blog.ts` already reads that directory. This card does not check that a checkout exists on this machine, and it does not name a checkout path.

## 6. What this slice does not do

**POLICY.** No image generator. No Search Console. No second site. No JSON writer. No Open Graph tags. No HTML writer. No new route, in this repo or in the portfolio. No automatic push. No walk of a queue. No second file for a second question in the same wake. No CLI for these five fields. No new form. The public HTML URL and the commit receipt in card 04 wait on the later push confirm. This slice's file is the checkout file after the first yes.

## 7. Acceptance

**POLICY.** One file for the named source, with the frontmatter in §4, passes `readPostFile` in `blog.ts`. Every fact in the body is already in the gather packet. The first implementation test is `docs/research/01_how_discovery_works.md` with fill `researched`. Ada writes that file.

**POLICY.** If the operator does not confirm, `content/blog/{slug}.md` is not written in the portfolio checkout. The local draft under `artifacts/` may exist. The campaign stays `waiting_on_aryan`.

**POLICY.** A second question does not overwrite the first slug. While `content/blog/{slug}.md` exists, that slug is refused. After that file is deleted, the same slug may be written again. This slice mints no `-2` suffix and no second filename for the same question.

## 8. Won't-chase

- An image generator. A fact that is not already in the gather packet. A call to action the person did not type on the campaign row.
- Search Console, a click count, or an impression count. Card 05.
- A second site, a second origin, or a JSON writer.
- Open Graph tags, HTML written by Ada, or a route this slice adds.
- An automatic git push, or treating push as part of the draft.
- A wake that writes many posts. One wake, one file.
- A word count or a link count. Card 04.
- A five-field form, or the CLI, for this slice.
- `Article` markup. Card 03.
- The `note` fallback in `_slugify` as a blog slug.

## 9. What would prove this wrong

1. `blog.ts` no longer requires the frontmatter in §4, or `canonical` is not `/blog/{slug}`, or the slug is not the filename without `.md`.
2. A file that matches §4 fails the portfolio build, or that build requires an image, a table, JSON, or Open Graph tags.
3. `POST /api/confirm` writes `content/blog/{slug}.md` when the operator has not confirmed, or it re-executes a tool that is not in `_CONFIRMABLE_TOOLS`.
4. A missing yes still leaves that file in the portfolio checkout.
5. A second question replaces the first slug's file.
6. `waiting_on_aryan` is not a campaign status, or `upsert_loop` accepts `next_wake_at` on a todo.
7. A researched file is accepted when the packet has no sources, or a step after gather adds a fact. Card 04. Card 07.

## 10. Source list

All accessed 2026-09-29.

1. Repository `aryanjohari/aryan-portfolio`. `src/lib/blog.ts`. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/lib/blog.ts
2. This repo. "04 — Pipeline steps." `docs/research/04_pipeline_steps.md`
3. This repo. "07 — Campaign." `docs/research/07_campaign.md`
4. This repo, this branch. `src/ada/memory/open_loops.py`. `CAMPAIGN_STATUSES`, `upsert_loop`, `handshake_after_artifact`, `due_campaigns`.
5. This repo, this branch. `src/ada/hud/routes_api.py`. `api_confirm`, `_CONFIRMABLE_TOOLS`.
6. This repo, this branch. `src/ada/memory/artifacts.py`. `write_artifact` is jailed to `artifacts/`.
7. This repo, this branch. `src/ada/hud/static/js/api.js`. `openChatStream`, `postConfirm`.
