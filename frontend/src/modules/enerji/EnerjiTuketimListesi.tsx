/**
 * Enerji tüketim ekranı — üstte trend grafiği (CAGG) kartı + sunucu-taraflı ölçüm tablosu +
 * "ölçüm ekle" (``enerji:yaz``) + tür filtresi.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type EnerjiOlcum, useEnerjiOlcumler } from './hooks';
import { EnerjiGirisFormu } from './EnerjiGirisFormu';
import { EnerjiTrend } from './EnerjiTrend';

const TURLER = ['elektrik', 'dogalgaz', 'su', 'hava', 'buhar'];

export function EnerjiTuketimListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('enerji:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useEnerjiOlcumler(param);
  const [formAcik, setFormAcik] = useState(false);

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
    <div style={{ maxWidth: 1320 }}>
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
    </div>
  );
}
