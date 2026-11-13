/**
 * Uygunsuzluk (CAPA vakası) oluşturma formu (modal). Başlık zorunlu; önem beyaz-listeden.
 * Makine / tedarikçi / kaynak kontrol / sorumlu opsiyonel; seçiciler ad gösterir, okuma izni
 * yoksa (ör. `crm:oku` olmayan kalite kullanıcısı) ilgili seçici gizlenir. Yeni vaka ``acik``
 * durumunda başlar. Tedarikçi seçimi giriş muayenesi uygunsuzluğunu firmaya bağlar (ADR-0025).
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, InputNumber, Modal, Select } from 'antd';

import { useKullaniciSecenekleri } from '@/modules/isemri/hooks';
import { useFirmaSecenekleri } from '@/modules/kimlik/hooks';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';

import { useUygunsuzlukOlustur } from './hooks';

const ONEMLER = ['dusuk', 'orta', 'yuksek', 'kritik'];

const ara = (girdi: string, secenek?: { label?: unknown }) =>
  String(secenek?.label ?? '')
    .toLocaleLowerCase('tr')
    .includes(girdi.toLocaleLowerCase('tr'));

/** İlişki seçicileri: Modal çocuğu olduğu için sorgular yalnız form ilk açıldığında başlar. */
function IliskiAlanlari() {
  const { t } = useTranslation();
  const izinVar = useAuthStore((s) => s.izinVar);
  // Makine listesi uretim:oku ister; kalite rolünde yoksa alan gizlenir (403 ve boş seçici yerine).
  const makineler = useMakineSecenekleri(izinVar('uretim:oku'));
  const firmalar = useFirmaSecenekleri(izinVar('crm:oku'));
  const kullanicilar = useKullaniciSecenekleri(izinVar('kullanici:oku'));

  return (
    <>
      {izinVar('uretim:oku') && (
        <Form.Item name="makine_id" label={t('kalite.makine')}>
          <Select
            allowClear
            showSearch
            filterOption={ara}
            loading={makineler.isPending}
            options={(makineler.data ?? []).map((m) => ({
              value: m.id,
              label: `${m.kod} · ${m.ad}`,
            }))}
          />
        </Form.Item>
      )}
      {izinVar('crm:oku') && (
        <Form.Item
          name="tedarikci_firma_id"
          label={t('kalite.tedarikci')}
          tooltip={t('kalite.tedarikci_ipucu')}
        >
          <Select
            allowClear
            showSearch
            filterOption={ara}
            loading={firmalar.isPending}
            options={(firmalar.data ?? [])
              .filter((f) => f.tip === 'tedarikci' || f.tip === 'her_ikisi')
              .map((f) => ({ value: f.id, label: f.ad }))}
          />
        </Form.Item>
      )}
      {izinVar('kullanici:oku') && (
        <Form.Item name="sorumlu_kullanici_id" label={t('kalite.sorumlu')}>
          <Select
            allowClear
            showSearch
            filterOption={ara}
            loading={kullanicilar.isPending}
            options={(kullanicilar.data ?? []).map((k) => ({
              value: k.id,
              label: k.ad_soyad || k.eposta,
            }))}
          />
        </Form.Item>
      )}
    </>
  );
}

export function UygunsuzlukFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useUygunsuzlukOlustur();

  useEffect(() => {
    if (acik) form.setFieldsValue({ onem: 'orta' });
  }, [acik, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync(v);
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={t('kalite.yeni_uygunsuzluk')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      mask={{ closable: false }}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item
          name="baslik"
          label={t('kalite.baslik')}
          rules={[{ required: true }, { max: 200 }]}
        >
          <Input autoFocus />
        </Form.Item>
        <Form.Item name="aciklama" label={t('kalite.aciklama')}>
          <Input.TextArea rows={3} maxLength={2000} />
        </Form.Item>
        <div className="form-iki-sutun">
          <Form.Item name="onem" label={t('kalite.onem')} rules={[{ required: true }]}>
            <Select options={ONEMLER.map((x) => ({ value: x, label: t(`kalite.onem_${x}`) }))} />
          </Form.Item>
          <IliskiAlanlari />
          <Form.Item name="kaynak_kontrol_id" label={t('kalite.kaynak_kontrol')}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
}
