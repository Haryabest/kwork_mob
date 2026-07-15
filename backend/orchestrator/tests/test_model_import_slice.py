"""Import model prepare key format §6.10."""


def test_import_key_format():
    model_uuid = "a" * 32 + "b" * 4  # uuid-like
    key = f"imports/{model_uuid}/model.glb"
    assert key.startswith("imports/")
    assert key.endswith(".glb")
    assert key.split("/")[1] == model_uuid
