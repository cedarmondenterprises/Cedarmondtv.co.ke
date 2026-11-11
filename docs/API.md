# Public API

Base URL: `https://cedarmondtv.co.ke/api/v1/`

This is a first-party, read-only API for Cedarmond TV's published reporting. It is not a news aggregation feed. Every article is selected from the same live-content queryset as the public site, so drafts, review submissions, and future-dated stories stay private. Responses exclude internal newsroom fields and unapproved reader comments. Article HTML is sanitized before it is returned.

## Routes

| Method and path | Description |
|---|---|
| `GET /articles/` | Newest published stories. Optional filters: `q`, `category`, `author`, `tag`. |
| `GET /articles/{slug}/` | Published story by its stable public slug. |
| `GET /categories/` | Sections with counts of currently published stories. |
| `GET /authors/` | Authors who have published stories. |
| `GET /tags/` | Topics attached to currently published stories. |

Article listings use page-number pagination. `page_size` defaults to 20 and accepts at most 50. Search text is limited to 120 characters; filter slugs are limited to 80 characters. Responses are JSON and anonymous requests are throttled to 600 per hour per client IP. A `429` response means the caller should wait before retrying.

## Story representation

The article response contains `id`, `title`, `slug`, `url`, `summary`, `body_html`, `category`, `author`, `tags`, `image`, `image_thumbnail`, `image_alt`, `image_credit`, `published_at`, `updated_at`, `reading_minutes`, `seo_title`, and `seo_description`. Media URLs and canonical article URLs are absolute when a request host is available. HTML is for display; clients should not treat it as trusted executable content.

## Documentation and schema

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`

The documentation JavaScript and CSS are bundled with the application and served from its own static files. No external API credentials, commercial API plan, or third-party documentation CDN is needed.
