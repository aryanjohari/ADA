# 05 — Search Console

Access date for every source below: 2026-09-29.

Tags: **EVIDENCE** (a cited source), **HUNCH** (a reading, not a measurement), **FEASIBLE** (this origin can host the object), **POLICY** (a rule this card locks), **UNKNOWN** (not established). A vendor page about a rank dashboard would be **MARKETING** and is not used as a report of what Search Console shows. None of the sources below are that.

The object is the one indexed, snippet-eligible HTML URL locked in card 01, on the portfolio origin locked in card 04. Search Console is a report about that URL. It is not a ranking system and it is not a publish step. This card does not restate how the URL is crawled, quoted, or cited, and it does not restate the spam rows, the blocks, or the five pipeline steps.

## 1. Question

What can Google Search Console report about one URL on this origin, which fields attach to that URL, and how long after publish those fields can be empty for a reason Google states?

## 2. Short answer

**POLICY:** For one URL, web-search Performance reports four numbers on the Pages row: clicks, impressions, click-through rate, and average position. In most cases those numbers attach to the canonical URL Google selects. A 2026 generative-AI report reports impressions of links in AI Overviews and AI Mode, and its metric list is impressions. Whether that URL is indexed is the indexing status in URL Inspection. Google says collected data is normally visible in 2–3 days, and that a newly created site or a newly added property can take up to a week to show any data. Google does not state a day count from the publish of one URL until the first impression, click, or query. An empty report is not a pass. No click count and no impression count is published as that pass. Reading these reports is not the card-02 row that forbids automated queries to Google, including a results scrape used to check rank. Whether a property is connected for this host is **UNKNOWN**.

## 3. Fields for one URL

The host in card 04 is `https://aryan-portfolio-one-kappa.vercel.app`. The path of the value page is **UNKNOWN**, as card 04 left it. A Search Console property is the container these reports read. This card did not find a public Google page that verifies a property for that host. The connection status is **UNKNOWN**. This card does not connect a property.

