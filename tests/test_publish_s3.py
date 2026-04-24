"""DEPLOY: S3 keys, manifest merge, moto (no real bucket)."""

from __future__ import annotations

import json
import os
from unittest import mock

import boto3
from moto import mock_aws

from ada.config import Settings
from ada.publish.page_schema_v1 import LeadGenV1, PageJsonV1
from ada.publish.s3_publish import (
    deploy_page_and_manifest,
    manifest_s3_key,
    normalize_manifest_to_entries,
    page_s3_key,
    upsert_route_entry,
)


def test_key_helpers():
    assert page_s3_key("p", "c", "s") == "p/c/s/page.json"
    assert manifest_s3_key("p", "c") == "p/c/manifest.json"


def test_manifest_normalize_array_and_upsert():
    arr = b'[{"niche":"a","slug":"x","title":"T","excerpt":""}]'
    assert len(normalize_manifest_to_entries(arr)) == 1
    wrapped = b'{"entries": [{"niche": "a", "slug": "x", "title": "T"}]}'
    ent = normalize_manifest_to_entries(wrapped)
    assert ent[0]["slug"] == "x"
    merged = upsert_route_entry(
        ent, niche="a", slug="x", title="T2", excerpt="e2"
    )
    assert any(r.get("excerpt") == "e2" for r in merged)


@mock_aws
def test_deploy_page_and_manifest_writes_both():
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    bucket = "ada-test-bucket-xyz-unique"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket)
    s3.put_object(
        Bucket=bucket,
        Key="p/c/manifest.json",
        Body=b'[{"niche":"o","slug":"old","title":"O"}]',
    )
    with mock.patch.dict(
        os.environ,
        {
            "S3_BUCKET_NAME": bucket,
            "AWS_DEFAULT_REGION": "us-east-1",
        },
    ):
        settings = Settings.load()
    page = PageJsonV1(
        slug="s",
        title="T",
        meta_description="M",
        content="<p>hi</p>",
        lead_gen=LeadGenV1(
            form_fields=[],
            form_action_url="https://x",
            call_display_phone="1",
            call_tel_link="tel:1",
        ),
        json_ld={},
    )
    out = deploy_page_and_manifest(
        settings, page=page, project_id="p", campaign_id="c", niche="n"
    )
    assert out["page_s3_key"] == "p/c/s/page.json"
    obj = s3.get_object(Bucket=bucket, Key="p/c/s/page.json")
    body = obj["Body"].read().decode("utf-8")
    d = json.loads(body)
    assert d["slug"] == "s"
    assert obj.get("ContentType", "").startswith("application/json")
    mobj = s3.get_object(Bucket=bucket, Key="p/c/manifest.json")
    arr = json.loads(mobj["Body"].read().decode("utf-8"))
    assert isinstance(arr, list)
    assert any(e.get("slug") == "s" and e.get("niche") == "n" for e in arr)
    assert any(e.get("slug") == "old" for e in arr)
