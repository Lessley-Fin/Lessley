# 0008 — The bank-journey return URL is server-configured

**Status:** Accepted

## Context

`POST /api/v1/User/init` called `InitiateConnectionJourney(email)` with no redirect URL. The
payload builder drops nulls, so Open Finance was never told where to send the user back.

`BankingStep.tsx` navigates the whole page to the provider (`window.location.assign`) in the
middle of the registration wizard. Users left and did not come back.

The overload that accepts a return URL took it from a query string — and that value is followed
automatically after a successful bank link, which makes an attacker-supplied absolute URL an open
redirect at the most sensitive moment in the product.

## Decision

`OpenFinanceConfig:RedirectUrl` in configuration, wired to `https://${DOMAIN}/insights` in both
compose files — the same origin as the edge.

Callers may supply a **relative path** so different entry points can land on different screens.
Anything absolute is ignored in favour of the configured page, and `//evil.com` is rejected
explicitly as protocol-relative.

## Consequences

- Both callers of `InitiateConnectionJourney` are fixed by one change, and a third cannot forget.
- Changing the landing page is configuration, not a deploy.
- If the value is unset the behaviour reverts to today's — no redirect at all. It is wired in both
  compose files so this does not happen silently.
