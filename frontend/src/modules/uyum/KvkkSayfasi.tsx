/**
 * KVKK self-servis ekranı (S23 / ADR-0022) — üç panel:
 *
 * 1. **Veri ihracı** — kişi bazlı (kullanıcı/personel) async ZIP üretimi (202 → kuyruk →
 *    hazır → indir). S14 rapor deseninin aynısı: durum sütunu + hazır olunca indirme.
 * 2. **Anonimleştirme** — geri alınamaz; S17 tehlikeli-aksiyon deseni: kullanıcı "ANONIM"
 *    yazmadan buton etkinleşmez.
 * 3. **Rıza kayıtlarım** — kişisel yüzey (oturum yeterli); geri çekme yeni satırdır.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ClearOutlined,
  DownloadOutlined,
  ExportOutlined,
  UserDeleteOutlined,
} from '@ant-design/icons';
import { App, Button, Form, Input, InputNumber, Select, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { ApiHata } from '@/api/client';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';

import {
  type ConsentKaydi,
  ihracIndir,
  type KvkkIhrac,
  useAnonimlestir,
  useConsentEkle,
  useConsentKayitlari,
  useIhracBaslat,
  useIhraclariTemizle,
  useKvkkIhraclar,
} from './hooks';

const DURUM_RENK: Record<string, string> = {
  kuyrukta: 'default',
  hazirlaniyor: 'blue',
  hazir: 'green',
  basarisiz: 'red',
  // Saklama süresi dolmuş: artefakt silindi, kayıt denetim için duruyor (indirilemez).
  suresi_doldu: 'default',
};

const KISI_TURLERI = ['kullanici', 'personel'];
const ONAY_METNI = 'ANONIM';

export function KvkkSayfasi() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending } = useKvkkIhraclar(param);
  const ihracBaslat = useIhracBaslat();
  const anonimlestir = useAnonimlestir();
  const consentler = useConsentKayitlari();
  const consentEkle = useConsentEkle();
  const temizle = useIhraclariTemizle();

  const [ihracForm] = Form.useForm<{ kisi_turu: string; kisi_id: number }>();
  const [anonimForm] = Form.useForm<{ kisi_turu: string; kisi_id: number; onay: string }>();
  const [onayMetni, setOnayMetni] = useState('');
  const [indirilen, setIndirilen] = useState<number | null>(null);

  async function indir(kayit: KvkkIhrac) {
    setIndirilen(kayit.id);
    try {
      await ihracIndir(kayit);
    } catch (e) {
      message.error(e instanceof ApiHata ? e.message : t('ortak.hata_baslik'));
    } finally {
      setIndirilen(null);
    }
  }

  const ihracKolonlari: ColumnsType<KvkkIhrac> = [
    {
      title: t('uyum.kod'),
      dataIndex: 'kod',
      width: 150,
      render: (k: string) => <span className="sayisal">{k}</span>,
    },
    {
      title: t('uyum.kisi'),
      key: 'kisi',
      render: (_, kayit) => (
        <span>
          {t(`uyum.kisi_turu_${kayit.kisi_turu}`)} <span className="sayisal">#{kayit.kisi_id}</span>
        </span>
      ),
    },
    {
      title: t('uyum.durum'),
      dataIndex: 'durum',
      width: 130,
      render: (durum: string) => (
        <Tag color={DURUM_RENK[durum] ?? 'default'}>{t(`uyum.ihrac_durum_${durum}`)}</Tag>
      ),
    },
    {
      title: t('uyum.kayit_sayisi'),
      dataIndex: 'kayit_sayisi',
      width: 120,
      align: 'right',
      render: (sayi: number) => <span className="sayisal">{sayi || '—'}</span>,
    },
    {
      title: t('uyum.olusturma'),
      dataIndex: 'olusturma_tarihi',
      width: 170,
      render: (deger: string) => (
        <span className="sayisal">{dayjs(deger).format('DD.MM.YYYY HH:mm')}</span>
      ),
    },
    {
      title: '',
      key: 'islem',
      width: 120,
      align: 'right',
      render: (_, kayit) => (
        <Button
          size="small"
          icon={<DownloadOutlined />}
          disabled={kayit.durum !== 'hazir'}
          loading={indirilen === kayit.id}
          onClick={() => void indir(kayit)}
        >
          {t('ortak.indir')}
        </Button>
      ),
    },
  ];

  const consentKolonlari: ColumnsType<ConsentKaydi> = [
    {
      title: t('uyum.consent_tur'),
      dataIndex: 'tur',
      render: (tur: string) => t(`uyum.consent_${tur}`),
    },
    { title: t('uyum.metin_surumu'), dataIndex: 'metin_surumu', width: 130 },
    {
      title: t('uyum.consent_durum'),
      dataIndex: 'kabul',
      width: 130,
      render: (kabul: boolean) => (
        <Tag color={kabul ? 'green' : 'red'}>
          {kabul ? t('uyum.kabul_edildi') : t('uyum.geri_cekildi')}
        </Tag>
      ),
    },
    {
      title: t('uyum.zaman'),
      dataIndex: 'olusturma_tarihi',
      width: 170,
      render: (deger: string) => (
        <span className="sayisal">{dayjs(deger).format('DD.MM.YYYY HH:mm')}</span>
      ),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('uyum.kvkk_baslik')} alt={t('uyum.kvkk_aciklama')} />

      <Space direction="vertical" size={18} style={{ width: '100%' }}>
        <PanelKart baslik={t('uyum.ihrac_baslik')} ikon={<ExportOutlined />}>
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Typography.Paragraph style={{ marginBottom: 0, color: 'var(--metin-soluk)' }}>
              {t('uyum.ihrac_aciklama')}
            </Typography.Paragraph>
            {/* Saklama süresi kullanıcıya AÇIKÇA söylenir: indirilmeyen dosya kaybolduğunda
                "sistem bozuk" izlenimi oluşmasın (beklenti yönetimi). */}
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {t('uyum.saklama_notu')}
            </Typography.Text>
            <Form
              form={ihracForm}
              layout="inline"
              initialValues={{ kisi_turu: 'kullanici' }}
              onFinish={(d) =>
                ihracBaslat.mutate(d, {
                  onSuccess: () => {
                    message.success(t('uyum.ihrac_kuyruga_alindi'));
                    ihracForm.resetFields();
                  },
                })
              }
            >
              <Form.Item name="kisi_turu" label={t('uyum.kisi_turu')}>
                <Select
                  style={{ width: 150 }}
                  options={KISI_TURLERI.map((k) => ({
                    value: k,
                    label: t(`uyum.kisi_turu_${k}`),
                  }))}
                />
              </Form.Item>
              <Form.Item
                name="kisi_id"
                label={t('uyum.kisi_id')}
                rules={[{ required: true, message: t('uyum.kisi_id_gerekli') }]}
              >
                <InputNumber min={1} style={{ width: 130 }} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={ihracBaslat.isPending}>
                  {t('uyum.ihrac_baslat')}
                </Button>
              </Form.Item>
            </Form>
          </Space>
        </PanelKart>

        <SunucuTablo<KvkkIhrac>
          kolonlar={ihracKolonlari}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          baslik={t('uyum.ihrac_listesi')}
          bosMetin={t('uyum.ihrac_bos')}
          araclar={
            <Button
              icon={<ClearOutlined />}
              loading={temizle.isPending}
              onClick={() =>
                temizle.mutate(undefined, {
                  onSuccess: (sonuc) =>
                    message.success(`${t('uyum.temizlendi')} (${sonuc.silinen})`),
                })
              }
            >
              {t('uyum.temizle')}
            </Button>
          }
        />

        <PanelKart
          baslik={t('uyum.anonim_baslik')}
          ikon={<UserDeleteOutlined />}
          renk="var(--hata)"
        >
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Typography.Paragraph type="danger" style={{ marginBottom: 0 }}>
              {t('uyum.anonim_uyari')}
            </Typography.Paragraph>
            <Form
              form={anonimForm}
              layout="inline"
              initialValues={{ kisi_turu: 'personel' }}
              onFinish={(d) =>
                anonimlestir.mutate(d, {
                  onSuccess: () => {
                    message.success(t('uyum.anonim_tamam'));
                    anonimForm.resetFields();
                    setOnayMetni('');
                  },
                })
              }
            >
              <Form.Item name="kisi_turu" label={t('uyum.kisi_turu')}>
                <Select
                  style={{ width: 150 }}
                  options={KISI_TURLERI.map((k) => ({
                    value: k,
                    label: t(`uyum.kisi_turu_${k}`),
                  }))}
                />
              </Form.Item>
              <Form.Item
                name="kisi_id"
                label={t('uyum.kisi_id')}
                rules={[{ required: true, message: t('uyum.kisi_id_gerekli') }]}
              >
                <InputNumber min={1} style={{ width: 130 }} />
              </Form.Item>
              <Form.Item name="onay" label={t('uyum.onay_metni')} extra={t('uyum.onay_ipucu')}>
                <Input
                  style={{ width: 150 }}
                  placeholder={ONAY_METNI}
                  onChange={(e) => setOnayMetni(e.target.value)}
                />
              </Form.Item>
              <Form.Item>
                <Button
                  danger
                  type="primary"
                  htmlType="submit"
                  disabled={onayMetni !== ONAY_METNI}
                  loading={anonimlestir.isPending}
                >
                  {t('uyum.anonimlestir')}
                </Button>
              </Form.Item>
            </Form>
          </Space>
        </PanelKart>

        <PanelKart baslik={t('uyum.consent_baslik')} govdeDolgu={0}>
          <Table<ConsentKaydi>
            rowKey="id"
            size="small"
            loading={consentler.isLoading}
            dataSource={consentler.data ?? []}
            columns={consentKolonlari}
            pagination={false}
            footer={() => (
              <Space>
                <Button
                  size="small"
                  loading={consentEkle.isPending}
                  onClick={() =>
                    consentEkle.mutate({ tur: 'aydinlatma', metin_surumu: 'v1', kabul: true })
                  }
                >
                  {t('uyum.aydinlatma_kabul')}
                </Button>
                <Button
                  size="small"
                  loading={consentEkle.isPending}
                  onClick={() =>
                    consentEkle.mutate({ tur: 'acik_riza', metin_surumu: 'v1', kabul: true })
                  }
                >
                  {t('uyum.riza_ver')}
                </Button>
                <Button
                  size="small"
                  danger
                  loading={consentEkle.isPending}
                  onClick={() =>
                    consentEkle.mutate({ tur: 'acik_riza', metin_surumu: 'v1', kabul: false })
                  }
                >
                  {t('uyum.riza_geri_cek')}
                </Button>
              </Space>
            )}
          />
        </PanelKart>
      </Space>
    </SayfaKapsayici>
  );
}
