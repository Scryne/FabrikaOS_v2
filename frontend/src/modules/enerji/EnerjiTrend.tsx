/** Enerji tüketim trendi (ECharts çizgi). Tür + aralık (saat/gün) filtreleri; CAGG'den okur. */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, Segmented, Select, Space } from 'antd';

import { EGrafik } from '@/components/grafik/EGrafik';
import { cizgiSecenek } from '@/components/grafik/grafikSecenek';

import { useEnerjiTrend } from './hooks';

const TURLER = ['elektrik', 'dogalgaz', 'su', 'hava', 'buhar'];

export function EnerjiTrend() {
  const { t } = useTranslation();
  const [tur, setTur] = useState('elektrik');
  const [aralik, setAralik] = useState('saat');
  const { data } = useEnerjiTrend({ enerji_turu: tur, aralik });

  const secenek = useMemo(
    () =>
      cizgiSecenek(
        (data ?? []).map((n) => ({
          zaman: new Date(n.zaman).toLocaleString(),
          deger: n.toplam,
        })),
      ),
    [data],
  );

  return (
    <Card
      title={t('menu.enerji_trend')}
      extra={
        <Space>
          <Select
            value={tur}
            onChange={setTur}
            options={TURLER.map((x) => ({ value: x, label: t(`enerji.tur_${x}`) }))}
            style={{ width: 150 }}
          />
          <Segmented
            value={aralik}
            onChange={(v) => setAralik(String(v))}
            options={[
              { value: 'saat', label: t('enerji.aralik_saat') },
              { value: 'gun', label: t('enerji.aralik_gun') },
            ]}
          />
        </Space>
      }
    >
      <EGrafik secenek={secenek} yukseklik={280} />
    </Card>
  );
}
