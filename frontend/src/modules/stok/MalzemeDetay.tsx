/**
 * Malzeme detayı — künye + eşikler (Descriptions) + son stok hareketleri (sunucu-taraflı tablo).
 * ``stok:yaz`` ile "stok hareketi" ve "düzenle" açılır. Bakiye/kritik canlı invalidate ile yansır.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeftOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Card, Descriptions, Result, Skeleton, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type Malzeme, type StokHareketi, useMalzeme, useStokHareketleri } from './hooks';
import { MalzemeFormu } from './MalzemeFormu';
import { StokHareketFormu } from './StokHareketFormu';

export function MalzemeDetay() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id: idParam } = useParams();
  const id = Number(idParam);
  const yazabilir = useAuthStore((s) => s.izinVar('stok:yaz'));

  const malzeme = useMalzeme(id);
  const [param, paramDegistir] = useSayfaParam({ adet: 8 });
  const hareketler = useStokHareketleri(param, id);
  const [hareketAcik, setHareketAcik] = useState(false);
  const [duzenleAcik, setDuzenleAcik] = useState(false);

  const kolonlar: ColumnsType<StokHareketi> = [
    {
      title: t('stok.tur'),
      dataIndex: 'tur',
      key: 'tur',
      render: (v: string) => t(`stok.${v}`),
    },
    {
      title: t('stok.miktar'),
      dataIndex: 'miktar',
      key: 'miktar',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('stok.bakiye_sonrasi'),
      dataIndex: 'bakiye_sonrasi',
      key: 'bakiye_sonrasi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('stok.aciklama'),
      dataIndex: 'aciklama',
      key: 'aciklama',
      render: (v: string) => v || '—',
    },
    {
      title: t('stok.son_hareketler'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      align: 'right',
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM HH:mm')}</span>,
    },
  ];

  if (malzeme.isPending) {
    return (
      <SayfaKapsayici enGenis={1160}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </SayfaKapsayici>
    );
  }

  if (malzeme.isError || !malzeme.data) {
    return (
      <Result
        status="404"
        title={t('stok.bos')}
        extra={
          <Button type="primary" onClick={() => navigate('/malzemeler')}>
            {t('ortak.geri')}
          </Button>
        }
      />
    );
  }

  const m: Malzeme = malzeme.data;

  return (
    <SayfaKapsayici enGenis={1160}>
      <SayfaBaslik
        baslik={
          <Space size={12} align="center" wrap>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/malzemeler')}
              aria-label={t('ortak.geri')}
            />
            <span className="sayisal">{m.kod}</span>
            <span style={{ color: 'var(--metin-soluk)', fontWeight: 400 }}>{m.ad}</span>
            {m.kritik && (
              <Tag color="red" bordered={false}>
                {t('stok.kritik_rozet')}
              </Tag>
            )}
          </Space>
        }
        sag={
          yazabilir && (
            <Space wrap>
              <Button icon={<EditOutlined />} onClick={() => setDuzenleAcik(true)}>
                {t('stok.duzenle')}
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setHareketAcik(true)}>
                {t('stok.hareket_ekle')}
              </Button>
            </Space>
          )
        }
      />

      <Card styles={{ body: { padding: 18 } }} style={{ marginBottom: 16 }}>
        <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
          <Descriptions.Item label={t('stok.mevcut')}>
            <span className="sayisal">
              {m.mevcut_miktar} {m.birim}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label={t('stok.kritik_esik')}>
            <span className="sayisal">{m.kritik_stok}</span>
          </Descriptions.Item>
          <Descriptions.Item label={t('stok.min')}>
            <span className="sayisal">{m.min_stok}</span>
          </Descriptions.Item>
          <Descriptions.Item label={t('stok.max')}>
            <span className="sayisal">{m.max_stok ?? '—'}</span>
          </Descriptions.Item>
          <Descriptions.Item label={t('stok.kategori')}>{m.kategori || '—'}</Descriptions.Item>
          <Descriptions.Item label={t('stok.durum')}>
            <Tag color={m.aktif ? 'green' : 'default'}>
              {m.aktif ? t('stok.aktif') : t('stok.pasif')}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={t('stok.son_hareketler')} styles={{ body: { padding: 18 } }}>
        <SunucuTablo<StokHareketi>
          kolonlar={kolonlar}
          veri={hareketler.data?.veri ?? []}
          meta={hareketler.data?.meta}
          yukleniyor={hareketler.isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          bosMetin={t('stok.bos')}
        />
      </Card>

      <MalzemeFormu acik={duzenleAcik} kapat={() => setDuzenleAcik(false)} malzeme={m} />
      <StokHareketFormu malzeme={hareketAcik ? m : null} kapat={() => setHareketAcik(false)} />
    </SayfaKapsayici>
  );
}
