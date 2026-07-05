/**
 * Personel oluşturma formu (modal). KVKK: TC kimlik girişi opsiyoneldir; yanıtlarda maskeli
 * döner. Sicil no tekildir (mükerrer → sunucu 409).
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal } from 'antd';

import { usePersonelOlustur } from './hooks';

export function PersonelFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = usePersonelOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ yillik_izin_hakki: 14 });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    const govde = {
      ...v,
      dogum_tarihi: v.dogum_tarihi ? v.dogum_tarihi.format('YYYY-MM-DD') : undefined,
      ise_giris_tarihi: v.ise_giris_tarihi ? v.ise_giris_tarihi.format('YYYY-MM-DD') : undefined,
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
      title={t('ik.personel_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="sicil_no" label={t('ik.sicil_no')} rules={[{ required: true }]}>
          <Input maxLength={50} />
        </Form.Item>
        <Form.Item name="ad" label={t('ik.ad')} rules={[{ required: true }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="soyad" label={t('ik.soyad')} rules={[{ required: true }]}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="tc_kimlik_no" label={t('ik.tc_kimlik_no')} extra={t('ik.tc_kvkk')}>
          <Input maxLength={11} />
        </Form.Item>
        <Form.Item name="departman" label={t('ik.departman')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="unvan" label={t('ik.unvan')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="telefon" label={t('ik.telefon')}>
          <Input maxLength={30} />
        </Form.Item>
        <Form.Item name="eposta" label={t('ik.eposta')}>
          <Input maxLength={255} />
        </Form.Item>
        <Form.Item name="dogum_tarihi" label={t('ik.dogum_tarihi')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="ise_giris_tarihi" label={t('ik.ise_giris_tarihi')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="yillik_izin_hakki" label={t('ik.yillik_izin_hakki')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
