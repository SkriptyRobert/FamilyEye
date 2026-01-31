import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const version = (() => {
  try {
    const v = readFileSync(resolve(__dirname, '../VERSION'), 'utf-8').trim()
    return v || '2.4.0'
  } catch {
    return '2.4.0'
  }
})()

export default defineConfig({
  plugins: [react()],
  base: process.env.GH_PAGES === '1' ? '/FamilyEye/' : '/',
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(version)
  },
  server: {
    port: 5174,
    open: true
  },
  build: {
    outDir: 'dist',
    target: 'esnext'
  }
})
