/**
 * Dijital ikiz saf sunum yardımcıları (DOM/istek yok; birim testli).
 *
 * Koordinat modeli: backend yüzde (0–100) saklar; tuval 16:9 SVG viewBox'ına
 * (`TUVAL`) ölçeklenir. Sürükleme matematiği burada saf tutulur ki ekran bileşeni
 * yalnız olay bağlama işi yapsın.
 */

import type { components } from '@/api/types.gen';

export type IkizDurumCevap = components['schemas']['IkizDurumCevapDTO'];
export type IkizDugumDurum = components['schemas']['IkizDugumDurumDTO'];
export type YerlesmemisMakine = components['schemas']['YerlesmemisMakineDTO'];
export type IkizDugumGiris = components['schemas']['IkizDugumGirisDTO'];

/** Şema tuvali viewBox boyutları (16:9; x/y yüzdeleri bu alana ölçeklenir). */
export const TUVAL = { genislik: 160, yukseklik: 90 } as const;

/** Makine durumu → CSS renk değişkeni (LED + düğüm çerçevesi). */
export const DURUM_RENGI: Record<string, string> = {
  calisiyor: 'var(--basari)',
  durdu: 'var(--metin-soluk)',
  bakimda: 'var(--uyari)',
  ariza: 'var(--hata)',
};

export function durumRengi(durum: string): string {
  return DURUM_RENGI[durum] ?? 'var(--metin-soluk)';
}

/** Yüzde koordinatı [0,100] aralığına kırpar ve 0.1 hassasiyetine yuvarlar. */
export function yuzdeKirp(deger: number): number {
  const kirpik = Math.min(100, Math.max(0, deger));
  return Math.round(kirpik * 10) / 10;
}

/** Pointer konumunu (px) tuval dikdörtgenine göre yüzde koordinata çevirir. */
export function konumdanYuzde(
  istemciX: number,
  istemciY: number,
  kutu: { left: number; top: number; width: number; height: number },
): { x: number; y: number } {
  if (kutu.width <= 0 || kutu.height <= 0) return { x: 0, y: 0 };
  return {
    x: yuzdeKirp(((istemciX - kutu.left) / kutu.width) * 100),
    y: yuzdeKirp(((istemciY - kutu.top) / kutu.height) * 100),
  };
}

/** Yüzde koordinatı SVG viewBox koordinatına çevirir. */
export function svgKonum(x: number, y: number): { sx: number; sy: number } {
  return { sx: (x / 100) * TUVAL.genislik, sy: (y / 100) * TUVAL.yukseklik };
}

/** OEE oranını yüzde etiketi yapar (pencere verisi yoksa uzun tire). */
export function oeeEtiket(oee: number | null | undefined): string {
  return oee == null ? '—' : `%${Math.round(oee * 100)}`;
}

/** Durum ucundaki düğümleri PUT gövdesi düğümlerine indirger (taslak başlangıcı). */
export function taslakDugumler(dugumler: IkizDugumDurum[]): IkizDugumGiris[] {
  return dugumler.map((d) => ({ makine_id: d.makine_id, x: d.x, y: d.y, bolge: d.bolge }));
}

/** Yeni düğüm için mevcutlarla çakışmayan ilk ızgara konumu (düğüm kutusu ~%11×%11). */
export function bosKonum(dugumler: Pick<IkizDugumGiris, 'x' | 'y'>[]): { x: number; y: number } {
  for (let i = 0; i < 40; i++) {
    const aday = { x: 15 + (i % 8) * 11, y: 18 + Math.floor(i / 8) * 16 };
    const cakisiyor = dugumler.some(
      (d) => Math.abs(d.x - aday.x) < 11 && Math.abs(d.y - aday.y) < 12,
    );
    if (!cakisiyor) return aday;
  }
  return { x: 50, y: 50 };
}

/** Kiosk makine karosu — yerleşimden bağımsız tüm filo tek listede. */
export type KioskKaro = {
  makine_id: number;
  kod: string;
  ad: string;
  durum: string;
  oee: number | null;
  toplam_adet: number;
};

/** Düğümler + yerleşmemişleri kod sırasıyla kiosk karolarına birleştirir. */
export function kioskKarolari(veri: Pick<IkizDurumCevap, 'dugumler' | 'yerlesmemis'>): KioskKaro[] {
  const karolar: KioskKaro[] = [
    ...veri.dugumler.map((d) => ({
      makine_id: d.makine_id,
      kod: d.makine_kod,
      ad: d.makine_ad,
      durum: d.durum,
      oee: d.oee ?? null,
      toplam_adet: d.toplam_adet,
    })),
    ...veri.yerlesmemis.map((m) => ({
      makine_id: m.makine_id,
      kod: m.makine_kod,
      ad: m.makine_ad,
      durum: m.durum,
      oee: null,
      toplam_adet: 0,
    })),
  ];
  return karolar.sort((a, b) => a.kod.localeCompare(b.kod, 'tr'));
}
