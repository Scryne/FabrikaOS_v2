/**
 * İzin talebi oluşturma formu (modal). ``personelId`` verilirse personel alanı gizlenir
 * (personel detayından açıldığında). Tarih aralığı seçilir; gün sayısı sunucuda hesaplanır.
 * Yıllık izinde kalan bakiye gösterilir (S26-B); asıl kapı onaydadır (aşım 409).
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, DatePicker, Form, Input, Modal, Select } from 'antd';
import type { FormInstance } from 'antd';
import type { Dayjs } from 'dayjs';

import { useIzinOlustur } from './hooks';
import { useIzinBakiyesi, usePersonelSecenekleri } from './olgunlukHooks';

const TURLER = ['yillik', 'mazeret', 'hastalik', 'ucretsiz', 'dogum', 'babalik'];

/** Personel seçici: Modal çocuğu, sorgu yalnız form açıkken çalışır. */
function PersonelAlani() {
  const { t } = useTranslation();
  const secenekler = usePersonelSecenekleri();
  return (
    <Form.Item name="personel_id" label={t('ik.personel')} rules={[{ required: true }]}>
      <Select
        showSearch
        optionFilterProp="label"
        loading={secenekler.isPending}
        options={(secenekler.data ?? [])
          .filter((p) => p.aktif)
          .map((p) => ({ value: p.id, label: `${p.ad} ${p.soyad} · ${p.sicil_no}` }))}
      />
    </Form.Item>
  );
}

function BakiyeIpucu({ form, personelId }: { form: FormInstance; personelId?: number }) {
  const { t } = useTranslation();
  const secili = Form.useWatch('personel_id', form) as number | undefined;
  const tur = Form.useWatch('izin_turu', form) as string | undefined;
  const aralik = Form.useWatch('aralik', form) as [Dayjs, Dayjs] | null | undefined;
  const bakiye = useIzinBakiyesi(tur === 'yillik' ? (personelId ?? secili) : undefined);
  const talepGun = aralik?.[0] && aralik[1] ? aralik[1].diff(aralik[0], 'day') + 1 : 0;

  if (tur !== 'yillik' || !bakiye.data) return null;
  const asim = talepGun > bakiye.data.bakiye;
  return (
    <Alert
      showIcon
      style={{ marginBottom: 16 }}
      type={asim ? 'warning' : 'info'}
      message={
        asim
          ? t('ik26.bakiye_asim', { kalan: bakiye.data.bakiye, talep: talepGun })
          : t('ik26.bakiye_bilgi', { kalan: bakiye.data.bakiye })
      }
    />
  );
}

export function IzinFormu({
  acik,
  kapat,
  personelId,
}: {
  acik: boolean;
  kapat: () => void;
  personelId?: number;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useIzinOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ izin_turu: 'yillik', personel_id: personelId });
  }, [acik, form, personelId]);

  const gonder = async () => {
    const v = await form.validateFields();
    const [bas, bit] = v.aralik ?? [];
    const govde = {
      personel_id: v.personel_id,
      izin_turu: v.izin_turu,
      aciklama: v.aciklama ?? '',
      baslangic_tarihi: bas ? bas.format('YYYY-MM-DD') : undefined,
      bitis_tarihi: bit ? bit.format('YYYY-MM-DD') : undefined,
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
      title={t('ik.izin_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        {personelId === undefined && <PersonelAlani />}
        <Form.Item name="izin_turu" label={t('ik.izin_turu')} rules={[{ required: true }]}>
          <Select options={TURLER.map((x) => ({ value: x, label: t(`ik.izin_turu_${x}`) }))} />
        </Form.Item>
        <Form.Item name="aralik" label={t('ik.tarih_araligi')} rules={[{ required: true }]}>
          <DatePicker.RangePicker style={{ width: '100%' }} />
        </Form.Item>
        <BakiyeIpucu form={form} personelId={personelId} />
        <Form.Item name="aciklama" label={t('ik.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
