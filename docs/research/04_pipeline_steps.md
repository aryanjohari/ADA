# 04 — Pipeline steps

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established). A vendor page selling a content pipeline would be **MARKETING** and is not used as a ranking rule. None of the sources below are that.

The page is the one card-03 page on the portfolio origin. The refusals are the card-02 rows and the card-03 blocks this card points at. This card does not restate how a URL is crawled, quoted, or cited, and it does not restate the spam behaviors or the block definitions.

## 1. Question

Which steps turn facts into one card-03 page on the portfolio origin, what does each step own, and what must a later step never invent?

## 2. Short answer

**POLICY:** Five steps, in this order. A fact exists only if gather wrote it. Gate, draft, and deploy add none.

1. Choose the fill and the one URL — one of the three card-03 fills, and one URL on the existing portfolio origin.
2. Gather facts or sources — the packet: every fact the page may say, each with a source or an operator receipt.
3. Gate — pass that packet through unchanged, or refuse it.
4. Draft — the card-03 page, using only the passed packet.
5. Deploy — one commit on `aryanjohari/aryan-portfolio`; the receipt is that commit and one public HTML URL on the existing origin.

## 3. Step table

| Step | What it reads | What it writes | What it must not do |
| --- | --- | --- | --- |
| Choose the fill and the one URL | The three fills card 03 named (build log, lesson, researched article) and the existing portfolio origin | One fill and one URL on that origin | Invent a fact. Choose a topic. Add `/blog`, a second URL, or a second origin. |
| Gather facts or sources | Shipped work, a source, or both, as the emission rules below state for that fill | The packet. Each fact has a source or an operator receipt | Invent a fact that is neither shipped work nor a source. Write the HTML. Publish. Choose the topic. Write a research method. |
| Gate | The packet, the fill, and the URL | The same packet, unchanged, or a refusal | Invent, drop, or rewrite a fact. Add a source or a receipt. Refuse the packet for length, link count, Core Web Vitals, E-E-A-T, or because automation was used. |
| Draft | The passed packet and the chosen URL | One card-03 HTML page | Invent a fact, a source, a receipt, a list, a table, or an image the packet does not support. Add `/blog`. |
| Deploy | The drafted page | A commit on `aryanjohari/aryan-portfolio` that contains that page. Vercel builds that repo. The public URL is on the existing origin | Invent a fact. Publish through an S3 `page.json`, a Pi organ, or a second site. Send automated queries to Google. |

**POLICY.** Gather is the only step that may introduce a fact. A later step that invents a fact gather did not write fails this card.

**POLICY.** Build log. Gather reads work the operator shipped. It writes each fact with the operator receipt for that work. It may write no external source. Card 03, external citation: a build log may have none.

**POLICY.** Lesson. Gather reads the operator's own lesson. It writes each fact that is the operator's own work with the operator receipt. It writes a claim that is not the operator's own work only together with the source that claim came from.

**POLICY.** Researched article. Gather reads a source for each claim that is not the operator's own work, and reads shipped work for each claim that is. It writes the first with that source and the second with that operator receipt.

**POLICY.** An operator receipt points at the shipped work the fact came from. This card does not fix that receipt's fields.

**POLICY.** This card locks no minimum number of sources. The gate is the next section's per-claim line. Card 02 left link count **UNKNOWN**. A minimum would be our gate, not Google's number. This card does not set one.

**UNKNOWN.** Where the subject of the page comes from. Choosing it is outside these five steps.

## 4. What the gate refuses

Each line is a refusal. A missing byline, a missing disclosure, a missing date, a missing image, a missing list, or a missing table is not a line here.

**POLICY.** A claim with no source and no operator receipt. Our gate, not a Google rule. Card 02 left link count **UNKNOWN**. A build log whose facts each have an operator receipt passes this line. Card 03, external citation: that fill may have no external citation.

**POLICY.** Cloaking. Card 02, cloaking row. The page a person receives is the page a crawler receives.

**POLICY.** Doorway abuse. Card 02, doorway row. Card 03, call to action: the heading, the direct-answer sentence, and the sections are the page for a reader who never follows the closing link. This card adds no `/blog` and no set of similar URLs.

