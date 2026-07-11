/**
 * Üretim bölümü domain panelleri (persona panosu) — Üretim & OEE, Saha cihazları, Bakım, Enerji.
 * Her biri kendi ``/ozet`` hook'undan beslenir (React Query cache modül ekranıyla paylaşılır).
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { EGrafik } from '@/components/grafik/EGrafik';
import { cubukSecenek, gostergeSecenek } from '@/components/grafik/grafikSecenek';
import { DurumPim } from '@/components/DurumPim';
import { UyariKarti } from '@/components/UyariKarti';
import { useBakimOzet } from '@/modules/bakim/hooks';
import { useEnerjiOzet } from '@/modules/enerji/hooks';
import { useSahaOzet } from '@/modules/saha/hooks';
import { useOeeOzet, useUretimOzet } from '@/modules/uretim/hooks';
import { RENKLER } from '@/tema/tema';

import { AltBaslik, IstatSira, WidgetKabuk } from './ortak';

const DURUM_RENK: Record<string, string> = {
  calisiyor: RENKLER.basari,
  durdu: RENKLER.metinSoluk,
  bakimda: RENKLER.uyari,
  ariza: RENKLER.hata,
};

/** Tam genişlik akışkan oran barı (widget içi; MiniBar'ın full-width kardeşi). */
function OranBar({ oran, renk }: { oran: number; renk: string }) {
  return (
    <div className="mini-bar" style={{ width: '100%' }} aria-hidden="true">
      <div
        className="mini-bar-dolu"
        style={{ background: renk, transform: `scaleX(${Math.max(0, Math.min(1, oran / 100))})` }}
      />
    </div>
  );
}

export function UretimPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useUretimOzet();
  const oeeOzet = useOeeOzet();
  const oee = Math.round((data?.ortalama_oee ?? 0) * 100);
  const gauge = useMemo(() => gostergeSecenek(oee), [oee]);
  const makineBar = useMemo(
    () =>
      cubukSecenek(
        (oeeOzet.data ?? [])
          .slice(0, 8)
          .map((s) => ({ ad: s.makine_kod, oee: Math.round(s.oee * 100) })),
      ),
    [oeeOzet.data],
  );
  const makineVar = (oeeOzet.data?.length ?? 0) > 0;

  return (
    <WidgetKabuk
      bolum="menu.bolum_uretim"
      ikonAnahtar="makineler"
      baslikAnahtari="pano.widget_uretim"
      yol="/makineler"
      yukleniyor={isPending}
      bos={data ? data.toplam_makine === 0 : false}
      bosMetin={t('pano.uretim_bos')}
      genis
    >
      {data && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
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
                {t('pano.filo_oee')}
              </p>
            </div>
            <div className="widget-yan">
              <IstatSira
                ogeler={[
                  { anahtar: 'makine', deger: data.toplam_makine, etiket: t('pano.st_makine') },
                  {
                    anahtar: 'calisan',
                    deger: data.calisan,
                    etiket: t('pano.st_calisan'),
                    ton: 'var(--basari)',
                  },
                  { anahtar: 'izlenen', deger: data.uretimli_makine, etiket: t('pano.st_izlenen') },
                ]}
              />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '9px 18px' }}>
                {data.durum_dagilimi
                  .filter((d) => d.adet > 0)
                  .map((d) => (
                    <span
                      key={d.durum}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 7,
                        fontSize: 12.5,
                      }}
                    >
                      <DurumPim
                        renk={DURUM_RENK[d.durum] ?? 'var(--metin-soluk)'}
                        etiket={t(`uretim.durum_${d.durum}`)}
                      />
                      <span className="sayisal" style={{ color: 'var(--metin)', fontWeight: 600 }}>
                        {d.adet}
                      </span>
                    </span>
                  ))}
              </div>
            </div>
          </div>
          {makineVar && (
            <div>
              <AltBaslik>{t('pano.makine_oee')}</AltBaslik>
              <EGrafik secenek={makineBar} yukseklik={148} />
            </div>
          )}
        </div>
      )}
    </WidgetKabuk>
  );
}

