# Cedarmond TV

A working, self-hosted Kenyan news publishing application for **cedarmondtv.co.ke**. The red-and-white interface is original; the publishing infrastructure uses established open-source components. Articles, pages, photographs, authors and advertising are managed in the newsroom. No fabricated articles, demo seed command, stock-photo content or dummy advertising placements ship with this version.

## Open-source architecture

- **Django + PostgreSQL**: publishing, permissions, durable content and subscriber records.
- **django-prose-editor (Tiptap/ProseMirror) + nh3**: rich-text editing and server-side HTML sanitization.
- **django-simple-history**: timestamped article/page revision records and author tracking. Editors can review a revision and restore its text into a separate unpublished draft, keeping the live article intact.
- **django-post-office**: durable SMTP queue, delivery logs, retries and an independent worker.
- **Valkey + django-redis + django-ratelimit**: cross-worker IP limits for public forms.
- **Pillow**: WebP photographs, small card thumbnails, metadata removal.
- **django-axes, WhiteNoise, Gunicorn and Caddy**: authentication lockout, compressed static assets, application serving and HTTPS.
- **Django REST Framework + drf-spectacular**: versioned, read-only JSON API for published stories, sections, authors and topics; self-hosted OpenAPI/Swagger/ReDoc docs. No paid API keys or external documentation CDN are required.

See [OPEN_SOURCE.md](docs/OPEN_SOURCE.md) for upstream projects and licenses. Python versions are pinned in `requirements.txt`.

## 20 working publishing capabilities

| # | Capability | Behavior |
|---|---|---|
| 1 | Responsive news homepage | Curated lead, latest stories and editorial selection |
| 2 | Section archives | Kenya, Politics, Counties, Business, Technology, Culture, Sports and Opinion |
| 3 | Rich-text publishing | Headings, emphasis, lists, quotations and safe links |
| 4 | Newsroom authentication | Staff sign-in, password validation and login lockout |
| 5 | Reporter ownership | Reporters can see/edit their own drafts; editors control publication |
| 6 | Editorial workflow | Draft → review action → editor publication |
| 7 | Scheduled stories | Future publication dates remain private until due |
| 8 | Optimized media | Uploads converted to WebP with separate thumbnails, captions and alt text |
| 9 | Author profiles | Bios and article archives |
| 10 | Topic archives | Tags connected to published articles |
| 11 | Search and pagination | Search titles, summaries and bodies; paginated archives |
| 12 | Editorial curation | Featured lead, developing-story strip, editor selections |
| 13 | Revision audit | Timestamped history with responsible staff user for admin edits |
| 14 | Private preview | Authenticated draft preview, ownership checks, noindex and no-cache |
| 15 | Reader tools | Related stories, WhatsApp sharing, link copy, local saved flag and reading progress |
| 16 | Subscriber lifecycle | Explicit consent, queued confirmation, expiring confirmation links and unsubscribe |
| 17 | Newsletter campaigns | Staff confirmation before queuing, permission checks, confirmed recipients only, duplicate-queue protection, SMTP retry/logging |
| 18 | Contact and corrections | Persistent inbox, honeypot, session throttle and shared IP limits |
| 19 | Managed pages and advertising | Publish real informational pages; show only configured ad placements |
| 20 | Search/distribution and operations | SEO overrides, Open Graph, JSON-LD, RSS, sitemap, Docker, health check, backups and CI |

New installations start with **no articles**. The empty state is honest. The newsroom must publish real reporting and approved informational pages before public launch. Newsletter calls to action are absent until `NEWSLETTER_ENABLED=1`; without configuration the app does not claim that email delivery is available.

The newsroom also includes CMS-style editorial cards, a monthly assignment/deadline desk, private review discussions, browser draft recovery, stale-edit detection, reusable rights-attributed media, and permanent redirects for changed story URLs. Readers can comment on published articles; comments are rate limited, held for editor approval, and rendered as escaped text. Search covers story text, authors, sections and topics. The public homepage and archives use responsive red-and-white story cards. These workflows use the existing Django admin, database and open-source packages; there is no separate SaaS dependency.

