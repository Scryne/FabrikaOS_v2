/**
 * Kritik stok — uyarı-odaklı ekran: üstte özet `UyariKarti` ("N kalem kritik altında"),
 * altında kritik-sıralı zengin tablo (malzeme varlık hücresi + stok mini-bar) + satırdan tek-tık
 * satınalma talebi CTA. Veri ``/stok/kritik`` (sayfasız; backend tüm kritikleri döner).
 */

import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { CheckCircleOutlined, GoldOutlined, ShoppingCartOutlined } from '@ant-design/icons';
import { Button, Card, Table } from 'antd';
import type { CSSProperties } from 'react';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { MiniBar } from '@/components/MiniBar';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { UyariKarti } from '@/components/UyariKarti';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { type Malzeme, useKritikStok } from './hooks';

export function KritikStok() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('satinalma:yaz'));
  const { data, isPending } = useKritikStok();
  const kritikler = data ?? [];

  const kolonlar: ColumnsType<Malzeme> = [
    {
      title: t('stok.ad'),
      key: 'ad',
      render: (_v: unknown, m: Malzeme) => (
        <span className="varlik-hucre">
          <span
            className="ikon-plaka kucuk"
            aria-hidden="true"
            style={{ '--plaka-renk': RENKLER.hata } as CSSProperties}
          >
            <GoldOutlined />
          </span>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {m.ad}
            </span>
            <span className="varlik-alt sayisal">
              {m.kod} · {m.birim}
            </span>
          </span>
        </span>
      ),
    },
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
          <MiniBar deger={v} enBuyuk={m.kritik_stok || 1} renk={RENKLER.hata} />
          <span
            className="sayisal"
            style={{ color: 'var(--hata)', fontWeight: 600, width: 60, textAlign: 'right' }}
          >
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
    ...(yazabilir
      ? [
          {
            title: '',
            key: 'aksiyon',
            align: 'right' as const,
            render: () => (
              <Button
                size="small"
                icon={<ShoppingCartOutlined />}
                onClick={() => navigate('/satinalma-talepleri')}
              >
                {t('menu.satinalma')}
              </Button>
            ),
          },
        ]
      : []),
  ];

  return (
    <SayfaKapsayici enGenis={1100}>
      <SayfaBaslik baslik={t('stok.kritik_baslik')} alt={t('stok.alt')} />

      {kritikler.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <UyariKarti
            onem="kritik"
            baslik={t('stok.kpi_kritik')}
            aciklama={`${kritikler.length} ${t('stok.kritik_rozet').toLocaleLowerCase('tr')}`}
          />
        </div>
      )}

      <Card styles={{ body: { padding: 18 } }}>
        <Table<Malzeme>
          rowKey="id"
          loading={isPending}
          dataSource={kritikler}
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
    </SayfaKapsayici>
  );
}
