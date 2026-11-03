/**
 * İSG eğitim ve KKD çalışma alanı (S26-B, ADR-0044). Dört sekme:
 * - Eğitimler: verilen oturumlar; katılımcılar eğitim kaydıyla birlikte girilir.
 * - Matris: personel × konu; hücre en yeni katılımın geçerlilik sonuna göre renklenir.
 * - KKD durumu: departman gereksinimine göre eksik KKD (KKD teslimi = `kkd` kategorili zimmet).
 * - Gereksinimler: departman başına zorunlu eğitim konuları ve KKD (boş departman = herkes).
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  DatePicker,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { usePersonelSecenekleri } from '@/modules/ik/olgunlukHooks';
import { useAuthStore } from '@/store/authStore';

import {
  type Egitim,
  type GereksinimTuru,
  useEgitim,
  useEgitimler,
  useEgitimMatrisi,
  useEgitimOlustur,
  useGereksinimEkle,
  useGereksinimler,
  useGereksinimSil,
  useKatilimcilar,
  useKkdEksikleri,
} from './olgunlukHooks';

const DURUM_RENK: Record<string, string> = {
  gecerli: 'green',
  yaklasiyor: 'gold',
  gecmis: 'red',
  eksik: 'red',
  gerekmez: 'default',
};
const GECERLILIK_SECENEK = [0, 12, 24, 36];
const tarih = (v: string | null | undefined) => (v ? dayjs(v).format('DD.MM.YYYY') : '—');

function useKonuEtiketi() {
  const { t, i18n } = useTranslation();
  return (konu: string) =>
    i18n.exists(`isg26.konu_${konu}`) ? t(`isg26.konu_${konu}`) : konu.replace(/_/g, ' ');
}

const BILINEN_KONULAR = [
  'temel_isg',
  'yangin',
  'ilk_yardim',
  'yuksekte_calisma',
  'kimyasal',
  'is_makinesi',
  'elektrik',
];

// ── Eğitimler ────────────────────────────────────────────────────────────────

function EgitimFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const konuEtiketi = useKonuEtiketi();
  const olustur = useEgitimOlustur();
  const personeller = usePersonelSecenekleri(acik);
  const [form] = Form.useForm();

  const gonder = async () => {
    const v = await form.validateFields();
    const e = await olustur.mutateAsync({
      konu: v.konu,
      baslik: v.baslik,
      tarih: (v.tarih as Dayjs).format('YYYY-MM-DD'),
      sure_saat: v.sure_saat ?? 0,
      egitmen: v.egitmen ?? '',
      gecerlilik_ay: v.gecerlilik_ay,
      aciklama: v.aciklama ?? '',
      personel_idler: v.personel_idler ?? [],
    });
    message.success(t('isg26.egitim_kaydedildi', { kod: e.kod }));
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      width={720}
      title={t('isg26.egitim_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      onCancel={kapat}
      onOk={() => void gonder()}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      mask={{ closable: false }}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        initialValues={{ tarih: dayjs(), gecerlilik_ay: 12, sure_saat: 2 }}
      >
        <div className="form-iki-sutun">
          <Form.Item
            name="konu"
            label={t('isg26.konu')}
            rules={[{ required: true }]}
            tooltip={t('isg26.konu_ipucu')}
          >
            <Select
              showSearch
              options={BILINEN_KONULAR.map((k) => ({ value: k, label: konuEtiketi(k) }))}
            />
          </Form.Item>
          <Form.Item name="baslik" label={t('isg26.baslik')} rules={[{ required: true }]}>
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item name="tarih" label={t('isg26.tarih')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="sure_saat" label={t('isg26.sure_saat')}>
            <InputNumber min={0} max={999} step={0.5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="egitmen" label={t('isg26.egitmen')}>
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item
            name="gecerlilik_ay"
            label={t('isg26.gecerlilik')}
            tooltip={t('isg26.gecerlilik_ipucu')}
          >
            <Select
              options={GECERLILIK_SECENEK.map((a) => ({
                value: a,
                label: a ? t('isg26.ay', { ay: a }) : t('isg26.suresiz'),
              }))}
            />
          </Form.Item>
        </div>
        <Form.Item name="personel_idler" label={t('isg26.katilimcilar')}>
          <Select
            mode="multiple"
            showSearch
            optionFilterProp="label"
            loading={personeller.isPending}
            options={(personeller.data ?? [])
              .filter((p) => p.aktif)
              .map((p) => ({
                value: p.id,
                label: `${p.ad} ${p.soyad}${p.departman ? ` · ${p.departman}` : ''}`,
              }))}
          />
        </Form.Item>
        <Form.Item name="aciklama" label={t('isg26.aciklama')}>
          <Input.TextArea rows={2} maxLength={2000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

function EgitimCekmecesi({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const konuEtiketi = useKonuEtiketi();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const { data: e } = useEgitim(id);
  const degistir = useKatilimcilar(id ?? 0);
  const personeller = usePersonelSecenekleri(!!id && yazabilir);

  return (
    <Drawer open={id !== null} onClose={kapat} size={480} title={e ? e.baslik : ''} destroyOnHidden>
      {e && (
        <>
          <p className="varlik-alt sayisal">
            {e.kod} · {konuEtiketi(e.konu)} · {tarih(e.tarih)}
            {e.gecerlilik_sonu ? ` → ${tarih(e.gecerlilik_sonu)}` : ''}
          </p>
          {yazabilir ? (
            <Select
              mode="multiple"
              style={{ width: '100%', marginBottom: 12 }}
              showSearch
              optionFilterProp="label"
              loading={degistir.isPending}
              value={e.katilimcilar.map((k) => k.personel_id)}
              onChange={(v: number[]) => degistir.mutate(v)}
              options={(personeller.data ?? []).map((p) => ({
                value: p.id,
                label: `${p.ad} ${p.soyad}`,
              }))}
              aria-label={t('isg26.katilimcilar')}
            />
          ) : null}
          <List
            size="small"
            header={<strong>{t('isg26.katilimci_sayisi', { adet: e.katilimcilar.length })}</strong>}
            dataSource={e.katilimcilar}
            locale={{ emptyText: t('isg26.katilimci_yok') }}
            renderItem={(k) => (
              <List.Item>
                <span>{k.ad_soyad}</span>
                <span className="varlik-alt">{k.departman || '—'}</span>
              </List.Item>
            )}
          />
        </>
      )}
    </Drawer>
  );
}

function EgitimlerSekmesi() {
  const { t } = useTranslation();
  const konuEtiketi = useKonuEtiketi();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const { data, isPending } = useEgitimler();
  const [formAcik, setFormAcik] = useState(false);
  const [detay, setDetay] = useState<number | null>(null);

  const kolonlar: ColumnsType<Egitim> = [
    {
      title: t('isg26.egitim'),
      dataIndex: 'baslik',
      render: (_v, e) => (
        <span>
          <span className="varlik-ad">{e.baslik}</span>
          <span className="varlik-alt sayisal" style={{ display: 'block' }}>
            {e.kod}
          </span>
        </span>
      ),
    },
    { title: t('isg26.konu'), dataIndex: 'konu', render: (v: string) => konuEtiketi(v) },
    {
      title: t('isg26.tarih'),
      dataIndex: 'tarih',
      render: (v: string) => <span className="sayisal">{tarih(v)}</span>,
    },
    {
      title: t('isg26.gecerlilik_sonu'),
      dataIndex: 'gecerlilik_sonu',
      responsive: ['md'],
      render: (v: string | null) => (
        <span className="sayisal">{v ? tarih(v) : t('isg26.suresiz')}</span>
      ),
    },
    {
      title: t('isg26.katilimci'),
      dataIndex: 'katilimci_sayisi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
  ];

  return (
    <>
      {yazabilir && (
        <Button
          type="primary"
          icon={<PlusOutlined />}
          style={{ marginBottom: 12 }}
          onClick={() => setFormAcik(true)}
        >
          {t('isg26.egitim_yeni')}
        </Button>
      )}
      <Table<Egitim>
        rowKey="id"
        loading={isPending}
        columns={kolonlar}
        dataSource={data ?? []}
        scroll={{ x: 'max-content' }}
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        onRow={(e) => ({ onClick: () => setDetay(e.id), style: { cursor: 'pointer' } })}
        locale={{ emptyText: <Empty description={t('isg26.egitim_bos')} /> }}
      />
      <EgitimFormu acik={formAcik} kapat={() => setFormAcik(false)} />
      <EgitimCekmecesi id={detay} kapat={() => setDetay(null)} />
    </>
  );
}

// ── Matris ───────────────────────────────────────────────────────────────────

function MatrisSekmesi({ departman }: { departman?: string }) {
  const { t } = useTranslation();
  const konuEtiketi = useKonuEtiketi();
  const { data, isPending } = useEgitimMatrisi(departman);
  type Satir = NonNullable<typeof data>['personeller'][number];

  const kolonlar: ColumnsType<Satir> = [
    {
      title: t('isg26.personel'),
      dataIndex: 'ad_soyad',
      fixed: 'left',
      render: (_v, s) => (
        <span>
          <span className="varlik-ad">{s.ad_soyad}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {s.departman || '—'}
          </span>
        </span>
      ),
    },
    ...(data?.konular ?? []).map((konu) => ({
      title: konuEtiketi(konu),
      key: konu,
      align: 'center' as const,
      render: (_v: unknown, s: Satir) => {
        const h = s.hucreler[konu];
        if (!h || h.durum === 'gerekmez') return <span className="varlik-alt">·</span>;
        return (
          <Tooltip
            title={
              h.son_tarih
                ? `${tarih(h.son_tarih)}${h.gecerlilik_sonu ? ` → ${tarih(h.gecerlilik_sonu)}` : ''}`
                : t('isg26.katilim_yok')
            }
          >
            <Tag color={DURUM_RENK[h.durum]} variant="filled">
              {t(`isg26.durum_${h.durum}`)}
            </Tag>
          </Tooltip>
        );
      },
    })),
  ];
  const o = data?.ozet ?? {};

  return (
    <>
      <OzetSerit
        yukleniyor={isPending}
        metrikler={[
          {
            anahtar: 'g',
            baslik: t('isg26.durum_gecerli'),
            deger: String(o.gecerli ?? 0),
            olumlu: true,
          },
          { anahtar: 'y', baslik: t('isg26.durum_yaklasiyor'), deger: String(o.yaklasiyor ?? 0) },
          {
            anahtar: 'e',
            baslik: t('isg26.eksik_veya_gecmis'),
            deger: String((o.eksik ?? 0) + (o.gecmis ?? 0)),
            olumlu: (o.eksik ?? 0) + (o.gecmis ?? 0) === 0,
          },
        ]}
      />
      <Table<Satir>
        style={{ marginTop: 16 }}
        rowKey="personel_id"
        size="small"
        loading={isPending}
        columns={kolonlar}
        dataSource={data?.personeller ?? []}
        scroll={{ x: 'max-content' }}
        pagination={{ pageSize: 25, hideOnSinglePage: true }}
        locale={{ emptyText: <Empty description={t('isg26.matris_bos')} /> }}
      />
    </>
  );
}

// ── KKD ──────────────────────────────────────────────────────────────────────

function KkdSekmesi({ departman }: { departman?: string }) {
  const { t } = useTranslation();
  const { data, isPending } = useKkdEksikleri(departman);
  const liste = data ?? [];
  const eksikKisi = liste.filter((s) => s.eksik.length > 0).length;

  return (
    <>
      <OzetSerit
        yukleniyor={isPending}
        metrikler={[
          { anahtar: 'k', baslik: t('isg26.kkd_kapsam'), deger: String(liste.length) },
          {
            anahtar: 'e',
            baslik: t('isg26.kkd_eksik_kisi'),
            deger: String(eksikKisi),
            olumlu: eksikKisi === 0,
          },
        ]}
      />
      <Table
        style={{ marginTop: 16 }}
        rowKey="personel_id"
        size="small"
        loading={isPending}
        dataSource={liste}
        scroll={{ x: 'max-content' }}
        pagination={{ pageSize: 25, hideOnSinglePage: true }}
        locale={{ emptyText: <Empty description={t('isg26.kkd_bos')} /> }}
        columns={[
          {
            title: t('isg26.personel'),
            dataIndex: 'ad_soyad',
            render: (_v, s) => (
              <span>
                <span className="varlik-ad">{s.ad_soyad}</span>
                <span className="varlik-alt" style={{ display: 'block' }}>
                  {s.departman || '—'}
                </span>
              </span>
            ),
          },
          {
            title: t('isg26.kkd_durum'),
            key: 'kkd',
            render: (_v, s) => (
              <Space size={[4, 4]} wrap>
                {s.gerekli.map((k) => (
                  <Tag key={k} color={s.eksik.includes(k) ? 'red' : 'green'} variant="filled">
                    {k}
                  </Tag>
                ))}
              </Space>
            ),
          },
        ]}
      />
      <p className="varlik-alt" style={{ marginTop: 12 }}>
        {t('isg26.kkd_ipucu')}
      </p>
    </>
  );
}

// ── Gereksinimler ────────────────────────────────────────────────────────────

function GereksinimListesi({ tur, departmanlar }: { tur: GereksinimTuru; departmanlar: string[] }) {
  const { t } = useTranslation();
  const konuEtiketi = useKonuEtiketi();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const { data, isPending } = useGereksinimler(tur);
  const ekle = useGereksinimEkle(tur);
  const sil = useGereksinimSil(tur);
  const [form] = Form.useForm<{ departman?: string; ad: string }>();

  return (
    <Card size="small" title={t(`isg26.gereksinim_${tur}`)}>
      {yazabilir && (
        <Form
          form={form}
          layout="inline"
          className="isg26-gereksinim-form"
          onFinish={(v) =>
            ekle.mutate(
              { departman: v.departman ?? '', ad: v.ad },
              { onSuccess: () => form.resetFields() },
            )
          }
        >
          <Form.Item name="departman">
            <Select
              allowClear
              placeholder={t('isg26.herkes')}
              style={{ width: 160 }}
              options={departmanlar.map((d) => ({ value: d, label: d }))}
              aria-label={t('isg26.departman')}
            />
          </Form.Item>
          <Form.Item name="ad" rules={[{ required: true, message: '' }]}>
            {tur === 'egitim' ? (
              <Select
                showSearch
                style={{ width: 200 }}
                placeholder={t('isg26.konu')}
                options={BILINEN_KONULAR.map((k) => ({ value: k, label: konuEtiketi(k) }))}
                aria-label={t('isg26.konu')}
              />
            ) : (
              <Input
                placeholder={t('isg26.kkd_ornek')}
                maxLength={200}
                aria-label={t('isg26.kkd')}
              />
            )}
          </Form.Item>
          <Button htmlType="submit" icon={<PlusOutlined />} loading={ekle.isPending}>
            {t('isg26.ekle')}
          </Button>
        </Form>
      )}
      <List
        size="small"
        loading={isPending}
        dataSource={data ?? []}
        locale={{ emptyText: t('isg26.gereksinim_bos') }}
        renderItem={(g) => (
          <List.Item
            actions={
              yazabilir
                ? [
                    <Popconfirm
                      key="sil"
                      title={t('isg26.gereksinim_sil_soru')}
                      okText={t('isg26.kaldir')}
                      cancelText={t('ortak.vazgec')}
                      onConfirm={() => sil.mutate(g.id)}
                    >
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        aria-label={t('isg26.kaldir')}
                      />
                    </Popconfirm>,
                  ]
                : []
            }
          >
            <span>{tur === 'egitim' ? konuEtiketi(g.ad) : g.ad}</span>
            <Tag variant="filled">{g.departman || t('isg26.herkes')}</Tag>
          </List.Item>
        )}
      />
    </Card>
  );
}

// ── Sayfa ────────────────────────────────────────────────────────────────────

export function IsgEgitimleri() {
  const { t } = useTranslation();
  const [departman, setDepartman] = useState<string | undefined>();
  const [sekme, setSekme] = useState('egitimler');
  const personeller = usePersonelSecenekleri();
  const departmanlar = useMemo(
    () => [...new Set((personeller.data ?? []).map((p) => p.departman).filter(Boolean))].sort(),
    [personeller.data],
  );
  const suzgecli = sekme === 'matris' || sekme === 'kkd';

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('isg26.baslik_sayfa')}
        alt={t('isg26.alt_sayfa')}
        sag={
          suzgecli ? (
            <Select
              allowClear
              placeholder={t('isg26.tum_departmanlar')}
              style={{ minWidth: 200 }}
              value={departman}
              onChange={setDepartman}
              options={departmanlar.map((d) => ({ value: d, label: d }))}
              aria-label={t('isg26.departman')}
            />
          ) : null
        }
      />
      <Card>
        <Tabs
          activeKey={sekme}
          onChange={setSekme}
          items={[
            { key: 'egitimler', label: t('isg26.sekme_egitimler'), children: <EgitimlerSekmesi /> },
            {
              key: 'matris',
              label: t('isg26.sekme_matris'),
              children: <MatrisSekmesi departman={departman} />,
            },
            {
              key: 'kkd',
              label: t('isg26.sekme_kkd'),
              children: <KkdSekmesi departman={departman} />,
            },
            {
              key: 'gereksinim',
              label: t('isg26.sekme_gereksinim'),
              children: (
                <div className="isg26-gereksinimler">
                  <GereksinimListesi tur="egitim" departmanlar={departmanlar} />
                  <GereksinimListesi tur="kkd" departmanlar={departmanlar} />
                </div>
              ),
            },
          ]}
        />
      </Card>
    </SayfaKapsayici>
  );
}
