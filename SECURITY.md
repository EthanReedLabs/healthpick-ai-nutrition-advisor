# Security Policy

## Supported scope

The competition release candidate is the only supported version. Public deployment is not yet active; local and Compose evidence must not be interpreted as a production security certification.

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
- HTTPS, managed-database TLS, rate limiting, public monitoring and seven-day availability depend on the final deployment and remain behind ACTION-05.
- The project is a nutrition information assistant, not a medical device or substitute for professional care.

Security evidence is summarized in `docs/evidence/phase-08-p08-01-quality.md` and the live task status remains in `docs/governance/CONTROL_BOARD.md`.
