/**
 * Kalite kontrol kaydı oluşturma formu (modal). Sonuç zorunlu (gecti/kaldi/sartli);
 * kontrol türü beyaz-listeden. Ölçüm/limit alanları opsiyonel InputNumber.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, InputNumber, Modal, Select } from 'antd';

import { useKontrolOlustur } from './hooks';

const KONTROL_TURLERI = ['uretim', 'giris', 'final'];
const SONUCLAR = ['gecti', 'kaldi', 'sartli'];

export function KaliteKontrolFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useKontrolOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ kontrol_turu: 'uretim', numune_adedi: 0, uygunsuz_adet: 0 });
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
      title={t('kalite.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item
          name="kontrol_turu"
          label={t('kalite.kontrol_turu')}
          rules={[{ required: true }]}
        >
          <Select
            options={KONTROL_TURLERI.map((x) => ({ value: x, label: t(`kalite.tur_${x}`) }))}
          />
        </Form.Item>
        <Form.Item name="sonuc" label={t('kalite.sonuc')} rules={[{ required: true }]}>
          <Select options={SONUCLAR.map((x) => ({ value: x, label: t(`kalite.sonuc_${x}`) }))} />
        </Form.Item>
        <Form.Item name="makine_id" label={t('kalite.makine')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="is_emri_id" label={t('kalite.is_emri')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="olculen_deger" label={t('kalite.olculen_deger')}>
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="alt_limit" label={t('kalite.alt_limit')}>
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="ust_limit" label={t('kalite.ust_limit')}>
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="numune_adedi" label={t('kalite.numune_adedi')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="uygunsuz_adet" label={t('kalite.uygunsuz_adet')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('kalite.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
