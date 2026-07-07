/**
 * AI modülü saf sunum yardımcıları — tür/yol eşlemeleri, rozet renkleri, model özeti.
 *
 * Backend `birimler.py` beyaz-listesinin aynasıdır; sonuç listelerinin alan sözleşmeleri
 * `modeller.py` tahmin fonksiyonlarında sabittir (buradaki tipler onların aynasıdır).
 */

import type { components } from '@/api/types.gen';

export type ModelKaydi = components['schemas']['ModelKaydiCevapDTO'];
export type TahminCevap = components['schemas']['TahminCevapDTO'];

export const MODEL_TURLERI = ['kestirimci_bakim', 'anomali', 'oee', 'stok'] as const;
export type ModelTuru = (typeof MODEL_TURLERI)[number];

/** tur → REST yolu (`/tahmin/<yol>`). */
export const TAHMIN_YOLU: Record<ModelTuru, string> = {
  kestirimci_bakim: 'kestirimci-bakim',
  anomali: 'anomali',
  oee: 'oee',
  stok: 'stok',
};

/** Model kaydı durumu → antd Tag rengi. */
export const DURUM_RENK: Record<string, string> = {
  hazir: 'success',
  egitiliyor: 'processing',
  basarisiz: 'error',
};

/** Kestirimci bakım risk seviyesi → antd Tag rengi. */
export const SEVIYE_RENK: Record<string, string> = {
  dusuk: 'success',
  orta: 'warning',
  yuksek: 'error',
};

/** Stok kalan gününü aciliyet rengine eşler. */
export function kalanGunRenk(kalanGun: number): string {
  if (kalanGun <= 7) return 'error';
  if (kalanGun <= 14) return 'warning';
  return 'success';
}

/**
 * Tür başına en güncel kaydı seçer. Liste `id` azalan geldiğinden türün ilk görülen
 * kaydı en yenisidir (eğitim sürüyorsa o görünür — kullanıcı ilerlemeyi izler).
 */
export function sonModeller(kayitlar: ModelKaydi[]): Partial<Record<ModelTuru, ModelKaydi>> {
  const sonuc: Partial<Record<ModelTuru, ModelKaydi>> = {};
  for (const kayit of kayitlar) {
    const tur = kayit.tur as ModelTuru;
    if (!(tur in sonuc)) sonuc[tur] = kayit;
  }
  return sonuc;
}

// --- Sonuç listesi alan sözleşmeleri (backend modeller.py aynası) ---
export type BakimSonuc = {
  makine_id: number;
  makine_kod: string;
  veri_gunu: string;
  risk_skoru: number;
  seviye: string;
};

export type OeeSonuc = {
  makine_id: number;
  makine_kod: string;
  tahminler: { gun: string; oee: number }[];
};

export type StokSonuc = {
  malzeme_id: number;
  kod: string;
  ad: string;
  birim: string;
  mevcut_miktar: number;
  kritik_stok: number;
  gunluk_tuketim: number;
  kalan_gun: number;
  onerilen_siparis: number;
};

export type AnomaliSonuc = {
  makine_id: number;
  makine_kod: string;
  gun: string;
  skor: number;
  durus_orani: number;
  fire_orani: number;
  performans: number;
};
