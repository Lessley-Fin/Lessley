---
name: react-dev
description: 'Start the Vite dev server for the Lessley React frontend. Use when: developing UI features, testing visual changes, debugging frontend behavior, or verifying that components render correctly.'
argument-hint: 'react-dev to start the frontend dev server'
user-invocable: true
---

# React Dev Server

Start the Lessley frontend development server with hot module replacement.

## Command

```bash
cd lessley-frontend && npm run dev
```

## What it does

- Starts Vite dev server on `http://localhost:5173`
- Enables HMR (hot module replacement) for instant feedback
- Proxies `/personalization` requests to the Personalization service (default `http://localhost:8002`)
- Requires the API Gateway to be running at `http://localhost:8001` (or set `VITE_API_GATEWAY_URL`)

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_GATEWAY_URL` | `http://localhost:8001` | Gateway API base URL |
| `VITE_PERSONALIZATION_PROXY_TARGET` | `http://localhost:8002` | Personalization service proxy target |

## Prerequisites

- Run `npm install` in `lessley-frontend/` if `node_modules/` is missing
- Backend services should be running (see `lessley-cd/` Docker Compose)
