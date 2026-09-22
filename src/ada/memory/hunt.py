"""M28 cv-draft-1 — hunt SoT resolve, verbatim load, sandboxed pack write.

Writes are jailed under HUNT_ROOT/applications/. Prod tree
``nz-cv-job-hunt`` (no ``-smoke``) is hard-refused for writes this slice.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from ada.body.vitals import utc_now_iso
from ada.io.atomic import atomic_write_text
from ada.io.paths import BodyFault, DataPaths, ada_data_mounted, require_ada_data

ENV_ADA_HUNT_ROOT = "ADA_HUNT_ROOT"
DEFAULT_SMOKE_NAME = "nz-cv-job-hunt-smoke"
PROD_HUNT_NAME = "nz-cv-job-hunt"
CV_DRAFT_CAMPAIGN_ID = "cv-draft-1"

# Paste-smoke stages (compile_pdf skipped for this slice).
CV_DRAFT_STAGES: list[dict[str, Any]] = [
    {"id": "link_or_jd", "state": "pending"},
    {"id": "jd_ready", "state": "pending"},
    {"id": "triage", "state": "pending"},
    {"id": "draft_pack", "state": "pending"},
    {"id": "you_send", "state": "pending", "gate": "operator_ship"},
]

VERBATIM_RELS: tuple[str, ...] = (
    "docs/FIT_AND_EXPECT.md",
    "docs/HUNT_SESSION.md",
    "docs/ADA_HUNT_WORKFLOW.md",
    ".cursor/skills/job-apply/SKILL.md",
    "applications/_defaults/cv-summaries.md",
    "applications/_defaults/covers.md",
    "applications/_defaults/education.md",
    "Job_Hunt_Brain/MASTER_PROFILE.md",
)

_PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")
_MAX_FILE_BYTES = 512 * 1024
_TRIAGE_DECISIONS = frozenset({"skip", "hold", "apply"})


def _require_paths(paths: DataPaths | None) -> DataPaths:
    p = paths or require_ada_data()
    if not ada_data_mounted(p.root):
        raise BodyFault(
            f"ada-data not mounted or missing at {p.root}; refusing hunt access"
        )
    return p


def _work_hunt_yaml(paths: DataPaths) -> Path:
    return paths.facts / "work_hunt.yaml"


def _load_work_hunt_fact(paths: DataPaths) -> dict[str, Any]:
    path = _work_hunt_yaml(paths)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def default_smoke_hunt_root(paths: DataPaths | None = None) -> Path:
    p = paths or require_ada_data()
    return (p.root / "hunt" / DEFAULT_SMOKE_NAME).resolve()


def resolve_hunt_root(*, paths: DataPaths | None = None) -> Path:
    """HUNT_ROOT: env ADA_HUNT_ROOT → FACT work_hunt.yaml → smoke default."""
    import os

    p = _require_paths(paths)
    env = (os.environ.get(ENV_ADA_HUNT_ROOT) or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    fact = _load_work_hunt_fact(p)
    fact_root = str(fact.get("hunt_root") or "").strip()
    if fact_root:
        return Path(fact_root).expanduser().resolve()
    return default_smoke_hunt_root(p)


def is_prod_hunt_root(hunt_root: Path) -> bool:
    """True when basename is exactly the prod clone (no -smoke)."""
    return hunt_root.resolve().name == PROD_HUNT_NAME


def applications_root(hunt_root: Path | None = None, *, paths: DataPaths | None = None) -> Path:
    root = (hunt_root or resolve_hunt_root(paths=paths)).resolve()
    return (root / "applications").resolve()


def _resolve_under_applications(apps: Path, rel: str) -> Path:
    raw = (rel or "").replace("\\", "/")
    if not raw or raw.startswith("/") or "\x00" in raw or ".." in raw.split("/"):
        raise ValueError("invalid applications path")
    rel = raw.lstrip("/")
    if not rel:
        raise ValueError("invalid applications path")
    target = (apps / rel).resolve()
    try:
        target.relative_to(apps)
    except ValueError as exc:
        raise ValueError("path escapes HUNT_ROOT/applications/") from exc
    return target


def assert_writable_hunt_root(hunt_root: Path) -> None:
    """Hard refuse pack writes into prod nz-cv-job-hunt this slice."""
    if is_prod_hunt_root(hunt_root):
        raise PermissionError(
            "refusing write to prod hunt root "
            f"{hunt_root}; use {DEFAULT_SMOKE_NAME} (or set ADA_HUNT_ROOT)"
        )


def load_verbatim(
    *,
    hunt_root: Path | None = None,
    paths: DataPaths | None = None,
    max_chars_per_file: int = 120_000,
) -> dict[str, Any]:
    """Load guideline / brain files from HUNT_ROOT (read-only; prod OK)."""
    root = (hunt_root or resolve_hunt_root(paths=paths)).resolve()
    if not root.is_dir():
        return {
            "ok": False,
            "outcome": "error",
            "error": f"HUNT_ROOT missing: {root}",
            "hunt_root": str(root),
        }
    files: list[dict[str, Any]] = []
    missing: list[str] = []
    for rel in VERBATIM_RELS:
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            missing.append(rel)
            continue
        if not path.is_file():
            missing.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        truncated = len(text) > max_chars_per_file
        body = text[:max_chars_per_file] if truncated else text
        files.append(
            {
                "rel": rel,
                "bytes": len(text.encode("utf-8")),
                "chars": len(text),
                "truncated": truncated,
                "text": body,
            }
        )
    return {
        "ok": True,
        "outcome": "ok",
        "hunt_root": str(root),
        "is_prod": is_prod_hunt_root(root),
        "files": files,
        "missing": missing,
        "count": len(files),
    }


def ensure_cv_draft_campaign(*, paths: DataPaths | None = None) -> dict[str, Any]:
    """Create or return campaign cv-draft-1 with paste-smoke stages."""
    from ada.memory.open_loops import get_loop, upsert_loop

    p = _require_paths(paths)
    existing = get_loop(CV_DRAFT_CAMPAIGN_ID, paths=p)
    if existing and existing.get("kind") == "campaign":
        return {"ok": True, "outcome": "ok", "loop": existing, "created": False}

    hunt = resolve_hunt_root(paths=p)
    r = upsert_loop(
        loop_id=CV_DRAFT_CAMPAIGN_ID,
        text="CV / hunt Mode B (named JD) — paste-JD smoke",
        kind="campaign",
        title="cv-draft-1 paste smoke",
        status="active",
        stages=[dict(s) for s in CV_DRAFT_STAGES],
        current_stage="link_or_jd",
        cadence="on_open_only",
        last_receipt=f"hunt_root:{hunt}",
        paths=p,
    )
    return {**r, "created": True}


def _mark_stages_done(
    stages: list[dict[str, Any]],
    *,
    done_ids: list[str],
    active_id: str | None,
) -> list[dict[str, Any]]:
    done = set(done_ids)
    out: list[dict[str, Any]] = []
    for raw in stages:
        stage = dict(raw)
        sid = str(stage.get("id") or "")
        if sid in done:
            stage["state"] = "done"
        if active_id and sid == active_id:
            stage["state"] = "active"
        out.append(stage)
    return out


def _validate_pack_id(pack_id: str) -> str:
    pid = (pack_id or "").strip().lower()
    if not _PACK_ID_RE.match(pid):
        raise ValueError(
            "pack_id must be lowercase slug [a-z0-9._-] (e.g. 2026-09-acme-junior-dev)"
        )
    if pid.startswith("_"):
        raise ValueError("pack_id must not start with _ (reserved for _defaults/_inbox)")
    return pid


def paste_jd(
    *,
    jd_text: str,
    pack_id: str,
    source_url: str | None = None,
    company: str | None = None,
    role: str | None = None,
    campaign_id: str = CV_DRAFT_CAMPAIGN_ID,
    paths: DataPaths | None = None,
    hunt_root: Path | None = None,
) -> dict[str, Any]:
    """Store pasted JD under applications/_inbox/<id>/ and advance to jd_ready."""
    from ada.memory.open_loops import get_loop, upsert_loop

    p = _require_paths(paths)
    root = (hunt_root or resolve_hunt_root(paths=p)).resolve()
    assert_writable_hunt_root(root)
    apps = applications_root(root)
    pid = _validate_pack_id(pack_id)
    text = (jd_text or "").strip()
    if len(text) < 40:
        return {
            "ok": False,
            "outcome": "error",
            "error": "jd_text too short for score-quality paste (need full JD body)",
        }
    if len(text.encode("utf-8")) > _MAX_FILE_BYTES:
        return {"ok": False, "outcome": "error", "error": "jd_text exceeds size cap"}

    ensure_cv_draft_campaign(paths=p)
    rel_dir = f"_inbox/{pid}"
    jd_path = _resolve_under_applications(apps, f"{rel_dir}/jd.md")
    manifest_path = _resolve_under_applications(apps, f"{rel_dir}/manifest.yaml")
    jd_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(jd_path, text if text.endswith("\n") else text + "\n")
    manifest = {
        "pack_id": pid,
        "source_url": (source_url or "").strip() or None,
        "fetch_ok": False,
        "paste": True,
        "company": (company or "").strip() or None,
        "role": (role or "").strip() or None,
        "notes": "paste-JD smoke path (no fetch)",
        "ts": utc_now_iso(),
    }
    atomic_write_text(
        manifest_path,
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
    )

    camp = get_loop(campaign_id, paths=p) or {}
    stages = camp.get("stages") if isinstance(camp.get("stages"), list) else [
        dict(s) for s in CV_DRAFT_STAGES
    ]
    new_stages = _mark_stages_done(
        [dict(s) for s in stages],
        done_ids=["link_or_jd", "jd_ready"],
        active_id="triage",
    )
    upsert_loop(
        loop_id=campaign_id,
        status="active",
        current_stage="triage",
        stages=new_stages,
        last_receipt=f"hunt:applications/{rel_dir}/jd.md",
        blocked_reason=None,
        paths=p,
    )
    return {
        "ok": True,
        "outcome": "ok",
        "hunt_root": str(root),
        "pack_id": pid,
        "jd_path": f"applications/{rel_dir}/jd.md",
        "manifest_path": f"applications/{rel_dir}/manifest.yaml",
        "campaign_id": campaign_id,
        "current_stage": "triage",
    }


def record_triage(
    *,
    pack_id: str,
    role_fit: int,
    expect: int,
    decision: str,
    rationale: str | None = None,
    residency_score: str | None = None,
    campaign_id: str = CV_DRAFT_CAMPAIGN_ID,
    paths: DataPaths | None = None,
    hunt_root: Path | None = None,
) -> dict[str, Any]:
    """Record dual scores + skip|hold|apply. No pack write here."""
    from ada.memory.open_loops import get_loop, upsert_loop

    p = _require_paths(paths)
    root = (hunt_root or resolve_hunt_root(paths=p)).resolve()
    assert_writable_hunt_root(root)
    apps = applications_root(root)
    pid = _validate_pack_id(pack_id)
    dec = (decision or "").strip().lower()
    if dec not in _TRIAGE_DECISIONS:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"decision must be one of {sorted(_TRIAGE_DECISIONS)}",
        }
    try:
        rf = int(role_fit)
        ex = int(expect)
    except (TypeError, ValueError):
        return {"ok": False, "outcome": "error", "error": "role_fit/expect must be ints"}
    if not 1 <= rf <= 5 or not 1 <= ex <= 5:
        return {
            "ok": False,
            "outcome": "error",
            "error": "role_fit and expect must be 1..5",
        }

    inbox = _resolve_under_applications(apps, f"_inbox/{pid}")
    if not (inbox / "jd.md").is_file():
        return {
            "ok": False,
            "outcome": "error",
            "error": f"missing pasted JD at applications/_inbox/{pid}/jd.md",
        }

    triage = {
        "pack_id": pid,
        "role_fit": rf,
        "expect": ex,
        "decision": dec,
        "residency_score": (residency_score or "").strip() or None,
        "rationale": (rationale or "").strip() or None,
        "ts": utc_now_iso(),
    }
    triage_path = inbox / "triage.yaml"
    atomic_write_text(
        triage_path,
        yaml.safe_dump(triage, sort_keys=False, allow_unicode=True),
    )

    camp = get_loop(campaign_id, paths=p) or {}
    stages = camp.get("stages") if isinstance(camp.get("stages"), list) else [
        dict(s) for s in CV_DRAFT_STAGES
    ]
    stages = [dict(s) for s in stages]
    stages = _mark_stages_done(stages, done_ids=["link_or_jd", "jd_ready", "triage"], active_id=None)

    if dec in ("skip", "hold"):
        # F-M28-11: no pack on skip/hold — pause / end triage branch.
        for stage in stages:
            if stage.get("id") == "draft_pack":
                stage["state"] = "skipped"
            if stage.get("id") == "you_send":
                stage["state"] = "skipped"
        upsert_loop(
            loop_id=campaign_id,
            status="paused" if dec == "hold" else "active",
            current_stage="triage",
            stages=stages,
            blocked_reason=f"triage {dec}: no pack (role_fit={rf} expect={ex})",
            last_receipt=f"hunt:applications/_inbox/{pid}/triage.yaml",
            paths=p,
        )
        return {
            "ok": True,
            "outcome": "ok",
            "pack_id": pid,
            "decision": dec,
            "role_fit": rf,
            "expect": ex,
            "pack_allowed": False,
            "triage_path": f"applications/_inbox/{pid}/triage.yaml",
            "note": "skip/hold — no pack (F-M28-11)",
        }

    # apply proposed — wait for Plan Accept before draft_pack
    for stage in stages:
        if stage.get("id") == "draft_pack":
            stage["state"] = "pending"
            stage["gate"] = "plan_accept"
    upsert_loop(
        loop_id=campaign_id,
        status="active",
        current_stage="draft_pack",
        stages=stages,
        blocked_reason=(
            f"Accept apply to draft tailored pack "
            f"(role_fit={rf} expect={ex}); Plan Accept = hunt Accept apply"
        ),
        last_receipt=f"hunt:applications/_inbox/{pid}/triage.yaml",
        paths=p,
    )
    return {
        "ok": True,
        "outcome": "ok",
        "pack_id": pid,
        "decision": dec,
        "role_fit": rf,
        "expect": ex,
        "pack_allowed": rf >= 3,
        "triage_path": f"applications/_inbox/{pid}/triage.yaml",
        "note": (
            "await Plan Accept then hunt_write_pack"
            if rf >= 3
            else "role_fit < 3 — refuse pack even after Accept"
        ),
    }


def _load_triage(apps: Path, pack_id: str) -> dict[str, Any] | None:
    path = _resolve_under_applications(apps, f"_inbox/{pack_id}/triage.yaml")
    if not path.is_file():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else None


def _tailored_stub_tex(
    *,
    kind: str,
    pack_id: str,
    company: str,
    role: str,
    body: str,
) -> str:
    """Minimal tailored .tex — never a copy of _defaults/fullstack-v1."""
    label = {"cv": "CV", "cover": "Cover", "jd": "JD"}.get(kind, kind)
    safe_body = (body or "").replace("\\", "\\\\")
    return (
        f"% TAILORED: {company} -- {role}\n"
        f"% pack_id: {pack_id}\n"
        f"% smoke pack ({label}) — not _defaults/fullstack-v1 (F-M28-11)\n"
        f"\\documentclass{{article}}\n"
        f"\\begin{{document}}\n"
        f"\\section*{{{label}: {company} / {role}}}\n"
        f"{safe_body}\n"
        f"\\end{{document}}\n"
    )


def write_pack(
    *,
    pack_id: str,
    accepted: bool,
    cv_body: str | None = None,
    cover_body: str | None = None,
    campaign_id: str = CV_DRAFT_CAMPAIGN_ID,
    paths: DataPaths | None = None,
    hunt_root: Path | None = None,
) -> dict[str, Any]:
    """Write tailored applications/<id>/{cv,cover,jd}.tex after Plan Accept only.

    Gates (F-M28-11 / F-M28-7 spirit):
    - accepted=true (Consent Integrity after Plan Accept)
    - campaign has plan_id (Accept pin)
    - triage decision=apply and role_fit >= 3
    - never write under prod hunt root
    - never auto-Applied / never campaign done
    """
    from ada.memory.open_loops import get_loop, handshake_after_artifact, upsert_loop

    p = _require_paths(paths)
    root = (hunt_root or resolve_hunt_root(paths=p)).resolve()
    assert_writable_hunt_root(root)
    apps = applications_root(root)
    pid = _validate_pack_id(pack_id)

    if not accepted:
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": "hunt_write_pack requires accepted=true after Plan Accept",
        }

    camp = get_loop(campaign_id, paths=p)
    if not camp or camp.get("kind") != "campaign":
        return {
            "ok": False,
            "outcome": "error",
            "error": f"campaign not found: {campaign_id}",
        }
    if not str(camp.get("plan_id") or "").strip():
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": (
                "campaign missing plan_id — Plan Accept first "
                "(Accept apply = Plan Accept)"
            ),
        }

    triage = _load_triage(apps, pid)
    if not triage:
        return {
            "ok": False,
            "outcome": "error",
            "error": f"missing triage for {pid}; run hunt_triage_record first",
        }
    decision = str(triage.get("decision") or "").strip().lower()
    if decision in ("skip", "hold"):
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": f"triage decision={decision} — no pack (F-M28-11)",
        }
    if decision != "apply":
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": f"triage decision must be apply; got {decision!r}",
        }
    try:
        rf = int(triage.get("role_fit"))
    except (TypeError, ValueError):
        return {"ok": False, "outcome": "error", "error": "triage.role_fit invalid"}
    if rf < 3:
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": f"role_fit={rf} < 3 — no pack (draft gate)",
        }

    inbox_jd = _resolve_under_applications(apps, f"_inbox/{pid}/jd.md")
    if not inbox_jd.is_file():
        return {"ok": False, "outcome": "error", "error": "missing pasted JD"}
    jd_text = inbox_jd.read_text(encoding="utf-8")
    manifest_path = apps / "_inbox" / pid / "manifest.yaml"
    company = "Company"
    role = "Role"
    if manifest_path.is_file():
        man = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if isinstance(man, dict):
            company = str(man.get("company") or company)
            role = str(man.get("role") or role)

    pack_dir = _resolve_under_applications(apps, pid)
    # Refuse writing into _defaults circulate packs.
    if pid in {"fullstack-v1", "default-ai", "lane-a-retail", "recruiter-register"}:
        return {
            "ok": False,
            "outcome": "denied",
            "denied_reason": "refusing to overwrite circulate _defaults pack id",
        }

    cv_tex = _tailored_stub_tex(
        kind="cv",
        pack_id=pid,
        company=company,
        role=role,
        body=(cv_body or "").strip()
        or f"Tailored CV draft for {role} at {company}. Replace with job-apply skill output.",
    )
    cover_tex = _tailored_stub_tex(
        kind="cover",
        pack_id=pid,
        company=company,
        role=role,
        body=(cover_body or "").strip()
        or f"Tailored cover draft for {role} at {company}.",
    )
    jd_tex = _tailored_stub_tex(
        kind="jd",
        pack_id=pid,
        company=company,
        role=role,
        body=jd_text[:8000],
    )
    # F-M28-11: refuse if someone tries to ship default circulate content.
    for label, blob in (("cv", cv_tex), ("cover", cover_tex)):
        if "TAILORED:" not in blob:
            return {
                "ok": False,
                "outcome": "denied",
                "denied_reason": f"{label}.tex missing TAILORED marker (F-M28-11)",
            }
        if "fullstack-v1" in blob.lower() and "not _defaults/fullstack-v1" not in blob:
            return {
                "ok": False,
                "outcome": "denied",
                "denied_reason": f"{label}.tex looks like default circulate (F-M28-11)",
            }

    pack_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, content in (
        ("cv.tex", cv_tex),
        ("cover.tex", cover_tex),
        ("jd.tex", jd_tex),
    ):
        target = _resolve_under_applications(apps, f"{pid}/{name}")
        if len(content.encode("utf-8")) > _MAX_FILE_BYTES:
            return {"ok": False, "outcome": "error", "error": f"{name} exceeds size cap"}
        atomic_write_text(target, content)
        written.append(f"applications/{pid}/{name}")

    # Advance draft_pack → you_send via handshake (waiting_on_aryan; never done).
    stages = camp.get("stages") if isinstance(camp.get("stages"), list) else [
        dict(s) for s in CV_DRAFT_STAGES
    ]
    stages = _mark_stages_done(
        [dict(s) for s in stages],
        done_ids=["link_or_jd", "jd_ready", "triage", "draft_pack"],
        active_id="you_send",
    )
    upsert_loop(loop_id=campaign_id, stages=stages, paths=p)

    receipt = f"hunt:applications/{pid}/cv.tex"
    handshake = handshake_after_artifact(
        campaign_id=campaign_id,
        artifact_path=receipt,
        next_stage="you_send",
        waiting_reason=(
            f"review pack applications/{pid}/ then submit; "
            "type 'sent to …' / apply URL (never auto-Applied)"
        ),
        paths=p,
    )
    return {
        "ok": True,
        "outcome": "ok",
        "hunt_root": str(root),
        "pack_id": pid,
        "written": written,
        "tailored": True,
        "campaign_id": campaign_id,
        "handshake": handshake,
        "status": "waiting_on_aryan",
        "note": "operator ships; Confirm + typed receipt → done (F-M28-7)",
    }
