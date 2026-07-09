/**
 * Duyuru listesi — sunucu-taraflı tablo (kod/başlık/önem/durum) + detay çekmecesi + yeni duyuru.
 * Yazma/yayın ``duyuru:yaz``.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { DurumPim, pimUret } from '@/components/DurumPim';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { type Duyuru, useDuyurular } from './hooks';
import { DuyuruDetay } from './DuyuruDetay';
import { DuyuruFormu } from './DuyuruFormu';

const ONEM_RENK: Record<string, string> = {
  bilgi: RENKLER.cyan,
  uyari: RENKLER.uyari,
  kritik: RENKLER.hata,
};
const OnemPim = pimUret(ONEM_RENK, 'duyuru.onem_');

export function DuyuruListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('duyuru:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useDuyurular(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Duyuru> = [
    {
      title: t('duyuru.kod'),
      dataIndex: 'kod',
      key: 'kod',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('duyuru.baslik'), dataIndex: 'baslik', key: 'baslik' },
    {
      title: t('duyuru.onem'),
      dataIndex: 'onem',
      key: 'onem',
      render: (v: string) => <OnemPim durum={v} />,
    },
    {
      title: t('duyuru.durum'),
      dataIndex: 'yayinda',
      key: 'yayinda',
      render: (v: boolean) => (
        <DurumPim
          renk={v ? RENKLER.basari : RENKLER.metinSoluk}
          etiket={v ? t('duyuru.yayinda') : t('duyuru.taslak')}
          solgun={!v}
        />
      ),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.duyurular')}
        alt={t('duyuru.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('duyuru.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Duyuru>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          bosMetin={isError ? t('ortak.hata_baslik') : t('duyuru.bos')}
          onRow={(kayit) => ({
            onClick: () => setDetayId(kayit.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <DuyuruDetay id={detayId} kapat={() => setDetayId(null)} />
      <DuyuruFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
