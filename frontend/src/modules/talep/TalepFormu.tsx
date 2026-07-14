/**
 * Talep oluşturma formu (modal). Tür + öncelik beyaz-listeden; firma opsiyonel.
 * ``hedef_tarih`` SLA hedefidir (S-VB): boş = SLA takibi yok.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd';
import type { Dayjs } from 'dayjs';

import { useTalepOlustur } from './hooks';

const TURLER = ['teklif', 'destek', 'sikayet', 'bilgi', 'diger'];
const ONCELIKLER = ['dusuk', 'orta', 'yuksek'];

export function TalepFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useTalepOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ tur: 'destek', oncelik: 'orta' });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    const hedef = v.hedef_tarih as Dayjs | undefined;
    await olustur.mutateAsync({
      ...v,
      hedef_tarih: hedef ? hedef.toISOString() : null,
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('talep.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="baslik" label={t('talep.baslik')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="tur" label={t('talep.tur')} rules={[{ required: true }]}>
          <Select options={TURLER.map((x) => ({ value: x, label: t(`talep.tur_${x}`) }))} />
        </Form.Item>
        <Form.Item name="oncelik" label={t('talep.oncelik')} rules={[{ required: true }]}>
          <Select options={ONCELIKLER.map((x) => ({ value: x, label: t(`talep.oncelik_${x}`) }))} />
        </Form.Item>
        <Form.Item name="firma_id" label={t('talep.firma')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="talep_eden_ad" label={t('talep.talep_eden_ad')}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="hedef_tarih" label={t('talep.hedef_tarih')} extra={t('talep.hedef_ipucu')}>
          <DatePicker showTime={{ format: 'HH:mm' }} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('talep.aciklama')}>
          <Input.TextArea rows={3} maxLength={2000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
