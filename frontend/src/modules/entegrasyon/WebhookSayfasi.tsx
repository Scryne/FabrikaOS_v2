/**
 * Entegrasyon çalışma alanı `/webhooklar` (Yönetim, slate — uiplani §11.1):
 * üç sekme — Webhook Abonelikleri · Teslimat Günlüğü · API Anahtarları.
 *
 * Gizli anahtar listede MASKELİDİR; tam değer yalnız oluşturma/anahtar-yenile
 * yanıtında bir kez `BirKezModal` ile gösterilir.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DeleteOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, Modal, Popconfirm, Select, Switch, Tabs, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { ApiAnahtarSekmesi } from './ApiAnahtarSekmesi';
import { BirKezModal } from './BirKezModal';
import {
  type Webhook,
  type WebhookOlustur,
  useAnahtarYenile,
  useOlayTurleri,
  useWebhooklar,
  useWebhookGuncelle,
  useWebhookOlustur,
  useWebhookSil,
} from './hooks';
import { TeslimatGunlugu } from './TeslimatGunlugu';

function WebhookAbonelikleri() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('entegrasyon:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useWebhooklar(param);
  const { data: olayTurleri } = useOlayTurleri();
  const olustur = useWebhookOlustur();
  const guncelle = useWebhookGuncelle();
  const sil = useWebhookSil();
  const anahtarYenile = useAnahtarYenile();
  const [formAcik, setFormAcik] = useState(false);
  const [birKez, setBirKez] = useState<string | null>(null);
  const [form] = Form.useForm();

  const gonder = async () => {
    const v = (await form.validateFields()) as WebhookOlustur;
    const sonuc = await olustur.mutateAsync({ ...v, olay_turleri: v.olay_turleri ?? [] });
    form.resetFields();
    setFormAcik(false);
    setBirKez(sonuc.gizli_anahtar); // tam anahtar yalnız bu yanıtta
  };

  const yenile = async (id: number) => {
    const sonuc = await anahtarYenile.mutateAsync(id);
    setBirKez(sonuc.gizli_anahtar);
  };

  const kolonlar: ColumnsType<Webhook> = [
    { title: t('entegrasyon.ad'), dataIndex: 'ad', key: 'ad' },
    {
      title: t('entegrasyon.url'),
      dataIndex: 'url',
      key: 'url',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('entegrasyon.olay_turleri'),
      dataIndex: 'olay_turleri',
      key: 'olay_turleri',
      render: (turler: string[]) =>
        turler.length ? (
          <span style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap' }}>
            {turler.map((tur) => (
              <Tag key={tur} bordered={false}>
                {tur}
              </Tag>
            ))}
          </span>
        ) : (
          <Tag bordered={false} color="blue">
            {t('entegrasyon.tum_olaylar')}
          </Tag>
        ),
    },
    {
      title: t('entegrasyon.gizli_anahtar'),
      dataIndex: 'gizli_anahtar',
      key: 'gizli_anahtar',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('entegrasyon.aktif'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean, kayit: Webhook) => (
        <Switch
          size="small"
          checked={aktif}
          disabled={!yazabilir}
          onChange={(deger) => guncelle.mutate({ id: kayit.id, aktif: deger })}
        />
      ),
    },
    ...(yazabilir
      ? [
          {
            title: '',
            key: 'aksiyon',
            align: 'right' as const,
            render: (_v: unknown, kayit: Webhook) => (
              <span style={{ display: 'inline-flex', gap: 8 }}>
                <Popconfirm
                  title={t('entegrasyon.anahtar_yenile_onay')}
                  okText={t('ortak.evet')}
                  cancelText={t('ortak.iptal')}
                  onConfirm={() => void yenile(kayit.id)}
                >
                  <Button size="small" icon={<ReloadOutlined />}>
                    {t('entegrasyon.anahtar_yenile')}
                  </Button>
                </Popconfirm>
                <Popconfirm
                  title={t('entegrasyon.sil_onay')}
                  okText={t('ortak.evet')}
                  cancelText={t('ortak.iptal')}
                  onConfirm={() => sil.mutate(kayit.id)}
                >
                  <Button size="small" danger icon={<DeleteOutlined />}>
                    {t('entegrasyon.sil')}
                  </Button>
                </Popconfirm>
              </span>
            ),
          },
        ]
      : []),
  ];

  return (
    <>
      <SunucuTablo<Webhook>
        kolonlar={kolonlar}
        veri={data?.veri ?? []}
        meta={data?.meta}
        yukleniyor={isPending}
        param={param}
        paramDegistir={paramDegistir}
        rowKey="id"
        bosMetin={isError ? t('ortak.hata_baslik') : t('entegrasyon.webhook_bos')}
        araclar={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('entegrasyon.yeni_webhook')}
            </Button>
          )
        }
      />

      <Modal
        open={formAcik}
        onCancel={() => setFormAcik(false)}
        onOk={() => void gonder()}
        title={t('entegrasyon.yeni_webhook')}
        okText={t('ortak.kaydet')}
        cancelText={t('ortak.iptal')}
        confirmLoading={olustur.isPending}
        destroyOnHidden
        maskClosable={false}
      >
        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item name="ad" label={t('entegrasyon.ad')} rules={[{ required: true }]}>
            <Input maxLength={120} placeholder={t('entegrasyon.webhook_ad_ornek')} />
          </Form.Item>
          <Form.Item
            name="url"
            label={t('entegrasyon.url')}
            rules={[{ required: true }]}
            extra={t('entegrasyon.url_aciklama')}
          >
            <Input maxLength={500} placeholder="https://erp.ornek.com/fabrikaos-webhook" />
          </Form.Item>
          <Form.Item
            name="olay_turleri"
            label={t('entegrasyon.olay_turleri')}
            extra={t('entegrasyon.olay_turleri_aciklama')}
          >
            <Select
              mode="multiple"
              allowClear
              placeholder={t('entegrasyon.tum_olaylar')}
              options={(olayTurleri ?? []).map((o) => ({
                value: o.kod,
                label: o.kod,
                title: o.aciklama,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <BirKezModal deger={birKez} kapat={() => setBirKez(null)} />
    </>
  );
}

export function WebhookSayfasi() {
  const { t } = useTranslation();

  return (
    <SayfaKapsayici enGenis={1240}>
      <SayfaBaslik baslik={t('menu.webhooklar')} alt={t('entegrasyon.alt')} />
      <Card styles={{ body: { padding: 18 } }}>
        <Tabs
          defaultActiveKey="abonelikler"
          items={[
            {
              key: 'abonelikler',
              label: t('entegrasyon.sekme_abonelikler'),
              children: <WebhookAbonelikleri />,
            },
            {
              key: 'teslimatlar',
              label: t('entegrasyon.sekme_teslimatlar'),
              children: <TeslimatGunlugu />,
            },
            {
              key: 'anahtarlar',
              label: t('entegrasyon.sekme_anahtarlar'),
              children: <ApiAnahtarSekmesi />,
            },
          ]}
        />
      </Card>
    </SayfaKapsayici>
  );
}
