/**
 * Sekme başlığı: "Ekran · FabrikaOS". Kabuklu ekranlarda kabuk menüden türetir; kabuksuz
 * yüzeyler (giriş, kiosk, dış portal) bu kancayı kendisi çağırır. Ad zaten ürün adını
 * taşıyorsa ("FabrikaOS Müşteri Portalı") sonek eklenmez.
 */

import { useEffect } from 'react';

const URUN = 'FabrikaOS';

export function sekmeBasligiMetni(ad: string | null | undefined): string {
  if (!ad) return URUN;
  return ad.includes(URUN) ? ad : `${ad} · ${URUN}`;
}

export function useSekmeBasligi(ad: string | null | undefined): void {
  const metin = sekmeBasligiMetni(ad);
  useEffect(() => {
    document.title = metin;
  }, [metin]);
}
