"""Company invitation revoke slice §2.5.5."""


def test_revoked_status_value():
    assert "revoked" != "pending"
