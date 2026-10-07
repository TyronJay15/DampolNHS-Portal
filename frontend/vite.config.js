import fs from 'node:fs'
import path from 'node:path'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

function productionRecaptchaSiteKey(root) {
  const fromProcess = (process.env.VITE_RECAPTCHA_SITE_KEY || '').trim()
  if (fromProcess) return fromProcess
  for (const name of ['.env.production.local', '.env.production']) {
    const file = path.join(root, name)
    if (!fs.existsSync(file)) continue
    const line = fs.readFileSync(file, 'utf8').split(/\r?\n/).find((row) => row.startsWith('VITE_RECAPTCHA_SITE_KEY='))
    const value = line ? line.slice('VITE_RECAPTCHA_SITE_KEY='.length).trim().replace(/^['"]|['"]$/g, '') : ''
    if (value) return value
  }
  return ''
}

function requireRecaptchaSiteKey(mode) {
  return {
    name: 'require-recaptcha-site-key',
    configResolved(config) {
      if (mode !== 'production') return
      if (productionRecaptchaSiteKey(config.root)) return
      throw new Error(
        'VITE_RECAPTCHA_SITE_KEY is missing from the production build. Set it for the build, or in .env.production. Local npm run dev may leave it empty.',
      )
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  return {
    plugins: [react(), requireRecaptchaSiteKey(mode)],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/media': 'http://localhost:8000',
      },
    },
  }
})
