#!/usr/bin/env python3
"""SMART/disk metrics для MinIO-узлов (§21 / §22.6) → Prometheus textfile.

Метрики:
  minio_node_disk_smart_health{device,model}
  minio_node_disk_smart_temp_c{device}
  minio_node_disk_used_percent{device,mount}
  minio_node_disk_reallocated_sectors{device}

Запуск на узле хранения (cron каждые 5 мин):
  MINIO_SMART_DEVICES=/dev/sda,/dev/nvme0n1 \\
    python3 exporter.py --textfile-dir /var/lib/node_exporter/textfile

Для admin API оркестратор читает JSON sidecar (MINIO_SMART_JSON).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _parse_smartctl(device: str) -> dict | None:
    if not shutil.which("smartctl"):
        return {"device": device, "error": "smartctl not installed", "health": "unknown"}
    try:
        proc = subprocess.run(
            ["smartctl", "-a", "-j", device],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode not in (0, 4):
            return {"device": device, "error": (proc.stderr or proc.stdout or "fail")[:300]}
        data = json.loads(proc.stdout or "{}")
        health = "ok"
        for item in data.get("ata_smart_attributes", {}).get("table", []) or []:
            if item.get("name") == "Reallocated_Sector_Ct" and int(item.get("raw", {}).get("value", 0)) > 0:
                health = "warn"
        smart_status = data.get("smart_status", {}).get("passed")
        if smart_status is False:
            health = "fail"
        temp = data.get("temperature", {}).get("current")
        if temp is None:
            for item in data.get("ata_smart_attributes", {}).get("table", []) or []:
                if item.get("name") in ("Temperature_Celsius", "Airflow_Temperature_Cel"):
                    temp = item.get("raw", {}).get("value")
                    break
        reallocated = 0
        for item in data.get("ata_smart_attributes", {}).get("table", []) or []:
            if item.get("name") == "Reallocated_Sector_Ct":
                reallocated = int(item.get("raw", {}).get("value", 0))
        return {
            "device": device,
            "model": data.get("model_name") or data.get("device", {}).get("name"),
            "health": health,
            "temp_c": temp,
            "reallocated_sectors": reallocated,
            "power_on_hours": data.get("power_on_time", {}).get("hours"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"device": device, "error": str(exc)[:300], "health": "unknown"}


def _disk_used_percent(mount: str) -> float | None:
    try:
        usage = shutil.disk_usage(mount)
        return round(100.0 * usage.used / usage.total, 2) if usage.total else None
    except Exception:  # noqa: BLE001
        return None


def collect(devices: list[str], mount: str) -> list[dict]:
    disks = []
    used_pct = _disk_used_percent(mount)
    for dev in devices:
        row = _parse_smartctl(dev) or {"device": dev, "health": "unknown"}
        if used_pct is not None:
            row["used_percent"] = used_pct
            row["mount"] = mount
        disks.append(row)
    return disks


def render_prometheus(disks: list[dict]) -> str:
    lines = [
        "# HELP minio_node_disk_smart_health SMART health 1=ok 0.5=warn 0=fail",
        "# TYPE minio_node_disk_smart_health gauge",
        "# HELP minio_node_disk_smart_temp_c Disk temperature",
        "# TYPE minio_node_disk_smart_temp_c gauge",
        "# HELP minio_node_disk_used_percent Disk used percent on mount",
        "# TYPE minio_node_disk_used_percent gauge",
        "# HELP minio_node_disk_reallocated_sectors Reallocated sectors",
        "# TYPE minio_node_disk_reallocated_sectors gauge",
    ]
    health_map = {"ok": 1.0, "warn": 0.5, "fail": 0.0, "unknown": -1.0}
    for d in disks:
        dev = d.get("device", "unknown")
        model = (d.get("model") or "unknown").replace('"', "'")
        h = health_map.get(str(d.get("health", "unknown")), -1.0)
        lines.append(f'minio_node_disk_smart_health{{device="{dev}",model="{model}"}} {h}')
        if d.get("temp_c") is not None:
            lines.append(f'minio_node_disk_smart_temp_c{{device="{dev}"}} {d["temp_c"]}')
        if d.get("used_percent") is not None:
            mount = d.get("mount") or "/data"
            lines.append(
                f'minio_node_disk_used_percent{{device="{dev}",mount="{mount}"}} {d["used_percent"]}'
            )
        if d.get("reallocated_sectors") is not None:
            lines.append(
                f'minio_node_disk_reallocated_sectors{{device="{dev}"}} {d["reallocated_sectors"]}'
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="MinIO node SMART exporter")
    parser.add_argument(
        "--devices",
        default=os.getenv("MINIO_SMART_DEVICES", "/dev/sda"),
        help="Список устройств через запятую",
    )
    parser.add_argument(
        "--mount",
        default=os.getenv("MINIO_DATA_MOUNT", "/data"),
        help="Mount point MinIO data",
    )
    parser.add_argument(
        "--textfile-dir",
        default=os.getenv("MINIO_SMART_TEXTFILE_DIR", "/var/lib/node_exporter/textfile"),
    )
    parser.add_argument(
        "--json-out",
        default=os.getenv("MINIO_SMART_JSON", ""),
        help="JSON sidecar для /storage/smart",
    )
    args = parser.parse_args()

    devices = [d.strip() for d in args.devices.split(",") if d.strip()]
    disks = collect(devices, args.mount)
    prom = render_prometheus(disks)

    out_dir = Path(args.textfile_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prom_path = out_dir / "minio_smart.prom"
    prom_path.write_text(prom, encoding="utf-8")

    payload = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "smart_disks": disks,
    }
    json_path = Path(args.json_out) if args.json_out else out_dir / "minio_smart.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[minio_smart] devices={len(disks)} prom={prom_path} json={json_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
