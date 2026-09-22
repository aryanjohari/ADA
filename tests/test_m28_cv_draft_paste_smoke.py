"""M28 paste-JD smoke — hunt path jail, Accept gate, STATUS resume (cv-draft-1)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from ada.cortex.adapter import CortexTurn
from ada.cortex.charter import mode_addendum
from ada.hud.app import create_app
from ada.io.paths import get_paths
from ada.memory import hunt as hunt_mod
from ada.memory.open_loops import get_loop, upsert_loop
from ada.tools.hunt_tools import (
    run_hunt_guidelines_load,
    run_hunt_paste_jd,
    run_hunt_triage_record,
    run_hunt_write_pack,
)
from ada.tools.toolspec import SPECS_BY_NAME

pytestmark = pytest.mark.tier_a

_FAKE_JD = """
Software Engineer — Acme NZ (Auckland hybrid)

About the role:
Build Python services and internal tools. Mentorship available.

Requirements:
- Python, SQL, git
- NZ work rights preferred
- 0–2 years experience OK

Nice to have: FastAPI, Docker.
""".strip()


def _seed_smoke_hunt(root: Path) -> Path:
    """Minimal smoke SoT under test ADA_DATA_ROOT (never touch real prod)."""
    hunt = root / "hunt" / hunt_mod.DEFAULT_SMOKE_NAME
    for rel in hunt_mod.VERBATIM_RELS:
        path = hunt / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# stub {rel}\nrole_fit and expect live here.\n", encoding="utf-8")
    (hunt / "applications" / "_inbox").mkdir(parents=True, exist_ok=True)
    (hunt / "applications" / "_defaults" / "fullstack-v1").mkdir(parents=True, exist_ok=True)
    (hunt / "applications" / "_defaults" / "fullstack-v1" / "cv.tex").write_text(
        "% default circulate — must never be shipped as named-JD pack\n",
        encoding="utf-8",
    )
    (hunt / "SMOKE_ROOT.md").write_text("smoke\n", encoding="utf-8")
    facts = root / "memory" / "facts"
    facts.mkdir(parents=True, exist_ok=True)
    (facts / "work_hunt.yaml").write_text(
        yaml.safe_dump(
            {
                "hunt_root": str(hunt),
                "campaign_hint": "cv-draft-1",
                "smoke": True,
            }
        ),
        encoding="utf-8",
    )
    return hunt


def _client(data_root, monkeypatch, factory):
    monkeypatch.setenv("ADA_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ADA_HUD_SESSION_SECRET", "test-secret-please-change")
    monkeypatch.setenv("ADA_HUD_PASSWORD", "test-password")
    monkeypatch.setenv("ADA_HUD_COOKIE_SECURE", "0")
    app = create_app()
    app.state.chat.adapter_factory = factory
    return TestClient(app), app


def _login(client: TestClient) -> None:
    login = client.post("/api/login", json={"password": "test-password"})
    assert login.status_code == 200


class _QuietCortex:
    model = "fake"

    def generate(self, *, system, contents, tools=None):
        return CortexTurn(
            text="ok",
            tool_calls=[],
            usage={
                "prompt_token_count": 1,
                "candidates_token_count": 1,
                "total_token_count": 2,
            },
        )


def test_resolve_hunt_root_prefers_env(data_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    smoke = _seed_smoke_hunt(data_root)
    other = data_root / "hunt" / "other-smoke"
    other.mkdir(parents=True)
    monkeypatch.setenv("ADA_HUNT_ROOT", str(other))
    assert hunt_mod.resolve_hunt_root() == other.resolve()
    monkeypatch.delenv("ADA_HUNT_ROOT", raising=False)
    assert hunt_mod.resolve_hunt_root() == smoke.resolve()


def test_path_jail_rejects_escape(data_root: Path) -> None:
    smoke = _seed_smoke_hunt(data_root)
    apps = hunt_mod.applications_root(smoke)
    with pytest.raises(ValueError, match="escape|invalid"):
        hunt_mod._resolve_under_applications(apps, "../secrets/x")
    with pytest.raises(ValueError, match="escape|invalid"):
        hunt_mod._resolve_under_applications(apps, "/etc/passwd")
    with pytest.raises(ValueError, match="escape|invalid"):
        hunt_mod._resolve_under_applications(apps, "foo/../../etc/passwd")


def test_refuse_write_to_prod_basename(data_root: Path) -> None:
    prod = data_root / "hunt" / hunt_mod.PROD_HUNT_NAME
    prod.mkdir(parents=True)
    (prod / "applications").mkdir()
    with pytest.raises(PermissionError, match="prod hunt"):
        hunt_mod.assert_writable_hunt_root(prod)


def test_no_pack_without_accept(data_root: Path) -> None:
    _seed_smoke_hunt(data_root)
    hunt_mod.ensure_cv_draft_campaign()
    paste = run_hunt_paste_jd(
        {
            "jd_text": _FAKE_JD,
            "pack_id": "2026-09-acme-junior-dev",
            "company": "Acme",
            "role": "Software Engineer",
        }
    )
    assert paste["ok"], paste
    triage = run_hunt_triage_record(
        {
            "pack_id": "2026-09-acme-junior-dev",
            "role_fit": 4,
            "expect": 3,
            "decision": "apply",
            "rationale": "python overlap",
        }
    )
    assert triage["ok"], triage
    denied = run_hunt_write_pack(
        {"pack_id": "2026-09-acme-junior-dev", "accepted": False}
    )
    assert denied["ok"] is False
    assert denied.get("outcome") == "denied"

    # Accept pin missing even if accepted=true
    denied2 = run_hunt_write_pack(
        {"pack_id": "2026-09-acme-junior-dev", "accepted": True}
    )
    assert denied2["ok"] is False
    assert "plan_id" in (denied2.get("denied_reason") or "")


def test_skip_hold_no_pack(data_root: Path) -> None:
    smoke = _seed_smoke_hunt(data_root)
    hunt_mod.ensure_cv_draft_campaign()
    run_hunt_paste_jd(
        {
            "jd_text": _FAKE_JD,
            "pack_id": "2026-09-skip-role",
            "company": "NoFit",
            "role": "EM",
        }
    )
    skip = run_hunt_triage_record(
        {
            "pack_id": "2026-09-skip-role",
            "role_fit": 1,
            "expect": 1,
            "decision": "skip",
        }
    )
    assert skip["ok"]
    assert skip["pack_allowed"] is False
    upsert_loop(loop_id="cv-draft-1", plan_id="plan_testskip01")
    denied = run_hunt_write_pack({"pack_id": "2026-09-skip-role", "accepted": True})
    assert denied["ok"] is False
    assert "no pack" in (denied.get("denied_reason") or "").lower()
    assert not (smoke / "applications" / "2026-09-skip-role").exists()


def test_accept_writes_tailored_pack_and_handshake(data_root: Path) -> None:
    smoke = _seed_smoke_hunt(data_root)
    hunt_mod.ensure_cv_draft_campaign()
    pack_id = "2026-09-acme-junior-dev"
    assert run_hunt_paste_jd(
        {
            "jd_text": _FAKE_JD,
            "pack_id": pack_id,
            "company": "Acme",
            "role": "Software Engineer",
        }
    )["ok"]
    assert run_hunt_triage_record(
        {
            "pack_id": pack_id,
            "role_fit": 4,
            "expect": 3,
            "decision": "apply",
        }
    )["ok"]
    upsert_loop(loop_id="cv-draft-1", plan_id="plan_acceptef01")

    written = run_hunt_write_pack(
        {
            "pack_id": pack_id,
            "accepted": True,
            "cv_body": "Python services; Tailscale HUD.",
            "cover_body": "Excited about Acme junior SE.",
        }
    )
    assert written["ok"], written
    assert written["tailored"] is True
    assert written["status"] == "waiting_on_aryan"
    for name in ("cv.tex", "cover.tex", "jd.tex"):
        path = smoke / "applications" / pack_id / name
        assert path.is_file(), name
        text = path.read_text(encoding="utf-8")
        assert "TAILORED:" in text
        assert "Acme" in text
        assert "fullstack-v1" not in text.lower() or "not _defaults" in text

    camp = get_loop("cv-draft-1")
    assert camp is not None
    assert camp["status"] == "waiting_on_aryan"
    assert camp["current_stage"] == "you_send"
    assert camp["plan_id"] == "plan_acceptef01"
    assert "applications/" in str(camp.get("last_receipt") or "")


def test_status_survives_reload(data_root: Path) -> None:
    """F-M28-8: HUD restart still sees cv-draft-1 STATUS from disk."""
    from ada.memory.open_loops import campaign_heads, format_campaign_head

    _seed_smoke_hunt(data_root)
    hunt_mod.ensure_cv_draft_campaign()
    pack_id = "2026-09-resume-me"
    run_hunt_paste_jd(
        {
            "jd_text": _FAKE_JD,
            "pack_id": pack_id,
            "company": "ResumeCo",
            "role": "SE",
        }
    )
    run_hunt_triage_record(
        {
            "pack_id": pack_id,
            "role_fit": 3,
            "expect": 3,
            "decision": "apply",
        }
    )
    upsert_loop(loop_id="cv-draft-1", plan_id="plan_resume99aa")
    assert run_hunt_write_pack({"pack_id": pack_id, "accepted": True})["ok"]

    camp = get_loop("cv-draft-1")
    assert camp is not None
    assert camp["status"] == "waiting_on_aryan"
    assert camp["plan_id"] == "plan_resume99aa"
    assert camp["current_stage"] == "you_send"
    head = format_campaign_head(camp)
    assert "STATUS=waiting_on_aryan" in head
    assert "cv-draft-1" in head or camp["id"] == "cv-draft-1"
    heads = campaign_heads(paths=get_paths())
    assert any(
        h.get("id") == "cv-draft-1" and h.get("status") == "waiting_on_aryan"
        for h in heads
    )


def test_plan_accept_pins_campaign_then_pack(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accept apply = Plan Accept (campaign_id) then hunt_write_pack."""
    smoke = _seed_smoke_hunt(data_root)
    hunt_mod.ensure_cv_draft_campaign()
    pack_id = "2026-09-accept-api"
    run_hunt_paste_jd(
        {
            "jd_text": _FAKE_JD,
            "pack_id": pack_id,
            "company": "ApiCo",
            "role": "SE",
        }
    )
    run_hunt_triage_record(
        {
            "pack_id": pack_id,
            "role_fit": 4,
            "expect": 3,
            "decision": "apply",
        }
    )

    client, _app = _client(data_root, monkeypatch, lambda: _QuietCortex())
    _login(client)
    accept = client.post(
        "/api/plan/accept",
        json={
            "plan_id": "plan_apiaccept01",
            "campaign_id": "cv-draft-1",
            "steps": [{"text": "Draft tailored Acme pack under smoke hunt"}],
        },
    )
    assert accept.status_code == 200, accept.text
    body = accept.json()
    assert body.get("plan_id") == "plan_apiaccept01"
    assert body.get("campaign_id") == "cv-draft-1"

    camp = get_loop("cv-draft-1")
    assert camp is not None
    assert camp.get("plan_id") == "plan_apiaccept01"

    written = run_hunt_write_pack({"pack_id": pack_id, "accepted": True})
    assert written["ok"], written
    assert (smoke / "applications" / pack_id / "cv.tex").is_file()
    assert get_loop("cv-draft-1")["status"] == "waiting_on_aryan"


