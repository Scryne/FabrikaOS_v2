/**
 * Sürdürülebilirlik (ESG) panosu (S32, ADR-0051) — Kapsam 1/2 emisyon, birim ürün başına karbon
 * ve enerji yoğunluğu, enerji türü kırılımı, emisyon faktörleri (kaynaklı varsayılan + tenant) ve
 * async ESG raporu. Faktörü olmayan tüketim 0 sayılmaz: ayrı uyarıda miktarıyla listelenir.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  CloudOutlined,
  DeleteOutlined,
  FileTextOutlined,
  FireOutlined,
  PlusOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Segmented,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';

import { EGrafik } from '@/components/grafik/EGrafik';
import { yiginCubukSecenek } from '@/components/grafik/grafikSecenek';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useRaporOlustur } from '@/modules/rapor/hooks';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import {
  type Donem,
  emisyonMetni,
  type EsgFaktor,
  type EsgOzet,
  useEsgFaktorler,
  useEsgOzet,
  useFaktorEkle,
  useFaktorSil,
} from './hooks';

const HAT = BOLUM_RENGI['menu.bolum_kalite'];
const ENERJI_TURLERI = ['elektrik', 'dogalgaz', 'su', 'hava', 'buhar'];
type Tur = EsgOzet['turler'][number];

/** Normalleştirilmiş birim → okunur yazım (sunucu kwh/m3 döner). */
const birimMetni = (b: string) => ({ kwh: 'kWh', m3: 'm³' })[b] ?? b;

const sayi = (v: number, b = 2) => v.toLocaleString('tr-TR', { maximumFractionDigits: b });

