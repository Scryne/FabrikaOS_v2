/**
 * Belge listesi — sunucu-taraflı tablo (kod/ad/kategori/güncel sürüm) + detay çekmecesi
 * (sürüm yükle/indir) + yeni belge. Yazma ``dys:yaz``.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AppstoreOutlined,
  CloudUploadOutlined,
  DatabaseOutlined,
  FolderOpenOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Card, Tag } from 'antd';
import type { CSSProperties } from 'react';
import type { ColumnsType } from 'antd/es/table';

import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { type Belge, useBelgeler, useDysOzet } from './hooks';
import { BelgeDetay } from './BelgeDetay';
import { BelgeFormu } from './BelgeFormu';

const HAT = BOLUM_RENGI['menu.bolum_dokuman'];

/** Bayt → okunur boyut (KB/MB). */
function boyutMetni(bayt: number): string {
  if (bayt >= 1024 * 1024) return `${(bayt / (1024 * 1024)).toFixed(1)} MB`;
  if (bayt >= 1024) return `${Math.round(bayt / 1024)} KB`;
  return `${bayt} B`;
}

export function BelgeListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('dys:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useBelgeler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useDysOzet();
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'belge',
          baslik: t('dys.kpi_belge'),
          deger: String(ozet.toplam_belge),
          ikon: <FolderOpenOutlined />,
        },
        {
          anahtar: 'kategori',
          baslik: t('dys.kpi_kategori'),
          deger: String(ozet.kategori_sayisi),
          ikon: <AppstoreOutlined />,
        },
        {
          anahtar: 'surum',
          baslik: t('dys.kpi_surum'),
          deger: String(ozet.bu_ay_surum),
          ikon: <CloudUploadOutlined />,
        },
        {
          anahtar: 'boyut',
          baslik: t('dys.kpi_boyut'),
          deger: boyutMetni(ozet.toplam_boyut),
          ikon: <DatabaseOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Belge> = [
    {
      title: t('dys.ad'),
      key: 'ad',
      sorter: true,
      render: (_v: unknown, b: Belge) => (
        <span className="varlik-hucre">
          <span
            className="ikon-plaka kucuk"
            aria-hidden="true"
            style={{ '--plaka-renk': HAT } as CSSProperties}
          >
            <FolderOpenOutlined />
          </span>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {b.ad}
            </span>
            <span className="varlik-alt sayisal">{b.kod}</span>
          </span>
        </span>
      ),
    },
    { title: t('dys.kategori'), dataIndex: 'kategori', key: 'kategori', sorter: true },
    {
      title: t('dys.guncel_surum'),
      dataIndex: 'guncel_surum',
      key: 'guncel_surum',
      align: 'right',
      render: (v: number) => (
        <Tag bordered={false} color={v > 0 ? 'blue' : 'default'}>
          v{v}
        </Tag>
      ),
    },
  ];

  return (
    <SayfaKapsayici>
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
      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />
      <div style={{ height: 20 }} />
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
    </SayfaKapsayici>
  );
}
