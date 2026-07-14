"""Owner notification routing §3.19 + YooKassa refund parse + soft-launch checklist."""

from app.services import company_notify as cn
from app.services import loki_logs as ll
from app.services import soft_launch as sl
from app.services.yookassa import yookassa_service


def test_normalize_routing_defaults():
    r = cn.normalize_routing(None)
    assert r["generation_done"] == "owner_manager"
    assert r["photographer_uploaded"] == "owner_manager"
    assert r["source_expire"] == "all"
    assert r["low_balance"] == "owner_only"


def test_normalize_routing_patch():
    r = cn.normalize_routing({"generation_done": "owner_only", "bogus": "all", "low_balance": "ALL"})
    assert r["generation_done"] == "owner_only"
    assert r["low_balance"] == "all"
    assert "bogus" not in r


def test_parse_webhook_refund():
    parsed = yookassa_service.parse_webhook(
        {
            "event": "refund.succeeded",
            "object": {
                "id": "ref-1",
                "payment_id": "pay-9",
                "status": "succeeded",
                "amount": {"value": "150.00", "currency": "RUB"},
                "metadata": {},
            },
        }
    )
    assert parsed["event"] == "refund.succeeded"
    assert parsed["refund_id"] == "ref-1"
    assert parsed["payment_id"] == "pay-9"
    assert parsed["amount"] == 150
    assert parsed["status"] == "succeeded"


def test_parse_webhook_payment_still_ok():
    parsed = yookassa_service.parse_webhook(
        {
            "event": "payment.succeeded",
            "object": {
                "id": "pay-1",
                "status": "succeeded",
                "amount": {"value": "99.00"},
                "metadata": {"order_id": "1"},
            },
        }
    )
    assert parsed["payment_id"] == "pay-1"
    assert parsed["refund_id"] is None


def test_soft_launch_normalize_checks():
    out = sl.normalize_checks({"env": True, "unknown": True, "gpu_e2e": 1})
    assert out["env"] is True
    assert out["gpu_e2e"] is True
    assert "unknown" not in out
    assert out["alerts"] is False
    assert len(out) == len(sl.CHECKLIST_ITEMS)


def test_loki_containers_default():
    containers = ll.configured_containers()
    assert "postgres" in containers
    assert "minio" in containers
