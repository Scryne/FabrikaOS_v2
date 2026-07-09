/**
 * İzin talepleri çalışma alanı — KPI şeridi + Liste / Board (onay akışı). Board: taslak →
 * onay bekliyor → onaylandı / reddedildi (iptal gösterilmez). KPI/board tek çekimden (useIzinPano)
 * istemcide hesaplanır. Kart tıkla → onay çekmecesi (``ik:onay`` görev ayrımı orada).
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  InboxOutlined,
  PlusOutlined,
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

import { type IzinTalebi, useIzinPano, useIzinler } from './hooks';
import { IzinDetay } from './IzinDetay';
import { IzinFormu } from './IzinFormu';
import { IzinTuruEtiketi } from './rozetler';

const HAT = BOLUM_RENGI['menu.bolum_isg_ik'];
const DURUMLAR = ['taslak', 'onay_bekliyor', 'onaylandi', 'reddedildi', 'iptal'];

const DURUM_RENK: Record<string, string> = {
  taslak: RENKLER.metinSoluk,
  onay_bekliyor: RENKLER.uyari,
  onaylandi: RENKLER.basari,
  reddedildi: RENKLER.hata,
  iptal: '#4b4b52',
};
const BOARD_DURUMLAR = ['taslak', 'onay_bekliyor', 'onaylandi', 'reddedildi'];
const IzinDurumPim = pimUret(DURUM_RENK, 'ik.durum_');

export function IzinListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const { data, isPending, isError } = useIzinler(param);
  const pano = useIzinPano();

  const sayac = useMemo(() => {
    const s = new Map<string, number>();
    for (const x of pano.data ?? []) s.set(x.durum, (s.get(x.durum) ?? 0) + 1);
    return s;
  }, [pano.data]);
  const say = (d: string) => sayac.get(d) ?? 0;

  const metrikler: OzetMetrik[] = pano.data
    ? [
        {
          anahtar: 'bekleyen',
          baslik: t('ik.kpi_izin_bekleyen'),
          deger: String(say('onay_bekliyor')),
          ikon: <ClockCircleOutlined />,
        },
        {
          anahtar: 'onaylanan',
          baslik: t('ik.kpi_izin_onaylanan'),
          deger: String(say('onaylandi')),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'reddedilen',
          baslik: t('ik.kpi_izin_reddedilen'),
          deger: String(say('reddedildi')),
          ikon: <CloseCircleOutlined />,
        },
        {
          anahtar: 'toplam',
          baslik: t('ik.kpi_izin_toplam'),
          deger: String((pano.data ?? []).length),
          ikon: <InboxOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<IzinTalebi> = [
    {
      title: t('ik.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.personel'),
      dataIndex: 'personel_id',
      key: 'personel_id',
      render: (v: number) => <span className="sayisal">#{v}</span>,
    },
    {
      title: t('ik.izin_turu'),
      dataIndex: 'izin_turu',
      key: 'izin_turu',
      render: (v: string) => <IzinTuruEtiketi tur={v} />,
    },
    {
      title: t('ik.baslangic'),
      dataIndex: 'baslangic_tarihi',
      key: 'baslangic_tarihi',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>,
    },
    {
      title: t('ik.gun_sayisi'),
      dataIndex: 'gun_sayisi',
      key: 'gun_sayisi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string) => <IzinDurumPim durum={v} />,
    },
  ];

  const boardKolon: KanbanKolon[] = BOARD_DURUMLAR.map((d) => ({
    anahtar: d,
    baslik: t(`ik.durum_${d}`),
    renk: DURUM_RENK[d] ?? RENKLER.metinSoluk,
  }));

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.izin_talepleri')}
        alt={t('ik.izin_alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} secenekler={['liste', 'pano']} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('ik.izin_yeni')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={pano.isPending} />

      <div style={{ height: 20 }} />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<IzinTalebi>
            kolonlar={kolonlar}
            veri={data?.veri ?? []}
            meta={data?.meta}
            yukleniyor={isPending}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            aramaYer={t('ik.izin_ara')}
            bosMetin={isError ? t('ortak.hata_baslik') : t('ik.izin_bos')}
            araclar={
              <Select
                allowClear
                placeholder={t('ik.durum')}
                style={{ width: 180 }}
                value={param.filtreler?.durum as string | undefined}
                onChange={(v) => paramDegistir({ filtreler: { durum: v } })}
                options={DURUMLAR.map((x) => ({ value: x, label: t(`ik.durum_${x}`) }))}
              />
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
        <KanbanPano<IzinTalebi>
          kolonlar={boardKolon}
          ogeler={pano.data ?? []}
          kolonAnahtar={(x) => x.durum}
          kartAnahtar={(x) => x.id}
          bosMetin={t('ik.izin_bos')}
          kartCiz={(x) => (
            <VeriKart
              ustSol={x.kod}
              ustSag={<IzinTuruEtiketi tur={x.izin_turu} />}
              baslik={`#${x.personel_id} · ${x.gun_sayisi} ${t('ik.gun_sayisi').toLocaleLowerCase('tr')}`}
              meta={
                <span className="sayisal">{dayjs(x.baslangic_tarihi).format('DD.MM.YYYY')}</span>
              }
              onClick={() => setDetayId(x.id)}
            />
          )}
        />
      )}

      <IzinDetay id={detayId} kapat={() => setDetayId(null)} />
      <IzinFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