**POLICY.** Expired domain abuse. Card 02, expired-domain row. The URL is on the existing portfolio origin.

**POLICY.** Hacked content. Card 02, hacked-content row. The HTML is the page draft wrote.

**POLICY.** Hidden text and link abuse. Card 02, hidden-text row. Card 03, hidden text: the facts are in the body a visitor can read. A fact that would exist only in markup fails this line.

**POLICY.** Keyword stuffing. Card 02, keyword-stuffing row. Card 03, title, main heading, alt text, and anchor text name this page and the link target.

**POLICY.** Link spam. Card 02, link-spam row. There is no link count to enforce. A paid link is published only with `rel="sponsored"` or `rel="nofollow"`, as card 02 locked. An ordinary editorial citation needs no `rel`.

**POLICY.** Machine-generated traffic. Card 02, machine-generated-traffic row. No step sends automated queries to Google, including a results scrape used to check rank.

**POLICY.** Malicious practices. Card 02, malicious-practices row.

**POLICY.** Misleading functionality. Card 02, misleading-functionality row.

**POLICY.** Scaled content abuse. Card 02, scaled-content row. Card 03, scaled content abuse and scraping: the fill is this page's own account. One page, for a reader. Using automation is this row only when the primary purpose is manipulating rankings, as card 02 locked. Card 02 states no page count. That count stays **UNKNOWN**.

**POLICY.** Scraping. Card 02, scraping row. Card 03, scaled content abuse and scraping: a republished page, a slight or automated rewrite of someone else's page, a copied feed, or a compilation of someone else's media is refused.

**POLICY.** Site reputation. Card 02, site-reputation row. The page is the operator's own page on this origin.

**POLICY.** Sneaky redirects. Card 02, sneaky-redirects row.

**POLICY.** Thin affiliation. Card 02, thin-affiliation row. Card 03, thin affiliation: the page's descriptions are its own. This origin is not assumed to be an affiliate site.

**POLICY.** User-generated spam. Card 02, user-generated-spam row. This card adds no channel for visitor text, files, or links.

**POLICY.** Legal removals. Card 02, legal-removals row, including child sexual abuse material. The volume that triggers a wider demotion stays **UNKNOWN**, as card 02 locked.

**POLICY.** Personal information removals. Card 02, personal-information row: doxxing, explicit personal imagery shared without consent, and explicit non-consensual fake content. The volume stays **UNKNOWN**.

**POLICY.** Policy circumvention. Card 02, policy-circumvention row. No new URL, subdirectory, or site whose purpose is to continue a violation from another row.

**POLICY.** Scam and fraud. Card 02, scam-and-fraud row.

**POLICY.** Technical floor. Card 02, technical requirements: the published response is HTTP 200, and the textual content is HTML. Card 01: the object is one public HTML URL. A chosen target on another host fails this line.

**POLICY.** The gate does not refuse length, a link count, a Core Web Vitals score, E-E-A-T, or the use of automation. Card 02. It does not refuse a missing byline, a missing automation disclosure, a missing image, a missing visible date, a missing list, a missing table, or missing `Article` markup. Card 03. A list is drafted only when the packet's facts are a sequence. A table is drafted only when they are a comparison. Card 03, list and table. `Article` markup is not a block and is not an indexing condition. Card 03.

## 5. What deploy writes and what the receipt is

**FEASIBLE.** Repository `aryanjohari/aryan-portfolio`, README, section "Vercel deployment", https://github.com/aryanjohari/aryan-portfolio/blob/main/README.md, accessed 2026-09-29. The site is that Next.js repo, built on Vercel. On each deploy, `prebuild` runs `fetch:projects` and `build:guide-context`. The same README says `npm run build` runs `fetch:projects` via prebuild, then `next build`.

**FEASIBLE.** Repository `aryanjohari/aryan-portfolio`, "Ship checklist", https://github.com/aryanjohari/aryan-portfolio/blob/main/docs/ship-checklist.md, accessed 2026-09-29. The file is pre-deploy verification: lint, build, and smoke tests of the routes it names. Under "Explicitly deferred (v2)" it lists "ADA blogs". This card does not add `/blog`.