The newsroom landing page now leads with staff actions instead of dropping editors into a model list. The public navigation has a mobile section menu and a direct Latest route. Archive pagination retains active search and section filters. Page transitions run only where the browser supports them and the visitor has not requested reduced motion. We use Django's built-in admin templates and existing editor widgets rather than adding a second admin theme stack.

## Search visibility

Public stories and pages emit canonical URLs, unique titles/descriptions, social sharing metadata and structured data. Articles include `NewsArticle` and breadcrumb markup with author, publisher, dates, section, tags and available images. The XML sitemap lists live stories, sections, authors, topics and published pages on the configured `SITE_URL`; search results are marked `noindex` without blocking crawlers from seeing that instruction. `/robots.txt` advertises the sitemap, and `/feed.xml` provides RSS. Editors can set SEO title/description overrides on stories and managed pages.

To monitor discovery, add `cedarmondtv.co.ke` as a **Domain property** in Google Search Console. Verify it with the DNS TXT record supplied by Google in Cloudflare, then submit `https://cedarmondtv.co.ke/sitemap.xml` in Search Console. Verification and submission are external account steps; being indexed or ranking for a query is not guaranteed by markup alone.

## Plug in a direct advertisement

Sign in to `/admin/` and choose **Ads and sponsorships** (or **Ad placements** from the editorial desk). Create or edit one creative for each available slot: **Homepage banner** and **Article sidebar**. Upload an approved JPG, PNG or WebP banner, enter its destination URL and label, then activate the placement. Only active placements appear on the public site. The current implementation supports image banners for direct-sold placements; it does not claim to track impressions or clicks. A separate ad server is unnecessary for this initial setup.

## Public API

The read-only API exposes original Cedarmond TV content after publication. It does not import or republish content from other publishers. Drafts, future stories, internal assignment notes, reporter ownership, and unapproved reader comments are excluded. Anonymous traffic is throttled to 600 requests per hour per client IP; pagination defaults to 20 and is capped at 50.

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/articles/` | Published stories; supports `q`, `category`, `author`, `tag`, `page`, and `page_size` |
| `GET /api/v1/articles/{slug}/` | One published story, including sanitized article HTML |
| `GET /api/v1/categories/` | Section metadata and live article counts |
| `GET /api/v1/authors/` | Authors with published work |
| `GET /api/v1/tags/` | Topics used by published stories |
| `/api/schema/` | OpenAPI 3 schema in JSON/YAML |
| `/api/docs/` and `/api/redoc/` | Self-hosted Swagger UI and ReDoc documentation |

Example: `curl 'https://cedarmondtv.co.ke/api/v1/articles/?category=politics&page_size=10'`. See [API.md](docs/API.md) for response fields and integration notes. The packages are open source; public API access does not require a third-party API key or paid service.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=1
python manage.py migrate
python manage.py setup_newsroom
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/`. Create an author, write an article and publish it. No default credentials exist. SQLite is used locally. For shared public-form rate limits locally, provide `REDIS_URL=redis://127.0.0.1:6379/0` pointing to Valkey; production Compose sets this automatically.

## Ubuntu / AWS deployment

Requires Docker Engine, the Compose plugin, a domain pointing to the VM, and free ports 80/443. If Patapesa or another application already owns those ports, integrate with the existing proxy as described in [DEPLOYMENT.md](docs/DEPLOYMENT.md); do not stop existing applications.

```bash
git clone https://github.com/cedarmondenterprises/Cedarmondtv.co.ke.git
cd Cedarmondtv.co.ke
python3 scripts/configure.py
# Edit .env for your domain and email provider; generated secrets are already set.
bash scripts/deploy.sh
docker compose exec web python manage.py createsuperuser
```

Caddy obtains HTTPS certificates after DNS and network access are correct. PostgreSQL and media are persistent Docker volumes. Neither the database, Valkey nor the application port is published to the host. The domain must be registered and DNS configured separately.

## Newsroom workflow

