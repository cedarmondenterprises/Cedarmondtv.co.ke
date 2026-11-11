# Security policy

## Reporting a vulnerability

Please report suspected security issues privately through GitHub's **Report a vulnerability** action for this repository. Do not publish credentials, personal data, exploit details, or an unpatched vulnerability in a public issue. Include the affected route or component, impact, and reproduction steps that do not access another person's data.

## Current application protections

- Production requires a strong secret key, HTTPS site URL, secure session and CSRF cookies, and HTTPS redirects.
- Django Axes limits repeated newsroom sign-in failures.
- Public HTML responses receive a per-response nonce-based Content Security Policy. Public script tags must carry that nonce. The Django admin and API documentation currently use their own UI assets and are excluded from this policy; they retain Django's authentication, CSRF, clickjacking, cookie and HTTPS protections.
- Caddy adds a strict referrer policy, a browser permissions policy, and removes its server-identification header. Django sets HSTS, MIME-sniffing protection, and frame protection.
- Article and live-update content is sanitized before it is rendered. Template autoescaping remains enabled for ordinary user and admin values.
- AdSense configuration accepts only a publisher ID and numeric ad-unit IDs. Arbitrary HTML and JavaScript are not accepted. Ad loading is disabled until explicitly enabled.

## Deployment notes

Keep the Django application reachable only through the configured reverse proxy. Set `TRUST_PROXY_HEADERS=1` only when that proxy is the only route to the application and overwrites incoming forwarded headers. Do not enable HSTS for all subdomains or browser preload until every affected hostname is permanently served over HTTPS. Do not add scripts to the CSP without reviewing their source, nonce behavior, and data collection.

Security controls reduce risk but do not guarantee that the service is free of vulnerabilities. Keep dependencies and the operating system updated, restrict newsroom accounts, and maintain recoverable backups.
