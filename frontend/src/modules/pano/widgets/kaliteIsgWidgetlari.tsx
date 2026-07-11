/**
 * Kalite & İSG-İK bölümü domain panelleri (persona panosu) — Kalite (geçme oranı göstergesi),
 * İSG (kazasız gün + 5×5 risk matrisi), İK (personel/izin/sertifika). Kalite/İSG persona'ları
 * fabrikanın tümünü değil, kendi domain'lerinin sinyallerini görür.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { EGrafik } from '@/components/grafik/EGrafik';
import { gostergeSecenek } from '@/components/grafik/grafikSecenek';
import { RiskMatrisi } from '@/components/RiskMatrisi';
import { useIkOzet } from '@/modules/ik/hooks';
import { useIsgOzet } from '@/modules/isg/hooks';
import { useKaliteOzet } from '@/modules/kalite/hooks';
import { riskSeviyesi, riskSkoru } from '@/modules/isg/riskMatris';
import { RENKLER } from '@/tema/tema';

import { AltBaslik, IstatSira, SegmentBar, WidgetKabuk } from './ortak';

const SEVIYE_RENK: Record<string, string> = {
  dusuk: RENKLER.basari,
  orta: RENKLER.cyan,
  yuksek: RENKLER.uyari,
  cok_yuksek: RENKLER.hata,
};

export function KalitePaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useKaliteOzet();
  const oran = Math.round((data?.gecti_orani ?? 0) * 100);
  const gauge = useMemo(() => gostergeSecenek(oran), [oran]);

  return (
    <WidgetKabuk
      bolum="menu.bolum_kalite"
      ikonAnahtar="kalite"
      baslikAnahtari="pano.widget_kalite"
      yol="/kalite-kontrolleri"
      yukleniyor={isPending}
      bos={data ? data.toplam_kontrol === 0 && data.toplam_uygunsuzluk === 0 : false}
      bosMetin={t('pano.kalite_bos')}
      genis
    >
      {data && (
        <div className="widget-split">
          <div className="widget-gorsel">
            <EGrafik secenek={gauge} yukseklik={150} />
            <p
              style={{
                textAlign: 'center',
                margin: '2px 0 0',
                fontSize: 12,
                color: 'var(--metin-soluk)',
              }}
            >
              {t('pano.gecme_orani')}
            </p>
          </div>
          <div className="widget-yan">
            <IstatSira
              ogeler={[
                {
                  anahtar: 'acik',
                  deger: data.acik_uygunsuzluk,
                  etiket: t('pano.st_acik_uygunsuzluk'),
                  ton: data.acik_uygunsuzluk > 0 ? 'var(--hata)' : undefined,
                },
                {
                  anahtar: 'dogrulama',
                  deger: data.dogrulamada,
                  etiket: t('pano.st_dogrulamada'),
                  ton: data.dogrulamada > 0 ? 'var(--uyari)' : undefined,
                },
                {
                  anahtar: 'kapanan',
                  deger: data.bu_ay_kapanan,
                  etiket: t('pano.st_bu_ay_kapanan'),
                  ton: 'var(--basari)',
                },
              ]}
            />
            {data.toplam_uygunsuzluk > 0 && (
              <div>
                <AltBaslik>{t('pano.uygunsuzluk_durumu')}</AltBaslik>
                <SegmentBar
                  segmentler={[
                    {
                      anahtar: 'acik',
                      ad: t('pano.uyg_acik'),
                      deger: data.acik_uygunsuzluk,
                      renk: 'var(--hata)',
                    },
                    {
                      anahtar: 'dogrulama',
                      ad: t('pano.uyg_dogrulama'),
                      deger: data.dogrulamada,
                      renk: 'var(--uyari)',
                    },
                    {
                      anahtar: 'kapali',
                      ad: t('pano.uyg_kapali'),
                      deger: data.kapali_uygunsuzluk,
                      renk: 'var(--basari)',
                    },
                  ]}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </WidgetKabuk>
  );
}

export function IsgPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useIsgOzet();

  const sayacMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const h of data?.risk_matrisi ?? []) m.set(`${h.olasilik}-${h.siddet}`, h.adet);
    return m;
  }, [data]);

  return (
    <WidgetKabuk
      bolum="menu.bolum_isg_ik"
      ikonAnahtar="is-kazalari"
      baslikAnahtari="pano.widget_isg"
      yol="/risk-degerlendirmeleri"
      yukleniyor={isPending}
      bos={false}
      genis
    >
      {data && (
        <div style={{ display: 'flex', gap: 22, flexWrap: 'wrap' }}>
          <div
            style={{
              flex: '1 1 180px',
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              justifyContent: 'center',
            }}
          >
            <div>
              <div
                className="sayisal"
                style={{
                  fontSize: 40,
                  fontWeight: 700,
                  lineHeight: 1,
                  letterSpacing: '-0.02em',
                  color: 'var(--basari)',
                }}
              >
                {data.gunluk_kazasiz}
              </div>
              <div style={{ fontSize: 12.5, color: 'var(--metin-soluk)', marginTop: 4 }}>
                {t('pano.gun_kazasiz')}
              </div>
            </div>
            <IstatSira
              ogeler={[
                { anahtar: 'acik_risk', deger: data.acik_risk, etiket: t('pano.st_acik_risk') },
                {
                  anahtar: 'yuksek',
                  deger: data.yuksek_risk,
                  etiket: t('pano.st_yuksek_risk'),
                  ton: data.yuksek_risk > 0 ? 'var(--hata)' : undefined,
                },
                {
                  anahtar: 'ramak',
                  deger: data.ramak_kala,
                  etiket: t('pano.st_ramak_kala'),
                },
              ]}
            />
          </div>
          <div style={{ flex: '0 0 auto', width: 216, maxWidth: '100%' }}>
            <RiskMatrisi
              sayac={(o, s) => sayacMap.get(`${o}-${s}`) ?? 0}
              renk={(o, s) => SEVIYE_RENK[riskSeviyesi(riskSkoru(o, s))] ?? RENKLER.metinSoluk}
            />
          </div>
        </div>
      )}
    </WidgetKabuk>
  );
}

export function IkPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useIkOzet();

  return (
    <WidgetKabuk
      bolum="menu.bolum_isg_ik"
      ikonAnahtar="personeller"
      baslikAnahtari="pano.widget_ik"
      yol="/personeller"
      yukleniyor={isPending}
      bos={data ? data.toplam_personel === 0 : false}
      bosMetin={t('pano.ik_bos')}
    >
      {data && (
        <IstatSira
          ogeler={[
            { anahtar: 'aktif', deger: data.aktif_personel, etiket: t('pano.st_aktif_personel') },
            {
              anahtar: 'izinli',
              deger: data.bugun_izinli,
              etiket: t('pano.st_bugun_izinli'),
              ton: data.bugun_izinli > 0 ? 'var(--cyan)' : undefined,
            },
            {
              anahtar: 'sertifika',
              deger: data.yaklasan_sertifika,
              etiket: t('pano.st_yaklasan_sertifika'),
              ton: data.yaklasan_sertifika > 0 ? 'var(--uyari)' : undefined,
            },
            { anahtar: 'zimmet', deger: data.acik_zimmet, etiket: t('pano.st_acik_zimmet') },
          ]}
        />
      )}
    </WidgetKabuk>
  );
}
