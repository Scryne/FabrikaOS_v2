/** Kontrol planı detayı (S26-A): karakteristikler, toleranslar, kart durumu; kartın kendisine geçiş. */

import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Card, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';

import { type Karakteristik, usePlan } from './spcHooks';

const sayi = (v: string | number | null | undefined) =>
  v === null || v === undefined ? '—' : String(v);

export function KontrolPlaniDetay() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const id = Number(useParams().id);
  const plan = usePlan(id);
  const p = plan.data;

  const kolonlar: ColumnsType<Karakteristik> = [
    { title: '#', dataIndex: 'sira', width: 48, className: 'sayisal' },
    {
      title: t('spc.karakteristik'),
      dataIndex: 'ad',
      render: (v: string, k) => (
        <Link
          to={`/karakteristikler/${k.id}/spc`}
          className="varlik-ad"
          onClick={(e) => e.stopPropagation()}
        >
          {v}
        </Link>
      ),
    },
    {
      title: t('spc.tolerans'),
      key: 'tol',
      render: (_v, k) => (
        <span className="sayisal">
          {sayi(k.alt_tolerans)} – {sayi(k.ust_tolerans)} {k.birim}
        </span>
      ),
    },
    { title: t('spc.n'), dataIndex: 'alt_grup_boyutu', align: 'right', responsive: ['md'] },
    { title: t('spc.alt_grup_sayisi'), dataIndex: 'alt_grup_sayisi', align: 'right' },
    {
      title: t('spc.kart_durumu'),
      key: 'durum',
      render: (_v, k) =>
        k.son_ihlal ? (
          <Tag color="red">{t('spc.son_noktada_ihlal')}</Tag>
        ) : k.limitler_sabit ? (
          <Tag color="green">{t('spc.limitler_sabit')}</Tag>
        ) : (
          <Tag>{t('spc.faz1')}</Tag>
        ),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={p ? p.ad : t('spc.plan')}
        alt={
          <span>
            <Link to="/kontrol-planlari">{t('spc.planlar_baslik')}</Link>
            {p && (
              <span className="sayisal">
                {' '}
                · {p.kod}
                {p.operasyon ? ` · ${p.operasyon}` : ''}
              </span>
            )}
          </span>
        }
      />
      <Card loading={plan.isPending}>
        <Table<Karakteristik>
          rowKey="id"
          columns={kolonlar}
          dataSource={p?.karakteristikler ?? []}
          pagination={false}
          scroll={{ x: 'max-content' }}
          onRow={(k) => ({
            onClick: () => navigate(`/karakteristikler/${k.id}/spc`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </SayfaKapsayici>
  );
}
