"""MinIO native lifecycle policies §9.5."""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from app.core.config import settings
from app.services.minio import minio_service

EXPECTED_RULES: list[dict[str, Any]] = [
    {"bucket_key": "photos", "days": 30, "prefix": ""},
    {"bucket_key": "backups_user", "days": 30, "prefix": "backups/"},
    {"bucket_key": "backups_pg", "days": 365, "prefix": "postgres/"},
    {"bucket_key": "models", "days": 30, "prefix": ""},
]


def _bucket_name(key: str) -> str:
    mapping = {
        "photos": settings.MINIO_BUCKET_PHOTOS,
        "models": settings.MINIO_BUCKET_MODELS,
        "backups_user": settings.MINIO_BUCKET_BACKUPS,
        "backups_pg": settings.MINIO_BUCKET_BACKUPS,
    }
    return mapping.get(key, key)


def _photos_days() -> int:
    return max(7, min(int(getattr(settings, "SOURCE_PHOTOS_TTL_DAYS", 30) or 30), 90))


def expected_rules() -> list[dict[str, Any]]:
    days = _photos_days()
    out: list[dict[str, Any]] = []
    for spec in EXPECTED_RULES:
        bucket = _bucket_name(spec["bucket_key"])
        rule_days = days if spec["bucket_key"] in ("photos", "backups_user", "models") else spec["days"]
        out.append(
            {
                "bucket": bucket,
                "bucket_key": spec["bucket_key"],
                "prefix": spec["prefix"],
                "expire_days": rule_days,
            }
        )
    return out


def _rule_matches(rule: dict, *, prefix: str, days: int) -> bool:
    if rule.get("Status") != "Enabled":
        return False
    filt = rule.get("Filter") or {}
    rule_prefix = filt.get("Prefix", "")
    if rule_prefix != prefix:
        return False
    exp = rule.get("Expiration") or {}
    return int(exp.get("Days") or 0) == days


def get_lifecycle_status() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for spec in expected_rules():
        bucket = spec["bucket"]
        try:
            cfg = minio_service.client.get_bucket_lifecycle_configuration(Bucket=bucket)
            rules = cfg.get("Rules") or []
            ok = any(
                _rule_matches(r, prefix=spec["prefix"], days=spec["expire_days"]) for r in rules
            )
            items.append(
                {
                    "bucket": bucket,
                    "prefix": spec["prefix"],
                    "expire_days": spec["expire_days"],
                    "configured": ok,
                    "rules_count": len(rules),
                }
            )
        except ClientError:
            items.append(
                {
                    "bucket": bucket,
                    "prefix": spec["prefix"],
                    "expire_days": spec["expire_days"],
                    "configured": False,
                    "rules_count": 0,
                }
            )
        except Exception as exc:  # noqa: BLE001
            items.append(
                {
                    "bucket": bucket,
                    "prefix": spec["prefix"],
                    "expire_days": spec["expire_days"],
                    "configured": False,
                    "error": str(exc)[:200],
                }
            )
    return {"items": items, "all_configured": all(i.get("configured") for i in items)}


def apply_default_lifecycle() -> dict[str, Any]:
    applied: list[str] = []
    errors: list[dict[str, str]] = []
    for spec in expected_rules():
        bucket = spec["bucket"]
        prefix = spec["prefix"]
        days = spec["expire_days"]
        rules = {
            "Rules": [
                {
                    "ID": f"expire-{bucket}-{prefix or 'root'}-{days}d",
                    "Status": "Enabled",
                    "Filter": {"Prefix": prefix},
                    "Expiration": {"Days": days},
                }
            ]
        }
        try:
            minio_service.client.put_bucket_lifecycle_configuration(
                Bucket=bucket, LifecycleConfiguration=rules
            )
            applied.append(f"{bucket}:{prefix or '/'}")
        except Exception as exc:  # noqa: BLE001
            errors.append({"bucket": bucket, "prefix": prefix, "error": str(exc)[:200]})
    status = get_lifecycle_status()
    return {"applied": applied, "errors": errors, **status}
