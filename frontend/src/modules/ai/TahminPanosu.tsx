/**
 * AI Tahminleri ekranı — tür başına model durum kartları (Eğit aksiyonu `ai:egit`) +
 * dört çıkarım sekmesi: kestirimci bakım riski, anomali taraması, OEE ufuk tahmini,
 * stok kalan gün. Aktif model yoksa sekme eğitime yönlendirir (404 beklenen durumdur).
 */

import { useState } from 'react';
import type { TFunction } from 'i18next';
import { useTranslation } from 'react-i18next';
import {
  AlertOutlined,
  ExperimentOutlined,
  FundProjectionScreenOutlined,
  GoldOutlined,
  SmileOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { Button, Card, Col, Row, Select, Skeleton, Table, Tabs, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { EGrafik } from '@/components/grafik/EGrafik';
import { cizgiSecenek } from '@/components/grafik/grafikSecenek';
import { useAuthStore } from '@/store/authStore';

import { modelYok, useEgit, useModeller, useTahmin } from './hooks';
import {
  type AnomaliSonuc,
  type BakimSonuc,
  DURUM_RENK,
  kalanGunRenk,
  type ModelKaydi,
  MODEL_TURLERI,
  type ModelTuru,
  type OeeSonuc,
  SEVIYE_RENK,
  sonModeller,
  type StokSonuc,
  type TahminCevap,
} from './sunum';

const TUR_IKONU: Record<ModelTuru, React.ReactNode> = {
  kestirimci_bakim: <ToolOutlined />,
  anomali: <AlertOutlined />,
  oee: <FundProjectionScreenOutlined />,
  stok: <GoldOutlined />,
};

function yuzde(deger: number): string {
  return `%${(deger * 100).toFixed(1)}`;
}

/** Model kartındaki tek satırlık metrik özeti (türe göre anlamlı metrik). */
function metrikOzet(kayit: ModelKaydi, t: TFunction): string | null {
  const m = kayit.metrikler;
  if (!m) return null;
  const n = typeof m.satir_sayisi === 'number' ? m.satir_sayisi : null;
  const parcalar: string[] = [];
  if (n !== null) parcalar.push(t('ai.gozlem_n', { n }));
  if (typeof m.dogruluk === 'number')
    parcalar.push(`${t('ai.metrik_dogruluk')} ${yuzde(m.dogruluk)}`);
  if (typeof m.r2 === 'number') parcalar.push(`R² ${m.r2}`);
  if (typeof m.malzeme_sayisi === 'number')
    parcalar.push(t('ai.malzeme_n', { n: m.malzeme_sayisi }));
  return parcalar.join(' · ') || null;
}

function ModelKarti({
  tur,
  kayit,
  egitAksiyon,
}: {
  tur: ModelTuru;
  kayit?: ModelKaydi;
  egitAksiyon: React.ReactNode;
}) {
  const { t } = useTranslation();
  const durum = kayit?.durum;
  return (
    <Card size="small" className="model-karti" styles={{ body: { padding: 14 } }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span className="ikon-plaka" style={{ ['--plaka-renk' as string]: 'var(--hat-zeka)' }}>
          {TUR_IKONU[tur]}
        </span>
        <span style={{ fontWeight: 600 }}>{t(`ai.tur_${tur}`)}</span>
        <Tag
          bordered={false}
          color={durum ? (DURUM_RENK[durum] ?? 'default') : 'default'}
          style={{ marginLeft: 'auto', marginInlineEnd: 0 }}
        >
          {durum ? t(`ai.durum_${durum}`) : t('ai.durum_yok')}
        </Tag>
      </div>
      <div style={{ minHeight: 40, color: 'var(--metin-soluk)', fontSize: 12 }}>
        {kayit ? (
          <>
            <div>
              <span className="sayisal">v{kayit.surum}</span>
              {' · '}
              {new Date(kayit.olusturma_tarihi).toLocaleString()}
            </div>
            {durum === 'basarisiz' ? (
              <Typography.Text
                type="danger"
                style={{ fontSize: 12 }}
                ellipsis={{ tooltip: kayit.hata }}
              >
                {kayit.hata}
              </Typography.Text>
            ) : (
              <div>{metrikOzet(kayit, t)}</div>
            )}
          </>
        ) : (
          t('ai.model_yok')
        )}
      </div>
      <div style={{ marginTop: 10 }}>{egitAksiyon}</div>
    </Card>
  );
}

/** Panel kabuğu: yükleniyor / model yok (404) / hata / içerik. */
function PanelKabuk({
  sorgu,
  egitAksiyon,
  cocuk,
}: {
  sorgu: ReturnType<typeof useTahmin>;
  egitAksiyon: React.ReactNode;
  cocuk: (veri: TahminCevap) => React.ReactNode;
}) {
  const { t } = useTranslation();
  if (sorgu.isPending) return <Skeleton active paragraph={{ rows: 4 }} />;
  if (sorgu.isError) {
    if (modelYok(sorgu.error))
      return (
        <BosDurum
          ikon={<ExperimentOutlined />}
          baslik={t('ai.model_yok_baslik')}
          aciklama={t('ai.model_yok')}
          aksiyon={egitAksiyon}
        />
      );
    return <BosDurum baslik={t('ortak.hata_baslik')} aciklama={String(sorgu.error.message)} />;
  }
  return (
    <>
      {cocuk(sorgu.data)}
      <div style={{ marginTop: 10, color: 'var(--metin-soluk)', fontSize: 12 }}>
        {t('ai.tahmin_kunyesi', {
          surum: sorgu.data.model_surum,
          zaman: new Date(sorgu.data.zaman).toLocaleString(),
        })}
      </div>
    </>
  );
}

function BakimPaneli({ egitAksiyon }: { egitAksiyon: React.ReactNode }) {
  const { t } = useTranslation();
  const sorgu = useTahmin('kestirimci_bakim');
  const kolonlar: ColumnsType<BakimSonuc> = [
    {
      title: t('ai.makine'),
      dataIndex: 'makine_kod',
      key: 'makine_kod',
      render: (v: string, s) => <span className="sayisal">{v || `#${s.makine_id}`}</span>,
    },
    {
      title: t('ai.risk'),
      dataIndex: 'risk_skoru',
      key: 'risk_skoru',
      align: 'right',
      render: (v: number) => <span className="sayisal">{yuzde(v)}</span>,
    },
    {
      title: t('ai.seviye'),
      dataIndex: 'seviye',
      key: 'seviye',
      render: (v: string) => (
        <Tag color={SEVIYE_RENK[v] ?? 'default'} bordered={false}>
          {t(`ai.seviye_${v}`)}
        </Tag>
      ),
    },
    { title: t('ai.veri_gunu'), dataIndex: 'veri_gunu', key: 'veri_gunu' },
  ];
  return (
    <PanelKabuk
      sorgu={sorgu}
      egitAksiyon={egitAksiyon}
      cocuk={(veri) => (
        <Table<BakimSonuc>
          rowKey="makine_id"
          size="small"
          pagination={false}
          dataSource={veri.sonuclar as BakimSonuc[]}
          columns={kolonlar}
          locale={{ emptyText: <BosDurum baslik={t('ai.sonuc_yok')} /> }}
        />
      )}
    />
  );
}

function AnomaliPaneli({ egitAksiyon }: { egitAksiyon: React.ReactNode }) {
  const { t } = useTranslation();
  const sorgu = useTahmin('anomali');
  const kolonlar: ColumnsType<AnomaliSonuc> = [
    {
      title: t('ai.makine'),
      dataIndex: 'makine_kod',
      key: 'makine_kod',
      render: (v: string, s) => <span className="sayisal">{v || `#${s.makine_id}`}</span>,
    },
    { title: t('ai.gun'), dataIndex: 'gun', key: 'gun' },
    {
      title: t('ai.skor'),
      dataIndex: 'skor',
      key: 'skor',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v.toFixed(4)}</span>,
    },
    {
      title: t('ai.durus'),
      dataIndex: 'durus_orani',
      key: 'durus_orani',
      align: 'right',
      render: (v: number) => <span className="sayisal">{yuzde(v)}</span>,
    },
    {
      title: t('ai.fire'),
      dataIndex: 'fire_orani',
      key: 'fire_orani',
      align: 'right',
      render: (v: number) => <span className="sayisal">{yuzde(v)}</span>,
    },
    {
      title: t('ai.performans'),
      dataIndex: 'performans',
      key: 'performans',
      align: 'right',
      render: (v: number) => <span className="sayisal">{yuzde(v)}</span>,
    },
  ];
  return (
    <PanelKabuk
      sorgu={sorgu}
      egitAksiyon={egitAksiyon}
      cocuk={(veri) => {
        const sonuclar = veri.sonuclar as AnomaliSonuc[];
        if (sonuclar.length === 0)
          return (
            <BosDurum
              ikon={<SmileOutlined />}
              baslik={t('ai.anomali_yok_baslik')}
              aciklama={t('ai.anomali_yok')}
            />
          );
        return (
          <Table<AnomaliSonuc>
            rowKey={(s) => `${s.makine_id}-${s.gun}`}
            size="small"
            pagination={false}
            dataSource={sonuclar}
            columns={kolonlar}
          />
        );
      }}
    />
  );
}

function OeePaneli({ egitAksiyon }: { egitAksiyon: React.ReactNode }) {
  const { t } = useTranslation();
  const sorgu = useTahmin('oee');
  const [secili, setSecili] = useState<number>();
  return (
    <PanelKabuk
      sorgu={sorgu}
      egitAksiyon={egitAksiyon}
      cocuk={(veri) => {
        const sonuclar = veri.sonuclar as OeeSonuc[];
        const ilk = sonuclar[0];
        if (!ilk) return <BosDurum baslik={t('ai.sonuc_yok')} />;
        const aktifId = secili ?? ilk.makine_id;
        const makine = sonuclar.find((s) => s.makine_id === aktifId) ?? ilk;
        const grafikVeri = makine.tahminler.map((p) => ({
          zaman: p.gun.slice(5), // AA-GG
          deger: Math.round(p.oee * 1000) / 10,
        }));
        return (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>{t('ai.makine')}</span>
              <Select
                size="small"
                style={{ minWidth: 160 }}
                value={aktifId}
                onChange={setSecili}
                options={sonuclar.map((s) => ({
                  value: s.makine_id,
                  label: s.makine_kod || `#${s.makine_id}`,
                }))}
              />
              <span style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>
                {t('ai.oee_grafik_alt')}
              </span>
            </div>
            <EGrafik secenek={cizgiSecenek(grafikVeri)} yukseklik={260} />
          </>
        );
      }}
    />
  );
}

function StokPaneli({ egitAksiyon }: { egitAksiyon: React.ReactNode }) {
  const { t } = useTranslation();
  const sorgu = useTahmin('stok');
  const kolonlar: ColumnsType<StokSonuc> = [
    {
      title: t('ai.malzeme'),
      dataIndex: 'kod',
      key: 'kod',
      render: (v: string, s) => (
        <>
          <span className="sayisal">{v}</span>
          <span style={{ color: 'var(--metin-soluk)', marginLeft: 8 }}>{s.ad}</span>
        </>
      ),
    },
    {
      title: t('ai.mevcut'),
      dataIndex: 'mevcut_miktar',
      key: 'mevcut_miktar',
      align: 'right',
      render: (v: number, s) => <span className="sayisal">{`${v} ${s.birim}`}</span>,
    },
    {
      title: t('ai.gunluk_tuketim'),
      dataIndex: 'gunluk_tuketim',
      key: 'gunluk_tuketim',
      align: 'right',
      render: (v: number, s) => <span className="sayisal">{`${v} ${s.birim}`}</span>,
    },
    {
      title: t('ai.kalan_gun'),
      dataIndex: 'kalan_gun',
      key: 'kalan_gun',
      align: 'right',
      render: (v: number) => (
        <Tag color={kalanGunRenk(v)} bordered={false}>
          {t('ai.kalan_gun_deger', { gun: v })}
        </Tag>
      ),
    },
    {
      title: t('ai.onerilen'),
      dataIndex: 'onerilen_siparis',
      key: 'onerilen_siparis',
      align: 'right',
      render: (v: number, s) => <span className="sayisal">{v > 0 ? `${v} ${s.birim}` : '—'}</span>,
    },
  ];
  return (
    <PanelKabuk
      sorgu={sorgu}
      egitAksiyon={egitAksiyon}
      cocuk={(veri) => (
        <Table<StokSonuc>
          rowKey="malzeme_id"
          size="small"
          pagination={false}
          dataSource={veri.sonuclar as StokSonuc[]}
          columns={kolonlar}
          locale={{ emptyText: <BosDurum baslik={t('ai.sonuc_yok')} /> }}
        />
      )}
    />
  );
}

export function TahminPanosu() {
  const { t } = useTranslation();
  const egitebilir = useAuthStore((s) => s.izinVar('ai:egit'));
  const modeller = useModeller();
  const egit = useEgit();
  const sonlar = sonModeller(modeller.data ?? []);

  const egitButonu = (tur: ModelTuru, birincil = false) => {
    if (!egitebilir) return null;
    const kayit = sonlar[tur];
    const egitiliyor = kayit?.durum === 'egitiliyor';
    return (
      <Button
        size="small"
        type={birincil ? 'primary' : 'default'}
        icon={<ExperimentOutlined />}
        loading={egitiliyor || (egit.isPending && egit.variables === tur)}
        onClick={() => egit.mutate(tur)}
      >
        {kayit?.durum === 'hazir' ? t('ai.yeniden_egit') : t('ai.egit')}
      </Button>
    );
  };

  const paneller = [
    {
      key: 'kestirimci_bakim',
      label: t('ai.tur_kestirimci_bakim'),
      children: <BakimPaneli egitAksiyon={egitButonu('kestirimci_bakim', true)} />,
    },
    {
      key: 'anomali',
      label: t('ai.tur_anomali'),
      children: <AnomaliPaneli egitAksiyon={egitButonu('anomali', true)} />,
    },
    {
      key: 'oee',
      label: t('ai.tur_oee'),
      children: <OeePaneli egitAksiyon={egitButonu('oee', true)} />,
    },
    {
      key: 'stok',
      label: t('ai.tur_stok'),
      children: <StokPaneli egitAksiyon={egitButonu('stok', true)} />,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik baslik={t('menu.tahminler')} alt={t('ai.alt')} />
      <Row gutter={[16, 16]}>
        {MODEL_TURLERI.map((tur) => (
          <Col xs={24} sm={12} xl={6} key={tur}>
            <ModelKarti tur={tur} kayit={sonlar[tur]} egitAksiyon={egitButonu(tur)} />
          </Col>
        ))}
      </Row>
      <Card style={{ marginTop: 16 }} styles={{ body: { padding: 16 } }}>
        <Tabs items={paneller} />
      </Card>
    </div>
  );
}
