# 03 — Page blocks

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established). A vendor page about blocks, skyscraper posts, or GEO rewrites would be **MARKETING** and is not used as a ranking rule. None of the sources below are that.

The page is the one public HTML URL locked in card 01. The refusals are the ones locked in card 02. This card does not restate how that URL is crawled, quoted, or cited, and it does not restate the spam rows.

## 1. Question

Which blocks belong on one value page on this origin, which of those blocks Google’s own docs actually name, and which blocks are only our fixed delivery structure?

## 2. Short answer

**POLICY:** The fixed page is one HTML URL. In the head: a `<title>`, then one self-referential canonical for this URL. In the body, in this order: one main heading; a visible published date, and a visible modified date after a significant update; the sentence a reader should be able to trust; then sections that hold the rest. A list is the shape of a section when the facts are a sequence. A table is the shape of a section when the facts are a comparison. An image sits beside the words it explains, when the text needs one. An internal link, and an external citation, sit in the sentence that uses them. A byline and an automation disclosure are on the page when a reader of that page would expect them. A call to action may close the page. The page is still the useful page if the reader never follows it. Which of those passages a snippet or a generated answer quotes is **UNKNOWN**.

## 3. Block list

| Block | What it contains | Tag | Source |
| --- | --- | --- | --- |
| Title | The `<title>` text for this URL: specific to the page, and a concise description of it. Google says every page should have one and lists it among title-link sources. Google states no length limit. The title link in results can be truncated to the device, and Google may use other text on the page. | EVIDENCE | Google, "Influencing your title links in search results." https://developers.google.com/search/docs/appearance/title-link |
| Main heading | One visible heading that states the page and is distinct from the other headings. Google lists heading elements among title-link sources. Search Essentials names the main heading as a prominent place for the words people use. The starter guide says heading order does not matter for Search, and that there is no ideal heading count. | EVIDENCE | Google, "Influencing your title links in search results." https://developers.google.com/search/docs/appearance/title-link ; Google, "Google Search Essentials." https://developers.google.com/search/docs/essentials ; Google, "Search Engine Optimization (SEO) Starter Guide." https://developers.google.com/search/docs/fundamentals/seo-starter-guide |
| Direct answer | The sentence a reader should be able to trust, in the visible body, before the sections. Card 01 locked visible text as what a snippet and an AI input quote. Google does not name this block. Which passage is quoted is **UNKNOWN**. | POLICY | our structure |
| Sections | The rest of the page, in paragraphs under headings, so a reader can move through it. | EVIDENCE | Google, "Search Engine Optimization (SEO) Starter Guide." https://developers.google.com/search/docs/fundamentals/seo-starter-guide |
| List | A visible sequence inside a section, when the facts are a sequence. It is not a block on every fill of the page. Google's featured-snippet page does not name a list as the piece it lifts. Whether a list is chosen is **UNKNOWN**. | POLICY | our structure |
| Table | A visible comparison inside a section, when the facts are a comparison. It is not a block on every fill of the page. Whether a table is chosen is **UNKNOWN**. | POLICY | our structure |
| Image | A picture the section needs, in an `img` element (or a `picture` with an `img` fallback), near the text it explains, with alt text that describes that picture. Absent when the page has no such picture. Google states no image count. | EVIDENCE | Google, "Google image SEO best practices." https://developers.google.com/search/docs/appearance/google-images |
| Internal link | A crawlable `<a href>` to another page on this origin, with anchor text that says what that page is, in the sentence that needs it. Google says there is no ideal number of links on a page. A page this origin cares about also needs a link from at least one other page on the origin. That inbound link is how the page is found. It is not a count of links in this body. | EVIDENCE | Google, "Link best practices for Google." https://developers.google.com/search/docs/crawling-indexing/links-crawlable |
| External citation | A crawlable link to the source this page is using, with anchor text that says what that source is, when the page draws on it. A build log may have none. An ordinary editorial link needs no `rel`, as card 02 locked. | EVIDENCE | Google, "Link best practices for Google." https://developers.google.com/search/docs/crawling-indexing/links-crawlable |
| Canonical | One absolute `rel="canonical"` in the head, pointing at this URL, including on this URL itself. Google calls that annotation a strong signal and says specifying a canonical is not required. If the site states none, Google picks one. | EVIDENCE | Google, "How to specify a canonical URL with rel=\"canonical\" and other methods." https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls |
| Published date | A visible, labeled date for when this page was first published. It is the page's date: not a future date, and not the date of an event the page describes. Google may use a prominent visible date as one factor when it estimates a byline date for results. Google does not guarantee that date is shown. Supplying a date is not, on that page, a condition of indexing. | EVIDENCE | Google, "Influence your byline dates in Google Search." https://developers.google.com/search/docs/appearance/publication-dates |
| Modified date | A visible, labeled date for a significant update, shown so a reader can tell it from the published date. It changes when the page substantially changes. The byline-date page says a last-updated date can be provided. The people-first page warns against changing a date so the page seems fresh when the content has not substantially changed. | EVIDENCE | Google, "Influence your byline dates in Google Search." https://developers.google.com/search/docs/appearance/publication-dates ; Google, "Creating helpful, reliable, people-first content." https://developers.google.com/search/docs/fundamentals/creating-helpful-content |
| Byline | The name of the person or organization who made the page, where a reader would expect to see who made it. Card 02 locked a missing byline as not a refusal. | EVIDENCE | Google, "Creating helpful, reliable, people-first content." https://developers.google.com/search/docs/fundamentals/creating-helpful-content |
| Automation disclosure | A short account of how automation was used, where a reader would ask how the page was made. Card 02 locked a missing disclosure as not a refusal, and locked automation alone as not spam. | EVIDENCE | Google, "Creating helpful, reliable, people-first content." https://developers.google.com/search/docs/fundamentals/creating-helpful-content |
| Call to action | An optional closing link. The heading, the sentence, and the sections are the page for a reader who never uses the link. | POLICY | our structure |

