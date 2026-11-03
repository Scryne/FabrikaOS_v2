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
  // Token'ın kendisine değil varlığına abone olunur: yenilenen token soketi yeniden açtırmaz
  // (bağlantı güncel token'ı ``tokenAl`` ile okur).
  const tokenVar = useAuthStore((s) => s.access !== null && s.access !== '');
  const onizleme = useAuthStore((s) => s.access === 'onizleme');
  const [soketBagli, setSoketBagli] = useState(false);
  const tenant = cozumleTenant();

  const oturum = girisYapildi && !!tenant && tokenVar;
  const soketGerekli = oturum && !onizleme;
  // Bağlantı durumu türetilir: oturum yoksa kapalı, önizlemede soket açılmadan canlı.
  const bagli = !oturum ? false : onizleme ? true : soketBagli;

  useEffect(() => {
    if (!soketGerekli || !tenant) return;
    const baglanti = gercekZamanBaglan({
      tokenAl: () => useAuthStore.getState().access,
      tenant,
      onDurum: setSoketBagli,
      onOlay: (olay) => olayIsle(qc, olay),
    });
    return () => {
      baglanti.kapat();
      setSoketBagli(false);
    };
  }, [soketGerekli, tenant, qc]);

  return <GercekZamanBaglam.Provider value={{ bagli }}>{children}</GercekZamanBaglam.Provider>;
}
