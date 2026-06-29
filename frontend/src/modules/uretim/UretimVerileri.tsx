/**
 * Üretim verileri — sunucu-taraflı tablo (zaman/adet sıralanabilir) + makine filtresi + giriş.
 * Üretim verisi metin içermez; bu yüzden arama kutusu yoktur (tablo arama olmadan da çalışır).
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Select, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type UretimVerisi, useMakineSecenekleri, useUretimVerileri } from './hooks';
import { UretimGirisFormu } from './UretimGirisFormu';

function sayi(v: number): string {
  return v.toLocaleString('tr-TR');
}

export function UretimVerileri() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));
  const [param, paramDegistir] = useSayfaParam({ siralama: 'zaman', yon: 'desc' });
  const { data, isPending, isError } = useUretimVerileri(param);
  const { data: makineler } = useMakineSecenekleri();
  const [formAcik, setFormAcik] = useState(false);

  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);
  const makineFiltre = (param.filtreler?.makine_id as number | undefined) ?? undefined;

  const kolonlar: ColumnsType<UretimVerisi> = [
    {
      title: t('uretim.zaman'),
      dataIndex: 'zaman',
      key: 'zaman',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY HH:mm')}</span>,
    },
    {
      title: t('uretim.makine'),
      dataIndex: 'makine_id',
      key: 'makine_id',
      render: (id: number) => makineHarita.get(id)?.kod ?? `#${id}`,
    },
    { title: t('uretim.vardiya'), dataIndex: 'vardiya', key: 'vardiya', render: (v) => v ?? '—' },
    {
      title: t('uretim.toplam_adet'),
      dataIndex: 'toplam_adet',
      key: 'toplam_adet',
      align: 'right',
      sorter: true,
      render: (v: number) => <span className="sayisal">{sayi(v)}</span>,
    },
    {
      title: t('uretim.saglam_adet'),
      dataIndex: 'saglam_adet',
      key: 'saglam_adet',
      align: 'right',
      render: (v: number) => <span className="sayisal">{sayi(v)}</span>,
    },
    {
      title: t('uretim.durus_sure'),
      dataIndex: 'durus_sure_dk',
      key: 'durus_sure_dk',
      align: 'right',
      sorter: true,
      render: (v: number) => <span className="sayisal">{sayi(v)}</span>,
    },
  ];

  const araclar = (
    <Space wrap>
      <Select
        value={makineFiltre}
        onChange={(id) => paramDegistir({ filtreler: { makine_id: id ?? undefined } })}
        style={{ width: 220 }}
        allowClear
        showSearch
        optionFilterProp="label"
        placeholder={t('uretim.makine_filtre')}
        options={(makineler ?? []).map((m) => ({ value: m.id, label: `${m.kod} · ${m.ad}` }))}
      />
      {yazabilir && (
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
          {t('uretim.uretim_girisi')}
        </Button>
      )}
    </Space>
  );

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik baslik={t('uretim.uretim_verileri')} alt={t('uretim.uretim_alt')} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<UretimVerisi>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          araclar={araclar}
          bosMetin={isError ? t('ortak.hata_baslik') : t('tablo.bos')}
        />
      </Card>

      <UretimGirisFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
