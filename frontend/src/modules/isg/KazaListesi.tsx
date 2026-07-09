/**
 * İş kazaları çalışma alanı — KPI şeridi (imza metrik **"X gündür kazasız"** + bu yıl kaza +
 * ramak kala + kayıp gün) + zengin tablo (tür/ağırlık pimi, yer, tarih, kayıp gün). KPI /isg/ozet.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CalendarOutlined,
  MedicineBoxOutlined,
  PlusOutlined,
  SafetyOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Button, Card, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { pimUret } from '@/components/DurumPim';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type IsKazasi, useIsgOzet, useKazalar } from './hooks';
import { KazaFormu } from './KazaFormu';

const HAT = BOLUM_RENGI['menu.bolum_isg_ik'];
const TURLER = ['kaza', 'ramak_kala', 'meslek_hastaligi'];

const TUR_RENK: Record<string, string> = {
  kaza: RENKLER.hata,
  ramak_kala: RENKLER.uyari,
  meslek_hastaligi: RENKLER.mor,
};
const AGIRLIK_RENK: Record<string, string> = {
  hafif: RENKLER.metinSoluk,
  orta: RENKLER.mavi,
  agir: RENKLER.uyari,
  olumcul: RENKLER.hata,
};
const TurPim = pimUret(TUR_RENK, 'isg.tur_');
const AgirlikPim = pimUret(AGIRLIK_RENK, 'isg.agirlik_');

export function KazaListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useKazalar(param);
  const { data: ozet, isPending: ozetYukleniyor } = useIsgOzet();
  const [formAcik, setFormAcik] = useState(false);

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'kazasiz',
          baslik: t('isg.kpi_kazasiz_baslik'),
          deger: ozet.gunluk_kazasiz >= 0 ? String(ozet.gunluk_kazasiz) : '—',
          altMetin: ozet.gunluk_kazasiz < 0 ? t('isg.kpi_kazasiz_yok') : undefined,
          ikon: <SafetyOutlined />,
        },
        {
          anahtar: 'bu_yil',
          baslik: t('isg.kpi_bu_yil_kaza'),
          deger: String(ozet.bu_yil_kaza),
          ikon: <MedicineBoxOutlined />,
        },
        {
          anahtar: 'ramak',
          baslik: t('isg.kpi_ramak'),
          deger: String(ozet.ramak_kala),
          ikon: <WarningOutlined />,
        },
        {
          anahtar: 'kayip',
          baslik: t('isg.kpi_kayip_gun'),
          deger: String(ozet.toplam_kayip_gun),
          ikon: <CalendarOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<IsKazasi> = [
    {
      title: t('isg.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('isg.tur'),
      dataIndex: 'tur',
      key: 'tur',
      render: (v: string) => <TurPim durum={v} />,
    },
    {
      title: t('isg.agirlik'),
      dataIndex: 'agirlik',
      key: 'agirlik',
      sorter: true,
      render: (v: string) => <AgirlikPim durum={v} />,
    },
    { title: t('isg.yer'), dataIndex: 'yer', key: 'yer' },
    {
      title: t('isg.olay_tarihi'),
      dataIndex: 'olay_tarihi',
      key: 'olay_tarihi',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY HH:mm')}</span>,
    },
    {
      title: t('isg.kaybedilen_gun'),
      dataIndex: 'kaybedilen_gun',
      key: 'kaybedilen_gun',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.is_kazalari')}
        alt={t('isg.kaza_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('isg.kaza_yeni')}
            </Button>
          )
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<IsKazasi>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('isg.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('isg.kaza_bos')}
          araclar={
            <Select
              allowClear
              placeholder={t('isg.tur')}
              style={{ width: 180 }}
              value={param.filtreler?.tur as string | undefined}
              onChange={(v) => paramDegistir({ filtreler: { tur: v } })}
              options={TURLER.map((x) => ({ value: x, label: t(`isg.tur_${x}`) }))}
            />
          }
        />
      </Card>
      <KazaFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
