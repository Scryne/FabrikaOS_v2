/**
 * Kenar çubuğu menü tanımı + RBAC görünürlük filtresi.
 *
 * Her öğe bir ``izin`` ilan edebilir; kullanıcıda o izin yoksa öğe **render edilmez**
 * (gizlenir). ``gorunurMenu`` saf fonksiyondur ve birim testlidir.
 */

export type MenuOgesi = {
  anahtar: string;
  /** i18n çeviri anahtarı (ör. 'menu.makineler'). */
  etiketAnahtari: string;
  yol: string;
  /** Gerekli RBAC izni; yoksa öğe herkese görünür (yalnız oturum yeterli). */
  izin?: string;
};

export const MENU: MenuOgesi[] = [
  { anahtar: 'pano', etiketAnahtari: 'menu.pano', yol: '/' },
  { anahtar: 'makineler', etiketAnahtari: 'menu.makineler', yol: '/makineler', izin: 'uretim:oku' },
  {
    anahtar: 'is-emirleri',
    etiketAnahtari: 'menu.is_emirleri',
    yol: '/is-emirleri',
    izin: 'isemri:oku',
  },
  { anahtar: 'bakim', etiketAnahtari: 'menu.bakim', yol: '/bakim-planlari', izin: 'bakim:oku' },
  {
    anahtar: 'kullanicilar',
    etiketAnahtari: 'menu.kullanicilar',
    yol: '/kullanicilar',
    izin: 'kullanici:oku',
  },
];

/** İzin gerektiren öğelerden yalnız kullanıcının yetkili olduklarını döndürür. */
export function gorunurMenu(ogeler: MenuOgesi[], izinVar: (izin: string) => boolean): MenuOgesi[] {
  return ogeler.filter((o) => o.izin === undefined || izinVar(o.izin));
}
