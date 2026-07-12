#!/bin/sh
# MinIO site replication 2-node (§5.7 / §20)
set -eu
mc alias set m1 http://minio-1:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"
mc alias set m2 http://minio-2:9000 "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"

for b in photos models backups checkpoints; do
  mc mb --ignore-existing "m1/$b" || true
  mc mb --ignore-existing "m2/$b" || true
done

# Bucket replication m1 → m2 (и обратно для HA)
for b in photos models backups checkpoints; do
  mc replicate add "m1/$b" --remote-bucket "http://minio-2:9000/$b" \
    --access-key "$MINIO_ACCESS_KEY" --secret-key "$MINIO_SECRET_KEY" || true
  mc replicate add "m2/$b" --remote-bucket "http://minio-1:9000/$b" \
    --access-key "$MINIO_ACCESS_KEY" --secret-key "$MINIO_SECRET_KEY" || true
done

echo "MinIO replication configured"
sleep infinity
