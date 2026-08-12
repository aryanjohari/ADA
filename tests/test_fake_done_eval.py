"""Fake-done without tool receipts should fail eval helper."""

from ada.harness.eval import claims_body_metric_without_receipt


def test_fake_done_without_receipt_rejected_by_eval_helper():
    answer = "I remounted ada-data and disk free is now fine."
    assert claims_body_metric_without_receipt(answer, []) is True
    receipts = [
        {
            "ok": True,
            "tool": "body_doctor",
            "data": {"mounted": True},
        }
    ]
    assert claims_body_metric_without_receipt(answer, receipts) is False
