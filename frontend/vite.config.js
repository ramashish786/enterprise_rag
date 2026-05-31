import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy API calls to FastAPI when running `npm run dev` locally
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
