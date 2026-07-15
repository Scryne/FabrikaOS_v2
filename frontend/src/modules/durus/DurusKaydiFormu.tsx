/**
 * Duruş kaydı oluşturma formu (modal). Makine + neden beyaz-listeden seçilir; aralık
 * RangePicker'dır (bitiş > başlangıç doğrulaması backend'de de zorlanır — 422).
 */

import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, Modal, Select } from 'antd';
import type { Dayjs } from 'dayjs';

import { useMakineSecenekleri } from '@/modules/uretim/hooks';

import { useDurusKaydiOlustur, useDurusNedenleri } from './hooks';

type Alanlar = {
  makine_id: number;
  neden_id: number;
  aralik: [Dayjs, Dayjs];
  aciklama?: string;
};

export function DurusKaydiFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<Alanlar>();
  const olustur = useDurusKaydiOlustur();
  const { data: makineler } = useMakineSecenekleri();
  const { data: nedenler } = useDurusNedenleri();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      makine_id: v.makine_id,
      neden_id: v.neden_id,
      baslangic: v.aralik[0].toISOString(),
      bitis: v.aralik[1].toISOString(),
      aciklama: v.aciklama?.trim() ?? '',
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      title={t('durus.yeni_kayit')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      onOk={() => void gonder()}
      onCancel={() => {
        form.resetFields();
        kapat();
      }}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional" preserve={false}>
        <Form.Item name="makine_id" label={t('durus.makine')} rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={t('uretim.makine_sec')}
            options={(makineler ?? []).map((m) => ({ value: m.id, label: `${m.kod} · ${m.ad}` }))}
          />
        </Form.Item>
        <Form.Item name="neden_id" label={t('durus.neden')} rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={t('durus.neden_sec')}
            options={(nedenler ?? [])
              .filter((n) => n.aktif)
              .map((n) => ({
                value: n.id,
                label: `${n.ad} (${t(`durus.sinif_${n.sinif}`)})`,
              }))}
          />
        </Form.Item>
        <Form.Item name="aralik" label={t('durus.aralik')} rules={[{ required: true }]}>
          <DatePicker.RangePicker showTime={{ format: 'HH:mm' }} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('durus.aciklama')}>
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
