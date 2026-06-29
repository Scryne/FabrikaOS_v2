/**
 * Pano (dashboard) — referans desenler: KPI kart sırası + OEE donut + üretim trendi + tablo.
 *
 * NOT: Veriler şimdilik **statik demo**'dur (başlıkta "Demo veri" rozetiyle işaretli). Gerçek
 * backend verisi + etkileşimli grafikler (ECharts) S6 sprint'inde bağlanacak.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DownloadOutlined } from '@ant-design/icons';
import { Button, Card, Col, Row, Segmented, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { Donut } from '@/components/grafik/Donut';
import { SutunGrafik } from '@/components/grafik/SutunGrafik';
import { KpiKart } from '@/components/KpiKart';
import { RENKLER } from '@/tema/tema';
import { useAuthStore } from '@/store/authStore';

type UretimSatiri = {
  id: number;
  makine: string;
  vardiya: string;
  adet: number;
  oee: number;
  durum: 'calisiyor' | 'durdu' | 'bakimda';
};

const SATIRLAR: UretimSatiri[] = [
  {
    id: 1,
    makine: 'MAK-A1 · Pres Hattı',
    vardiya: 'Gündüz',
    adet: 1240,
    oee: 87,
    durum: 'calisiyor',
  },
  {
    id: 2,
    makine: 'MAK-B2 · Enjeksiyon',
    vardiya: 'Gündüz',
    adet: 980,
    oee: 79,
    durum: 'calisiyor',
  },
  { id: 3, makine: 'MAK-C1 · CNC Freze', vardiya: 'Gece', adet: 0, oee: 0, durum: 'durdu' },
  { id: 4, makine: 'MAK-D3 · Montaj', vardiya: 'Gündüz', adet: 1520, oee: 91, durum: 'calisiyor' },
  { id: 5, makine: 'MAK-E2 · Kaynak', vardiya: 'Gece', adet: 430, oee: 64, durum: 'bakimda' },
];

const TREND = [
  { etiket: 'Oca', deger: 28 },
  { etiket: 'Şub', deger: 35 },
  { etiket: 'Mar', deger: 45 },
  { etiket: 'Nis', deger: 38 },
  { etiket: 'May', deger: 30 },
  { etiket: 'Haz', deger: 42 },
  { etiket: 'Tem', deger: 51 },
  { etiket: 'Ağu', deger: 47 },
  { etiket: 'Eyl', deger: 39 },
];

function oeeRenk(oee: number): string {
  if (oee >= 85) return 'var(--basari)';
  if (oee >= 70) return 'var(--uyari)';
  return 'var(--hata)';
}

export function PanoSayfasi() {
  const { t } = useTranslation();
  const kullanici = useAuthStore((s) => s.kullanici);
  const [donem, setDonem] = useState('ay');

  const durumStil: Record<UretimSatiri['durum'], { renk: string; etiket: string }> = {
    calisiyor: { renk: 'var(--basari)', etiket: t('pano.durum_calisiyor') },
    durdu: { renk: 'var(--metin-soluk)', etiket: t('pano.durum_durdu') },
    bakimda: { renk: 'var(--uyari)', etiket: t('pano.durum_bakimda') },
  };

  const kolonlar: ColumnsType<UretimSatiri> = [
    { title: t('pano.t_makine'), dataIndex: 'makine', key: 'makine' },
    { title: t('pano.t_vardiya'), dataIndex: 'vardiya', key: 'vardiya' },
    {
      title: t('pano.t_adet'),
      dataIndex: 'adet',
      key: 'adet',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v.toLocaleString('tr-TR')}</span>,
    },
    {
      title: t('pano.t_oee'),
      dataIndex: 'oee',
      key: 'oee',
      align: 'right',
      render: (v: number) => (
        <span className="sayisal" style={{ color: oeeRenk(v), fontWeight: 600 }}>
          %{v}
        </span>
      ),
    },
    {
      title: t('pano.t_durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: UretimSatiri['durum']) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
          <span
            style={{ width: 8, height: 8, borderRadius: '50%', background: durumStil[d].renk }}
          />
          {durumStil[d].etiket}
        </span>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      {/* Başlık + dönem + dışa aktar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 22,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Typography.Title level={3} style={{ margin: 0, letterSpacing: '-0.02em' }}>
              {t('pano.hosgeldin', { ad: kullanici?.ad_soyad || kullanici?.eposta || '' })}
            </Typography.Title>
            <Tag color="warning" bordered={false}>
              {t('ortak.demo_veri')}
            </Tag>
          </div>
          <Typography.Paragraph style={{ color: 'var(--metin-soluk)', margin: '4px 0 0' }}>
            {t('pano.alt_baslik')}
          </Typography.Paragraph>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Segmented
            value={donem}
            onChange={(v) => setDonem(String(v))}
            options={[
              { label: t('ortak.gun'), value: 'gun' },
              { label: t('ortak.hafta'), value: 'hafta' },
              { label: t('ortak.ay'), value: 'ay' },
            ]}
          />
          <Button type="primary" icon={<DownloadOutlined />}>
            {t('ortak.disa_aktar')}
          </Button>
        </div>
      </div>

      {/* KPI kart sırası */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_toplam_uretim')}
            deger="12.450"
            birim={t('pano.birim_adet')}
            deltaMetin="%5"
            yon="yukari"
            olumlu
            altMetin={t('pano.dune_gore')}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_oee')}
            deger="%84,2"
            deltaMetin="%2"
            yon="yukari"
            olumlu
            altMetin={t('pano.dune_gore')}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_durus')}
            deger="38"
            birim={t('pano.birim_dk')}
            deltaMetin="%12"
            yon="asagi"
            olumlu
            altMetin={t('pano.dune_gore')}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_kalite')}
            deger="%98,5"
            deltaMetin="%0,5"
            yon="yukari"
            olumlu
            altMetin={t('pano.dune_gore')}
          />
        </Col>
      </Row>

      {/* OEE kırılımı + üretim trendi */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={9}>
          <Card title={t('pano.oee_kirilim')} style={{ height: '100%' }}>
            <Donut
              merkezUst="%84,2"
              merkezAlt="OEE"
              segmentler={[
                { etiket: t('pano.kullanilabilirlik'), deger: 90, renk: RENKLER.basari },
                { etiket: t('pano.performans'), deger: 88, renk: RENKLER.mavi },
                { etiket: t('pano.kalite'), deger: 96, renk: RENKLER.uyari },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card
            title={t('pano.uretim_trendi')}
            extra={
              <span style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>
                ×1000 {t('pano.birim_adet')}
              </span>
            }
            style={{ height: '100%' }}
          >
            <SutunGrafik veri={TREND} vurguIndeks={6} />
          </Card>
        </Col>
      </Row>

      {/* Son üretim tablosu */}
      <Card title={t('pano.son_uretim')} style={{ marginTop: 16 }}>
        <Table
          rowKey="id"
          columns={kolonlar}
          dataSource={SATIRLAR}
          pagination={false}
          size="middle"
        />
      </Card>
    </div>
  );
}