export function EsgPano() {
  const { t } = useTranslation();
  const izinVar = useAuthStore((s) => s.izinVar);
  const yaz = izinVar('esg:yaz');
  const raporYaz = izinVar('rapor:yaz');
  const [donem, setDonem] = useState<Donem>('gun');
  const [aralik, setAralik] = useState<[Dayjs, Dayjs]>(() => [
    dayjs().subtract(29, 'day').startOf('day'),
    dayjs().startOf('day'),
  ]);
  const [faktorAcik, setFaktorAcik] = useState(false);
  const ozet = useEsgOzet(aralik[0].format('YYYY-MM-DD'), aralik[1].format('YYYY-MM-DD'), donem);
  const faktorler = useEsgFaktorler();
  const sil = useFaktorSil();
  const rapor = useRaporOlustur();
  const o = ozet.data;

  const grafik = useMemo(() => {
    if (!o || o.donemler.length === 0) return null;
    const bicim = donem === 'gun' ? 'DD.MM' : 'MM.YYYY';
    return yiginCubukSecenek(
      o.donemler.map((d) => dayjs(d.donem).format(bicim)),
      [
        {
          ad: t('esg.kapsam1'),
          renk: RENKLER.uyari,
          veri: o.donemler.map((d) => Math.round(d.kapsam1_kg * 10) / 10),
        },
        {
          ad: t('esg.kapsam2'),
          renk: RENKLER.cyan,
          veri: o.donemler.map((d) => Math.round(d.kapsam2_kg * 10) / 10),
        },
      ],
    );
  }, [o, donem, t]);

  const turKolon: ColumnsType<Tur> = [
    {
      title: t('esg.enerji_turu'),
      dataIndex: 'enerji_turu',
      key: 'tur',
      render: (v: string) => t(`enerji.tur_${v}`, { defaultValue: v }),
    },
    {
      title: t('esg.tuketim'),
      key: 'miktar',
      align: 'right',
      render: (_v, r) => (
        <span className="sayisal">
          {sayi(r.miktar)} <span className="varlik-alt">{birimMetni(r.birim)}</span>
        </span>
      ),
    },
    {
      title: t('esg.faktor'),
      key: 'faktor',
      align: 'right',
      render: (_v, r) =>
        r.faktor == null ? (
          '—'
        ) : (
          <Tooltip title={r.faktor_kaynagi}>
            <span className="sayisal">{sayi(r.faktor, 4)}</span>
          </Tooltip>
        ),
    },
    {
      title: t('esg.kapsam'),
      dataIndex: 'kapsam',
      key: 'kapsam',
      render: (v: string | null) => (v ? <Tag bordered={false}>{t(`esg.${v}`)}</Tag> : '—'),
    },
    {
      title: t('esg.emisyon'),
      dataIndex: 'emisyon_kg',
      key: 'emisyon',
      align: 'right',
      render: (v: number | null) => (
        <span className="sayisal">{v == null ? '—' : emisyonMetni(v)}</span>
      ),
    },
  ];

  const faktorKolon: ColumnsType<EsgFaktor> = [
    {
      title: t('esg.enerji_turu'),
      key: 'tur',
      render: (_v, f) => (
        <span>
          {t(`enerji.tur_${f.enerji_turu}`, { defaultValue: f.enerji_turu })}{' '}
          <span className="varlik-alt">/ {birimMetni(f.birim)}</span>
        </span>
      ),
    },
    {
      title: t('esg.faktor_birimli'),
      dataIndex: 'deger',
      key: 'deger',
      align: 'right',
      render: (v: number) => <span className="sayisal">{sayi(v, 4)}</span>,
    },
    {
      title: t('esg.kapsam'),
      dataIndex: 'kapsam',
      key: 'kapsam',
      render: (v: string) => <Tag bordered={false}>{t(`esg.${v}`)}</Tag>,
    },
    {
      title: t('esg.gecerlilik'),
      dataIndex: 'gecerlilik',
      key: 'gecerlilik',
      responsive: ['md'],
      render: (v: string, f) =>
        f.koken === 'varsayilan' ? (
          <span className="varlik-alt">—</span>
        ) : (
          <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>
        ),
    },
    {
      title: t('esg.kaynak'),
      key: 'kaynak',
      render: (_v, f) => (
        <span>
          <Tag bordered={false} color={f.koken === 'varsayilan' ? 'default' : 'blue'}>
            {t(`esg.koken_${f.koken}`)}
          </Tag>
          <span className="varlik-alt esg-kaynak">{f.kaynak}</span>
        </span>
      ),
    },
    ...(yaz
      ? [
          {
            title: '',
            key: 'sil',
            width: 48,
            render: (_v: unknown, f: EsgFaktor) =>
              f.id != null && (
                <Popconfirm
                  title={t('esg.faktor_sil_soru')}
                  okText={t('esg.sil')}
                  cancelText={t('ortak.vazgec')}
                  onConfirm={() => sil.mutate(f.id!)}
                >
                  <Button type="text" danger icon={<DeleteOutlined />} aria-label={t('esg.sil')} />
                </Popconfirm>
              ),
          },
        ]
      : []),
  ];

  const gun = aralik[1].diff(aralik[0], 'day') + 1;

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.esg')}
        alt={t('esg.alt')}
        sag={
          <Space wrap size={8}>
            <Segmented
              value={donem}
              onChange={(v) => setDonem(v as Donem)}
              options={[
                { value: 'gun', label: t('esg.gunluk') },
                { value: 'ay', label: t('esg.aylik') },
              ]}
              aria-label={t('esg.kirilim')}
            />
            <DatePicker.RangePicker
              value={aralik}
              allowClear={false}
              format="DD.MM.YYYY"
              onChange={(v) => v?.[0] && v[1] && setAralik([v[0], v[1]])}
              aria-label={t('esg.aralik')}
            />
            {raporYaz && (
              <Button
                icon={<FileTextOutlined />}
                loading={rapor.isPending}
                onClick={() => rapor.mutate({ tur: 'esg', bicim: 'pdf', gun: Math.min(gun, 365) })}
              >
                {t('esg.rapor_uret')}
              </Button>
            )}
          </Space>
        }
      />
      {ozet.isError && (
        <Alert type="error" showIcon message={t('esg.aralik_hata')} style={{ marginBottom: 16 }} />
      )}
      <OzetSerit
        renk={HAT}
        yukleniyor={ozet.isPending}
        metrikler={
          o
            ? [
                {
                  anahtar: 'toplam',
                  baslik: t('esg.toplam'),
                  deger: sayi(o.toplam_ton, 3),
                  birim: 't CO₂e',
                  ikon: <CloudOutlined />,
                },
                {
                  anahtar: 'k1',
                  baslik: t('esg.kapsam1_uzun'),
                  deger: sayi(o.kapsam1_ton, 3),
                  birim: 't',
                  ikon: <FireOutlined />,
                },
                {
                  anahtar: 'k2',
                  baslik: t('esg.kapsam2_uzun'),
                  deger: sayi(o.kapsam2_ton, 3),
                  birim: 't',
                  ikon: <ThunderboltOutlined />,
                },
                {
                  anahtar: 'kg_adet',
                  baslik: t('esg.karbon_yogunlugu'),
                  deger: o.kg_adet == null ? '—' : sayi(o.kg_adet, 3),
                  birim: o.kg_adet == null ? undefined : 'kg/adet',
                  ikon: <CloudOutlined />,
                },
                {
                  anahtar: 'kwh_adet',
                  baslik: t('esg.enerji_yogunlugu'),
                  deger: o.kwh_adet == null ? '—' : sayi(o.kwh_adet, 3),
                  birim: o.kwh_adet == null ? undefined : 'kWh/adet',
                  ikon: <ThunderboltOutlined />,
                },
              ]
            : []
        }
      />
      <div style={{ height: 16 }} />
      {o && o.faktorsuz.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message={t('esg.faktorsuz_baslik', { n: o.faktorsuz.length })}
          description={
            <>
              {o.faktorsuz
                .map(
                  (f) =>
                    `${t(`enerji.tur_${f.enerji_turu}`, { defaultValue: f.enerji_turu })} ${sayi(f.miktar)} ${birimMetni(f.birim)}`,
                )
                .join(' · ')}
              . {t('esg.faktorsuz_aciklama')}
            </>
          }
        />
      )}
      <Row gutter={[20, 20]}>
        <Col xs={24} xl={14}>
          <Card title={t('esg.emisyon_seyri')} styles={{ body: { padding: 18 } }}>
            {ozet.isPending ? (
              <Skeleton active />
            ) : !grafik ? (
              <Empty description={t('esg.veri_yok')} />
            ) : (
              <EGrafik secenek={grafik} yukseklik={300} etiket={t('esg.emisyon_seyri')} />
            )}
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card title={t('esg.tur_kirilimi')} styles={{ body: { padding: 0 } }}>
            <Table<Tur>
              rowKey={(r) => `${r.enerji_turu}-${r.birim}`}
              size="middle"
              columns={turKolon}
              dataSource={o?.turler ?? []}
              loading={ozet.isPending}
              pagination={false}
              scroll={{ x: 'max-content' }}
              locale={{ emptyText: t('esg.veri_yok') }}
            />
          </Card>
        </Col>
      </Row>
      <div style={{ height: 20 }} />
      <Card
        title={t('esg.faktorler')}
        extra={
          yaz && (
            <Button icon={<PlusOutlined />} onClick={() => setFaktorAcik(true)}>
              {t('esg.faktor_ekle')}
            </Button>
          )
        }
        styles={{ body: { padding: 0 } }}
      >
        <p className="varlik-alt" style={{ margin: '12px 18px 0' }}>
          {t('esg.faktor_aciklama')}
        </p>
        <Table<EsgFaktor>
          rowKey={(f) => `${f.koken}-${f.id ?? f.enerji_turu}-${f.birim}-${f.gecerlilik}`}
          size="middle"
          columns={faktorKolon}
          dataSource={faktorler.data ?? []}
          loading={faktorler.isPending}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
        <p className="varlik-alt" style={{ margin: '12px 18px' }}>
          {t('esg.rapor_ipucu')} <Link to="/raporlar">{t('menu.raporlar')}</Link>
        </p>
      </Card>
      <FaktorFormu acik={faktorAcik} kapat={() => setFaktorAcik(false)} />
    </SayfaKapsayici>
  );
}

