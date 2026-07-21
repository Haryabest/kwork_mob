#!/bin/sh
# Healthcheck для Keepalived — MinIO live
curl -fsS "http://127.0.0.1:9000/minio/health/live" >/dev/null 2>&1
