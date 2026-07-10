/**
 * API anahtarları sekmesi — 3. taraf (ERP/e-Fatura) erişim anahtarları.
 * Düz anahtar yalnız oluşturmada gösterilir (BirKezModal); listede önek + kapsam çipleri.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Form, Input, Modal, Popconfirm, Select, Switch, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { BirKezModal } from './BirKezModal';
import {
  API_KAPSAMLARI,
  type ApiAnahtari,
  useApiAnahtarGuncelle,
  useApiAnahtarlari,
  useApiAnahtarOlustur,
  useApiAnahtarSil,
} from './hooks';

function tarih(v: string | null | undefined): string {
  return v ? new Date(v).toLocaleString('tr-TR') : '—';
}

export function ApiAnahtarSekmesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('entegrasyon:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useApiAnahtarlari(param);
  const olustur = useApiAnahtarOlustur();
  const guncelle = useApiAnahtarGuncelle();
  const sil = useApiAnahtarSil();
  const [formAcik, setFormAcik] = useState(false);
  const [birKez, setBirKez] = useState<string | null>(null);
  const [form] = Form.useForm();

  const gonder = async () => {
    const v = (await form.validateFields()) as { ad: string; izinler: string[] };
    const sonuc = await olustur.mutateAsync(v);
    form.resetFields();
    setFormAcik(false);
    setBirKez(sonuc.anahtar ?? null); // tam anahtar yalnız bu yanıtta
  };

  const kolonlar: ColumnsType<ApiAnahtari> = [
    { title: t('entegrasyon.ad'), dataIndex: 'ad', key: 'ad' },
    {
      title: t('entegrasyon.onek'),
      dataIndex: 'onek',
      key: 'onek',
      render: (v: string) => <span className="sayisal">{v}…</span>,
    },
    {
      title: t('entegrasyon.kapsamlar'),
      dataIndex: 'izinler',
      key: 'izinler',
      render: (izinler: string[]) => (
        <span style={{ display: 'inline-flex', gap: 4, flexWrap: 'wrap' }}>
          {izinler.map((k) => (
            <Tag key={k} bordered={false}>
              {k}
            </Tag>
          ))}
        </span>
      ),
    },
    {
      title: t('entegrasyon.son_kullanim'),
      dataIndex: 'son_kullanim_tarihi',
      key: 'son_kullanim_tarihi',
      render: (v: string | null) => <span className="sayisal">{tarih(v)}</span>,
    },
    {
      title: t('entegrasyon.aktif'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean, kayit: ApiAnahtari) => (
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
            render: (_v: unknown, kayit: ApiAnahtari) => (
              <Popconfirm
                title={t('entegrasyon.anahtar_sil_onay')}
                okText={t('ortak.evet')}
                cancelText={t('ortak.iptal')}
                onConfirm={() => sil.mutate(kayit.id)}
              >
                <Button size="small" danger icon={<DeleteOutlined />}>
                  {t('entegrasyon.sil')}
                </Button>
              </Popconfirm>
            ),
          },
        ]
      : []),
  ];

  return (
    <>
      <SunucuTablo<ApiAnahtari>
        kolonlar={kolonlar}
        veri={data?.veri ?? []}
        meta={data?.meta}
        yukleniyor={isPending}
        param={param}
        paramDegistir={paramDegistir}
        rowKey="id"
        bosMetin={isError ? t('ortak.hata_baslik') : t('entegrasyon.anahtar_bos')}
        araclar={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('entegrasyon.yeni_anahtar')}
            </Button>
          )
        }
      />

      <Modal
        open={formAcik}
        onCancel={() => setFormAcik(false)}
        onOk={() => void gonder()}
        title={t('entegrasyon.yeni_anahtar')}
        okText={t('ortak.kaydet')}
        cancelText={t('ortak.iptal')}
        confirmLoading={olustur.isPending}
        destroyOnHidden
        maskClosable={false}
      >
        <Form form={form} layout="vertical" requiredMark="optional">
          <Form.Item name="ad" label={t('entegrasyon.ad')} rules={[{ required: true }]}>
            <Input maxLength={120} placeholder={t('entegrasyon.anahtar_ad_ornek')} />
          </Form.Item>
          <Form.Item
            name="izinler"
            label={t('entegrasyon.kapsamlar')}
            rules={[{ required: true, message: t('entegrasyon.kapsam_zorunlu') }]}
            extra={t('entegrasyon.kapsam_aciklama')}
          >
            <Select
              mode="multiple"
              allowClear
              placeholder={t('entegrasyon.kapsam_sec')}
              options={API_KAPSAMLARI.map((k) => ({ value: k, label: k }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <BirKezModal deger={birKez} kapat={() => setBirKez(null)} />
    </>
  );
}
