"""Vitals API matches organ collect_vitals schema."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ada.body.vitals import collect_vitals
from ada.hud.app import create_app


def test_vitals_matches_organ_schema(data_root, monkeypatch):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    client = TestClient(create_app())
    resp = client.get("/api/vitals")
    assert resp.status_code == 200
    body = resp.json()
    organ = collect_vitals().model_dump()
    assert set(body["vitals"].keys()) == set(organ.keys())
    assert "urgent_faults" in body
    assert isinstance(body["urgent_faults"], list)
    # Core honesty fields present
    assert "thermal" in body["vitals"]
    assert "mounts" in body["vitals"]
    assert "disks" in body["vitals"]
