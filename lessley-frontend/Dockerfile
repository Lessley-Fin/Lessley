# ── Stage 1: build the SPA ────────────────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Production is same-origin (Caddy serves this SPA and routes /api/v1 + /hubs to the
# gateway), so API/SignalR calls must be relative. An empty base URL yields "/api/...".
# .env.production also sets this; the ENV here guarantees it even if that file is absent.
ENV VITE_API_GATEWAY_URL=""
RUN npm run build

# ── Stage 2: bake the built assets into the Caddy image ───────────────────────
FROM caddy:2-alpine
COPY --from=build /app/dist /srv/frontend
