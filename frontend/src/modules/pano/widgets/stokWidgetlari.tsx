/**
 * Stok bölümü domain panelleri (persona panosu) — Stok (kritik malzeme önizlemesi) + Satınalma.
 * Depo persona'sının çekirdek panelleri: depo kullanıcısı yalnız bunları görür (tüm fabrikayı değil).
 */

import { useTranslation } from 'react-i18next';

import { MiniBar } from '@/components/MiniBar';
import { UyariKarti } from '@/components/UyariKarti';
import { useKritikStok, useSatinalmaOzet, useStokOzet } from '@/modules/stok/hooks';

import { AltBaslik, IstatSira, WidgetKabuk } from './ortak';

export function StokPaneli() {
  const { t } = useTranslation();
  const ozet = useStokOzet();
  const kritik = useKritikStok();
  const data = ozet.data;
  const kritikListe = (kritik.data ?? []).slice(0, 5);

  return (
    <WidgetKabuk
      bolum="menu.bolum_stok"
      ikonAnahtar="malzemeler"
      baslikAnahtari="pano.widget_stok"
      yol="/malzemeler"
      yukleniyor={ozet.isPending}
      bos={data ? data.toplam_malzeme === 0 : false}
      bosMetin={t('pano.stok_bos')}
      genis
    >
      {data && (
        <>
          <IstatSira
            ogeler={[
              { anahtar: 'aktif', deger: data.aktif_malzeme, etiket: t('pano.st_aktif_malzeme') },
              {
                anahtar: 'kritik',
                deger: data.kritik_alti,
                etiket: t('pano.st_kritik_alti'),
                ton: data.kritik_alti > 0 ? 'var(--hata)' : undefined,
              },
              { anahtar: 'hareket', deger: data.bugun_hareket, etiket: t('pano.st_bugun_hareket') },
            ]}
          />
          <div style={{ marginTop: 18 }}>
            <AltBaslik>{t('pano.kritik_malzemeler')}</AltBaslik>
            {kritikListe.length === 0 ? (
              <div className="widget-bos">{t('pano.kritik_yok')}</div>
            ) : (
              kritikListe.map((m) => {
                const kritikMi = m.mevcut_miktar <= m.kritik_stok;
                const enBuyuk = Math.max(m.min_stok, m.kritik_stok, m.mevcut_miktar, 1);
                return (
                  <div key={m.id} className="widget-satir">
                    <div style={{ minWidth: 0 }}>
                      <div className="widget-satir-ad">{m.ad}</div>
                      <div
                        className="sayisal"
                        style={{ fontSize: 12, color: 'var(--metin-soluk)' }}
                      >
                        {m.kod}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 11, flexShrink: 0 }}>
                      <span
                        className="sayisal"
                        style={{ fontSize: 12.5, color: 'var(--metin-soluk)' }}
                      >
                        <span style={{ color: kritikMi ? 'var(--hata)' : 'var(--metin)' }}>
                          {m.mevcut_miktar}
                        </span>{' '}
                        / {m.kritik_stok} {m.birim}
                      </span>
                      <MiniBar
                        deger={m.mevcut_miktar}
                        enBuyuk={enBuyuk}
                        renk={kritikMi ? 'var(--hata)' : 'var(--uyari)'}
                        genislik={56}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </WidgetKabuk>
  );
}

export function SatinalmaPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useSatinalmaOzet();

  return (
    <WidgetKabuk
      bolum="menu.bolum_stok"
      ikonAnahtar="satinalma"
      baslikAnahtari="pano.widget_satinalma"
      yol="/satinalma-talepleri"
      yukleniyor={isPending}
      bos={data ? data.toplam === 0 : false}
      bosMetin={t('pano.satinalma_bos')}
    >
      {data && (
        <>
          <IstatSira
            ogeler={[
              {
                anahtar: 'bekleyen',
                deger: data.onay_bekleyen,
                etiket: t('pano.st_onay_bekleyen'),
                ton: data.onay_bekleyen > 0 ? 'var(--uyari)' : undefined,
              },
              { anahtar: 'taslak', deger: data.taslak, etiket: t('pano.st_taslak') },
              {
                anahtar: 'onaylandi',
                deger: data.onaylandi,
                etiket: t('pano.st_onaylandi'),
                ton: 'var(--basari)',
              },
            ]}
          />
          {data.onay_bekleyen > 0 && (
            <div style={{ marginTop: 14 }}>
              <UyariKarti
                onem="uyari"
                baslik={t('pano.satinalma_bekleyen_baslik', { adet: data.onay_bekleyen })}
                aciklama={t('pano.satinalma_bekleyen_alt')}
              />
            </div>
          )}
        </>
      )}
    </WidgetKabuk>
  );
}
