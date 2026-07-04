/**
 * Talep listesi — sunucu-taraflı tablo (kod/başlık/öncelik/durum) + detay çekmecesi + yeni talep.
 * Yazma ``talep:yaz``.
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

import { type Talep, useTalepler } from './hooks';
import { TalepDurumEtiketi, TalepOncelikEtiketi } from './rozetler';
import { TalepDetay } from './TalepDetay';
import { TalepFormu } from './TalepFormu';

export function TalepListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('talep:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useTalepler(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Talep> = [
    {
      title: t('talep.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('talep.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    {
      title: t('talep.oncelik'),
      dataIndex: 'oncelik',
      key: 'oncelik',
      sorter: true,
      render: (v: string) => <TalepOncelikEtiketi oncelik={v} />,
    },
    {
      title: t('talep.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: string) => <TalepDurumEtiketi durum={d} />,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.talepler')}
        alt={t('talep.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('talep.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Talep>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('talep.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('talep.bos')}
          onRow={(kayit) => ({
            onClick: () => setDetayId(kayit.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <TalepDetay id={detayId} kapat={() => setDetayId(null)} />
      <TalepFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
