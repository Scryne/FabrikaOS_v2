/**
 * Abonelik listesi — tenant × plan × durum birleşik görünümü (salt-okunur;
 * plan değişikliği tenant detayından yapılır).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { usePlatformAbonelikler } from './hooks';
import type { AbonelikSatir } from './hooks';

export function AbonelikListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [sayfa, setSayfa] = useState(1);
  const { data, isLoading } = usePlatformAbonelikler(sayfa, 20);

  const kolonlar: ColumnsType<AbonelikSatir> = [
    {
      title: t('platform.slug'),
      dataIndex: 'tenant_slug',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('platform.ad'), dataIndex: 'tenant_ad' },
    {
      title: t('platform.plan'),
      dataIndex: 'plan_kodu',
      render: (v: string) => <Tag color="processing">{v}</Tag>,
    },
    { title: t('platform.durum'), dataIndex: 'durum' },
    {
      title: t('platform.baslangic'),
      dataIndex: 'baslangic_tarihi',
      render: (v: string) => new Date(v).toLocaleDateString(),
    },
    {
      title: t('platform.bitis'),
      dataIndex: 'bitis_tarihi',
      render: (v: string | null) => (v ? new Date(v).toLocaleDateString() : '—'),
    },
  ];

  return (
    <div>
      <h2 style={{ margin: '0 0 16px', fontSize: 17 }}>{t('platform.abonelikler')}</h2>
      <Table<AbonelikSatir>
        rowKey="id"
        size="middle"
        loading={isLoading}
        columns={kolonlar}
        dataSource={data?.veri ?? []}
        onRow={(k) => ({
          onClick: () => navigate(`/platform/tenantlar/${k.tenant_id}`),
          style: { cursor: 'pointer' },
        })}
        pagination={{
          current: data?.meta.sayfa ?? sayfa,
          pageSize: data?.meta.adet ?? 20,
          total: data?.meta.toplam ?? 0,
          showSizeChanger: false,
          onChange: setSayfa,
        }}
      />
    </div>
  );
}
