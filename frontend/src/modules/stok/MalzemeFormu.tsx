/**
 * Malzeme oluşturma/düzenleme formu (modal). ``malzeme`` verilirse düzenleme (``kod`` sabit),
 * yoksa oluşturma. Miktar eşikleri (min/max/kritik) InputNumber; birim beyaz-listeden Select.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, InputNumber, Modal, Select } from 'antd';

import { type Malzeme, useMalzemeGuncelle, useMalzemeOlustur } from './hooks';

const BIRIMLER = [
  'adet',
  'kg',
  'gram',
  'litre',
  'mililitre',
  'metre',
  'santimetre',
  'paket',
  'kutu',
  'koli',
  'ton',
  'rulo',
];

export function MalzemeFormu({
  acik,
  kapat,
  malzeme,
}: {
  acik: boolean;
  kapat: () => void;
  malzeme?: Malzeme;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useMalzemeOlustur();
  const guncelle = useMalzemeGuncelle();
  const duzenleme = malzeme != null;

  useEffect(() => {
    if (acik) form.setFieldsValue(malzeme ?? { birim: 'adet', min_stok: 0, kritik_stok: 0 });
  }, [acik, malzeme, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    if (duzenleme) await guncelle.mutateAsync({ id: malzeme.id, govde: v });
    else await olustur.mutateAsync(v);
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={duzenleme ? t('stok.duzenle') : t('stok.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending || guncelle.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        {!duzenleme && (
          <Form.Item name="kod" label={t('stok.kod')} rules={[{ required: true }, { max: 50 }]}>
            <Input autoFocus />
          </Form.Item>
        )}
        <Form.Item name="ad" label={t('stok.ad')} rules={[{ required: true }, { max: 200 }]}>
          <Input />
        </Form.Item>
        <Form.Item name="birim" label={t('stok.birim')} rules={[{ required: true }]}>
          <Select options={BIRIMLER.map((b) => ({ value: b, label: b }))} />
        </Form.Item>
        <Form.Item name="kategori" label={t('stok.kategori')}>
          <Input />
        </Form.Item>
        <Form.Item name="min_stok" label={t('stok.min')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="max_stok" label={t('stok.max')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="kritik_stok" label={t('stok.kritik_esik')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
