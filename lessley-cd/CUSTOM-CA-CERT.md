# Loading your own CA root+key into a running Caddy container

Use this when you already have a CA certificate **and its private key** (e.g. the same root
you already generated/trusted for another environment) and you want the production Caddy
container to sign its TLS certs with that root instead of generating a brand-new one — with
zero changes to the Caddyfile or docker-compose files. Caddy is assumed to already be up and
running (`docker compose -f docker-compose.prod.yaml ps caddy` shows `Up`).

This only works if `DOMAIN` in `lessley-cd/.env` is a non-public name/IP (Caddy's own
hostname, an internal DNS name, or `localhost`). If `DOMAIN` looks like a real registrable
public domain, Caddy ignores what's in storage and tries Let's Encrypt instead.

## Before you start

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

## Steps

All commands below assume you're in `lessley-cd/` and use the prod compose file; swap
`-f docker-compose.prod.yaml` for the dev file if you're doing this against Mode 2 instead.

**1. Copy your CA files into the running container**, overwriting whatever Caddy generated
for itself on first boot:

```powershell
docker compose -f docker-compose.prod.yaml cp .\root.crt caddy:/data/caddy/pki/authorities/local/root.crt
docker compose -f docker-compose.prod.yaml cp .\root.key caddy:/data/caddy/pki/authorities/local/root.key
```

**2. Remove the old intermediate cert/key.** Caddy's internal issuer signs leaf certs with an
intermediate, not the root directly. The existing intermediate was signed by the *old* root,
so it won't chain to your new one — delete it so Caddy generates a fresh intermediate signed
by your root:

```powershell
docker compose -f docker-compose.prod.yaml exec caddy rm -f /data/caddy/pki/authorities/local/intermediate.crt /data/caddy/pki/authorities/local/intermediate.key
```

**3. Remove any already-issued leaf certificate for your domain.** Caddy caches issued certs
and won't reissue a still-valid one on its own, so the old cert (signed under the old root)
would keep being served otherwise:

```powershell
# See what's actually cached first if you're not sure of the exact folder name:
docker compose -f docker-compose.prod.yaml exec caddy ls /data/caddy/certificates/local/

docker compose -f docker-compose.prod.yaml exec caddy rm -rf "/data/caddy/certificates/local/<your-domain>"
```

**4. Restart Caddy** so it reloads cleanly with the new files in place:

```powershell
docker compose -f docker-compose.prod.yaml restart caddy
```

**5. Force a fresh handshake** so Caddy actually issues a new leaf cert under your root (it
issues lazily, on first connection, not at startup):

```powershell
curl -k https://<DOMAIN>
```

**6. Verify the chain.** Check Caddy's logs for errors, and confirm the served cert's issuer
matches your CA:

```powershell
docker compose -f docker-compose.prod.yaml logs caddy --tail 50
openssl s_client -connect <DOMAIN>:443 -servername <DOMAIN> </dev/null 2>$null | openssl x509 -noout -issuer -subject
```

**7. Trust the root on client machines**, if they don't already trust it — same
`root.crt`, installed as a Trusted Root Certification Authority (Windows: double-click →
Install Certificate → Local Machine → Trusted Root Certification Authorities).

## Rolling back

To go back to Caddy's own self-generated CA, delete everything you copied in and restart —
Caddy regenerates a fresh root, intermediate, and leaf cert automatically:

```powershell
docker compose -f docker-compose.prod.yaml exec caddy rm -rf /data/caddy/pki/authorities/local /data/caddy/certificates/local
docker compose -f docker-compose.prod.yaml restart caddy
curl -k https://<DOMAIN>
```

## Troubleshooting

- **Browser still shows the old cert / a warning after step 5.** Browsers cache TLS sessions
  aggressively. Verify server-side with `curl -k` or `openssl s_client` first (step 6) before
  assuming Caddy is still wrong — a hard refresh or a fresh browser profile usually clears it.
- **`docker compose exec caddy rm` fails with "no such file or directory".** Fine — it just
  means there was nothing to clean up at that path yet (e.g. no leaf cert had been issued for
  that domain). Continue to the next step.
- **Caddy logs show an ACME/Let's Encrypt attempt instead of using your CA.** `DOMAIN` in
  `.env` looks like a public hostname to Caddy. Confirm it's set to something non-public and
  restart.
