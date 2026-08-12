/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// Ports (canonical scheme):
//   client 8000 (dev) / 5000 (prod preview) · gateway 8001 (dev) / 5001 (prod)
//   personalization 8002 (dev) / 5002 (prod) · deal-optimizer 8003 (dev) / 5003 (prod)
// The client talks ONLY to Caddy in prod (relative /api/v1 + /hubs, same-origin). This dev
// proxy stands in for Caddy: it routes the Personalization-owned prefixes to that service
// and everything else to the gateway, so the browser sees one origin either way.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const gatewayTarget = env.GATEWAY_PROXY_TARGET || 'http://localhost:8001'
  const personalizationTarget = env.PERSONALIZATION_PROXY_TARGET || 'http://localhost:8002'
  const optimizerTarget = env.OPTIMIZER_PROXY_TARGET || 'http://localhost:8003'

  // Mode 1 has no Caddy, so nothing authenticates the caller or injects the verified
  // identity in front of Personalization. It falls back to decoding the access_token
  // cookie itself (Environment=Development AND its own opt-in flag are both required) —
  // that cookie rides along with this proxy unchanged, so nothing extra is needed here.
  const personalizationProxy = {
    target: personalizationTarget,
    changeOrigin: true,
    rewrite: (p: string) => p.replace(/^\/api\/v1/, ''),
  }

  // The optimizer sits at the edge too, and carries its own /optimizer route prefix —
  // so Caddy and this proxy both strip only /api/v1. Mode 1 has no Caddy to forward_auth
  // the request, so the service needs Environment=Development AND Edge_AllowUnverified
  // to accept the access_token cookie as identity (see deal-optimizer/README.md).
  const optimizerProxy = {
    target: optimizerTarget,
    changeOrigin: true,
    rewrite: (p: string) => p.replace(/^\/api\/v1/, ''),
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 8000,
      // Fail loudly if 8000 is taken instead of silently drifting to another port
      // (a stray Vite drifting onto 8002 collided with Personalization — hard to debug).
      strictPort: true,
      // Proxy the gateway so the browser talks to it SAME-ORIGIN (mirrors Caddy in prod):
      // no CORS, and Secure/HttpOnly/SameSite cookies behave exactly as in prod. Point
      // GATEWAY_PROXY_TARGET at the gateway (http://localhost:8001 dotnet / 5001 docker).
      proxy: {
        // Personalization-owned prefixes FIRST — Vite matches by prefix in declaration
        // order, so a general '/api' entry above these would swallow them.
        // Keep this list identical to the `@personalization` matcher in lessley-cd/Caddyfile.
        // (/api/v1/clubs is NOT here: clubs are served by the Gateway's ClubController.)
        '/api/v1/insights': personalizationProxy,
        '/api/v1/open-finance': personalizationProxy,
        // Same rule: edge-owned prefix, must precede the general '/api' entry below.
        '/api/v1/optimizer': optimizerProxy,
        '/api': {
          target: gatewayTarget,
          changeOrigin: true,
          // Caddy does this rewrite in prod; the gateway's own routes stay at /api/*.
          rewrite: (p: string) => p.replace(/^\/api\/v1/, '/api'),
        },
        '/hubs': {
          target: gatewayTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    preview: {
      port: 5000,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: true,
    },
  }
})
