# Loading our pre-issued certificate into Caddy

`lessley.cs.colman.ac.il` is a private, college-administered DNS name: not publicly
resolvable, so Let's Encrypt can't validate it, and Caddy's own self-signed internal CA
would need every client's browser to trust a root it generated — not viable across campus.
The college's network PKI already issued us a certificate + private key for that exact
hostname, so Caddy just loads that file pair directly and skips automatic HTTPS entirely —
no issuance, no renewal, no DNS resolution needed at all.

This works via the `CADDY_TLS_DIRECTIVE` env var, wired into the shared `Caddyfile`
(`lessley-cd/Caddyfile`) as `{$CADDY_TLS_DIRECTIVE:}` on the site block — required in
`docker-compose.prod.yaml`; dev leaves it unset and gets Caddy's internal-CA cert instead.

## Steps

**1. Drop the cert and key into `lessley-cd/certs/`** (this directory is gitignored — the
private key must never be committed):

```
lessley-cd/certs/college.crt
lessley-cd/certs/college.key
```

That directory is already mounted read-only into the `caddy` container at `/etc/caddy/certs`
by both compose files.

**2. `DOMAIN`** in `lessley-cd/.env` is `lessley.cs.colman.ac.il` — the same name the
certificate was issued for.

**3. `CADDY_TLS_DIRECTIVE`** in `lessley-cd/.env` is the full Caddy `tls` directive, pointing
at the in-container paths (not the host paths):

```
CADDY_TLS_DIRECTIVE=tls /etc/caddy/certs/college.crt /etc/caddy/certs/college.key
```

**4. Restart Caddy** so it picks up the cert files and env var:

```powershell
docker compose -f docker-compose.prod.yaml up -d --build caddy
```

**5. Verify.** Caddy's logs should show no ACME/resolution attempts at all, and the served
cert should be the college's:

```powershell
docker compose -f docker-compose.prod.yaml logs caddy --tail 50
curl -kv https://<DOMAIN> 2>&1 | grep -i "issuer\|subject"
```

No client trust setup needed — the certificate is already trusted by whatever CA the
college's network devices already trust.

## Why this couldn't just be `tls {$CERT_FILE} {$KEY_FILE}` with blank defaults

Worth knowing if you ever touch the Caddyfile: a bare `tls` directive with empty/no arguments
is a **Caddyfile parse error**, not a no-op (confirmed by running `caddy validate` — Caddy
refuses to even start). Making the *entire* directive — including the word `tls` itself — come
from one placeholder is what makes "unset" (the dev case) a true no-op (an empty line, which
Caddy just skips), without touching the directive's argument-count validation at all. Don't
reintroduce the two-separate-placeholder version.