1. Run `setup_newsroom` to create sections and Reporter/Editor groups (no users or content).
2. Create staff users and assign groups. Reporters own new stories. Editors can publish/schedule and manage author records.
3. Create an author profile. Write a draft with original reporting, summary, category, tags, image credit and alt text.
4. Open **Editorial desk** from the article list to see deadlines, assignments, review cards, private draft-recovery copies and pending reader comments. Add review notes in the story’s **Editorial discussion** workspace. Approve or reject reader comments from the **Reader comments** queue before they appear publicly.
5. Open **Private preview** from the article form. Submit drafts for review from the article list. Draft text is recovered privately in the browser; uploads and publishing settings still need the normal Save action.
6. Editors set status to Published and choose a publication date. Future dates are enforced in every public query. The article’s history view can restore prior story text as a new unpublished draft.
7. Create approved About, privacy and editorial policy entries under **Pages**; publish them to expose footer links. Nothing is pre-filled with invented policies.

## Email delivery

Configure `EMAIL_HOST`, `EMAIL_PORT`, TLS/SSL, username/password and `DEFAULT_FROM_EMAIL` in `.env`. Enable `NEWSLETTER_ENABLED=1` only once the provider is ready; restart `web` and `mail` after changes. The production settings reject an enabled newsletter without an SMTP backend/host. The mail worker processes queued messages every 30 seconds.

A superuser or staff account with Campaign permissions and `news.send_campaign` can create a newsletter and choose **Queue selected newsletters**. A confirmation screen is required. Only confirmed subscribers are included; queuing the same campaign again does not create duplicates. Post Office logs delivery results and retries failures. Every campaign includes a recipient-specific unsubscribe URL. Unsubscribe removes pending campaign mail; an SMTP message already in flight cannot be recalled. SMTP delivery is at-least-once: a crash after provider acceptance but before database acknowledgment can result in a duplicate.

Configure and test actual SMTP delivery, SPF/DKIM/DMARC and provider quotas before accepting subscriptions. Automated bounce/webhook suppression and one-click mailbox-provider unsubscribe are not implemented; manage hard bounces in the subscriber list and monitor delivery logs.

## Tests, CI and operations

```bash
DEBUG=1 python manage.py test
DEBUG=1 python manage.py makemigrations --check --dry-run
DEBUG=1 python manage.py collectstatic --noinput
DEBUG=1 python manage.py check
bash scripts/backup.sh
```

CI runs with PostgreSQL and Valkey, validates the rich editor and publishing permissions, executes newsletter queue/dispatch tests against a local-memory email backend, and builds the Docker image. It does not send to real recipients. See [VERIFICATION.md](docs/VERIFICATION.md).

Production `check --deploy` intentionally leaves only the optional HSTS subdomain/preload warnings; these are not enabled without knowing the configuration of all subdomains.

Backups must be copied off the VM, scheduled by the operator and restore-tested. This deployment targets one Linux host. For multiple web replicas, move media to shared object storage. A static-only host cannot run the backend. DNS, VM sizing, actual email delivery, monitoring and real editorial content are launch requirements, not simulated integrations.

## Upgrade from the first foundation commit

Back up first. Migration 0002 deletes only articles explicitly marked as generated demos, removes unused generated author/tag records, converts existing plain-text articles safely to HTML, and adds revision/campaign data. Real articles are retained. Existing uploaded files are not deleted automatically; remove unused demo files separately only after reviewing media references. Existing subscriptions remain, but old confirmation links are invalidated by the versioned token format.

Run `python manage.py migrate` after updating to apply migration 0003. It adds assignment metadata, the media library, private editorial comments, draft recovery and permanent article-URL history. Existing article slugs are registered automatically, so their addresses keep working after an edit.

### Error monitoring and off-server backups

To enable Sentry, add your Django project's DSN as `SENTRY_DSN` in the VM's
deployment `.env` and redeploy. Reporting is disabled in debug mode. Request
bodies, stack-frame locals and default personal data collection are disabled.
Review event scrubbing in your Sentry project before sending production events.

Install Restic on the VM and configure an off-server repository and credentials
in a restricted environment file. Initialize the repository once with
`restic init`. Load that environment before running `scripts/backup.sh` with
the same Compose project name and files used for deployment. Schedule the script
using your existing cron or systemd setup once the first upload succeeds.
A failed upload leaves the completed local backup available for retry.
Store the repository password separately and confirm recovery into an isolated
directory with `restic restore latest --tag cedarmondtv --target <restore-directory>`.
