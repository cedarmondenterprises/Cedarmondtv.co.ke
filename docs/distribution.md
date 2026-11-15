# Content discovery service

This optional Docker worker runs separately from web requests. It reads only published articles whose publication time has arrived. Every five minutes it checks changes, reports missing descriptions/images, and sends batches of up to 100 URLs to IndexNow. Its private SQLite volume records successful deliveries. HTTP errors retry on the next pass; 202 remains pending until 200. Run only one distribution replica.

## Activate

Generate an IndexNow verification key with python3 -c 'import secrets; print(secrets.token_hex(16))' and set INDEXNOW_KEY in the production .env. Deploy the new web image first so /indexnow-key.txt returns the same key publicly. Cloudflare must allow that file to be fetched without a browser challenge.

Start the optional service:

```bash
sudo docker compose -p cedarmondtv-public -f compose.yaml -f compose.public.yaml -f compose.distribution.yaml up -d --build distribution
```

Inspect delivery and SEO findings:

```bash
sudo docker compose -p cedarmondtv-public -f compose.yaml -f compose.public.yaml -f compose.distribution.yaml logs --tail=100 distribution
```

Keep compose.distribution.yaml in future Compose deployment invocations so the worker is updated alongside web. Preserve distribution_state when replacing containers.

IndexNow acceptance does not guarantee indexing or ranking. For Google, submit the existing /sitemap.xml in Search Console. Google's Indexing API is restricted to eligible job and livestream pages. This release does not connect Google accounts or social accounts, rewrite editorial metadata, submit removed URLs, or automatically publish social posts. API limits and network failures are visible in worker logs.

## Verification

Before activating in production, run once with a staging domain and key, then run again to check that accepted unchanged URLs are skipped. Edit a published story and repeat. Confirm drafts and future scheduled stories never appear. Test an invalid key and an unreachable endpoint to confirm failures leave delivery state pending.

The service uses the existing open-source Django framework and Python standard library. No paid API subscription is required; VM and network usage still apply.
