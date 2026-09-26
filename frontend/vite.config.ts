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
    chunkSizeWarningLimit: 1250,
    // Vite 8 (rolldown): eski `manualChunks` nesnesi kabul edilmiyor; yerel karşılığı
    // `advancedChunks` grupları. Öncelik yüksek olan grup önce eşleşir.
    rolldownOptions: {
      output: {
        advancedChunks: {
          groups: [
            { name: 'echarts', test: /node_modules[\\/](echarts|zrender)[\\/]/, priority: 30 },
            {
              name: 'react',
              test: /node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/,
              priority: 20,
            },
            {
              name: 'antd',
              test: /node_modules[\\/](antd|@ant-design|rc-[^\\/]+|@rc-component)[\\/]/,
              priority: 10,
            },
          ],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // antd formlarına userEvent.type ile yazan testler (KVKK, Webhook) jsdom'da 4-6 sn sürüyor;
    // Vitest 5'te 5 sn varsayılanına takılıp rastgele düşüyorlardı (2026-09-26 ölçümü).
    testTimeout: 15_000,
    // Vitest yalnız src birim/komponent testlerini çalıştırır; e2e Playwright'a aittir.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
