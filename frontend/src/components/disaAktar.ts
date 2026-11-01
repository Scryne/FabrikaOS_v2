/**
 * Liste dışa aktarma çekirdeği (S27-B, ADR-0046) — saf fonksiyonlar, DOM bilmez.
 *
 * CSV, Türkiye'deki Excel'in varsayılanına göre üretilir: ayraç `;`, ondalık virgül, UTF-8 BOM
 * (BOM'suz dosyada Excel Türkçe karakterleri bozar). Formül enjeksiyonuna karşı `= + - @` ile
 * başlayan metin hücreleri tek tırnakla etkisizleştirilir (OWASP CSV injection).
 */

export type DisaSutun<T> = {
  baslik: string;
  /** Kayıttan hücre değeri; yoksa ``alan`` doğrudan okunur. */
  deger?: (kayit: T) => string | number | boolean | null | undefined;
  alan?: string;
};

export const DISA_AKTAR_SINIRI = 5000;

const FORMUL = /^[=+\-@\t\r]/;

export function hucreDegeri<T>(kayit: T, s: DisaSutun<T>): string | number | null {
  const ham = s.deger
    ? s.deger(kayit)
    : s.alan
      ? (kayit as Record<string, unknown>)[s.alan]
      : undefined;
  if (ham === null || ham === undefined || ham === '') return null;
  if (typeof ham === 'boolean') return ham ? 'Evet' : 'Hayır';
  if (typeof ham === 'number') return ham;
  if (typeof ham === 'object') return JSON.stringify(ham);
  return String(ham);
}

function csvHucre(v: string | number | null): string {
  if (v === null) return '';
  if (typeof v === 'number') return String(v).replace('.', ',');
  const metin = FORMUL.test(v) && Number.isNaN(Number(v.replace(',', '.'))) ? `'${v}` : v;
  return /[";\n\r]/.test(metin) ? `"${metin.replace(/"/g, '""')}"` : metin;
}

export function csvUret<T>(kayitlar: T[], sutunlar: DisaSutun<T>[]): string {
  const satirlar = [
    sutunlar.map((s) => csvHucre(s.baslik)).join(';'),
    ...kayitlar.map((k) => sutunlar.map((s) => csvHucre(hucreDegeri(k, s))).join(';')),
  ];
  return '﻿' + satirlar.join('\r\n') + '\r\n';
}

export function dosyaAdi(temel: string, uzanti: 'csv' | 'xlsx', simdi = new Date()): string {
  const g = (n: number) => String(n).padStart(2, '0');
  const damga = `${simdi.getFullYear()}${g(simdi.getMonth() + 1)}${g(simdi.getDate())}-${g(simdi.getHours())}${g(simdi.getMinutes())}`;
  const guvenli = temel.replace(/[^\p{L}\p{N}_-]+/gu, '-').replace(/^-+|-+$/g, '') || 'liste';
  return `${guvenli}-${damga}.${uzanti}`;
}

/**
 * Tablo sütunlarından dışa aktarma sütunu türetir: başlığı metin ve ``dataIndex``i düz alan olan
 * sütunlar alınır (işlem/ikon sütunları atlanır). ``cevir`` kodlu alanları okunur etikete çevirir.
 * Alanı kayıtlarda hiç bulunmayan sütun ``bosSutunlariAt`` ile indirme anında düşer.
 */
export function kolonlardanSutunlar<T>(
  kolonlar: readonly { title?: unknown; dataIndex?: unknown; key?: unknown }[],
  cevir: Partial<Record<string, (v: unknown, kayit: T) => string>> = {},
): DisaSutun<T>[] {
  return kolonlar.flatMap((k) => {
    // dataIndex yoksa key alan adı sayılır (render'lı "Ad" sütunları çoğunlukla key taşır).
    const alan =
      typeof k.dataIndex === 'string' ? k.dataIndex : typeof k.key === 'string' ? k.key : null;
    if (typeof k.title !== 'string' || !k.title || !alan) return [];
    const c = cevir[alan];
    return [
      c
        ? { baslik: k.title, deger: (r: T) => c((r as Record<string, unknown>)[alan], r) }
        : { baslik: k.title, alan },
    ];
  });
}

/**
 * İndirme anında sütunları kesinleştirir:
 * - hiçbir kayıtta değeri olmayan (hesaplanmış görünüm) sütun atılır;
 * - ``kod`` alanına bağlı sütun "Kod" başlığını alır (tablolar çoğu zaman kod+adı tek "Ad"
 *   hücresinde gösterir, başlık yanıltıcı kalırdı);
 * - kayıtta kimlik alanları (kod, ad, ad_soyad, başlık) varsa ve sütunlarda yoksa başa eklenir:
 *   dışa aktarılan her satır tanımlanabilir kalır.
 */
export function bosSutunlariAt<T>(
  kayitlar: T[],
  sutunlar: DisaSutun<T>[],
  kimlikBasliklari: Record<string, string> = {
    kod: 'Kod',
    ad: 'Ad',
    ad_soyad: 'Ad soyad',
    baslik: 'Başlık',
  },
): DisaSutun<T>[] {
  const dolu = sutunlar
    .filter((s) => s.deger || kayitlar.some((k) => hucreDegeri(k, s) !== null))
    .map((s) =>
      s.alan === 'kod' && kimlikBasliklari.kod ? { ...s, baslik: kimlikBasliklari.kod } : s,
    );
  const eklenecek = Object.entries(kimlikBasliklari)
    .filter(
      ([alan]) =>
        !dolu.some((s) => s.alan === alan) &&
        kayitlar.some((k) => (k as Record<string, unknown>)[alan] != null),
    )
    .map(([alan, baslik]) => ({ baslik, alan }));
  return [...eklenecek, ...dolu];
}
