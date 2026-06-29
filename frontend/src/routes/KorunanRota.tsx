/**
 * Erişim kapıları:
 * - ``KorunanRota`` (layout): oturum yoksa /giris'e yönlendirir, varsa Outlet'i render eder.
 * - ``IzinKapisi`` (sarmalayıcı): gerekli RBAC izni yoksa Yetkisiz sayfasını gösterir.
 */

import type { ReactNode } from 'react';
import { Navigate, Outlet } from 'react-router-dom';

import { YetkisizSayfa } from '@/components/YetkisizSayfa';
import { useAuthStore } from '@/store/authStore';

export function KorunanRota() {
  const girisYapildi = useAuthStore((s) => s.girisYapildi);
  if (!girisYapildi) return <Navigate to="/giris" replace />;
  return <Outlet />;
}

export function IzinKapisi({ izin, children }: { izin: string; children: ReactNode }) {
  const izinVar = useAuthStore((s) => s.izinVar);
  if (!izinVar(izin)) return <YetkisizSayfa />;
  return <>{children}</>;
}
