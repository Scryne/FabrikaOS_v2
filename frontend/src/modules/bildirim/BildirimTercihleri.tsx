/**
 * Bildirim tercihleri ekranı — olay türü başına uygulama-içi / e-posta anahtarı (S-VB).
 *
 * Kişisel ayardır (izin gerekmez); anahtar değişimi anında kaydedilir (tek satır upsert).
 * Kayıt yoksa varsayılan: uygulama-içi açık, e-posta kapalı — backend ile aynı sözleşme.
 */

import { useTranslation } from 'react-i18next';
import { BellOutlined } from '@ant-design/icons';
import { Skeleton, Switch, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';

import type { BildirimTercih } from './hooks';
import { useBildirimTercihleri, useTercihGuncelle } from './hooks';

export function BildirimTercihleri() {
  const { t } = useTranslation();
  const tercihler = useBildirimTercihleri();
  const guncelle = useTercihGuncelle();

  const degistir = (kayit: BildirimTercih, alan: 'uygulama_ici' | 'eposta', deger: boolean) => {
    guncelle.mutate([{ ...kayit, [alan]: deger }]);
  };

  const kolonlar: ColumnsType<BildirimTercih> = [
    {
      title: t('bildirim.olay_turu'),
      dataIndex: 'olay_turu',
      render: (olayTuru: string) => (
        <span>
          <span style={{ display: 'block', fontWeight: 600, fontSize: 13 }}>
            {t(`bildirim.olay.${olayTuru.replace('.', '_')}`)}
          </span>
          <span className="sayisal" style={{ fontSize: 11.5, color: 'var(--metin-soluk)' }}>
            {olayTuru}
          </span>
        </span>
      ),
    },
    {
      title: t('bildirim.uygulama_ici'),
      dataIndex: 'uygulama_ici',
      width: 160,
      align: 'center',
      render: (_: boolean, kayit) => (
        <Switch
          size="small"
          checked={kayit.uygulama_ici}
          aria-label={`${kayit.olay_turu} ${t('bildirim.uygulama_ici')}`}
          onChange={(deger) => degistir(kayit, 'uygulama_ici', deger)}
        />
      ),
    },
    {
      title: t('bildirim.eposta'),
      dataIndex: 'eposta',
      width: 160,
      align: 'center',
      render: (_: boolean, kayit) => (
        <Switch
          size="small"
          checked={kayit.eposta}
          aria-label={`${kayit.olay_turu} ${t('bildirim.eposta')}`}
          onChange={(deger) => degistir(kayit, 'eposta', deger)}
        />
      ),
    },
  ];

  return (
    <SayfaKapsayici enGenis={860}>
      <SayfaBaslik baslik={t('bildirim.tercihler')} alt={t('bildirim.tercihler_alt')} />
      <PanelKart baslik={t('bildirim.tercihler')} ikon={<BellOutlined />} govdeDolgu={0}>
        {tercihler.isLoading ? (
          <div style={{ padding: 20 }}>
            <Skeleton active paragraph={{ rows: 6 }} />
          </div>
        ) : (
          <Table<BildirimTercih>
            rowKey="olay_turu"
            columns={kolonlar}
            dataSource={tercihler.data ?? []}
            pagination={false}
            size="middle"
          />
        )}
      </PanelKart>
    </SayfaKapsayici>
  );
}
