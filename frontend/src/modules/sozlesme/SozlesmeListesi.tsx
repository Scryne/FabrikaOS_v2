/**
 * Sözleşme listesi — sunucu-taraflı tablo (kod/başlık/bitiş/tutar/durum) + detay çekmecesi
 * + yeni sözleşme. Yazma ``sozlesme:yaz``.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type Sozlesme, useSozlesmeler } from './hooks';
import { SozlesmeDurumEtiketi } from './rozetler';
import { SozlesmeDetay } from './SozlesmeDetay';
import { SozlesmeFormu } from './SozlesmeFormu';

export function SozlesmeListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('sozlesme:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useSozlesmeler(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Sozlesme> = [
    {
      title: t('sozlesme.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('sozlesme.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    { title: t('sozlesme.bitis'), dataIndex: 'bitis_tarihi', key: 'bitis_tarihi', sorter: true },
    {
      title: t('sozlesme.tutar'),
      dataIndex: 'tutar',
      key: 'tutar',
      align: 'right',
      render: (v: number, k) => (
        <span className="sayisal">
          {v} {k.para_birimi}
        </span>
      ),
    },
    {
      title: t('sozlesme.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: string) => <SozlesmeDurumEtiketi durum={d} />,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.sozlesmeler')}
        alt={t('sozlesme.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('sozlesme.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Sozlesme>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('sozlesme.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('sozlesme.bos')}
          onRow={(kayit) => ({
            onClick: () => setDetayId(kayit.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <SozlesmeDetay id={detayId} kapat={() => setDetayId(null)} />
      <SozlesmeFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
