"""Guard rails: keyword publish path stays explicit and disjoint from matrix planner."""

from ada.workflow.templates import WORKFLOW_KINDS, expand_workflow_template


def test_keyword_publish_template_untouched_registry():
    """Matrix planner proposes only publish_entity_v1 ids; keyword kind stays deterministic."""
    assert "publish_keyword_v1" in WORKFLOW_KINDS
    steps = expand_workflow_template(
        "publish_keyword_v1",
        {
            "target_keyword_cluster": "widget installer",
            "project_id": "proj",
            "campaign_id": "camp",
            "niche": "widgets",
        },
        max_steps=10,
    )
    assert [x["step_type"] for x in steps] == ["ENRICH", "DRAFT", "DEPLOY"]