## 4. What is required for the page to be the card-01 object, versus what is our structure

**EVIDENCE.** Google, "Google Search Essentials," https://developers.google.com/search/docs/essentials, accessed 2026-09-29 (page last updated 2025-12-10 UTC). The best-practice list names the title, the main heading, alt text, and link text, and it says to make links crawlable and to follow the image and structured-data guides. Card 02 already locked those as outside the eligibility floor.

**EVIDENCE.** Google, "Search Engine Optimization (SEO) Starter Guide," https://developers.google.com/search/docs/fundamentals/seo-starter-guide, accessed 2026-09-29 (page last updated 2025-12-10 UTC). Break long content into paragraphs and sections, and provide headings, so a reader can follow the page. From Google Search's perspective, heading order does not matter. There is no ideal number of headings.

**EVIDENCE.** Google, "Control your snippets in search results," https://developers.google.com/search/docs/appearance/snippet, accessed 2026-09-29. A snippet is created from the page content. Google sometimes uses the meta description when that element describes the page better than the body. The sentence in §3 is our place for the claim a reader should trust. It is not a format Google says it will select.

**EVIDENCE.** Google, "Featured snippets and your website," https://developers.google.com/search/docs/appearance/featured-snippets, accessed 2026-09-29. A site cannot mark a page as a featured snippet. The page does not name a list, a table, or a word count as the piece that is lifted. Card 01 left that choice **UNKNOWN**. This card leaves it **UNKNOWN**.

**EVIDENCE.** Google, "AI features and your website," https://developers.google.com/search/docs/appearance/ai-features, accessed 2026-09-29 (page last updated 2025-12-10 UTC). Important content is available as text. Images and video support that text when they apply. Structured data matches the visible text. There is no special schema.org type for AI Overviews or AI Mode. Card 01 locked that. This card does not add one.

