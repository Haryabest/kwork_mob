"""NSFW SLA dashboard + source expire + maintenance checklist."""

from datetime import date, datetime, timedelta, timezone

from app.services import maintenance as mt
from app.services import source_expire as se
from app.services.age_gate import age_years, is_adult_category, parse_birth_date
from app.services.nsfw_sla_dashboard import sla_fields


def test_sla_fields_overdue():
    now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
    created = now - timedelta(hours=30)
    f = sla_fields(created, now=now)
    assert f["overdue"] is True
    assert f["hours_overdue"] >= 5


def test_sla_fields_urgent():
    now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)
    created = now - timedelta(hours=20)
    f = sla_fields(created, now=now)
    assert f["overdue"] is False
    assert f["urgent"] is True


def test_source_ttl_and_warn_days():
    assert se.ttl_days() >= 7
    assert 7 in se.WARN_DAYS and 1 in se.WARN_DAYS


def test_maintenance_normalize():
    out = mt.normalize_checks({"smart": True, "bogus": True})
    assert out["smart"] is True
    assert "bogus" not in out
    assert out["backup_restore"] is False
    assert len(out) == len(mt.CHECKLIST_ITEMS)


def test_age_adult_category_and_codes():
    assert is_adult_category("adult")
    assert not is_adult_category("clothing")
    assert parse_birth_date("01.05.2000") == date(2000, 5, 1)
    assert age_years(date(2000, 1, 1), today=date(2026, 7, 14)) >= 18
