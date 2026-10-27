import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// Only the env var below is read; declared here to avoid a @types/node dependency.
declare const process: { env: Record<string, string | undefined> };

// Dev server only: proxy to a backend started separately (default localhost:8000).
const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': backend,
      '/ws': { target: backend.replace(/^http/, 'ws'), ws: true },
    },
  },
  build: { sourcemap: false, target: 'es2022' },
  test: { environment: 'node' },
});
