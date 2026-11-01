/**
 * Satış siparişi formu (S31) — yeni sipariş ya da taslak düzeltme. Kalemler ürün × miktar
 * (+ isteğe bağlı birim fiyat); malzeme ihtiyacı formda değil, detaydaki MRP tablosunda görünür.
 * Müşteri listesi ``musteri`` ve ``her_ikisi`` tipindeki firmalardır (sunucu da tedarikçiyi reddeder).
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, DatePicker, Form, Input, InputNumber, Modal, Select } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';

import { useFirmalar } from '@/modules/crm/hooks';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useUrunSecenekleri } from '@/modules/urun/hooks';

import { type Siparis, useSiparisGuncelle, useSiparisOlustur } from './hooks';

type KalemDeger = { urun_id?: number; miktar?: number; birim_fiyat?: number | null };
type FormDeger = {
  firma_id?: number;
  teslim_tarihi?: Dayjs;
  makine_id?: number;
  aciklama?: string;
  kalemler: KalemDeger[];
};

export function SiparisFormu({
  acik,
  kapat,
  duzenlenen,
}: {
  acik: boolean;
  kapat: () => void;
  duzenlenen?: Siparis | null;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm<FormDeger>();
  const firmalar = useFirmalar({ sayfa: 1, adet: 100, siralama: 'ad', yon: 'asc' });
  const urunler = useUrunSecenekleri(acik);
  const makineler = useMakineSecenekleri();
  const olustur = useSiparisOlustur();
  const guncelle = useSiparisGuncelle();

  useEffect(() => {
    if (!acik) return;
    if (duzenlenen) {
      form.setFieldsValue({
        firma_id: duzenlenen.firma_id,
        teslim_tarihi: dayjs(duzenlenen.teslim_tarihi),
        makine_id: duzenlenen.makine_id ?? undefined,
        aciklama: duzenlenen.aciklama,
        kalemler: duzenlenen.kalemler.map((k) => ({
          urun_id: k.urun_id,
          miktar: k.miktar,
          birim_fiyat: k.birim_fiyat,
        })),
      });
    } else {
      form.resetFields();
    }
  }, [acik, duzenlenen, form]);

  const musteriler = (firmalar.data?.veri ?? [])
    .filter((f) => f.tip === 'musteri' || f.tip === 'her_ikisi')
    .map((f) => ({ value: f.id, label: f.ad }));

  const gonder = async () => {
    const d = await form.validateFields();
    const kalemler = d.kalemler.map((k) => ({
      urun_id: k.urun_id!,
      miktar: String(k.miktar),
      birim_fiyat: k.birim_fiyat == null ? null : String(k.birim_fiyat),
    }));
    if (duzenlenen) {
      await guncelle.mutateAsync({
        id: duzenlenen.id,
        govde: {
          teslim_tarihi: d.teslim_tarihi!.format('YYYY-MM-DD'),
          makine_id: d.makine_id ?? null,
          aciklama: d.aciklama ?? '',
          kalemler,
        },
      });
    } else {
      await olustur.mutateAsync({
        firma_id: d.firma_id!,
        teslim_tarihi: d.teslim_tarihi!.format('YYYY-MM-DD'),
        makine_id: d.makine_id ?? null,
        aciklama: d.aciklama ?? '',
        para_birimi: 'TRY',
        kalemler,
      });
    }
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={duzenlenen ? t('satis.duzenle_baslik', { kod: duzenlenen.kod }) : t('satis.yeni')}
      okText={t('satis.taslak_kaydet')}
      cancelText={t('ortak.iptal')}
      width={760}
      confirmLoading={olustur.isPending || guncelle.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form<FormDeger>
        form={form}
        layout="vertical"
        requiredMark="optional"
        initialValues={{ teslim_tarihi: dayjs().add(14, 'day'), kalemler: [{ miktar: 1 }] }}
      >
        <div className="form-izgara-3">
          <Form.Item
            name="firma_id"
            label={t('satis.musteri')}
            rules={[{ required: true, message: t('satis.musteri_sec') }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={musteriler}
              loading={firmalar.isPending}
              disabled={!!duzenlenen}
              placeholder={t('satis.musteri_sec')}
              aria-label={t('satis.musteri')}
            />
          </Form.Item>
          <Form.Item name="teslim_tarihi" label={t('satis.teslim')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="makine_id" label={t('satis.uretim_hatti')} extra={t('satis.hat_ipucu')}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              loading={makineler.isPending}
              aria-label={t('satis.uretim_hatti')}
              options={(makineler.data ?? []).map((m) => ({
                value: m.id,
                label: `${m.kod} · ${m.ad}`,
              }))}
            />
          </Form.Item>
        </div>

        <Form.List
          name="kalemler"
          rules={[
            {
              validator: (_, liste: unknown[]) =>
                liste && liste.length > 0
                  ? Promise.resolve()
                  : Promise.reject(new Error(t('satis.kalem_gerekli'))),
            },
          ]}
        >
          {(alanlar, { add, remove }, { errors }) => (
            <div className="fatura-kalemleri">
              <div className="siparis-kalem fatura-kalem-baslik" aria-hidden>
                <span>{t('satis.urun')}</span>
                <span>{t('satis.miktar')}</span>
                <span>{t('satis.birim_fiyat')}</span>
                <span />
              </div>
              {alanlar.map((alan) => (
                <div key={alan.key} className="siparis-kalem">
                  <Form.Item
                    name={[alan.name, 'urun_id']}
                    rules={[{ required: true, message: t('satis.urun_sec') }]}
                  >
                    <Select
                      showSearch
                      optionFilterProp="label"
                      loading={urunler.isPending}
                      placeholder={t('satis.urun_sec')}
                      aria-label={t('satis.urun')}
                      options={(urunler.data ?? []).map((u) => ({
                        value: u.id,
                        label: `${u.kod} · ${u.ad}`,
                      }))}
                    />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'miktar']} rules={[{ required: true }]}>
                    <InputNumber
                      min={0.001}
                      style={{ width: '100%' }}
                      placeholder={t('satis.miktar')}
                      aria-label={t('satis.miktar')}
                    />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'birim_fiyat']}>
                    <InputNumber
                      min={0}
                      step={0.01}
                      style={{ width: '100%' }}
                      placeholder={t('satis.birim_fiyat')}
                      aria-label={t('satis.birim_fiyat')}
                    />
                  </Form.Item>
                  <Button
                    type="text"
                    icon={<MinusCircleOutlined />}
                    disabled={alanlar.length === 1}
                    onClick={() => remove(alan.name)}
                    aria-label={t('satis.kalem_sil')}
                  />
                </div>
              ))}
              <Button
                type="dashed"
                block
                icon={<PlusOutlined />}
                onClick={() => add({ miktar: 1 })}
              >
                {t('satis.kalem_ekle')}
              </Button>
              <Form.ErrorList errors={errors} />
            </div>
          )}
        </Form.List>

        <Form.Item name="aciklama" label={t('satis.not')} style={{ marginTop: 12 }}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
