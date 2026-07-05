/**
 * Bakım planı oluşturma formu (modal). Makine beyaz-listeden seçilir; tip önleyici/kestirimci/
 * periyodik; periyot + son/sonraki bakım tarihleri opsiyoneldir.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd';

import { useMakineSecenekleri } from '@/modules/uretim/hooks';

import { BAKIM_TIPLERI, useBakimPlaniOlustur } from './hooks';

export function BakimPlaniFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const { data: makineler } = useMakineSecenekleri();
  const olustur = useBakimPlaniOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ tip: 'onleyici' });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    const govde = {
      ...v,
      son_bakim_tarihi: v.son_bakim_tarihi ? v.son_bakim_tarihi.toISOString() : undefined,
      sonraki_bakim_tarihi: v.sonraki_bakim_tarihi
        ? v.sonraki_bakim_tarihi.toISOString()
        : undefined,
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
      title={t('bakim.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="makine_id" label={t('bakim.makine')} rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={t('bakim.makine_sec')}
            options={(makineler ?? []).map((m) => ({ value: m.id, label: `${m.kod} — ${m.ad}` }))}
          />
        </Form.Item>
        <Form.Item name="ad" label={t('bakim.ad')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="tip" label={t('bakim.tip')} rules={[{ required: true }]}>
          <Select options={BAKIM_TIPLERI.map((x) => ({ value: x, label: t(`bakim.tip_${x}`) }))} />
        </Form.Item>
        <Form.Item name="periyot_gun" label={t('bakim.periyot_gun')}>
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="son_bakim_tarihi" label={t('bakim.son_bakim')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="sonraki_bakim_tarihi" label={t('bakim.sonraki_bakim')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('bakim.aciklama')}>
          <Input.TextArea rows={3} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
