"""TRELLIS worker deploy config (web-admin)."""

from app.services import worker_deploy as wd


def test_default_config_has_trellis_keys():
    cfg = wd.default_config()
    env = cfg["env"]
    assert env["TRELLIS2_PIPELINE_TYPE"] == "1024"
    assert env["WORKER_PIPELINE_MODE"] == "trellis"
    assert cfg["container_name"] == "kwork-worker"


def test_build_env_file_lines():
    cfg = wd.default_config()
    cfg["env"]["WORKER_ID"] = "test-gpu"
    lines = wd._build_env_file_lines(cfg)
    text = "\n".join(lines)
    assert "WORKER_ID=test-gpu" in text
    assert "WORKER_DOCKER_IMAGE=" in text
    assert "WORKER_BIND_SCRIPTS=" in text


def test_mask_env():
    env = {"WORKER_ID": "a", "HF_TOKEN": "secret"}
    masked = wd._mask_env(env)
    assert masked["WORKER_ID"] == "a"
    assert masked["HF_TOKEN"] == wd.MASK


def test_coerce_env_map_ignores_bad_payload():
    assert wd._coerce_env_map(None) == {}
    assert wd._coerce_env_map("broken") == {}
    assert wd._coerce_env_map({"WORKER_ID": 42}) == {"WORKER_ID": "42"}
