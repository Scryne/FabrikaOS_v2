/**
 * Satınalma talepleri çalışma alanı — KPI şeridi + Liste / Board (onay akışı) görünüm geçişi.
 * Board kolonları = taslak → onay bekliyor → onaylandı / reddedildi (iptal gösterilmez);
 * kart tıkla → detay çekmecesi (onay/ret orada, ``satinalma:onay`` görev ayrımı). KPI /satinalma/ozet.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  FileOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Card, Empty, Skeleton, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { pimUret } from '@/components/DurumPim';
import { GorunumGecis, type Gorunum } from '@/components/GorunumGecis';
import { KanbanPano, type KanbanKolon } from '@/components/KanbanPano';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { VeriKart } from '@/components/VeriKart';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type SatinalmaTalebi, useSatinalmaOzet, useTalepler, useTalepPano } from './hooks';
import { SatinalmaTalepDetay } from './SatinalmaTalepDetay';
import { SatinalmaTalepFormu } from './SatinalmaTalepFormu';

const HAT = BOLUM_RENGI['menu.bolum_stok'];

const DURUM_RENK: Record<string, string> = {
  taslak: RENKLER.metinSoluk,
  onay_bekliyor: RENKLER.mavi,
  onaylandi: RENKLER.basari,
  reddedildi: RENKLER.hata,
  iptal: '#4b4b52',
};
const BOARD_DURUMLAR = ['taslak', 'onay_bekliyor', 'onaylandi', 'reddedildi'];
const TalepPim = pimUret(DURUM_RENK, 'satinalma.durum_');

export function SatinalmaTalepListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('satinalma:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const { data, isPending, isError } = useTalepler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useSatinalmaOzet();
  const pano = useTalepPano();

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'bekleyen',
          baslik: t('satinalma.kpi_bekleyen'),
          deger: String(ozet.onay_bekleyen),
          ikon: <ClockCircleOutlined />,
        },
        {
          anahtar: 'taslak',
          baslik: t('satinalma.kpi_taslak'),
          deger: String(ozet.taslak),
          ikon: <FileOutlined />,
        },
        {
          anahtar: 'onaylandi',
          baslik: t('satinalma.kpi_onaylandi'),
          deger: String(ozet.onaylandi),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'reddedildi',
          baslik: t('satinalma.durum_reddedildi'),
          deger: String(ozet.reddedildi),
          ikon: <CloseCircleOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<SatinalmaTalebi> = [
    {
      title: t('satinalma.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('satinalma.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    {
      title: t('satinalma.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: string) => <TalepPim durum={d} />,
    },
    {
      title: t('satinalma.olusturma'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      align: 'right',
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>,
    },
  ];

  const boardKolon: KanbanKolon[] = BOARD_DURUMLAR.map((d) => ({
    anahtar: d,
    baslik: t(`satinalma.durum_${d}`),
    renk: DURUM_RENK[d] ?? RENKLER.metinSoluk,
  }));

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.satinalma')}
        alt={t('satinalma.alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} secenekler={['liste', 'pano']} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('satinalma.yeni')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<SatinalmaTalebi>
            kolonlar={kolonlar}
            veri={data?.veri ?? []}
            meta={data?.meta}
            yukleniyor={isPending}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            aramaYer={t('satinalma.ara')}
            bosMetin={isError ? t('ortak.hata_baslik') : t('satinalma.bos')}
            onRow={(kayit) => ({
              onClick: () => setDetayId(kayit.id),
              style: { cursor: 'pointer' },
            })}
          />
        </Card>
      ) : pano.isPending ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : pano.isError ? (
        <Empty description={t('ortak.hata_baslik')} />
      ) : (
        <KanbanPano<SatinalmaTalebi>
          kolonlar={boardKolon}
          ogeler={pano.data ?? []}
          kolonAnahtar={(x) => x.durum}
          kartAnahtar={(x) => x.id}
          bosMetin={t('satinalma.bos')}
          kartCiz={(x) => (
            <VeriKart
              ustSol={x.kod}
              baslik={x.baslik}
              meta={
                <span>
                  {t('satinalma.yas_gun', { n: dayjs().diff(dayjs(x.olusturma_tarihi), 'day') })}
                </span>
              }
              onClick={() => setDetayId(x.id)}
            />
          )}
        />
      )}

      <SatinalmaTalepDetay id={detayId} kapat={() => setDetayId(null)} />
      <SatinalmaTalepFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
