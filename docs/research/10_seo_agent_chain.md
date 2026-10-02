# 10 — SEO agent chain

Access date for every source this card fetched: 2026-09-30. Cards 01–09 keep the access date on those cards, 2026-09-29, when this card cites them instead of re-fetching the page.

Tags: **EVIDENCE** (a primary source), **HUNCH** (a reading, not a measurement), **MARKETING** (an agency, blog, or tool page; not a ranking rule and not a publish gate), **POLICY** (a rule this card locks), **METAL** (code this card read), **FEASIBLE** (this origin can host the object), **UNKNOWN** (not established).

The page is the one public HTML URL locked in card 01, filled with the card-03 blocks, gated by the card-02 refusals and the card-04 steps. The file is the `content/blog/{slug}.md` contract locked in cards 08 and 09. This card designs the unattended chain that writes that file on one origin. It writes no product code and no post.

## 1. Question

What chain, with what rails, writes one portfolio blog page and pushes it with no human confirm, and which earlier locks does that chain replace?

## 2. Short answer

**POLICY.** For `github.com/aryanjohari/aryan-portfolio` only, the first checkout write and the git push of `content/blog/{slug}.md` do not wait for a person to say yes. That is a deliberate supersession of the confirm requirement in cards 07, 08, and 09, and of the charter sentence that `blog_checkout_write` needs confirm. It does not apply to any other origin. It does not apply to delete. It does not apply to overwrite of a slug that already exists.

**POLICY.** Twelve stages, in this order. One wake advances one stage of one queue item, writes a receipt, writes `next_wake_at`, and sleeps. Bind site. Understand aim. Plan. External fetch. Gather. Gate. Draft. Librarian. Diagram. Critic. Deliver. Push. A critic failure does not deliver. Search Console, patch or leave, and the next campaign are named later stages. They are not v1 code.

**POLICY.** The control surface is a wake and a tool. This card adds no HUD control and does not use the existing blog form as the way a page is published.

**Superseded 2026-09-30** for one control only. What replaced that sentence: a form and a button. The wake, the twelve stages, the receipts, and `next_wake_at` stay. The form queues titles. The button runs the remaining stages for the next queued title, then stops. This control is not the existing four-step Blog page form (store, gather, draft, copy, delete). That form stays.

**Superseded 2026-09-30** for the operator-typed title on this form. The form queues titles. The button runs the remaining stages for the next queued title, then stops. What replaced that title: the plan writes one reader question from one named source and the YAML aim, keywords stay off the question, and one button publishes one page. The wake, the twelve stages, the receipts, and `next_wake_at` stay.

**Superseded 2026-10-01.** Why: the first prose line was an access-date stamp, so the title, the description, and the opening did not name the topic. What replaced it: the line under "## 1. Question" is the title when the slug fits. A longer question is refused whole. The draft still writes a reading for a stranger and leaves an access-date stamp, a repo path, and a machine name out of the prose. Keywords stay off the question. The wake, the twelve stages, the receipts, and `next_wake_at` stay.

**Superseded 2026-10-01** for the verbatim Question line. Why: that line is a research question, so the title named the research frame, and a code file's first sentence made the page a review of the file. What replaced it: the plan asks for one short question in plain words, using only words already in the file. The research Question line is not copied whole. A question that does not fit the slug is refused whole. The draft answers that question for a stranger and does not review the file line by line. A list is for a sequence and a table is for a comparison. The diagram still skips when the page has neither. Keywords stay off the question. The wake, the twelve stages, the receipts, and `next_wake_at` stay.

## 3. Research findings

### What Google says the page needs

These rows are the published conditions and best practices this chain is allowed to treat as Google's words. A best practice is not an eligibility floor. Card 02 already locked that split. This card does not add a third floor.

**EVIDENCE.** Google, [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features) (page last updated 2025-12-10 UTC). To be a supporting link in AI Overviews or AI Mode, a page must be indexed and eligible to be shown with a snippet. There are no additional technical requirements and no special schema.org type. The listed fundamentals include crawling allowed, the page findable by internal links, important content in text, images and video when they apply, and structured data that matches the visible text. Meeting the requirements does not guarantee crawling, indexing, or serving. AI Overviews often do not trigger.

**EVIDENCE.** Google, [Optimizing your website for generative AI features on Google Search](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), accessed 2026-09-30. Generative AI features on Search sit on the core ranking and quality systems. Grounding retrieves pages from the Search index and shows clickable links. The same page says a page must be indexed, snippet-eligible, and included in Search generative AI features in Search Console. It tells owners to write non-commodity, people-first pages, organize them in paragraphs and sections with headings, and support the text with relevant images and video when that helps a reader. It says making a separate page for every query variation, primarily to manipulate rankings or generative AI responses, violates the scaled-content spam policy.

