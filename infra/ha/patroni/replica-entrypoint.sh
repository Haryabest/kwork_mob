#!/bin/sh
# Streaming replica bootstrap (упрощённый Patroni-совместимый standby).
set -eu
DATA=/var/lib/postgresql/data
if [ ! -s "$DATA/PG_VERSION" ]; then
  echo "Waiting for primary..."
  until pg_isready -h postgres-primary -U "${POSTGRES_USER:-kwork}"; do sleep 2; done
  export PGPASSWORD="${POSTGRES_PASSWORD:-kwork_secret}"
  pg_basebackup -h postgres-primary -D "$DATA" -U "${POSTGRES_USER:-kwork}" -Fp -Xs -P -R || {
    echo "pg_basebackup failed — ensure primary allows replication"
    sleep 5
    exit 1
  }
fi
exec postgres -c hot_standby=on
