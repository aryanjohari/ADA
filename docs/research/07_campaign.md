# 07 — Campaign

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established), **METAL** (code this card read: the file, and what the function does). A vendor page that sells a topic cluster would be **MARKETING** and is not a ranking rule. None of the sources below are that.

The page is the one public HTML URL locked in card 01. The refusals are the card-02 rows. The steps are the five in card 04. The console fields, and the decisions they cannot make, stay in card 05. Patch or leave stays in card 06. This card does not restate those pages.

## 1. Question

What inputs does an organ need to open one campaign for one site, what does that campaign contain, and which of its steps may run unattended?

## 2. Short answer

**POLICY.** One campaign belongs to one site. A site is one origin. The first site is the portfolio, the repo `github.com/aryanjohari/aryan-portfolio`. A later site is another record with the same fields. This card does not design that site.

**POLICY.** The inputs that open the campaign are the site and one audience sentence. The inputs that name the next page are that sentence, a source, a question, and a fill. The question becomes the title. One campaign serves the one HTML URL. It is not a campaign for SEO, a second for the answer box, and a third for a generated citation.

**POLICY.** The record holds the site, the audience, a queue, the links already published on that site, and `next_wake_at`. One wake reads that record, advances one stage of one queue item, writes the record, and sleeps.

**POLICY.** Unattended, the organ may read the campaign and draft from a packet gather already wrote. The first publish of a URL waits until a person says yes. A later patch of that same URL waits, unless the new fact is already in the gather packet and the gate passes.

## 3. Inputs

One row is one input. The person who opens the campaign supplies each of them. On the portfolio, that person is the operator. Gather may write a fact only from the source already on the row, and only under card 04.

| Name | Who supplies it | What it may not be |
| --- | --- | --- |
| Site | That person. The first value is the portfolio repo `github.com/aryanjohari/aryan-portfolio`, one origin. Card 04 measured the public host `https://aryan-portfolio-one-kappa.vercel.app`. | A second origin. A keyword. Another person's product. |
| Audience | That person, as one sentence about who the page is for. | A traffic target. A click count or an impression count. A Search Console query. A keyword list. |
| Source | That person. For the portfolio's first page, shipped work. Gather writes each fact with the operator receipt. That fill may carry no external citation. | A Search Console query. A keyword. A fact with no receipt and no source. |
| Question | That person. It becomes the `<title>` of the one URL. | A keyword list. A Search Console query. A second question for a URL that already has one. |
| Fill | That person: a build log, a lesson, or a researched article. The first subject on the portfolio is a build log of shipped work. | A separate page for SEO, for the answer box, or for a citation. A researched article whose sources are not already in the packet. |

**POLICY.** Choosing the subject stays outside the five card-04 steps. These five inputs are that choice, written down before a wake runs. A wake does not supply a missing row.

**UNKNOWN.** The path of the URL on the origin. Card 04 left it unknown. The URL field on a queue item stays empty until that path is known. This card does not add a route.

## 4. The campaign record

**POLICY.** The fields are these, and no others.

| Field | What it holds |
| --- | --- |
| Site | One origin. The campaign publishes only on that origin. A site may hold more than one campaign. A campaign does not publish onto a second origin. |
| Audience | The one sentence from §3. |
| Queue | One item per page. Each item holds a source, a question, a fill, a URL, and a status. |
| Links already published | The URLs this campaign has already published on that site. Internal links are written only between those URLs, plus one link from a page the site already serves. The anchor text is the question. |
| `next_wake_at` | When the next wake may read this campaign. After the one step, the wake writes the next time. Between wakes the organ is idle. |

**Superseded 2026-10-01.** The queue item is now fact, question, source, and url, capped at 12. Card 11.

**POLICY.** The status on a queue item is the campaign STATUS this branch already stores: `active`, `blocked`, `waiting_on_aryan`, `paused`, `done`, `failed`. `waiting_on_aryan` means a person has to answer before the next public step.

**POLICY.** The stages of one item, once the §3 inputs are present, are gather, then gate, then draft, then deploy. Those are the card-04 steps. Choosing the subject is not a stage. One wake advances one stage of one item, writes that item's status and `next_wake_at`, and sleeps. A wake does not walk the queue. The stage a wake may run with no person present is draft, and only from a packet gather already wrote.

**POLICY.** Gather is the only stage that may add a fact. Draft uses the passed packet and adds none. Deploy, when it runs, is one commit on that site's repo and one public HTML URL on that origin. For the portfolio the repo is `github.com/aryanjohari/aryan-portfolio`.

**POLICY.** A link in a draft points at a URL already in "links already published," or it is the one link from a page the site already serves. The anchor text is the question for the target page. The holder of that inbound link on the portfolio stays **UNKNOWN**, as card 06 left it. This card does not write the href while that holder and the path are unknown.

