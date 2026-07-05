/**
 * Kritik stok ekranı — ``/stok/kritik`` (sayfasız; backend tüm kritikleri döner).
 * Aktif + kritik eşiği aşılmış (mevcut ≤ kritik) malzemeleri kırmızı rozetle listeler.
 */

import { useTranslation } from 'react-i18next';
import { CheckCircleOutlined } from '@ant-design/icons';
import { Card, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { SayfaBaslik } from '@/components/SayfaBaslik';

import { type Malzeme, useKritikStok } from './hooks';

/** Mevcut/eşik doluluk çubuğu — eşiğe yakınlık tek bakışta (tüm satırlar zaten kritik). */
function EsikCubugu({ mevcut, esik }: { mevcut: number; esik: number }) {
  const oran = esik > 0 ? Math.max(0, Math.min(1, mevcut / esik)) : 0;
  return (
    <div
      style={{
        width: 90,
        height: 5,
        borderRadius: 3,
        background: 'rgba(255,255,255,0.08)',
        overflow: 'hidden',
      }}
      aria-hidden="true"
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          background: oran < 0.5 ? 'var(--hata)' : 'var(--uyari)',
          transform: `scaleX(${oran})`,
          transformOrigin: 'left',
        }}
      />
    </div>
  );
}

export function KritikStok() {
  const { t } = useTranslation();
  const { data, isPending } = useKritikStok();

  const kolonlar: ColumnsType<Malzeme> = [
    {
      title: t('stok.kod'),
      dataIndex: 'kod',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('stok.ad'), dataIndex: 'ad' },
    {
      title: t('stok.mevcut'),
      dataIndex: 'mevcut_miktar',
      align: 'right',
      render: (v: number, m) => (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 10,
            justifyContent: 'flex-end',
          }}
        >
          <EsikCubugu mevcut={v} esik={m.kritik_stok} />
          <span className="sayisal" style={{ color: 'var(--hata)', fontWeight: 600 }}>
            {v} {m.birim}
          </span>
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
          locale={{
            emptyText: (
              <BosDurum
                ikon={<CheckCircleOutlined style={{ color: 'var(--basari)' }} />}
                baslik={t('stok.kritik_bos')}
              />
            ),
          }}
          pagination={false}
          columns={kolonlar}
        />
      </Card>
    </div>
  );
}
