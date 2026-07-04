/** Belge (üstveri) oluşturma formu (modal). İçerik ayrıca sürüm olarak yüklenir. */

import { useTranslation } from 'react-i18next';
import { Form, Input, Modal } from 'antd';

import { useBelgeOlustur } from './hooks';

export function BelgeFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useBelgeOlustur();

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
      title={t('dys.yeni_belge')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="ad" label={t('dys.ad')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="kategori" label={t('dys.kategori')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('dys.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
