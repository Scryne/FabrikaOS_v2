/**
 * Kiosk — saha büyük ekranı için kabuksuz, salt-okunur üretim panosu.
 *
 * `/ikiz/durum` tek veri kaynağıdır (ADR-0017): dev KPI kartları + makine karoları.
 * Canlılık: WS olayları `['ikiz']` sorgusunu geçersizleştirir; 30 sn yoklama ağ
 * kopmalarını toparlar. İstek hatasında son bilinen veri ekranda kalır, yalnız
 * bağlantı rozeti "Bağlanıyor…"a düşer. Ekranda hiçbir yazma aksiyonu yoktur;
 * salt-okunurluk ayrıca API seviyesinde `kiosk` rolüyle garantidir.
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { LogoIsareti } from '@/components/Marka';
import { useGercekZaman } from '@/modules/ortak/gercekZamanBaglam';

import { useIkizDurum } from '@/modules/ikiz/hooks';
import { durumRengi, kioskKarolari, oeeEtiket, type KioskKaro } from '@/modules/ikiz/sunum';

const YOKLAMA_MS = 30_000;

function KpiKaro({ baslik, deger, alt }: { baslik: string; deger: string; alt?: string }) {
  return (
    <div
      style={{
        background: 'var(--yuzey)',
        border: '1px solid var(--kenarlik)',
        borderRadius: 12,
        padding: '18px 22px',
        minWidth: 0,
      }}
    >
      <div style={{ color: 'var(--metin-soluk)', fontSize: 14, fontWeight: 500 }}>{baslik}</div>
      <div className="sayisal" style={{ fontSize: 44, fontWeight: 700, lineHeight: 1.15 }}>
        {deger}
      </div>
      {alt && <div style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>{alt}</div>}
    </div>
  );
}

function MakineKaro({ karo }: { karo: KioskKaro }) {
  const { t } = useTranslation();
  const renk = durumRengi(karo.durum);
  const oran = karo.oee == null ? 0 : Math.min(1, Math.max(0, karo.oee));
  return (
    <div
      style={{
        background: 'var(--yuzey)',
        border: '1px solid var(--kenarlik)',
        borderTop: `3px solid ${renk}`,
        borderRadius: 10,
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        minWidth: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="sayisal" style={{ fontSize: 19, fontWeight: 700 }}>
          {karo.kod}
        </span>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 12.5,
            color: 'var(--metin-soluk)',
          }}
        >
          <span
            aria-hidden="true"
            style={{
              width: 9,
              height: 9,
              borderRadius: '50%',
              background: renk,
              display: 'inline-block',
            }}
          />
          {t(`uretim.durum_${karo.durum}`, { defaultValue: karo.durum })}
        </span>
      </div>
      <div
        style={{
          color: 'var(--metin-soluk)',
          fontSize: 13,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {karo.ad}
      </div>
      <div
        aria-hidden="true"
        style={{ height: 6, borderRadius: 3, background: 'var(--kenarlik)', overflow: 'hidden' }}
      >
        <div style={{ width: `${oran * 100}%`, height: '100%', background: renk }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
        <span style={{ color: 'var(--metin-soluk)' }}>
          OEE <span className="sayisal">{oeeEtiket(karo.oee)}</span>
        </span>
        <span style={{ color: 'var(--metin-soluk)' }}>
          <span className="sayisal">{karo.toplam_adet.toLocaleString('tr-TR')}</span>{' '}
          {t('uretim.toplam_adet').toLocaleLowerCase('tr-TR')}
        </span>
      </div>
    </div>
  );
}

export function KioskSayfasi() {
  const { t } = useTranslation();
  const { bagli } = useGercekZaman();
  const { data, isError, dataUpdatedAt } = useIkizDurum(24, YOKLAMA_MS);

  const [simdi, setSimdi] = useState(() => new Date());
  useEffect(() => {
    const sayac = window.setInterval(() => setSimdi(new Date()), 1000);
    return () => window.clearInterval(sayac);
  }, []);

  const ozet = data?.ozet;
  const karolar = data ? kioskKarolari(data) : [];
  const canli = bagli && !isError;

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--zemin)',
        padding: '28px 36px 36px',
        display: 'flex',
        flexDirection: 'column',
        gap: 22,
      }}
    >
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <Link to="/" aria-label={t('ortak.uygulama_adi')} style={{ display: 'inline-flex' }}>
            <LogoIsareti boyut={36} />
          </Link>
          <div>
            <div style={{ fontSize: 21, fontWeight: 700, lineHeight: 1.2 }}>
              {t('kiosk.baslik')}
            </div>
            <div style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>
              {t('ortak.uygulama_adi')}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <span className="canli-rozet">
            {canli && <span className="canli-nokta" aria-hidden="true" />}
            {canli ? t('ortak.canli') : t('ortak.baglaniyor')}
          </span>
          <div style={{ textAlign: 'right' }}>
            <div className="sayisal" style={{ fontSize: 40, fontWeight: 700, lineHeight: 1.1 }}>
              {simdi.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
            </div>
            <div style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>
              {simdi.toLocaleDateString('tr-TR', {
                day: 'numeric',
                month: 'long',
                weekday: 'long',
              })}
            </div>
          </div>
        </div>
      </header>

      <section
        aria-label={t('kiosk.baslik')}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: 14,
        }}
      >
        <KpiKaro
          baslik={t('kiosk.uretim')}
          deger={(ozet?.toplam_adet ?? 0).toLocaleString('tr-TR')}
          alt={t('kiosk.saglam', { n: (ozet?.saglam_adet ?? 0).toLocaleString('tr-TR') })}
        />
        <KpiKaro baslik={t('kiosk.oee')} deger={ozet ? oeeEtiket(ozet.oee) : '—'} />
        <KpiKaro
          baslik={t('kiosk.calisan')}
          deger={`${ozet?.durumlar['calisiyor'] ?? 0}/${ozet?.toplam_makine ?? 0}`}
        />
        <KpiKaro baslik={t('kiosk.acik_ariza')} deger={String(ozet?.acik_ariza ?? '—')} />
        <KpiKaro baslik={t('kiosk.fire')} deger={ozet ? oeeEtiket(ozet.fire_orani) : '—'} />
      </section>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))',
          gap: 14,
          flex: 1,
          alignContent: 'start',
        }}
      >
        {karolar.length === 0 ? (
          <div style={{ color: 'var(--metin-soluk)', fontSize: 15 }}>
            {data ? t('kiosk.makine_yok') : t('ortak.yukleniyor')}
          </div>
        ) : (
          karolar.map((karo) => <MakineKaro key={karo.makine_id} karo={karo} />)
        )}
      </section>

      <footer style={{ color: 'var(--metin-soluk)', fontSize: 12.5 }}>
        {t('kiosk.son_guncelleme')}:{' '}
        <span className="sayisal">
          {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString('tr-TR') : '—'}
        </span>
      </footer>
    </div>
  );
}
