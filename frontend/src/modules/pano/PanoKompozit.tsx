/**
 * Persona panosu kompozit düzeni (saf sunum) — persona hero başlığı (selam + persona etiketi +
 * canlı durum/modül sayısı) + görünür domain panellerinin bento ızgarası. Panellerin her biri
 * kendi verisini çeker; kompozit yalnız düzeni ve persona kimliğini (hat rengi) kurar.
 */

import type { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { AppstoreOutlined } from '@ant-design/icons';

import { BosDurum } from '@/components/BosDurum';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useGercekZaman } from '@/modules/ortak/gercekZamanBaglam';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import type { PanoWidget } from './personalar';

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
  const hatRenk =
    widgetlar.length > 0 ? (BOLUM_RENGI[widgetlar[0]!.bolum] ?? 'var(--mavi)') : 'var(--mavi)';

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
        <div className="pano-bento">
          {widgetlar.map((w) => (
            <w.Panel key={w.anahtar} />
          ))}
        </div>
      )}
    </SayfaKapsayici>
  );
}
