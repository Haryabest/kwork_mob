"""Интеграция с MinIO (S3-совместимое хранилище)."""

from __future__ import annotations

import uuid
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class MinioService:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    @property
    def buckets(self) -> list[str]:
        return [
            settings.MINIO_BUCKET_PHOTOS,
            settings.MINIO_BUCKET_MODELS,
            settings.MINIO_BUCKET_BACKUPS,
            "logs",
        ]

    def ensure_buckets(self) -> list[str]:
        """Создать buckets, если их нет."""
        existing = {b["Name"] for b in self.client.list_buckets().get("Buckets", [])}
        created: list[str] = []
        for name in self.buckets:
            if name not in existing:
                self.client.create_bucket(Bucket=name)
                created.append(name)
        return created

    def health(self) -> dict[str, Any]:
        try:
            buckets = [b["Name"] for b in self.client.list_buckets().get("Buckets", [])]
            return {"ok": True, "endpoint": settings.MINIO_ENDPOINT, "buckets": buckets}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "endpoint": settings.MINIO_ENDPOINT, "error": str(exc)}

    def smart(self) -> dict[str, Any]:
        """SMART / disk usage proxy для admin Storage (§21).

        MinIO не отдаёт ATA SMART через S3 API — собираем usage по бакетам +
        опциональный admin endpoint (MINIO_ADMIN_ENDPOINT / mc admin info).
        """
        base = self.health()
        if not base.get("ok"):
            return {**base, "smart": None, "usage": []}
        usage = []
        total_bytes = 0
        for name in base.get("buckets") or []:
            size = 0
            count = 0
            try:
                paginator = self.client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=name):
                    for obj in page.get("Contents") or []:
                        size += int(obj.get("Size") or 0)
                        count += 1
            except Exception as exc:  # noqa: BLE001
                usage.append({"bucket": name, "error": str(exc)[:200]})
                continue
            total_bytes += size
            usage.append({"bucket": name, "objects": count, "bytes": size})
        # Порог алерта: > 85% если задан MINIO_DISK_TOTAL_BYTES
        disk_total = int(getattr(settings, "MINIO_DISK_TOTAL_BYTES", 0) or 0)
        pct = round(100 * total_bytes / disk_total, 2) if disk_total > 0 else None
        alert = bool(pct is not None and pct >= 85)
        return {
            **base,
            "usage": usage,
            "total_bytes": total_bytes,
            "disk_total_bytes": disk_total or None,
            "used_percent": pct,
            "alert_disk_high": alert,
            "smart": {
                "source": "s3_usage",
                "note": "ATA SMART — через агент узла хранения; здесь usage бакетов",
                "status": "warn" if alert else "ok",
            },
        }

    def uuid_key(self, prefix: str, filename: str = "") -> str:
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()[:10]
        return f"{prefix.rstrip('/')}/{uuid.uuid4().hex}{ext}"

    def generate_presigned_url(
        self, bucket: str, key: str, expires: int = 1800, method: str = "get_object"
    ) -> str:
        """Presigned URL: get_object (скачивание) или put_object (загрузка)."""
        return self.client.generate_presigned_url(
            method,
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires,
        )

    def upload_bytes(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        return f"s3://{bucket}/{key}"

    def upload_file(self, bucket: str, key: str, file_path: str) -> str:
        self.client.upload_file(file_path, bucket, key)
        return f"s3://{bucket}/{key}"

    def object_exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False

    def download_bytes(self, bucket: str, key: str) -> bytes:
        obj = self.client.get_object(Bucket=bucket, Key=key)
        try:
            return obj["Body"].read()
        finally:
            try:
                obj["Body"].close()
            except Exception:  # noqa: BLE001
                pass


minio_service = MinioService()
