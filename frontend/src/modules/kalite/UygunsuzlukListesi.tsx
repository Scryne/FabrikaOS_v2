/**
 * Uygunsuzluk (CAPA) listesi — sunucu-taraflı tablo (kod/başlık/önem/durum rozeti) + satır →
 * detay çekmecesi + "yeni uygunsuzluk" (``kalite:yaz``) + durum/önem filtreleri.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Select, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type Uygunsuzluk, useUygunsuzluklar } from './hooks';
import { OnemEtiketi, UygunsuzlukDurumEtiketi } from './rozetler';
import { UygunsuzlukDetay } from './UygunsuzlukDetay';
import { UygunsuzlukFormu } from './UygunsuzlukFormu';

const DURUMLAR = [
  'acik',
  'kok_neden',
  'aksiyon_plani',
  'uygulama',
  'dogrulama',
  'kapandi',
  'iptal',
];
const ONEMLER = ['dusuk', 'orta', 'yuksek', 'kritik'];

export function UygunsuzlukListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useUygunsuzluklar(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

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
      render: (v: string) => <OnemEtiketi onem={v} />,
    },
    {
      title: t('kalite.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string) => <UygunsuzlukDurumEtiketi durum={v} />,
    },
    {
      title: t('kalite.olusturma'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      sorter: true,
      render: (v: string) => <span className="sayisal">{new Date(v).toLocaleString()}</span>,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.uygunsuzluklar')}
        alt={t('kalite.uygunsuzluk_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('kalite.yeni_uygunsuzluk')}
            </Button>
          )
        }
      />
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
                options={DURUMLAR.map((x) => ({ value: x, label: t(`kalite.durum_${x}`) }))}
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
      <UygunsuzlukDetay id={detayId} kapat={() => setDetayId(null)} />
      <UygunsuzlukFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
