# 06 — Maintain loop

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established). A vendor page about a refresh calendar would be **MARKETING** and is not used as a ranking rule. None of the sources below are that.

The page is one card-03 page already live on the portfolio origin. The receipt is the card-04 commit and the one public URL. The path stays **UNKNOWN**. A later read uses only the card-05 fields, and the decisions those fields cannot make stay in force. This card does not restate the blocks, the spam rows, the five steps, or the report definitions.

## 1. Question

After one card-03 page is live, how does a later run decide to patch that same URL or leave it, where does the next subject come from, and which existing page supplies the inbound link?

## 2. Short answer

**POLICY.** Patch or leave, in this order. The first match is the run.

1. A second URL for the same question is a duplicate. Leave the live URL. Do not open the second URL.
2. Leave when gather has no new fact for this URL, or the new fact would not substantially change the page. The modified date stays.
3. Patch when a new fact for this same URL would substantially change the page. Gather writes that fact. Then the same gate, draft, and deploy. The modified date changes. The receipt is a new commit on `aryanjohari/aryan-portfolio` and the same public URL.

A card-05 field does not add a step above these three and does not flip the mark. This card locks no click count, no impression count, and no average position as a target.

## 3. The loop

**POLICY.** A new fact is one gather can write under card 04: shipped work with an operator receipt, or a source for a claim that is not the operator's own work when that fill allows the source. Gather is the only step that may add a fact. A console number is not a fact.

**POLICY.** "Substantially" is the card-03 test for the modified date. This card adds no size cutoff for it.

**POLICY.** The weekly list is our schedule for this loop. It is not a cadence Google states. Card 05's week is the wait for data on a newly created site or a newly added property. Card 05's 2–3 days are how long collected numbers normally take to become visible. Neither is a count of days from this URL's publish until the first impression, click, or query. That count stays **UNKNOWN**.

| Stage | What it reads | What it writes | What it must not do |
| --- | --- | --- | --- |
| wait | The deploy receipt: the commit and the one public URL. The two card-05 lags, only as reasons a later read can be empty. | Nothing. No mark. | Invent a number of days from this publish until the first impression, click, or query. Treat our weekly list, the card-05 week, or the 2–3 days as that number. Connect a property. Send a query to Google. |
| read | Only the card-05 fields for this URL, and only when a property contains it. Web-search Performance on the Pages row or under a URL filter: clicks, impressions, CTR, and average position. Under that filter: query, country, device, and date. Search appearance for that page. Indexing status from URL Inspection. Generative-AI impressions, and the country, device, and date of those impressions. | That reading. An empty field keeps the card-05 reason that applies. A dash stays a dash. If the property connection is **UNKNOWN**, a note that no number was read. | Use any other report. Treat empty as a pass or a fail. Treat "URL is on Google" as proof the URL is showing. Treat a URL missing from the Page indexing sample as proof it is absent. Treat a dash, or a zero written over a dash, as position zero. Read an unfiltered property chart, or an unfiltered query, country, device, or date row, as this URL's number. Read clicks, CTR, average position, or queries from the generative-AI report. Connect a property. Send automated queries to Google, including a results scrape used to check rank. Choose the path. Add `/blog`. Mark patch or leave. |
| decide | The reading. The facts already on this URL. Whether gather can write a new fact for this same URL. | One mark, patch or leave, in the §2 order. | Let a card-05 field change the mark. Treat a low CTR as a cutoff. Card 05 calls that a prompt to look at the title and the query. Open a second URL. Invent a fact. Choose a subject. Choose the path. |
| patch or leave | The mark. On a patch, the new gather packet. | On a patch: the same gate, draft, and deploy, on the same URL. A new receipt, the commit and that same URL, only if the gate passes. The modified date changes only when the page substantially changes. On a leave: no commit. If the gate refuses, no commit, and the live page stays. | Add a fact gather did not write. Bump the modified date when the page has not substantially changed. Add `/blog` or a second URL. Publish through an S3 `page.json`, a Pi organ, or a second site. Send automated queries to Google. |
| rollup | The live URLs, and whether this run wrote a new receipt for each. | A weekly list. Each live URL is marked patch or leave. Patch is recorded only when the new receipt for that same URL was written. | Publish a page. Add a URL. Choose a subject. Turn a query into a page. Act as a publisher or a topic farm. State the week as Google's rule. |

## 4. Where the next subject comes from

**POLICY.** The first subject is a build log. Its facts are work the operator already shipped. Gather writes each fact with the operator receipt for that work. That fill may carry no external citation. This card names the subject and does not write the page.

**POLICY.** A later subject stays inside that rule until a researched article has sources. Until then the subject is shipped work: another build log, or a lesson whose facts of the operator's own work carry operator receipts. A claim that is not the operator's own work is written only with the source it came from. A researched article is that fill only when those sources are in the packet. Card 04. The path of any such page stays **UNKNOWN**. This card does not add a route.

**POLICY.** A later subject is a different question. The same question stays on the live URL. §2.

**POLICY.** The weekly list does not choose a subject. A query, a click, or an impression does not choose a subject. Choosing the subject stays outside the five card-04 steps. This card names the source of the subject. It does not add a publish step.

## 5. The inbound link

