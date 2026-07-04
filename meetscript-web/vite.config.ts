import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  cacheDir: '/tmp/.vite',
  server: {
    port: 5173,
    proxy: {
      '/api/': {
        // Docker Compose 内部 DNS（api 容器）；Windows 本地开发用 localhost:8000
        target: 'http://api:8000',
        changeOrigin: true,
        timeout: 5 * 60 * 1000, // 5 minutes for large file uploads
      },
    },
  },
})
