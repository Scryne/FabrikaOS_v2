/**
 * Talep durum makinesi **aynası** — backend ``talep/durum.py`` ile birebir.
 * UI yalnız geçerli hedefleri gösterir; nihai doğrulama backend'dedir.
 */

export const GECISLER: Record<string, string[]> = {
  acik: ['inceleniyor', 'iptal'],
  inceleniyor: ['cozuldu', 'iptal'],
  cozuldu: ['kapandi', 'inceleniyor'],
  kapandi: [],
  iptal: [],
};

export const TERMINAL = ['kapandi', 'iptal'] as const;

export function gecerliHedefler(mevcut: string): string[] {
  return GECISLER[mevcut] ?? [];
}
