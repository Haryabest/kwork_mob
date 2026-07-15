"""Balance filters API slice §20.3.4."""

from types import SimpleNamespace

from app.services.balance_filters import (
    get_company_filters,
    get_personal_filters,
    save_company_filters,
    save_personal_filters,
)


def test_default_personal_filters():
    user = SimpleNamespace(notification_prefs={})
    assert get_personal_filters(user) == {
        "date_from": "",
        "date_to": "",
        "tx_type": "all",
        "page_size": 20,
    }


def test_save_and_load_personal_filters():
    user = SimpleNamespace(notification_prefs={})

    async def _run():
        class FakeDb:
            async def flush(self):
                return None

        saved = await save_personal_filters(
            FakeDb(),
            user,
            {"date_from": "2026-01-01", "date_to": "2026-01-31", "tx_type": "topup", "page_size": 50},
        )
        assert saved["tx_type"] == "topup"
        assert saved["page_size"] == 50
        loaded = get_personal_filters(user)
        assert loaded["date_from"] == "2026-01-01"
        assert loaded["tx_type"] == "topup"

    import asyncio

    asyncio.run(_run())


def test_company_filters_author_id():
    user = SimpleNamespace(
        notification_prefs={
            "balance_tx_filters": {
                "companies": {"7": {"author_id": 42, "tx_type": "charge", "page_size": 100}}
            }
        }
    )
    f = get_company_filters(user, 7)
    assert f["author_id"] == 42
    assert f["tx_type"] == "charge"
    assert f["page_size"] == 100


def test_topup_failed_pref_respected():
    from app.services.push import user_wants_notification

    user = SimpleNamespace(notification_prefs={"topup_failed": False, "push_enabled": True})
    assert user_wants_notification(user, "topup_failed") is False
    user2 = SimpleNamespace(notification_prefs={"topup_failed": True, "push_enabled": True})
    assert user_wants_notification(user2, "topup_failed") is True
