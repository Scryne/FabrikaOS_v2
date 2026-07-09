/**
 * Talepler çalışma alanı — KPI şeridi + Liste / Board (durum makinesi kolonları). Board:
 * açık → inceleniyor → çözüldü → kapandı (iptal gösterilmez). Kart tıkla → detay çekmecesi.
 * KPI/board `/talep/ozet` + pano çekimi.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { InboxOutlined, PlusOutlined, SyncOutlined, UserDeleteOutlined } from '@ant-design/icons';
import { CheckCircleOutlined } from '@ant-design/icons';
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

import { type Talep, useTalepOzet, useTalepPano, useTalepler } from './hooks';
import { TalepDetay } from './TalepDetay';
import { TalepFormu } from './TalepFormu';

const HAT = BOLUM_RENGI['menu.bolum_ticari'];

const DURUM_RENK: Record<string, string> = {
  acik: RENKLER.metinSoluk,
  inceleniyor: RENKLER.mavi,
  cozuldu: RENKLER.basari,
  kapandi: RENKLER.cyan,
  iptal: '#4b4b52',
};
const ONCELIK_RENK: Record<string, string> = {
  dusuk: RENKLER.metinSoluk,
  orta: RENKLER.mavi,
  yuksek: RENKLER.uyari,
};
const BOARD_DURUMLAR = ['acik', 'inceleniyor', 'cozuldu', 'kapandi'];
const TalepDurumPim = pimUret(DURUM_RENK, 'talep.hal_');
const OncelikPim = pimUret(ONCELIK_RENK, 'talep.oncelik_');

export function TalepListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('talep:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const { data, isPending, isError } = useTalepler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useTalepOzet();
  const pano = useTalepPano();

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'acik',
          baslik: t('talep.kpi_acik'),
          deger: String(ozet.acik),
          ikon: <InboxOutlined />,
        },
        {
          anahtar: 'atanmamis',
          baslik: t('talep.kpi_atanmamis'),
          deger: String(ozet.atanmamis),
          ikon: <UserDeleteOutlined />,
        },
        {
          anahtar: 'cozulen',
          baslik: t('talep.kpi_cozulen'),
          deger: String(ozet.cozulen),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'toplam',
          baslik: t('talep.kpi_toplam'),
          deger: String(ozet.toplam),
          ikon: <SyncOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Talep> = [
    {
      title: t('talep.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('talep.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    {
      title: t('talep.oncelik'),
      dataIndex: 'oncelik',
      key: 'oncelik',
      sorter: true,
      render: (v: string) => <OncelikPim durum={v} />,
    },
    {
      title: t('talep.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: string) => <TalepDurumPim durum={d} />,
    },
  ];

  const boardKolon: KanbanKolon[] = BOARD_DURUMLAR.map((d) => ({
    anahtar: d,
    baslik: t(`talep.hal_${d}`),
    renk: DURUM_RENK[d] ?? RENKLER.metinSoluk,
  }));

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.talepler')}
        alt={t('talep.alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} secenekler={['liste', 'pano']} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('talep.yeni')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<Talep>
            kolonlar={kolonlar}
            veri={data?.veri ?? []}
            meta={data?.meta}
            yukleniyor={isPending}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            aramaYer={t('talep.ara')}
            bosMetin={isError ? t('ortak.hata_baslik') : t('talep.bos')}
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
        <KanbanPano<Talep>
          kolonlar={boardKolon}
          ogeler={pano.data ?? []}
          kolonAnahtar={(x) => x.durum}
          kartAnahtar={(x) => x.id}
          bosMetin={t('talep.bos')}
          kartCiz={(x) => (
            <VeriKart
              ustSol={x.kod}
              ustSag={<OncelikPim durum={x.oncelik} />}
              baslik={x.baslik}
              meta={
                <span>
                  {t('talep.yas_gun', { n: dayjs().diff(dayjs(x.olusturma_tarihi), 'day') })}
                </span>
              }
              onClick={() => setDetayId(x.id)}
            />
          )}
        />
      )}

      <TalepDetay id={detayId} kapat={() => setDetayId(null)} />
      <TalepFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
