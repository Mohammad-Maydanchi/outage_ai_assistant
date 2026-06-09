import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Runs the web page in development. The "proxy" quietly forwards any request
// to /requests or /health over to the backend at localhost:8000, so the page
// and the backend can talk without any extra setup.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/requests': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