type FaktorDeger = {
  enerji_turu: string;
  birim: string;
  deger: number;
  kapsam: 'kapsam1' | 'kapsam2';
  gecerlilik: Dayjs;
  kaynak: string;
};

function FaktorFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<FaktorDeger>();
  const ekle = useFaktorEkle();
  const gonder = async () => {
    const d = await form.validateFields();
    await ekle.mutateAsync({
      enerji_turu: d.enerji_turu,
      birim: d.birim,
      deger: String(d.deger),
      kapsam: d.kapsam,
      gecerlilik: d.gecerlilik.format('YYYY-MM-DD'),
      kaynak: d.kaynak,
    });
    kapat();
  };
  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('esg.faktor_ekle')}
      okText={t('esg.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={ekle.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form<FaktorDeger>
        form={form}
        layout="vertical"
        requiredMark="optional"
        initialValues={{
          enerji_turu: 'elektrik',
          birim: 'kwh',
          kapsam: 'kapsam2',
          gecerlilik: dayjs().startOf('year'),
        }}
      >
        <div className="form-izgara-3">
          <Form.Item name="enerji_turu" label={t('esg.enerji_turu')} rules={[{ required: true }]}>
            <Select
              options={ENERJI_TURLERI.map((x) => ({
                value: x,
                label: t(`enerji.tur_${x}`, { defaultValue: x }),
              }))}
            />
          </Form.Item>
          <Form.Item name="birim" label={t('esg.birim')} rules={[{ required: true }]}>
            <Select
              options={['kwh', 'm3'].map((b) => ({ value: b, label: b === 'kwh' ? 'kWh' : 'm³' }))}
            />
          </Form.Item>
          <Form.Item name="kapsam" label={t('esg.kapsam')} rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'kapsam1', label: t('esg.kapsam1') },
                { value: 'kapsam2', label: t('esg.kapsam2') },
              ]}
            />
          </Form.Item>
        </div>
        <div className="form-izgara-3">
          <Form.Item
            name="deger"
            label={t('esg.faktor_birimli')}
            rules={[{ required: true }]}
            extra={t('esg.deger_ipucu')}
          >
            <InputNumber min={0} step={0.001} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="gecerlilik" label={t('esg.gecerlilik')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
          </Form.Item>
        </div>
        <Form.Item
          name="kaynak"
          label={t('esg.kaynak')}
          rules={[{ required: true, min: 3, message: t('esg.kaynak_gerekli') }]}
          extra={t('esg.kaynak_ipucu')}
        >
          <Input.TextArea rows={2} maxLength={300} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