**EVIDENCE.** Google, [Link best practices for Google](https://developers.google.com/search/docs/crawling-indexing/links-crawlable) (page last updated 2025-12-10 UTC). Google uses links to find pages. A link Google can crawl is an `<a>` element with an `href`. Anchor text is the visible text of that link. The page says good anchor text is descriptive, reasonably concise, and relevant to the page it is on and the page it links to. The same page says every page you care about should have a link from at least one other page on your site. It says there is no ideal number of links on a page. The page does not define an object called a campaign, and it does not define a topic cluster.

**POLICY.** "Campaign" in this card is the disk record above. It is not a ranking object. A topic cluster, as an agency page uses that phrase, is **MARKETING**. It is not a rule on the links page.

**METAL.** `src/ada/memory/open_loops.py` on this branch. `CAMPAIGN_STATUSES` is `active`, `blocked`, `waiting_on_aryan`, `paused`, `done`, `failed`. `STAGE_STATES` is `pending`, `active`, `done`, `skipped`. `upsert_loop` rejects `next_wake_at` on a todo and returns the error that the field is campaign-only. `due_campaigns` returns a campaign when its status is `blocked` or `waiting_on_aryan`, when `next_wake_at` is at or before now, or when `cadence` is `daily` and the last progress is at least 48 hours old. `campaign_check` lists those rows and calls no model. The file stores `stages`, `current_stage`, and `next_wake_at`. It does not store site, audience, a queue, or links already published. This card does not add those keys to the file.

**METAL.** `docs/modules/M06_CAMPAIGNS_LONG_HORIZON.md`. A campaign is durable STATUS on disk. A wake advances one step, or asks the person, writes STATUS, and sleeps. A stage that touches the world waits for a confirm. The module refuses an always-on worker that advances a campaign unsupervised.

**HUNCH.** The 48-hour stale mark in `due_campaigns` is a reason to read a record, in that function. It is not a reason to publish. This card does not measure that reading against a live site.

**FEASIBLE.** The portfolio origin can hold the one public URL a deploy writes. The campaign record is disk state for that origin. This card does not check that a campaign row exists today.

**UNKNOWN.** Which page the site already serves will hold the inbound link. Card 06. Click and impression thresholds. Card 05. This card adds neither a holder nor a threshold.

### What one wake reads and writes

**POLICY.** A wake reads one campaign whose `next_wake_at` has passed: the site, the audience, one queue item, the links already published, and that item's status. When that item already has a passed packet, the wake may write the draft, then the item's status and the next `next_wake_at`. Then it is idle.

**POLICY.** When the item has no passed packet, the wake does not draft and does not deploy. Gather remains the only stage that may add a fact, and only from the source on the item. This card does not mark gather as unattended. The item stays `waiting_on_aryan` until that packet exists. A wake with an empty queue writes no item. It writes the next `next_wake_at` and sleeps. The next row waits on a person.

## 5. What stays attended

### The first publish

**POLICY.** The first publish of a URL waits until a person says yes. The status is `waiting_on_aryan`. A draft may already exist. The yes is the confirm before a public side effect. After the yes, deploy is one commit on that site's repo and one public URL on that origin. The URL is then recorded under links already published.

### A patch

**POLICY.** A later patch of that same URL waits, unless the new fact is already in the gather packet and the gate passes. When both are true, the patch is the one step of that wake: the same gate, draft, and deploy, on the same URL, one new commit, the same public URL. When either is false, the status is `waiting_on_aryan` and the wake does not deploy. A card-05 field does not satisfy either condition. If the gate refuses, there is no commit, and the live page stays.

### Empty queue

**POLICY.** An empty queue, or a queue with no question a person supplied, stays attended. The wake does not invent a site, an audience sentence, a source, a question, or a fill. The next page appears when that person writes the next row. Card 04 left choosing the subject outside the five steps. Card 06: the weekly list does not choose a subject, and a query does not choose one.

## 6. What this organ refuses

**METAL.** On git branch `main`, `src/ada/analytics/keyword_select.py` function `select_keyword_cluster` sets `keyword_cluster` to the query string of the first row from `list_gsc_top_queries_safe`. On that same branch, `src/ada/analytics/planner.py` functions `ctr_gap` and `ranking_gap` score a row by the gap to 0.12 CTR and the gap to position 5, and `opportunity_score` multiplies impressions by those two gaps. For a content-gap row, `build_gsc_campaign_plan_payload` sets `suggested_action` to `create or split dedicated landing page for this query cluster`, and `proposed_pages` is those query strings.

**POLICY.** This organ refuses that cluster, that score, and that action. The lines below say which lock each refusal enforces.

**POLICY.** A query becoming a page. The top query is not the question, and `proposed_pages` is not a queue. Card 06: a query does not become a URL. Patch the same URL or leave it. Card 04: choosing the subject is outside the five steps, and deploy writes one URL.

**POLICY.** A click target becoming a pass. The 12% CTR and the position-5 gap are the arithmetic in `planner.py` on `main`. They are not a number Google publishes. Card 05: no click count and no impression count is a pass, a console field cannot pass or fail a page, and a console field cannot prove a patch caused a change. Those thresholds stay **UNKNOWN**. "More people coming to the site" is the hope. It is not a field on this record and it is not a pass.

**POLICY.** Doorway pages, a pile of near-duplicate questions, scaled pages, keyword stuffing, and a page whose primary purpose is manipulating rankings. Card 02. One wake, one stage, one item. This organ does not run a writer that emits many pages.

**POLICY.** A word count or a link count as a gate. Card 02 states no such cutoff. The links page states no ideal number of links. This card does not add one.

**POLICY.** A fact that gather did not write. Card 04. A console number is not a fact. Card 06.

**POLICY.** A deploy that is not one commit on that site's repo and one public URL on that origin. Card 04. No second origin. No `/blog`.

**POLICY.** A researched article before its sources are in the packet. Card 04. Card 06: the first subject on the portfolio is a build log of shipped work, and a researched page needs those sources already.

**POLICY.** A second URL for the same question, including a second campaign whose job is only the answer box or only the citation. Card 06. Card 04: one URL.

**POLICY.** A Search Console field choosing the next subject, or standing in for the audience, the source, the question, or the fill. Card 05. Card 06.

## 7. In / out

**In.** The five inputs. The record: site, audience, queue, links already published, `next_wake_at`. What one wake reads and writes. Which steps stay attended: the first publish, a patch that lacks a gathered fact or a passed gate, and an empty queue. The unattended pair: read, and draft. The refusals of the `main` planner behavior.

**Out.** Code. A new route, including `/blog`. Connecting Search Console. Choosing the path. Naming the inbound-link holder. Writing the build log. Another person's product. Card 8.

## 8. Won't-chase

- Three campaigns for one page, split by SEO, the answer box, and a citation.
- A topic cluster from an agency page (**MARKETING**).
- The 12% CTR and the position-5 gap as a target. Card 05.
- A click count or an impression count. Both stay **UNKNOWN**.
- A daemon that writes many pages. One stage, then sleep.
- A word count or a link count.
- `/blog`, a second origin, or a second URL for the same question.
- Connecting Search Console, or a results scrape.

## 9. What would prove this wrong

1. The links page, or a Google page cards 01 through 05 cite, defines a campaign as the object Google ranks, or it withdraws the sentence that every page you care about should have a link from at least one other page on the site.
2. Google states that a keyword list or a Search Console query is an input that creates a page.
3. Google publishes 12% CTR or position 5 as a pass, where card 05 says no such pass is published.
4. Card 04 lets a step other than gather add a fact, or card 06 treats a new URL for the same question as the maintenance of the first URL.
5. A first publish of a URL on this origin is allowed with no person saying yes, and that publish is still the rule this series wants.
6. The first subject on the portfolio is not a build log of shipped work, or a researched page is allowed before its sources are in the packet.
7. `upsert_loop` on this branch accepts `next_wake_at` on a todo, where this card says the field is campaign-only.

## 10. Source list

All accessed 2026-09-29.

1. Google. "Link best practices for Google." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/crawling-indexing/links-crawlable
2. This repo. "01 — How discovery works." `docs/research/01_how_discovery_works.md`
3. This repo. "02 — Google page rules." `docs/research/02_google_page_rules.md`
4. This repo. "04 — Pipeline steps." `docs/research/04_pipeline_steps.md`
5. This repo. "05 — Search Console." `docs/research/05_search_console.md`
6. This repo. "06 — Maintain loop." `docs/research/06_maintain_loop.md`
7. This repo. "M06 — Campaigns / Long-Horizon Continuity." `docs/modules/M06_CAMPAIGNS_LONG_HORIZON.md`
8. This repo, this branch. `src/ada/memory/open_loops.py`. `upsert_loop` rejects `next_wake_at` on a todo. `due_campaigns` and `campaign_check` list due campaigns and call no model.
9. This repo, git branch `main`. `src/ada/analytics/keyword_select.py`. `select_keyword_cluster` takes the first top query.
10. This repo, git branch `main`. `src/ada/analytics/planner.py`. `ctr_gap`, `ranking_gap`, and `opportunity_score` score against 0.12 CTR and position 5. A content-gap row proposes a page for the query.
