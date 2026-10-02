# 02 — Google page rules

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established). A vendor page selling a spam checker would be **MARKETING** and is not used as a ranking rule. None of the sources below are that.

The object these rules judge is the one public HTML URL locked in card 01. This card does not restate how that URL is crawled, quoted, or cited.

## 1. Question

What do Google’s own published Search Essentials and spam policies require of one public HTML page, and which failures must make a later pipeline refuse to publish?

## 2. Short answer

Google’s eligibility floor for that page is three technical conditions: Googlebot is not blocked, the response is HTTP 200, and the page has indexable content. Indexable content means text in a supported type, and HTML is one, that does not violate the spam policies. Meeting the floor does not guarantee indexing. The spam policies then name page behaviors, including cloaking, doorway pages, hidden text, scaled content abuse, scraping, and thin affiliation, that can lower a ranking or omit a page or a site. A later pipeline must refuse a publish that matches one of those behaviors. People-first writing, E-E-A-T, and page experience describe what Google’s systems seek to reward. They are not a scored pass, and Google states no word-count, link-count, or page-count cutoff.

## 3. What Google requires of a page

**EVIDENCE.** Google, [Google Search Essentials](https://developers.google.com/search/docs/essentials) (page last updated 2025-12-10 UTC). Search Essentials has three parts: technical requirements (what a page needs in order to be shown), spam policies (behaviors that can lower a ranking or omit a page or a site), and key best practices (practices that can improve how a site appears). Appearing in Search costs nothing. A page that meets the requirements and the best practices may still not be crawled, indexed, or served.

**EVIDENCE.** Google, [Google Search technical requirements](https://developers.google.com/search/docs/essentials/technical) (page last updated 2025-12-18 UTC). A page is eligible to be indexed when three things are true. Googlebot is not blocked: Google indexes pages that are public and that do not block the crawler; a page that requires a login is not crawled, and a mechanism that blocks indexing keeps the page out of the index. The page works: Google indexes a page served with HTTP `200 (success)`, and it does not index client or server error pages. The page has indexable content: the textual content is in a file type Google Search supports, and the content does not violate the spam policies. Meeting the three conditions does not mean the page will be indexed.

**EVIDENCE.** Google, [File types indexable by Google](https://developers.google.com/search/docs/crawling-indexing/indexable-file-types) (page last updated 2026-02-03 UTC). The file type is taken from the `Content-Type` header. HTML (`.htm`, `.html`, and other extensions) is a supported flat file type. This is the type card 01 already fixed as the object. The rest of that file-type list is not a requirement for this page.

**EVIDENCE.** Google, [Spam policies for Google web search](https://developers.google.com/search/docs/essentials/spam-policies) (page last updated 2026-08-28 UTC). Spam, in Google’s wording, is techniques used to deceive users or to manipulate Search into featuring content prominently. The same sentence includes attempts to manipulate rankings and attempts to manipulate generative AI responses in Google Search. To be eligible for Google web search, a page must not violate Google Search’s overall policies or the spam policies on that page. The policies apply to all web results, including Google’s own properties. Detection is automated, and human review can add a manual action. A violating site may rank lower or not appear. The page says its list covers common spam, and that Google may act on other spam it detects.

**EVIDENCE.** Google Search Help, [Content policies for Google Search](https://support.google.com/websearch/answer/10622781), the page the spam policies cite as those overall policies. The overall content policies apply to web results. They cover child sexual abuse material, certain highly personal information (including doxxing, explicit personal images, and involuntary fake pornography), spam, removals a site owner requests, and valid legal requests such as a DMCA notice. A separate group, search-feature policies, is stated not to apply to web results.

**HUNCH.** The spam page’s phrase “overall policies” means that overall group, because the feature group says it does not govern web results. This card does not turn a feature-only policy into a reason to drop the ordinary HTML page.

**EVIDENCE.** Google, [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) (page last updated 2025-12-10 UTC). Search Essentials lists this as a key best practice. The page says ranking systems are designed to prioritize helpful, reliable information created for people, rather than content created to manipulate rankings. It offers self-assessment questions about originality, a descriptive title and main heading, sourcing, and care. It says E-E-A-T (experience, expertise, authoritativeness, and trustworthiness) is not itself a specific ranking factor. Trust matters most. The other three contribute to trust, and a page does not have to show all of them. Systems give more weight to strong E-E-A-T on topics that can significantly affect health, financial stability, safety, or the welfare of society (Your Money or Your Life). The page asks creators to be clear about who made the content, how it was made, and why. It strongly encourages an accurate byline where a reader would expect one. It says to consider an automation disclosure where a reader would ask how the content was made. On word count, the page’s own answer is that Google does not have a preferred word count.

**EVIDENCE.** Google Search Central Blog, Danny Sullivan and Chris Nelson, [Google Search's guidance about AI-generated content](https://developers.google.com/search/blog/2023/02/google-search-and-ai-content), 8 February 2023. The people-first page cites this post. Appropriate use of AI or automation is not against the guidelines. Using automation, including AI, to generate content whose primary purpose is manipulating rankings is a violation of the spam policies. Using AI gives a page no special gain. A byline is worth adding where a reader would ask who wrote it, not as a rule for every page. A disclosure is worth adding where a reader would ask how it was made. Listing AI as the author is not the way the post says to make that role clear.

**EVIDENCE.** Google, [Understanding page experience in Google Search results](https://developers.google.com/search/docs/appearance/page-experience) (page last updated 2026-09-22 UTC). The people-first page cites this for the advice behind “a great page experience.” Core ranking systems look to reward a good page experience. There is no single page-experience signal. Core Web Vitals are used by ranking systems. Other page-experience aspects do not directly raise ranking. Search still seeks to show the most relevant content when the page experience is sub-par. The page states no Core Web Vitals number.

**EVIDENCE.** The same Search Essentials page. The other key best practices are: use words people would use, in prominent places such as the title, the main heading, alt text, and link text; make links crawlable; tell people about the site; follow the specific guides for images, video, structured data, and JavaScript; enable appearance features that fit the site; use the controls for content that should not be in results. Those are practices that can affect appearance. They are not the eligibility floor, and they are not spam headings. A later card names blocks. This card does not.

**POLICY.** The later pipeline must refuse a publish that is not HTTP 200, or whose textual content is not in a type the file-type page lists. HTML qualifies. This enforces the technical-requirements page. Card 01 already locked the fetch and snippet switches. This card does not add a second crawl rule.

**POLICY.** The pipeline must not refuse a page for length, for a link count, for a Core Web Vitals score, for a missing byline, or for a missing AI disclosure. Google states no such cutoff, and it says E-E-A-T is not a ranking factor. A byline or a disclosure stays a judgment about what a reader of that page would expect.

**POLICY.** The pipeline must not treat the use of automation or AI, by itself, as spam. The violation Google states is primary purpose: producing the content to manipulate rankings.

**POLICY.** The pipeline must not invent a test for spam the spam page does not name. Google says it may act on other spam it detects. What that unnamed practice is, is **UNKNOWN**.

**FEASIBLE.** The existing portfolio origin can serve one public HTML URL with HTTP 200. This card did not measure that origin’s status codes or compare its HTML to the spam rows. Whether any current URL is indexed, or would be treated as spam, is **UNKNOWN**.

## 4. What Google calls spam or abuse

**EVIDENCE.** Each row is a heading on [Spam policies for Google web search](https://developers.google.com/search/docs/essentials/spam-policies) (page last updated 2026-08-28 UTC). The behavior cell is the page behavior that heading describes. There is no heading titled “thin content.” Low-value mass pages are scaled content abuse. Copied pages are scraping. Affiliate copies are thin affiliation.

| Name | URL | Page behavior that matches it |
| --- | --- | --- |
| Cloaking | https://developers.google.com/search/docs/essentials/spam-policies#cloaking | The server shows users and search engines different content in order to manipulate rankings and mislead users. Examples: a travel page for the crawler and a different page for the user; keywords inserted only when the user agent is a search engine. A paywall is not cloaking when Google sees the same full content a person with access sees, and the site follows Google’s flexible-sampling guidance. Making JavaScript or images accessible is not cloaking. |
| Doorway abuse | https://developers.google.com/search/docs/essentials/spam-policies#doorways | Pages or sites exist to rank for specific, similar queries and send people to an intermediate page that is less useful than the destination. Examples: many near-duplicate sites; city or region pages that funnel to one page; generated pages whose job is to funnel; substantially similar pages that stand in for a browseable hierarchy. |
| Expired domain abuse | https://developers.google.com/search/docs/essentials/spam-policies#expired-domains | An expired domain is bought and reused mainly to manipulate rankings, with content of little or no value to users. The examples are a change of purpose on the old domain, such as commercial content on a former public or charity site. |
| Hacked content | https://developers.google.com/search/docs/essentials/spam-policies#hacked-content | Content is placed on the site without the owner’s permission. Examples: malicious code injected into pages; new spam or phishing pages; hidden links or hidden text added so crawlers see them; redirects that depend on referrer, user agent, or device. |
| Hidden text and link abuse | https://developers.google.com/search/docs/essentials/spam-policies#hidden-text-and-links | Content is placed so a search engine can use it and a visitor cannot easily see it, solely to manipulate rankings. Examples: white text on white, text behind an image, CSS off-screen, font size or opacity 0, a link on one small character. Accordion or tabbed content, a slideshow, a tooltip, and text for screen readers are not violations. |
| Keyword stuffing | https://developers.google.com/search/docs/essentials/spam-policies#keyword-stuffing | The page is filled with keywords or numbers to manipulate rankings. They often appear in a list, unnaturally, or out of context. Examples: phone-number lists with no added value; blocks of cities and regions the page is trying to rank for; the same phrase repeated until it sounds unnatural. Google states no repetition count. |
| Link spam | https://developers.google.com/search/docs/essentials/spam-policies#link-spam | Links to or from a site are created mainly to manipulate rankings. Examples include buying or selling links for rank, excessive link exchange, automated link creation, a link required by contract with no choice to qualify it, advertisements that pass ranking credit, and advertorials with ranking credit or optimized anchors. Google says paid links are allowed when the `<a>` tag uses `rel="nofollow"` or `rel="sponsored"`. Also in this heading: low-value content created mainly to manipulate linking signals. |
| Machine-generated traffic | https://developers.google.com/search/docs/essentials/spam-policies#machine-generated-traffic | Automated queries are sent to Google, including scraping results to check rank, without express permission. This is traffic to Google, not a property of the HTML page. It also violates the Google Terms of Service. |
| Malicious practices | https://developers.google.com/search/docs/essentials/spam-policies#malicious-practices | The page creates a harmful or deceptive outcome. Examples: malware; unwanted software that changes browser settings or leaks private information without disclosure; back-button hijacking. |
| Misleading functionality | https://developers.google.com/search/docs/essentials/spam-policies#misleading-functionality | The site intentionally pretends a visitor can use a function or service that it does not provide. Examples: a fake generator; a claimed tool that leads to ads instead of the tool. |
| Scaled content abuse | https://developers.google.com/search/docs/essentials/spam-policies#scaled-content | Many pages are generated primarily to manipulate rankings and not to help users. The focus is a large amount of unoriginal content with little or no value, however it is produced. Examples: generative AI or similar tools used to make many pages without added value; scraping or copying feeds or results, including synonymizing, translating, or other obfuscation, with little value; stitching pages together without added value; many sites used to hide the scale; many pages that make little sense to a reader but contain search keywords. Google says to exclude such content from Search. Google states no count for “many.” |
| Scraping | https://developers.google.com/search/docs/essentials/spam-policies#scraped-content | Content is taken from other sites, often automatically, and hosted to manipulate rankings. Examples: republishing with no original content or value, and without citing the source; copying and changing it only slightly, including by synonyms or automation; reproducing a feed with no unique benefit; a site that embeds or compiles others’ videos, images, or media without substantial added value. |
| Site reputation policy | https://developers.google.com/search/docs/essentials/spam-policies#site-reputation | Third-party content is published on a host mainly to use ranking signals the host earned with its own content. Third-party content alone is not a violation. Examples that conflict with the policy: a sponsored page written by an outside party and distributed to many sites; a low-quality third-party advertising page that is not part of the host site. News syndication, forums, editorial columns, and affiliate links treated appropriately are listed as not inconsistent. Outside the EEA, the relevant pages may get a manual action. Inside the EEA, they may be ranked apart from the main domain and are not subject to that manual action. |
| Sneaky redirects | https://developers.google.com/search/docs/essentials/spam-policies#sneaky-redirects | A visitor is sent to a different URL in order to show users and engines different content, or to show users something that does not meet the request. Examples: the crawler sees one type of content and users are redirected to something significantly different; desktop users see a normal page and mobile users are sent to a spam domain. A move to a new address, merging pages, or a redirect after login is not this heading. |
| Thin affiliation | https://developers.google.com/search/docs/essentials/spam-policies#thin-affiliate-pages | Product descriptions and reviews are copied from the merchant, with affiliate links and no original content or added value. The same pattern includes a template repeated across affiliates, on one site or across domains or languages. A page that adds its own information, such as price detail, original reviews, testing, or comparison, is not this heading. |
| User-generated spam | https://developers.google.com/search/docs/essentials/spam-policies#user-generated-spam | Visitors add spam through a channel meant for their content. Examples: spam accounts on an open host, spam forum posts, comment spam, spam files on a file host. |
| Legal removals | https://developers.google.com/search/docs/essentials/spam-policies#copyright-removal-requests | A significant volume of valid copyright removals can be used to demote other content from that site. Google applies similar demotion for defamation, counterfeit goods, and court-ordered removals. Child sexual abuse material is removed when identified, and a site with a significant proportion of it is demoted. Google states no volume and no proportion. |
| Personal information removals | https://developers.google.com/search/docs/essentials/spam-policies#online-harassment-removals | A significant volume of personal-information removals, on a site with exploitative removal practices, can demote other content from that site. Similar demotion may follow a significant volume of removals for doxxing, explicit personal imagery without consent, or explicit non-consensual fake content. Google states no volume. |
| Policy circumvention | https://developers.google.com/search/docs/essentials/spam-policies#policy-circumvension | The site keeps acting to bypass spam or content policies. Examples: a new subdomain, subdirectory, or site used to continue a violation; other methods used to keep distributing the same violating content. Google may then restrict features or remove more of the site. The anchor on the live page is spelled `policy-circumvension`. |
| Scam and fraud | https://developers.google.com/search/docs/essentials/spam-policies#scam-and-fraud | The page impersonates a business or service, shows false information about one, or draws users in on false pretenses. Examples: impersonation in order to take payment; a fake customer-support site or fake contact details. |

**EVIDENCE.** Google, [Qualify your outbound links to Google](https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links) (page last updated 2025-12-10 UTC). The link-spam row cites this page. `rel="sponsored"` marks advertisements and paid placements. `rel="nofollow"` is for the other cases where the site does not want Google to associate it with the target, or to crawl that target from the page. `rel="ugc"` is recommended for links in user-generated content such as comments and forum posts. A normal editorial link needs no `rel`. These attributes are not a ranking-credit switch the spam page applies to every link. The spam page’s own allowance for paid links is `rel="nofollow"` or `rel="sponsored"`.

## 5. What a later pipeline must refuse

Each line enforces one row in §4. A self-assessment question in §3 is not a refusal.

**POLICY.** Cloaking. Refuse a publish that serves a crawler different page content from the content a person receives, in order to manipulate rankings or mislead. Do not treat accessible JavaScript, accessible images, or a paywall that shows Google the same full content as this row.

**POLICY.** Doorway abuse. Refuse a page built to rank for a query and pass the person on, and refuse a set of substantially similar pages that stand in for a hierarchy. This card adds no such URL and no `/blog`.

**POLICY.** Expired domain abuse. Refuse to publish this page onto an expired domain bought so the content can use that domain’s old ranking. On the existing portfolio origin this is a target check, not a check of the sentences.

**POLICY.** Hacked content. Refuse HTML that contains code, extra pages, hidden links, or redirects the pipeline did not generate.

**POLICY.** Hidden text and link abuse. Refuse text or links that exist for a crawler and not for a visitor, in the ways that row lists. Accordion, tab, slideshow, tooltip, and screen-reader text stay allowed for a later block card.

**POLICY.** Keyword stuffing. Refuse a page filled with repeated phrases, or with city, region, or number lists, in order to manipulate rankings. There is no repetition count to enforce.

**POLICY.** Link spam. Refuse links that are bought, sold, exchanged, or required in order to pass ranking credit, and refuse a page created to manufacture those signals. A paid link may be published only with `rel="sponsored"` or `rel="nofollow"`. An ordinary editorial link needs no `rel`. There is no link count to enforce.

**POLICY.** Machine-generated traffic. Refuse any publish step that sends automated queries to Google, including a results scrape used to check rank. The HTML of the page is not what this row judges.

**POLICY.** Malicious practices. Refuse malware, unwanted software, and a page that hijacks the back button.

**POLICY.** Misleading functionality. Refuse a page that claims a function or service it does not perform, including a claimed tool that leads to ads instead.

**POLICY.** Scaled content abuse. Refuse a page, or a set of pages, whose primary purpose is manipulating rankings and that adds little or no value for a user. That includes generative-AI output, scraped or stitched copy, and keyword pages that make little sense, when that is the purpose. Do not refuse a page only because AI or automation helped write it. There is no page count to enforce. How many pages Google treats as “many” is **UNKNOWN**.

**POLICY.** Scraping. Refuse a page that republishes another site’s content without original value, a slight or automated rewrite, a copied feed, or a compilation of someone else’s media without substantial added value.

**POLICY.** Site reputation. Refuse third-party content placed on this origin mainly to borrow the origin’s ranking signals. The owner’s own page on the portfolio origin is not this row.

**POLICY.** Sneaky redirects. Refuse a URL that shows a crawler one page and sends a person to significantly different content, including a mobile-only redirect to another spam domain. An address move, a merge of pages, or a redirect after login is not this row.

**POLICY.** Thin affiliation. Refuse an affiliate page whose descriptions or reviews are copied from the merchant, or the same affiliate template repeated with no added value. A page with its own information is not this row. This origin is not assumed to be an affiliate site.

**POLICY.** User-generated spam. If the published page has a channel for visitor text, files, or links, refuse spam in that channel. This card adds no such channel. `rel="ugc"` stays a recommendation on those links, not an extra spam heading.

**POLICY.** Legal removals. Refuse child sexual abuse material. Refuse a copied page that the scraping row already refuses. A demotion after “a significant volume” of legal removals has no published count. That count is **UNKNOWN**.

**POLICY.** Personal information removals. Refuse doxxing, explicit personal imagery shared without consent, and explicit non-consensual fake content. The volume that triggers a wider demotion is **UNKNOWN**.

**POLICY.** Policy circumvention. Refuse a new URL, subdirectory, or site whose purpose is to continue a violation from another row.

**POLICY.** Scam and fraud. Refuse a page that impersonates a business or service, states false information about one, or draws a visitor in on false pretenses.

## 6. In / out for this card

**In.** The technical eligibility floor for one public HTML page. The spam and abuse headings Google publishes, and the page behavior each one names. Which of those behaviors a later publish step must refuse. The line between a rule Google states and a refusal this pipeline locks.

**Out.** How crawling, featured snippets, and AI Overviews work (card 01). The blocks on the page. The pipeline that fills a page and publishes it. Search Console, manual-action reports, and the measurement loop. A new route, including `/blog`. Home-assistant organs, the Pi, and an S3 `page.json`.

## 7. Won’t-chase

- A word count, a link count, a page count, or a Core Web Vitals score as a publish gate. Google states no such number on the pages this card used.
- E-E-A-T as a factor the page must pass. Google says it is not a ranking factor.
- A ban on AI-assisted writing. Google says the violation is purpose, not the tool.
- Search-feature content policies as a reason to refuse the ordinary HTML page. That page says they do not apply to web results.
- The old title “thin content,” if it lived on a page these documents do not cite. The live headings are scaled content abuse, scraping, and thin affiliation.
- Vendor spam scorecards (**MARKETING**).
- How to file a reconsideration request, read a manual action, or operate Search Console.

## 8. What would prove this wrong

1. Google removes one of the §4 headings, or states that the behavior in that row does not risk a lower ranking or omission.
2. Google publishes a number for word count, link count, “many” pages, or “significant volume,” where this card says that number is **UNKNOWN**.
3. Google states that using AI or automation makes a page ineligible even when the primary purpose is helping a user.
4. Google states that accordion, tab, slideshow, tooltip, or screen-reader text is hidden-text abuse.
5. Google states that a search-feature content policy makes the ordinary web listing ineligible.
6. Google states that E-E-A-T is a specific ranking factor a page must pass.
7. On this origin, a page that matches a §4 row is indexed and served with no lower ranking and no omission that Google attributes to that policy.

## 9. Source list

All accessed 2026-09-29.

1. Google. "Google Search Essentials." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/essentials
2. Google. "Google Search technical requirements." Last updated 2025-12-18 UTC. https://developers.google.com/search/docs/essentials/technical
3. Google. "Spam policies for Google web search." Last updated 2026-08-28 UTC. https://developers.google.com/search/docs/essentials/spam-policies
4. Google. "Creating helpful, reliable, people-first content." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/fundamentals/creating-helpful-content
5. Google Search Help. "Content policies for Google Search." https://support.google.com/websearch/answer/10622781
6. Google. "File types indexable by Google." Last updated 2026-02-03 UTC. https://developers.google.com/search/docs/crawling-indexing/indexable-file-types
7. Google. "Qualify your outbound links to Google." Last updated 2025-12-10 UTC. https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links
8. Sullivan, Danny, and Chris Nelson. "Google Search's guidance about AI-generated content." Google Search Central Blog, 8 February 2023. https://developers.google.com/search/blog/2023/02/google-search-and-ai-content
9. Google. "Understanding page experience in Google Search results." Last updated 2026-09-22 UTC. https://developers.google.com/search/docs/appearance/page-experience