**EVIDENCE.** Google, "Article (`Article`, `NewsArticle`, `BlogPosting`) structured data," https://developers.google.com/search/docs/appearance/structured-data/article, accessed 2026-09-29 (page last updated 2026-09-08 UTC). There are no required properties. `headline`, `author`, `datePublished`, `dateModified`, and `image` are recommended when they apply. The page says the markup can help Google show title text, images, and dates. It does not say the markup is a condition of indexing.

**EVIDENCE.** Google, "General structured data guidelines," https://developers.google.com/search/docs/appearance/structured-data/sd-policies, accessed 2026-09-29. Markup has to represent content the reader can see. A structured-data manual action removes rich-result eligibility. On that page's wording, it does not change how the page ranks in web search. Google does not guarantee a rich result.

**EVIDENCE.** Google, "Creating helpful, reliable, people-first content," https://developers.google.com/search/docs/fundamentals/creating-helpful-content, accessed 2026-09-29 (page last updated 2025-12-10 UTC). The page asks whether the main heading or page title is a descriptive summary, whether sourcing is clear when the page draws on other sources, whether a byline is present where a reader would expect one, and whether automation is evident where a reader would ask how the page was made. Those are self-assessment questions. Card 02 already locked them as not publish cutoffs. The same page says Google has no preferred word count.

**POLICY.** To be the card-01 object, this page needs the properties card 01 already named: one public HTML URL, the facts in visible text, a title, and one canonical URL for the cluster. Snippet eligibility stays the card-01 switch. The three technical conditions stay the card-02 floor. This card adds no third eligibility test.

**POLICY.** Our structure is the order and the optional slots in §3. The sentence a reader should trust, the sections, a list or a table as the shape of a section, an image only when the text needs one, links only in the sentence that needs them, a byline and a disclosure only when a reader of that page would expect them, and an optional call to action. Google names the title, the main heading, sections, the image, the links, the canonical, the dates, the byline, and the disclosure. The order, the direct-answer slot, the list, the table, and the call to action are this page's delivery shape.

**POLICY.** A published date and a modified date are on the page so a reader, and Google's byline-date estimate, can see when the page appeared and when it last changed in substance. If `Article` markup is added, `datePublished`, `dateModified`, `headline`, `author`, and `image` repeat those visible fields and add none the body lacks. Markup is not a block in §3.

**POLICY.** A build log, a lesson, and a researched article are three fills of this same page. This card defines the page. It does not define how the facts are gathered.

**FEASIBLE.** The existing portfolio origin can serve this HTML page. This card does not add `/blog` and does not read `portfolio.yaml`.

**HUNCH.** One shape for those three fills follows from card 01's single URL. It is not a measurement that this order is the passage Google will quote.

**UNKNOWN.** Whether any current URL on the origin already has these blocks. Whether Google will index the page, quote it, show a byline date, or show a rich result.

## 5. What this page must not do

Each line is one card-02 refusal. A self-assessment question in §4 is not a refusal.

**POLICY.** Doorway. The call to action is an optional slot. A reader who never follows it still has the heading, the sentence, and the sections. This card adds no set of similar URLs and no `/blog`.

**POLICY.** Hidden text. The sentence and the sections are in the body a visitor can read. The canonical is a `link` in the head, and structured data may repeat visible text. Those are not the hidden-text examples card 02 lists. A fact that exists only in markup, or only where a visitor cannot easily see it, is not this page. Accordion, tab, slideshow, tooltip, and screen-reader text stay allowed, as card 02 locked.

**POLICY.** Keyword stuffing. The title, the main heading, the alt text, and the anchor text say what this page is and what the link target is. They are not a repeated phrase, and they are not a list of places or numbers written to be ranked for. Card 02 states no repetition count. This card adds none.

**POLICY.** Scaled content abuse and scraping. Each fill is this page's own account: a build log, a lesson, or a researched article. A republished page, a slight or automated rewrite of someone else's page, a copied feed, or a stitched page is the card-02 refusal. Producing many such pages in order to be ranked is the same refusal. This card does not say how the facts were gathered, and it states no page count.

