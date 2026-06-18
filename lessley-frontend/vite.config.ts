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
    proxy: {
      '/personalization': {
        target: process.env.VITE_PERSONALIZATION_PROXY_TARGET ?? 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/personalization/, ''),
      },
    },
  },
})
