/**
 * Kritik stok ekranı — ``/stok/kritik`` (sayfasız; backend tüm kritikleri döner).
 * Aktif + kritik eşiği aşılmış (mevcut ≤ kritik) malzemeleri kırmızı rozetle listeler.
 */

import { useTranslation } from 'react-i18next';
import { Card, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';

import { type Malzeme, useKritikStok } from './hooks';

export function KritikStok() {
  const { t } = useTranslation();
  const { data, isPending } = useKritikStok();

  const kolonlar: ColumnsType<Malzeme> = [
    {
      title: t('stok.kod'),
      dataIndex: 'kod',
      render: (v: string) => (
        <span className="sayisal">
          {v}{' '}
          <Tag color="red" bordered={false}>
            {t('stok.kritik_rozet')}
          </Tag>
        </span>
      ),
    },
    { title: t('stok.ad'), dataIndex: 'ad' },
    {
      title: t('stok.mevcut'),
      dataIndex: 'mevcut_miktar',
      align: 'right',
      render: (v: number, m) => (
        <span className="sayisal">
          {v} {m.birim}
        </span>
      ),
    },
    {
      title: t('stok.kritik_esik'),
      dataIndex: 'kritik_stok',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
  ];

  return (
    <div style={{ maxWidth: 1100 }}>
      <SayfaBaslik baslik={t('stok.kritik_baslik')} />
      <Card styles={{ body: { padding: 18 } }}>
        <Table<Malzeme>
          rowKey="id"
          loading={isPending}
          dataSource={data ?? []}
          locale={{ emptyText: t('stok.kritik_bos') }}
          pagination={false}
          columns={kolonlar}
        />
      </Card>
    </div>
  );
}
