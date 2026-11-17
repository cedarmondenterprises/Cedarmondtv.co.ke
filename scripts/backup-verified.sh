#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${RESTIC_REPOSITORY:?Set an off-server RESTIC_REPOSITORY}"
: "${RESTIC_PASSWORD_FILE:?Set RESTIC_PASSWORD_FILE to a root-readable password file}"
# Compose project/files must be supplied by the operator, as for deployment.
command -v restic >/dev/null
bash scripts/backup.sh
restic check
printf 'Backup uploaded and repository checked. Run verify-backup.sh for a full database restore test.\n'
