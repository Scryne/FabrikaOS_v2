/**
 * İzin talebi oluşturma formu (modal). ``personelId`` verilirse personel alanı gizlenir
 * (personel detayından açıldığında). Tarih aralığı seçilir; gün sayısı sunucuda hesaplanır.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd';

import { useIzinOlustur } from './hooks';

const TURLER = ['yillik', 'mazeret', 'hastalik', 'ucretsiz', 'dogum', 'babalik'];

export function IzinFormu({
  acik,
  kapat,
  personelId,
}: {
  acik: boolean;
  kapat: () => void;
  personelId?: number;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useIzinOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ izin_turu: 'yillik', personel_id: personelId });
  }, [acik, form, personelId]);

  const gonder = async () => {
    const v = await form.validateFields();
    const [bas, bit] = v.aralik ?? [];
    const govde = {
      personel_id: v.personel_id,
      izin_turu: v.izin_turu,
      aciklama: v.aciklama ?? '',
      baslangic_tarihi: bas ? bas.format('YYYY-MM-DD') : undefined,
      bitis_tarihi: bit ? bit.format('YYYY-MM-DD') : undefined,
    };
    await olustur.mutateAsync(govde);
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('ik.izin_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        {personelId === undefined && (
          <Form.Item name="personel_id" label={t('ik.personel')} rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        )}
        <Form.Item name="izin_turu" label={t('ik.izin_turu')} rules={[{ required: true }]}>
          <Select options={TURLER.map((x) => ({ value: x, label: t(`ik.izin_turu_${x}`) }))} />
        </Form.Item>
        <Form.Item name="aralik" label={t('ik.tarih_araligi')} rules={[{ required: true }]}>
          <DatePicker.RangePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('ik.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
