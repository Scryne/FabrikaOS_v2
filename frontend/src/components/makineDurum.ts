/** Makine durum kodları (backend `MakineDurum` ile aynı sıra). Bileşen dosyasından ayrı: hızlı yenileme yalnız
 * bileşen dışa aktaran dosyalarda çalışır. */
export const MAKINE_DURUMLARI = ['calisiyor', 'durdu', 'bakimda', 'ariza'] as const;
export type MakineDurum = (typeof MAKINE_DURUMLARI)[number];
