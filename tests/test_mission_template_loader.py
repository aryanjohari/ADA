"""Mission template loader: brief_md, pack, skills."""

from __future__ import annotations

import pytest

from ada.mission_cli import _load_mission_template, list_mission_template_names
from ada.programme.packet import ProgrammePacket
from ada.programme.packs import PACK_SKILL_ALLOWLIST, validate_skills_for_pack


def test_list_mission_template_names_includes_isr_publish() -> None:
    names = list_mission_template_names()
    assert "isr-publish" in names
    assert "ops" in names


def test_isr_publish_template_loads_brief_pack_skills() -> None:
    data = _load_mission_template("isr-publish")
    packet = ProgrammePacket.model_validate(data)
    assert packet.defaults_json.get("pack") == "isr-publish"
    assert "publish_entity_v1" in packet.skills_enabled
    assert "NZ ISR" in packet.brief_md or "ISR" in packet.brief_md
    assert len(packet.brief_md) > 20


@pytest.mark.parametrize("name", list_mission_template_names())
def test_template_skills_subset_of_pack_allowlist(name: str) -> None:
    data = _load_mission_template(name)
    packet = ProgrammePacket.model_validate(data)
    pack = packet.defaults_json.get("pack")
    assert pack, f"template {name!r} missing pack"
    assert pack in PACK_SKILL_ALLOWLIST
    skills = list(packet.skills_enabled)
    assert skills, f"template {name!r} must set skills_enabled"
    err = validate_skills_for_pack(skills, str(pack))
    assert err is None, err
