# Open-source components

Cedarmond TV integrates maintained libraries rather than copying complete third-party news sites. Package versions (including transitive dependencies) are pinned in `requirements.txt`; the Docker services use supported release series. Libraries are installed from their upstream Python distributions, retaining their bundled licenses.

| Component | Purpose | Upstream / license |
|---|---|---|
| Django | ORM, sessions, CSRF, templates, permissions, admin | https://github.com/django/django — BSD-3-Clause |
| django-prose-editor | ProseMirror/Tiptap rich-text editor | https://github.com/feincms/django-prose-editor — BSD-3-Clause |
| nh3 | Server-side HTML sanitization | https://github.com/messense/nh3 — MIT |
| django-simple-history | Timestamped article and page revisions | https://github.com/django-commons/django-simple-history — BSD-3-Clause |
| django-post-office | Durable mail queue, delivery logs and SMTP retries | https://github.com/ui/django-post_office — MIT |
| django-ratelimit | IP-based public-form limits | https://github.com/jsocol/django-ratelimit — Apache-2.0 |
| django-redis | Shared cache connection | https://github.com/jazzband/django-redis — BSD-3-Clause |
| django-axes | Authentication lockout | https://github.com/jazzband/django-axes — MIT |
| Django REST Framework | Versioned, read-only JSON API and request throttling | https://github.com/encode/django-rest-framework — BSD-3-Clause |
| drf-spectacular + sidecar | OpenAPI schema, self-hosted Swagger UI and ReDoc assets | https://github.com/tfranzel/drf-spectacular — BSD-3-Clause; https://github.com/tfranzel/drf-spectacular-sidecar — BSD-3-Clause |
| Pillow | WebP encoding, thumbnails, metadata removal | https://github.com/python-pillow/Pillow — MIT-CMU |
| WhiteNoise / Gunicorn | Compressed static assets / WSGI application server | https://github.com/evansd/whitenoise (MIT), https://github.com/benoitc/gunicorn (MIT) |
| PostgreSQL | Relational content and mail storage | https://www.postgresql.org/about/licence/ — PostgreSQL License |
| Valkey 8 | Cross-worker rate-limit counters (Redis-compatible protocol) | https://github.com/valkey-io/valkey — BSD-3-Clause |
| Caddy | Reverse proxy and automatic HTTPS | https://github.com/caddyserver/caddy — Apache-2.0 |

The custom application code remains under the repository owner's chosen terms; no license is granted for user-owned articles or photography by these dependency licenses. No scraped news stories or competitor assets are included.
