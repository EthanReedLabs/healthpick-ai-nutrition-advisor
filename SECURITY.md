# Security Policy

## Supported scope

The competition release candidate is the only supported version. A short-lived public deployment is active at `https://106.14.13.139`; this deployment and the local/Compose evidence are competition engineering evidence, not a general production security certification.

## Reporting a vulnerability

Contact the project owner through the competition submission contact or repository maintainer channel. Do not post passwords, bearer tokens, health conversations, database URLs, provider keys, or exploit payloads in a public issue. Include an affected component, reproducible steps, impact, and a redacted request ID.

## Implemented controls

- deterministic A/B/C source boundaries, citation validation, medical pre/post gates, and prompt-injection tests;
- request body and string limits, stable error contracts, CORS allowlist, resource ownership checks, password hashing, token hashing and expiry;
- PostgreSQL foreign keys and cascading account/conversation deletion;
- production rejection of mock LLM and ephemeral conversation storage;
- non-root, read-only API/Web containers with `no-new-privileges`;
- repository secret scan covering tracked and untracked submission candidates, plus dependency vulnerability audit;
- logs designed to exclude raw health text, passwords, tokens, provider keys and internal prompts.

## Known limitations

- Web authentication currently stores the bearer token in `localStorage`, not an HttpOnly Cookie. A production service should migrate to HttpOnly/Secure/SameSite cookies and CSRF protection.
- There is no automatic conversation-retention worker. Users must delete conversations/accounts, and the competition operator must clean demonstration data.
- HTTPS is active through Caddy, and the operator has committed to keep the ECS and certificate renewal available for at least seven days after the actual competition submission. There is no external uptime monitor or application rate limiter; PostgreSQL is an on-host container rather than a managed TLS database.
- The project is a nutrition information assistant, not a medical device or substitute for professional care.

Security evidence is summarized in `docs/evidence/phase-08-p08-01-quality.md`; the supplemental RC10 status and seven-day commitment are recorded in `control/records/RC10-CONTROL.yaml` and `docs/evidence/phase-09-rc10-05-availability.md`.
