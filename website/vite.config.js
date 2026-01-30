import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: process.env.GH_PAGES === '1' ? '/Parential-Control_Enterprise/' : '/',
  server: {
    port: 5174,
    open: true
  },
  build: {
    outDir: 'dist',
    target: 'esnext'
  }
})
