/**
 * İzin talebi durum makinesi **aynası** — backend ``ik/izin_durum.py`` ile birebir.
 * UI yalnız geçerli aksiyonları gösterir; nihai doğrulama backend'dedir.
 */

export const GECISLER: Record<string, string[]> = {
  taslak: ['onay_bekliyor', 'iptal'],
  onay_bekliyor: ['onaylandi', 'reddedildi', 'iptal'],
  onaylandi: [],
  reddedildi: [],
  iptal: [],
};

export const TERMINAL = ['onaylandi', 'reddedildi', 'iptal'] as const;

export function gecerliHedefler(mevcut: string): string[] {
  return GECISLER[mevcut] ?? [];
}
