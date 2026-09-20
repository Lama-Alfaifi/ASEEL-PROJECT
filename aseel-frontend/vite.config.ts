import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// The ASEEL backend (main.py) does not enable CORS, so the browser talks to
// this dev/preview server at /api and Vite forwards the request to FastAPI.
// No backend change is needed. See README.md for the production equivalent.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const target = env.VITE_API_TARGET || 'http://127.0.0.1:8000';
  const proxy = {
    '/api': {
      target,
      changeOrigin: true,
      rewrite: (p: string) => p.replace(/^\/api/, ''),
      // The agent pipeline makes several LLM calls; allow slow answers.
      timeout: 180_000,
      proxyTimeout: 180_000,
    },
  };
  return {
    plugins: [react()],
    server: { port: 5173, proxy },
    preview: { port: 4173, proxy },
    build: { chunkSizeWarningLimit: 900 },
  };
});
