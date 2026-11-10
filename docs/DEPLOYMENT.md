# Deployment and operations

## Existing VM with other applications

The provided Compose file is for a host with free ports 80/443. If another Caddy/Nginx/Traefik proxy is already running, do not run the bundled `caddy` service on the same ports. Join `web` to the existing proxy's network, route this domain to `web:8000`, and mount the media volume read-only in that proxy for `/media/`. Keep the database on the internal network. The app trusts proxy HTTPS and client-IP headers, so do not expose its port directly to the internet. Configure trusted origins and `ALLOWED_HOSTS` for every actual hostname.

For a different domain, update `DOMAIN`, `SITE_URL`, `ALLOWED_HOSTS`, SMTP sender and any branding/legal contact text. The environment template assumes only the apex domain; add an explicit www redirect if desired.

## Before public launch

- Publish original verified content; remove or unpublish all demo stories.
- Review About, editorial standards and privacy copy; confirm the legal operator and data handling practices.
- Configure authenticated SMTP, SPF/DKIM/DMARC and confirm delivery; every campaign must include unsubscribe.
- Add real images with documented permissions and accurate credits/alt text.
- Exercise reporter and editor accounts; keep superuser access restricted. Strong passwords and login lockout are included; MFA is not yet included.
- Test mobile layouts, search, contact submissions, publishing and HTTPS on the real domain.
- Set up external uptime monitoring, patching, offsite backups and log retention. No analytics/ad tracking is enabled by default.
- Session-based public-form throttles can be bypassed with new cookies; add reverse-proxy/IP rate limiting or a managed challenge if spam appears.

## Updates

Back up first. Pull the reviewed code, build, migrate, then restart:

```bash
bash scripts/backup.sh
git pull --ff-only
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose up -d
docker compose ps
docker compose logs --tail=100 web
```

The web image collects static files at build time. Uploaded media persists separately. Database migrations must succeed before switching to new code. For incompatible schema changes, plan a maintenance window and explicit rollback.

## Restore drill

Restore only into an isolated new deployment first. `--clean` replaces data, so never run against the live database without a separate verified backup and an explicit recovery plan.

```bash
# Replace the date directory with the intended backup; verify it first.
docker compose stop web caddy
cat backups/YYYYMMDD-HHMMSS/database.dump | docker compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
cat backups/YYYYMMDD-HHMMSS/media.tar.gz | docker compose run --rm -T web tar xzf - -C /app
docker compose up -d
```

A media restore overlays files. Use a fresh volume for a faithful snapshot restore. Back up `.env` separately in a secure credential store. Keep secrets out of the repository and ordinary ZIP exports.

## Portability and sizing

Start with one Linux VM, persistent PostgreSQL and media volumes. Adjust Gunicorn workers to available RAM/CPU and load-test. For multiple web replicas, move media to shared object storage and use a managed/shared PostgreSQL service; the default local-media setup is single-host. Caddy needs outbound internet and reachable DNS for certificate issuance. Availability depends on DNS, storage, resources and correct configuration; no deployment is guaranteed problem-free.

## Newsletter operations

Subscriptions are activated only after a signed confirmation POST. Confirmation links expire after 48 hours. Unsubscribe links do not expire. Generate a recipient-specific unsubscribe URL using `python manage.py newsletter_links user@example.com` and include it in every future campaign. Campaign composition, batching, bounce handling and scheduled delivery are not implemented in this foundation. Console email is a development fallback; SMTP must be configured before launch.
