/**
 * Belge listesi — sunucu-taraflı tablo (kod/ad/kategori/güncel sürüm) + detay çekmecesi
 * (sürüm yükle/indir) + yeni belge. Yazma ``dys:yaz``.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type Belge, useBelgeler } from './hooks';
import { BelgeDetay } from './BelgeDetay';
import { BelgeFormu } from './BelgeFormu';

export function BelgeListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('dys:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useBelgeler(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Belge> = [
    {
      title: t('dys.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('dys.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    { title: t('dys.kategori'), dataIndex: 'kategori', key: 'kategori', sorter: true },
    {
      title: t('dys.guncel_surum'),
      dataIndex: 'guncel_surum',
      key: 'guncel_surum',
      align: 'right',
      render: (v: number) => <Tag bordered={false}>v{v}</Tag>,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.belgeler')}
        alt={t('dys.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('dys.yeni_belge')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Belge>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('dys.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('dys.bos')}
          onRow={(kayit) => ({
            onClick: () => setDetayId(kayit.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <BelgeDetay id={detayId} kapat={() => setDetayId(null)} />
      <BelgeFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
