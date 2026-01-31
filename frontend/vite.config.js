import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: parseInt(process.env.VITE_DASHBOARD_PORT || '3000', 10),
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || process.env.VITE_DEFAULT_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  optimizeDeps: {
    exclude: ['@yume-chan/adb-daemon-webusb']
  },
  build: {
    target: 'esnext'
  }
})

