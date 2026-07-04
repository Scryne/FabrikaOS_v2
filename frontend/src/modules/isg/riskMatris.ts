/**
 * Risk matrisi **aynası** — backend ``isg/risk_matrisi.py`` ile birebir. Yalnız form
 * önizlemesi içindir (skor/seviye nihai olarak sunucuda hesaplanır ve kaydedilir).
 */

export function riskSkoru(olasilik: number, siddet: number): number {
  return olasilik * siddet;
}

export function riskSeviyesi(skor: number): string {
  if (skor <= 4) return 'dusuk';
  if (skor <= 9) return 'orta';
  if (skor <= 15) return 'yuksek';
  return 'cok_yuksek';
}
