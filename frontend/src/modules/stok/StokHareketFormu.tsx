/**
 * Stok hareketi formu (modal). ``malzeme`` seçiliyse açılır; tür giriş/çıkış/düzeltme,
 * miktar > 0. ``düzeltme`` mutlak yeni bakiyedir (sayım). Submit → bakiye + kritik canlı yansır.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, InputNumber, Modal, Select } from 'antd';

import { type Malzeme, useStokHareketEkle } from './hooks';

export function StokHareketFormu({
  malzeme,
  kapat,
}: {
  malzeme: Malzeme | null;
  kapat: () => void;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const ekle = useStokHareketEkle();

  useEffect(() => {
    if (malzeme) form.setFieldsValue({ tur: 'giris', miktar: 1, aciklama: '' });
  }, [malzeme, form]);

  const gonder = async () => {
    if (!malzeme) return;
    const v = await form.validateFields();
    await ekle.mutateAsync({ malzeme_id: malzeme.id, ...v });
    kapat();
  };

  return (
    <Modal
      open={malzeme != null}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={`${t('stok.hareket_ekle')} — ${malzeme?.kod ?? ''}`}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={ekle.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="tur" label={t('stok.tur')} rules={[{ required: true }]}>
          <Select
            options={[
              { value: 'giris', label: t('stok.giris') },
              { value: 'cikis', label: t('stok.cikis') },
              { value: 'duzeltme', label: t('stok.duzeltme') },
            ]}
          />
        </Form.Item>
        <Form.Item name="miktar" label={t('stok.miktar')} rules={[{ required: true }]}>
          <InputNumber min={0.001} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('stok.aciklama')}>
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