**FEASIBLE.** The GitHub homepage field for `aryanjohari/aryan-portfolio`, read 2026-09-29, is `https://aryan-portfolio-one-kappa.vercel.app`. A fetch of that URL on 2026-09-29 returned HTTP 200 and `Content-Type: text/html`. The README and the ship checklist do not name this hostname.

**HUNCH.** Those two files say the prebuild runs on each deploy. They do not name the git event that starts a Vercel deploy. This card does not treat a push to `main` as a trigger those files document.

**POLICY.** Deploy writes one commit on `github.com/aryanjohari/aryan-portfolio` containing the drafted page. After the Vercel build of that repo, the page is one public HTML URL on the existing origin. The receipt is that commit and that URL.

**POLICY.** Deploy does not publish through an S3 `page.json`, a Pi organ, or a second site. Card 01: the object is the public HTML URL.

**POLICY.** Draft writes the card-03 blocks from the packet. The `<title>`, the main heading, the sections, an image only when the packet has a picture the text needs, links only for URLs the packet or the chosen URL already has, one self-referential canonical for the chosen URL, a visible published date and a visible modified date, a byline and an automation disclosure only when a reader of that page would expect them, and a call to action only as an optional close. The direct-answer sentence is a fact the packet already contains. Card 03.

**POLICY.** The published date is the date this page is published. The modified date changes when the page substantially changes. Card 03, published date and modified date. Draft must not write a future date, and must not label an event date from the packet as the page's published date.

**UNKNOWN.** Which path on the origin the one URL uses. This card does not add a route.

**UNKNOWN.** Which existing page on the origin will hold the inbound link. Card 03, internal link: a page this origin cares about needs a link from at least one other page on the origin. This card does not name that page.

## 6. In / out for this card

**In.** The five steps. What each step reads, writes, and must not invent. What gather emits for a build log, a lesson, and a researched article. What the gate refuses. The deploy receipt: a commit on the portfolio repo and one public HTML URL on the existing origin.

**Out.** Choosing a topic. A research method. Search Console and the measurement loop. Code and a new route, including `/blog`. An S3 `page.json`, a Pi organ, and a second site.

## 7. Won't-chase

- A word count, or a link count stated as Google's number. Card 02 left link count **UNKNOWN**.
- A minimum number of sources. This card does not lock one. A later card that locks one must tag it **POLICY** and call it our gate, not Google's.
- A revalidation interval as a ranking rule.
- A Search Console report, a manual action, or a measurement loop.
- `Article` markup as a block or as an indexing condition. Card 03.
- Refusing a page for length, link count, Core Web Vitals, E-E-A-T, or for using automation. Card 02. AI writing is a card-02 violation only when the primary purpose is manipulating rankings.
- `llms.txt`, a Markdown twin, or a second file. Card 01.
- Vendor pipeline kits (**MARKETING**).

## 8. What would prove this wrong

1. The portfolio README or `docs/ship-checklist.md` states that the production page is an S3 `page.json`, a Pi organ, or a second site.
2. The published HTML URL shows a fact that the gather packet for that commit does not contain.
3. Card 03's build log is required to carry an external citation, so a packet of operator receipts alone cannot be that fill.
4. A packet that matches a card-02 row in §4 is still a valid pass for this gate.
5. Google publishes a source count or a link count and states that a page under that count is ineligible, where this card says any such number is our gate and card 02 left link count **UNKNOWN**.

## 9. Source list

All accessed 2026-09-29. The Google pages this gate points at stay in cards 01, 02, and 03. This card adds the portfolio repo.

1. Repository `aryanjohari/aryan-portfolio`. "README", section "Vercel deployment." https://github.com/aryanjohari/aryan-portfolio/blob/main/README.md
2. Repository `aryanjohari/aryan-portfolio`. "Ship checklist." https://github.com/aryanjohari/aryan-portfolio/blob/main/docs/ship-checklist.md
3. This repo. "01 — How discovery works." `docs/research/01_how_discovery_works.md`
4. This repo. "02 — Google page rules." `docs/research/02_google_page_rules.md`
5. This repo. "03 — Page blocks." `docs/research/03_page_blocks.md`
