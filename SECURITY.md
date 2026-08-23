# Security Policy

## Supported scope

The competition release candidate is the only supported version. A short-lived public deployment is active at `https://106.14.13.139`; this deployment and the local/Compose evidence are competition engineering evidence, not a general production security certification.

## Repository credentials

This public repository does not contain production API keys, database passwords, private keys, access tokens, or deployment credentials. Configuration files ending in `.example` contain placeholders only. Copy them to an ignored local environment file and inject real values through the deployment environment; never commit the populated file.

The repository runs two redacted checks in CI:

- `scripts/audit_repository_security.py` scans the current tracked submission candidate, including readable content inside DOCX/ZIP archives;
- `scripts/audit_git_history_security.py` scans every Git blob reachable from all fetched refs.

Both scanners report only the file path, line number and rule identifier. Candidate values are deliberately excluded from console logs and evidence files.

## Implemented controls

- deterministic A/B/C source boundaries, citation validation, medical pre/post gates, and prompt-injection tests;
- request body and string limits, stable error contracts, CORS allowlist, resource ownership checks, password hashing, token hashing and expiry;
- PostgreSQL foreign keys and cascading account/conversation deletion;
- production rejection of mock LLM and ephemeral conversation storage;
- non-root, read-only API/Web containers with `no-new-privileges`;
- current-tree and all-history secret scans, including readable DOCX/ZIP content, plus dependency vulnerability audit;
- logs designed to exclude raw health text, passwords, tokens, provider keys and internal prompts.

## Known limitations

- Web authentication currently stores the bearer token in browser `localStorage`, not an HttpOnly Cookie. Users should not reuse an important password, should sign out after testing, and may clear the site's browser storage to remove the local token. A production service should migrate to HttpOnly/Secure/SameSite cookies and CSRF protection.
- There is no automatic conversation-retention worker. Users must delete conversations/accounts, and the competition operator must clean demonstration data.
- HTTPS is active through Caddy, and the operator has committed to keep the ECS and certificate renewal available for at least seven days after the actual competition submission. There is no external uptime monitor or application rate limiter; PostgreSQL is an on-host container rather than a managed TLS database.
- The project is a nutrition information assistant, not a medical device or substitute for professional care.

## Reporting a vulnerability

Do not place credentials, personal data or an unredacted exploit in a public issue. Use the repository owner's GitHub private vulnerability reporting channel or contact the competition submission owner through the official competition channel. Include the affected component and commit, reproducible steps, impact and a redacted request ID, but mask any secret value.

## Credential response

If a credential is suspected to have been exposed, revoke or rotate it first. Deleting a file or a later commit is not sufficient because the value may remain in Git history, forks, caches or logs. After rotation, remove the material from the current tree and reachable history, run both scanners, and verify the public repository again.

Security evidence is summarized in `docs/evidence/phase-08-p08-01-quality.md`; the supplemental RC10 status and seven-day commitment are recorded in `control/records/RC10-CONTROL.yaml` and `docs/evidence/phase-09-rc10-05-availability.md`. Public-repository sanitization evidence is recorded under Phase 13.
