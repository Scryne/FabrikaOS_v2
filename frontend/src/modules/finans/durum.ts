/**
 * Fatura durum makinesi — backend ``finans/durum.py`` ile birebir (S29, ADR-0048). Ekran yalnız
 * geçerli hedeflerin düğmelerini gösterir; son söz sunucunundur (409).
 */

export const FATURA_GECISLER: Record<string, readonly string[]> = {
  taslak: ['onay_bekliyor', 'iptal'],
  onay_bekliyor: ['kesildi', 'taslak', 'iptal'],
  kesildi: ['kapandi', 'iptal'],
  kapandi: [],
  iptal: [],
};

export function gecerliHedefler(durum: string): readonly string[] {
  return FATURA_GECISLER[durum] ?? [];
}

/**
 * Kalem tutarı — sunucuyla aynı kural: satır 2 basamağa yarım-yukarı yuvarlanır, KDV yuvarlanmış
 * satırdan hesaplanır. Formdaki canlı toplam önizlemesidir; kayıtlı tutar sunucudan gelir.
 */
export function kalemTutari(miktar: number, birimFiyat: number, kdvOrani: number) {
  const yuvarla = (x: number) => Math.round((x + Number.EPSILON) * 100) / 100;
  const satir = yuvarla(miktar * birimFiyat);
  return { satir, kdv: yuvarla((satir * kdvOrani) / 100) };
}

export function faturaToplami(
  kalemler: { miktar?: number; birim_fiyat?: number; kdv_orani?: number }[],
) {
  let ara = 0;
  let kdv = 0;
  for (const k of kalemler) {
    if (!k?.miktar || k.birim_fiyat == null) continue;
    const t = kalemTutari(k.miktar, k.birim_fiyat, k.kdv_orani ?? 20);
    ara += t.satir;
    kdv += t.kdv;
  }
  const iki = (x: number) => Math.round(x * 100) / 100;
  return { ara: iki(ara), kdv: iki(kdv), genel: iki(ara + kdv) };
}
