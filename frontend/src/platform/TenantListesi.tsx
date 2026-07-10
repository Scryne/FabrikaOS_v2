/**
 * Tenant listesi — platform ana ekranı: durum/plan/koltuk kullanımı sütunları +
 * slug/ad araması. Satır tıklaması detaya götürür.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { SearchOutlined } from '@ant-design/icons';
import { Input, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { useTenantlar } from './hooks';
import type { TenantOzet } from './hooks';

export function TenantListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [sayfa, setSayfa] = useState(1);
  const [arama, setArama] = useState('');
  const { data, isLoading } = useTenantlar(sayfa, 20, arama);

  const kolonlar: ColumnsType<TenantOzet> = [
    {
      title: t('platform.slug'),
      dataIndex: 'slug',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('platform.ad'), dataIndex: 'ad' },
    {
      title: t('platform.plan'),
      dataIndex: 'plan_kodu',
      render: (v: string | null) => (v ? <Tag color="processing">{v}</Tag> : '—'),
    },
    {
      title: t('platform.durum'),
      dataIndex: 'aktif',
      render: (aktif: boolean) =>
        aktif ? (
          <Tag color="success">{t('platform.aktif')}</Tag>
        ) : (
          <Tag color="warning">{t('platform.askida')}</Tag>
        ),
    },
    {
      title: t('platform.koltuk'),
      key: 'koltuk',
      render: (_, k) => (
        <span className="sayisal">
          {k.koltuk_kullanilan ?? '—'} / {k.koltuk_limiti ?? t('platform.koltuk_sinirsiz')}
        </span>
      ),
    },
    {
      title: t('platform.olusturma'),
      dataIndex: 'olusturma_tarihi',
      render: (v: string) => new Date(v).toLocaleDateString(),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
          marginBottom: 16,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 17 }}>{t('platform.tenantlar')}</h2>
        <Input
          allowClear
          prefix={<SearchOutlined style={{ color: 'var(--metin-soluk)' }} />}
          placeholder={t('platform.ara')}
          style={{ maxWidth: 280 }}
          onChange={(e) => {
            setArama(e.target.value);
            setSayfa(1);
          }}
        />
      </div>

      <Table<TenantOzet>
        rowKey="id"
        size="middle"
        loading={isLoading}
        columns={kolonlar}
        dataSource={data?.veri ?? []}
        onRow={(k) => ({
          onClick: () => navigate(`/platform/tenantlar/${k.id}`),
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
