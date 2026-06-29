/**
 * Pano türev verileri (saf fonksiyonlar) — OEE özetinden filo ortalamaları, makine listesinden
 * durum dağılımı, OEE özetinden makine-bazlı çubuklar. Oranlar 0–1'den yüzdeye (0–100) çevrilir.
 */

import { MAKINE_DURUMLARI } from '@/components/DurumRozet';
import type { components } from '@/api/types.gen';

type OeeOzetSatir = components['schemas']['OeeOzetSatirDTO'];
type Makine = components['schemas']['MakineCevapDTO'];

export type FiloOzeti = {
  oee: number;
  kullanilabilirlik: number;
  performans: number;
  kalite: number;
};

/** OEE özeti satırlarının (üretimi olan makineler) yüzde cinsinden ortalamaları. */
export function filoOrtalamalari(ozet: OeeOzetSatir[]): FiloOzeti {
  if (ozet.length === 0) return { oee: 0, kullanilabilirlik: 0, performans: 0, kalite: 0 };
  const ort = (f: (s: OeeOzetSatir) => number) =>
    (ozet.reduce((a, s) => a + f(s), 0) / ozet.length) * 100;
  return {
    oee: ort((s) => s.oee),
    kullanilabilirlik: ort((s) => s.kullanilabilirlik),
    performans: ort((s) => s.performans),
    kalite: ort((s) => s.kalite),
  };
}

/** Makine durum dağılımı (bilinen durumlar sırayla; bilinmeyenler sona eklenir). */
export function durumDagilimi(makineler: Makine[]): { durum: string; adet: number }[] {
  const sayac = new Map<string, number>(MAKINE_DURUMLARI.map((d) => [d, 0]));
  for (const m of makineler) sayac.set(m.durum, (sayac.get(m.durum) ?? 0) + 1);
  return [...sayac.entries()].map(([durum, adet]) => ({ durum, adet }));
}

/** Makine-bazlı OEE çubukları (yüzde), en fazla ``limit`` makine. */
export function makineOeeCubuklari(
  ozet: OeeOzetSatir[],
  limit = 12,
): { ad: string; oee: number }[] {
  return ozet.slice(0, limit).map((s) => ({ ad: s.makine_kod, oee: s.oee * 100 }));
}
