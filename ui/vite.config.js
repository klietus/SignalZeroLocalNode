import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = {
    ...process.env,
    ...loadEnv(mode, process.cwd(), '')
  };
  const proxyTarget = (env.VITE_DEV_PROXY_TARGET || 'http://localhost:8000').replace(/\/$/, '');

  const shouldOpen = env.VITE_DEV_SERVER_OPEN === 'true';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      open: shouldOpen,
      proxy: {
        '/symbols': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/symbol': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/domains': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/domains/external': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/sync/symbols': {
          target: proxyTarget,
          changeOrigin: true
        },
        '/query': {
          target: proxyTarget,
          changeOrigin: true
        }
      }
    }
  };
});
