/**
 * Sözleşme durum makinesi **aynası** — backend ``sozlesme/durum.py`` ile birebir.
 * UI yalnız geçerli hedefleri gösterir; nihai doğrulama backend'dedir.
 */

export const GECISLER: Record<string, string[]> = {
  taslak: ['aktif', 'iptal'],
  aktif: ['sonlandi', 'feshedildi', 'iptal'],
  sonlandi: [],
  feshedildi: [],
  iptal: [],
};

export const TERMINAL = ['sonlandi', 'feshedildi', 'iptal'] as const;

export function gecerliHedefler(mevcut: string): string[] {
  return GECISLER[mevcut] ?? [];
}