**EVIDENCE.** Google Search Console Help, [Performance report (Search results): Overview and basic setup](https://support.google.com/webmasters/answer/7576553), accessed 2026-09-29. The metrics are clicks, impressions, CTR, and average position. In the table, average position is the average position of the specific URL or grouping in that row. In the chart, it is the average position of the topmost result from the whole property. The table groups by queries, pages, countries, devices, search appearance, or dates. Grouping by queries, countries, devices, or dates aggregates by property. Grouping by pages or by search appearance aggregates by page. The chart aggregates by property. The search-type filter includes web, split into text-based and multimodal. The same page says that a query can be in the report and still not be what a person sees when they run that query, because results depend on time, place, device, and recent history.

**EVIDENCE.** Google Search Console Help, [Performance report (Search results): About the data](https://support.google.com/webmasters/answer/17011364), accessed 2026-09-29. Aggregated by page, each unique URL is counted separately. Position is the topmost position of that specific page. CTR and average position are generally higher when aggregated by property, when several pages from the same site appear together, because the property count keeps only the topmost position and counts the property once.

**EVIDENCE.** Google Search Console Help, [Performance report (Search results): Dimensions and data groupings](https://support.google.com/webmasters/answer/17011259), accessed 2026-09-29. The page dimension is the final URL linked by a Search result after any redirects. Most performance data is assigned to the canonical URL, not to a duplicate. A click on a duplicate URL counts toward the canonical URL, not toward the URL the user visits. The URL Inspection tool is how the canonical is identified. Some queries are omitted to protect privacy (anonymized queries). They stay in the chart totals unless a query filter is applied. Search Console stores top rows, so the table is not every query. The queries dimension is not available for the multimodal web search type. The branded and non-branded filter is information only and does not affect ranking. That filter is unavailable for sites with a low number of impressions. Google states no number for “low.” Dates in the report, other than the 24-hour view, are Pacific Time.

**EVIDENCE.** Google Search Console Help, [What are impressions, position, and clicks?](https://support.google.com/webmasters/answer/7042828), accessed 2026-09-29. Click, impression, and position data are attributed to the canonical URL of the link. In some cases data might be assigned to the actual URL rather than the canonical. A link must get an impression for a position to be recorded. A dash means there is no recorded position because the user did not see the property for that query. Clicking a link to an external page in an AI Overview counts as a click, and the same is true in AI Mode. An AI Overview occupies a single position, and every link in it is assigned that position. Standard impression rules apply to both. Search Console does not include data from experiments in Search Labs. A redirect after the user lands does not change which URL received the impression or the click.

**EVIDENCE.** Google Search Console Help, [Performance report (Search results): Common tasks and use cases](https://support.google.com/webmasters/answer/17010961), accessed 2026-09-29. A URL filter focuses the report on the page or pages selected. Clicking a query filters the report to that query, and the Pages tab then lists the URLs shown for it. The same page says it can be difficult to tell whether a specific page change caused a change in Search performance, because user sentiment, news, or another site can change the numbers too. It recommends reading trends in impressions and clicks ahead of position alone. It states no click count and no impression count that means a page passed.

### Web search Performance

These rows are the web search type of the Performance report. Image, video, and news are other search types on that report. They are not rows here.

| Name | What it counts | The URL it attaches to | Source |
| --- | --- | --- | --- |
| Clicks | Times a user clicked a link from Google Search results through to the page. A click that stays on Google is not counted. A click on a link in an AI Overview, or in AI Mode, counts as a click in this report. | In most cases, the canonical URL Google selects. The Pages row is the final URL after redirects. Sometimes the data is assigned to the actual URL instead. | Overview, answer 7576553; impressions, answer 7042828; dimensions, answer 17011259 |
| Impressions | Times a link to the page was in the results the user was shown. Inside a carousel or an expanding block, the link usually has to be scrolled or expanded into view. An AI Overview link and an AI Mode link use those standard impression rules. | Same URL as clicks. | Impressions, answer 7042828; about the data, answer 17011364 |
| CTR | Clicks divided by impressions. | The page, when the table is grouped by Pages or by search appearance. The chart CTR is the property, and those two totals differ when several URLs from the property appear together. | Overview, answer 7576553; about the data, answer 17011364 |
| Average position | The average of the topmost position of that page’s link, across the impressions that were recorded. No impression means no position, and the report can show a dash. An AI Overview takes one position, and each of its links gets that same position. | The URL in the Pages row. The chart position is the topmost result from the whole property. | Overview, answer 7576553; about the data, answer 17011364; impressions, answer 7042828 |
| Query | The search term those metrics were recorded for. Anonymized queries and other rare queries are omitted from the table. The queries dimension is absent for multimodal web search. A branded or non-branded label does not affect ranking. | An unfiltered query row is the property. A URL filter focuses the report on the selected page, and clicking a query then lists the pages shown for that query. | Dimensions, answer 17011259; common tasks, answer 17010961; overview, answer 7576553 |
| Country | The country where the search originated, as a grouping of the metrics. | An unfiltered country row is the property. A URL filter focuses the report on the selected page. | Overview, answer 7576553; dimensions, answer 17011259; common tasks, answer 17010961 |
| Device | Desktop, tablet, or mobile, as a grouping of the metrics. | An unfiltered device row is the property. A URL filter focuses the report on the selected page. | Overview, answer 7576553; dimensions, answer 17011259 |
| Search appearance | The result type in which the link was recorded. The filter lists only types that already have impressions. One impression is counted per feature type in a session. Clicks are assigned to the URL, not to the pair of URL and feature, so a filtered click count is not guaranteed to be clicks on that feature. | The page. Grouping or filtering by search appearance aggregates the table by page. | Dimensions, answer 17011259 |
| Date | The day, week, or month of the metrics. Dates are Pacific Time, except the 24-hour view, which uses the browser’s local time. The newest points can be preliminary. | An unfiltered date row is the property. A URL filter focuses the report on the selected page. | Dimensions, answer 17011259; overview, answer 7576553 |

**POLICY.** A later read of one URL uses the Pages row, or the same report with a URL filter on that URL. An unfiltered query, country, device, or date row is the property. The chart is the property even when the table is the page.

### Whether the URL is indexed

**EVIDENCE.** Google Search Console Help, [URL Inspection tool](https://support.google.com/webmasters/answer/9012289), accessed 2026-09-29. The tool reports Google’s indexed version of one URL in the open property. Indexing status is “The page is indexed,” or “The page is not indexed” with a reason. One reason is “URL is unknown to Google,” which means Google has not seen that URL. “URL is on Google” means the URL has been indexed and can appear in Search results. The same page says that status does not guarantee the URL is appearing. The result is the last indexed version, not a live test. The inspected URL has to be in the current property.

**EVIDENCE.** Google Search Console Help, [Page indexing report](https://support.google.com/webmasters/answer/7440203), accessed 2026-09-29. The report counts indexed URLs and not-indexed URLs that Google knows about in the property. Indexed means those URLs were successfully indexed. The same page says this report is not for the index status of a specific page, and that the specific page is read with URL Inspection. The example list is limited to 1,000 URLs and is not guaranteed to include every URL in a status. Being indexed does not guarantee the page will show for a search.

| Name | What it counts | The URL it attaches to | Source |
| --- | --- | --- | --- |
| Indexing status | Whether the indexed version is “The page is indexed” or not indexed, including unknown to Google. “URL is on Google” means indexed and eligible to appear. It does not mean the URL is showing. | The inspected URL, which has to sit in the open property. | URL Inspection, answer 9012289 |

**POLICY.** The per-URL index read is that indexing status. The Page indexing totals and the 1,000-URL sample are the property. A URL missing from the sample is not a report that the URL is unindexed.

### Generative AI performance

**EVIDENCE.** Google Search Console Help, [Generative AI performance report (Search)](https://support.google.com/webmasters/answer/16984139), accessed 2026-09-29. A note on the page says that as of 31 August 2026 these insights are rolled out to all websites worldwide. The report shows impressions in generative AI features on Google Search: AI Overviews and AI Mode. An impression is how many times links to the site were shown in one of those features. The metric in the default view is impressions. Dimensions are pages, countries, dates, and devices. The Pages row is the final URL linked by the feature after redirects, and most of the data is assigned to the canonical URL, not a duplicate. The chart is the property, and a URL filter aggregates that chart by URL. The page says the report includes data from the web search type of the Performance report. It does not list clicks, CTR, average position, or queries. Search Labs experiments are excluded. The report can be absent because a property does not have access while rollout continues, because the site has not received enough impressions in those features, or because the site was excluded from Search generative AI features. Google states no number for “enough.”

**EVIDENCE.** Hillel Maoz and Moshe Samet, [Introducing Search Generative AI performance reports in Search Console](https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports), Google Search Central Blog, 3 June 2026, accessed 2026-09-29. The reports show impressions of URLs in generative AI features on Search, including AI Overviews and AI Mode, plus a separate Discover report. The same post says this data is included in the overall performance report, and that the new view is the generative-AI slice. The listed items are impressions, pages, countries, devices, and dates. The post says Google is still considering additional metrics over time.

| Name | What it counts | The URL it attaches to | Source |
| --- | --- | --- | --- |
| Impressions | Times a link to the page was shown in an AI Overview or in AI Mode on Google Search. | The Pages row: the final URL after redirects. Most data is assigned to the canonical URL, not a duplicate. A URL filter makes the chart that URL. | Generative AI performance report, answer 16984139 |
| Country | The country of those impressions. | A country row grouped that way is the property. The page grouping is the URL above. | Same page |
| Device | Desktop, tablet, or mobile, for those impressions. | A device row grouped that way is the property. The page grouping is the URL above. | Same page |
| Date | The day, week, or month of those impressions, in Pacific Time. Newest points can be preliminary and can change in the next few hours. | A date row grouped that way is the property. The page grouping is the URL above. | Same page |

**EVIDENCE.** The same generative-AI help page, accessed 2026-09-29. What that page measures is link impressions in AI Overviews and AI Mode. What it lists as a metric is impressions. Clicks, CTR, average position, and queries are fields of the web-search Performance report above, including the click and position rules that page gives for an AI Overview and for AI Mode. The generative-AI report does not list them. The blog post says further metrics may be added later. Neither page says an impression is a quotation of the page, a grounding judgment, or a citation share.

**UNKNOWN.** Whether this host’s property, if one exists, shows the generative-AI report. The help page both announces a worldwide rollout on 31 August 2026 and still lists rollout access as a reason the report can be missing. This card cannot tell which sentence applies here, because the property connection is **UNKNOWN**. The impression count Google calls “enough” is **UNKNOWN**. The number of impressions Google calls “low” for the branded-query filter is **UNKNOWN**.

## 4. Delay

**EVIDENCE.** Google Search Console Help, [About Search Console data](https://support.google.com/webmasters/answer/96568), accessed 2026-09-29. It can take up to a week to generate data for a newly created site, or a site newly added to Search Console. If there is still no data after a week, one stated reason is the wrong protocol on the property. If the Performance report shows no data, the same page says it may be because people are not yet clicking the site in search results. Collected data is published in intervals. Normally, collected data should be available in 2–3 days. The Performance tables omit rare queries. A table shows at most 1,000 rows.

**EVIDENCE.** Google Search Console Help, [Performance report (Search results): About the data](https://support.google.com/webmasters/answer/17011364), accessed 2026-09-29. The newest data is sometimes preliminary: still being collected, and it may change in the next few hours. The report shows complete days by default. Preliminary data appears when a day that has it is selected, usually today and sometimes yesterday. Values shown as `~` or `-` become zeros in a download.

**EVIDENCE.** The generative-AI report page cited in §3. Its newest data can be preliminary and might change in the next few hours. The page does not state a different day count for a new URL.

**POLICY.** The lags this card may quote are the ones those pages state: collected data normally available in 2–3 days, and up to a week before any data for a newly created site or a newly added property. Preliminary points for today, and sometimes yesterday, can still change within a few hours.

**UNKNOWN.** How many days after the publish of one URL the first impression, click, or query can appear. The week is about a new site or a new property. The 2–3 days are about collected numbers becoming visible. Neither sentence is a wait from the card-04 deploy until this URL must show a row.

An empty field, for a reason those pages state, can be any of these:

- The property was added recently, or the site is new to Search Console, inside that week.
- Collected numbers are inside the 2–3 day interval.
- The selected day is still preliminary.
- The Performance report has no data because people are not yet clicking.
- The query was omitted as rare or anonymized, or it fell outside the 1,000 stored rows.
- Position is a dash because that view had no impression.
- The generative-AI report is absent because of access, because the site has not had enough of those impressions, or because the site is excluded from the features. The count for “enough” stays **UNKNOWN**.
- URL Inspection says the URL is unknown to Google. That is an index status, not a Performance lag.

**POLICY.** Empty is not a decision that the page failed. Card 04 left link count **UNKNOWN**. This card locks no click threshold and no impression threshold.

**HUNCH.** A download that turns a dash into zero can be read as a position of zero. The report’s own mark for that cell is “not a number,” which the impressions page ties to no recorded position. The zero is an export artifact.

## 5. What this card locks for a later loop

**POLICY.** A later patch decision may read, for the one deployed URL, and only when a property contains that URL:

- Web-search Performance, on the Pages row or under a URL filter: clicks, impressions, CTR, and average position.
- Under that same URL filter: the query, country, device, and date groupings of those four numbers.
- Search appearance for that page, with clicks still credited to the URL.
- Indexing status from URL Inspection.
- Generative-AI impressions for that page, and the country, device, and date groupings of those impressions.

**POLICY.** Those fields cannot make these decisions:

- They cannot pass or fail the page. Google publishes no click count and no impression count for that pass. Card 02 and card 04 left link count **UNKNOWN**. A low CTR, in the common-tasks wording, is a prompt to look at the title and the query. It is not a cutoff.
- They cannot rank the page, and they cannot require a rank. Average position reports where the topmost link was seen. The branded-query label does not affect ranking. Search Console is not a ranking system.
- They cannot decide that a patch caused a change in the numbers. The common-tasks page says other events can move the same numbers.
- They cannot publish, refuse, or replace the page. Card 04 deploy writes a commit and a public HTML URL. These reports are not a step in that deploy.
- They cannot decide that the page was quoted, grounded, or given a featured snippet. Generative-AI impressions count links shown in AI Overviews and AI Mode. Web-search clicks and position include those links under the rules in §3. Which passage is quoted stays **UNKNOWN**, as card 01 locked.
- They cannot send automated queries to Google, including a results scrape used to check rank. That is the card-02 machine-generated-traffic row. Reading a Search Console report is not that row.
- They cannot treat “URL is on Google” as proof the URL is showing, and they cannot treat a URL missing from the Page indexing sample as proof it is absent.
- They cannot treat a dash, or a zero that a download wrote in place of a dash, as position zero.
- They cannot connect a property, add `/blog`, or choose the path. The path stays **UNKNOWN**. The property connection stays **UNKNOWN**.

## 6. In / out for this card

**In.** What the web-search Performance report can say about one URL. What the generative-AI Search report measures, and which of the web-search fields it does not list. The index status of one URL, and the limit of the Page indexing report. The delays and empty-report reasons Google states. Which of those fields a later patch decision may read, and which decisions they cannot make.

**Out.** Connecting a property. Calling the Search Console API. Opening this host’s console. The closed measurement loop. A results scrape. Code, a new route, and `/blog`. Choosing the path. Crawl, snippet, and AI-citation rules (card 01). Spam refusals (card 02). Blocks (card 03). The five deploy steps (card 04).

## 7. Won't-chase

- A click count or an impression count that means the page passed. The pages this card used state no such number. “Low” impressions and “enough” impressions stay **UNKNOWN**.
- A day count from publish of one URL until the first impression, click, or query. The stated lags are the 2–3 days and the week in §4.
- Reading an unfiltered property chart, or an unfiltered query row, as the number for one URL.
- Discover, News, image search, and video search as fields for this URL. The common-tasks page lists Search, News, and Discover as separate reports.
- Core Web Vitals, a manual action, or E-E-A-T as a field this loop reads. Card 02.
- The Page indexing reason list, beyond indexed or not indexed for one URL. The per-URL status is URL Inspection.
- A `site:` query or any other results check. Card 02. This card does not describe one.
- Request indexing, or any other console action, as a substitute for the card-04 deploy.
- Vendor rank dashboards (**MARKETING**).

## 8. What would prove this wrong

1. Google’s Performance help stops assigning clicks, impressions, CTR, or average position to a page URL.
2. Google publishes a click count or an impression count and says a page at that count has passed, where this card says that number is **UNKNOWN**.
3. Google states a number of days from the publish of one URL until impressions, clicks, or queries must appear, or it withdraws the 2–3 day sentence or the one-week sentence this card quotes.
4. The generative-AI performance help lists clicks, queries, or average position, or it says the report measures quotation, grounding, or citation share.
5. Google states that reading a Search Console report is the same act as sending automated queries that scrape results to check rank.
6. A public Google document verifies a Search Console property for `https://aryan-portfolio-one-kappa.vercel.app`, where this card says that connection is **UNKNOWN**.
7. Google states that the Page indexing report is how to read one URL’s index status, and that URL Inspection does not report it.

## 9. Source list

All accessed 2026-09-29.

1. Google Search Console Help. "Performance report (Search results): Overview and basic setup." https://support.google.com/webmasters/answer/7576553
2. Google Search Console Help. "Performance report (Search results): About the data." https://support.google.com/webmasters/answer/17011364
3. Google Search Console Help. "Performance report (Search results): Dimensions and data groupings." https://support.google.com/webmasters/answer/17011259
4. Google Search Console Help. "Performance report (Search results): Common tasks and use cases." https://support.google.com/webmasters/answer/17010961
5. Google Search Console Help. "What are impressions, position, and clicks?" https://support.google.com/webmasters/answer/7042828
6. Google Search Console Help. "About Search Console data." https://support.google.com/webmasters/answer/96568
7. Google Search Console Help. "URL Inspection tool." https://support.google.com/webmasters/answer/9012289
8. Google Search Console Help. "Page indexing report." https://support.google.com/webmasters/answer/7440203
9. Google Search Console Help. "Generative AI performance report (Search)." https://support.google.com/webmasters/answer/16984139
10. Maoz, Hillel, and Moshe Samet. "Introducing Search Generative AI performance reports in Search Console." Google Search Central Blog, 3 June 2026. https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports
