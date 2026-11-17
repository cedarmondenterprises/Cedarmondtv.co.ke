# Platform integrations

This branch integrates the twenty proposed tools into the existing Django site.
It does not provision third-party accounts, move production media, import subscribers,
send campaigns/notifications, or certify legal compliance. External credentials stay in
`.env` or a root-readable backup environment file. Nothing below enables staff 2FA by
itself: retain `NEWSROOM_2FA_REQUIRED=1` if already configured.

## Inventory and activation

| Integration | Delivered behaviour | Activation / verification |
| --- | --- | --- |
| Unfold | Light white/red admin, existing newsroom routes and OTP enforcement retained | Enabled by deployment; verify authoring and 2FA in preview |
| Import/export | CSV/Excel taxonomy import/export with validation and transactions | Categories/topics only; superusers only; no article publication or subscriber imports |
| ImageKit | Existing upload pipeline generates 1800px article and 640px card WebP images | Enabled for new uploads; existing images remain unchanged |
| django-storages | S3/R2-compatible public media backend | Set MEDIA_S3_* only after copying existing media and verifying URLs; bucket policy managed separately |
| Meilisearch | Public article index, typo-tolerant search, Django live-content recheck and database fallback | Set URL/key; start search/jobs profiles; run sync_search; verify search results |
| Umami | Consent-controlled external analytics script | Set HTTPS UMAMI_SCRIPT_URL and website ID; verify events in dashboard |
| Listmonk | Create newsletter drafts from ten public stories | Set URL/API username/token; configure provider and consented lists in Listmonk; explicit command only |
| Anymail | Provider email backend and bounce/complaint suppression | Example: anymail.backends.mailgun.EmailBackend plus MAILGUN_* and ANYMAIL_WEBHOOK_SECRET |
| pywebpush | CSRF-protected opt-in/out, ownership token, same-origin notification links | Generate VAPID keys; set WEBPUSH_ENABLED=1; explicit send command only |
| CookieConsent | Essential/analytics/advertising preferences, optional-script gating and reload on changes | Enabled; audit any manually inserted scripts and configured GTM tags separately |
| Celery | JSON-only background worker with resource limits | Start jobs profile; uses Redis DB 1 |
| django-celery-beat | Database schedules; public search refresh every 300 seconds | Exactly one beat; optional schedule settings in admin are privileged |
| GlitchTip | Uses existing Sentry SDK integration without a second SDK | Set SENTRY_DSN to GlitchTip project DSN; verify receipt, not just configuration |
| Uptime Kuma | Optional loopback-only monitoring container and admin link | Start monitoring profile or deploy on a separate host; create account/monitors through SSH tunnel |
| django-health-check | Database/cache diagnostic behind superuser and admin OTP checks | /admin/integrations/health/; generic result, no public infrastructure detail |
| Restic | Existing encrypted backups plus repository verification and daily timer templates | Install restic, initialize remote repository, configure credentials and timer; exercise restore |
| Guardian | Explicit view/edit grants for individual drafts | share_draft command; global model permissions still needed; no publishing privilege escalation |
| Auditlog | Changes to AdSense, direct ads and breaking ticker | Enabled; existing story/page history retained; no subscriber/contact/credential logging |
| axe-core | Mobile accessibility and consent browser checks | npm ci; npx playwright install --with-deps chromium; npm run test:a11y |
| pip-audit | CI Python dependency vulnerability scan | pip install -r requirements-dev.txt; pip-audit -r requirements.txt |

The private setup inventory is linked on the admin dashboard at `/admin/integrations/`.
"Configured" describes configuration, not a successful end-to-end connection.

## First deployment

Use preview first. Back up the production database and media before applying third-party
migrations. Keep local `Caddyfile` and template modifications: inspect `git status` before
merging. Do not use `git reset --hard` or a union merge for template conflicts.

All existing services must use the same updated application image. `scripts/deploy.sh`
now builds all selected Compose services, including the distribution worker.

```bash
sudo env COMPOSE_PROJECT_NAME=cedarmondtv-public COMPOSE_FILE=compose.yaml:compose.public.yaml:compose.distribution.yaml:compose.integrations.yaml bash scripts/deploy.sh
```

Optional services have profiles and do not start with this command. The application
packages/migrations, improved admin, consent, upload processing and private integration
page are installed together. Self-hosted services consume additional RAM and disk; the
existing 2-vCPU VM should not host every external service without capacity measurements.

### Search and scheduler

Generate a long random `MEILISEARCH_KEY` in `.env` and set
`MEILISEARCH_URL=http://meilisearch:7700`. This key never goes into public JavaScript.
Run commands with the same project and four Compose files as above:

```bash
sudo docker compose -p cedarmondtv-public -f compose.yaml -f compose.public.yaml -f compose.distribution.yaml -f compose.integrations.yaml --profile search --profile jobs up -d --build meilisearch celery beat
sudo docker compose -p cedarmondtv-public -f compose.yaml -f compose.public.yaml -f compose.distribution.yaml -f compose.integrations.yaml exec -T web python manage.py sync_search
```

After changing `.env`, recreate web/mail/distribution and selected workers to load it.
Index synchronization builds a staging index then swaps it, removing obsolete documents.
Only the designated Cedarmond indexes are touched. The search service is not published
on a host port. Results are capped at 200 and rechecked against current live stories.

### Analytics, advertising and consent

Set `UMAMI_SCRIPT_URL`, `UMAMI_WEBSITE_ID` and optionally `UMAMI_DASHBOARD_URL`.
Use `GTM_CONTAINER_ID` for GTM; remove any duplicate manually inserted GTM script only
after reviewing its diff. GTM tags must also enforce the corresponding consent category;
loading the container does not configure its tags. No tracking ID is hard-coded.
Existing configured AdSense slots initialize only after advertising consent. CookieConsent
is not a Google-certified CMP and is not a substitute where a certified CMP is required.
Existing cookies set by third parties may persist after revocation; optional scripts stop
loading after the page reload. Review cookie disclosures against actual deployed tags.

### Newsletter and email

Choose a Listmonk host and configure its sender, double opt-in and unsubscribe handling.
No existing subscriber records are silently copied or overwritten. Create a draft with:

```bash
python manage.py listmonk_draft --list-id 1 --subject 'The Cedarmond Briefing'
```

The command makes one create-draft API request. Review and send inside Listmonk.
For existing Django/Post Office mail, choose the Anymail backend in `EMAIL_BACKEND` and
configure provider credentials. Webhook routes are absent unless `ANYMAIL_WEBHOOK_SECRET`
is set. Configure the provider's authenticated webhook using Anymail's provider docs;
Mailgun's endpoint is `/integrations/anymail/mailgun/tracking/`. Test bounce/complaint
handling with the provider sandbox before sending a real campaign. Keep only one system
responsible for each mailing list to avoid duplicate sends.

### Browser notifications

Generate VAPID keys with py-vapid on the server. Keep the private key secret; configure
`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_CONTACT=mailto:YOUR_REAL_ADDRESS` and
`WEBPUSH_ENABLED=1`. The private key may be a PEM/key value supported by py-vapid.
Only explicit clicks subscribe readers. Test the actual browsers you support.

```bash
python manage.py send_story_push ARTICLE_ID
python manage.py send_story_push ARTICLE_ID --send
```

The first command is a dry run. The second contacts opted-in browsers; never run it as
part of deployment. Failed 404/410 subscriptions are deleted. Delivery is not automatic
and the operator should avoid sending the same story repeatedly.

### Media storage

The default remains the existing media volume. Before setting `MEDIA_S3_ENABLED=1`,
copy all existing paths to the chosen bucket and test public read access and CORS.
Do not put database backups in the public-media bucket. `MEDIA_S3_CUSTOM_DOMAIN` is a
hostname without a scheme. Local media archives no longer cover new remote uploads:
configure bucket versioning/backups separately before enabling remote media.

### Backup and monitoring

Restic is a host tool. Keep passwords in a root-readable password file; point
`RESTIC_PASSWORD_FILE` to it. Initialize a genuinely off-server repository first.
`/etc/cedarmond-backup.env` should contain `CEDARMOND_PROJECT_DIR`, `COMPOSE_PROJECT_NAME`,
`COMPOSE_FILE`, `RESTIC_REPOSITORY`, `RESTIC_PASSWORD_FILE` and storage credentials.
Use absolute paths for COMPOSE_FILE in this file. Install the supplied service/timer in
`/etc/systemd/system/`, then `systemctl daemon-reload` and
`systemctl enable --now cedarmond-backup.timer`. This is not installed automatically.

Run `scripts/verify-backup.sh backups/TIMESTAMP` with the production Compose variables
to restore into an isolated disposable Postgres container. `restic check` alone is not
a restore test. Before turning on S3 media, extend the backup plan to include that bucket.
No snapshot deletion/retention pruning is automatic.

Uptime Kuma profile binds only `127.0.0.1:13001`; access through an SSH tunnel and create
its account immediately. Monitoring on a separate host can detect a full VM outage.
Do not open its dashboard to the internet without authentication and TLS.

### Staff collaboration

```bash
python manage.py share_draft ARTICLE_ID STAFF_USERNAME
python manage.py share_draft ARTICLE_ID STAFF_USERNAME --edit
python manage.py share_draft ARTICLE_ID STAFF_USERNAME --revoke
```

Only the selected draft is shared. Published articles remain read-only for non-publishers.
No new staff global permissions are assigned automatically.

## Verification and rollback

Run the full Django suite, migrations check and OTP tests before production. Keep browser
checks in CI and inspect the light admin at phone/desktop widths before merging. Preserve
a pre-deployment backup; do not unapply third-party migrations casually. Disable optional
credentials/profiles to turn off integrations. Reverting code should retain the new database
tables until a separately tested rollback is prepared.
