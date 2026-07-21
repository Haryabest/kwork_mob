"""Инициализация MinIO buckets + lifecycle §9: photos/backups 30 дней."""

from __future__ import annotations

import json
import os
import sys

import boto3
from botocore.client import Config

endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    config=Config(signature_version="s3v4"),
)

BUCKETS = ["photos", "models", "backups", "logs"]
PHOTOS_DAYS = int(os.getenv("MINIO_PHOTOS_EXPIRE_DAYS", "30"))
BACKUPS_DAYS = int(os.getenv("MINIO_BACKUPS_EXPIRE_DAYS", "365"))


def ensure_buckets() -> None:
    for bucket in BUCKETS:
        try:
            client.create_bucket(Bucket=bucket)
            print(f"Created bucket: {bucket}")
        except client.exceptions.BucketAlreadyOwnedByYou:
            print(f"Bucket exists: {bucket}")
        except Exception as exc:  # noqa: BLE001
            # MinIO may raise differently
            if "BucketAlreadyOwnedByYou" in type(exc).__name__ or "BucketAlreadyExists" in str(exc):
                print(f"Bucket exists: {bucket}")
            else:
                print(f"Bucket {bucket}: {exc}")


def put_lifecycle(bucket: str, days: int, prefix: str = "") -> None:
    rules = {
        "Rules": [
            {
                "ID": f"expire-{bucket}-{days}d",
                "Status": "Enabled",
                "Filter": {"Prefix": prefix},
                "Expiration": {"Days": days},
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration=rules)
    print(f"Lifecycle {bucket}: expire {days}d prefix={prefix!r}")
    print(json.dumps(rules, indent=2))


def main() -> None:
    ensure_buckets()
    try:
        put_lifecycle("photos", PHOTOS_DAYS)
    except Exception as exc:  # noqa: BLE001
        print(f"photos lifecycle failed: {exc}", file=sys.stderr)
    try:
        put_lifecycle("backups", PHOTOS_DAYS, prefix="backups/")
    except Exception as exc:  # noqa: BLE001
        print(f"backups user lifecycle failed: {exc}", file=sys.stderr)
    try:
        put_lifecycle("backups", BACKUPS_DAYS, prefix="postgres/")
    except Exception as exc:  # noqa: BLE001
        print(f"backups lifecycle failed: {exc}", file=sys.stderr)
    print("Done")


if __name__ == "__main__":
    main()
