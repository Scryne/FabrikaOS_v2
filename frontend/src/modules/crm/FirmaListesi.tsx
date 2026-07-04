/**
 * Firma listesi — sunucu-taraflı tablo (ad/tip/sektör/il) + satır → detay çekmecesi + yeni firma
 * formu. Yazma aksiyonları ``crm:yaz`` iznine bağlı.
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

import { FirmaDetay } from './FirmaDetay';
import { FirmaFormu } from './FirmaFormu';
import { type Firma, useFirmalar } from './hooks';
import { FirmaTipEtiketi } from './rozetler';

export function FirmaListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('crm:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useFirmalar(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Firma> = [
    { title: t('crm.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    {
      title: t('crm.tip'),
      dataIndex: 'tip',
      key: 'tip',
      render: (v: string) => <FirmaTipEtiketi tip={v} />,
    },
    { title: t('crm.sektor'), dataIndex: 'sektor', key: 'sektor', sorter: true },
    { title: t('crm.il'), dataIndex: 'il', key: 'il' },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.firmalar')}
        alt={t('crm.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('crm.yeni_firma')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Firma>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('crm.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('crm.bos')}
          onRow={(kayit) => ({
            onClick: () => setDetayId(kayit.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <FirmaDetay id={detayId} kapat={() => setDetayId(null)} />
      <FirmaFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
