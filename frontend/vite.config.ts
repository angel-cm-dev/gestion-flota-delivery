/// <reference types="vitest" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// En desarrollo, /api y /health se redirigen al backend para evitar CORS.
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': apiTarget,
      '/health': apiTarget,
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Leaflet pesa ~150 kB: en un chunk propio se cachea aparte del código de la app.
        manualChunks: { leaflet: ['leaflet', 'react-leaflet'], react: ['react', 'react-dom', 'react-router-dom'] },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
