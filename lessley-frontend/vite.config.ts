/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// Ports (canonical scheme):
//   client 8000 (dev) / 5000 (prod preview) · gateway 8001 (dev) / 5001 (prod)
// The client talks ONLY to the gateway (relative /api + /hubs, proxied same-origin in dev,
// served by Caddy in prod). It never knows about the Personalization service.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const gatewayTarget = env.VITE_GATEWAY_PROXY_TARGET || 'http://localhost:8001'

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
      // VITE_GATEWAY_PROXY_TARGET at the gateway (http://localhost:8001 dotnet / 5001 docker).
      proxy: {
        '/api': {
          target: gatewayTarget,
          changeOrigin: true,
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