def test_guidelines_load_and_tools_registered(data_root: Path) -> None:
    _seed_smoke_hunt(data_root)
    loaded = run_hunt_guidelines_load({})
    assert loaded["ok"]
    assert loaded["count"] == len(hunt_mod.VERBATIM_RELS)
    for name in (
        "hunt_guidelines_load",
        "hunt_paste_jd",
        "hunt_triage_record",
        "hunt_write_pack",
        "hunt_ensure_campaign",
    ):
        assert name in SPECS_BY_NAME
    agent = mode_addendum("agent")
    assert "hunt_write_pack" in agent
    assert "cv-draft-1" in agent


def test_write_never_touches_sibling_prod_tree(data_root: Path) -> None:
    smoke = _seed_smoke_hunt(data_root)
    prod = data_root / "hunt" / hunt_mod.PROD_HUNT_NAME
    prod.mkdir(parents=True)
    prod_apps = prod / "applications"
    prod_apps.mkdir()
    prod_index = prod_apps / "index.csv"
    prod_index.write_text("id,status\nkeep-me,Applied\n", encoding="utf-8")
    before = prod_index.read_text(encoding="utf-8")

    hunt_mod.ensure_cv_draft_campaign()
    pack_id = "2026-09-safe-write"
    run_hunt_paste_jd(
        {
            "jd_text": _FAKE_JD,
            "pack_id": pack_id,
            "company": "Safe",
            "role": "SE",
        }
    )
    run_hunt_triage_record(
        {
            "pack_id": pack_id,
            "role_fit": 4,
            "expect": 4,
            "decision": "apply",
        }
    )
    upsert_loop(loop_id="cv-draft-1", plan_id="plan_safe0001")
    assert run_hunt_write_pack({"pack_id": pack_id, "accepted": True})["ok"]

    assert prod_index.read_text(encoding="utf-8") == before
    assert not (prod_apps / pack_id).exists()
    assert (smoke / "applications" / pack_id / "cv.tex").is_file()
