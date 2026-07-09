/**
 * Enerji tüketim ekranı — üstte trend grafiği (CAGG) kartı + sunucu-taraflı ölçüm tablosu +
 * "ölçüm ekle" (``enerji:yaz``) + tür filtresi.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ApiOutlined,
  ClockCircleOutlined,
  PlusOutlined,
  RobotOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Button, Card, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { type EnerjiOlcum, useEnerjiOlcumler, useEnerjiOzet } from './hooks';
import { EnerjiGirisFormu } from './EnerjiGirisFormu';
import { EnerjiTrend } from './EnerjiTrend';

const HAT = BOLUM_RENGI['menu.bolum_kalite'];
const TURLER = ['elektrik', 'dogalgaz', 'su', 'hava', 'buhar'];

export function EnerjiTuketimListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('enerji:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useEnerjiOlcumler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useEnerjiOzet();
  const [formAcik, setFormAcik] = useState(false);

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'kayit',
          baslik: t('enerji.kpi_kayit'),
          deger: String(ozet.toplam_kayit),
          ikon: <ThunderboltOutlined />,
        },
        {
          anahtar: 'bugun',
          baslik: t('enerji.kpi_bugun'),
          deger: String(ozet.bugun_kayit),
          ikon: <ClockCircleOutlined />,
        },
        {
          anahtar: 'tur',
          baslik: t('enerji.kpi_tur'),
          deger: String(ozet.tur_sayisi),
          ikon: <ApiOutlined />,
        },
        {
          anahtar: 'makine',
          baslik: t('enerji.kpi_makine'),
          deger: String(ozet.izlenen_makine),
          ikon: <RobotOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<EnerjiOlcum> = [
    {
      title: t('enerji.zaman'),
      dataIndex: 'zaman',
      key: 'zaman',
      sorter: true,
      render: (v: string) => <span className="sayisal">{new Date(v).toLocaleString()}</span>,
    },
    {
      title: t('enerji.enerji_turu'),
      dataIndex: 'enerji_turu',
      key: 'enerji_turu',
      render: (v: string) => t(`enerji.tur_${v}`),
    },
    {
      title: t('enerji.tuketim'),
      dataIndex: 'tuketim',
      key: 'tuketim',
      align: 'right',
      render: (v: number, m) => (
        <span className="sayisal">
          {v} {m.birim}
        </span>
      ),
    },
    {
      title: t('enerji.makine'),
      dataIndex: 'makine_id',
      key: 'makine_id',
      render: (v: number | null) => <span className="sayisal">{v ?? '—'}</span>,
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.enerji')}
        alt={t('enerji.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('enerji.olcum_ekle')}
            </Button>
          )
        }
      />
      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />
      <div style={{ height: 20 }} />
      <div style={{ marginBottom: 18 }}>
        <EnerjiTrend />
      </div>
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<EnerjiOlcum>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          bosMetin={isError ? t('ortak.hata_baslik') : t('enerji.bos')}
          araclar={
            <Select
              allowClear
              placeholder={t('enerji.enerji_turu')}
              style={{ width: 170 }}
              value={param.filtreler?.enerji_turu as string | undefined}
              onChange={(v) => paramDegistir({ filtreler: { enerji_turu: v } })}
              options={TURLER.map((x) => ({ value: x, label: t(`enerji.tur_${x}`) }))}
            />
          }
        />
      </Card>
      <EnerjiGirisFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
