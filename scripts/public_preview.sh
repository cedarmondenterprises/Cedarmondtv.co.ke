#!/usr/bin/env bash
# Start a production-configured, publicly accessible HTTPS preview alongside
# the private preview. Does not expose the Django debug server.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${EUID}" -ne 0 ]]; then
  printf 'Run with sudo: sudo bash scripts/public_preview.sh PUBLIC_IPV4\n' >&2
  exit 1
fi

public_ip="${1:-}"
if ! python3 - "$public_ip" <<'PY'
import ipaddress, sys
try:
    addr = ipaddress.IPv4Address(sys.argv[1])
    assert addr.is_global
except (ValueError, IndexError, AssertionError):
    sys.exit("Provide a valid, publicly routable IPv4 address.")
PY
then
  exit 1
fi

hostname="${public_ip//./-}.sslip.io"
url="https://${hostname}"
if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
  printf 'Docker Engine and Docker Compose plugin are required.\n' >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  python3 scripts/configure.py
fi

# Update only non-secret public-host settings; preserve existing random secrets.
CEDARMOND_PUBLIC_HOST="$hostname" python3 - <<'PY'
import os
from pathlib import Path
p = Path(".env")
content = p.read_text().splitlines()
host = os.environ["CEDARMOND_PUBLIC_HOST"]
updates = {
    "DEBUG": "0",
    "DOMAIN": host,
    "SITE_URL": "https://" + host,
    "ALLOWED_HOSTS": host + ",localhost,127.0.0.1",
    "NEWSLETTER_ENABLED": "0",
}
seen = set()
result = []
for line in content:
    key = line.split("=", 1)[0] if "=" in line and not line.lstrip().startswith("#") else None
    if key in updates:
        result.append(key + "=" + updates[key])
        seen.add(key)
    else:
        result.append(line)
for key, value in updates.items():
    if key not in seen:
        result.append(key + "=" + value)
p.write_text("\n".join(result) + "\n")
p.chmod(0o600)
PY

export COMPOSE_PROJECT_NAME=cedarmondtv-public
echo "Deploying Cedarmond TV at ${url}"
echo "This is an independent production-configured Compose stack, not the DEBUG=1 local preview."
echo "AWS security group must allow inbound TCP 80 and 443 from the Internet."
bash scripts/deploy.sh

echo
echo "Services:"
docker compose ps
echo
echo "Browser address: ${url}"
echo "Admin login: ${url}/admin/"
echo "If the browser cannot connect, verify AWS security group inbound TCP 80/443,"
echo "host firewall rules, and Caddy certificate logs:"
echo "  sudo docker compose -p cedarmondtv-public logs --tail=100 caddy"
