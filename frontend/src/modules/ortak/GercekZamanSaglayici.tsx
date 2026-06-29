/**
 * Gerçek-zaman sağlayıcı — oturum açıkken WS'e bağlanır ve gelen olayları ilgili sorguları
 * geçersizleştirerek (olayIsle) işler; pano/listeler canlı güncellenir. Bağlantı durumu
 * context ile paylaşılır (canlı gösterge). DEV önizlemede (``access==='onizleme'``) soket
 * açılmaz, gösterge canlı sayılır.
 */

import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { gercekZamanBaglan } from '@/api/gercekzaman';
import { cozumleTenant } from '@/api/tenant';
import { useAuthStore } from '@/store/authStore';

import { GercekZamanBaglam } from './gercekZamanBaglam';
import { olayIsle } from './olayIsle';

export function GercekZamanSaglayici({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const girisYapildi = useAuthStore((s) => s.girisYapildi);
  const [bagli, setBagli] = useState(false);
  const tenant = cozumleTenant();

  useEffect(() => {
    if (!girisYapildi || !tenant) {
      setBagli(false);
      return;
    }
    const access = useAuthStore.getState().access;
    if (!access) {
      setBagli(false);
      return;
    }
    if (access === 'onizleme') {
      setBagli(true);
      return;
    }
    const baglanti = gercekZamanBaglan({
      tokenAl: () => useAuthStore.getState().access,
      tenant,
      onDurum: setBagli,
      onOlay: (olay) => olayIsle(qc, olay),
    });
    return () => baglanti.kapat();
  }, [girisYapildi, tenant, qc]);

  return <GercekZamanBaglam.Provider value={{ bagli }}>{children}</GercekZamanBaglam.Provider>;
}
