/** Firma oluşturma/düzenleme formu (modal). Tip beyaz-listeden. */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, Modal, Select, Switch } from 'antd';

import { type Firma, useFirmaGuncelle, useFirmaOlustur } from './hooks';

const TIPLER = ['musteri', 'tedarikci', 'her_ikisi'];

export function FirmaFormu({
  acik,
  kapat,
  mevcut,
}: {
  acik: boolean;
  kapat: () => void;
  mevcut?: Firma | null;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useFirmaOlustur();
  const guncelle = useFirmaGuncelle();
  const duzenleme = mevcut != null;

  useEffect(() => {
    if (acik) {
      if (mevcut) form.setFieldsValue(mevcut);
      else form.setFieldsValue({ tip: 'musteri', aktif: true });
    }
  }, [acik, mevcut, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    if (duzenleme && mevcut) await guncelle.mutateAsync({ id: mevcut.id, govde: v });
    else await olustur.mutateAsync(v);
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={duzenleme ? t('crm.firma_duzenle') : t('crm.yeni_firma')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending || guncelle.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="ad" label={t('crm.ad')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="tip" label={t('crm.tip')} rules={[{ required: true }]}>
          <Select options={TIPLER.map((x) => ({ value: x, label: t(`crm.tip_${x}`) }))} />
        </Form.Item>
        <Form.Item name="sektor" label={t('crm.sektor')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="il" label={t('crm.il')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="vergi_no" label={t('crm.vergi_no')}>
          <Input maxLength={20} />
        </Form.Item>
        <Form.Item name="telefon" label={t('crm.telefon')}>
          <Input maxLength={30} />
        </Form.Item>
        <Form.Item name="eposta" label={t('crm.eposta')}>
          <Input maxLength={255} />
        </Form.Item>
        <Form.Item name="adres" label={t('crm.adres')}>
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
        <Form.Item name="aktif" label={t('crm.aktif')} valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}
