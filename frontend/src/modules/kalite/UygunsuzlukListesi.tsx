/**
 * Uygunsuzluk (CAPA) çalışma alanı — KPI şeridi + Liste / Board (6 kolonlu CAPA akışı) geçişi.
 * Board: açık → kök neden → aksiyon planı → uygulama → doğrulama → kapandı (iptal gösterilmez;
 * kolonlar min-genişlik + yatay kaydırma). Kart tıkla → detay çekmecesi (aşama geçişi + aksiyonlar).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  FileSearchOutlined,
  IssuesCloseOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Button, Card, Empty, Select, Skeleton, Space } from 'antd';
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

import { type Uygunsuzluk, useKaliteOzet, useUygunsuzluklar, useUygunsuzlukPano } from './hooks';
import { UygunsuzlukDetay } from './UygunsuzlukDetay';
import { UygunsuzlukFormu } from './UygunsuzlukFormu';

const HAT = BOLUM_RENGI['menu.bolum_kalite'];

const DURUM_RENK: Record<string, string> = {
  acik: RENKLER.metinSoluk,
  kok_neden: RENKLER.cyan,
  aksiyon_plani: RENKLER.mavi,
  uygulama: RENKLER.uyari,
  dogrulama: RENKLER.mor,
  kapandi: RENKLER.basari,
  iptal: '#4b4b52',
};
const ONEM_RENK: Record<string, string> = {
  dusuk: RENKLER.metinSoluk,
  orta: RENKLER.mavi,
  yuksek: RENKLER.uyari,
  kritik: RENKLER.hata,
};
const BOARD_DURUMLAR = ['acik', 'kok_neden', 'aksiyon_plani', 'uygulama', 'dogrulama', 'kapandi'];
const LISTE_DURUMLAR = [...BOARD_DURUMLAR, 'iptal'];
const ONEMLER = ['dusuk', 'orta', 'yuksek', 'kritik'];

const DurumPim2 = pimUret(DURUM_RENK, 'kalite.durum_');
const OnemPim = pimUret(ONEM_RENK, 'kalite.onem_');

export function UygunsuzlukListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const { data, isPending, isError } = useUygunsuzluklar(param);
  const { data: ozet, isPending: ozetYukleniyor } = useKaliteOzet();
  const pano = useUygunsuzlukPano();

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'acik',
          baslik: t('kalite.kpi_acik'),
          deger: String(ozet.acik_uygunsuzluk),
          ikon: <IssuesCloseOutlined />,
        },
        {
          anahtar: 'dogrulama',
          baslik: t('kalite.kpi_dogrulamada'),
          deger: String(ozet.dogrulamada),
          ikon: <FileSearchOutlined />,
        },
        {
          anahtar: 'buay',
          baslik: t('kalite.kpi_bu_ay'),
          deger: String(ozet.bu_ay_kapanan),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'toplam',
          baslik: t('kalite.kpi_toplam'),
          deger: String(ozet.toplam_uygunsuzluk),
          ikon: <SafetyCertificateOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Uygunsuzluk> = [
    {
      title: t('kalite.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('kalite.baslik'), dataIndex: 'baslik', key: 'baslik' },
    {
      title: t('kalite.onem'),
      dataIndex: 'onem',
      key: 'onem',
      render: (v: string) => <OnemPim durum={v} />,
    },
    {
      title: t('kalite.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string) => <DurumPim2 durum={v} />,
    },
    {
      title: t('kalite.olusturma'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      sorter: true,
      align: 'right',
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>,
    },
  ];

  const boardKolon: KanbanKolon[] = BOARD_DURUMLAR.map((d) => ({
    anahtar: d,
    baslik: t(`kalite.durum_${d}`),
    renk: DURUM_RENK[d] ?? RENKLER.metinSoluk,
  }));

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.uygunsuzluklar')}
        alt={t('kalite.uygunsuzluk_alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} secenekler={['liste', 'pano']} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('kalite.yeni_uygunsuzluk')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<Uygunsuzluk>
            kolonlar={kolonlar}
            veri={data?.veri ?? []}
            meta={data?.meta}
            yukleniyor={isPending}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            aramaYer={t('kalite.uygunsuzluk_ara')}
            bosMetin={isError ? t('ortak.hata_baslik') : t('kalite.uygunsuzluk_bos')}
            araclar={
              <Space>
                <Select
                  allowClear
                  placeholder={t('kalite.durum')}
                  style={{ width: 170 }}
                  value={param.filtreler?.durum as string | undefined}
                  onChange={(v) => paramDegistir({ filtreler: { durum: v } })}
                  options={LISTE_DURUMLAR.map((x) => ({ value: x, label: t(`kalite.durum_${x}`) }))}
                />
                <Select
                  allowClear
                  placeholder={t('kalite.onem')}
                  style={{ width: 140 }}
                  value={param.filtreler?.onem as string | undefined}
                  onChange={(v) => paramDegistir({ filtreler: { onem: v } })}
                  options={ONEMLER.map((x) => ({ value: x, label: t(`kalite.onem_${x}`) }))}
                />
              </Space>
            }
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
        <KanbanPano<Uygunsuzluk>
          kolonlar={boardKolon}
          ogeler={pano.data ?? []}
          kolonAnahtar={(x) => x.durum}
          kartAnahtar={(x) => x.id}
          bosMetin={t('kalite.uygunsuzluk_bos')}
          kartCiz={(x) => (
            <VeriKart
              ustSol={x.kod}
              ustSag={<OnemPim durum={x.onem} />}
              baslik={x.baslik}
              meta={
                <span>
                  {t('kalite.yas_gun', { n: dayjs().diff(dayjs(x.olusturma_tarihi), 'day') })}
                </span>
              }
              onClick={() => setDetayId(x.id)}
            />
          )}
        />
      )}

      <UygunsuzlukDetay id={detayId} kapat={() => setDetayId(null)} />
      <UygunsuzlukFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
