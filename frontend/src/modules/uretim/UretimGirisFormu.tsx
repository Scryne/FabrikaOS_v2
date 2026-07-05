/**
 * Üretim verisi giriş formu (modal). OEE girdileri: planlanan/duruş süresi, toplam/sağlam adet,
 * ideal çevrim. ``makineId`` verilirse makine alanı önseçili ve kilitli gelir (makine detayından).
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Col, Form, InputNumber, Modal, Row, Select } from 'antd';

import { useMakineSecenekleri, useUretimGiris } from './hooks';

type Alanlar = {
  makine_id: number;
  vardiya?: string;
  planlanan_sure_dk: number;
  durus_sure_dk: number;
  toplam_adet: number;
  saglam_adet: number;
  ideal_cevrim_sn: number;
};

const VARDIYALAR = ['Gündüz', 'Gece', 'Vardiya 3'];

export function UretimGirisFormu({
  acik,
  kapat,
  makineId,
}: {
  acik: boolean;
  kapat: () => void;
  makineId?: number;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm<Alanlar>();
  const { data: makineler } = useMakineSecenekleri();
  const giris = useUretimGiris();

  useEffect(() => {
    if (acik && makineId) form.setFieldsValue({ makine_id: makineId });
  }, [acik, makineId, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    await giris.mutateAsync({ ...v, makine_id: makineId ?? v.makine_id });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      width={560}
      title={t('uretim.uretim_girisi')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={giris.isPending}
      onOk={() => void gonder()}
      onCancel={() => {
        form.resetFields();
        kapat();
      }}
      destroyOnHidden
      maskClosable={false}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        preserve={false}
        initialValues={{ durus_sure_dk: 0 }}
      >
        <Row gutter={16}>
          <Col span={14}>
            <Form.Item
              name="makine_id"
              label={t('uretim.makine')}
              rules={[{ required: true, message: t('uretim.makine_gerekli') }]}
            >
              <Select
                disabled={makineId != null}
                showSearch
                optionFilterProp="label"
                placeholder={t('uretim.makine_sec')}
                options={(makineler ?? []).map((m) => ({
                  value: m.id,
                  label: `${m.kod} · ${m.ad}`,
                }))}
              />
            </Form.Item>
          </Col>
          <Col span={10}>
            <Form.Item name="vardiya" label={t('uretim.vardiya')}>
              <Select
                allowClear
                placeholder={t('uretim.vardiya_sec')}
                options={VARDIYALAR.map((v) => ({ value: v, label: v }))}
              />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={12}>
            <Form.Item
              name="planlanan_sure_dk"
              label={t('uretim.planlanan_sure')}
              rules={[{ required: true, message: t('uretim.zorunlu') }]}
            >
              <InputNumber min={0} style={{ width: '100%' }} addonAfter={t('pano.birim_dk')} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="durus_sure_dk" label={t('uretim.durus_sure')}>
              <InputNumber min={0} style={{ width: '100%' }} addonAfter={t('pano.birim_dk')} />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col span={8}>
            <Form.Item
              name="toplam_adet"
              label={t('uretim.toplam_adet')}
              rules={[{ required: true, message: t('uretim.zorunlu') }]}
            >
              <InputNumber min={0} precision={0} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="saglam_adet"
              label={t('uretim.saglam_adet')}
              dependencies={['toplam_adet']}
              rules={[
                { required: true, message: t('uretim.zorunlu') },
                ({ getFieldValue }) => ({
                  validator(_, deger) {
                    if (deger == null || deger <= getFieldValue('toplam_adet')) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error(t('uretim.saglam_toplami_asamaz')));
                  },
                }),
              ]}
            >
              <InputNumber min={0} precision={0} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item
              name="ideal_cevrim_sn"
              label={t('uretim.ideal_cevrim')}
              rules={[{ required: true, message: t('uretim.zorunlu') }]}
            >
              <InputNumber min={0} style={{ width: '100%' }} addonAfter="sn" />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </Modal>
  );
}
