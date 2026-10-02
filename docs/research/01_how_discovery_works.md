# 01 — How discovery works

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established). A vendor page selling GEO or AEO would be **MARKETING** and is not used as a ranking rule. None of the sources below are that.

## 1. Question

What do SEO, answer-engine optimization (AEO), and generative-engine optimization (GEO) each actually consume, and which of those needs are the same page?

## 2. Short answer

**POLICY:** This card locks AEO to the answer box (a featured snippet or a People Also Ask box) and GEO to a generated answer that cites sources. Google does not publish either name as a ranking system.

For Google, all three read the same public object: one HTML URL that Googlebot can fetch, render, index, and quote. SEO stores that page and may return it as a ranked link. The answer box lifts a short piece of that page. AI Overviews and AI Mode retrieve indexed, snippet-eligible pages and write a new answer with links back. A second file is not what those surfaces read. The academic GEO result is a later step, inside a generator that already has the page in context. Whether any page on this origin is indexed, extracted, or cited is **UNKNOWN**.

## 3. What each surface reads

### SEO — what the crawler indexes

**EVIDENCE.** Google, [In-depth guide to how Google Search works](https://developers.google.com/search/docs/fundamentals/how-search-works). Google Search crawls, indexes, then serves. Crawling downloads text, images, and videos. There is no central registry of pages: Google discovers a URL from a link on a known page or from a sitemap. Googlebot renders the page and runs JavaScript with a recent Chrome. Indexing analyzes the textual content and tags such as `title` elements and alt attributes, plus images and videos, then clusters duplicates and selects a canonical. Serving searches that index and returns pages by relevance. Relevancy uses hundreds of factors, including the user's location, language, and device. Google does not accept payment to crawl a site more often or to rank it higher, and it does not guarantee that a page will be crawled, indexed, or served.

**EVIDENCE.** Google, [A guide to Google Search ranking systems](https://developers.google.com/search/docs/appearance/ranking-systems-guide). Ranking works on the page. Link analysis, including PageRank, is one core system. Passage ranking identifies sections of a page so Google can judge how relevant that page is. The unit that is ranked is still the page.

**EVIDENCE.** Google, [Myths and facts about crawling](https://developers.google.com/crawling/docs/myths-about-crawling). A page has to be crawled to be in results. Crawl rate itself is not a ranking signal.

**FEASIBLE.** The first site is the portfolio on the existing origin (Next.js on Vercel). That origin can serve a public HTML URL of the kind Googlebot fetches. This card did not check whether any current URL is indexed. That status is **UNKNOWN**.

### AEO — what the answer box extracts

**POLICY.** "AEO" here means Google's featured snippet and the related-questions group (People Also Ask). It does not mean a separate crawler, a schema flag, or a ChatGPT referral program. See the naming note at the end of this section.

**EVIDENCE.** Google Search Help, [How Google's featured snippets work](https://support.google.com/websearch/answer/9351707). A featured snippet is a box that shows a little piece of a website. It can sit at the top of the results, inside People Also Ask, or next to the Knowledge Graph. Google shows it when it judges that people want an answer that fits in a short piece of a website. The piece comes from a website Google has found. Google picks it by how well it answers the question and how helpful it is. Usually there is one box. Feature-specific policies (including consensus on civic, historical, medical, and scientific topics) apply to the snippet. Those policies do not remove the ordinary web listing.

**EVIDENCE.** Google Search Central, [Featured snippets and your website](https://developers.google.com/search/docs/appearance/featured-snippets). A site cannot mark a page as a featured snippet. Google's systems decide whether to elevate it. `nosnippet` blocks featured snippets and regular snippets. A shorter `max-snippet` makes a featured snippet less likely, because the box appears only if enough text can be shown. Google publishes no exact minimum length. A click is sent to the section that was shown, or to the top of the page if the system cannot locate that section.

**EVIDENCE.** Google Search Console Help, [Missing features in Google Search results](https://support.google.com/webmasters/answer/9079920). Featured snippets are chosen by entirely programmatic means. A page owner cannot request one. Some other Search features are explicitly enabled. This one is not.

**EVIDENCE.** Google, ranking-systems guide (same URL as above). If a listing is elevated to a featured snippet, Google does not repeat that listing on the first page of results. MUM is used for some featured-snippet callouts. MUM is not the general ranking system.

**UNKNOWN.** Which heading, list, table, or word count makes a passage more likely to be chosen. Google does not publish that recipe. Agency pages that do are **MARKETING** and are not a ranking rule. This card does not cite them.

**HUNCH.** A short answer that is already visible text on the indexed page is the kind of piece a featured snippet can lift. That is a description of the input, not a prediction that this origin will be chosen.

### GEO — what an AI answer cites

Two consumers show up in primary sources. They are not the same claim.

**Google's own AI answers, which are the consumer for this origin.**

**EVIDENCE.** Google, [AI features and your website](https://developers.google.com/search/docs/appearance/ai-features). AI Overviews and AI Mode show links to supporting pages. Overviews are for getting the gist of a question. AI Mode is for exploration, reasoning, and comparison. Both may use query fan-out: several related searches, then a wider set of links than one classic query. They can use different models, so the links differ. Overviews appear when the systems judge them additive to classic Search, and often do not trigger. To be a supporting link, a page must be indexed and eligible to be shown in Google Search with a snippet. Google states there are no additional technical requirements, and no special schema.org type for these features. The listed fundamentals are the ordinary ones: crawling allowed, the page findable by internal links, important content in text, structured data matching the visible text.

**EVIDENCE.** Google, [Optimizing your website for generative AI features on Google Search](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide). These features sit on the core Search ranking and quality systems. Retrieval-augmented generation (grounding) retrieves pages from the Search index, reviews information from those pages, and shows clickable links. The same guide says a page must be indexed, snippet-eligible, and included in Search generative AI features in Search Console. It also says the names AEO and GEO are common online, and that many suggested hacks are not how Google Search works. Google says it does not use `llms.txt` or other special AI markup, does not require content to be chunked, does not require pages to be rewritten for the model, and does not require a special schema type for generative AI search. Structured data remains a rich-result tool, not a generative-AI requirement.

**EVIDENCE.** Google Search Console Help, [Search generative AI control](https://support.google.com/webmasters/answer/16908024). As of 31 August 2026 the control is rolled out worldwide. It covers AI Overviews, AI Mode, and generative AI features in Discover. The default is include: the site's content may appear as links and may help ground responses. Exclude stops links, grounding, and use of crawled content as an input to those features. The control is not a ranking or inclusion signal for the rest of Search, and it does not change model training. How to operate the report is out of scope for this card.

**EVIDENCE.** Google, [Robots meta tag specifications](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag) (page last updated 2026-03-24 UTC). `nosnippet` applies to web search, Google Images, Discover, AI Overviews, and AI Mode, and it prevents the page from being used as a direct input for AI Overviews and AI Mode. `max-snippet` limits how much text may be used as that direct input. `noindex` drops the page from Search results.

**EVIDENCE.** Google, [List of Google's common crawlers](https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers) (page last updated 2026-07-14 UTC). Crawl preferences for `Googlebot` affect Google Search, including Discover and all Google Search features. `Google-Extended` is a robots.txt token for training future Gemini models and for grounding in Gemini Apps and in Grounding with Google Search on Vertex AI. It does not change inclusion in Google Search and is not a Search ranking signal. It is not the switch for AI Overviews or AI Mode.

**The academic generative engine. This is an experiment, not a Google eligibility rule.**

**EVIDENCE.** Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, and Deshpande, [GEO: Generative Engine Optimization](https://arxiv.org/abs/2311.09735), KDD 2024, DOI `10.1145/3637528.3671900`. They define a generative engine as a search retriever plus language models that write one answer with inline citations. In their benchmark the retriever is Google, limited to the top five results, and the writer is `gpt-3.5-turbo` given those full sources. Visibility is the share of the answer attributed to a citation, adjusted by position. It is not a blue-link rank. On sources already inside that fixed set, adding statistics, quotations, or citations to the source text raised their impression scores; they report a relative gain of up to about 40 percent on position-adjusted word count. Keyword stuffing did not help in that bench. The 40 percent figure is their relative impression change inside that simulator. It is not a traffic forecast for this site, and it is not a statement by Google.

**EVIDENCE.** Martinez, [Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization (2023–2026)](https://arxiv.org/abs/2607.14035), arXiv preprint, 15 July 2026. The survey's reading of that experiment matches the paper's own setup: the gain applies when the source is already in a fixed context. The survey states that this does not establish organic discoverability or a durable traffic effect, and that no technique in the reviewed set shows a stable cross-platform causal effect on discoverability. Treat the survey as a preprint argument, and the experimental limit as Aggarwal et al.'s own method.

**POLICY.** Quotation-and-statistics rewrites stay an experimental finding about citation share after retrieval. They are not a requirement Google states for AI Overviews or AI Mode. Google's optimization guide says rewriting a page just for those systems is unnecessary.

### Naming note

**EVIDENCE.** Watanabe and Nakayashiki (Glasp Inc.), [Disentangling Answer Engine Optimization from Platform Growth](https://arxiv.org/abs/2606.04362), arXiv, 24 August 2026. They use "AEO" for a practice aimed at LLM answer engines such as ChatGPT, and they say it overlaps GEO. Their own placebo test does not establish a causal traffic effect. That paper is a field study by a product company. It is not labeled **MARKETING**, because it is not a sales page, and it is not a ranking rule.

**POLICY.** Later cards keep this card's split: answer box versus generated citation. A preprint that uses AEO for the citation surface is describing the GEO consumer, not a third file.

## 4. What is the same on one page

**EVIDENCE, from the Google pages in §3.** The shared object is one public HTML URL with these properties at once:

- Googlebot can fetch it (robots.txt allows the crawl; the host answers).
- The rendered page contains the facts in text, with a title. Images and video can be indexed too. Text is what a snippet and an AI input quote.
- The URL is indexed, and it is not `noindex`.
- A snippet is allowed (`nosnippet` is absent). That same switch gates the regular snippet, the featured snippet, and use as a direct input to AI Overviews and AI Mode.
- One canonical represents the cluster, so the URL that can be linked is stable.

**Where the three differ on that page:**

- The index stores the page and may rank the page. Passage ranking uses a section to judge the page. The result is a link, plus a short snippet drawn from the page content or, sometimes, the meta description.
- The answer box cuts out a short piece and shows that piece as the answer. It does not write a new paragraph. The owner cannot request the cut. A click can land on the section.
- An AI Overview or AI Mode writes a new answer from several retrieved pages and attaches supporting links. The page is an input and a link. Query fan-out can retrieve a page other than the one that ranks for the original wording. These boxes often do not appear.
- A generator outside Google Search, as in the KDD experiment, cites page text only after some retrieval step has already selected it. **UNKNOWN:** whether any non-Google answer engine requires the Google index. `Google-Extended` does not control those engines, and it does not control AI Overviews.

**FEASIBLE.** One value page on the existing origin can cover the crawler, the answer box, and Google's AI citation, once the sentence a reader should trust is visible HTML on a snippet-eligible URL. There is no `/blog` on that origin. This card does not add one. Facts that exist only in `portfolio.yaml` are invisible to all three until they are in that HTML. This card does not specify how they get there.

**HUNCH.** Separate URLs for "the SEO page," "the answer page," and "the AI page" would fight the canonical clustering Google describes, and they are not a requirement in any source above.

## 5. In / out for this card

**In.** What each surface reads. The naming collision. The conclusion that one public HTML page is the shared object. The places this work does not belong.

**Out.** Google's spam rules, the blocks on the page, the pipeline that fills a page from sources and publishes it, Search Console setup and the measurement loop, reading `portfolio.yaml`, and any new route. Home-assistant organs, the Pi, and an S3 `page.json` are the wrong place for this work: the crawler reads a public URL, and those stores are not that URL.

## 6. Won't-chase

- `llms.txt`, a Markdown twin, or other special AI markup. Google says Search, including its generative features, does not use them.
- Chunking the page for the model, or a special schema type whose purpose is AI Overviews.
- Keyword stuffing. In the KDD bench it did not raise citation share. Google does not list it as a way to be cited.
- Treating added statistics or quotations as a Google eligibility rule.
- Paying for crawl or rank. Google says it does not sell either.
- Vendor GEO or AEO playbooks (**MARKETING**).
- A discovery pipeline whose output lives on an organ, on the Pi, or in S3 `page.json`.

## 7. What would prove this wrong

1. Google documents a file other than the indexed, snippet-eligible HTML page as required for a featured snippet, an AI Overview, or AI Mode.
2. After a recrawl, Google shows a featured snippet, or uses a page as a direct input to AI Overviews or AI Mode, for a URL that is not indexed or that carries `nosnippet`.
3. Google states that AI-feature eligibility requires the KDD rewrite methods (added statistics, quotations, or citations).
4. On this origin, a featured snippet or an AI citation quotes a fact that is absent from the rendered HTML and present only in `portfolio.yaml`, an organ, or an S3 `page.json`.
5. The three surfaces require three different URLs for the same facts.

## 8. Source list

All accessed 2026-09-29.

1. Google. "In-depth guide to how Google Search works." https://developers.google.com/search/docs/fundamentals/how-search-works
2. Google. "A guide to Google Search ranking systems." https://developers.google.com/search/docs/appearance/ranking-systems-guide
3. Google. "Myths and facts about crawling." https://developers.google.com/crawling/docs/myths-about-crawling
4. Google Search Help. "How Google's featured snippets work." https://support.google.com/websearch/answer/9351707
5. Google Search Central. "Featured snippets and your website." https://developers.google.com/search/docs/appearance/featured-snippets
6. Google Search Console Help. "Missing features in Google Search results." https://support.google.com/webmasters/answer/9079920
7. Google. "AI features and your website." https://developers.google.com/search/docs/appearance/ai-features
8. Google. "Optimizing your website for generative AI features on Google Search." https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
9. Google Search Console Help. "Search generative AI control." https://support.google.com/webmasters/answer/16908024
10. Google. "Robots meta tag, data-nosnippet, and X-Robots-Tag specifications." https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
11. Google. "List of Google's common crawlers." https://developers.google.com/crawling/docs/crawlers-fetchers/google-common-crawlers
12. Aggarwal, Murahari, Rajpurohit, Kalyan, Narasimhan, and Deshpande. "GEO: Generative Engine Optimization." KDD 2024. https://arxiv.org/abs/2311.09735
13. Martinez. "Optimizing Visibility in Generative Engines: A Critical Survey of Generative Engine Optimization (2023–2026)." arXiv preprint, 15 July 2026. https://arxiv.org/abs/2607.14035
14. Watanabe and Nakayashiki (Glasp Inc.). "Disentangling Answer Engine Optimization from Platform Growth." arXiv, 24 August 2026. https://arxiv.org/abs/2606.04362
