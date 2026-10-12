import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const https = {
  key: readFileSync(fileURLToPath(new URL('../certs/lan-dev-key.pem', import.meta.url))),
  cert: readFileSync(fileURLToPath(new URL('../certs/lan-dev.pem', import.meta.url))),
};

const backendTarget = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    https,
    proxy: {
      // Vite proxies locally to the backend; the browser only calls this HTTPS origin.
      '/health': { target: backendTarget, changeOrigin: true },
      '/api': { target: backendTarget, changeOrigin: true },
      '/auth': { target: backendTarget, changeOrigin: true },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    https,
    proxy: {
      '/health': { target: backendTarget, changeOrigin: true },
      '/api': { target: backendTarget, changeOrigin: true },
      '/auth': { target: backendTarget, changeOrigin: true },
    },
  },
});
