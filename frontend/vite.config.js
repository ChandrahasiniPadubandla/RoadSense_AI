
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  const useHttps = env.VITE_ENABLE_HTTPS === 'true';
  const keyPath = fileURLToPath(
    new URL('../certs/lan-dev-key.pem', import.meta.url)
  );
  const certPath = fileURLToPath(
    new URL('../certs/lan-dev.pem', import.meta.url)
  );

  const https =
    useHttps && existsSync(keyPath) && existsSync(certPath)
      ? {
          key: readFileSync(keyPath),
          cert: readFileSync(certPath),
        }
      : false;

  const backendTarget =
    env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

  return {
    plugins: [react()],

    server: {
      host: '0.0.0.0',
      port: 5173,
      https,

      // Allow the Render hostname
      allowedHosts: ['roadsense-ai-pffi.onrender.com'],

      proxy: {
        '/health': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/api': {
          target: backendTarget,
          changeOrigin: true,
        },
        '/auth': {
          target: backendTarget,
          changeOrigin: true,
        },
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
  };
});
