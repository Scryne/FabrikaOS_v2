/** Duyuru oluşturma formu (modal). Önem beyaz-listeden. */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, Modal, Select } from 'antd';

import { useDuyuruOlustur } from './hooks';

const ONEMLER = ['bilgi', 'uyari', 'kritik'];

export function DuyuruFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useDuyuruOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ onem: 'bilgi' });
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
      title={t('duyuru.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="baslik" label={t('duyuru.baslik')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="onem" label={t('duyuru.onem')} rules={[{ required: true }]}>
          <Select options={ONEMLER.map((x) => ({ value: x, label: t(`duyuru.onem_${x}`) }))} />
        </Form.Item>
        <Form.Item name="hedef_departman" label={t('duyuru.hedef_departman')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="icerik" label={t('duyuru.icerik')}>
          <Input.TextArea rows={4} maxLength={5000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