**EVIDENCE.** Google, [Link best practices for Google](https://developers.google.com/search/docs/crawling-indexing/links-crawlable) (page last updated 2025-12-10 UTC). Google uses links to find pages and as a relevancy signal. A crawlable link is an `<a>` with an `href`. Good anchor text is descriptive, reasonably concise, and relevant to both pages. Every page you care about should have a link from at least one other page on the site. There is no ideal number of links. Linking to other sites is not something to avoid. External links can help establish trustworthiness, for example by citing sources. Use `nofollow` when you do not trust the source, not on every external link. A paid link uses `sponsored` or `nofollow`.

**EVIDENCE.** Google, [Qualify your outbound links to Google](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links) (page last updated 2025-12-10 UTC). A regular link you expect Google to fetch needs no `rel`. `sponsored` marks ads and paid placements. `nofollow` is for the other cases where you do not want Google to associate the site with the target, or to crawl that target from the page. `ugc` is recommended for links visitors insert.

**EVIDENCE.** Google, [Google image SEO best practices](https://developers.google.com/search/docs/appearance/google-images) (page last updated 2026-03-02 UTC). Google finds images in the `src` of an `img` (including an `img` inside `picture`). It does not index CSS images. Supported formats in that `src` include WebP and SVG. Use a descriptive filename, place the image near the text it explains, and write alt text that describes the picture. Keyword-stuffed alt text is named as a bad example that may be treated as spam. The same URL should be used when the same image is referenced more than once. The page states no image count. `og:image` and `primaryImageOfPage` can influence which image is chosen as a preview. They are not a condition of indexing the page.

**EVIDENCE.** Cards 01 and 03, accessed 2026-09-29. Title, visible headings, visible text, a self-referential canonical, and visible published and modified dates are the blocks those cards already tied to Google's title-link, snippet, canonical, and byline-date pages. This card does not restate those pages. A featured snippet cannot be requested. Which passage is quoted stays **UNKNOWN**.

**HUNCH.** A direct answer in visible text, a heading that states the page, and a citation next to the claim are the kind of page those Google sentences describe. They are not a forecast that this origin will be crawled, indexed, snipped, or cited.

### What Google says it does not require

**EVIDENCE.** The same AI-features page. No additional technical requirements for AI Overviews or AI Mode. No new machine-readable file, AI text file, or special schema.org type.

**EVIDENCE.** The same optimization guide, section "Mythbusting generative AI search." Google says you can ignore, for Google Search: `llms.txt` and other special AI markup (Google Search does not use them; keeping such a file neither helps nor hurts Search); chunking the page for the model; rewriting the page in a special way for generative AI search; seeking inauthentic mentions; treating structured data as required for generative AI search. There is no ideal page length. The names AEO and GEO are described as terms people use online. Optimizing for those Google features is still SEO. Third-party tools do not have Google's internal ranking or AI metrics.

**POLICY.** This chain does not emit `llms.txt`, a Markdown twin, a chunk file, or a schema type whose purpose is AI Overviews. `Article` markup stays what card 03 locked: not a block and not an indexing condition. A missing byline and a missing automation disclosure stay non-refusals, as card 02 locked.

### What the GEO research measured

**EVIDENCE.** Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, and Deshpande, [GEO: Generative Engine Optimization](https://arxiv.org/abs/2311.09735), KDD 2024, DOI `10.1145/3637528.3671900`. A generative engine, in that paper, is a retriever plus a model that writes one answer with citations. On GEO-bench the retriever is the top five Google results, given to `gpt-3.5-turbo`. Visibility there is a share of the answer attributed to a source, not a blue-link rank. Cite Sources, Quotation Addition, and Statistics Addition raised position-adjusted word count on the order of 30–40 percent relative, inside that fixed set. Keyword stuffing did not help in that bench. The paper also reports a Perplexity.ai check. Card 01 already locked the limit: the gain is citation share after the source is already in context. It is not a Google eligibility rule and not a traffic forecast.

**EVIDENCE.** Martinez, [Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization (2023–2026)](https://arxiv.org/abs/2607.14035), arXiv preprint, 15 July 2026, accessed 2026-09-30. The survey reads that 40 percent figure as a relative gain inside a five-document context. It says the result does not establish organic discoverability or a durable traffic effect. Across the studies it reviewed, it found no technique with a stable cross-platform causal effect on organic discoverability or on downstream clicks. It treats visibility as something that varies by engine, date, place, and query. This card treats the survey as a preprint argument. The experimental limit is the paper's own method, as card 01 locked.

**POLICY.** Quotations, statistics, and extra citations are not a rewrite this chain performs in order to be cited. A citation is written only when gather stored that URL. A number is written only when it is a span in the packet. Keyword stuffing stays the card-02 refusal.

### What practitioners say, and what this chain does with it

Each row is **MARKETING**. The pages sell or teach a blog checklist. None of them is a Google ranking rule. The Semrush percentage and the "March 2026 core update" sentences on the Kozec page are claims that page makes. This card did not find those sentences on a Google page fetched today. Google's optimization guide, fetched 2026-09-30, still says structured data is not required for generative AI search and that there is no special schema type.

| What the pages say | Where | This chain |
| --- | --- | --- |
| Answer the question in the first 100 words, or open with a TL;DR. | [Marketing USA](https://marketingusaagency.com/optimize-a-blog-post-for-seo/), accessed 2026-09-30. [Rankai](https://rankai.ai/articles/how-to-optimize-a-blog-post) says the work starts with keyword research and continues through a Search Console rewrite. | Adopt the direct answer as **POLICY**, which card 03 already placed first in the body. Refuse 100 words, and refuse any word count, as a gate. Card 02 and card 03 state no such cutoff. |
| Put the primary keyword in the title, the first paragraph, one H2, and the image alt text. | Marketing USA, same page. | Refuse as a recipe. The title is the question. Alt text describes the picture. Anchor text describes the target. Card 02, keyword stuffing. The links page says not to cram keywords into anchors. |
| Use 3–5 internal links, or 2–4 internal links per 1,000 words. Link out to 1–3 "authority" sources per 1,000 words. | Marketing USA. [Verold](https://www.verold.com/on-page-seo-elements-blog-post-2026/), accessed 2026-09-30. [Kozec](https://kozec.ai/seo-blog-post-structure-best-practices/), accessed 2026-09-30. | Refuse the counts. The links page states no ideal number. Card 02 left link count **UNKNOWN**. Adopt descriptive anchors and in-sentence links, which that Google page does state. "Authority" and a per-1,000-words quota are not a publish gate. |
| Give every post a featured image, often 1200×630, plus Open Graph tags. One of the pages says not to repeat that hero in the body. Another says put the image near the top. | Verold. Marketing USA. | Refuse the pixel size, the Open Graph tags, and "every post" as gates. Card 03 left `og:image` off the block list and left a missing image as a non-refusal. Adopt an image only when the text needs one, beside that text, with alt text. Google's image page supports WebP and SVG and asks for a descriptive filename and alt text. |
| Place a CTA in the first 30 percent, again in the middle, and again after the conclusion. Kozec ties the first 30 percent to a Semrush figure of 44.2 percent of LLM citations. | Kozec. [Helping Bloggers](https://helping-bloggers.com/blog-post-structure-intro-body-and-cta-that-converts/) tells the writer to put a CTA at the end. | Refuse stacked CTAs and the Semrush figure. **POLICY** placement is in §5: the direct answer comes first; the CTA may close; one thin link to the same target may sit after that sentence. The page is still the page if the reader never follows the link. Card 03. |
| Add FAQ schema, Article schema, and a table of contents so AI engines will cite the page. Kozec says a March 2026 core update turned FAQ schema into an AI trust signal, and that pages without schema ask AI engines to trust them without credentials. | Kozec. Marketing USA also tells the writer to paste Article schema. | Refuse. The AI-features page and the optimization guide say there is no special schema type for these features. Card 03. A schema claim that appears on these blogs and not on those Google pages stays **MARKETING**. |
| Internal links raise "AI citation probability" and topical authority. Keep every page within three clicks of the home page. | Kozec. Verold says internal links pass authority and that a new post linked from older posts is crawled within hours. | Refuse the probability, the hour count, and the three-click rule. **EVIDENCE** for the narrower fact: Google uses links to find pages, and a page you care about should have at least one internal link. Whether this origin is crawled on any clock is **UNKNOWN**. |
| Choose the title from keyword research before writing. | Marketing USA. Rankai. | Refuse as an automatic title. A keyword list may be logged beside the plan as **MARKETING** or **HUNCH**. It does not become the question. §4. |

### Images, three ways

**EVIDENCE.** Google's image page, above. The image that can be indexed is an `img` `src` in a supported type, including WebP and SVG, near the relevant text, with alt text that describes it.

**(a) A diagram committed in the portfolio repo.** **FEASIBLE.** `blog.ts` already reads `content/blog/*.md`. A sibling file under that repo can be the `src` the markdown points at. The page does not depend on a third-party image host. The alt text and the bytes are in the same commit as the post.

**(b) Unsplash.** **EVIDENCE.** [Unsplash API Guidelines](https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines), written by Unsplash Dev, 27 July 2026. API use must hotlink `photo.urls`. Choosing an image for a blog post or a header must call `photo.links.download_location` (that endpoint counts a download; it is not the URL you embed). The page must attribute the photographer and Unsplash, and links back to Unsplash use `?utm_source=your_app_name&utm_medium=referral`. Keys stay confidential. [The authentic-experiences guideline](https://help.unsplash.com/en/articles/2511256-guideline-high-quality-authentic-experiences), same author and date, says the API is for non-automated, high-quality, authentic experiences, and lists data mining and training AI models among the uses to stay away from.

**(c) A generated picture.** **EVIDENCE.** Google, [Google Search's guidance on using generative AI content on your website](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content) (page last updated 2025-12-10 UTC). Generative AI can help research a topic and add structure to original content. Generating many pages without added value may violate scaled content abuse. The page says to consider telling readers how automation was used, including image metadata, where that would help them. The IPTC `DigitalSourceType` `TrainedAlgorithmicMedia` rule on that page is a Merchant Center rule for ecommerce images. This portfolio page is not a Merchant Center product.

**POLICY.** The portfolio default is (a): one diagram, WebP or SVG, committed in the checkout, only when a section is a flow the words need a picture of. The fallback is (c): a generated diagram committed on that same path, with alt text, and only when no committed diagram exists and the section is that kind of flow. Unsplash is refused for v1. Hotlinking would put the public page on Unsplash's CDN. Committing the file would break the hotlink rule. An unattended wake that searches the API and picks a photo is the automated use that guideline tells applications to avoid. A stock photo is not the diagram this page uses. Card 03: no picture when the text does not need one.

### Outbound links

**EVIDENCE.** The links page, above. External links can help establish trustworthiness when they cite sources. They are not forbidden. `nofollow` is for a source you do not trust, or for a paid link, not for every citation. The qualify-outbound-links page says a normal editorial link needs no `rel`.

**EVIDENCE.** Card 02, link-spam row. The abuse is links bought, sold, exchanged, or required in order to pass ranking credit, and pages created to manufacture those signals. An ordinary editorial link is not that row.

**HUNCH.** A citation can help a reader check a claim. Whether any citation on this origin raises rank, trust, or AI citation share is **UNKNOWN**. The GEO papers do not turn "add citations" into a Google rule. Card 01.

**POLICY.** The librarian may link to a URL that is already in the packet. That link is editorial and has no `rel`. This chain creates no paid link, no link exchange, and no link whose purpose is ranking credit.

### Automation and scaled content

**EVIDENCE.** Danny Sullivan and Chris Nelson, [Google Search's guidance about AI-generated content](https://developers.google.com/search/blog/2023/02/google-search-and-ai-content), 8 February 2023. Appropriate use of AI or automation is not against the guidelines. Using automation, including AI, primarily to manipulate rankings is a spam violation. Helpful automation is already part of the web: sports scores, weather forecasts, transcripts. Using AI gives a page no special gain. A disclosure is worth adding where a reader would ask how the page was made. Listing AI as the author is not how that post says to make the role clear.

**EVIDENCE.** Google, [Spam policies for Google web search](https://developers.google.com/search/docs/essentials/spam-policies), scaled content abuse, retrieved 2026-09-30. Many pages generated primarily to manipulate rankings, not to help users. The focus is a large amount of unoriginal content with little or no value, however it is produced. One example is generative AI used to make many pages without added value. Google states no count for "many." Card 02 left that count **UNKNOWN**.

**EVIDENCE.** The optimization guide, above. Separate pages for query variants, written primarily to manipulate rankings or generative AI responses, violate that policy. A high quantity of pages does not make a site more relevant.

**EVIDENCE.** The generative-AI content page, above. The same line: many pages without added value may be scaled content abuse. The quality-rater sections it points at are not a ranking recipe. Raters' scores do not directly change ranking.

**POLICY.** This chain may write with automation. The critic refuses a page that pastes a source, a page that is only a query variant of a page already queued, a city or service-area grid, and a page whose sentences are not an account of the packet. One wake still writes one stage of one item. This card adds no page-count cap. Google states none. Card 02.

## 4. Policy supersessions

What changes, and what does not.

| Earlier lock | What this card does |
| --- | --- |
| Card 07 §2 and §5. The first publish waits until a person says yes. Status `waiting_on_aryan` is that wait. | **Superseded** for the portfolio checkout write and the portfolio git push only. Those two stages run when the critic has passed. They do not set `waiting_on_aryan` and they do not read a confirm flag. |
| Card 08 §2 and §5 steps 4–7. After draft, status is `waiting_on_aryan`. The yes is `POST /api/confirm`. Git push is a second confirm. | **Superseded** for those two stages on this origin. The local draft under `artifacts/` remains. The checkout write is no longer that confirm. The push is no longer a second confirm. |
| Card 09 slices 4 and 6. `blog_checkout_write` uses `side_effect` `confirm`. Git push stays a later confirm. The charter sentence says the checkout write needs confirm. | **Superseded** for portfolio deliver and push. A later code slice changes that tool and that sentence. This card does not edit them. |
| Card 07 §3 and §5. A person supplies the question. An empty queue stays attended. The wake does not invent a question. | **Superseded** for this origin's plan stage. The plan may write questions from the fixed aim and from named sources already on disk, and it logs that plan. It still may not invent a site, an audience sentence, or a question that is a keyword or a Search Console query. If no named source exists, the queue stays empty and no draft runs. |
| Card 06 §4 and card 07 §3. The first subject on the portfolio is a build log of shipped work. | **Superseded** for queue order. A researched item whose source is a file under `docs/research/` may be queued, including as the first item. Card 08 already locked that file as the first implementation test. A build log remains the fill when the facts are shipped work with an operator receipt. The plan does not prefer researched pages in order to be ranked. |
| `docs/modules/M06_CAMPAIGNS_LONG_HORIZON.md`. A stage that touches the world waits for a confirm. | **Superseded** only for portfolio blog deliver and portfolio blog push. Delete, any other origin, mail, and home-assistant actuators stay on that confirm rule. |
| Card 08. The call to action is a label and a URL the person typed, or the page has none. | **Narrowed.** The label and the URLs come from the fixed portfolio config, written once, not from a per-page confirm. The writer still may not invent a label or a URL. If the config has no pair, the page has no call to action. |
| Card 03. A call to action may close the page. The heading, the direct-answer sentence, and the sections are the page for a reader who never follows it. | **Stands.** This card adds one optional thin link, after the direct answer, to the same target as the close. It does not move the call to action above the direct answer. It does not allow the link to be the only useful block. |
| Card 03. An image is absent when the text needs none. Links sit in the sentence that uses them. | **Stands.** The diagram stage may skip. Citations in a closing list may only repeat URLs already used in those sentences. |
| Card 04. Gather is the only step that may introduce a fact. Deploy is one commit on this repo and one public HTML URL. | **Stands.** External fetch writes spans into the packet before gather closes. Draft, librarian, diagram, critic, deliver, and push add no fact. The push receipt is the commit. The public URL is not marked observed until a later read sees HTTP 200 HTML. Card 04 left the Vercel trigger as a **HUNCH**. This card does not treat a push to `main` as a documented deploy trigger. |
| Card 02 spam refusals. Card 05 fields cannot pass, fail, or choose a subject. Card 06 patch or leave. Card 07 refusals of the `main` planner (top query as a page, 0.12 CTR, position 5). | **Stand.** |
| Card 08 and card 09. While `content/blog/{slug}.md` exists, refuse to overwrite it. Delete removes that file and clears the slug, and the same slug may be written again. No `-2` suffix. | **Stand.** Delete still requires confirm. This card does not automate delete. v1 deliver never overwrites. |
| Card 06. The holder of the inbound link from a page the site already serves is **UNKNOWN**. | **Stands** for `/`, `/about`, `/projects`, `/workshop`, and `/projects/{slug}`. Once two blog files exist, the librarian may link between their canonical paths. That does not name the site-wide holder. |
| Card 09. `ADA_PORTFOLIO_CHECKOUT` must be a git checkout whose origin URL contains `aryanjohari/aryan-portfolio`. | **Stands.** |

Card 07's own falsifier 5 said a first publish with no person saying yes would mean that card was no longer the rule the series wants. This card is that change, for this origin only.

## 5. Chain stages

**POLICY.** The fixed config is one YAML file the operator writes before the first wake. A wake does not create it and does not fill a missing field. The fields are: `site` = `github.com/aryanjohari/aryan-portfolio`; one audience sentence; `aims` drawn only from `hire`, `prove-shipping`, and `educate`; optional `default_cta` with label `Get in touch` plus a `mail` URL and a `call` URL, both present or both absent; `branch` = `main` or another branch name in that file; the public host from card 04, `https://aryan-portfolio-one-kappa.vercel.app`, as a label, not as a fresh measurement. Local service-area intent is not an aim.

**Superseded 2026-10-01.** Card 11 is the file shape. What changed: one aim (`hire`, `prove-shipping`, `educate`, `book`, or `call`), a fact queue of `fact`, `question`, `source`, and `url`, a 12-item cap, and a proven service fact may be a page. A suburb grid is still refused. What did not change: the twelve stages, portfolio bind, and no Search Console.

**POLICY.** Ports. A source adapter returns verbatim spans from a named local path or a named URL. A sink adapter writes one markdown file on one origin and may push that file. v1 source is a file under this repo, plus URLs named on the plan item. v1 sink is the portfolio checkout. A later sink named `9horsemen` is a second adapter with the same method names. This card does not implement it and does not publish there.

**POLICY.** The plan is automated and auditable. Plan writes a YAML artifact of the queue before any draft. There is no human accept of that artifact. The artifact is the record of what was queued, which aim it serves, and which suggestions were refused.

**POLICY.** Page shape for this origin, which is not a service-by-suburb page. In the body, in this order: the question as the title and the main heading; the direct-answer sentence; an optional thin "Get in touch" link, only after that sentence, only to the config URLs; the problem; how it works; an optional diagram beside the words it explains; the same call to action as a close; citations that repeat packet URLs already used in the sentences. A list is the shape of a section when the facts are a sequence. A table is the shape when they are a comparison. Card 03. The page is still useful if the reader never follows the call to action.

| Stage | Reads | Writes | Must not |
| --- | --- | --- | --- |
| 1. Bind site | `ADA_PORTFOLIO_CHECKOUT` and the origin URL. The fixed config `site`. | A receipt that the checkout is `aryanjohari/aryan-portfolio`, or a refusal. | Draft, fetch, or write the checkout. Accept any other origin, including a 9horsemen checkout. |
| 2. Understand aim | The fixed config: audience sentence and aims. | Those fields on the plan artifact. | Invent an audience. Read Semrush, DataForSEO, or Search Console. Choose a keyword as the audience. |
| 3. Plan | The aim. Named sources already on disk: `docs/research/*.md`, and operator receipts for shipped work. The published set: `content/blog/*.md` canonical paths, if the checkout exists. | A queue. Each item has a question, a fill (`build-log`, `lesson`, or `researched`), one source path, and the default call to action copied from config or marked absent. A log line for any keyword suggestion, tagged so it cannot be copied into `question`. **Superseded 2026-10-01.** Why: the first prose line was an access-date stamp, so the title, the description, and the opening did not name the topic. What replaced it: the line under "## 1. Question" is the title when the slug fits. A longer question is refused whole. The draft still writes a reading for a stranger and leaves an access-date stamp, a repo path, and a machine name out of the prose. Keywords stay off the question. The wake, the twelve stages, the receipts, and `next_wake_at` stay. **Superseded 2026-10-01** for the verbatim Question line. Why: that line is a research question, so the title named the research frame, and a code file's first sentence made the page a review of the file. What replaced it: the plan asks for one short question in plain words, using only words already in the file. The research Question line is not copied whole. A question that does not fit the slug is refused whole. The draft answers that question for a stranger and does not review the file line by line. A list is for a sequence and a table is for a comparison. The diagram still skips when the page has neither. Keywords stay off the question. The wake, the twelve stages, the receipts, and `next_wake_at` stay. **Superseded 2026-10-01.** Card 11. What changed: one aim, a fact queue, a 12-item cap, and a proven service fact may be queued. A suburb grid is still refused. What did not change: the twelve stages, portfolio bind, and no Search Console. **Superseded 2026-10-02.** What changed: the button writes one short reader question from the YAML fact and the 2 or 3 local notes, and that question is the title. What did not change: one page per fact, no web search, keywords stay off the question, the draft still answers the stored question. **Superseded 2026-10-02.** Why: the brief was denied for a word outside the audience, the aim, and the fact, and the title became the date sentence before a note was opened. What changed: the brief may use ordinary words, and the title is one question written after the notes are opened, with every content word in the fact or those paragraphs. What did not change: one page per fact, the YAML question is not copied whole, keywords stay off the question, a slug that does not fit is refused whole. **Superseded 2026-10-02.** Why: the YAML question became the title, so the page answered a lab check. What changed: the plan reads the site from the YAML, writes the idea, gathers passages for that idea, then writes a search-intent title. The YAML question is a frame and is not the title. What did not change: twelve stages, one page per queue row, keywords stay off the question, no web search. **Superseded 2026-10-02.** Why: a search title was refused when it used a word that was not already in the fact or the notes, so the page never got a title a stranger would search. What changed: the title may use the words a stranger would type. A new URL, host, date, or number is still refused. What did not change: twelve stages, one page per queue row, the YAML question is not the title, keywords stay off the question, no web search. **Superseded 2026-10-02.** Why: a search title was allowed to leave the passages, so the page promised a guide the notes do not contain. What changed: the title may still use the words a stranger would type, and it has to name what the passages say. It must not promise a guide, a definition, or a procedure the passages do not contain. What did not change: twelve stages, one page per queue row, the YAML question is not the title, keywords stay off the question, no web search, a new URL, host, date, or number is still refused. **Superseded 2026-10-02.** Why: the plan started from one URL fact, one source file, and a YAML question, so every page was that measurement. What changed: the YAML stores the business and a list of facts with their notes, and the plan chooses one page those facts can support, then the notes, then the passages, then the title. What did not change: twelve stages, one page per run, no web search, keywords stay off the title, a new URL, host, date, or number is still refused, the title still has to name what the passages say. **Superseded 2026-10-02.** Why: the plan could only see the sentences the operator had copied into the file, so after those sentences were used the operator had to replace them by hand. What changed: the YAML stores the business and the card folders, and the plan chooses the next unpublished card in those folders, then the notes, then the passages, then the title. What did not change: twelve stages, one page per run, no web search, at most three notes, keywords stay off the title, a new URL, host, date, or number is still refused, the title still has to name what the passages say. | Turn a keyword, a Search Console query, or a Semrush row into a title. Open a second URL for a question already in the published set. Queue a city, suburb, or service-area page. Queue a researched item whose source file is missing. Walk the queue. Write a post. |
| 4. External fetch | URLs already named on this item, including URLs listed as sources inside the named research card. **Superseded 2026-10-02.** What changed: fetch reads 2 or 3 local markdown files for the YAML fact, then the allowlisted paper links those files already name. What did not change: no web search, no new allowlist entry, no hop beyond those links, one page per fact. **Superseded 2026-10-02.** Why: artifacts/2026-10-01/what-public-host-returned-this-html.md. The date in a file name matched the fact, and the notes were not about that fact. What changed: the button writes a short brief, shows a heading and two sentences per research note, and Gemini picks at most 3 notes about the fact. What did not change: one page per fact, no web search, no new allowlist entry, the code critic still gates publish, keywords stay off the question. **Superseded 2026-10-02.** Why: fetches was empty because the portfolio address was in backticks and the paper hosts were not allowlisted. What changed: a backtick or bare https URL in the stored section is a citation, and fetch still requests only an allowlisted markdown link. What did not change: no new allowlist entry, confirm_host stays false, no hop, no web search. | Verbatim spans plus the URL, stored on the item. A skip receipt when the item names no URL. | Search the web. Query Google. Add a URL the item did not name. Send automated queries to Google, including a results scrape used to check rank. Card 02. |
| 5. Gather | The named source file. The fetch spans from stage 4. For a build log, the operator receipt. **Superseded 2026-10-02.** Why: two catalog sentences hid the fact. What changed: the button opens a chosen file once and stores the paragraph that meets the fact. What did not change: at most 3 files, no web search, no new allowlist entry, the code critic still gates publish. **Superseded 2026-10-02.** Why: one paragraph hid the rest of the deploy section, and a dot in the host split the URL. What changed: the button stores the section that contains the fact, and a URL is kept whole. What did not change: at most 3 files, not every line of the file, the code critic still gates publish. **Superseded 2026-10-02.** Why: the stored heading included the lab lines, so the draft became a receipt and the title became the unknown path. What changed: the button stores the later paragraph that meets the fact, and a plain operator question may be the title. What did not change: at most 3 files, the catalog stays two sentences, the code critic still gates publish. **Superseded 2026-10-02.** Why: the stored body was only the paragraph that met the fact, so the draft could only repeat the measurement. What changed: the button stores the passages from the chosen files that teach the idea, and leaves out UNKNOWN, POLICY, and HUNCH. What did not change: at most 3 files, the catalog stays two sentences, no web search. | The packet. Each fact is a verbatim span with that source or that receipt. | Invent a fact. Write markdown. Publish. Card 04. |
| 6. Gate | The packet, the fill, and the site. | The same packet, or a refusal. | Drop, rewrite, or add a fact. Refuse length, link count, Core Web Vitals, E-E-A-T, or the use of automation. Card 02. Card 04. |
| 7. Draft | The passed packet and the question. | One local file `artifacts/{UTC date}/{slug}.md`. Frontmatter as in card 08. Body in the shape above, with no links and no image yet. New sentences. No new facts. **Superseded 2026-09-30.** What replaced that sentence: the draft writes one plain page of paragraphs from the packet, a claim must be in the packet, the model may use its own words, and ## The problem, ## How it works, and ## Spans are not required. **Superseded 2026-09-30** for the content-word rule in that sentence. What replaced it: ordinary words are allowed, and a number, a date, a tool name, or a numeric outcome that is not in the spans is refused. **Superseded 2026-09-30** for the fact rule. What replaced it: the page is a reading of the packet in the model's own words. The draft and the critic do not refuse a word, a number, a date, or a name. They still refuse a pasted source and a pipe table of every line. The shape checks stay. The wake, the twelve stages, the receipts, and `next_wake_at` stay. **Superseded 2026-10-02.** What changed: one retry inside the draft wake, with the refusal reason on the second prompt. What did not change: the shape rules, the critic's one delete-repair, no push after a second draft refusal. **Superseded 2026-10-02.** Why: the page restated the research card. What changed: the draft writes a post a stranger would read from the stored paragraph. What did not change: no pasted source, no new facts, the shape checks stay. **Superseded 2026-10-02.** Why: the first paragraph was ordered to answer the YAML question from that one measurement. What changed: the draft writes a post for the planned title from the stored passages. What did not change: no pasted source, no new facts, no invented URL, the shape checks stay, the code critic still gates publish. **Superseded 2026-10-02.** Why: the draft was told to write a publishable page for that title, with scannable headings and a step list, and that the live URL was not the subject, so three lab sentences became an outline. What changed: the draft writes only the post the stored passages can support, as a few plain paragraphs, with the useful fact first and the title not repeated as that paragraph. A heading or a list appears only when the passages are a sequence or a comparison. What did not change: no pasted source, no new URL, the critic still refuses a pasted source, a card body, an unknown claim, and a raw-URL anchor. | Paste the source. Add a fact, a URL, or a picture. Append `## Cites` by passing `source_cites`. Card 08. Card 09. |
| 8. Librarian | The draft. The published canonical paths on this origin. Packet URLs. | In-sentence internal links and external citations, plus a closing citation list that only repeats those URLs. **Superseded 2026-10-01.** Why: a URL was linked only when the verbatim span was still on the page, so a rewritten sentence left the live pages with a bare address or no link. What replaced it: link a URL that already appears in the named source file or in a packet span, in the sentence that uses it, even when the model rewrote the span. Do not invent a URL. Do not add `rel`. An internal link may use a shorter phrase that still names an already published blog post, and the whole question does not have to appear verbatim. Do not link `/`, `/about`, `/projects`, `/workshop`, or a project slug. Do not invent a call to action. If `portfolio_chain.yaml` has no `default_cta` mail and call pair, the page still has none. **Superseded 2026-10-02.** Why: the anchor was the URL, so the critic failed. What changed: the librarian links a name already in the stored paragraph. What did not change: do not invent a URL, do not add `rel`. | Link to a URL that is not in the published set and not in the packet. Invent an anchor that is a keyword list. Add `rel` on an editorial citation. Add a paid link. Name `/`, `/about`, `/projects`, `/workshop`, or a project slug as the site-wide holder. Card 06. |
| 9. Diagram | The draft. Whether a section is a flow. | One WebP or SVG under `artifacts/{UTC date}/{slug}.webp` or `.svg`, plus one image line and alt text in the local draft. Or a skip receipt. **Superseded 2026-10-01.** Why: the picture was only the words "How it works", so the live diagram did not show the steps or the comparison, and a later pass could insert a second image. What replaced it: still skip when the page has neither a numbered sequence nor a comparison table. When it draws, the SVG shows those steps or those comparison rows. If the page already has the one diagram image, replace its bytes and do not insert a second image. Alt text says what that diagram shows. | Write `content/blog/` or any checkout path. Hotlink Unsplash or any other host. Generate a stock photo. Put a fact only inside the image. Keyword-stuff the alt text. |
| 10. Critic | The assembled markdown and the packet. | A pass receipt, or a fail receipt that lists the checks in §6. | Write the checkout. Add a fact in order to pass. Push. |
| 11. Deliver | A pass receipt, the markdown, and the staged diagram if stage 9 wrote one. | `{checkout}/content/blog/{slug}.md` once. If a diagram was staged, the same bytes at `{checkout}/content/blog/media/{slug}.webp` or `.svg`. `published` and `modified` are the UTC calendar date of this write, and they are equal. A receipt that lists those paths. | Run if the critic did not pass. Overwrite an existing slug. Write outside `content/blog/`. Copy a diagram that is not the staged file. Require `confirmed=true`. Set `waiting_on_aryan` for this write. Mark the campaign `done`. Leave the checkout dirty when the critic failed. |
| 12. Push | The deliver receipt. `git status` limited to the paths on that receipt. | `git add` of those paths only, one commit, `git push` to the config branch with no force. The receipt is the commit SHA. | Force-push. Add any other path. Push a different remote. Amend. Skip hooks. Mark `done` from the SHA alone. Treat the push as proof the public URL is live. |

**POLICY.** A critic failure returns the item to draft for one repair wake. That wake may only remove a sentence, a link, or an image the fail receipt names. It may not add a fact. A second failure sets the item `failed` and does not deliver. No person is asked.

**Superseded 2026-10-01.** Why: the fail receipt named no sentence, so the repair deleted nothing, and Publish one page opened a new campaign instead of waking the page that was already on draft. What replaced it: the one repair wake deletes only the text the fail receipt names. A second failure still marks the item failed and does not deliver. Repair and publish wakes the current chain campaign from its current stage through push. It does not open a new campaign, does not call the planner, and does not call Gemini for a new title. Publish one page stays two model calls, a new campaign, and one new page.

**POLICY.** After a successful push the item's deploy stage is done and the campaign stays `active` until the queue has no pending item. `done` waits on the later public-URL read, because card 04's receipt is the commit and the public HTML URL. The SHA is not that URL.

**POLICY.** One wake does not run two stages and does not start the next queue item. `next_wake_at` stays a sleep. This card does not add an always-on worker. M06.

### Later stages, named only

**POLICY.** These names are reserved. v1 code does not call Search Console, does not patch a live file, and does not open the next campaign from a query.

| Stage | What it will be | What it must not become |
| --- | --- | --- |
| GSC read | Card 05 fields for the one URL, only when a property contains it. | A pass, a fail, or a rank target. A results scrape. |
| Analyse | A note of those fields. Empty stays empty. Card 05. | A decision that a patch caused a change. |
| Patch or leave | Card 06's three-step order on the same URL. A patch may replace bytes of that slug only when gather has a new fact, the gate passes, and the critic passes. `modified` changes only then. Still no confirm on this origin. Still no second URL. | An overwrite of a different question. A delete. A new slug. |
| Next campaign | A new plan from the aim and from named sources, not from a query row. | The `main` planner's proposed pages. Card 07. |

9horsemen is a later sink adapter. It is not a v1 origin, not a v1 config, and not a path the bind stage accepts.

## 6. Critic checklist

Each line is a machine check. A fail blocks deliver. A missing byline, a missing disclosure, a missing image, a missing list, a missing table, and missing `Article` markup are not lines here. Card 02. Card 03.

**POLICY.** Frontmatter matches `blog.ts`, read 2026-09-30: `title`, `question`, `description`, `published`, `modified`, `fill` in `build-log` | `lesson` | `researched`, `source`, `canonical` equal to `/blog/{slug}`. Dates are real `YYYY-MM-DD`. `title` and `question` are the queued question. `description` is the first sentence of that question and adds no word the question did not contain. Card 08. Slug rules in card 09 stand, including the 80-character refusal and no `-2`.

**POLICY.** The direct-answer sentence is present and comes before the problem, the how-it-works section, the diagram, and the closing call to action. Every fact in the body is a span in the packet. The body is not the source file.

**Superseded 2026-09-30.** What replaced that paragraph: the draft writes one plain page of paragraphs from the packet, a claim must be in the packet, the model may use its own words, and ## The problem, ## How it works, and ## Spans are not required. **Superseded 2026-09-30** for the content-word rule in that paragraph. What replaced it: ordinary words are allowed, and a number, a date, a tool name, or a numeric outcome that is not in the spans is refused. **Superseded 2026-09-30** for the fact rule. What replaced it: the page is a reading of the packet in the model's own words. The draft and the critic do not refuse a word, a number, a date, or a name. They still refuse a pasted source and a pipe table of every line. The shape checks stay. The wake, the twelve stages, the receipts, and `next_wake_at` stay.

**POLICY.** Call to action. Either there is none, or every CTA href is the config `mail` or the config `call`, the visible label is `Get in touch`, and a closing instance exists. A thin link may appear only after the direct answer. A CTA before that sentence fails. A third href fails. The heading and the sections remain if the links are ignored.

**Superseded 2026-09-30** for the required sections in that paragraph. What replaced them: the draft writes one plain page of paragraphs from the packet, a claim must be in the packet, the model may use its own words, and ## The problem, ## How it works, and ## Spans are not required. The call to action checks stay. **Superseded 2026-09-30** for the content-word rule in that sentence. What replaced it: ordinary words are allowed, and a number, a date, a tool name, or a numeric outcome that is not in the spans is refused. **Superseded 2026-09-30** for the fact rule. What replaced it: the page is a reading of the packet in the model's own words. The draft and the critic do not refuse a word, a number, a date, or a name. They still refuse a pasted source and a pipe table of every line. The shape checks stay. The wake, the twelve stages, the receipts, and `next_wake_at` stay.

**POLICY.** Links. Every internal href is a canonical path already in the published set, or `/blog/{slug}` for this file. Every external href is a packet URL. Anchors are non-empty. No `rel` on an editorial citation. No paid link.

**Superseded 2026-10-01.** Why: any sentence that contained the letters `rel=` failed, so a real page whose bullet named `rel="nofollow"` was blocked and sent back to draft. What replaced it: a sentence that talks about `rel="sponsored"` or `rel="nofollow"` passes. Fail only a markdown link or an HTML tag that actually carries a `rel` attribute. An external href may be a URL that already appears in the named source file or in a packet span. When a check fails because of a sentence, a link, or an image, that text is named on the receipt remove list.

**POLICY.** Image. Either there is no image, or there is one image whose markdown path is `content/blog/media/{slug}.webp` or `.svg`, the alt text is non-empty and is not a keyword list, and the bytes are the staged artifact from stage 9. An Unsplash host fails. A hotlinked host fails. The critic reads the staged file. It does not require the checkout copy. Deliver is what copies it.

**POLICY.** Spam refusals from card 02, checked as page behavior: cloaking, doorway (including a page that only sends the reader on, and a service-by-suburb or city grid), hidden text, keyword stuffing, link spam, scaled content abuse, scraping (the body is not a republished source), thin affiliation, sneaky redirects, and scam. Machine-generated traffic: this chain does not query Google. Technical floor: the file is markdown the portfolio build turns into HTML. This critic does not fetch the live URL.

**POLICY.** Slug collision. If `content/blog/{slug}.md` exists, deliver fails closed. The bytes stay.

## 7. Image policy

**POLICY.** Default (a). When the how-it-works section is a sequence a diagram would explain, stage one WebP or SVG at `artifacts/{UTC date}/{slug}.webp` or `.svg`. The markdown image path, written into the draft, is `content/blog/media/{slug}.webp` or `.svg`. Deliver copies the staged bytes to that checkout path only after the critic passes. The image sits in that section, not above the direct answer. Alt text says what the diagram shows. The filename is the slug plus the extension. Google's image page lists WebP and SVG among formats in an `img` `src`, and it asks for alt text and a non-generic filename.

**POLICY.** Fallback (c). If no diagram file was supplied with the source, a generated diagram may be written to that same path, under the same alt rule, and only for that section. The packet gains no fact from the picture. A disclosure may be one sentence when a reader would ask how the picture was made. A missing disclosure does not fail the critic. Card 02. The Merchant Center IPTC rule is not applied to this page.

**POLICY.** Unsplash is out. So is any hotlinked stock URL. So is a decorative photo on a page that does not need a picture. A skip receipt is a pass for this stage.

**UNKNOWN.** Whether the portfolio template renders a markdown image. This card does not edit the template. If the build ignores the image line, the words still have to carry every fact. Card 03.

## 8. Librarian rules

**POLICY.** Internal links point only at canonical paths of markdown files already in `content/blog/` on this checkout, other than this slug, and only in a sentence that uses that page. The anchor is that page's question, or a shorter phrase that still names it. Card 07 used the question as the anchor. This card keeps that. Generic anchors ("here", "read more") fail the critic. There is no minimum and no maximum. Card 02. The links page.

**POLICY.** External citations point only at packet URLs, in the sentence that uses the span. The closing citation list repeats those URLs and adds none. No `rel` unless a later card marks the link paid, which this chain does not do.

**POLICY.** The librarian does not add the inbound link on `/`, `/about`, `/projects`, `/workshop`, or a project page. That holder stays **UNKNOWN**. Card 06. A blog page with no internal link is allowed to ship. The links page says a page you care about should have one inbound link. This card does not invent the holder in order to satisfy that sentence. When a second blog file exists, a later item may link to the first. That is the inbound link this chain is allowed to write.

## 9. Automation and safety rails

These rails replace the confirm on portfolio deliver and push. They are the product requirement: fully automated for this origin, v1.

**POLICY.** Site jail. Bind refuses a checkout whose origin URL does not contain `aryanjohari/aryan-portfolio`. `ADA_PORTFOLIO_CHECKOUT` unset, missing, or not a git checkout is a refusal. No home directory is hardcoded. Card 09. 9horsemen is not accepted.

**POLICY.** Gather-only facts. A sentence that is not an account of a packet span fails the critic. External fetch cannot add a URL the plan did not name.

**Superseded 2026-09-30** for the sentence that a fact must be a packet span. What replaced it: the draft writes one plain page of paragraphs from the packet, a claim must be in the packet, the model may use its own words, and ## The problem, ## How it works, and ## Spans are not required. **Superseded 2026-09-30** for the content-word rule in that sentence. What replaced it: ordinary words are allowed, and a number, a date, a tool name, or a numeric outcome that is not in the spans is refused. **Superseded 2026-09-30** for the fact rule. What replaced it: the page is a reading of the packet in the model's own words. The draft and the critic do not refuse a word, a number, a date, or a name. They still refuse a pasted source and a pipe table of every line. The shape checks stay. The wake, the twelve stages, the receipts, and `next_wake_at` stay.

**POLICY.** The critic must pass before deliver. Deliver checks the pass receipt. A model saying the page is fine is not the receipt.

**POLICY.** No overwrite. An existing `content/blog/{slug}.md` blocks deliver. Delete stays `blog_checkout_delete` with `confirmed=true`. After that confirm deletes the file and clears the slug, a later deliver may create the same slug. No second filename. Card 08. Card 09.

**POLICY.** One wake, one stage, one item. The wake writes `next_wake_at` and sleeps. It does not loop stages in one call. It does not emit many pages. Card 07. M06's refusal of an always-on worker stands.

**POLICY.** Audit. Each stage appends a receipt on disk: stage name, campaign id, slug, outcome, and the paths or the commit SHA. Deliver's receipt is the checkout path. Push's receipt is the SHA. A path under `artifacts/` is still not ship proof. Card 09, `is_draft_artifact_receipt`.

**POLICY.** Push jail. `git add` only the paths on the deliver receipt: `content/blog/{slug}.md` and, when deliver copied one, `content/blog/media/{slug}.webp` or `.svg`. The branch is the config branch. The remote is the checkout's origin. No `--force`. No `--no-verify`. No amend. No other repo. A critic failure deletes nothing from a live slug, because deliver has not written one, and it does not leave a new file in the checkout.

**POLICY.** Rate. The existing 24-hour `next_wake_at` in `campaign_page.next_wake_iso` is the sleep this card keeps. A later card may change the interval. This card does not.

**POLICY.** Keywords from Semrush, DataForSEO, or any similar tool may be stored only as a suggestion log on the plan artifact. They are **MARKETING** or **HUNCH**. Copying one into `question` fails plan. Search Console queries stay on the same side of that line. Card 05. Card 07.

## 10. In / out

**In.** This card. The supersession table. The twelve stages. The critic. The image choice. The librarian. The rails that replace confirm. The v1 build order in §14.

**Out.** Product code in this card. A HUD form or a new HUD control. **Superseded 2026-09-30** for one control only: the form and button in §2 replace that sentence. The wake, the twelve stages, the receipts, and `next_wake_at` stay. That control is not the four-step Blog page form. A 9horsemen deploy. Make.com. NotebookLM. Search Console calls. A patch of a live slug. Rank guarantees and impression forecasts. A local service-area campaign. An edit to portfolio `blog.ts`.

## 11. Won't-chase

- A confirm dialog on portfolio deliver or push, and a `waiting_on_aryan` hold whose only job is that yes.
- An automated delete, or an overwrite of an existing slug in v1.
- A force-push, a commit outside `content/blog/`, or a push to any remote but the portfolio origin.
- Unsplash, a hotlinked stock photo, and `og:image` as a block.
- `llms.txt`, chunking, a special AI schema, and a GEO rewrite that adds statistics the packet does not contain.
- A word count, a link count, a 100-word TL;DR, a 1200×630 image, or a 3–5 link quota as a gate.
- A keyword, a Semrush row, or a Search Console query as a title.
- Three campaigns for one page. Card 07.
- City, suburb, and service-area pages on this origin.
- The 0.12 CTR and position-5 gaps. Card 07.
- Marking `done` from a commit SHA or from an `artifacts/` path.
- A daemon that walks the queue in one wake.

## 12. What would prove this wrong

1. Google's AI-features page or optimization guide states that AI Overviews or AI Mode require `llms.txt`, chunking, a special schema type, or a rewrite for the model, where §3 says they do not.
2. Google states that an ordinary editorial citation hurts eligibility, or that `nofollow` is required on every outbound link, where the links page says a citation can help and a normal link needs no `rel`.
3. Google states that using automation makes a page ineligible even when the primary purpose is helping a user.
4. Aggarwal et al. or a later Google page states that the GEO-bench gain is a condition of being indexed or of being shown in AI Overviews.
5. `blog.ts` no longer requires the frontmatter in §6, or `canonical` is not `/blog/{slug}`.
6. A deliver with a failed critic, a wrong origin, or an existing slug still writes `content/blog/{slug}.md`.
7. A push adds a path outside `content/blog/` or uses `--force`.
8. The plan stores a keyword or a Search Console query as `question`.
9. Cards 07–09 are still the rule the series wants for a first portfolio publish, so this supersession should be withdrawn.
10. The portfolio build requires an image, Open Graph tags, or Article schema before a markdown file can ship.

## 13. Source list

Fetched or retrieved 2026-09-30, unless the line says the date lives on an earlier card.

1. Google. "AI features and your website." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/appearance/ai-features
2. Google. "Optimizing your website for generative AI features on Google Search." https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
3. Google. "Link best practices for Google." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/crawling-indexing/links-crawlable
4. Google. "Qualify your outbound links to Google." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links
5. Google. "Google image SEO best practices." Last updated 2026-03-02 UTC. https://developers.google.com/search/docs/appearance/google-images
6. Google. "Spam policies for Google web search." Scaled content abuse. https://developers.google.com/search/docs/essentials/spam-policies
7. Google. "Google Search's guidance on using generative AI content on your website." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
8. Sullivan, Danny, and Chris Nelson. "Google Search's guidance about AI-generated content." Google Search Central Blog, 8 February 2023. https://developers.google.com/search/blog/2023/02/google-search-and-ai-content
9. Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, and Deshpande. "GEO: Generative Engine Optimization." KDD 2024. https://arxiv.org/abs/2311.09735
10. Martinez. "Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization (2023–2026)." arXiv preprint, 15 July 2026. https://arxiv.org/abs/2607.14035
11. Unsplash. "Unsplash API Guidelines." Unsplash Dev, 27 July 2026. https://help.unsplash.com/en/articles/2511245-unsplash-api-guidelines
12. Unsplash. "Guideline: High-quality, Authentic Experiences." Unsplash Dev, 27 July 2026. https://help.unsplash.com/en/articles/2511256-guideline-high-quality-authentic-experiences
13. Repository `aryanjohari/aryan-portfolio`. `src/lib/blog.ts`. https://github.com/aryanjohari/aryan-portfolio/blob/main/src/lib/blog.ts
14. This repo. Cards 01–09. `docs/research/01_how_discovery_works.md` through `docs/research/09_agent_plan.md`. Access date on those cards: 2026-09-29.
15. This repo. `docs/modules/M06_CAMPAIGNS_LONG_HORIZON.md`. Confirm for world-touching stages. Superseded here only for portfolio deliver and push.

**MARKETING**, accessed 2026-09-30. Not ranking rules.

16. Marketing USA. "How to Optimize a Blog Post for SEO." https://marketingusaagency.com/optimize-a-blog-post-for-seo/
17. Verold. "10 Essential On-Page SEO Elements for Blog Posts 2026." https://www.verold.com/on-page-seo-elements-blog-post-2026/
18. Kozec. "SEO Blog Post Structure Best Practices 2026." https://kozec.ai/seo-blog-post-structure-best-practices/
19. Rankai. "How to Optimize a Blog Post in 2026." https://rankai.ai/articles/how-to-optimize-a-blog-post
20. Helping Bloggers. "Blog Post Structure: Intro, Body, and CTA That Converts." https://helping-bloggers.com/blog-post-structure-intro-body-and-cta-that-converts/

## 14. Metal map and v1 build order

Design only. This card changes no Python. Tests for these slices belong under `tests/` and use a temporary checkout. They do not touch a live portfolio checkout. Card 09.

**METAL.** [src/ada/memory/campaign_page.py](../../src/ada/memory/campaign_page.py). `SITE` is `github.com/aryanjohari/aryan-portfolio`. `upsert_campaign_page` refuses any other site, requires one audience sentence, and stores an optional call to action only when both a label and a URL are present. The open-loop shell gets stages `gather`, `gate`, `draft`, `deploy`. The queue, the aims, and the plan artifact are not on that file.

**METAL.** [src/ada/memory/blog_packet.py](../../src/ada/memory/blog_packet.py). `gather_packet` reads the one source path on the row. `gate_packet` refuses a span that is not in that file, a missing field, a bad fill, or an empty researched packet.

**METAL.** [src/ada/memory/blog_draft.py](../../src/ada/memory/blog_draft.py). `compose_markdown` writes the `blog.ts` frontmatter, account prose, a table of spans, and a call-to-action line. `draft_page` calls it with `image=False`. An image line is refused unless a packet span is already a picture path.

**METAL.** [src/ada/memory/blog_slug.py](../../src/ada/memory/blog_slug.py). The slug is one path segment, at most 80 characters, with no truncation and no `-2`.

**METAL.** [src/ada/tools/blog_tools.py](../../src/ada/tools/blog_tools.py). `resolve_portfolio_checkout` refuses an unset, missing, or non-portfolio origin. `blog_checkout_write` returns `needs_confirm` unless `confirmed=true`, and it refuses an existing `content/blog/{slug}.md`. `blog_checkout_delete` has the same confirm gate. Neither function runs git.

**METAL.** [src/ada/tools/toolspec.py](../../src/ada/tools/toolspec.py). `blog_checkout_write` and `blog_checkout_delete` are `side_effect` `confirm`. [src/ada/hud/routes_api.py](../../src/ada/hud/routes_api.py) lists both in `_CONFIRMABLE_TOOLS`. [src/ada/cortex/charter.py](../../src/ada/cortex/charter.py) says the checkout write needs confirm and that `artifact_write` does not perform it. [src/ada/hud/blog_form.py](../../src/ada/hud/blog_form.py) calls the write and delete handlers. This chain does not use that form.

**POLICY.** v1 build order. One slice at a time. A slice does not start until the slice before it has a test.

1. Fixed config reader. Refuse a missing file, a second site, an audience that is not one sentence, and an aim outside `hire` | `prove-shipping` | `educate`. No HUD.
2. Plan artifact. Write the queue YAML from named research-card paths and the aim. Log keyword suggestions off the question field. Do not write the checkout.
3. External fetch into the packet, URLs named on the item only, then the existing gather and gate. A span that is not verbatim still fails.
4. Draft the §5 body from the packet. No new facts. No image yet.
5. Librarian pass. Internal links from the published set. External links from the packet only.
6. Diagram writer. Default path in §7. Skip receipt allowed. Unsplash host refused.
7. Critic. The §6 checks. A fail does not write the checkout.
8. Deliver without confirm, portfolio origin only. Keep the existing overwrite refusal. Leave delete on `confirmed=true`. Update the charter sentence so it matches this split.
9. Push tool. Path jail, no force, receipt is the SHA. Do not mark `done`.
10. Tests for jail, critic fail, existing slug, delete-still-confirms, and push path jail.

Search Console, patch or leave, the next campaign, and the 9horsemen sink stay out of these ten slices.
