#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { printf 'Run python3 scripts/configure.py first.
' >&2; exit 1; }
docker compose config --quiet
docker compose up -d db redis
docker compose build web mail
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py setup_newsroom
docker compose run --rm web python manage.py check --deploy
docker compose up -d --wait --wait-timeout 120
printf 'Deployment started. Create your administrator with: docker compose exec web python manage.py createsuperuser
'
