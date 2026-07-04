/**
 * İş kazası / ramak-kala kaydı oluşturma formu (modal). Tür + ağırlık beyaz-listeden;
 * olay tarihi + yer + açıklama; opsiyonel personel/makine bağı.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd';

import { useKazaOlustur } from './hooks';

const TURLER = ['kaza', 'ramak_kala', 'meslek_hastaligi'];
const AGIRLIKLAR = ['hafif', 'orta', 'agir', 'olumcul'];

export function KazaFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useKazaOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ tur: 'kaza', agirlik: 'hafif', kaybedilen_gun: 0 });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    const govde = {
      ...v,
      olay_tarihi: v.olay_tarihi ? v.olay_tarihi.toISOString() : undefined,
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
      title={t('isg.kaza_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="tur" label={t('isg.tur')} rules={[{ required: true }]}>
          <Select options={TURLER.map((x) => ({ value: x, label: t(`isg.tur_${x}`) }))} />
        </Form.Item>
        <Form.Item name="agirlik" label={t('isg.agirlik')} rules={[{ required: true }]}>
          <Select options={AGIRLIKLAR.map((x) => ({ value: x, label: t(`isg.agirlik_${x}`) }))} />
        </Form.Item>
        <Form.Item name="olay_tarihi" label={t('isg.olay_tarihi')}>
          <DatePicker showTime style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="yer" label={t('isg.yer')}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="yaralanma_turu" label={t('isg.yaralanma_turu')}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="kaybedilen_gun" label={t('isg.kaybedilen_gun')}>
          <InputNumber min={0} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="personel_id" label={t('isg.personel')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="makine_id" label={t('isg.makine')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('isg.aciklama')}>
          <Input.TextArea rows={3} maxLength={2000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
