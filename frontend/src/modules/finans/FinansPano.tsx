/**
 * Finans özeti — KPI şeridi, alacak/borç yaşlandırması (vade yaşına göre yığın çubuk + en büyük
 * açık alacaklar) ve üretim malzeme maliyeti (kapanan iş emirleri; fiyatı olmayan kalem 0 diye
 * sayılmaz, işaretlenir).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  ClockCircleOutlined,
  DollarOutlined,
  FallOutlined,
  FileSearchOutlined,
  RiseOutlined,
  WalletOutlined,
} from '@ant-design/icons';
import { Alert, Card, Col, Empty, Row, Segmented, Skeleton, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { EGrafik } from '@/components/grafik/EGrafik';
import { yiginCubukSecenek } from '@/components/grafik/grafikSecenek';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import {
  type IsEmriMaliyeti,
  paraBicim,
  paraKisa,
  useFinansOzet,
  useMaliyet,
  useYaslandirma,
  type Yaslandirma,
} from './hooks';

const HAT = BOLUM_RENGI['menu.bolum_finans'];
// Yaşa göre sıralı renk: vadesi gelmemiş nötr-olumlu → 90+ gün kırmızı.
const KOVALAR = [
  { anahtar: 'vadesi_gelmemis', renk: RENKLER.basari },
  { anahtar: 'gun_0_30', renk: RENKLER.cyan },
  { anahtar: 'gun_31_60', renk: RENKLER.uyari },
  { anahtar: 'gun_61_90', renk: '#f97316' },
  { anahtar: 'gun_90_ustu', renk: RENKLER.hata },
] as const;

type Kova = (typeof KOVALAR)[number]['anahtar'];
type FirmaSatiri = Yaslandirma['alacak']['firmalar'][number];
type MaliyetKalemi = IsEmriMaliyeti['kalemler'][number];

export function FinansPano() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [gun, setGun] = useState(30);
  const ozet = useFinansOzet();
  const yas = useYaslandirma();
  const maliyet = useMaliyet(gun);
  const o = ozet.data;
  const y = yas.data;

  const secenek = y
    ? yiginCubukSecenek(
        [t('finans.alacak_yonu'), t('finans.borc_yonu')],
        KOVALAR.map((k) => ({
          ad: t(`finans.kova_${k.anahtar}`),
          renk: k.renk,
          veri: [y.alacak[k.anahtar as Kova], y.borc[k.anahtar as Kova]],
        })),
      )
    : null;
  if (secenek) {
    // Lejant iki satıra iner: çizim alanını aşağı it; eksen Türkçe kısa biçimde.
    secenek.grid = { left: 6, right: 14, top: 64, bottom: 4, containLabel: true };
    secenek.yAxis = {
      ...(secenek.yAxis as object),
      axisLabel: {
        color: RENKLER.metinSoluk,
        formatter: (v: number) => (v >= 1000 ? `${Math.round(v / 1000)} bin` : String(v)),
      },
    };
  }

  const tutarHucre = (v: number) => (
    <span className="sayisal" style={{ opacity: v > 0 ? 1 : 0.35 }}>
      {v > 0 ? paraBicim(v) : '—'}
    </span>
  );
  // Dar kartta beş kova sığmaz: vadesi gelmemiş / vadesi geçen / 90+ / toplam.
  const firmaKolon: ColumnsType<FirmaSatiri> = [
    { title: t('finans.firma'), dataIndex: 'firma_ad', key: 'firma_ad' },
    {
      title: t('finans.kova_vadesi_gelmemis'),
      dataIndex: 'vadesi_gelmemis',
      key: 'vadesi_gelmemis',
      align: 'right',
      render: tutarHucre,
    },
    {
      title: t('finans.vadesi_gecmis'),
      key: 'vadesi_gecmis',
      align: 'right',
      render: (_v, f) => tutarHucre(f.toplam - f.vadesi_gelmemis),
    },
    {
      title: t('finans.kova_gun_90_ustu'),
      dataIndex: 'gun_90_ustu',
      key: 'gun_90_ustu',
      align: 'right',
      render: tutarHucre,
    },
    {
      title: t('finans.toplam'),
      dataIndex: 'toplam',
      key: 'toplam',
      align: 'right',
      render: (v: number) => <strong className="sayisal">{paraBicim(v)}</strong>,
    },
  ];

  const maliyetKolon: ColumnsType<IsEmriMaliyeti> = [
    {
      title: t('finans.is_emri'),
      dataIndex: 'is_emri_kod',
      key: 'is_emri_kod',
      render: (v: string, m) => (
        <span>
          <span className="sayisal">{v}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {m.urun_kod} · {m.urun_ad}
          </span>
        </span>
      ),
    },
    {
      title: t('finans.kapanis'),
      dataIndex: 'kapanis_tarihi',
      key: 'kapanis_tarihi',
      render: (v: string | null) => (
        <span className="sayisal">{v ? dayjs(v).format('DD.MM.YYYY') : '—'}</span>
      ),
    },
    {
      title: t('finans.miktar'),
      dataIndex: 'miktar',
      key: 'miktar',
      align: 'right',
      render: (v: number | null) => (
        <span className="sayisal">{v != null ? v.toLocaleString('tr-TR') : '—'}</span>
      ),
    },
    {
      title: t('finans.malzeme_maliyeti'),
      dataIndex: 'malzeme_maliyeti',
      key: 'malzeme_maliyeti',
      align: 'right',
      render: (v: number, m) => (
        <span className="sayisal">
          {paraBicim(v)}
          {m.eksik_fiyat > 0 && ' *'}
        </span>
      ),
    },
    {
      title: t('finans.birim_maliyet'),
      dataIndex: 'birim_maliyet',
      key: 'birim_maliyet',
      align: 'right',
      render: (v: number | null, m) =>
        v != null ? (
          <span className="sayisal">{paraBicim(v)}</span>
        ) : (
          <Tag color="warning" variant="filled">
            {t('finans.eksik_fiyat', { n: m.eksik_fiyat })}
          </Tag>
        ),
    },
  ];

  const kalemKolon: ColumnsType<MaliyetKalemi> = [
    {
      title: t('finans.malzeme'),
      dataIndex: 'malzeme_ad',
      key: 'malzeme_ad',
      render: (v: string, k) => (
        <span>
          {v} <span className="varlik-alt sayisal">{k.malzeme_kod}</span>
        </span>
      ),
    },
    {
      title: t('finans.miktar'),
      dataIndex: 'miktar',
      key: 'miktar',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v.toLocaleString('tr-TR')}</span>,
    },
    {
      title: t('finans.birim_fiyat'),
      dataIndex: 'birim_fiyat',
      key: 'birim_fiyat',
      align: 'right',
      render: (v: number | null, k) =>
        v != null ? (
          <span className="sayisal" title={t(`finans.fiyat_kaynagi_${k.fiyat_kaynagi}`)}>
            {paraBicim(v)}
          </span>
        ) : (
          <Tag color="warning" variant="filled">
            {t('finans.fiyat_yok')}
          </Tag>
        ),
    },
    {
      title: t('finans.tutar'),
      dataIndex: 'tutar',
      key: 'tutar',
      align: 'right',
      render: (v: number | null) => (
        <span className="sayisal">{v != null ? paraBicim(v) : '—'}</span>
      ),
    },
  ];

  const eksikVar = (maliyet.data ?? []).some((m) => m.eksik_fiyat > 0);

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('menu.finans_ozet')} alt={t('finans.pano_alt')} />
      <OzetSerit
        renk={HAT}
        yukleniyor={ozet.isPending}
        metrikler={
          o
            ? [
                {
                  anahtar: 'alacak',
                  baslik: t('finans.acik_alacak'),
                  deger: paraKisa(o.acik_alacak),
                  ikon: <RiseOutlined />,
                },
                {
                  anahtar: 'borc',
                  baslik: t('finans.acik_borc'),
                  deger: paraKisa(o.acik_borc),
                  ikon: <FallOutlined />,
                },
                {
                  anahtar: 'vadesi',
                  baslik: t('finans.vadesi_gecen'),
                  deger: paraKisa(o.vadesi_gecen_alacak),
                  ikon: <ClockCircleOutlined />,
                  olumlu: o.vadesi_gecen_alacak === 0,
                },
                {
                  anahtar: 'satis',
                  baslik: t('finans.bu_ay_satis'),
                  deger: paraKisa(o.bu_ay_satis),
                  ikon: <DollarOutlined />,
                },
                {
                  anahtar: 'tahsilat',
                  baslik: t('finans.bu_ay_tahsilat'),
                  deger: paraKisa(o.bu_ay_tahsilat),
                  ikon: <WalletOutlined />,
                },
                {
                  anahtar: 'onay',
                  baslik: t('finans.onay_bekleyen'),
                  deger: String(o.onay_bekleyen),
                  ikon: <FileSearchOutlined />,
                },
              ]
            : []
        }
      />
      <div style={{ height: 20 }} />
      <Row gutter={[20, 20]}>
        <Col xs={24} xl={9}>
          <Card title={t('finans.yaslandirma')} styles={{ body: { padding: 18 } }}>
            {yas.isPending ? (
              <Skeleton active />
            ) : !y || (y.alacak.toplam === 0 && y.borc.toplam === 0) ? (
              <Empty description={t('finans.yaslandirma_bos')} />
            ) : (
              secenek && (
                <EGrafik
                  secenek={secenek}
                  yukseklik={300}
                  etiket={t('finans.yaslandirma_etiket', {
                    alacak: paraBicim(y.alacak.toplam),
                    borc: paraBicim(y.borc.toplam),
                  })}
                />
              )
            )}
          </Card>
        </Col>
        <Col xs={24} xl={15}>
          <Card title={t('finans.en_buyuk_alacaklar')} styles={{ body: { padding: 18 } }}>
            <Table<FirmaSatiri>
              rowKey="firma_id"
              size="small"
              columns={firmaKolon}
              dataSource={(y?.alacak.firmalar ?? []).slice(0, 8)}
              loading={yas.isPending}
              pagination={false}
              className="finans-tablo"
              scroll={{ x: 560 }}
              onRow={(f) => ({
                onClick: () => navigate(`/faturalar?firma=${f.firma_id}`),
                style: { cursor: 'pointer' },
              })}
              locale={{ emptyText: t('finans.alacak_yok') }}
            />
          </Card>
        </Col>
        <Col span={24}>
          <Card
            title={t('finans.uretim_maliyeti')}
            extra={
              <Segmented
                value={gun}
                onChange={(v) => setGun(Number(v))}
                options={[
                  { value: 30, label: t('finans.son_gun', { n: 30 }) },
                  { value: 90, label: t('finans.son_gun', { n: 90 }) },
                  { value: 365, label: t('finans.son_gun', { n: 365 }) },
                ]}
              />
            }
            styles={{ body: { padding: 18 } }}
          >
            <p className="varlik-alt" style={{ marginTop: 0 }}>
              {t('finans.maliyet_aciklama')}
            </p>
            {eksikVar && (
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 12 }}
                title={t('finans.eksik_fiyat_uyari')}
              />
            )}
            <Table<IsEmriMaliyeti>
              rowKey="is_emri_id"
              size="small"
              columns={maliyetKolon}
              dataSource={maliyet.data ?? []}
              loading={maliyet.isPending}
              pagination={{ pageSize: 10, hideOnSinglePage: true }}
              scroll={{ x: 640 }}
              expandable={{
                expandedRowRender: (m) => (
                  <Table<MaliyetKalemi>
                    rowKey="malzeme_id"
                    size="small"
                    columns={kalemKolon}
                    dataSource={m.kalemler}
                    pagination={false}
                  />
                ),
              }}
              locale={{ emptyText: t('finans.maliyet_bos') }}
            />
          </Card>
        </Col>
      </Row>
    </SayfaKapsayici>
  );
}
