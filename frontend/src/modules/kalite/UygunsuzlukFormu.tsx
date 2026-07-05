/**
 * Uygunsuzluk (CAPA vakası) oluşturma formu (modal). Başlık zorunlu; önem beyaz-listeden.
 * Makine / kaynak kontrol / sorumlu opsiyonel. Yeni vaka ``acik`` durumunda başlar.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, InputNumber, Modal, Select } from 'antd';

import { useUygunsuzlukOlustur } from './hooks';

const ONEMLER = ['dusuk', 'orta', 'yuksek', 'kritik'];

export function UygunsuzlukFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useUygunsuzlukOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ onem: 'orta' });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync(v);
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('kalite.yeni_uygunsuzluk')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item
          name="baslik"
          label={t('kalite.baslik')}
          rules={[{ required: true }, { max: 200 }]}
        >
          <Input autoFocus />
        </Form.Item>
        <Form.Item name="aciklama" label={t('kalite.aciklama')}>
          <Input.TextArea rows={3} maxLength={2000} />
        </Form.Item>
        <Form.Item name="onem" label={t('kalite.onem')} rules={[{ required: true }]}>
          <Select options={ONEMLER.map((x) => ({ value: x, label: t(`kalite.onem_${x}`) }))} />
        </Form.Item>
        <Form.Item name="makine_id" label={t('kalite.makine')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="kaynak_kontrol_id" label={t('kalite.kaynak_kontrol')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="sorumlu_kullanici_id" label={t('kalite.sorumlu')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
