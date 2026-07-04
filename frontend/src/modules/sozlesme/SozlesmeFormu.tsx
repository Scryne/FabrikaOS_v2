/** Sözleşme oluşturma/düzenleme formu (modal). Tarihler DatePicker; ISO-8601 (YYYY-MM-DD). */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd';
import dayjs from 'dayjs';

import { type Sozlesme, useSozlesmeGuncelle, useSozlesmeOlustur } from './hooks';

const TURLER = ['satis', 'alis', 'hizmet', 'nda', 'kira', 'diger'];

export function SozlesmeFormu({
  acik,
  kapat,
  mevcut,
  firmaId,
}: {
  acik: boolean;
  kapat: () => void;
  mevcut?: Sozlesme | null;
  firmaId?: number;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useSozlesmeOlustur();
  const guncelle = useSozlesmeGuncelle();
  const duzenleme = mevcut != null;

  useEffect(() => {
    if (!acik) return;
    if (mevcut) {
      form.setFieldsValue({
        ...mevcut,
        baslangic_tarihi: dayjs(mevcut.baslangic_tarihi),
        bitis_tarihi: dayjs(mevcut.bitis_tarihi),
      });
    } else {
      form.setFieldsValue({ tur: 'hizmet', para_birimi: 'TRY', tutar: 0, firma_id: firmaId });
    }
  }, [acik, mevcut, firmaId, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    const govde = {
      ...v,
      baslangic_tarihi: v.baslangic_tarihi.format('YYYY-MM-DD'),
      bitis_tarihi: v.bitis_tarihi.format('YYYY-MM-DD'),
    };
    if (duzenleme && mevcut) {
      // firma_id düzenlemede değişmez; SozlesmeGuncelleDTO'da yer almaz (backend yok sayar).
      await guncelle.mutateAsync({ id: mevcut.id, govde });
    } else {
      await olustur.mutateAsync(govde);
    }
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={duzenleme ? t('sozlesme.duzenle') : t('sozlesme.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending || guncelle.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="firma_id" label={t('sozlesme.firma')} rules={[{ required: true }]}>
          <InputNumber min={1} style={{ width: '100%' }} disabled={duzenleme} />
        </Form.Item>
        <Form.Item name="baslik" label={t('sozlesme.baslik')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="tur" label={t('sozlesme.tur')} rules={[{ required: true }]}>
          <Select options={TURLER.map((x) => ({ value: x, label: t(`sozlesme.tur_${x}`) }))} />
        </Form.Item>
        <Form.Item
          name="baslangic_tarihi"
          label={t('sozlesme.baslangic')}
          rules={[{ required: true }]}
        >
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="bitis_tarihi" label={t('sozlesme.bitis')} rules={[{ required: true }]}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="tutar" label={t('sozlesme.tutar')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="para_birimi" label={t('sozlesme.para_birimi')}>
          <Input maxLength={3} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('sozlesme.aciklama')}>
          <Input.TextArea rows={2} maxLength={2000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
