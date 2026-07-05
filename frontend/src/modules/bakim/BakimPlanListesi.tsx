/**
 * Bakım planları listesi — sunucu-taraflı tablo (ad/makine/tip/periyot/sonraki bakım/durum) +
 * makine & durum filtresi + "yeni plan" (``bakim:yaz``). Tarihi geçmiş sonraki bakım
 * vurgulanır; yazma yetkisi olan plan durumunu satırdan aktif/pasif değiştirebilir.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Select, Switch, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';

import { BakimPlaniFormu } from './BakimPlaniFormu';
import { type BakimPlani, useBakimPlaniGuncelle, useBakimPlanlari } from './hooks';

const TIP_RENK: Record<string, string> = {
  onleyici: 'blue',
  kestirimci: 'purple',
  periyodik: 'cyan',
};

export function BakimPlanListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('bakim:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useBakimPlanlari(param);
  const { data: makineler } = useMakineSecenekleri();
  const guncelle = useBakimPlaniGuncelle();
  const [formAcik, setFormAcik] = useState(false);

  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);

  const kolonlar: ColumnsType<BakimPlani> = [
    { title: t('bakim.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    {
      title: t('bakim.makine'),
      dataIndex: 'makine_id',
      key: 'makine_id',
      render: (id: number) => {
        const m = makineHarita.get(id);
        return m ? <span className="sayisal">{m.kod}</span> : `#${id}`;
      },
    },
    {
      title: t('bakim.tip'),
      dataIndex: 'tip',
      key: 'tip',
      sorter: true,
      render: (v: string) => <Tag color={TIP_RENK[v]}>{t(`bakim.tip_${v}`, v)}</Tag>,
    },
    {
      title: t('bakim.periyot_gun'),
      dataIndex: 'periyot_gun',
      key: 'periyot_gun',
      align: 'right',
      render: (v: number | null) =>
        v != null ? (
          <span className="sayisal">{v}</span>
        ) : (
          <span style={{ color: 'var(--metin-soluk)' }}>—</span>
        ),
    },
    {
      title: t('bakim.son_bakim'),
      dataIndex: 'son_bakim_tarihi',
      key: 'son_bakim_tarihi',
      render: (v: string | null) =>
        v ? (
          <span className="sayisal">{new Date(v).toLocaleDateString()}</span>
        ) : (
          <span style={{ color: 'var(--metin-soluk)' }}>—</span>
        ),
    },
    {
      title: t('bakim.sonraki_bakim'),
      dataIndex: 'sonraki_bakim_tarihi',
      key: 'sonraki_bakim_tarihi',
      sorter: true,
      render: (v: string | null, kayit) => {
        if (!v) return <span style={{ color: 'var(--metin-soluk)' }}>—</span>;
        const gecikti = kayit.aktif && new Date(v).getTime() < Date.now();
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span className="sayisal">{new Date(v).toLocaleDateString()}</span>
            {gecikti && <Tag color="red">{t('bakim.gecikti')}</Tag>}
          </span>
        );
      },
    },
    {
      title: t('bakim.durum'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean, kayit) =>
        yazabilir ? (
          <Switch
            size="small"
            checked={aktif}
            loading={guncelle.isPending && guncelle.variables?.id === kayit.id}
            onChange={(deger) => guncelle.mutate({ id: kayit.id, govde: { aktif: deger } })}
            aria-label={t('bakim.durum')}
          />
        ) : (
          <Tag color={aktif ? 'green' : 'default'}>
            {aktif ? t('bakim.aktif') : t('bakim.pasif')}
          </Tag>
        ),
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.bakim')}
        alt={t('bakim.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('bakim.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<BakimPlani>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('bakim.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('bakim.bos')}
          araclar={
            <>
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder={t('bakim.makine')}
                style={{ width: 200 }}
                value={param.filtreler?.makine_id as number | undefined}
                onChange={(v) => paramDegistir({ filtreler: { makine_id: v } })}
                options={(makineler ?? []).map((m) => ({ value: m.id, label: m.kod }))}
              />
              <Select
                allowClear
                placeholder={t('bakim.durum')}
                style={{ width: 140 }}
                value={param.filtreler?.aktif as boolean | undefined}
                onChange={(v) => paramDegistir({ filtreler: { aktif: v } })}
                options={[
                  { value: true, label: t('bakim.aktif') },
                  { value: false, label: t('bakim.pasif') },
                ]}
              />
            </>
          }
        />
      </Card>
      <BakimPlaniFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
