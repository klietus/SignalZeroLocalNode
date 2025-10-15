import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
    proxy: {
      '/symbols': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/symbol': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
