import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  cacheDir: '/tmp/.vite',
  server: {
    port: 5173,
    proxy: {
      '/api/': {
        target: 'http://api:8000',
        changeOrigin: true,
        timeout: 5 * 60 * 1000, // 5 minutes for large file uploads
      },
    },
  },
})
