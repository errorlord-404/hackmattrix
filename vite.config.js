import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // Electron loads the production renderer from file://, so bundled assets
  // must resolve relative to dist/index.html instead of the drive root.
  base: './',
  plugins: [react(), tailwindcss()],
  // Electron can keep an existing renderer open while a new local build runs.
  // Retaining earlier hashed chunks prevents that renderer from requesting a
  // now-deleted lazy route module before the farmer restarts the app.
  build: { emptyOutDir: false },
})
