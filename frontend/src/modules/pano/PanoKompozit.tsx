/**
 * Persona panosu kompozit düzeni (saf sunum) — persona hero başlığı (selam + persona etiketi +
 * canlı durum/modül sayısı) + görünür domain panellerinin **mozaik (masonry) düzeni**.
 *
 * Paneller farklı yüksekliktedir (grafikli olanlar uzun, istatistik olanlar kısa). Tek CSS grid'de
 * yan yana dizmek satır yüksekliğini en uzuna hizalar → kısa kartların yanında/altında boşluk kalır.
 * Bunun yerine paneller, dengeli **dikey sütunlara** paketlenir: her sütun bir flex yığınıdır, kartlar
 * üst üste sıkışır (iç boşluk yok), sütunlar ağırlıkça dengelenir (uzun paneller sütunlara serpiştirilir).
 * Sıra korunur (öncelik) — greedy: her panel o an en hafif sütuna eklenir. Panellerin verisi
 * kendi hook'undan gelir; kompozit yalnız düzeni ve persona kimliğini (hat rengi) kurar.
 */

import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { AppstoreOutlined } from '@ant-design/icons';

import { BosDurum } from '@/components/BosDurum';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useGercekZaman } from '@/modules/ortak/gercekZamanBaglam';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import type { PanoWidget } from './personalar';

/** Grafik taşıyan paneller daha uzundur → dengeleme için görece ağırlık (varsayılan 1). */
const PANEL_AGIRLIK: Record<string, number> = {
  uretim: 2.4,
  kalite: 2.0,
  isg: 1.9,
  stok: 1.6,
};

/** Görünür genişliğe göre sütun sayısı (panel sayısıyla sınırlı). */
function kolonSayisiHesapla(genislik: number, adet: number): number {
  const hedef = genislik >= 1560 ? 3 : genislik >= 900 ? 2 : 1;
  return Math.max(1, Math.min(hedef, adet));
}

/** Pencere genişliğini izler (mozaik sütun sayısı için); yeniden boyutlandırmada güncellenir. */
function usePencereGenisligi(): number {
  const [genislik, setGenislik] = useState(() =>
    typeof window === 'undefined' ? 1280 : window.innerWidth,
  );
  useEffect(() => {
    const isle = () => setGenislik(window.innerWidth);
    window.addEventListener('resize', isle);
    return () => window.removeEventListener('resize', isle);
  }, []);
  return genislik;
}

/** Panelleri ağırlıkça dengeli ``kolonSayisi`` sütuna dağıtır (sıra korunur, greedy en-hafif). */
function sutunlaraDagit(widgetlar: PanoWidget[], kolonSayisi: number): PanoWidget[][] {
  const sutunlar: PanoWidget[][] = Array.from({ length: kolonSayisi }, () => []);
  const yukler = new Array<number>(kolonSayisi).fill(0);
  for (const w of widgetlar) {
    let enHafif = 0;
    for (let i = 1; i < kolonSayisi; i++) if (yukler[i]! < yukler[enHafif]!) enHafif = i;
    sutunlar[enHafif]!.push(w);
    yukler[enHafif] = (yukler[enHafif] ?? 0) + (PANEL_AGIRLIK[w.anahtar] ?? 1);
  }
  return sutunlar;
}

export function PanoKompozit({
  kullaniciAdi,
  personaAnahtari,
  widgetlar,
}: {
  kullaniciAdi: string;
  personaAnahtari: string;
  widgetlar: PanoWidget[];
}) {
  const { t } = useTranslation();
  const { bagli } = useGercekZaman();
  const genislik = usePencereGenisligi();
  const hatRenk =
    widgetlar.length > 0 ? (BOLUM_RENGI[widgetlar[0]!.bolum] ?? 'var(--mavi)') : 'var(--mavi)';

  const sutunlar = useMemo(
    () => sutunlaraDagit(widgetlar, kolonSayisiHesapla(genislik, widgetlar.length)),
    [widgetlar, genislik],
  );

  return (
    <SayfaKapsayici>
      <div className="pano-hero">
        <div>
          <div className="pano-hero-kirinti" style={{ '--hat': hatRenk } as CSSProperties}>
            <i className="hat-nokta" aria-hidden="true" />
            {t(personaAnahtari)}
          </div>
          <h1 className="pano-hero-selam">{t('pano.hosgeldin', { ad: kullaniciAdi })}</h1>
        </div>
        <div className="pano-hero-mefta">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
            <i
              className="canli-nokta"
              aria-hidden="true"
              style={bagli ? undefined : { background: 'var(--metin-soluk)', animation: 'none' }}
            />
            {bagli ? t('pano.canli') : t('pano.cevrimdisi')}
          </span>
          {widgetlar.length > 0 && (
            <>
              <span className="ayrac" aria-hidden="true" />
              <span className="sayisal">{t('pano.modul_sayisi', { adet: widgetlar.length })}</span>
            </>
          )}
        </div>
      </div>

      {widgetlar.length === 0 ? (
        <BosDurum
          ikon={<AppstoreOutlined />}
          baslik={t('pano.bos_baslik')}
          aciklama={t('pano.bos_aciklama')}
        />
      ) : (
        <div className="pano-mozaik">
          {sutunlar.map((sutun, i) => (
            <div className="pano-mozaik-kolon" key={i}>
              {sutun.map((w) => (
                <w.Panel key={w.anahtar} />
              ))}
            </div>
          ))}
        </div>
      )}
    </SayfaKapsayici>
  );
}
