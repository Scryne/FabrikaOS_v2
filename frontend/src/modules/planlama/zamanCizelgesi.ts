/**
 * Gantt zaman çizelgesinin saf hesapları (S30, ADR-0049) — DOM'suz, birim testli.
 *
 * Çizelge yatay eksende ``[bas, bit)`` aralığını yüzdeye çevirir; aralık dışına taşan parça
 * kırpılır, tamamen dışarıdaki parça çizilmez. İş durumu tek bir sınıfa indirgenir ki çubuk rengi,
 * tablo etiketi ve ekran okuyucu metni aynı kaynaktan gelsin.
 */

export type IsDurumu = 'zamaninda' | 'sira_gecikmesi' | 'kapasite_asimi' | 'sigmadi';

export type DurumGirdisi = {
  gecikme_dk: number;
  sigmadi: boolean;
  kapasite_asimi: boolean;
  sira_kaynakli_gecikme: boolean;
};

/** Öncelik: sığmadı > kapasite aşımı > sıra kaynaklı gecikme > zamanında. */
export function isDurumu(i: DurumGirdisi): IsDurumu {
  if (i.sigmadi) return 'sigmadi';
  if (i.kapasite_asimi) return 'kapasite_asimi';
  if (i.sira_kaynakli_gecikme || i.gecikme_dk > 0) return 'sira_gecikmesi';
  return 'zamaninda';
}

export type Yerlesim = { sol: number; genislik: number };

/**
 * ``[a, b)`` parçasının ``[bas, bit)`` ekseni üzerindeki konumu (yüzde). Eksen dışındaysa ``null``.
 * Çok kısa parçalar görünür kalsın diye en az ``enAz`` yüzde genişlik verilir.
 */
export function yerlestir(
  a: number,
  b: number,
  bas: number,
  bit: number,
  enAz = 0.35,
): Yerlesim | null {
  const toplam = bit - bas;
  if (toplam <= 0 || b <= bas || a >= bit || b <= a) return null;
  const s = Math.max(a, bas);
  const e = Math.min(b, bit);
  const sol = ((s - bas) / toplam) * 100;
  const genislik = Math.max(((e - s) / toplam) * 100, enAz);
  return { sol, genislik: Math.min(genislik, 100 - sol) };
}

/** Dakikayı okunur süreye çevirir: 45 → "45 dk", 90 → "1 sa 30 dk", 1500 → "1 g 1 sa". */
export function sureMetni(dk: number): string {
  const d = Math.round(dk);
  if (d < 60) return `${d} dk`;
  const gun = Math.floor(d / 1440);
  const sa = Math.floor((d % 1440) / 60);
  const kalan = d % 60;
  if (gun > 0) return sa > 0 ? `${gun} g ${sa} sa` : `${gun} g`;
  return kalan > 0 ? `${sa} sa ${kalan} dk` : `${sa} sa`;
}

/** Günlük yük oranı (0–∞); kapasite yoksa ``null`` (o gün vardiya yok). */
export function yukOrani(planDk: number, kapasiteDk: number): number | null {
  if (kapasiteDk <= 0) return null;
  return planDk / kapasiteDk;
}

/** Yük oranına göre ton: boş / normal / yoğun (≥%85) / dolu (≥%100). */
export function yukTonu(oran: number | null): 'yok' | 'bos' | 'normal' | 'yogun' | 'dolu' {
  if (oran === null) return 'yok';
  if (oran <= 0) return 'bos';
  if (oran >= 0.995) return 'dolu';
  if (oran >= 0.85) return 'yogun';
  return 'normal';
}
