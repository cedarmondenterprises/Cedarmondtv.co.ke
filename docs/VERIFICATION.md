# Verification

## Foundation

The first remote build, commit `2145d8f`, passed GitHub Actions, including its Docker image build: https://github.com/cedarmondenterprises/Cedarmondtv.co.ke/actions/runs/42913022071

## Open-source production workflow update

Local automated checks cover route rendering, draft/future visibility, sanitized rich text, revision history, consent and queued confirmation delivery, unsubscribe and stale-token rejection, campaign deduplication and confirmed-recipient filtering, pending-mail cancellation, staff permissions, history-route protections, private previews, media conversion and absent-placeholder behavior.

The shared-cache test is skipped locally without Valkey and is enabled in CI. CI runs the suite with PostgreSQL + Valkey and builds the Docker image. Delivery tests use an in-memory email backend, never real recipients.

Actual DNS/HTTPS on the user's AWS VM, real SMTP deliverability, production backups and external uptime monitoring remain deployment verification tasks. No production VM or email-provider credentials were supplied to this session.

The open-source workflow update passed all 21 tests with PostgreSQL/Valkey, built the production image, and passed the production-container health/homepage smoke test in GitHub Actions: https://github.com/cedarmondenterprises/Cedarmondtv.co.ke/actions/runs/42965608611

A subsequent regression test simulates a temporary SMTP failure and verifies that Post Office schedules a retry using the configured five-minute interval. No real email was sent by that test.
