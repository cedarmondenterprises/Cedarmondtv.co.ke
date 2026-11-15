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

## Newsroom two-factor authentication

1. Deploy the new image with `NEWSROOM_2FA_REQUIRED=0` to apply the OTP migrations.
2. From a private terminal, run the following on the production VM for each active staff account, starting with the site owner.

   ```bash
   sudo docker compose -p cedarmondtv-public -f compose.yaml -f compose.public.yaml exec web python manage.py enroll_newsroom_2fa YOUR_USERNAME
   ```

3. Store the one-time recovery codes in a password manager. Keep your VM session open, set `NEWSROOM_2FA_REQUIRED=1` in the production `.env`, and redeploy.
4. In a private browser window, verify that a password alone fails, a fresh authenticator code works, and a recovery code works once. Verify that a private article preview also requires a verified session.
5. If access fails during rollout, set `NEWSROOM_2FA_REQUIRED=0` and redeploy from the VM. Re-enable it after resolving enrollment. Keep terminal access restricted to trusted operators.

The authenticator keys and recovery codes are stored in the database by django-otp. Restrict access to database dumps and backups.
