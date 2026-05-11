"""WordPress-style CSV row mapping (shared by export CLI and publish delivery)."""

from __future__ import annotations

import csv
import io
from typing import Any

# Header must match a typical WordPress/CSV import (e.g. wordpress.csv).
WORDPRESS_CSV_FIELDNAMES = (
    "Title",
    "Content",
    "Slug",
    "Meta_Description",
    "Focus_Keyword",
)


def resolve_focus_keyword(
    output_json: dict[str, Any],
    step_input_json: dict[str, Any],
    workflow_params_json: dict[str, Any],
) -> str:
    """1:1 with publish params: target_keyword_cluster, else niche."""
    for src in (output_json, step_input_json, workflow_params_json):
        t = src.get("target_keyword_cluster")
        if isinstance(t, str) and t.strip():
            return t.strip()
    for src in (step_input_json, workflow_params_json):
        n = src.get("niche")
        if isinstance(n, str) and n.strip():
            return n.strip()
    return ""


def page_to_wordpress_row(
    page: dict[str, Any],
    focus_keyword: str,
) -> dict[str, str]:
    """Map PageJsonV1 dump keys to WordPress column names."""
    title = str(page.get("title", "") or "")
    content = str(page.get("content", "") or "")
    slug = str(page.get("slug", "") or "")
    meta = str(page.get("meta_description", "") or "")
    return {
        "Title": title,
        "Content": content,
        "Slug": slug,
        "Meta_Description": meta,
        "Focus_Keyword": focus_keyword,
    }


def wordpress_csv_single_row_bytes(row: dict[str, str]) -> bytes:
    """UTF-8 CSV with header + one data row."""
    buf = io.StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(WORDPRESS_CSV_FIELDNAMES),
        quoting=csv.QUOTE_MINIMAL,
    )
    w.writeheader()
    w.writerow({k: row.get(k, "") for k in WORDPRESS_CSV_FIELDNAMES})
    return buf.getvalue().encode("utf-8")


def wordpress_csv_s3_object_key(
    *,
    slug: str,
    explicit_key: str | None,
    prefix: str | None,
) -> str:
    """
    Resolve S3 object key: exact ``key`` wins; else ``prefix`` + normalized slug + .csv.
    ``prefix`` may be "" or a path ending with or without ``/``.
    """
    if explicit_key is not None and str(explicit_key).strip():
        k = str(explicit_key).strip().lstrip("/")
        if ".." in k or k.startswith("/"):
            raise ValueError("wordpress_csv_s3.key must be a relative S3 key without '..'")
        return k
    pfx = (prefix if prefix is not None else "").strip().strip("/")
    s = str(slug).strip().strip("/")
    if not s:
        raise ValueError("wordpress_csv_s3 requires non-empty page slug when using prefix")
    if ".." in s or "/" in s:
        raise ValueError("page slug must not contain '/' or '..' for prefix-based CSV key")
    if pfx:
        return f"{pfx}/{s}.csv"
    return f"{s}.csv"