**POLICY.** Thin affiliation. The page's descriptions are its own. A call to action does not replace that account. If an outbound link is paid, card 02 already requires `rel="sponsored"` or `rel="nofollow"`. An ordinary citation needs no `rel`. This origin is not assumed to be an affiliate site.

## 6. In / out for this card

**In.** The blocks on one value page. Which of those Google's docs name. Which are the fixed shape of this page. The five card-02 refusals those blocks must not match: doorway, hidden text, stuffing, scaled or scraped pages, and thin affiliation.

**Out.** How a build log, a lesson, or a researched article is researched. The pipeline that fills a page and publishes it. Search Console and the measurement loop. A new route, including `/blog`. Reading `portfolio.yaml`. Home-assistant organs, the Pi, and an S3 `page.json`.

## 7. Won't-chase

- A word count, a link count, an image count, a heading count, or a character count for the title. The pages this card used state no such cutoff. The title-link page says there is no limit on the `<title>` element, and that the title link is truncated to fit the device.
- A claim that a list or a table is the passage a snippet lifts, or that a table ranks better. Card 01 left the choice **UNKNOWN**.
- FAQ schema, or any special schema, as a requirement for AI Overviews or AI Mode. The AI-features page says there is no such type. `Article` markup is a rich-result aid with no required properties. It is not an indexing condition.
- A byline, an automation disclosure, a visible date, or an image as a publish cutoff.
- A Core Web Vitals score, or E-E-A-T as a pass. Card 02 locked both.
- A meta description as a block on this page. The snippet page says the snippet is primarily the page content, and sometimes the meta description.
- `og:title` and `WebSite` structured data as blocks. The title-link page lists them among title-link sources. They are not the card-01 object.
- Google News rules for date and time placement. This page is a value page on the portfolio origin.
- Vendor block kits, skyscraper outlines, and GEO rewrites (**MARKETING**).

## 8. What would prove this wrong

1. Google states that indexing, a snippet, or an AI Overview requires a list, a table, a word count, a link count, an image count, or a heading count.
2. Google states that a page is ineligible to be indexed, snippet-eligible, or cited without a byline, an automation disclosure, a visible date, an image, or `Article` structured data.
3. Google states that a special schema type is required for AI Overviews or AI Mode.
4. Google states that a page whose only useful act is sending the reader onward is outside the doorway row.
5. On this origin, a featured snippet or an AI citation quotes a fact that is absent from the visible HTML.
6. Google states that a self-referential canonical is required before a page can be indexed.

## 9. Source list

All accessed 2026-09-29.

1. Google. "Google Search Essentials." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/essentials
2. Google. "Search Engine Optimization (SEO) Starter Guide." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/fundamentals/seo-starter-guide
3. Google. "Influencing your title links in search results." https://developers.google.com/search/docs/appearance/title-link
4. Google. "Control your snippets in search results." https://developers.google.com/search/docs/appearance/snippet
5. Google. "Featured snippets and your website." https://developers.google.com/search/docs/appearance/featured-snippets
6. Google. "Link best practices for Google." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/crawling-indexing/links-crawlable
7. Google. "Google image SEO best practices." https://developers.google.com/search/docs/appearance/google-images
8. Google. "How to specify a canonical URL with rel=\"canonical\" and other methods." Last updated 2026-07-10 UTC. https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
9. Google. "Influence your byline dates in Google Search." https://developers.google.com/search/docs/appearance/publication-dates
10. Google. "Article (`Article`, `NewsArticle`, `BlogPosting`) structured data." Last updated 2026-09-08 UTC. https://developers.google.com/search/docs/appearance/structured-data/article
11. Google. "General structured data guidelines." https://developers.google.com/search/docs/appearance/structured-data/sd-policies
12. Google. "Creating helpful, reliable, people-first content." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/fundamentals/creating-helpful-content
13. Google. "AI features and your website." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/appearance/ai-features
