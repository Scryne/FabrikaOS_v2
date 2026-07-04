/** Ortak (kontak) ekleme formu (modal) — bir firmaya bağlı. */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, Modal, Switch } from 'antd';

import { useOrtakOlustur } from './hooks';

export function OrtakFormu({
  acik,
  kapat,
  firmaId,
}: {
  acik: boolean;
  kapat: () => void;
  firmaId: number;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useOrtakOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ birincil: false });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({ ...v, firma_id: firmaId });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('crm.yeni_ortak')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="ad_soyad" label={t('crm.ad_soyad')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="unvan" label={t('crm.unvan')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="telefon" label={t('crm.telefon')}>
          <Input maxLength={30} />
        </Form.Item>
        <Form.Item name="eposta" label={t('crm.eposta')}>
          <Input maxLength={255} />
        </Form.Item>
        <Form.Item name="birincil" label={t('crm.birincil')} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
