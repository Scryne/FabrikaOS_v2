/**
 * Yönetici 360° pano — sunum katmanı (saf props). Hem gerçek (PanoSayfasi) hem demo (OnizlemePano)
 * aynı düzeni besler: KPI sırası + filo OEE göstergesi + makine-bazlı OEE + durum dağılımı + son üretim.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  DashboardOutlined,
  EyeOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Card, Col, Empty, Row, Skeleton, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { EGrafik } from '@/components/grafik/EGrafik';
import { cubukSecenek, donutSecenek, gostergeSecenek } from '@/components/grafik/grafikSecenek';
import { KpiKart } from '@/components/KpiKart';
import { OranSatiri } from '@/components/OranSatiri';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { RENKLER } from '@/tema/tema';
import type { components } from '@/api/types.gen';

import type { FiloOzeti } from './panoVeri';

type Makine = components['schemas']['MakineCevapDTO'];
type UretimVerisi = components['schemas']['UretimVerisiCevapDTO'];

const DURUM_RENK: Record<string, string> = {
  calisiyor: RENKLER.basari,
  durdu: RENKLER.metinSoluk,
  bakimda: RENKLER.uyari,
  ariza: RENKLER.hata,
};

export type PanoVerisi = {
  filo: FiloOzeti;
  makineSayisi: number;
  calisanSayisi: number;
  izlenenSayisi: number;
  durumlar: { durum: string; adet: number }[];
  makineOee: { ad: string; oee: number }[];
  sonUretim: UretimVerisi[];
  makineHarita: Map<number, Makine>;
};

export function PanoIcerik({
  kullaniciAdi,
  demo = false,
  yukleniyor = false,
  veri,
}: {
  kullaniciAdi: string;
  demo?: boolean;
  yukleniyor?: boolean;
  veri: PanoVerisi;
}) {
  const { t } = useTranslation();
  const { filo, makineSayisi, calisanSayisi, izlenenSayisi, durumlar, makineOee, sonUretim } = veri;

  const gauge = useMemo(() => gostergeSecenek(filo.oee), [filo.oee]);
  const bar = useMemo(() => cubukSecenek(makineOee), [makineOee]);
  const donut = useMemo(
    () =>
      donutSecenek(
        durumlar.map((d) => ({
          ad: t(`uretim.durum_${d.durum}`),
          deger: d.adet,
          renk: DURUM_RENK[d.durum] ?? RENKLER.metinSoluk,
        })),
      ),
    [durumlar, t],
  );

  const uretimKolonlari: ColumnsType<UretimVerisi> = [
    {
      title: t('uretim.zaman'),
      dataIndex: 'zaman',
      key: 'zaman',
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM HH:mm')}</span>,
    },
    {
      title: t('uretim.makine'),
      dataIndex: 'makine_id',
      key: 'makine_id',
      render: (id: number) => veri.makineHarita.get(id)?.kod ?? `#${id}`,
    },
    { title: t('uretim.vardiya'), dataIndex: 'vardiya', key: 'vardiya', render: (v) => v ?? '—' },
    {
      title: t('uretim.toplam_adet'),
      dataIndex: 'toplam_adet',
      key: 'toplam_adet',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v.toLocaleString('tr-TR')}</span>,
    },
  ];

  const baslik = (
    <SayfaBaslik
      baslik={
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          {t('pano.hosgeldin', { ad: kullaniciAdi })}
          {demo && (
            <Tag color="warning" bordered={false}>
              {t('ortak.demo_veri')}
            </Tag>
          )}
        </span>
      }
      alt={t('pano.alt_baslik')}
    />
  );

  if (!yukleniyor && makineSayisi === 0) {
    return (
      <div style={{ maxWidth: 1320 }}>
        {baslik}
        <Card>
          <Empty description={t('pano.makine_yok')} />
        </Card>
      </div>
    );
  }

  if (yukleniyor) {
    return (
      <div style={{ maxWidth: 1320 }}>
        {baslik}
        <Skeleton active paragraph={{ rows: 8 }} />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1320 }}>
      {baslik}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_oee')}
            deger={`%${Math.round(filo.oee)}`}
            ikon={<DashboardOutlined />}
            renk="var(--mavi)"
            altMetin={t('pano.filo_geneli')}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_calisan')}
            deger={`${calisanSayisi}/${makineSayisi}`}
            ikon={<ThunderboltOutlined />}
            renk="var(--cyan)"
            altMetin={t('pano.makine')}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_izlenen')}
            deger={String(izlenenSayisi)}
            ikon={<EyeOutlined />}
            renk="var(--hat-stok)"
            altMetin={t('pano.uretimli_makine')}
          />
        </Col>
        <Col xs={24} sm={12} xl={6}>
          <KpiKart
            baslik={t('pano.kpi_kalite')}
            deger={`%${Math.round(filo.kalite)}`}
            ikon={<CheckCircleOutlined />}
            renk="var(--basari)"
            altMetin={t('pano.filo_geneli')}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={9}>
          <Card title={t('pano.filo_oee')} style={{ height: '100%' }}>
            <EGrafik secenek={gauge} yukseklik={200} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 4 }}>
              <OranSatiri
                etiket={t('pano.kullanilabilirlik')}
                yuzde={filo.kullanilabilirlik}
                renk={RENKLER.basari}
              />
              <OranSatiri
                etiket={t('pano.performans')}
                yuzde={filo.performans}
                renk={RENKLER.mavi}
              />
              <OranSatiri etiket={t('pano.kalite')} yuzde={filo.kalite} renk={RENKLER.uyari} />
            </div>
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card
            title={t('pano.makine_oee')}
            extra={<span style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>%OEE</span>}
            style={{ height: '100%' }}
          >
            {makineOee.length > 0 ? (
              <EGrafik secenek={bar} yukseklik={280} />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('pano.uretim_yok')} />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={9}>
          <Card title={t('pano.durum_dagilimi')} style={{ height: '100%' }}>
            <EGrafik secenek={donut} yukseklik={220} />
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 8 }}>
              {durumlar.map((d) => (
                <span
                  key={d.durum}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}
                >
                  <span
                    style={{
                      width: 9,
                      height: 9,
                      borderRadius: 3,
                      background: DURUM_RENK[d.durum] ?? RENKLER.metinSoluk,
                    }}
                  />
                  <span style={{ color: 'var(--metin-soluk)' }}>
                    {t(`uretim.durum_${d.durum}`)}
                  </span>
                  <span className="sayisal" style={{ color: 'var(--metin)' }}>
                    {d.adet}
                  </span>
                </span>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card title={t('pano.son_uretim')} style={{ height: '100%' }}>
            <Table<UretimVerisi>
              rowKey="id"
              columns={uretimKolonlari}
              dataSource={sonUretim}
              pagination={false}
              size="middle"
              locale={{ emptyText: t('pano.uretim_yok') }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
