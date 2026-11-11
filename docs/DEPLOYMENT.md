# Deployment and operations

## Infrastructure

Use a supported Ubuntu release with Docker Engine and the Compose plugin. Point the domain A record at the VM's stable public IP. Correct/remove stale AAAA records. Allow inbound TCP 80/443, optionally UDP 443, and restrict SSH access. Ensure persistent disk capacity for PostgreSQL, images and email logs.

`python3 scripts/configure.py` generates `.env` with independent random application/database secrets and restrictive file permissions. It refuses to overwrite existing configuration. Set the actual domain, `SITE_URL` and `ALLOWED_HOSTS`; production requires HTTPS and a sufficiently long secret.

Run `bash scripts/deploy.sh`, then create the first superuser. The script validates Compose, starts PostgreSQL/Valkey, builds images, applies migrations, creates permission groups and waits for services. No accounts, demo stories or policies are inserted.

## Existing applications on the same VM

The bundled Caddy owns ports 80/443. If an existing proxy serves Patapesa or another application, do not start the second proxy on those ports. Join Cedarmond's `web` service to the existing proxy's Docker network, configure a host route to it on port 8000, and mount Cedarmond's media volume read-only for `/media/`. Use an unambiguous upstream service alias if both projects name their service `web`. Keep PostgreSQL/Valkey private. The app trusts forwarding headers only with `TRUST_PROXY_HEADERS=1`; the upstream proxy must overwrite them and the application must not have a public host port.

For www, add a Caddy redirect to the canonical apex domain and configure DNS. Change all configured domains if deploying under another hostname.

## Email operations

Configure authenticated SMTP, TLS/SSL mode, sender identity, SPF/DKIM/DMARC and provider sending limits. Set `NEWSLETTER_ENABLED=1` and recreate `web`/`mail`. The separate mail container drains Post Office's database queue every 30 seconds, with up to three configured retries. Run only one mail worker instance with this configuration. Monitor failed messages in Post Office admin and the mail container logs. Do not enable a console backend in production.

Test signup with your own address, open the confirmation link, confirm it, send a small campaign, verify receipt, and unsubscribe. Confirm that unsubscribed recipients no longer receive queued newsletters. Never import or activate a mailing list without documented consent. Post Office delivery records contain recipient/content data: establish retention and regularly use its `cleanup_mail --days 30` command after validating your retention requirements. Configure bounce handling with your provider; automated bounce webhooks are not included.

## Editorial launch

Publish original reporting and authorized photographs. Create approved About/privacy/editorial policy Pages and publish them. Review staff roles and author attribution. Image uploads become WebP files (maximum dimension 1800px), with 640px thumbnails and metadata stripped. Keep archival originals outside the website if your newsroom needs them.

Revision history is read-only to prevent publication/ownership bypasses. Reporters submit their own drafts; editors publish. A local saved-story flag is a per-browser convenience, not an account-synced reading list. No sample feed, invented stories, dummy advertisements or external tracker is enabled.

## Updates

```bash
bash scripts/backup.sh
git pull --ff-only
bash scripts/deploy.sh
docker compose ps
docker compose logs --tail=100 web mail
```

Back up before every migration. For incompatible changes, schedule maintenance. Migration 0002 removes generated demo records but retains real articles. Historical image files are not automatically deleted, preserving older references; review orphan files separately.

## Backup and restore

`bash scripts/backup.sh` exports PostgreSQL and media into a private timestamped folder. Schedule it with your preferred operator tooling, copy it to encrypted offsite storage, and test restoring into an isolated new deployment. Keep `.env` separately in a credential store. Docker volumes alone are not backups.

Restore only into the intended recovery deployment. The database restore command replaces database objects:

```bash
docker compose stop web mail caddy
cat backups/YYYYMMDD-HHMMSS/database.dump | docker compose exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
cat backups/YYYYMMDD-HHMMSS/media.tar.gz | docker compose run --rm -T web tar xzf - -C /app
docker compose up -d
```

Use a fresh media volume for an exact snapshot restore; extracting over existing media overlays files. Pause publication/uploads while making a consistent database/media recovery snapshot when needed. Valkey contains disposable rate counters and does not require backup.

## Reliability and scale

Configure external uptime alerts for `/healthz/`, disk-space/log monitoring, dependency updates and a patch schedule. Valkey has a 128MB no-eviction limit so counters cannot be silently evicted; monitor capacity and availability. If cache access fails, form limiting fails closed rather than bypassing protection. Core health checks verify database access; SMTP and worker health need separate monitoring.

The bundled setup is single-host. For multiple web replicas, use shared PostgreSQL and object storage for media. Tune workers against CPU/RAM and actual traffic. TLS, DNS, provider limits and resource availability must be tested on the deployment; no infrastructure is guaranteed failure-free.
