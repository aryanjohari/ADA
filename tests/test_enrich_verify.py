"""ENRICH post-condition helper."""

from ada.workflow.enrich_verify import enrich_postcondition_met


def test_postcondition_edge_id_increase():
    assert enrich_postcondition_met(
        snap_edge_max=1,
        snap_facts=0,
        snap_seq=0,
        after_edge_max=2,
        after_facts=0,
        chain_after=[],
    )


def test_postcondition_facts_increase():
    assert enrich_postcondition_met(
        snap_edge_max=5,
        snap_facts=1,
        snap_seq=10,
        after_edge_max=5,
        after_facts=3,
        chain_after=[],
    )


def test_postcondition_record_edge_tool_row():
    chain = [
        {
            "role": "tool",
            "sequence": 11,
            "parts": [
                {
                    "type": "function_response",
                    "name": "record_edge",
                    "response": {"edge_id": 99},
                }
            ],
        }
    ]
    assert enrich_postcondition_met(
        snap_edge_max=1,
        snap_facts=0,
        snap_seq=10,
        after_edge_max=1,
        after_facts=0,
        chain_after=chain,
    )


def test_postcondition_record_edge_with_error_ignored():
    chain = [
        {
            "role": "tool",
            "sequence": 11,
            "parts": [
                {
                    "type": "function_response",
                    "name": "record_edge",
                    "response": {"error": "bad"},
                }
            ],
        }
    ]
    assert not enrich_postcondition_met(
        snap_edge_max=1,
        snap_facts=0,
        snap_seq=10,
        after_edge_max=1,
        after_facts=0,
        chain_after=chain,
    )


def test_postcondition_sequence_not_newer():
    chain = [
        {
            "role": "tool",
            "sequence": 5,
            "parts": [
                {
                    "type": "function_response",
                    "name": "record_edge",
                    "response": {"edge_id": 99},
                }
            ],
        }
    ]
    assert not enrich_postcondition_met(
        snap_edge_max=1,
        snap_facts=0,
        snap_seq=10,
        after_edge_max=1,
        after_facts=0,
        chain_after=chain,
    )
