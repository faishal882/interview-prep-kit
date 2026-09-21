# Registration is closed by default; users are operator-provisioned

## Context

The service has a real Gemini quota and a crawler that can be aimed at arbitrary
URLs. Open self-service registration would let anyone burn the model budget and
use the fetcher as an open proxy. The production-readiness brief also asks for
secure cookies, quotas and fail-closed origin checks — none of which help if
accounts are free for the taking.

## Decision

Registration is **closed by default** (`REGISTRATION_OPEN=false`). Operators
create accounts with `npm run users:create -- --email … --password …` (or the
equivalent `python -m app.cli.create_user` inside the API container). Setting
`REGISTRATION_OPEN=true` reopens self-service registration explicitly for local
demos and tests.

Passwords are hashed with Argon2id only, off the request loop, with length
bounds. Session cookies are `HttpOnly` and `Secure` in production. Quotas and
login throttling (client address + account) apply regardless of how the user
was created.

## Consequences

- Onboarding someone requires an operator step (documented in the runbook).
- The register API still exists and returns a clear "closed" error when shut.
- Tests that need accounts set `REGISTRATION_OPEN=true` or use the operator
  command / API under that setting.
