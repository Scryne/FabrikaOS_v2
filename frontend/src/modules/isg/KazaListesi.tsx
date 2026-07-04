/**
 * İş kazası listesi — sunucu-taraflı tablo (kod/tür rozeti/ağırlık/olay tarihi/kayıp gün) +
 * "yeni kayıt" (``isg:yaz``) + tür filtresi. Kayıtlar salt-liste.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type IsKazasi, useKazalar } from './hooks';
import { KazaFormu } from './KazaFormu';
import { AgirlikEtiketi, KazaTurEtiketi } from './rozetler';

const TURLER = ['kaza', 'ramak_kala', 'meslek_hastaligi'];

export function KazaListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useKazalar(param);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<IsKazasi> = [
    {
      title: t('isg.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('isg.tur'),
      dataIndex: 'tur',
      key: 'tur',
      render: (v: string) => <KazaTurEtiketi tur={v} />,
    },
    {
      title: t('isg.agirlik'),
      dataIndex: 'agirlik',
      key: 'agirlik',
      sorter: true,
      render: (v: string) => <AgirlikEtiketi agirlik={v} />,
    },
    {
      title: t('isg.yer'),
      dataIndex: 'yer',
      key: 'yer',
    },
    {
      title: t('isg.olay_tarihi'),
      dataIndex: 'olay_tarihi',
      key: 'olay_tarihi',
      sorter: true,
      render: (v: string) => <span className="sayisal">{new Date(v).toLocaleString()}</span>,
    },
    {
      title: t('isg.kaybedilen_gun'),
      dataIndex: 'kaybedilen_gun',
      key: 'kaybedilen_gun',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.is_kazalari')}
        alt={t('isg.kaza_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('isg.kaza_yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<IsKazasi>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('isg.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('isg.kaza_bos')}
          araclar={
            <Select
              allowClear
              placeholder={t('isg.tur')}
              style={{ width: 180 }}
              value={param.filtreler?.tur as string | undefined}
              onChange={(v) => paramDegistir({ filtreler: { tur: v } })}
              options={TURLER.map((x) => ({ value: x, label: t(`isg.tur_${x}`) }))}
            />
          }
        />
      </Card>
      <KazaFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
