#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
backup_dir="backups/$(date -u +%Y%m%d-%H%M%S)"
if [[ -n "${RESTIC_REPOSITORY:-}" ]]; then
    command -v restic >/dev/null || { printf 'Install restic before enabling off-server backups.\n' >&2; exit 1; }
fi
mkdir -p backups
mkdir "$backup_dir"
trap 'rm -rf -- "$backup_dir"' EXIT
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_dir/database.dump"
docker compose exec -T web tar czf - -C /app media > "$backup_dir/media.tar.gz"
trap - EXIT
printf 'Local backup saved to %s.\n' "$backup_dir"
if [[ -n "${RESTIC_REPOSITORY:-}" ]]; then
    restic backup --tag cedarmondtv "$backup_dir"
fi
