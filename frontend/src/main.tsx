/**
 * Uygulama girişi — sağlayıcı yığını: ConfigProvider (koyu tema) → AntD App (message bağlamı)
 * → QueryClient → Router → App. i18n yan etkiyle başlatılır.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App as AntdApp, ConfigProvider } from 'antd';
// ESM yolu: `antd/locale/tr_TR` CommonJS'tir; Vite 8 (rolldown) onu `default` altında
// sarıyordu ve locale sessizce İngilizceye düşüyordu ("20 / page", 2026-09-26).
import trTR from 'antd/es/locale/tr_TR';

import '@fontsource-variable/inter';
import '@fontsource-variable/jetbrains-mono';
import 'antd/dist/reset.css';
import './index.css';
import './i18n';

import { App } from './App';
import { tema } from './tema/tema';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const kok = document.getElementById('root');
if (!kok) throw new Error('#root bulunamadı');

ReactDOM.createRoot(kok).render(
  <React.StrictMode>
    <ConfigProvider theme={tema} locale={trTR}>
      <AntdApp>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </QueryClientProvider>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
);
