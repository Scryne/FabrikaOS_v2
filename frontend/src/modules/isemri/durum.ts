/**
 * İş emri durum makinesi — backend ``app/modules/isemri/durum.py`` aynası.
 *
 * Yaşam döngüsü: acik → atandi → devam_ediyor → kapandi; her aktif aşamadan iptal.
 * Terminal (kapandi/iptal) durumlarından çıkış yoktur. UI yalnız geçerli hedefleri sunar;
 * yetkisiz/yanlış geçişi backend 409 ile zaten reddeder (bu yalnız kullanıcı kolaylığı).
 *
 * ``atandi``ya geçiş ``atanan_kullanici_id`` gerektirir (atama akışı ekranda yönetilir).
 */

export const GECISLER: Record<string, readonly string[]> = {
  acik: ['atandi', 'iptal'],
  atandi: ['devam_ediyor', 'iptal'],
  devam_ediyor: ['kapandi', 'iptal'],
  kapandi: [],
  iptal: [],
};

export const DURUMLAR = ['acik', 'atandi', 'devam_ediyor', 'kapandi', 'iptal'] as const;
export type IsEmriDurum = (typeof DURUMLAR)[number];

/** Kanban'da kart olarak gösterilecek durum sütunları (soldan sağa akış). */
export const KANBAN_DURUMLARI: IsEmriDurum[] = ['acik', 'atandi', 'devam_ediyor', 'kapandi'];

export const TERMINAL_DURUMLAR = ['kapandi', 'iptal'] as const;
export const ONCELIKLER = ['dusuk', 'orta', 'yuksek', 'kritik'] as const;
export type Oncelik = (typeof ONCELIKLER)[number];

/** ``mevcut`` durumdan gidilebilecek geçerli hedef durumlar (tanımsızsa boş). */
export function gecerliHedefler(mevcut: string): readonly string[] {
  return GECISLER[mevcut] ?? [];
}

export function terminalMi(durum: string): boolean {
  return (TERMINAL_DURUMLAR as readonly string[]).includes(durum);
}