export function SahaPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useSahaOzet();
  const oran =
    data && data.toplam_cihaz > 0 ? Math.round((data.cevrimici / data.toplam_cihaz) * 100) : 0;

  return (
    <WidgetKabuk
      bolum="menu.bolum_uretim"
      ikonAnahtar="saha-cihazlar"
      baslikAnahtari="pano.widget_saha"
      yol="/saha/cihazlar"
      yukleniyor={isPending}
      bos={data ? data.toplam_cihaz === 0 : false}
      bosMetin={t('pano.saha_bos')}
    >
      {data && (
        <>
          <IstatSira
            ogeler={[
              {
                anahtar: 'online',
                deger: `${data.cevrimici}/${data.toplam_cihaz}`,
                etiket: t('pano.st_cevrimici'),
                ton: 'var(--cyan)',
              },
              {
                anahtar: 'olcum',
                deger: data.bugun_olcum.toLocaleString('tr-TR'),
                etiket: t('pano.st_bugun_olcum'),
              },
            ]}
          />
          <div style={{ marginTop: 16 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 12,
                color: 'var(--metin-soluk)',
                marginBottom: 6,
              }}
            >
              <span>{t('pano.cevrimici_orani')}</span>
              <span className="sayisal" style={{ color: 'var(--metin)' }}>
                %{oran}
              </span>
            </div>
            <OranBar oran={oran} renk="var(--cyan)" />
          </div>
        </>
      )}
    </WidgetKabuk>
  );
}

export function BakimPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useBakimOzet();

  return (
    <WidgetKabuk
      bolum="menu.bolum_uretim"
      ikonAnahtar="bakim"
      baslikAnahtari="pano.widget_bakim"
      yol="/bakim-planlari"
      yukleniyor={isPending}
      bos={data ? data.toplam_plan === 0 : false}
      bosMetin={t('pano.bakim_bos')}
    >
      {data && (
        <>
          <IstatSira
            ogeler={[
              { anahtar: 'aktif', deger: data.aktif_plan, etiket: t('pano.st_aktif_plan') },
              {
                anahtar: 'hafta',
                deger: data.bu_hafta_vadesi,
                etiket: t('pano.st_hafta_vadesi'),
                ton: data.bu_hafta_vadesi > 0 ? 'var(--uyari)' : undefined,
              },
              {
                anahtar: 'gecikmis',
                deger: data.gecikmis,
                etiket: t('pano.st_gecikmis'),
                ton: data.gecikmis > 0 ? 'var(--hata)' : undefined,
              },
            ]}
          />
          {data.gecikmis > 0 && (
            <div style={{ marginTop: 14 }}>
              <UyariKarti
                onem="kritik"
                baslik={t('pano.bakim_gecikmis_baslik', { adet: data.gecikmis })}
                aciklama={t('pano.bakim_gecikmis_alt')}
              />
            </div>
          )}
        </>
      )}
    </WidgetKabuk>
  );
}

export function EnerjiPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useEnerjiOzet();

  return (
    <WidgetKabuk
      bolum="menu.bolum_kalite"
      ikonAnahtar="enerji"
      baslikAnahtari="pano.widget_enerji"
      yol="/enerji-tuketimleri"
      yukleniyor={isPending}
      bos={data ? data.toplam_kayit === 0 : false}
      bosMetin={t('pano.enerji_bos')}
    >
      {data && (
        <IstatSira
          ogeler={[
            {
              anahtar: 'bugun',
              deger: data.bugun_kayit.toLocaleString('tr-TR'),
              etiket: t('pano.st_bugun_kayit'),
            },
            {
              anahtar: 'izlenen',
              deger: data.izlenen_makine,
              etiket: t('pano.st_izlenen_makine'),
              ton: 'var(--hat-kalite)',
            },
            { anahtar: 'tur', deger: data.tur_sayisi, etiket: t('pano.st_tur') },
          ]}
        />
      )}
    </WidgetKabuk>
  );
}
