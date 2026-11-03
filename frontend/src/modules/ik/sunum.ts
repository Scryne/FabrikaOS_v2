/** İK kayıtlarının ekranda okunur gösterimi (saf yardımcılar). */

/**
 * İzin kaydındaki personelin okunur adı. Ad backend'den gelir (``personel_ad``, yalnız ad/soyad;
 * KVKK alanı taşımaz). Personel kaydı yoksa (silinmiş) son çare olarak kayıt numarası gösterilir.
 */
export function personelAdi(izin: { personel_id: number; personel_ad?: string | null }): string {
  return izin.personel_ad || `#${izin.personel_id}`;
}
