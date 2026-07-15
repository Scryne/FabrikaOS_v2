/**
 * Vardiya & Duruş yönetimi (S24) — dört görünüm tek çalışma alanında:
 * kayıtlar (sunucu-taraflı tablo) · pareto (neden 80/20 grafiği + kırılım tablosu) ·
 * neden kataloğu · vardiya tanımları. KPI şeridi pareto verisinden türetilir (son N gün
 * toplam duruş, plansız payı, en büyük neden).
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarChartOutlined,
  ClockCircleOutlined,
  FieldTimeOutlined,
  PauseCircleOutlined,
  PlusOutlined,
  TagsOutlined,
  UnorderedListOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Segmented,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  TimePicker,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Dayjs } from 'dayjs';

import { EGrafik } from '@/components/grafik/EGrafik';
import { paretoSecenek } from '@/components/grafik/grafikSecenek';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { DurusKaydiFormu } from './DurusKaydiFormu';
import {
  DURUS_SINIFLARI,
  type DurusKaydi,
  type DurusNedeni,
  type ParetoSatir,
  type Vardiya,
  useDurusKayitlari,
  useDurusNedenleri,
  useDurusNedeniGuncelle,
  useDurusNedeniOlustur,
  useDurusPareto,
  useVardiyaGuncelle,
  useVardiyalar,
  useVardiyaOlustur,
} from './hooks';

const HAT = BOLUM_RENGI['menu.bolum_uretim'];

type Gorunum = 'kayitlar' | 'pareto' | 'nedenler' | 'vardiyalar';

/** Basit katalog formu (neden / vardiya ortak kabuğu). */
function NedenFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<{ ad: string; sinif: string }>();
  const olustur = useDurusNedeniOlustur();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({ ad: v.ad.trim(), sinif: v.sinif });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      title={t('durus.yeni_neden')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      onOk={() => void gonder()}
      onCancel={() => {
        form.resetFields();
        kapat();
      }}
      destroyOnHidden
      maskClosable={false}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        preserve={false}
        initialValues={{ sinif: 'plansiz' }}
      >
        <Form.Item name="ad" label={t('durus.neden')} rules={[{ required: true }, { max: 100 }]}>
          <Input autoFocus />
        </Form.Item>
        <Form.Item name="sinif" label={t('durus.sinif')} rules={[{ required: true }]}>
          <Select
            options={DURUS_SINIFLARI.map((s) => ({ value: s, label: t(`durus.sinif_${s}`) }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function VardiyaFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<{ ad: string; aralik: [Dayjs, Dayjs] }>();
  const olustur = useVardiyaOlustur();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      ad: v.ad.trim(),
      baslangic_saat: v.aralik[0].format('HH:mm:ss'),
      bitis_saat: v.aralik[1].format('HH:mm:ss'),
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      title={t('durus.yeni_vardiya')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      onOk={() => void gonder()}
      onCancel={() => {
        form.resetFields();
        kapat();
      }}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional" preserve={false}>
        <Form.Item
          name="ad"
          label={t('durus.vardiya_ad')}
          rules={[{ required: true }, { max: 50 }]}
        >
          <Input placeholder={t('durus.vardiya_ipucu')} autoFocus />
        </Form.Item>
        <Form.Item
          name="aralik"
          label={t('durus.saat_araligi')}
          rules={[{ required: true }]}
          extra={t('durus.gece_ipucu')}
        >
          <TimePicker.RangePicker format="HH:mm" order={false} style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function DurusEkrani({ baslangicGorunum = 'kayitlar' }: { baslangicGorunum?: Gorunum }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));
  const [gorunum, setGorunum] = useState<Gorunum>(baslangicGorunum);
  const [paretoGun, setParetoGun] = useState(30);
  const [kayitFormAcik, setKayitFormAcik] = useState(false);
  const [nedenFormAcik, setNedenFormAcik] = useState(false);
  const [vardiyaFormAcik, setVardiyaFormAcik] = useState(false);

  const [param, paramDegistir] = useSayfaParam();
  const { data: kayitlar, isPending: kayitYukleniyor, isError } = useDurusKayitlari(param);
  const { data: nedenler, isPending: nedenYukleniyor } = useDurusNedenleri();
  const { data: vardiyalar, isPending: vardiyaYukleniyor } = useVardiyalar();
  const { data: pareto, isPending: paretoYukleniyor } = useDurusPareto(paretoGun);
  const { data: makineler } = useMakineSecenekleri();
  const nedenGuncelle = useDurusNedeniGuncelle();
  const vardiyaGuncelle = useVardiyaGuncelle();

  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);
  const nedenHarita = useMemo(() => new Map((nedenler ?? []).map((n) => [n.id, n])), [nedenler]);

  const toplamDk = (pareto ?? []).reduce((s, p) => s + p.toplam_dk, 0);
  const plansizDk = (pareto ?? [])
    .filter((p) => p.sinif === 'plansiz')
    .reduce((s, p) => s + p.toplam_dk, 0);
  const metrikler: OzetMetrik[] = [
    {
      anahtar: 'toplam',
      baslik: t('durus.kpi_toplam', { gun: paretoGun }),
      deger: `${Math.round(toplamDk)} dk`,
      ikon: <FieldTimeOutlined />,
    },
    {
      anahtar: 'plansiz',
      baslik: t('durus.kpi_plansiz'),
      deger: toplamDk > 0 ? `%${Math.round((plansizDk / toplamDk) * 100)}` : '—',
      ikon: <WarningOutlined />,
    },
    {
      anahtar: 'buyuk',
      baslik: t('durus.kpi_en_buyuk'),
      deger: pareto?.[0]?.neden ?? '—',
      ikon: <PauseCircleOutlined />,
    },
    {
      anahtar: 'vardiya',
      baslik: t('durus.kpi_vardiya'),
      deger: String((vardiyalar ?? []).filter((v) => v.aktif).length),
      ikon: <ClockCircleOutlined />,
    },
  ];

  const kayitKolonlari: ColumnsType<DurusKaydi> = [
    {
      title: t('durus.makine'),
      dataIndex: 'makine_id',
      key: 'makine_id',
      render: (id: number) => {
        const m = makineHarita.get(id);
        return m ? <span className="sayisal">{m.kod}</span> : `#${id}`;
      },
    },
    {
      title: t('durus.neden'),
      dataIndex: 'neden_id',
      key: 'neden_id',
      render: (id: number) => {
        const n = nedenHarita.get(id);
        if (!n) return `#${id}`;
        return (
          <Space size={8}>
            <span>{n.ad}</span>
            <Tag color={n.sinif === 'plansiz' ? 'red' : 'blue'}>{t(`durus.sinif_${n.sinif}`)}</Tag>
          </Space>
        );
      },
    },
    {
      title: t('durus.baslangic'),
      dataIndex: 'baslangic',
      key: 'baslangic',
      render: (v: string) => <span className="sayisal">{new Date(v).toLocaleString()}</span>,
    },
    {
      title: t('durus.bitis'),
      dataIndex: 'bitis',
      key: 'bitis',
      render: (v: string) => <span className="sayisal">{new Date(v).toLocaleString()}</span>,
    },
    {
      title: t('durus.sure_dk'),
      dataIndex: 'sure_dk',
      key: 'sure_dk',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v.toFixed(1)}</span>,
    },
    { title: t('durus.aciklama'), dataIndex: 'aciklama', key: 'aciklama', ellipsis: true },
  ];

  const nedenKolonlari: ColumnsType<DurusNedeni> = [
    { title: t('durus.neden'), dataIndex: 'ad', key: 'ad' },
    {
      title: t('durus.sinif'),
      dataIndex: 'sinif',
      key: 'sinif',
      render: (v: string) => (
        <Tag color={v === 'plansiz' ? 'red' : 'blue'}>{t(`durus.sinif_${v}`)}</Tag>
      ),
    },
    {
      title: t('durus.aktif'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean, kayit) =>
        yazabilir ? (
          <Switch
            size="small"
            checked={aktif}
            loading={nedenGuncelle.isPending && nedenGuncelle.variables?.id === kayit.id}
            onChange={(deger) => nedenGuncelle.mutate({ id: kayit.id, govde: { aktif: deger } })}
            aria-label={t('durus.aktif')}
          />
        ) : (
          <Tag color={aktif ? 'green' : 'default'}>
            {aktif ? t('durus.aktif') : t('durus.pasif')}
          </Tag>
        ),
    },
  ];

  const vardiyaKolonlari: ColumnsType<Vardiya> = [
    { title: t('durus.vardiya_ad'), dataIndex: 'ad', key: 'ad' },
    {
      title: t('durus.saat_araligi'),
      key: 'aralik',
      // "HH:mm:ss" → "HH:mm" (dayjs customParseFormat eklentisi projede yok; dilimleme yeter).
      render: (_, v) => (
        <span className="sayisal">
          {v.baslangic_saat.slice(0, 5)} – {v.bitis_saat.slice(0, 5)}
        </span>
      ),
    },
    {
      title: t('durus.aktif'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean, kayit) =>
        yazabilir ? (
          <Switch
            size="small"
            checked={aktif}
            loading={vardiyaGuncelle.isPending && vardiyaGuncelle.variables?.id === kayit.id}
            onChange={(deger) => vardiyaGuncelle.mutate({ id: kayit.id, govde: { aktif: deger } })}
            aria-label={t('durus.aktif')}
          />
        ) : (
          <Tag color={aktif ? 'green' : 'default'}>
            {aktif ? t('durus.aktif') : t('durus.pasif')}
          </Tag>
        ),
    },
  ];

  const yeniButon =
    gorunum === 'kayitlar' ? (
      <Button type="primary" icon={<PlusOutlined />} onClick={() => setKayitFormAcik(true)}>
        {t('durus.yeni_kayit')}
      </Button>
    ) : gorunum === 'nedenler' ? (
      <Button type="primary" icon={<PlusOutlined />} onClick={() => setNedenFormAcik(true)}>
        {t('durus.yeni_neden')}
      </Button>
    ) : gorunum === 'vardiyalar' ? (
      <Button type="primary" icon={<PlusOutlined />} onClick={() => setVardiyaFormAcik(true)}>
        {t('durus.yeni_vardiya')}
      </Button>
    ) : null;

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.vardiya_durus')}
        alt={t('durus.alt')}
        sag={
          <Space>
            <Segmented<Gorunum>
              value={gorunum}
              onChange={setGorunum}
              options={[
                {
                  value: 'kayitlar',
                  icon: <UnorderedListOutlined />,
                  label: t('durus.sekme_kayitlar'),
                },
                { value: 'pareto', icon: <BarChartOutlined />, label: t('durus.sekme_pareto') },
                { value: 'nedenler', icon: <TagsOutlined />, label: t('durus.sekme_nedenler') },
                {
                  value: 'vardiyalar',
                  icon: <ClockCircleOutlined />,
                  label: t('durus.sekme_vardiyalar'),
                },
              ]}
            />
            {yazabilir && yeniButon}
          </Space>
        }
      />
      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={paretoYukleniyor} />
      <div style={{ height: 20 }} />

      {gorunum === 'kayitlar' && (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<DurusKaydi>
            kolonlar={kayitKolonlari}
            veri={kayitlar?.veri ?? []}
            meta={kayitlar?.meta}
            yukleniyor={kayitYukleniyor}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            bosMetin={isError ? t('ortak.hata_baslik') : t('durus.bos')}
            araclar={
              <>
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('durus.makine')}
                  style={{ width: 200 }}
                  value={param.filtreler?.makine_id as number | undefined}
                  onChange={(v) => paramDegistir({ filtreler: { makine_id: v } })}
                  options={(makineler ?? []).map((m) => ({ value: m.id, label: m.kod }))}
                />
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('durus.neden')}
                  style={{ width: 200 }}
                  value={param.filtreler?.neden_id as number | undefined}
                  onChange={(v) => paramDegistir({ filtreler: { neden_id: v } })}
                  options={(nedenler ?? []).map((n) => ({ value: n.id, label: n.ad }))}
                />
              </>
            }
          />
        </Card>
      )}

      {gorunum === 'pareto' && (
        <Card
          title={t('durus.pareto_baslik')}
          extra={
            <Segmented<number>
              value={paretoGun}
              onChange={setParetoGun}
              options={[
                { value: 7, label: t('durus.gun_7') },
                { value: 30, label: t('durus.gun_30') },
                { value: 90, label: t('durus.gun_90') },
              ]}
            />
          }
          styles={{ body: { padding: 18 } }}
        >
          {(pareto ?? []).length === 0 ? (
            <div style={{ color: 'var(--metin-soluk)', padding: 24, textAlign: 'center' }}>
              {t('durus.pareto_bos')}
            </div>
          ) : (
            <>
              <EGrafik
                secenek={paretoSecenek(
                  (pareto ?? []).map((p) => ({ ad: p.neden, deger: Math.round(p.toplam_dk) })),
                )}
                yukseklik={300}
              />
              <Table<ParetoSatir>
                size="small"
                rowKey="neden"
                pagination={false}
                dataSource={pareto ?? []}
                style={{ marginTop: 16 }}
                columns={[
                  { title: t('durus.neden'), dataIndex: 'neden', key: 'neden' },
                  {
                    title: t('durus.sinif'),
                    dataIndex: 'sinif',
                    key: 'sinif',
                    render: (v: string) => (
                      <Tag color={v === 'plansiz' ? 'red' : 'blue'}>{t(`durus.sinif_${v}`)}</Tag>
                    ),
                  },
                  {
                    title: t('durus.sure_dk'),
                    dataIndex: 'toplam_dk',
                    key: 'toplam_dk',
                    align: 'right',
                    render: (v: number) => <span className="sayisal">{v.toFixed(1)}</span>,
                  },
                  {
                    title: t('durus.yuzde'),
                    dataIndex: 'yuzde',
                    key: 'yuzde',
                    align: 'right',
                    render: (v: number) => <span className="sayisal">%{v.toFixed(1)}</span>,
                  },
                  {
                    title: t('durus.kumulatif'),
                    dataIndex: 'kumulatif_yuzde',
                    key: 'kumulatif_yuzde',
                    align: 'right',
                    render: (v: number) => <span className="sayisal">%{v.toFixed(1)}</span>,
                  },
                ]}
              />
            </>
          )}
        </Card>
      )}

      {gorunum === 'nedenler' && (
        <Card styles={{ body: { padding: 18 } }}>
          <Table<DurusNedeni>
            size="middle"
            rowKey="id"
            pagination={false}
            loading={nedenYukleniyor}
            dataSource={nedenler ?? []}
            columns={nedenKolonlari}
            locale={{ emptyText: t('durus.neden_bos') }}
          />
        </Card>
      )}

      {gorunum === 'vardiyalar' && (
        <Card styles={{ body: { padding: 18 } }}>
          <Table<Vardiya>
            size="middle"
            rowKey="id"
            pagination={false}
            loading={vardiyaYukleniyor}
            dataSource={vardiyalar ?? []}
            columns={vardiyaKolonlari}
            locale={{ emptyText: t('durus.vardiya_bos') }}
          />
        </Card>
      )}

      <DurusKaydiFormu acik={kayitFormAcik} kapat={() => setKayitFormAcik(false)} />
      <NedenFormu acik={nedenFormAcik} kapat={() => setNedenFormAcik(false)} />
      <VardiyaFormu acik={vardiyaFormAcik} kapat={() => setVardiyaFormAcik(false)} />
    </SayfaKapsayici>
  );
}
