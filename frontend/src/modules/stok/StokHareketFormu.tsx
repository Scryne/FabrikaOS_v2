/**
 * Stok hareketi formu (modal). ``malzeme`` seçiliyse açılır; tür giriş/çıkış (+ eski mutlak
 * düzeltme yalnız ``stok:duzeltme`` iznine görünür; sayım farkı için Sayımlar akışı kullanılır).
 * S25: lokasyon ve lot seçilebilir; girişte "Hızlı mal kabul" irsaliye no ister ve sonra
 * siparişin resmî teslimiyle eşleşir (ADR-0024 §4b). Submit → bakiye + kritik canlı yansır.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Checkbox, Form, Input, InputNumber, Modal, Select } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { useDepolar } from './depoHooks';
import { type Malzeme, useStokHareketEkle } from './hooks';

export function StokHareketFormu({
  malzeme,
  kapat,
}: {
  malzeme: Malzeme | null;
  kapat: () => void;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const ekle = useStokHareketEkle();
  const depolar = useDepolar();
  const mutlakDuzeltebilir = useAuthStore((s) => s.izinVar('stok:duzeltme'));
  const tur = Form.useWatch('tur', form) as string | undefined;
  const hizli = Form.useWatch('hizli_kabul', form) as boolean | undefined;

  useEffect(() => {
    if (malzeme) form.setFieldsValue({ tur: 'giris', miktar: 1, aciklama: '', hizli_kabul: false });
  }, [malzeme, form]);

  const gonder = async () => {
    if (!malzeme) return;
    const v = await form.validateFields();
    const hizliKabul = v.tur === 'giris' && Boolean(v.hizli_kabul);
    await ekle.mutateAsync({
      malzeme_id: malzeme.id,
      tur: v.tur,
      miktar: v.miktar,
      aciklama: v.aciklama ?? '',
      lokasyon_id: v.lokasyon_id ?? null,
      lot_no: (v.lot_no ?? '').trim(),
      kaynak: hizliKabul ? v.kaynak.trim() : undefined,
      hizli_kabul: hizliKabul,
    });
    kapat();
  };

  return (
    <Modal
      open={malzeme != null}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={`${t('stok.hareket_ekle')} — ${malzeme?.kod ?? ''}`}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={ekle.isPending}
      destroyOnHidden
      mask={{ closable: false }}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item name="tur" label={t('stok.tur')} rules={[{ required: true }]}>
          <Select
            options={[
              { value: 'giris', label: t('stok.giris') },
              { value: 'cikis', label: t('stok.cikis') },
              ...(mutlakDuzeltebilir ? [{ value: 'duzeltme', label: t('stok.duzeltme') }] : []),
            ]}
          />
        </Form.Item>
        <Form.Item name="miktar" label={t('stok.miktar')} rules={[{ required: true }]}>
          <InputNumber min={0.001} style={{ width: '100%' }} suffix={malzeme?.birim} />
        </Form.Item>
        <Form.Item name="lokasyon_id" label={t('stok.lokasyon')}>
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder={t('stok.lokasyon_bos')}
            options={(depolar.data ?? []).flatMap((d) =>
              d.lokasyonlar.map((l) => ({ value: l.id, label: `${d.kod} / ${l.kod} · ${l.ad}` })),
            )}
          />
        </Form.Item>
        {(malzeme?.lot_takipli || tur !== 'duzeltme') && (
          <Form.Item
            name="lot_no"
            label={t('stok.lot')}
            rules={
              malzeme?.lot_takipli && tur === 'giris'
                ? [{ required: true, whitespace: true, message: t('siparis.lot_gerekli') }]
                : []
            }
          >
            <Input maxLength={60} />
          </Form.Item>
        )}
        {tur === 'giris' && (
          <Form.Item name="hizli_kabul" valuePropName="checked" extra={t('stok.hizli_kabul_ipucu')}>
            <Checkbox>{t('stok.hizli_kabul')}</Checkbox>
          </Form.Item>
        )}
        {tur === 'giris' && hizli && (
          <Form.Item
            name="kaynak"
            label={t('stok.irsaliye_no')}
            rules={[{ required: true, whitespace: true, message: t('stok.irsaliye_gerekli') }]}
          >
            <Input maxLength={40} />
          </Form.Item>
        )}
        <Form.Item name="aciklama" label={t('stok.aciklama')}>
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
