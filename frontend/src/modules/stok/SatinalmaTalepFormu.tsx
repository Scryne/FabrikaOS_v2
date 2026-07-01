/**
 * Satınalma talebi oluşturma formu (modal) — dinamik çok-kalemli ``Form.List``.
 * Her kalem: malzeme (Select, en güncel 100), miktar, birim, tahmini birim fiyat.
 */

import { useTranslation } from 'react-i18next';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Form, Input, InputNumber, Modal, Select, Space } from 'antd';

import { useMalzemeler, useTalepOlustur } from './hooks';

const BIRIMLER = [
  'adet',
  'kg',
  'gram',
  'litre',
  'mililitre',
  'metre',
  'santimetre',
  'paket',
  'kutu',
  'koli',
  'ton',
  'rulo',
];

export function SatinalmaTalepFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useTalepOlustur();
  const { data: malzemeler } = useMalzemeler({ sayfa: 1, adet: 100 });
  const secenekler = (malzemeler?.veri ?? []).map((m) => ({
    value: m.id,
    label: `${m.kod} — ${m.ad}`,
  }));

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({ para_birimi: 'TRY', ...v });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('satinalma.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      width={720}
      confirmLoading={olustur.isPending}
      destroyOnClose
      maskClosable={false}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        initialValues={{ kalemler: [{ birim: 'adet', miktar: 1 }] }}
      >
        <Form.Item name="baslik" label={t('satinalma.baslik')} rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.List
          name="kalemler"
          rules={[
            {
              validator: (_, kalemler: unknown[]) =>
                kalemler && kalemler.length >= 1
                  ? Promise.resolve()
                  : Promise.reject(new Error(t('satinalma.kalemler'))),
            },
          ]}
        >
          {(alanlar, { add, remove }) => (
            <>
              {alanlar.map((alan) => (
                <Space key={alan.key} align="baseline" style={{ display: 'flex', marginBottom: 8 }}>
                  <Form.Item name={[alan.name, 'malzeme_id']} rules={[{ required: true }]}>
                    <Select
                      style={{ width: 240 }}
                      options={secenekler}
                      placeholder={t('satinalma.malzeme')}
                      showSearch
                      optionFilterProp="label"
                    />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'miktar']} rules={[{ required: true }]}>
                    <InputNumber min={0.001} placeholder={t('satinalma.miktar')} />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'birim']} rules={[{ required: true }]}>
                    <Select
                      style={{ width: 110 }}
                      options={BIRIMLER.map((b) => ({ value: b, label: b }))}
                    />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'tahmini_birim_fiyat']}>
                    <InputNumber min={0} placeholder={t('satinalma.birim_fiyat')} />
                  </Form.Item>
                  {alanlar.length > 1 && <MinusCircleOutlined onClick={() => remove(alan.name)} />}
                </Space>
              ))}
              <Button
                type="dashed"
                onClick={() => add({ birim: 'adet', miktar: 1 })}
                icon={<PlusOutlined />}
                block
              >
                {t('satinalma.kalem_ekle')}
              </Button>
            </>
          )}
        </Form.List>
      </Form>
    </Modal>
  );
}
