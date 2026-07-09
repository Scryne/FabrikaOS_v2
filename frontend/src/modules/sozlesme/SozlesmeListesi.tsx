/**
 * Sözleşmeler çalışma alanı — KPI şeridi + Liste / Board (durum makinesi kolonları) + üstte
 * "yaklaşan" uyarı şeridi. Kart/tablo: SZ- kod · bitiş + **kalan-gün çipi** (30/15/7 eşik
 * renkleri). Kart tıkla → detay çekmecesi (durum geçişi orada). KPI/board /sozlesme/ozet + pano.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Card, Empty, Skeleton, Space } from 'antd';
import type { ReactNode } from 'react';
import type { ColumnsType } from 'antd/es/table';
import type { TFunction } from 'i18next';
import dayjs from 'dayjs';

import { DurumPim, pimUret } from '@/components/DurumPim';
import { GorunumGecis, type Gorunum } from '@/components/GorunumGecis';
import { KanbanPano, type KanbanKolon } from '@/components/KanbanPano';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { UyariKarti } from '@/components/UyariKarti';
import { VeriKart } from '@/components/VeriKart';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import {
  type Sozlesme,
  useSozlesmeOzet,
  useSozlesmePano,
  useSozlesmeler,
  useYaklasanSozlesmeler,
} from './hooks';
import { SozlesmeDetay } from './SozlesmeDetay';
import { SozlesmeFormu } from './SozlesmeFormu';

const HAT = BOLUM_RENGI['menu.bolum_ticari'];

const DURUM_RENK: Record<string, string> = {
  taslak: RENKLER.metinSoluk,
  aktif: RENKLER.basari,
  sonlandi: RENKLER.mavi,
  feshedildi: RENKLER.hata,
  iptal: '#4b4b52',
};
const BOARD_DURUMLAR = ['taslak', 'aktif', 'sonlandi', 'feshedildi'];
const SozlesmePim = pimUret(DURUM_RENK, 'sozlesme.durum_');

/** Bitişe kalan gün çipi (yalnız aktif + 30 gün içinde; 7/15/30 eşik renkleri). */
function kalanGunCip(s: Sozlesme, t: TFunction): ReactNode {
  if (s.durum !== 'aktif') return null;
  const gun = dayjs(s.bitis_tarihi).diff(dayjs(), 'day');
  if (gun < 0 || gun > 30) return null;
  const renk = gun <= 7 ? RENKLER.hata : gun <= 15 ? RENKLER.uyari : RENKLER.mavi;
  return <DurumPim renk={renk} etiket={t('sozlesme.kalan_gun', { gun })} />;
}

export function SozlesmeListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('sozlesme:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const { data, isPending, isError } = useSozlesmeler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useSozlesmeOzet();
  const { data: yaklasan } = useYaklasanSozlesmeler();
  const pano = useSozlesmePano();

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'aktif',
          baslik: t('sozlesme.kpi_aktif'),
          deger: String(ozet.aktif),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'yaklasan',
          baslik: t('sozlesme.kpi_yaklasan'),
          deger: String(ozet.yaklasan),
          ikon: <ClockCircleOutlined />,
        },
        {
          anahtar: 'taslak',
          baslik: t('sozlesme.kpi_taslak'),
          deger: String(ozet.taslak),
          ikon: <FileTextOutlined />,
        },
        {
          anahtar: 'toplam',
          baslik: t('sozlesme.kpi_toplam'),
          deger: String(ozet.toplam),
          ikon: <FileProtectOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Sozlesme> = [
    {
      title: t('sozlesme.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('sozlesme.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    {
      title: t('sozlesme.bitis'),
      dataIndex: 'bitis_tarihi',
      key: 'bitis_tarihi',
      sorter: true,
      render: (v: string, s) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>
          {kalanGunCip(s, t)}
        </span>
      ),
    },
    {
      title: t('sozlesme.tutar'),
      dataIndex: 'tutar',
      key: 'tutar',
      align: 'right',
      render: (v: number, k) => (
        <span className="sayisal">
          {v.toLocaleString('tr-TR')} {k.para_birimi}
        </span>
      ),
    },
    {
      title: t('sozlesme.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: string) => <SozlesmePim durum={d} />,
    },
  ];

  const boardKolon: KanbanKolon[] = BOARD_DURUMLAR.map((d) => ({
    anahtar: d,
    baslik: t(`sozlesme.durum_${d}`),
    renk: DURUM_RENK[d] ?? RENKLER.metinSoluk,
  }));

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.sozlesmeler')}
        alt={t('sozlesme.alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} secenekler={['liste', 'pano']} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('sozlesme.yeni')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      {yaklasan && yaklasan.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <UyariKarti
            onem="uyari"
            baslik={t('sozlesme.kpi_yaklasan')}
            aciklama={yaklasan
              .slice(0, 4)
              .map((s) => `${s.kod} (${dayjs(s.bitis_tarihi).diff(dayjs(), 'day')}g)`)
              .join(' · ')}
          />
        </div>
      )}

      <div style={{ height: 20 }} />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<Sozlesme>
            kolonlar={kolonlar}
            veri={data?.veri ?? []}
            meta={data?.meta}
            yukleniyor={isPending}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            aramaYer={t('sozlesme.ara')}
            bosMetin={isError ? t('ortak.hata_baslik') : t('sozlesme.bos')}
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
        <KanbanPano<Sozlesme>
          kolonlar={boardKolon}
          ogeler={pano.data ?? []}
          kolonAnahtar={(x) => x.durum}
          kartAnahtar={(x) => x.id}
          bosMetin={t('sozlesme.bos')}
          kartCiz={(x) => (
            <VeriKart
              ustSol={x.kod}
              ustSag={kalanGunCip(x, t)}
              baslik={x.baslik}
              meta={<span className="sayisal">{dayjs(x.bitis_tarihi).format('DD.MM.YYYY')}</span>}
              onClick={() => setDetayId(x.id)}
            />
          )}
        />
      )}

      <SozlesmeDetay id={detayId} kapat={() => setDetayId(null)} />
      <SozlesmeFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
