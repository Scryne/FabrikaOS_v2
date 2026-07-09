/**
 * Saha cihazları çalışma alanı — KPI şeridi (kayıtlı cihaz + çevrimiçi + bugün ölçüm + protokol
 * türü; `/saha/ozet`) + zengin tablo (varlık hücre + protokol pimi + **çevrimiçi/çevrimdışı
 * pimi** son görülme <5dk) + canlı ``son_gorulme``. Salt-okunur (MES/SCADA entegrasyon görünümü).
 */

import { useTranslation } from 'react-i18next';
import { ApiOutlined, ClockCircleOutlined, WifiOutlined } from '@ant-design/icons';
import { Card } from 'antd';
import type { CSSProperties } from 'react';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { DurumPim } from '@/components/DurumPim';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type Cihaz, useCihazlar, useSahaOzet } from './hooks';

const HAT = BOLUM_RENGI['menu.bolum_uretim'];

/** Son görülme <5 dk → çevrimiçi. */
function cevrimici(sonGorulme: string | null): boolean {
  return sonGorulme != null && dayjs().diff(dayjs(sonGorulme), 'minute') < 5;
}

export function CihazListesi() {
  const { t } = useTranslation();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useCihazlar(param);
  const { data: ozet, isPending: ozetYukleniyor } = useSahaOzet();

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'cihaz',
          baslik: t('saha.kpi_cihaz'),
          deger: String(ozet.toplam_cihaz),
          ikon: <WifiOutlined />,
        },
        {
          anahtar: 'online',
          baslik: t('saha.kpi_cevrimici'),
          deger: String(ozet.cevrimici),
          ikon: <ApiOutlined />,
        },
        {
          anahtar: 'olcum',
          baslik: t('saha.kpi_olcum'),
          deger: String(ozet.bugun_olcum),
          ikon: <ClockCircleOutlined />,
        },
        {
          anahtar: 'protokol',
          baslik: t('saha.kpi_protokol'),
          deger: String(ozet.protokol_dagilimi.length),
          ikon: <ApiOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Cihaz> = [
    {
      title: t('saha.ad'),
      key: 'ad',
      sorter: true,
      render: (_v: unknown, c: Cihaz) => (
        <span className="varlik-hucre">
          <span
            className="ikon-plaka kucuk"
            aria-hidden="true"
            style={{ '--plaka-renk': HAT } as CSSProperties}
          >
            <WifiOutlined />
          </span>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {c.ad}
            </span>
            <span className="varlik-alt sayisal">{c.kod}</span>
          </span>
        </span>
      ),
    },
    {
      title: t('saha.protokol'),
      dataIndex: 'protokol',
      key: 'protokol',
      sorter: true,
      render: (p: string) => (
        <DurumPim renk={RENKLER.metinSoluk} etiket={t(`saha.protokol_${p}`, p)} solgun />
      ),
    },
    {
      title: t('saha.durum'),
      key: 'cevrimici',
      render: (_v: unknown, c: Cihaz) => {
        const online = cevrimici(c.son_gorulme ?? null);
        return (
          <DurumPim
            renk={online ? RENKLER.basari : RENKLER.metinSoluk}
            etiket={online ? t('saha.cevrimici') : t('saha.cevrimdisi')}
            solgun={!online}
          />
        );
      },
    },
    {
      title: t('saha.son_gorulme'),
      dataIndex: 'son_gorulme',
      key: 'son_gorulme',
      sorter: true,
      align: 'right',
      render: (v: string | null) =>
        v ? (
          <span className="sayisal">{dayjs(v).format('DD.MM.YYYY HH:mm')}</span>
        ) : (
          <span style={{ color: 'var(--metin-soluk)' }}>—</span>
        ),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('menu.saha')} alt={t('saha.alt')} />
      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />
      <div style={{ height: 20 }} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Cihaz>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('saha.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('saha.bos')}
        />
      </Card>
    </SayfaKapsayici>
  );
}
