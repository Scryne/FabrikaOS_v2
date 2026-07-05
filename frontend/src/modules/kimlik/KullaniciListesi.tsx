/**
 * Kullanıcı listesi — tenant kullanıcıları + rol rozetleri + "yeni kullanıcı"
 * (``kullanici:yaz``). Backend listesi yalnız sayfalama destekler (arama/sıralama yok).
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

import { type Kullanici, useKullanicilar } from './hooks';
import { KullaniciFormu } from './KullaniciFormu';

export function KullaniciListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('kullanici:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useKullanicilar(param);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Kullanici> = [
    {
      title: t('kullanici.eposta'),
      dataIndex: 'eposta',
      key: 'eposta',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('kullanici.ad_soyad'), dataIndex: 'ad_soyad', key: 'ad_soyad' },
    {
      title: t('kullanici.roller'),
      dataIndex: 'roller',
      key: 'roller',
      render: (roller: string[]) =>
        roller.length ? (
          <span style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap' }}>
            {roller.map((r) => (
              <Tag key={r}>{r}</Tag>
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
        <Tag color={aktif ? 'green' : 'default'}>
          {aktif ? t('kullanici.aktif') : t('kullanici.pasif')}
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1100 }}>
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
    </div>
  );
}
