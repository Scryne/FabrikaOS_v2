/** Makine oluşturma formu (modal). OEE hedefi yüzde girilir, API'ye 0–1 oran olarak gider. */

import { useTranslation } from 'react-i18next';
import { Form, Input, InputNumber, Modal } from 'antd';

import { useMakineOlustur } from './hooks';

type Alanlar = { kod: string; ad: string; oee_hedefi_yuzde?: number };

export function MakineFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<Alanlar>();
  const olustur = useMakineOlustur();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      kod: v.kod.trim(),
      ad: v.ad.trim(),
      oee_hedefi: v.oee_hedefi_yuzde != null ? v.oee_hedefi_yuzde / 100 : null,
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      title={t('uretim.makine_ekle')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      onOk={() => void gonder()}
      onCancel={() => {
        form.resetFields();
        kapat();
      }}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional" preserve={false}>
        <Form.Item
          name="kod"
          label={t('uretim.kod')}
          rules={[{ required: true, message: t('uretim.kod_gerekli') }, { max: 50 }]}
        >
          <Input placeholder="MAK-A1" autoFocus />
        </Form.Item>
        <Form.Item
          name="ad"
          label={t('uretim.ad')}
          rules={[{ required: true, message: t('uretim.ad_gerekli') }, { max: 200 }]}
        >
          <Input placeholder={t('uretim.ad_ipucu')} />
        </Form.Item>
        <Form.Item name="oee_hedefi_yuzde" label={t('uretim.oee_hedefi')}>
          <InputNumber
            min={0}
            max={100}
            style={{ width: '100%' }}
            addonAfter="%"
            placeholder="85"
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
