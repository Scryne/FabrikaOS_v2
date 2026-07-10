/**
 * Platform rota kapısı — mount'ta saklı refresh ile sessiz giriş dener; oturum
 * yoksa /platform/giris'e yönlendirir. Tenant ``KorunanRota``'sından ayrık düzlem.
 */

import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { Spin } from 'antd';

import { platformOturumBaslat } from './kimlik';
import { usePlatformAuthStore } from './store';

export function PlatformKorunanRota() {
  const girisYapildi = usePlatformAuthStore((s) => s.girisYapildi);
  const [hazir, setHazir] = useState(girisYapildi);

  useEffect(() => {
    if (!hazir) void platformOturumBaslat().finally(() => setHazir(true));
  }, [hazir]);

  if (!hazir) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin />
      </div>
    );
  }
  if (!girisYapildi) return <Navigate to="/platform/giris" replace />;
  return <Outlet />;
}
