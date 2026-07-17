"""Models list filters §19.9."""

from types import SimpleNamespace

from app.api.v1.user import list_user_models


def test_list_models_query_params_signature():
    import inspect

    sig = inspect.signature(list_user_models)
    names = set(sig.parameters)
    for key in (
        "search",
        "date_from",
        "date_to",
        "tier",
        "author_id",
        "category",
        "publish_filter",
        "sort",
        "limit",
        "offset",
    ):
        assert key in names
