# Prospective Archive Security / Governance Verification

Date: 2026-09-27

## Database

Existing provider tables:
- `fsffl.projection_snapshot`: RLS enabled; no RLS policies;
- `fsffl.projection_observation`: RLS enabled; no RLS policies.

New tables:
- `fsffl.current_football_state_capture`: RLS enabled; no user-facing policy;
- `fsffl.football_event_snapshot`: RLS enabled; no user-facing policy.

`anon` and `authenticated` table privileges are explicitly revoked on the new tables.

The Supabase security advisor reports the expected informational `rls_enabled_no_policy` finding for these private server-side tables, consistent with other governed `fsffl` server-only tables. No public access policy was added.

## Ingest authentication

Edge Function `fsffl-research-snapshot-ingest` uses custom GitHub OIDC verification.

Built-in Supabase JWT verification is disabled because the caller token is a GitHub OIDC JWT, not a Supabase user token.

The function verifies:
- issuer `https://token.actions.githubusercontent.com`;
- fixed audience;
- exact GitHub repository and repository ID;
- exact `main` branch ref;
- exact capture workflow ref;
- allowed event type.

Only then does it use the Edge Function's private `SUPABASE_DB_URL` to write.

## Public-repository constraint

No provider rows or full capture payloads are uploaded as GitHub artifacts.

Pull requests build a temporary payload under `/tmp` and skip ingest. The temporary file is not uploaded.

On main, the payload is POSTed directly to the private ingest function and deleted.

## Authority

This mechanism creates prospective Research evidence only.

It changes no:
- Forecast model authority;
- provider rights classification;
- H3/Intrinsic value;
- product read path;
- Decision/Search/Team Utility behavior.
