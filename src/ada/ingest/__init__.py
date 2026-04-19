"""Data ingestion (RSS, etc.)."""

from ada.ingest.rss import IngestRssResult, ingest_rss_feeds, run_ingest_rss_cli

__all__ = ["IngestRssResult", "ingest_rss_feeds", "run_ingest_rss_cli"]
