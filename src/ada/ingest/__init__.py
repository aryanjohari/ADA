"""Data ingestion (RSS, keywords, GETS, etc.)."""

from ada.ingest.gets import (
    IngestGetsResult,
    ingest_gets_index,
    parse_gets_index_html,
    run_ingest_gets_cli,
)
from ada.ingest.keywords import (
    IngestKeywordsResult,
    ingest_keywords_batch,
    run_ingest_keywords_cli,
)
from ada.ingest.rss import IngestRssResult, ingest_rss_feeds, run_ingest_rss_cli

__all__ = [
    "IngestGetsResult",
    "IngestKeywordsResult",
    "IngestRssResult",
    "ingest_gets_index",
    "ingest_keywords_batch",
    "ingest_rss_feeds",
    "parse_gets_index_html",
    "run_ingest_gets_cli",
    "run_ingest_keywords_cli",
    "run_ingest_rss_cli",
]
