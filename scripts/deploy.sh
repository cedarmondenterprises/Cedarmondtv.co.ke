#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test -f .env || { printf 'Run python3 scripts/configure.py first.
' >&2; exit 1; }
docker compose config --quiet
docker compose build web mail
# Validate production security before applying migrations or updating the running stack.
docker compose run --rm --no-deps web python manage.py shell -c 'from django.conf import settings; import sys; sys.exit("Deployment refused: DEBUG is enabled." if settings.DEBUG else 0)'
docker compose run --rm --no-deps web python manage.py check --deploy
docker compose up -d db redis
docker compose run --rm web python manage.py makemigrations --check --dry-run
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py setup_newsroom
docker compose up -d --wait --wait-timeout 120
printf 'Deployment started. Create your administrator with: docker compose exec web python manage.py createsuperuser
'
