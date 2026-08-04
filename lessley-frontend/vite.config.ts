/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // The Gateway's CorsOrigins allows http://localhost:8000, so the dev server
    // has to serve from that origin or every API call is blocked by CORS.
    // strictPort makes a taken port fail loudly instead of silently falling back
    // to another port that the Gateway would then reject.
    port: 8000,
    strictPort: true,
    proxy: {
      '/personalization': {
        target: process.env.VITE_PERSONALIZATION_PROXY_TARGET ?? 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/personalization/, ''),
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
})
