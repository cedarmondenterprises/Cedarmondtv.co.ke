#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
backup_dir="backups/$(date -u +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_dir/database.dump"
docker compose exec -T web tar czf - -C /app media > "$backup_dir/media.tar.gz"
printf 'Backup saved to %s. Copy it to encrypted offsite storage.
' "$backup_dir"
