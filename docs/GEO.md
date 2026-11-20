# Search and AI discovery

GEO means Generative Engine Optimization. These features improve the public evidence and clarity of stories. They do not guarantee rankings or AI citations.

## Editors

Optionally expand **Reader key facts** on an article and enter short, verified facts, one per line. Do not invent claims or statistics for search systems.

Under **Public sources**, add a title and HTTP(S) URL for each publishable document or report. Readers see the same citations included in NewsArticle structured data. Never enter confidential source identities or private document links here. Existing verification notes remain private.

Keep headlines, summaries, author biographies, image credits, dates and Google search metadata accurate. Both new features are optional. Normal publication permissions, draft previews and scheduling rules apply.

## Read-only audit

Run `python manage.py audit_geo` to review published stories. Each line is JSON. This is an editorial checklist, not an SEO score; not every story needs external citations or a separate key-facts box. Drafts and future scheduled stories are excluded. No content is changed or external requests made.

## Operations

Verify public stories return HTTP 200, with readable text, valid source links, canonical URLs and accurate JSON-LD. Use Search Console URL Inspection and sitemaps. Keep private previews and search results noindex. The existing wildcard robots policy permits public crawling; this release does not change training permissions or Cloudflare rules.

Inspect Cloudflare events for challenged legitimate crawlers. Metadata cannot fix an edge challenge. Do not disable protection globally. Use actual referral analytics and Search Console to measure discovery.

Google requires no special AI schema or llms.txt file. This change uses standard NewsArticle citations matching the visible page. Reference: https://developers.google.com/search/docs/appearance/ai-features

## Release

Includes a migration joining the AdSense and platform migration branches, then additive key-fact/source migrations. Back up production first. Preserves consent-gated ads and the AdSense account verification tag. No paid API or subscription required.

## Admin review

Open /admin/geo/ or choose Search and AI discovery review from the newsroom home.
Search published headlines and follow permitted edit links to address gaps. The
report shows 25 stories per page, respects article access permissions and the
configured admin 2FA requirement, and excludes drafts and scheduled stories.
It shares the same checks as audit_geo and does not change any content.
