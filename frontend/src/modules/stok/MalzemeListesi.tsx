/**
 * Malzeme listesi — sunucu-taraflı tablo + kritik rozet + "yeni malzeme" + hareket aksiyonu.
 * Satıra tıklayınca malzeme detayına gider; ``stok:yaz`` izni varsa yazma aksiyonları görünür.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type Malzeme, useMalzemeler } from './hooks';
import { MalzemeFormu } from './MalzemeFormu';
import { StokHareketFormu } from './StokHareketFormu';

export function MalzemeListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('stok:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useMalzemeler(param);
  const [formAcik, setFormAcik] = useState(false);
  const [hareketMalzeme, setHareketMalzeme] = useState<Malzeme | null>(null);

  const kolonlar: ColumnsType<Malzeme> = [
    {
      title: t('stok.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string, m) => (
        <Space>
          <span className="sayisal">{v}</span>
          {m.kritik && (
            <Tag color="red" bordered={false}>
              {t('stok.kritik_rozet')}
            </Tag>
          )}
        </Space>
      ),
    },
    { title: t('stok.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    {
      title: t('stok.mevcut'),
      dataIndex: 'mevcut_miktar',
      key: 'mevcut_miktar',
      sorter: true,
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
      key: 'kritik_stok',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('stok.durum'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean) => (
        <Tag color={aktif ? 'green' : 'default'}>{aktif ? t('stok.aktif') : t('stok.pasif')}</Tag>
      ),
    },
    ...(yazabilir
      ? [
          {
            title: '',
            key: 'aksiyon',
            align: 'right' as const,
            render: (_: unknown, m: Malzeme) => (
              <Button
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  setHareketMalzeme(m);
                }}
              >
                {t('stok.hareket_ekle')}
              </Button>
            ),
          },
        ]
      : []),
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.malzemeler')}
        alt={t('stok.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('stok.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Malzeme>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('stok.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('stok.bos')}
          onRow={(kayit) => ({
            onClick: () => navigate(`/malzemeler/${kayit.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <MalzemeFormu acik={formAcik} kapat={() => setFormAcik(false)} />
      <StokHareketFormu malzeme={hareketMalzeme} kapat={() => setHareketMalzeme(null)} />
    </div>
  );
}
