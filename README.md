# Cedarmond TV

A portable Kenyan news publishing platform for **cedarmondtv.co.ke**. Built with Django 5.2, PostgreSQL, server-rendered HTML, custom CSS, and small progressive JavaScript enhancements. The interface uses editorial serif headlines, a crimson masthead, white space, fine rules, and mobile-first news layouts.

This is an initial newsroom foundation, not a claim of parity with a mature national publisher. No stories, logos, or source code were copied from Tuko or Kenyans. The seeded editorial material is clearly labelled sample content.

## The 20 foundation features

| # | Feature | Included behavior |
|---|---|---|
| 1 | Responsive editorial homepage | Lead story, secondary leads, compact latest rail, headline grid; mobile layouts |
| 2 | Section navigation | Kenya, Politics, Counties, Business, Technology, Culture, Sports, Opinion |
| 3 | Article reading pages | Summary, byline, date, image caption, reading time, readable paragraphs |
| 4 | Authenticated newsroom | Django admin, password validation, login lockout, audit log |
| 5 | Reporter and editor roles | Reporters draft; publishers control status and published articles |
| 6 | Editorial workflow | Draft, review, published states |
| 7 | Scheduled publishing | Future publication dates stay hidden across public pages, search, RSS and sitemap |
| 8 | Media management | Image uploads, required alt text, credits, type and size validation |
| 9 | Author profiles | Author bio and article archive |
| 10 | Topic tags | Article tagging and topic archives |
| 11 | Search and pagination | Server-side title, summary and body search with paginated results |
| 12 | Homepage curation | Featured lead and editor selections |
| 13 | Developing-story strip | Editor-controlled breaking/developing banner |
| 14 | Related articles | Same-section recommendations beneath articles |
| 15 | Reader utilities | WhatsApp sharing, copy link, browser-local saved flag and reading progress |
| 16 | Newsletter foundation | Consent, email confirmation, subscriber records, unsubscribe; SMTP configuration required |
| 17 | Contact and corrections inbox | Validated submissions stored in newsroom; honeypot and session throttle |
| 18 | Search/distribution metadata | SEO overrides, canonical article URLs, Open Graph, NewsArticle JSON-LD, RSS, sitemap and robots |
| 19 | Advertising foundation | Managed header/sidebar image placements, sponsored labels, enquiry page; no ad network tracker |
| 20 | Portable operations | Docker Compose, PostgreSQL/media volumes, Caddy HTTPS, health check, backup script, CI and tests |

**Boundaries:** the newsletter does not yet send scheduled campaigns; saved stories have a per-article local toggle, not a cross-device library; body editing is safe plain text, not a rich-text/block editor. Video, comments, analytics, advanced search and CDN integrations are future work. Contact throttling is a light first layer, not a comprehensive anti-spam service.

## Local development

Python 3.12+:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DEBUG=1
python manage.py migrate
python manage.py setup_newsroom
python manage.py seed_demo  # optional; creates 12 labelled sample stories
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000` and `/admin/`. No default credentials exist. SQLite is used locally; Compose configures PostgreSQL. Set staff status and the Reporter/Editor group when adding newsroom users. The Editor role intentionally cannot access subscriber emails; a superuser can delegate that permission separately.

## Deploy to an Ubuntu AWS VM

Use a supported Ubuntu release with Docker Engine and the Compose plugin installed. The default deployment needs the VM's ports **80 and 443 free**. If another application (such as Patapesa) owns them, use the existing reverse proxy and a shared Docker network instead; do not stop unrelated services. See [deployment notes](docs/DEPLOYMENT.md).

1. Point the domain's A record at the VM's stable public IP. Remove incorrect AAAA records. Allow inbound TCP 80/443 (optionally UDP 443) in the security group; restrict SSH to trusted addresses.
2. Clone this repository and enter its directory.
3. Run `cp .env.example .env`. Generate two different secrets with `openssl rand -hex 32`, then edit `.env`. Never commit it.
4. Run:

```bash
docker compose up -d db
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py setup_newsroom
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
```

Caddy obtains and renews certificates once DNS and ports are correct. Visit `https://cedarmondtv.co.ke/admin/` and publish original articles. Demo content is **not** installed by deployment. For a private staging environment, optionally run `docker compose exec web python manage.py seed_demo`.

Configure SMTP and verify a subscription end to end before advertising the newsletter. Without SMTP, confirmation messages go to container logs for development. DNS/email authentication and your chosen SMTP provider are external setup tasks.

## Tests and checks

```bash
DEBUG=1 python manage.py test
DEBUG=1 python manage.py makemigrations --check --dry-run
DEBUG=1 python manage.py collectstatic --noinput
DEBUG=1 python manage.py check
```

The suite checks public routes, draft/scheduled visibility, search, script escaping, confirmation/unsubscribe, CSRF, contact throttling, newsroom authentication, reporter restrictions and repeatable demo seeding. GitHub Actions additionally builds the Docker image.

Production `check --deploy` intentionally leaves two optional warnings: HSTS subdomain enforcement and HSTS preload are not enabled automatically because ownership/configuration of other subdomains is unknown.

## Backups and updates

```bash
bash scripts/backup.sh
```

This exports PostgreSQL and uploaded media. Copy backups to encrypted storage outside this VM and test restoration. Do not rely on Docker volumes as a backup. See [deployment notes](docs/DEPLOYMENT.md) for restore and update instructions. Backup is manual until you configure a schedule.

## Project layout

- `news/`: models, public views, admin permissions, forms and tests
- `templates/`, `static/`: original editorial interface
- `config/`: environment-driven Django settings and routes
- `demo-assets/`: optional illustrative stock photos, provenance in `SOURCES.md`
- `compose.yaml`, `Dockerfile`, `Caddyfile`: portable Linux deployment
- `docs/`: operations and launch guidance

This project has no hosting-provider API dependency. A platform must support Python and persistent database/media storage, or Docker Compose; static-only hosts cannot run the publishing backend.
