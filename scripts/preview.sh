#!/usr/bin/env bash
# Private on-host preview. Does not modify Patapesa or bind any public host port.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Engine and its Compose plugin first." >&2
  exit 1
fi
docker compose version >/dev/null

if [[ ! -f .env ]]; then
  python3 scripts/configure.py
fi

port="${CEDARMOND_PREVIEW_PORT:-18080}"
if ! [[ "$port" =~ ^[0-9]+$ ]] || (( 10#$port < 1024 || 10#$port > 65535 )); then
  echo "CEDARMOND_PREVIEW_PORT must be an integer from 1024 to 65535." >&2
  exit 1
fi

compose=(docker compose -p cedarmondtv-preview -f compose.yaml -f compose.preview.yaml)
"${compose[@]}" config --quiet
"${compose[@]}" up -d --wait --wait-timeout 120 db redis
"${compose[@]}" build web
"${compose[@]}" run --rm --no-deps web python manage.py migrate --noinput
"${compose[@]}" run --rm --no-deps web python manage.py setup_newsroom
"${compose[@]}" up -d --wait --wait-timeout 120 web
curl --fail --silent --show-error --retry 8 --retry-connrefused --retry-delay 2 "http://127.0.0.1:${port}/healthz/" >/dev/null

echo
echo "Cedarmond TV preview is healthy on the VM."
echo "Local VM URL: http://127.0.0.1:${port}/"
echo "From your phone, open a separate Termux SSH tunnel:"
echo "  ssh -N -L ${port}:127.0.0.1:${port} YOUR_EXISTING_AWS_SSH_HOST"
echo "Then open http://127.0.0.1:${port}/ in your phone browser."
echo "The site is NOT publicly exposed. Do not open the port in the AWS security group."
echo "Admin accounts are not generated automatically."
"${compose[@]}" ps
