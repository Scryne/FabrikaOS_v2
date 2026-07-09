/**
 * Firma listesi — sunucu-taraflı tablo (ad/tip/sektör/il) + satır → detay çekmecesi + yeni firma
 * formu. Yazma aksiyonları ``crm:yaz`` iznine bağlı.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BankOutlined,
  CheckCircleOutlined,
  FileProtectOutlined,
  InboxOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Card } from 'antd';
import type { CSSProperties } from 'react';
import type { ColumnsType } from 'antd/es/table';

import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useTicariOzet } from '@/modules/ticari/hooks';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { FirmaDetay } from './FirmaDetay';
import { FirmaFormu } from './FirmaFormu';
import { type Firma, useFirmalar } from './hooks';
import { FirmaTipEtiketi } from './rozetler';

const HAT = BOLUM_RENGI['menu.bolum_ticari'];

export function FirmaListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('crm:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useFirmalar(param);
  const { data: ozet, isPending: ozetYukleniyor } = useTicariOzet();
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const s = ozet?.sayaclar;
  const metrikler: OzetMetrik[] = s
    ? [
        {
          anahtar: 'firma',
          baslik: t('crm.kpi_firma'),
          deger: String(s.firma_sayisi),
          ikon: <BankOutlined />,
        },
        {
          anahtar: 'aktif',
          baslik: t('crm.kpi_aktif'),
          deger: String(s.aktif_firma),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'sozlesme',
          baslik: t('crm.kpi_sozlesme'),
          deger: String(s.aktif_sozlesme),
          ikon: <FileProtectOutlined />,
        },
        {
          anahtar: 'talep',
          baslik: t('crm.kpi_talep'),
          deger: String(s.acik_talep),
          ikon: <InboxOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Firma> = [
    {
      title: t('crm.ad'),
      key: 'ad',
      sorter: true,
      render: (_v: unknown, f: Firma) => (
        <span className="varlik-hucre">
          <span
            className="ikon-plaka kucuk"
            aria-hidden="true"
            style={{ '--plaka-renk': HAT } as CSSProperties}
          >
            <BankOutlined />
          </span>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {f.ad}
            </span>
            {f.sektor && <span className="varlik-alt">{f.sektor}</span>}
          </span>
        </span>
      ),
    },
    {
      title: t('crm.tip'),
      dataIndex: 'tip',
      key: 'tip',
      render: (v: string) => <FirmaTipEtiketi tip={v} />,
    },
    { title: t('crm.il'), dataIndex: 'il', key: 'il' },
  ];

  return (
    <SayfaKapsayici>
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
      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />
      <div style={{ height: 20 }} />
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
    </SayfaKapsayici>
  );
}