**UNKNOWN.** Which existing page holds the inbound link. The files below show the HTML routes the repo already has. They do not name one of them as the page that links to the value page. The value page's path is **UNKNOWN**, so this card cannot point the href at a path.

**FEASIBLE.** Repository `aryanjohari/aryan-portfolio`, README, section "Current phase", https://github.com/aryanjohari/aryan-portfolio/blob/main/README.md, accessed 2026-09-29. The route split named there is `/` (guide home) and `/workshop` (project table). The same README says the nav and the about page link to `/resume.pdf`. That file is not an HTML page. This card does not use it as the holder.

**FEASIBLE.** Repository `aryanjohari/aryan-portfolio`, "Ship checklist", https://github.com/aryanjohari/aryan-portfolio/blob/main/docs/ship-checklist.md, accessed 2026-09-29. The smoke table names `/`, `/projects`, `/projects/background-studio`, `/projects/ada`, and `/about`. Under "Explicitly deferred (v2)" it lists "ADA blogs". This card does not add `/blog`.

**FEASIBLE.** The `main` tree of that repo, read 2026-09-29, contains these route files:

| Route | Route file |
| --- | --- |
| `/` | `src/app/(site)/page.tsx` |
| `/about` | `src/app/(site)/about/page.tsx` |
| `/projects` | `src/app/(site)/projects/page.tsx` |
| `/workshop` | `src/app/(site)/workshop/page.tsx` |
| `/projects/[slug]` | `src/app/projects/[slug]/page.tsx` |

The home route file says the page body is empty, the home stage lives in VoidChrome, and a deep link to `/` still resolves. The ship checklist still smokes `/`. This card did not read an anchor out of that file.

**POLICY.** The holder, once known, has to be one of those HTML routes, already served, and not the value page. The inbound link is one crawlable link on that page. The anchor text says what the value page is. The target is the value page's one URL. Card 03, internal link. One link. Card 02 left link count **UNKNOWN**. This card does not add the link while the holder and the path are **UNKNOWN**.

## 6. In / out

**In.** The order that patches one live URL or leaves it. The five stages. The first subject, a build log of shipped work, and the rule for a later subject. The inbound link: **UNKNOWN**, plus the condition on a page the repo already serves.

**Out.** Connecting a property. Calling the Search Console API. Code. A new route, including `/blog`. Choosing the path. Writing the build log. A research method. Crawl, snippet, and citation rules (card 01). Spam refusals (card 02). Block definitions (card 03). The five deploy steps, restated (card 04). Report definitions (card 05).

## 7. Won't-chase

- A click count, an impression count, or an average position that means patch or leave. Card 05 publishes no such pass. "Low" and "enough" stay **UNKNOWN**.
- A number of days from this URL's publish until the first impression, click, or query. Card 05 left that lag **UNKNOWN**.
- Our weekly list stated as Google's rule, or as the card-05 week.
- A second URL for the same question.
- A subject taken from a query row.
- A modified date moved so the page looks fresh when it has not substantially changed. Card 03.
- `/blog`, a new route, or a chosen path.
- Connecting Search Console, request indexing, or a results scrape.
- The first build log, written out.
- Vendor refresh calendars (**MARKETING**).

## 8. What would prove this wrong

1. Card 03 or card 04 calls a second URL for the same question the maintenance of the first URL.
2. A card-05 field is sufficient to patch or to leave, or Google publishes a click count, an impression count, or a rank and says that number means the page passed.
3. Google states a number of days from the publish of one URL until the first impression, click, or query, where card 05 marks that lag **UNKNOWN**.
4. The README, the ship checklist, or the route files name one existing HTML page as the page that holds this value page's inbound link, where this card marks that page **UNKNOWN**.
5. The first subject is not a build log of work the operator already shipped, or a researched article is allowed before its sources are in the gather packet.
6. The modified date must change when the page has not substantially changed.
7. The weekly list adds a URL or chooses a subject.
8. A patch may add a fact that gather did not write.

## 9. Source list

All accessed 2026-09-29. The Google pages for dates, links, and Search Console stay in cards 03 and 05. This card adds the portfolio routes it verified.

1. Repository `aryanjohari/aryan-portfolio`. "README", section "Current phase." https://github.com/aryanjohari/aryan-portfolio/blob/main/README.md
2. Repository `aryanjohari/aryan-portfolio`. "Ship checklist." https://github.com/aryanjohari/aryan-portfolio/blob/main/docs/ship-checklist.md
3. Repository `aryanjohari/aryan-portfolio`. Home route. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/app/(site)/page.tsx
4. Repository `aryanjohari/aryan-portfolio`. About route. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/app/(site)/about/page.tsx
5. Repository `aryanjohari/aryan-portfolio`. Projects route. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/app/(site)/projects/page.tsx
6. Repository `aryanjohari/aryan-portfolio`. Workshop route. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/app/(site)/workshop/page.tsx
7. Repository `aryanjohari/aryan-portfolio`. Project slug route. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/app/projects/%5Bslug%5D/page.tsx
8. This repo. "03 — Page blocks." `docs/research/03_page_blocks.md`
9. This repo. "04 — Pipeline steps." `docs/research/04_pipeline_steps.md`
10. This repo. "05 — Search Console." `docs/research/05_search_console.md`
