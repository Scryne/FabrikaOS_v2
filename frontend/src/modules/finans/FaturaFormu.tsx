/**
 * Fatura hazırlama/düzenleme formu (modal). Yeni taslak ya da iade edilmiş/taslak faturanın
 * düzeltilmesi. Kalemler dinamik ``Form.List``; toplam canlı önizlenir (kayıtlı tutarı sunucu
 * hesaplar, kural aynı: satır başına yuvarlama).
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Segmented,
  Select,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';

import { useFirmalar } from '@/modules/crm/hooks';

import { faturaToplami } from './durum';
import { type Fatura, paraBicim, useFaturaGuncelle, useFaturaOlustur } from './hooks';

const KDV_ORANLARI = [0, 1, 10, 20];
const BIRIMLER = ['adet', 'kg', 'metre', 'litre', 'saat', 'gün', 'ton', 'paket', 'hizmet'];

type KalemDeger = {
  aciklama?: string;
  miktar?: number;
  birim?: string;
  birim_fiyat?: number;
  kdv_orani?: number;
};
type FormDeger = {
  tur: 'satis' | 'alis';
  firma_id?: number;
  fatura_tarihi: Dayjs;
  vade_gun: number;
  kalemler: KalemDeger[];
  aciklama?: string;
};

export function FaturaFormu({
  acik,
  kapat,
  duzenlenen,
}: {
  acik: boolean;
  kapat: () => void;
  /** Verilirse düzenleme (yalnız taslak). */
  duzenlenen?: Fatura | null;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm<FormDeger>();
  const olustur = useFaturaOlustur();
  const guncelle = useFaturaGuncelle();
  const tur = Form.useWatch('tur', form) ?? 'satis';
  const kalemler = Form.useWatch('kalemler', form) ?? [];
  const toplam = faturaToplami(kalemler);
  const firmalar = useFirmalar({ sayfa: 1, adet: 100, siralama: 'ad', yon: 'asc' });
  const secenekler = (firmalar.data?.veri ?? [])
    .filter((f) => (tur === 'satis' ? f.tip !== 'tedarikci' : f.tip !== 'musteri'))
    .map((f) => ({ value: f.id, label: f.ad }));

  useEffect(() => {
    if (!acik) return;
    if (duzenlenen) {
      form.setFieldsValue({
        tur: duzenlenen.tur as 'satis' | 'alis',
        firma_id: duzenlenen.firma_id,
        fatura_tarihi: dayjs(duzenlenen.fatura_tarihi),
        vade_gun: dayjs(duzenlenen.vade_tarihi).diff(dayjs(duzenlenen.fatura_tarihi), 'day'),
        aciklama: duzenlenen.aciklama,
        kalemler: duzenlenen.kalemler.map((k) => ({
          aciklama: k.aciklama,
          miktar: k.miktar,
          birim: k.birim,
          birim_fiyat: k.birim_fiyat,
          kdv_orani: k.kdv_orani,
        })),
      });
    } else {
      form.resetFields();
    }
  }, [acik, duzenlenen, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    const govdeKalemler = v.kalemler.map((k) => ({
      aciklama: k.aciklama ?? '',
      miktar: String(k.miktar ?? 0),
      birim: k.birim ?? 'adet',
      birim_fiyat: String(k.birim_fiyat ?? 0),
      kdv_orani: k.kdv_orani ?? 20,
    }));
    if (duzenlenen) {
      await guncelle.mutateAsync({
        id: duzenlenen.id,
        govde: {
          firma_id: v.firma_id,
          fatura_tarihi: v.fatura_tarihi.format('YYYY-MM-DD'),
          vade_gun: v.vade_gun,
          aciklama: v.aciklama ?? '',
          kalemler: govdeKalemler,
        },
      });
    } else {
      await olustur.mutateAsync({
        tur: v.tur,
        senaryo: 'TEMELFATURA',
        firma_id: v.firma_id!,
        fatura_tarihi: v.fatura_tarihi.format('YYYY-MM-DD'),
        vade_gun: v.vade_gun,
        aciklama: v.aciklama ?? '',
        kalemler: govdeKalemler,
      });
    }
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={
        duzenlenen ? t('finans.duzenle_baslik', { kod: duzenlenen.kod }) : t('finans.yeni_fatura')
      }
      okText={t('finans.taslak_kaydet')}
      cancelText={t('ortak.iptal')}
      width={860}
      confirmLoading={olustur.isPending || guncelle.isPending}
      destroyOnHidden
      mask={{ closable: false }}
    >
      {duzenlenen?.iade_nedeni && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title={t('finans.iade_edildi')}
          description={duzenlenen.iade_nedeni}
        />
      )}
      <Form<FormDeger>
        form={form}
        layout="vertical"
        requiredMark="optional"
        initialValues={{
          tur: 'satis',
          fatura_tarihi: dayjs(),
          vade_gun: 30,
          kalemler: [{ birim: 'adet', miktar: 1, kdv_orani: 20 }],
        }}
      >
        <div className="form-izgara-3">
          <Form.Item name="tur" label={t('finans.tur')}>
            <Segmented
              disabled={!!duzenlenen}
              options={[
                { value: 'satis', label: t('finans.tur_satis') },
                { value: 'alis', label: t('finans.tur_alis') },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="firma_id"
            label={tur === 'satis' ? t('finans.musteri') : t('finans.tedarikci')}
            rules={[{ required: true, message: t('finans.firma_sec') }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={secenekler}
              loading={firmalar.isPending}
              placeholder={t('finans.firma_sec')}
              aria-label={t('finans.firma')}
            />
          </Form.Item>
          <div style={{ display: 'flex', gap: 12 }}>
            <Form.Item
              name="fatura_tarihi"
              label={t('finans.fatura_tarihi')}
              rules={[{ required: true }]}
              style={{ flex: 1 }}
            >
              <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="vade_gun" label={t('finans.vade')} style={{ width: 120 }}>
              <InputNumber min={0} max={365} style={{ width: '100%' }} suffix={t('finans.gun')} />
            </Form.Item>
          </div>
        </div>

        <Form.List
          name="kalemler"
          rules={[
            {
              validator: (_, liste: unknown[]) =>
                liste && liste.length > 0
                  ? Promise.resolve()
                  : Promise.reject(new Error(t('finans.kalem_gerekli'))),
            },
          ]}
        >
          {(alanlar, { add, remove }, { errors }) => (
            <div className="fatura-kalemleri">
              <div className="fatura-kalem fatura-kalem-baslik" aria-hidden>
                <span>{t('finans.aciklama')}</span>
                <span>{t('finans.miktar')}</span>
                <span>{t('finans.birim')}</span>
                <span>{t('finans.birim_fiyat')}</span>
                <span>{t('finans.kdv')}</span>
                <span />
              </div>
              {alanlar.map((alan) => (
                <div key={alan.key} className="fatura-kalem">
                  <Form.Item
                    name={[alan.name, 'aciklama']}
                    rules={[{ required: true, message: t('finans.aciklama_gerekli') }]}
                  >
                    <Input placeholder={t('finans.aciklama')} aria-label={t('finans.aciklama')} />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'miktar']} rules={[{ required: true }]}>
                    <InputNumber
                      min={0.001}
                      style={{ width: '100%' }}
                      placeholder={t('finans.miktar')}
                      aria-label={t('finans.miktar')}
                    />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'birim']}>
                    <Select
                      options={BIRIMLER.map((b) => ({ value: b, label: b }))}
                      aria-label={t('finans.birim')}
                    />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'birim_fiyat']} rules={[{ required: true }]}>
                    <InputNumber
                      min={0}
                      step={0.01}
                      style={{ width: '100%' }}
                      placeholder={t('finans.birim_fiyat')}
                      aria-label={t('finans.birim_fiyat')}
                    />
                  </Form.Item>
                  <Form.Item name={[alan.name, 'kdv_orani']}>
                    <Select
                      options={KDV_ORANLARI.map((o) => ({ value: o, label: `%${o}` }))}
                      aria-label={t('finans.kdv')}
                    />
                  </Form.Item>
                  <Button
                    type="text"
                    icon={<MinusCircleOutlined />}
                    disabled={alanlar.length === 1}
                    onClick={() => remove(alan.name)}
                    aria-label={t('finans.kalem_sil')}
                  />
                </div>
              ))}
              <Button
                type="dashed"
                block
                icon={<PlusOutlined />}
                onClick={() => add({ birim: 'adet', miktar: 1, kdv_orani: 20 })}
              >
                {t('finans.kalem_ekle')}
              </Button>
              <Form.ErrorList errors={errors} />
            </div>
          )}
        </Form.List>

        <dl className="fatura-toplam">
          <dt>{t('finans.ara_toplam')}</dt>
          <dd className="sayisal">{paraBicim(toplam.ara)}</dd>
          <dt>{t('finans.kdv')}</dt>
          <dd className="sayisal">{paraBicim(toplam.kdv)}</dd>
          <dt className="genel">{t('finans.genel_toplam')}</dt>
          <dd className="sayisal genel">{paraBicim(toplam.genel)}</dd>
        </dl>

        <Form.Item name="aciklama" label={t('finans.not')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
