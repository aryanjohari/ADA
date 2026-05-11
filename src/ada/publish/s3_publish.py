"""S3 `page.json` + `manifest.json` writes for the DEPLOY step."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from ada.config import Settings
from ada.publish.page_schema_v1 import PageJsonV1

log = logging.getLogger("ada.publish.s3")

JSON_UTF8 = "application/json; charset=utf-8"
CSV_UTF8 = "text/csv; charset=utf-8"


def page_s3_key(project_id: str, campaign_id: str, slug: str) -> str:
    p = str(project_id).strip().strip("/")
    c = str(campaign_id).strip().strip("/")
    s = str(slug).strip().strip("/")
    return f"{p}/{c}/{s}/page.json"


def manifest_s3_key(project_id: str, campaign_id: str) -> str:
    p = str(project_id).strip().strip("/")
    c = str(campaign_id).strip().strip("/")
    return f"{p}/{c}/manifest.json"


def normalize_manifest_to_entries(raw: bytes | str) -> list[dict[str, Any]]:
    """Accept array or object with entries|pages|routes|items; return a list of dict rows."""
    if isinstance(raw, bytes):
        t = raw.decode("utf-8")
    else:
        t = str(raw)
    t = t.strip()
    if not t:
        return []
    data = json.loads(t)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ("entries", "pages", "routes", "items"):
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def upsert_route_entry(
    entries: list[dict[str, Any]],
    *,
    niche: str,
    slug: str,
    title: str,
    excerpt: str,
    image_url: str = "",
) -> list[dict[str, Any]]:
    n = str(niche).strip()
    s = str(slug).strip()
    out: list[dict[str, Any]] = [dict(x) for x in entries if isinstance(x, dict)]
    for i, row in enumerate(out):
        rniche = str(row.get("niche", "") or "").strip()
        rslug = str(row.get("slug", "") or "").strip()
        if rniche.lower() == n.lower() and rslug.lower() == s.lower():
            row["niche"] = n
            row["slug"] = s
            row["title"] = title
            if excerpt:
                row["excerpt"] = excerpt
            if image_url:
                row["image_url"] = image_url
            out[i] = row
            return out
    out.append(
        {
            "niche": n,
            "slug": s,
            "title": title,
            "excerpt": excerpt,
            **({"image_url": image_url} if image_url else {}),
        }
    )
    return out


def s3_client_for_settings(settings: Settings):
    extra: dict[str, Any] = {}
    if settings.aws_endpoint_url:
        extra["endpoint_url"] = settings.aws_endpoint_url
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        config=BotoConfig(retries={"max_attempts": 3, "mode": "standard"}),
        **extra,
    )


def put_s3_object_bytes(
    settings: Settings,
    *,
    bucket: str,
    key: str,
    body: bytes,
    content_type: str,
) -> dict[str, Any]:
    """Single-object PutObject (e.g. WordPress CSV delivery). Returns output_json-friendly fields."""
    b = str(bucket).strip()
    k = str(key).strip().lstrip("/")
    if not b:
        raise ValueError("S3 bucket is required")
    if not k or ".." in k:
        raise ValueError("S3 key is required and must not contain '..'")
    client = s3_client_for_settings(settings)
    client.put_object(Bucket=b, Key=k, Body=body, ContentType=content_type)
    return {"bucket": b, "key": k, "bytes_written": len(body)}


def deploy_page_and_manifest(
    settings: Settings,
    *,
    page: PageJsonV1,
    project_id: str,
    campaign_id: str,
    niche: str,
) -> dict[str, Any]:
    """
    Put `page.json`, read–merge–write `manifest.json`. Returns output_json-friendly dict.
    """
    bucket = (settings.s3_bucket_name or "").strip()
    if not bucket:
        raise ValueError("S3 bucket not configured (S3_BUCKET_NAME or ADA_S3_BUCKET)")
    if not str(page.og_image or "").strip():
        raise ValueError("DEPLOY requires page.og_image")

    d = page.model_dump(mode="json", exclude_none=True)
    page_body = json.dumps(d, ensure_ascii=False)
    pkey = page_s3_key(project_id, campaign_id, page.slug)
    mkey = manifest_s3_key(project_id, campaign_id)

    client = s3_client_for_settings(settings)
    b_page = page_body.encode("utf-8")

    client.put_object(
        Bucket=bucket,
        Key=pkey,
        Body=b_page,
        ContentType=JSON_UTF8,
    )

    entries: list[dict[str, Any]] = []
    try:
        obj = client.get_object(Bucket=bucket, Key=mkey)
        raw = obj["Body"].read()
        entries = normalize_manifest_to_entries(raw)
    except ClientError as e:
        code = (e.response.get("Error") or {}).get("Code", "")
        if str(code) not in ("404", "NoSuchKey", "NotFound"):
            log.warning("manifest get %s: %s", mkey, e)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("manifest parse %s: %s", mkey, e)
        entries = []

    ex = (page.meta_description or "")[:240]
    img = str(page.og_image or "").strip()
    merged = upsert_route_entry(
        entries,
        niche=niche,
        slug=page.slug,
        title=page.title,
        excerpt=ex,
        image_url=img,
    )
    mbody = json.dumps(merged, ensure_ascii=False)
    client.put_object(
        Bucket=bucket,
        Key=mkey,
        Body=mbody.encode("utf-8"),
        ContentType=JSON_UTF8,
    )

    return {
        "page_s3_key": pkey,
        "manifest_s3_key": mkey,
        "bytes_written": {
            "page": len(b_page),
            "manifest": len(mbody.encode("utf-8")),
        },
    }
