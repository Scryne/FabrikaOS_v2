/**
 * Satınalma talep listesi — sunucu-taraflı tablo (kod/başlık/durum rozeti) + satır → detay
 * çekmecesi + "yeni talep" formu. Yazma aksiyonları ``satinalma:yaz`` iznine bağlı.
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

import { type SatinalmaTalebi, useTalepler } from './hooks';
import { TalepDurumEtiketi } from './rozetler';
import { SatinalmaTalepDetay } from './SatinalmaTalepDetay';
import { SatinalmaTalepFormu } from './SatinalmaTalepFormu';

export function SatinalmaTalepListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('satinalma:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useTalepler(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<SatinalmaTalebi> = [
    {
      title: t('satinalma.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('satinalma.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    {
      title: t('satinalma.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: string) => <TalepDurumEtiketi durum={d} />,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.satinalma')}
        alt={t('satinalma.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('satinalma.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<SatinalmaTalebi>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('satinalma.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('satinalma.bos')}
          onRow={(kayit) => ({
            onClick: () => setDetayId(kayit.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <SatinalmaTalepDetay id={detayId} kapat={() => setDetayId(null)} />
      <SatinalmaTalepFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
