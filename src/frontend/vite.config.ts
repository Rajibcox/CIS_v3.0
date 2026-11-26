import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../../dist', // Output to QUANTUM_TRADER_V1/dist
  },
  server: {
    port: 3000, // Frontend dev server port
    proxy: {
      '/api': 'http://localhost:8000', // Proxy API requests to backend
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})