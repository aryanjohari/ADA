"""Hunt SoT tools — paste-JD smoke for cv-draft-1 (M28)."""

from __future__ import annotations

from typing import Any

from ada.memory import hunt as hunt_mod


def run_hunt_guidelines_load(args: dict[str, Any]) -> dict[str, Any]:
    max_chars = int(args.get("max_chars_per_file") or 120_000)
    return hunt_mod.load_verbatim(max_chars_per_file=max_chars)


def run_hunt_paste_jd(args: dict[str, Any]) -> dict[str, Any]:
    jd = args.get("jd_text") or args.get("text")
    pack_id = args.get("pack_id")
    if not jd:
        raise ValueError("jd_text required")
    if not pack_id:
        raise ValueError("pack_id required")
    return hunt_mod.paste_jd(
        jd_text=str(jd),
        pack_id=str(pack_id),
        source_url=str(args["source_url"]) if args.get("source_url") else None,
        company=str(args["company"]) if args.get("company") else None,
        role=str(args["role"]) if args.get("role") else None,
        campaign_id=str(args.get("campaign_id") or hunt_mod.CV_DRAFT_CAMPAIGN_ID),
    )


def run_hunt_triage_record(args: dict[str, Any]) -> dict[str, Any]:
    pack_id = args.get("pack_id")
    if not pack_id:
        raise ValueError("pack_id required")
    if args.get("role_fit") is None or args.get("expect") is None:
        raise ValueError("role_fit and expect required")
    decision = args.get("decision")
    if not decision:
        raise ValueError("decision required (skip|hold|apply)")
    return hunt_mod.record_triage(
        pack_id=str(pack_id),
        role_fit=int(args["role_fit"]),
        expect=int(args["expect"]),
        decision=str(decision),
        rationale=str(args["rationale"]) if args.get("rationale") else None,
        residency_score=(
            str(args["residency_score"]) if args.get("residency_score") else None
        ),
        campaign_id=str(args.get("campaign_id") or hunt_mod.CV_DRAFT_CAMPAIGN_ID),
    )


def run_hunt_write_pack(args: dict[str, Any]) -> dict[str, Any]:
    pack_id = args.get("pack_id")
    if not pack_id:
        raise ValueError("pack_id required")
    return hunt_mod.write_pack(
        pack_id=str(pack_id),
        accepted=bool(args.get("accepted", False)),
        cv_body=str(args["cv_body"]) if args.get("cv_body") else None,
        cover_body=str(args["cover_body"]) if args.get("cover_body") else None,
        campaign_id=str(args.get("campaign_id") or hunt_mod.CV_DRAFT_CAMPAIGN_ID),
    )


def run_hunt_ensure_campaign(args: dict[str, Any]) -> dict[str, Any]:
    _ = args
    return hunt_mod.ensure_cv_draft_campaign()


DISPATCH = {
    "hunt_guidelines_load": run_hunt_guidelines_load,
    "hunt_paste_jd": run_hunt_paste_jd,
    "hunt_triage_record": run_hunt_triage_record,
    "hunt_write_pack": run_hunt_write_pack,
    "hunt_ensure_campaign": run_hunt_ensure_campaign,
}
