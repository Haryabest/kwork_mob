# MinIO SMART exporter (§21)

Cron на узле хранения (каждые 5 мин):

```bash
MINIO_SMART_DEVICES=/dev/nvme0n1 \
MINIO_SMART_TEXTFILE_DIR=/var/lib/node_exporter/textfile \
MINIO_SMART_JSON=/var/lib/node_exporter/textfile/minio_smart.json \
python3 exporter.py
```

Оркестратор: `MINIO_SMART_JSON=...` → `GET /api/v1/storage/smart` → `smart_disks[]`.
