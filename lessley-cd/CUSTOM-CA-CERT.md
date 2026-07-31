# Loading a certificate into Caddy without automatic HTTPS

Caddy's automatic HTTPS decides between an ACME (Let's Encrypt) cert and a self-issued
"internal" cert based on whether `DOMAIN` looks public. Both need something Caddy controls:
Let's Encrypt needs `DOMAIN` to be publicly resolvable/reachable; the internal issuer needs
every client to install its self-signed root. Neither works for a private, institution-only
DNS name (a college or corporate network) whose administrators already gave you a certificate
that's already trusted there. This doc covers two different ways to hand Caddy a certificate
you already have — pick based on what you were given:

| You have... | Use | Caddy behavior |
|---|---|---|
| A CA root cert **and its private key** (e.g. reusing the same root you already trust from another environment) | [Option A](#option-a-reuse-a-ca-rootkey) | Caddy keeps auto-issuing/renewing leaf certs itself, just signed by your root |
| A specific certificate **already issued for your exact domain** (e.g. handed to you by network admins) — a cert + key pair, not a signing CA | [Option B](#option-b-load-a-pre-issued-certificate-directly) | Caddy serves that exact file pair; no issuance, no renewal, no DNS resolution needed at all |

If Caddy is failing with something like "could not resolve domain" or an ACME/ownership
validation error, and you already have a cert+key for that exact domain, you almost certainly
want **Option B** — it bypasses automatic HTTPS (and the domain-resolution/validation it does)
entirely.

## Option A: reuse a CA root+key

Use this when you already have a CA certificate **and its private key** (e.g. the same root
you already generated/trusted for another environment) and you want the production Caddy
container to sign its TLS certs with that root instead of generating a brand-new one — with
zero changes to the Caddyfile or docker-compose files. Caddy is assumed to already be up and
running (`docker compose -f docker-compose.prod.yaml ps caddy` shows `Up`).

This only works if `DOMAIN` in `lessley-cd/.env` is a non-public name/IP (Caddy's own
hostname, an internal DNS name, or `localhost`). If `DOMAIN` looks like a real registrable
public domain, Caddy ignores what's in storage and tries Let's Encrypt instead.

### Before you start

> **You need the private key, not just the public cert.** A root cert you previously
> extracted for *trusting* on a client (e.g. via `docker compose cp caddy:.../root.crt ...`,
> as documented in `RUNNING.md`) is **not enough** — that only gives browsers something to
> validate against. To make Caddy actually *issue new certificates* under that same identity,
> it needs the matching `root.key` too. If you only have `root.crt`, you cannot reuse that CA
> here; either locate the original `root.key` (wherever that CA was first generated) or
> generate a fresh CA and trust it everywhere instead.

You should have two files ready on the machine you're running `docker compose` from:
- `root.crt`
- `root.key`

### Steps

All commands below assume you're in `lessley-cd/` and use the prod compose file; swap
`-f docker-compose.prod.yaml` for the dev file if you're doing this against Mode 2 instead.
Run them from **PowerShell**, not Git Bash/WSL — MSYS-based shells rewrite POSIX-looking
paths like `/data/caddy/...` into a Windows path before Docker ever sees them, which breaks
the container-side half of these commands.

**1. Make sure the destination directory exists.** Caddy only creates
`pki/authorities/local` lazily, the first time it needs an internal CA — if this container has
never handled an HTTPS request yet, the directory won't exist and `docker cp` won't create it
for you:

```powershell
docker compose -f docker-compose.prod.yaml exec caddy mkdir -p /data/caddy/pki/authorities/local
```

**2. Copy your CA files into the running container**, overwriting whatever Caddy generated
for itself on first boot:

```powershell
docker compose -f docker-compose.prod.yaml cp .\root.crt caddy:/data/caddy/pki/authorities/local/root.crt
docker compose -f docker-compose.prod.yaml cp .\root.key caddy:/data/caddy/pki/authorities/local/root.key
```

**3. Remove the old intermediate cert/key.** Caddy's internal issuer signs leaf certs with an
intermediate, not the root directly. The existing intermediate was signed by the *old* root,
so it won't chain to your new one — delete it so Caddy generates a fresh intermediate signed
by your root:

```powershell
docker compose -f docker-compose.prod.yaml exec caddy rm -f /data/caddy/pki/authorities/local/intermediate.crt /data/caddy/pki/authorities/local/intermediate.key
```

**4. Remove any already-issued leaf certificate for your domain.** Caddy caches issued certs
and won't reissue a still-valid one on its own, so the old cert (signed under the old root)
would keep being served otherwise:

```powershell
# See what's actually cached first if you're not sure of the exact folder name:
docker compose -f docker-compose.prod.yaml exec caddy ls /data/caddy/certificates/local/

docker compose -f docker-compose.prod.yaml exec caddy rm -rf "/data/caddy/certificates/local/<your-domain>"
```

**5. Restart Caddy** so it reloads cleanly with the new files in place:

```powershell
docker compose -f docker-compose.prod.yaml restart caddy
```

**6. Force a fresh handshake** so Caddy actually issues a new leaf cert under your root (it
issues lazily, on first connection, not at startup):

```powershell
curl -k https://<DOMAIN>
```

**7. Verify the chain.** Check Caddy's logs for errors, and confirm the served cert's issuer
matches your CA:

```powershell
docker compose -f docker-compose.prod.yaml logs caddy --tail 50
openssl s_client -connect <DOMAIN>:443 -servername <DOMAIN> </dev/null 2>$null | openssl x509 -noout -issuer -subject
```

**8. Trust the root on client machines**, if they don't already trust it — same
`root.crt`, installed as a Trusted Root Certification Authority (Windows: double-click →
Install Certificate → Local Machine → Trusted Root Certification Authorities).

### Rolling back Option A

To go back to Caddy's own self-generated CA, delete everything you copied in and restart —
Caddy regenerates a fresh root, intermediate, and leaf cert automatically:

```powershell
docker compose -f docker-compose.prod.yaml exec caddy rm -rf /data/caddy/pki/authorities/local /data/caddy/certificates/local
docker compose -f docker-compose.prod.yaml restart caddy
curl -k https://<DOMAIN>
```

### Troubleshooting Option A

- **Browser still shows the old cert / a warning after step 6.** Browsers cache TLS sessions
  aggressively. Verify server-side with `curl -k` or `openssl s_client` first (step 7) before
  assuming Caddy is still wrong — a hard refresh or a fresh browser profile usually clears it.
- **`docker compose exec caddy rm` fails with "no such file or directory".** Fine — it just
  means there was nothing to clean up at that path yet (e.g. no leaf cert had been issued for
  that domain). Continue to the next step.
- **Caddy logs show an ACME/Let's Encrypt attempt instead of using your CA.** `DOMAIN` in
  `.env` looks like a public hostname to Caddy. Confirm it's set to something non-public and
  restart.

## Option B: load a pre-issued certificate directly

Use this when you were handed a **specific certificate + private key already issued for your
exact domain** — e.g. by a college or corporate network's own PKI — and you don't want Caddy
to try to obtain or generate anything at all. This is what fixes Caddy failing to resolve a
private/local-only DNS name: automatic HTTPS (ACME or the internal issuer) was still trying to
validate or generate a cert for that domain, which requires DNS resolution it can't do.
Pointing Caddy at a static file pair skips that logic completely — no resolution needed.

This works via an optional `CADDY_TLS_DIRECTIVE` env var wired into the shared `Caddyfile`
(`lessley-cd/Caddyfile`). Left unset (the default everywhere else), it's a no-op — dev and any
normal public-domain prod deployment are unaffected.

### Steps

**1. Drop your cert and key into `lessley-cd/certs/`** (this directory is gitignored — the
private key must never be committed):

```
lessley-cd/certs/college.crt
lessley-cd/certs/college.key
```

That directory is already mounted read-only into the `caddy` container at `/etc/caddy/certs`
by both compose files.

**2. Set `DOMAIN`** in `lessley-cd/.env` to the private DNS name your college gave you (the
same one the certificate was issued for).

**3. Set `CADDY_TLS_DIRECTIVE`** in `lessley-cd/.env` to the full Caddy `tls` directive,
pointing at the in-container paths (not your host paths):

```
CADDY_TLS_DIRECTIVE=tls /etc/caddy/certs/college.crt /etc/caddy/certs/college.key
```

**4. Restart Caddy** so it picks up the new env var and config:

```powershell
docker compose -f docker-compose.prod.yaml up -d --build caddy
```

**5. Verify.** Caddy's logs should show no ACME/resolution attempts at all, and the served
cert should be your college's:

```powershell
docker compose -f docker-compose.prod.yaml logs caddy --tail 50
curl -kv https://<DOMAIN> 2>&1 | grep -i "issuer\|subject"
```

No client trust setup needed here — the certificate is already trusted by whatever CA your
college's network devices already trust.

### Rolling back Option B

Clear the variable and restart — Caddy falls straight back to automatic HTTPS:

```
CADDY_TLS_DIRECTIVE=
```
```powershell
docker compose -f docker-compose.prod.yaml up -d --build caddy
```

### Why this couldn't just be `tls {$CERT_FILE} {$KEY_FILE}` with blank defaults

Worth knowing if you ever touch the Caddyfile: a bare `tls` directive with empty/no arguments
is a **Caddyfile parse error**, not a no-op (confirmed by running `caddy validate` — Caddy
refuses to even start). Making the *entire* directive — including the word `tls` itself — come
from one placeholder is what makes "unset" a true no-op (an empty line, which Caddy just
skips), without touching the directive's argument-count validation at all. Don't reintroduce
the two-separate-placeholder version.
