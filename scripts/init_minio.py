"""Скрипт инициализации MinIO buckets."""

import os
import sys

import boto3

endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
client = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
)

BUCKETS = ["photos", "models", "backups", "logs"]

for bucket in BUCKETS:
    try:
        client.create_bucket(Bucket=bucket)
        print(f"Created bucket: {bucket}")
    except client.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket exists: {bucket}")

print("Done")
