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
  /** Bölüm başlığı i18n anahtarı (sidebar gruplaması). */
  bolum: string;
  yol: string;
  /** Gerekli RBAC izni; yoksa öğe herkese görünür (yalnız oturum yeterli). */
  izin?: string;
  /** Bağlı olduğu entitlement modülü; kapalıysa öğe gizlenir (S16). Yoksa çekirdek. */
  modul?: string;
};

export const MENU: MenuOgesi[] = [
  { anahtar: 'pano', etiketAnahtari: 'menu.pano', bolum: 'menu.bolum_genel', yol: '/' },
  {
    anahtar: 'makineler',
    etiketAnahtari: 'menu.makineler',
    bolum: 'menu.bolum_uretim',
    yol: '/makineler',
    izin: 'uretim:oku',
    modul: 'uretim',
  },
  {
    anahtar: 'uretim-verileri',
    etiketAnahtari: 'menu.uretim_verileri',
    bolum: 'menu.bolum_uretim',
    yol: '/uretim-verileri',
    izin: 'uretim:oku',
    modul: 'uretim',
  },
  {
    anahtar: 'is-emirleri',
    etiketAnahtari: 'menu.is_emirleri',
    bolum: 'menu.bolum_uretim',
    yol: '/is-emirleri',
    izin: 'isemri:oku',
    modul: 'isemri',
  },
  {
    anahtar: 'ikiz',
    etiketAnahtari: 'menu.ikiz',
    bolum: 'menu.bolum_uretim',
    yol: '/ikiz',
    izin: 'uretim:oku',
    modul: 'uretim',
  },
  {
    anahtar: 'saha-cihazlar',
    etiketAnahtari: 'menu.saha',
    bolum: 'menu.bolum_uretim',
    yol: '/saha/cihazlar',
    izin: 'saha:oku',
    modul: 'saha',
  },
  {
    anahtar: 'bakim',
    etiketAnahtari: 'menu.bakim',
    bolum: 'menu.bolum_uretim',
    yol: '/bakim-planlari',
    izin: 'bakim:oku',
    modul: 'bakim',
  },
  {
    anahtar: 'malzemeler',
    etiketAnahtari: 'menu.malzemeler',
    bolum: 'menu.bolum_stok',
    yol: '/malzemeler',
    izin: 'stok:oku',
    modul: 'stok',
  },
  {
    anahtar: 'kritik-stok',
    etiketAnahtari: 'menu.kritik_stok',
    bolum: 'menu.bolum_stok',
    yol: '/stok/kritik',
    izin: 'stok:oku',
    modul: 'stok',
  },
  {
    anahtar: 'satinalma',
    etiketAnahtari: 'menu.satinalma',
    bolum: 'menu.bolum_stok',
    yol: '/satinalma-talepleri',
    izin: 'satinalma:oku',
    modul: 'stok',
  },
  {
    anahtar: 'kalite',
    etiketAnahtari: 'menu.kalite',
    bolum: 'menu.bolum_kalite',
    yol: '/kalite-kontrolleri',
    izin: 'kalite:oku',
    modul: 'kalite',
  },
  {
    anahtar: 'uygunsuzluklar',
    etiketAnahtari: 'menu.uygunsuzluklar',
    bolum: 'menu.bolum_kalite',
    yol: '/uygunsuzluklar',
    izin: 'kalite:oku',
    modul: 'kalite',
  },
  {
    anahtar: 'enerji',
    etiketAnahtari: 'menu.enerji',
    bolum: 'menu.bolum_kalite',
    yol: '/enerji-tuketimleri',
    izin: 'enerji:oku',
    modul: 'enerji',
  },
  {
    anahtar: 'is-kazalari',
    etiketAnahtari: 'menu.is_kazalari',
    bolum: 'menu.bolum_isg_ik',
    yol: '/is-kazalari',
    izin: 'isg:oku',
    modul: 'isg',
  },
  {
    anahtar: 'risk-degerlendirme',
    etiketAnahtari: 'menu.risk_degerlendirme',
    bolum: 'menu.bolum_isg_ik',
    yol: '/risk-degerlendirmeleri',
    izin: 'isg:oku',
    modul: 'isg',
  },
  {
    anahtar: 'personeller',
    etiketAnahtari: 'menu.personeller',
    bolum: 'menu.bolum_isg_ik',
    yol: '/personeller',
    izin: 'ik:oku',
    modul: 'ik',
  },
  {
    anahtar: 'izin-talepleri',
    etiketAnahtari: 'menu.izin_talepleri',
    bolum: 'menu.bolum_isg_ik',
    yol: '/izin-talepleri',
    izin: 'ik:oku',
    modul: 'ik',
  },
  {
    anahtar: 'ticari-pano',
    etiketAnahtari: 'menu.ticari_pano',
    bolum: 'menu.bolum_ticari',
    yol: '/ticari',
    izin: 'crm:oku',
    modul: 'crm',
  },
  {
    anahtar: 'firmalar',
    etiketAnahtari: 'menu.firmalar',
    bolum: 'menu.bolum_ticari',
    yol: '/firmalar',
    izin: 'crm:oku',
    modul: 'crm',
  },
  {
    anahtar: 'sozlesmeler',
    etiketAnahtari: 'menu.sozlesmeler',
    bolum: 'menu.bolum_ticari',
    yol: '/sozlesmeler',
    izin: 'sozlesme:oku',
    modul: 'sozlesme',
  },
  {
    anahtar: 'talepler',
    etiketAnahtari: 'menu.talepler',
    bolum: 'menu.bolum_ticari',
    yol: '/talepler',
    izin: 'talep:oku',
    modul: 'talep',
  },
  {
    anahtar: 'belgeler',
    etiketAnahtari: 'menu.belgeler',
    bolum: 'menu.bolum_dokuman',
    yol: '/belgeler',
    izin: 'dys:oku',
    modul: 'dys',
  },
  {
    anahtar: 'duyurular',
    etiketAnahtari: 'menu.duyurular',
    bolum: 'menu.bolum_dokuman',
    yol: '/duyurular',
    izin: 'duyuru:oku',
    modul: 'duyuru',
  },
  {
    anahtar: 'tahminler',
    etiketAnahtari: 'menu.tahminler',
    bolum: 'menu.bolum_zeka',
    yol: '/tahminler',
    izin: 'ai:oku',
    modul: 'ai',
  },
  {
    anahtar: 'analitik',
    etiketAnahtari: 'menu.analitik',
    bolum: 'menu.bolum_zeka',
    yol: '/analitik',
    izin: 'analitik:oku',
    modul: 'analitik',
  },
  {
    anahtar: 'raporlar',
    etiketAnahtari: 'menu.raporlar',
    bolum: 'menu.bolum_zeka',
    yol: '/raporlar',
    izin: 'rapor:oku',
    modul: 'rapor',
  },
  {
    anahtar: 'kullanicilar',
    etiketAnahtari: 'menu.kullanicilar',
    bolum: 'menu.bolum_yonetim',
    yol: '/kullanicilar',
    izin: 'kullanici:oku',
  },
];

/**
 * İzin gerektiren öğelerden yalnız kullanıcının yetkili olduklarını, entitlement
 * modülü kapalı olanları da eleyerek döndürür. `modulAcik` verilmezse modül süzgeci
 * uygulanmaz (fail-open — güvenlik backend'de; S16/ADR-0018).
 */
export function gorunurMenu(
  ogeler: MenuOgesi[],
  izinVar: (izin: string) => boolean,
  modulAcik: (modul: string) => boolean = () => true,
): MenuOgesi[] {
  return ogeler.filter(
    (o) =>
      (o.izin === undefined || izinVar(o.izin)) && (o.modul === undefined || modulAcik(o.modul)),
  );
}
