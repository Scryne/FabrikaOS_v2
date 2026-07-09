/**
 * Kullanıcılar çalışma alanı — KPI şeridi (toplam/aktif/pasif/rol sayısı; `/kullanicilar/ozet`)
 * + zengin tablo (avatar varlık hücre + rol çipleri + durum pimi) + "yeni kullanıcı"
 * (``kullanici:yaz``). Backend listesi yalnız sayfalama destekler.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  IdcardOutlined,
  PlusOutlined,
  StopOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Card, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { DurumPim } from '@/components/DurumPim';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type Kullanici, useKullaniciOzet, useKullanicilar } from './hooks';
import { KullaniciFormu } from './KullaniciFormu';

const HAT = BOLUM_RENGI['menu.bolum_yonetim'];

function basHarf(ad: string, eposta: string): string {
  const kaynak = ad || eposta;
  return (
    kaynak
      .split(/[\s@.]+/)
      .map((p) => p[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || '?'
  );
}

export function KullaniciListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('kullanici:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useKullanicilar(param);
  const { data: ozet, isPending: ozetYukleniyor } = useKullaniciOzet();
  const [formAcik, setFormAcik] = useState(false);

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'toplam',
          baslik: t('kullanici.kpi_toplam'),
          deger: String(ozet.toplam),
          ikon: <TeamOutlined />,
        },
        {
          anahtar: 'aktif',
          baslik: t('kullanici.kpi_aktif'),
          deger: String(ozet.aktif),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'pasif',
          baslik: t('kullanici.kpi_pasif'),
          deger: String(ozet.pasif),
          ikon: <StopOutlined />,
        },
        {
          anahtar: 'rol',
          baslik: t('kullanici.kpi_rol'),
          deger: String(ozet.rol_sayisi),
          ikon: <IdcardOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Kullanici> = [
    {
      title: t('kullanici.ad_soyad'),
      key: 'kullanici',
      render: (_v: unknown, k: Kullanici) => (
        <span className="varlik-hucre">
          <Avatar
            size={34}
            style={{
              backgroundColor: 'rgba(148,163,184,0.18)',
              color: HAT,
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            {basHarf(k.ad_soyad, k.eposta)}
          </Avatar>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {k.ad_soyad || '—'}
            </span>
            <span className="varlik-alt sayisal">{k.eposta}</span>
          </span>
        </span>
      ),
    },
    {
      title: t('kullanici.roller'),
      dataIndex: 'roller',
      key: 'roller',
      render: (roller: string[]) =>
        roller.length ? (
          <span style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap' }}>
            {roller.map((r) => (
              <Tag key={r} bordered={false}>
                {r}
              </Tag>
            ))}
          </span>
        ) : (
          <span style={{ color: 'var(--metin-soluk)' }}>—</span>
        ),
    },
    {
      title: t('kullanici.durum'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean) => (
        <DurumPim
          renk={aktif ? RENKLER.basari : RENKLER.metinSoluk}
          etiket={aktif ? t('kullanici.aktif') : t('kullanici.pasif')}
          solgun={!aktif}
        />
      ),
    },
  ];

  return (
    <SayfaKapsayici enGenis={1160}>
      <SayfaBaslik
        baslik={t('menu.kullanicilar')}
        alt={t('kullanici.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('kullanici.yeni')}
            </Button>
          )
        }
      />
      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />
      <div style={{ height: 20 }} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Kullanici>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          bosMetin={isError ? t('ortak.hata_baslik') : t('kullanici.bos')}
        />
      </Card>
      <KullaniciFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
