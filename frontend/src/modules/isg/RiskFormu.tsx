/**
 * Risk değerlendirme oluşturma formu (modal). Olasılık × Şiddet (1..5) seçilir; skor ve
 * seviye canlı önizlenir (nihai hesap sunucuda). Önlem + durum + geçerlilik tarihi opsiyonel.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, Modal, Select, Space } from 'antd';

import { useRiskOlustur } from './hooks';
import { riskSeviyesi, riskSkoru } from './riskMatris';
import { RiskSeviyeEtiketi } from './rozetler';

const BIRDEN_BESE = [1, 2, 3, 4, 5];
const DURUMLAR = ['acik', 'devam', 'kapandi'];

export function RiskFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useRiskOlustur();
  const olasilik = Form.useWatch('olasilik', form) ?? 3;
  const siddet = Form.useWatch('siddet', form) ?? 3;
  const skor = riskSkoru(olasilik, siddet);

  useEffect(() => {
    if (acik) form.setFieldsValue({ olasilik: 3, siddet: 3, durum: 'acik' });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    const govde = {
      ...v,
      gecerlilik_tarihi: v.gecerlilik_tarihi ? v.gecerlilik_tarihi.format('YYYY-MM-DD') : undefined,
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
      title={t('isg.risk_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="baslik" label={t('isg.baslik')} rules={[{ required: true }]}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="bolum" label={t('isg.bolum')}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item name="tehlike" label={t('isg.tehlike')}>
          <Input.TextArea rows={2} maxLength={2000} />
        </Form.Item>
        <Space size="large" style={{ display: 'flex' }}>
          <Form.Item name="olasilik" label={t('isg.olasilik')} rules={[{ required: true }]}>
            <Select
              style={{ width: 90 }}
              options={BIRDEN_BESE.map((x) => ({ value: x, label: String(x) }))}
            />
          </Form.Item>
          <Form.Item name="siddet" label={t('isg.siddet')} rules={[{ required: true }]}>
            <Select
              style={{ width: 90 }}
              options={BIRDEN_BESE.map((x) => ({ value: x, label: String(x) }))}
            />
          </Form.Item>
          <Form.Item label={t('isg.risk_skoru')}>
            <Space>
              <span className="sayisal">{skor}</span>
              <RiskSeviyeEtiketi seviye={riskSeviyesi(skor)} />
            </Space>
          </Form.Item>
        </Space>
        <Form.Item name="onlem" label={t('isg.onlem')}>
          <Input.TextArea rows={2} maxLength={2000} />
        </Form.Item>
        <Form.Item name="durum" label={t('isg.risk_durum')}>
          <Select options={DURUMLAR.map((x) => ({ value: x, label: t(`isg.risk_durum_${x}`) }))} />
        </Form.Item>
        <Form.Item name="gecerlilik_tarihi" label={t('isg.gecerlilik_tarihi')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
