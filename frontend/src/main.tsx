/**
 * Uygulama girişi — sağlayıcı yığını: ConfigProvider (koyu tema) → AntD App (message bağlamı)
 * → QueryClient → Router → App. i18n yan etkiyle başlatılır.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App as AntdApp, ConfigProvider } from 'antd';
import trTR from 'antd/locale/tr_TR';

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
