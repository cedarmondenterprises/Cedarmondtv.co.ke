#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
backup_dir=${1:?Usage: bash scripts/verify-backup.sh BACKUP_DIRECTORY}
backup_dir=$(realpath "$backup_dir")
test -s "$backup_dir/database.dump"
test -s "$backup_dir/media.tar.gz"
image=$(docker compose images -q db)
test -n "$image"

docker run --rm --network none --mount "type=bind,src=$backup_dir,dst=/backup,readonly" \
    --entrypoint sh "$image" -ec '
    work=$(mktemp -d)
    chown postgres:postgres "$work"
    su-exec postgres initdb -D "$work/data" >/dev/null
    su-exec postgres pg_ctl -D "$work/data" -o "-k $work -c listen_addresses=" -w start >/dev/null
    trap '\''su-exec postgres pg_ctl -D "$work/data" -m fast stop >/dev/null'\'' EXIT
    createdb -h "$work" -U postgres recovery
    pg_restore -h "$work" -U postgres --exit-on-error --no-owner --no-privileges -d recovery /backup/database.dump
    psql -h "$work" -U postgres -d recovery -v ON_ERROR_STOP=1 -c "SELECT count(*) AS restored_articles FROM news_article"
    mkdir "$work/media-check"
    tar -xzf /backup/media.tar.gz -C "$work/media-check"
    test -d "$work/media-check/media"
    printf "Database restored and media archive extracted.\n"
'
