/**
 * Risk değerlendirme listesi — sunucu-taraflı tablo (kod/başlık/bölüm/skor/seviye rozeti/durum)
 * + "yeni" (``isg:yaz``) + seviye filtresi.
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

import { type RiskDegerlendirme, useRiskler } from './hooks';
import { RiskFormu } from './RiskFormu';
import { RiskDurumEtiketi, RiskSeviyeEtiketi } from './rozetler';

const SEVIYELER = ['dusuk', 'orta', 'yuksek', 'cok_yuksek'];

export function RiskListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useRiskler(param);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<RiskDegerlendirme> = [
    {
      title: t('isg.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('isg.baslik'), dataIndex: 'baslik', key: 'baslik' },
    { title: t('isg.bolum'), dataIndex: 'bolum', key: 'bolum' },
    {
      title: t('isg.risk_skoru'),
      dataIndex: 'risk_skoru',
      key: 'risk_skoru',
      align: 'right',
      sorter: true,
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('isg.risk_seviyesi'),
      dataIndex: 'risk_seviyesi',
      key: 'risk_seviyesi',
      render: (v: string) => <RiskSeviyeEtiketi seviye={v} />,
    },
    {
      title: t('isg.risk_durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string) => <RiskDurumEtiketi durum={v} />,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.risk_degerlendirme')}
        alt={t('isg.risk_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('isg.risk_yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<RiskDegerlendirme>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('isg.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('isg.risk_bos')}
          araclar={
            <Select
              allowClear
              placeholder={t('isg.risk_seviyesi')}
              style={{ width: 180 }}
              value={param.filtreler?.risk_seviyesi as string | undefined}
              onChange={(v) => paramDegistir({ filtreler: { risk_seviyesi: v } })}
              options={SEVIYELER.map((x) => ({ value: x, label: t(`isg.seviye_${x}`) }))}
            />
          }
        />
      </Card>
      <RiskFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
