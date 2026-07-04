/**
 * Personel alt-kayıt formları (modal): fazla mesai, zimmet, sertifika. Her biri ``personelId``
 * için kayıt açar; ilgili alt-liste mutasyon sonrası canlı invalidate edilir.
 */

import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal } from 'antd';

import { useMesaiOlustur, useSertifikaOlustur, useZimmetOlustur } from './hooks';

type FormProps = { acik: boolean; kapat: () => void; personelId: number };

export function MesaiFormu({ acik, kapat, personelId }: FormProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useMesaiOlustur();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      personel_id: personelId,
      tarih: v.tarih.format('YYYY-MM-DD'),
      saat: v.saat,
      aciklama: v.aciklama ?? '',
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('ik.mesai_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="tarih" label={t('ik.tarih')} rules={[{ required: true }]}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="saat" label={t('ik.saat')} rules={[{ required: true }]}>
          <InputNumber min={0.5} step={0.5} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('ik.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function ZimmetFormu({ acik, kapat, personelId }: FormProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useZimmetOlustur();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      personel_id: personelId,
      demirbas: v.demirbas,
      seri_no: v.seri_no ?? '',
      zimmet_tarihi: v.zimmet_tarihi.format('YYYY-MM-DD'),
      aciklama: v.aciklama ?? '',
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('ik.zimmet_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="demirbas" label={t('ik.demirbas')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="seri_no" label={t('ik.seri_no')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="zimmet_tarihi" label={t('ik.zimmet_tarihi')} rules={[{ required: true }]}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('ik.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function SertifikaFormu({ acik, kapat, personelId }: FormProps) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useSertifikaOlustur();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      personel_id: personelId,
      ad: v.ad,
      kurum: v.kurum ?? '',
      belge_no: v.belge_no ?? '',
      alinma_tarihi: v.alinma_tarihi.format('YYYY-MM-DD'),
      gecerlilik_tarihi: v.gecerlilik_tarihi ? v.gecerlilik_tarihi.format('YYYY-MM-DD') : undefined,
      aciklama: v.aciklama ?? '',
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('ik.sertifika_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="ad" label={t('ik.sertifika_ad')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="kurum" label={t('ik.kurum')}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="belge_no" label={t('ik.belge_no')}>
          <Input maxLength={100} />
        </Form.Item>
        <Form.Item name="alinma_tarihi" label={t('ik.alinma_tarihi')} rules={[{ required: true }]}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="gecerlilik_tarihi" label={t('ik.gecerlilik_tarihi')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('ik.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
