/**
 * Reçete (BOM) düzenleme çekmecesi — kalem listesi yerelde düzenlenir, "Kaydet"
 * **replace-all** PUT atar (backend mükerrer malzemeyi 422 ile reddeder; burada da
 * seçenek listesinden eklenmiş malzemeler düşürülerek yapısal önlenir).
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Drawer, Empty, InputNumber, Select, Space, Table, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { useAuthStore } from '@/store/authStore';

import { type Urun, useMalzemeSecenekleri, useRecete, useReceteKaydet } from './hooks';

type KalemSatiri = {
  malzeme_id: number;
  malzeme_kod: string;
  malzeme_ad: string;
  birim: string;
  miktar: number;
};

export function ReceteCekmecesi({ urun, kapat }: { urun: Urun | null; kapat: () => void }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));
  // Kalem ekleme seçenekleri stok:oku ister; kayıtlı kalem adları reçete cevabından gelir.
  const stokOku = useAuthStore((s) => s.izinVar('stok:oku'));
  const urunId = urun?.id ?? 0;
  const { data: recete, isPending } = useRecete(urunId);
  const { data: malzemeler } = useMalzemeSecenekleri(stokOku && urun !== null);
  const kaydet = useReceteKaydet();

  const [kalemler, setKalemler] = useState<KalemSatiri[]>([]);
  const [seciliMalzeme, setSeciliMalzeme] = useState<number | undefined>();

  // Sunucudaki reçete yüklendiğinde yerel düzenleme durumunu eşitle.
  useEffect(() => {
    setKalemler(
      (recete?.kalemler ?? []).map((k) => ({
        malzeme_id: k.malzeme_id,
        malzeme_kod: k.malzeme_kod,
        malzeme_ad: k.malzeme_ad,
        birim: k.birim,
        miktar: k.miktar,
      })),
    );
  }, [recete]);

  const eklenebilir = (malzemeler ?? []).filter(
    (m) => !kalemler.some((k) => k.malzeme_id === m.id),
  );

  const ekle = () => {
    const m = (malzemeler ?? []).find((x) => x.id === seciliMalzeme);
    if (!m) return;
    setKalemler((eski) => [
      ...eski,
      { malzeme_id: m.id, malzeme_kod: m.kod, malzeme_ad: m.ad, birim: m.birim, miktar: 1 },
    ]);
    setSeciliMalzeme(undefined);
  };

  const gonder = async () => {
    await kaydet.mutateAsync({
      urunId,
      govde: {
        ad: recete?.ad ?? '',
        kalemler: kalemler.map((k) => ({ malzeme_id: k.malzeme_id, miktar: String(k.miktar) })),
      },
    });
    kapat();
  };

  const kolonlar: ColumnsType<KalemSatiri> = [
    {
      title: t('urun.malzeme'),
      key: 'malzeme',
      render: (_, k) => (
        <span>
          <span className="sayisal">{k.malzeme_kod}</span>
          <span style={{ color: 'var(--metin-soluk)' }}> · {k.malzeme_ad}</span>
        </span>
      ),
    },
    {
      title: t('urun.miktar_birim'),
      key: 'miktar',
      width: 170,
      render: (_, k) =>
        yazabilir ? (
          <Space size={8}>
            <InputNumber
              size="small"
              min={0.001}
              step={0.5}
              value={k.miktar}
              onChange={(v) =>
                setKalemler((eski) =>
                  eski.map((x) =>
                    x.malzeme_id === k.malzeme_id ? { ...x, miktar: Number(v) || 0 } : x,
                  ),
                )
              }
              aria-label={t('urun.miktar')}
            />
            <span style={{ color: 'var(--metin-soluk)' }}>{k.birim}</span>
          </Space>
        ) : (
          <span className="sayisal">
            {k.miktar} {k.birim}
          </span>
        ),
    },
    ...(yazabilir
      ? [
          {
            key: 'sil',
            width: 48,
            render: (_: unknown, k: KalemSatiri) => (
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                aria-label={t('ortak.sil')}
                onClick={() =>
                  setKalemler((eski) => eski.filter((x) => x.malzeme_id !== k.malzeme_id))
                }
              />
            ),
          } as ColumnsType<KalemSatiri>[number],
        ]
      : []),
  ];

  return (
    <Drawer
      open={urun !== null}
      onClose={kapat}
      width={560}
      title={
        urun ? (
          <span>
            {t('urun.recete_baslik')} — <span className="sayisal">{urun.kod}</span>
          </span>
        ) : (
          ''
        )
      }
      destroyOnHidden
      extra={
        yazabilir && (
          <Button type="primary" loading={kaydet.isPending} onClick={() => void gonder()}>
            {t('ortak.kaydet')}
          </Button>
        )
      }
    >
      <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
        {t('urun.recete_ipucu', { birim: urun?.birim ?? '' })}
      </Typography.Paragraph>

      {yazabilir && (
        <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={t('urun.malzeme_sec')}
            style={{ flex: 1 }}
            value={seciliMalzeme}
            onChange={setSeciliMalzeme}
            options={eklenebilir.map((m) => ({ value: m.id, label: `${m.kod} · ${m.ad}` }))}
          />
          <Button icon={<PlusOutlined />} disabled={seciliMalzeme === undefined} onClick={ekle}>
            {t('urun.kalem_ekle')}
          </Button>
        </Space.Compact>
      )}

      <Table<KalemSatiri>
        size="small"
        rowKey="malzeme_id"
        pagination={false}
        loading={isPending && urunId > 0}
        dataSource={kalemler}
        columns={kolonlar}
        locale={{
          emptyText: (
            <Empty description={t('urun.recete_bos')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ),
        }}
      />
    </Drawer>
  );
}
