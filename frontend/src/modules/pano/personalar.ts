/**
 * Persona panosu kayıt defteri — hangi domain panelinin (widget) kime görüneceğini belirler.
 *
 * Her widget bir ``izin`` + opsiyonel entitlement ``modul`` ilan eder; kullanıcıda izin yoksa
 * veya modül kapalıysa panel görünmez (menü süzgeciyle birebir kural; S16). Böylece depo
 * kullanıcısı yalnız stok/satınalma panellerini, kalite sorumlusu yalnız kalite panelini,
 * yönetici ise tüm bento'yu görür — "her modül için farklı pano". Sıra = persona önceliği:
 * baskın domain önce gelir (dar personada doğru "hero" paneli). Saf modül — birim testli.
 */

import type { ComponentType } from 'react';

import { IkPaneli, IsgPaneli, KalitePaneli } from './widgets/kaliteIsgWidgetlari';
import { SatinalmaPaneli, StokPaneli } from './widgets/stokWidgetlari';
import { DokumanPaneli, TicariPaneli, ZekaPaneli } from './widgets/ticariZekaWidgetlari';
import { BakimPaneli, EnerjiPaneli, SahaPaneli, UretimPaneli } from './widgets/uretimWidgetlari';

export type PanoWidget = {
  /** Benzersiz anahtar (React key + test). */
  anahtar: string;
  /** Gerekli RBAC izni (ozet ucunun beklediği izinle birebir → 403 riski yok). */
  izin: string;
  /** Bağlı entitlement modülü; kapalıysa panel gizlenir. Yoksa çekirdek. */
  modul?: string;
  /** Hat rengi/persona kaynağı bölümü. */
  bolum: string;
  /** Panel bileşeni. */
  Panel: ComponentType;
};

export const PANO_WIDGETLARI: PanoWidget[] = [
  {
    anahtar: 'uretim',
    izin: 'uretim:oku',
    modul: 'uretim',
    bolum: 'menu.bolum_uretim',
    Panel: UretimPaneli,
  },
  { anahtar: 'stok', izin: 'stok:oku', modul: 'stok', bolum: 'menu.bolum_stok', Panel: StokPaneli },
  {
    anahtar: 'satinalma',
    izin: 'satinalma:oku',
    modul: 'stok',
    bolum: 'menu.bolum_stok',
    Panel: SatinalmaPaneli,
  },
  {
    anahtar: 'kalite',
    izin: 'kalite:oku',
    modul: 'kalite',
    bolum: 'menu.bolum_kalite',
    Panel: KalitePaneli,
  },
  { anahtar: 'isg', izin: 'isg:oku', modul: 'isg', bolum: 'menu.bolum_isg_ik', Panel: IsgPaneli },
  { anahtar: 'ik', izin: 'ik:oku', modul: 'ik', bolum: 'menu.bolum_isg_ik', Panel: IkPaneli },
  {
    anahtar: 'bakim',
    izin: 'bakim:oku',
    modul: 'bakim',
    bolum: 'menu.bolum_uretim',
    Panel: BakimPaneli,
  },
  {
    anahtar: 'ticari',
    izin: 'crm:oku',
    modul: 'crm',
    bolum: 'menu.bolum_ticari',
    Panel: TicariPaneli,
  },
  {
    anahtar: 'enerji',
    izin: 'enerji:oku',
    modul: 'enerji',
    bolum: 'menu.bolum_kalite',
    Panel: EnerjiPaneli,
  },
  {
    anahtar: 'saha',
    izin: 'saha:oku',
    modul: 'saha',
    bolum: 'menu.bolum_uretim',
    Panel: SahaPaneli,
  },
  {
    anahtar: 'dokuman',
    izin: 'dys:oku',
    modul: 'dys',
    bolum: 'menu.bolum_dokuman',
    Panel: DokumanPaneli,
  },
  {
    anahtar: 'zeka',
    izin: 'analitik:oku',
    modul: 'analitik',
    bolum: 'menu.bolum_zeka',
    Panel: ZekaPaneli,
  },
];

/**
 * Kullanıcının izin + entitlement'ına göre görünür panelleri (sırayı koruyarak) döndürür.
 * ``modulAcik`` verilmezse modül süzgeci uygulanmaz (fail-open; güvenlik backend'de).
 */
export function gorunurWidgetlar(
  izinVar: (izin: string) => boolean,
  modulAcik: (modul: string) => boolean = () => true,
): PanoWidget[] {
  return PANO_WIDGETLARI.filter(
    (w) => izinVar(w.izin) && (w.modul === undefined || modulAcik(w.modul)),
  );
}

const BOLUM_PERSONA: Record<string, string> = {
  'menu.bolum_uretim': 'pano.persona_uretim',
  'menu.bolum_stok': 'pano.persona_depo',
  'menu.bolum_kalite': 'pano.persona_kalite',
  'menu.bolum_isg_ik': 'pano.persona_isg_ik',
  'menu.bolum_ticari': 'pano.persona_ticari',
  'menu.bolum_dokuman': 'pano.persona_dokuman',
  'menu.bolum_zeka': 'pano.persona_zeka',
};

/**
 * Görünür panellerden persona etiketi (i18n anahtarı) çıkarır: tek bölüm → o domain'in personası
 * (ör. yalnız stok → Depo Kontrol Paneli); 4+ bölüm → Yönetim Panosu; arası → genel çalışma alanı.
 */
export function personaAnahtari(widgetlar: PanoWidget[]): string {
  const bolumler = new Set(widgetlar.map((w) => w.bolum));
  if (bolumler.size === 0) return 'pano.persona_genel';
  if (bolumler.size >= 4) return 'pano.persona_yonetim';
  if (bolumler.size === 1) return BOLUM_PERSONA[[...bolumler][0]!] ?? 'pano.persona_genel';
  return 'pano.persona_genel';
}
