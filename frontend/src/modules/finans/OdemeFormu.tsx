/**
 * Tahsilat / ödeme kaydı (modal). Faturadan açılırsa firma, fatura ve açık tutar dolu gelir.
 * Her açılışta yeni bir Idempotency-Key üretilir: aynı pencerede çift tık ya da ağ kopması
 * ikinci ödeme yazmaz. Firmaya ödeme ``finans:onay`` ister (düğme yetkiye göre görünür).
 */

import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, InputNumber, Modal, Segmented, Select } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';

import { useFirmalar } from '@/modules/crm/hooks';
import { useAuthStore } from '@/store/authStore';

import { type Fatura, paraBicim, useFaturalar, useOdemeOlustur } from './hooks';

const YONTEMLER = ['havale', 'nakit', 'kredi_karti', 'cek', 'senet'];

type FormDeger = {
  tur: 'tahsilat' | 'odeme';
  firma_id?: number;
  fatura_id?: number;
  tutar?: number;
  tarih: Dayjs;
  yontem: string;
  aciklama?: string;
};

export function OdemeFormu({
  acik,
  kapat,
  fatura,
  varsayilanTur = 'tahsilat',
}: {
  acik: boolean;
  kapat: () => void;
  fatura?: Fatura | null;
  varsayilanTur?: 'tahsilat' | 'odeme';
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm<FormDeger>();
  const olustur = useOdemeOlustur();
  const onayli = useAuthStore((s) => s.izinVar('finans:onay'));
  const tur = Form.useWatch('tur', form) ?? varsayilanTur;
  const firmaId = Form.useWatch('firma_id', form);
  // Pencere başına tek anahtar: aynı formun tekrar gönderimi aynı ödemeyi döndürür.
  const anahtar = useMemo(() => (acik ? crypto.randomUUID() : ''), [acik]);

  const firmalar = useFirmalar({ sayfa: 1, adet: 100, siralama: 'ad', yon: 'asc' });
  const aciklar = useFaturalar({
    sayfa: 1,
    adet: 100,
    filtreler: {
      firma_id: firmaId,
      durum: 'kesildi',
      tur: tur === 'tahsilat' ? 'satis' : 'alis',
    },
  });
  const faturaSecenek = (firmaId ? (aciklar.data?.veri ?? []) : []).map((f) => ({
    value: f.id,
    label: `${f.kod} · ${t('finans.acik')} ${paraBicim(f.acik_tutar, f.para_birimi)}`,
    acik: f.acik_tutar,
  }));

  useEffect(() => {
    if (!acik) return;
    form.resetFields();
    if (fatura) {
      form.setFieldsValue({
        tur: fatura.tur === 'satis' ? 'tahsilat' : 'odeme',
        firma_id: fatura.firma_id,
        fatura_id: fatura.id,
        tutar: fatura.acik_tutar,
      });
    } else {
      form.setFieldsValue({ tur: varsayilanTur });
    }
  }, [acik, fatura, form, varsayilanTur]);

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      anahtar,
      govde: {
        tur: v.tur,
        firma_id: v.firma_id!,
        fatura_id: v.fatura_id ?? null,
        tutar: String(v.tutar),
        tarih: v.tarih.format('YYYY-MM-DD'),
        yontem: v.yontem,
        aciklama: v.aciklama ?? '',
      },
    });
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={tur === 'tahsilat' ? t('finans.yeni_tahsilat') : t('finans.yeni_odeme')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form<FormDeger>
        form={form}
        layout="vertical"
        requiredMark="optional"
        initialValues={{ tur: varsayilanTur, tarih: dayjs(), yontem: 'havale' }}
      >
        <Form.Item name="tur" label={t('finans.odeme_turu')}>
          <Segmented
            disabled={!!fatura}
            options={[
              { value: 'tahsilat', label: t('finans.tur_tahsilat') },
              { value: 'odeme', label: t('finans.tur_odeme'), disabled: !onayli },
            ]}
          />
        </Form.Item>
        <Form.Item name="firma_id" label={t('finans.firma')} rules={[{ required: true }]}>
          <Select
            showSearch
            disabled={!!fatura}
            optionFilterProp="label"
            loading={firmalar.isPending}
            options={(firmalar.data?.veri ?? []).map((f) => ({ value: f.id, label: f.ad }))}
            onChange={() => form.setFieldValue('fatura_id', undefined)}
            aria-label={t('finans.firma')}
          />
        </Form.Item>
        <Form.Item
          name="fatura_id"
          label={t('finans.bagli_fatura')}
          extra={t('finans.bagli_fatura_ipucu')}
        >
          <Select
            allowClear
            disabled={!!fatura || !firmaId}
            options={faturaSecenek}
            onChange={(id?: number) => {
              const secilen = faturaSecenek.find((s) => s.value === id);
              if (secilen) form.setFieldValue('tutar', secilen.acik);
            }}
            aria-label={t('finans.bagli_fatura')}
          />
        </Form.Item>
        <div style={{ display: 'flex', gap: 12 }}>
          <Form.Item
            name="tutar"
            label={t('finans.tutar')}
            rules={[{ required: true }]}
            style={{ flex: 1 }}
          >
            <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} suffix="₺" />
          </Form.Item>
          <Form.Item name="tarih" label={t('finans.tarih')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" />
          </Form.Item>
        </div>
        <Form.Item name="yontem" label={t('finans.yontem')}>
          <Select options={YONTEMLER.map((y) => ({ value: y, label: t(`finans.yontem_${y}`) }))} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('finans.not')}>
          <Input maxLength={500} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
