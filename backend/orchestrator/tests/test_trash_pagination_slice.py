"""Trash list pagination §3.3.1."""

import inspect

from app.api.v1.models import list_trash_models


def test_trash_list_has_pagination_params():
    sig = inspect.signature(list_trash_models)
    assert "limit" in sig.parameters
    assert "offset" in sig.parameters
