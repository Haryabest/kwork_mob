"""Member detail API smoke §20.5.3."""

import inspect

from app.api.v1.company import get_member, member_sessions, member_tasks


def test_member_detail_endpoints_exist():
    assert inspect.iscoroutinefunction(get_member)
    assert inspect.iscoroutinefunction(member_tasks)
    assert inspect.iscoroutinefunction(member_sessions)
