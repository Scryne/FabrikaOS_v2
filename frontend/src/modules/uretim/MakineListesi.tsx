/**
 * Makine listesi — sunucu-taraflı tablo (sayfalama/sıralama/arama) + durum filtresi.
 * Satıra tıklayınca makine detayına gider; ``uretim:yaz`` izni varsa "Makine ekle" görünür.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Select, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { DurumRozet, MAKINE_DURUMLARI } from '@/components/DurumRozet';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type Makine, useMakineler } from './hooks';
import { MakineFormu } from './MakineFormu';

export function MakineListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useMakineler(param);
  const [formAcik, setFormAcik] = useState(false);

  const durumFiltre = (param.filtreler?.durum as string | undefined) ?? '';

  const kolonlar: ColumnsType<Makine> = [
    {
      title: t('uretim.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('uretim.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    {
      title: t('uretim.durum'),
      dataIndex: 'durum',
      key: 'durum',
      sorter: true,
      render: (d: string) => <DurumRozet durum={d} />,
    },
    {
      title: t('uretim.oee_hedefi'),
      dataIndex: 'oee_hedefi',
      key: 'oee_hedefi',
      align: 'right',
      render: (v: number | null) =>
        v != null ? (
          <span className="sayisal">%{Math.round(v * 100)}</span>
        ) : (
          <span style={{ color: 'var(--metin-soluk)' }}>—</span>
        ),
    },
  ];

  const araclar = (
    <Space wrap>
      <Select
        value={durumFiltre}
        onChange={(d) => paramDegistir({ filtreler: { durum: d || undefined } })}
        style={{ width: 160 }}
        options={[
          { value: '', label: t('ortak.tumu') },
          ...MAKINE_DURUMLARI.map((d) => ({ value: d, label: t(`uretim.durum_${d}`) })),
        ]}
      />
      {yazabilir && (
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
          {t('uretim.makine_ekle')}
        </Button>
      )}
    </Space>
  );

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik baslik={t('menu.makineler')} alt={t('uretim.makine_alt')} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Makine>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('uretim.makine_ara')}
          araclar={araclar}
          bosMetin={isError ? t('ortak.hata_baslik') : t('tablo.bos')}
          onRow={(kayit) => ({
            onClick: () => navigate(`/makineler/${kayit.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>

      <MakineFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
