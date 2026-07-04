import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
  },
  build: {
    // Büyük satıcıları ayrı, önbellek-dostu parçalara böl (echarts ~1MB, antd ~1.1MB —
    // DatePicker/rc-picker ile büyüdü; ikisi de tek izole satıcı parçası, gzip'te ~345KB).
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts'],
          antd: ['antd', '@ant-design/icons'],
          react: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // Vitest yalnız src birim/komponent testlerini çalıştırır; e2e Playwright'a aittir.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
