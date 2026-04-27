"""Unit tests for draft → WordPress CSV mapping (no DB)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from ada.draft_wordpress_csv_export import (
    page_to_wordpress_row,
    resolve_focus_keyword,
    write_wordpress_csv,
    WORDPRESS_CSV_FIELDNAMES,
)


def test_resolve_focus_keyword_precedence() -> None:
    out = {"target_keyword_cluster": " from-out "}
    step = {"target_keyword_cluster": "step", "niche": "niche1"}
    wf = {"target_keyword_cluster": "wf", "niche": "niche2"}
    assert resolve_focus_keyword(out, step, wf).strip() == "from-out"
    o2: dict = {}
    assert resolve_focus_keyword(o2, step, wf) == "step"
    assert resolve_focus_keyword(o2, {}, {"niche": "  nz  "}) == "nz"


def test_page_to_wordpress_row() -> None:
    page = {
        "title": "T",
        "content": "C",
        "slug": "s",
        "meta_description": "M",
    }
    r = page_to_wordpress_row(page, "focus")
    assert r["Title"] == "T"
    assert r["Content"] == "C"
    assert r["Slug"] == "s"
    assert r["Meta_Description"] == "M"
    assert r["Focus_Keyword"] == "focus"


def test_write_wordpress_csv_header_matches_sample(tmp_path: Path) -> None:
    p = tmp_path / "out.csv"
    write_wordpress_csv(
        p,
        [
            page_to_wordpress_row(
                {
                    "title": "A",
                    "content": "line1\nline2",
                    "slug": "a",
                    "meta_description": "d",
                },
                "f",
            )
        ],
    )
    first = p.read_text(encoding="utf-8").splitlines()[0]
    assert first == "Title,Content,Slug,Meta_Description,Focus_Keyword"
    with p.open("r", encoding="utf-8", newline="") as f:
        r = list(csv.DictReader(f))
    assert r[0]["Title"] == "A"
    assert "line1\nline2" in r[0]["Content"]


def test_csv_multiline_quoted_like_wordpress() -> None:
    buf = io.StringIO()
    w = csv.DictWriter(
        buf, fieldnames=list(WORDPRESS_CSV_FIELDNAMES), quoting=csv.QUOTE_MINIMAL
    )
    w.writeheader()
    w.writerow(
        page_to_wordpress_row(
            {
                "title": "T",
                "content": 'hello\n"world"',
                "slug": "s",
                "meta_description": "m",
            },
            "",
        )
    )
    s = buf.getvalue()
    assert s.splitlines()[0] == "Title,Content,Slug,Meta_Description,Focus_Keyword"
