"""TRELLIS worker deploy config (web-admin)."""

from pathlib import Path

from app.services import worker_deploy as wd


def test_default_config_has_trellis_keys():
    cfg = wd.default_config()
    env = cfg["env"]
    assert env["TRELLIS2_PIPELINE_TYPE"] == "1536"
    assert env["WORKER_PIPELINE_MODE"] == "trellis"
    assert env["QUALITY_THRESHOLD"] == "0.35"
    assert env["TRELLIS2_LOW_VRAM"] == "1"
    assert env["WORKER_TRELLIS_INPROCESS"] == "0"
    assert env["NOBG_SENSITIVITY"] == "1.0"
    assert env["NOBG_INPUT_SIZE"] == "1024"
    assert env["TRELLIS2_TEX_STEPS"] == "12"
    assert env["TRELLIS2_TEX_GUIDANCE"] == "3"
    assert env["TRELLIS2_MAX_NUM_TOKENS"] == "999999"
    assert env["TRELLIS2_DECIMATION"] == "1000000"
    assert env["TRELLIS2_REORIENT_VERTICES"] == "0"
    assert env["TRELLIS2_SHAPE_REFINE_GUIDANCE"] == "6.5"
    assert cfg["container_name"] == "kwork-worker"


def test_env_presets():
    presets = wd.env_presets()
    assert "lan" in presets and "quality" in presets
    assert float(presets["quality"]["env"]["QUALITY_THRESHOLD"]) > float(
        presets["lan"]["env"]["QUALITY_THRESHOLD"]
    )
    assert presets["comfy"]["env"]["TRELLIS2_SS_STEPS"] == presets["lan"]["env"]["TRELLIS2_SS_STEPS"]


def test_build_env_file_includes_quality_threshold():
    cfg = wd.default_config()
    text = "\n".join(wd._build_env_file_lines(cfg))
    assert "QUALITY_THRESHOLD=0.35" in text
    assert "NOBG_SENSITIVITY=1.0" in text


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


def test_repo_root_does_not_index_parents():
    root = wd._repo_root()
    assert root.is_absolute()


def test_worker_dir_replaces_container_paths(monkeypatch):
    monkeypatch.setattr(wd.settings, "WORKER_HOST_REPO_ROOT", "/home/dom/kwork_mob")
    path = wd._worker_dir({"worker_repo_path": "/app/kwork_mob/worker"})
    assert path == Path("/home/dom/kwork_mob/worker")


def test_worker_redis_url_rewrites_compose_hostname():
    assert wd._worker_redis_url("redis://redis:6379/0") == "redis://host.docker.internal:6382/0"
    assert wd._worker_redis_url("redis://192.168.0.177:6382/0") == "redis://192.168.0.177:6382/0"


def test_normalize_worker_env_keeps_admin_redis():
    url = "redis://192.168.0.177:6382/0"
    env = wd._normalize_worker_env({"REDIS_URL": url})
    assert env["REDIS_URL"] == url


def test_build_env_file_lines_uses_admin_redis():
    cfg = wd.default_config()
    cfg["env"] = {"WORKER_ID": "gpu-1", "REDIS_URL": "redis://192.168.0.177:6382/0"}
    text = "\n".join(wd._build_env_file_lines(cfg))
    assert "REDIS_URL=redis://192.168.0.177:6382/0" in text


def test_compose_subprocess_env_prefers_worker_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env.worker"
    env_file.write_text("REDIS_URL=redis://192.168.0.177:6382/0\n", encoding="utf-8")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    env = wd._compose_subprocess_env(env_file)
    assert env["REDIS_URL"] == "redis://192.168.0.177:6382/0"
