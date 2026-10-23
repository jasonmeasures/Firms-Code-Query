/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const port = Number(env.VITE_DEV_PORT || 3000);
  const apiUrl = (env.VITE_API_URL || '').replace(/\/$/, '');
  const proxyTarget = env.VITE_API_PROXY || apiUrl || 'http://127.0.0.1:8080';
  return {
    plugins: [react()],
    server: {
      host: true,
      port,
      strictPort: true,
      proxy: apiUrl ? undefined : { '/api': { target: proxyTarget, changeOrigin: true } },
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
    },
  };
});
