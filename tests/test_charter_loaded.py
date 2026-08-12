"""Charter loads constitution §14 extract."""

from ada.cortex.charter import build_system_charter, load_section_14_extract


def test_charter_contains_no_consciousness_line():
    extract = load_section_14_extract()
    assert "Never claim consciousness" in extract
    assert "not conscious" in extract.lower() or "not conscious" in extract


def test_charter_loaded_includes_mode():
    text = build_system_charter(mode="observe")
    assert "Never claim consciousness" in text
    assert "Observe" in text
    assert "body_vitals" in text
