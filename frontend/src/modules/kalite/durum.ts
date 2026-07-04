/**
 * CAPA (uygunsuzluk) durum makinesi **aynası** — backend ``kalite/durum.py`` ile birebir.
 * UI yalnız geçerli hedefleri gösterir; nihai doğrulama backend'dedir (geçersiz geçiş 409).
 */

export const GECISLER: Record<string, string[]> = {
  acik: ['kok_neden', 'iptal'],
  kok_neden: ['aksiyon_plani', 'iptal'],
  aksiyon_plani: ['uygulama', 'iptal'],
  uygulama: ['dogrulama', 'iptal'],
  dogrulama: ['kapandi', 'uygulama', 'iptal'],
  kapandi: [],
  iptal: [],
};

export const TERMINAL = ['kapandi', 'iptal'] as const;
export const AKTIF = ['acik', 'kok_neden', 'aksiyon_plani', 'uygulama', 'dogrulama'] as const;

export function gecerliHedefler(mevcut: string): string[] {
  return GECISLER[mevcut] ?? [];
}
