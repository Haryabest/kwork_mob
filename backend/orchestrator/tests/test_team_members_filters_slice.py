"""Team members list filters §20."""

import inspect

from app.api.v1.company import list_members


def test_list_members_query_params():
    sig = inspect.signature(list_members)
    for key in ("search", "role", "limit", "offset"):
        assert key in sig.parameters
