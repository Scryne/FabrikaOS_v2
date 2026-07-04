/**
 * Enerji tüketim ölçümü giriş formu (modal). Tür beyaz-listeden; tüketim > 0 zorunlu;
 * birim öntanımlı "kWh". Makine opsiyonel (boşsa tesis geneli). Zaman opsiyonel (boşsa şimdi).
 */

import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd';
import type { Dayjs } from 'dayjs';

import { useOlcumEkle } from './hooks';

type Alanlar = {
  enerji_turu: string;
  tuketim: number;
  birim: string;
  makine_id?: number;
  zaman?: Dayjs;
};

const TURLER = ['elektrik', 'dogalgaz', 'su', 'hava', 'buhar'];

export function EnerjiGirisFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<Alanlar>();
  const olcumEkle = useOlcumEkle();

  const gonder = async () => {
    const v = await form.validateFields();
    await olcumEkle.mutateAsync({
      enerji_turu: v.enerji_turu,
      tuketim: v.tuketim,
      birim: v.birim,
      makine_id: v.makine_id,
      zaman: v.zaman ? v.zaman.toISOString() : undefined,
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('enerji.olcum_ekle')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olcumEkle.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        preserve={false}
        initialValues={{ birim: 'kWh' }}
      >
        <Form.Item name="enerji_turu" label={t('enerji.enerji_turu')} rules={[{ required: true }]}>
          <Select options={TURLER.map((x) => ({ value: x, label: t(`enerji.tur_${x}`) }))} />
        </Form.Item>
        <Form.Item
          name="tuketim"
          label={t('enerji.tuketim')}
          rules={[{ required: true, type: 'number', min: 0.001 }]}
        >
          <InputNumber min={0.001} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="birim" label={t('enerji.birim')} rules={[{ required: true }, { max: 20 }]}>
          <Input />
        </Form.Item>
        <Form.Item name="makine_id" label={t('enerji.makine')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="zaman" label={t('enerji.zaman')}>
          <DatePicker showTime style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
