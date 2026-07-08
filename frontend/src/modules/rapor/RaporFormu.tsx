/** Yeni rapor modalı — tür + biçim + dönem seçimi → 202 (üretim arka planda başlar). */

import { useTranslation } from 'react-i18next';
import { Form, Modal, Radio, Segmented, Select } from 'antd';

import { useRaporOlustur } from './hooks';
import { RAPOR_BICIMLERI, RAPOR_TURLERI, type RaporOlustur } from './sunum';

export function RaporFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<RaporOlustur>();
  const olustur = useRaporOlustur();

  const gonder = (degerler: RaporOlustur) => {
    olustur.mutate(degerler, {
      onSuccess: () => {
        form.resetFields();
        kapat();
      },
    });
  };

  return (
    <Modal
      title={t('rapor.yeni')}
      open={acik}
      onCancel={kapat}
      onOk={() => form.submit()}
      okText={t('rapor.uret')}
      cancelText={t('ortak.vazgec')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
    >
      <Form<RaporOlustur>
        form={form}
        layout="vertical"
        onFinish={gonder}
        initialValues={{ tur: 'uretim', bicim: 'pdf', gun: 30 }}
      >
        <Form.Item name="tur" label={t('rapor.tur')} rules={[{ required: true }]}>
          <Select
            options={RAPOR_TURLERI.map((tur) => ({
              value: tur,
              label: t(`rapor.tur_${tur}`),
            }))}
          />
        </Form.Item>
        <Form.Item name="bicim" label={t('rapor.bicim')} rules={[{ required: true }]}>
          <Radio.Group>
            {RAPOR_BICIMLERI.map((bicim) => (
              <Radio.Button key={bicim} value={bicim}>
                {bicim.toUpperCase()}
              </Radio.Button>
            ))}
          </Radio.Group>
        </Form.Item>
        <Form.Item name="gun" label={t('rapor.donem')} rules={[{ required: true }]}>
          <Segmented
            options={[7, 30, 90].map((g) => ({
              label: t('analitik.gun_n', { n: g }),
              value: g,
            }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
