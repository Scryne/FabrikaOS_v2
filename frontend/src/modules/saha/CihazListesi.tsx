/**
 * Saha cihazları listesi — salt-okunur sunucu-taraflı tablo (sayfalama/sıralama/arama).
 * ``son_gorulme`` saha ölçümü geldikçe canlı güncellenir (olayIsle → 'saha-cihazlar' invalidate).
 */

import { useTranslation } from 'react-i18next';
import { Card, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';

import { type Cihaz, useCihazlar } from './hooks';

export function CihazListesi() {
  const { t } = useTranslation();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useCihazlar(param);

  const kolonlar: ColumnsType<Cihaz> = [
    {
      title: t('saha.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('saha.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    {
      title: t('saha.protokol'),
      dataIndex: 'protokol',
      key: 'protokol',
      sorter: true,
      render: (p: string) => <Tag>{t(`saha.protokol_${p}`, p)}</Tag>,
    },
    {
      title: t('saha.durum'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean) => (
        <Tag color={aktif ? 'green' : 'default'}>{aktif ? t('saha.aktif') : t('saha.pasif')}</Tag>
      ),
    },
    {
      title: t('saha.son_gorulme'),
      dataIndex: 'son_gorulme',
      key: 'son_gorulme',
      sorter: true,
      align: 'right',
      render: (v: string | null) =>
        v ? (
          <span className="sayisal">{new Date(v).toLocaleString()}</span>
        ) : (
          <span style={{ color: 'var(--metin-soluk)' }}>—</span>
        ),
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik baslik={t('menu.saha')} alt={t('saha.alt')} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Cihaz>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('saha.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('saha.bos')}
        />
      </Card>
    </div>
  );
}
