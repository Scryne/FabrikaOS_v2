/**
 * Sunucu-taraflı sayfalama/sıralama/arama/filtre parametre modeli + sorgu dizesi üretimi.
 *
 * Backend liste uçlarıyla aynı dil: ``?sayfa=&adet=&siralama=&yon=&arama=`` + modüle özgü
 * filtreler (durum, makine_id, aktif…). Boş/tanımsız değerler dizeye yazılmaz.
 */

export type SiralamaYon = 'asc' | 'desc';

export type FiltreDeger = string | number | boolean | undefined;

export type SayfaParam = {
  sayfa: number;
  adet: number;
  siralama?: string;
  yon?: SiralamaYon;
  arama?: string;
  /** Modüle özgü ek filtreler (ör. ``{ durum: 'calisiyor', makine_id: 4 }``). */
  filtreler?: Record<string, FiltreDeger>;
};

export const VARSAYILAN_SAYFA: SayfaParam = { sayfa: 1, adet: 20 };

/** ``SayfaParam``dan backend'in beklediği sorgu dizesini üretir (boş alanları atar). */
export function sorguDizesi(param: SayfaParam): string {
  const usp = new URLSearchParams();
  usp.set('sayfa', String(param.sayfa));
  usp.set('adet', String(param.adet));
  if (param.siralama) {
    usp.set('siralama', param.siralama);
    usp.set('yon', param.yon ?? 'asc');
  }
  const arama = param.arama?.trim();
  if (arama) usp.set('arama', arama);
  for (const [anahtar, deger] of Object.entries(param.filtreler ?? {})) {
    if (deger !== undefined && deger !== '') usp.set(anahtar, String(deger));
  }
  return usp.toString();
}
