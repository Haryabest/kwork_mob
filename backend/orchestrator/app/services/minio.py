"""Интеграция с MinIO (S3-совместимое хранилище) + SSE §10.6.3."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


def resolve_kms_key_id() -> str | None:
    """Ключ SSE-KMS: env MINIO_KMS_KEY_ID или Vault."""
    key = (settings.MINIO_KMS_KEY_ID or "").strip()
    if key:
        return key
    if not settings.VAULT_ADDR or not settings.VAULT_TOKEN:
        return None
    try:
        import httpx

        path = settings.VAULT_MINIO_KMS_KEY_PATH.lstrip("/")
        url = f"{settings.VAULT_ADDR.rstrip('/')}/v1/{path}"
        r = httpx.get(url, headers={"X-Vault-Token": settings.VAULT_TOKEN}, timeout=5.0)
        r.raise_for_status()
        data = r.json().get("data") or {}
        # KV v2: data.data.key_id | data.key_id
        nested = data.get("data") if isinstance(data.get("data"), dict) else data
        return (nested.get("key_id") or nested.get("value") or "").strip() or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vault KMS key fetch failed: %s", exc)
        return None


class MinioService:
    def __init__(self) -> None:
        vip = (getattr(settings, "MINIO_VIP", "") or "").strip()
        self._primary_endpoint = vip or settings.MINIO_ENDPOINT
        self._replica_endpoint = (getattr(settings, "MINIO_REPLICA_ENDPOINT", "") or "").strip()
        self.client = self._make_client(self._primary_endpoint)
        self._replica_client = (
            self._make_client(self._replica_endpoint) if self._replica_endpoint else None
        )

    @staticmethod
    def _make_client(endpoint: str):
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def _clients_for_read(self) -> list[Any]:
        clients = [self.client]
        if self._replica_client is not None:
            clients.append(self._replica_client)
        return clients

    @property
    def buckets(self) -> list[str]:
        return [
            settings.MINIO_BUCKET_PHOTOS,
            settings.MINIO_BUCKET_MODELS,
            settings.MINIO_BUCKET_BACKUPS,
            "logs",
            "audit-logs",
        ]

    def sse_mode(self) -> str:
        mode = (settings.MINIO_SSE_MODE or "sse-s3").strip().lower()
        if mode not in ("none", "sse-s3", "sse-kms"):
            return "sse-s3"
        return mode

    def encryption_extra_args(self) -> dict[str, str]:
        """Args для put_object / upload_file (§10.6.3)."""
        mode = self.sse_mode()
        if mode == "none":
            return {}
        if mode == "sse-kms":
            key_id = resolve_kms_key_id()
            if not key_id:
                logger.warning("SSE-KMS без key id — fallback SSE-S3")
                return {"ServerSideEncryption": "AES256"}
            return {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": key_id}
        return {"ServerSideEncryption": "AES256"}

    def encryption_status(self) -> dict[str, Any]:
        mode = self.sse_mode()
        key = resolve_kms_key_id() if mode == "sse-kms" else None
        return {
            "mode": mode,
            "kms_key_configured": bool(key),
            "kms_key_id_masked": (f"{key[:4]}…{key[-4:]}" if key and len(key) > 8 else ("***" if key else None)),
            "buckets": self.buckets,
        }

    def ensure_buckets(self) -> list[str]:
        """Создать buckets + default encryption."""
        existing = {b["Name"] for b in self.client.list_buckets().get("Buckets", [])}
        created: list[str] = []
        for name in self.buckets:
            if name not in existing:
                self.client.create_bucket(Bucket=name)
                created.append(name)
            self._apply_bucket_encryption(name)
        self._ensure_cors()
        return created

    def ensure_bucket(self, name: str) -> bool:
        """Создать один bucket + SSE (§9.5.1 dedicated B2B)."""
        existing = {b["Name"] for b in self.client.list_buckets().get("Buckets", [])}
        created = name not in existing
        if created:
            self.client.create_bucket(Bucket=name)
        self._apply_bucket_encryption(name)
        return created

    def _apply_bucket_encryption(self, bucket: str) -> None:
        mode = self.sse_mode()
        if mode == "none":
            try:
                self.client.delete_bucket_encryption(Bucket=bucket)
            except ClientError:
                pass
            return
        if mode == "sse-kms":
            key_id = resolve_kms_key_id()
            if key_id:
                rules = {
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "aws:kms",
                                "KMSMasterKeyID": key_id,
                            },
                            "BucketKeyEnabled": True,
                        }
                    ]
                }
            else:
                rules = {
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                            "BucketKeyEnabled": True,
                        }
                    ]
                }
        else:
            rules = {
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                        "BucketKeyEnabled": True,
                    }
                ]
            }
        try:
            self.client.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration=rules)
        except ClientError as exc:
            logger.warning("put_bucket_encryption %s: %s", bucket, exc)

    def _ensure_cors(self) -> None:
        origins = list(settings.CORS_ORIGINS)
        if settings.is_development and "*" not in origins:
            origins.append("*")
        cors = {
            "CORSRules": [
                {
                    "AllowedOrigins": origins or ["*"],
                    "AllowedMethods": ["GET", "HEAD", "PUT", "POST"],
                    "AllowedHeaders": ["*"],
                    "ExposeHeaders": ["ETag", "Content-Length"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        }
        for name in self.buckets:
            try:
                self.client.put_bucket_cors(Bucket=name, CORSConfiguration=cors)
            except Exception:  # noqa: BLE001
                pass

    def health(self) -> dict[str, Any]:
        replica = self._replica_endpoint or None
        for label, client, endpoint in (
            ("primary", self.client, self._primary_endpoint),
            ("replica", self._replica_client, replica),
        ):
            if client is None:
                continue
            try:
                buckets = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
                return {
                    "ok": True,
                    "endpoint": endpoint,
                    "active": label,
                    "replica_endpoint": replica,
                    "buckets": buckets,
                    "encryption": self.encryption_status(),
                }
            except Exception as exc:  # noqa: BLE001
                if label == "primary" and self._replica_client is not None:
                    continue
                return {
                    "ok": False,
                    "endpoint": endpoint,
                    "replica_endpoint": replica,
                    "error": str(exc),
                }
        return {"ok": False, "endpoint": self._primary_endpoint, "replica_endpoint": replica}

    def _load_smart_disks(self) -> list[dict[str, Any]]:
        """JSON sidecar с узла MinIO (minio_smart_exporter)."""
        import json
        from pathlib import Path

        path = (getattr(settings, "MINIO_SMART_JSON", "") or "").strip()
        if not path:
            return []
        try:
            raw = Path(path).read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                if isinstance(data.get("smart_disks"), list):
                    return data["smart_disks"]
                if isinstance(data.get("disks"), list):
                    return data["disks"]
        except Exception:  # noqa: BLE001
            return []
        return []

    def _load_cluster_ha(self) -> dict[str, Any]:
        """HA snapshot: MinIO replication / PG lag / node heartbeat (§11.16.2)."""
        import json
        from pathlib import Path

        out: dict[str, Any] = {
            "minio_replication": [],
            "postgres": {},
            "nodes": [],
            "source": None,
        }
        path = (getattr(settings, "MINIO_HA_JSON", "") or getattr(settings, "MINIO_SMART_JSON", "") or "").strip()
        if not path:
            return out
        try:
            raw = Path(path).read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return out
            out["source"] = path
            if isinstance(data.get("minio_replication"), list):
                out["minio_replication"] = data["minio_replication"]
            elif isinstance(data.get("replication"), list):
                out["minio_replication"] = data["replication"]
            if isinstance(data.get("postgres"), dict):
                out["postgres"] = data["postgres"]
            if isinstance(data.get("nodes"), list):
                out["nodes"] = data["nodes"]
            # если весь файл — только replication list в корне smart json
            if isinstance(data.get("ha"), dict):
                ha = data["ha"]
                if isinstance(ha.get("minio_replication"), list):
                    out["minio_replication"] = ha["minio_replication"]
                if isinstance(ha.get("postgres"), dict):
                    out["postgres"] = ha["postgres"]
                if isinstance(ha.get("nodes"), list):
                    out["nodes"] = ha["nodes"]
        except Exception:  # noqa: BLE001
            return out
        return out

    def smart(self) -> dict[str, Any]:
        h = self.health()
        usage: list[dict[str, Any]] = []
        total_bytes = 0
        for name in self.buckets:
            try:
                paginator = self.client.get_paginator("list_objects_v2")
                objects = 0
                size = 0
                for page in paginator.paginate(Bucket=name):
                    for obj in page.get("Contents") or []:
                        objects += 1
                        size += int(obj.get("Size") or 0)
                usage.append({"bucket": name, "objects": objects, "bytes": size})
                total_bytes += size
            except Exception as exc:  # noqa: BLE001
                usage.append({"bucket": name, "error": str(exc)})
        disk_total = int(settings.MINIO_DISK_TOTAL_BYTES or 0)
        used_percent = round(100.0 * total_bytes / disk_total, 1) if disk_total > 0 else None
        free_percent = round(100.0 - used_percent, 1) if used_percent is not None else None
        disks = self._load_smart_disks()
        ha = self._load_cluster_ha()
        status = "ok"
        if used_percent is not None and used_percent >= 85:
            status = "disk_high"
        if used_percent is not None and used_percent >= 95:
            status = "disk_critical"
        if free_percent is not None and free_percent < 10:
            status = "disk_critical"
        if any((d.get("health") or "").lower() in ("fail", "failed", "critical") for d in disks):
            status = "smart_fail"
        elif any(
            int(d.get("reallocated_sectors") or 0) > 0
            or (d.get("health") or "").lower() in ("warn", "warning")
            for d in disks
        ):
            if status == "ok":
                status = "smart_warn"
        repl = ha.get("minio_replication") or []
        repl_failed = [
            r
            for r in repl
            if str(r.get("status") or "").lower() in ("failed", "fail", "error", "paused")
        ]
        return {
            **h,
            "usage": usage,
            "total_bytes": total_bytes,
            "disk_total_bytes": disk_total or None,
            "used_percent": used_percent,
            "free_percent": free_percent,
            "alert_disk_high": used_percent is not None and used_percent >= 85,
            "alert_disk_critical": (used_percent is not None and used_percent >= 95)
            or (free_percent is not None and free_percent < 10),
            "smart": {
                "status": status,
                "source": "minio_smart_exporter" if disks else "s3_usage",
                "note": f"SSE: {self.sse_mode()}; ATA SMART — агент узла / usage бакетов",
            },
            "smart_disks": disks,
            "cluster_ha": ha,
            "alert_replication_failed": bool(repl_failed),
            "encryption": self.encryption_status(),
        }

    def delete_prefix(self, bucket: str, prefix: str) -> int:
        """Удалить все объекты с префиксом. Возвращает число удалённых."""
        deleted = 0
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            objs = page.get("Contents") or []
            if not objs:
                continue
            # delete_objects max 1000
            for i in range(0, len(objs), 1000):
                chunk = objs[i : i + 1000]
                self.client.delete_objects(
                    Bucket=bucket,
                    Delete={"Objects": [{"Key": o["Key"]} for o in chunk], "Quiet": True},
                )
                deleted += len(chunk)
        return deleted

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
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        kwargs.update(self.encryption_extra_args())
        self.client.put_object(**kwargs)
        return f"s3://{bucket}/{key}"

    def upload_file(self, bucket: str, key: str, file_path: str) -> str:
        extra = self.encryption_extra_args()
        if extra:
            self.client.upload_file(file_path, bucket, key, ExtraArgs=extra)
        else:
            self.client.upload_file(file_path, bucket, key)
        return f"s3://{bucket}/{key}"

    def object_exists(self, bucket: str, key: str) -> bool:
        for client in self._clients_for_read():
            try:
                client.head_object(Bucket=bucket, Key=key)
                return True
            except ClientError:
                continue
        return False

    def download_bytes(self, bucket: str, key: str) -> bytes:
        last_exc: Exception | None = None
        for client in self._clients_for_read():
            try:
                obj = client.get_object(Bucket=bucket, Key=key)
                try:
                    return obj["Body"].read()
                finally:
                    try:
                        obj["Body"].close()
                    except Exception:  # noqa: BLE001
                        pass
            except ClientError as exc:
                last_exc = exc
        if last_exc:
            raise last_exc
        raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

    def list_objects(self, bucket: str, prefix: str = "") -> list[str]:
        keys: list[str] = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents") or []:
                keys.append(obj["Key"])
        return keys


minio_service = MinioService()
