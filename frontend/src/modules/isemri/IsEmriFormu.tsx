/**
 * İş emri oluşturma formu (modal). Makine zorunlu; öncelik varsayılan "orta"; atama
 * opsiyonel. ``hedef_tarih`` SLA hedefidir (S-VB): boş = SLA takibi yok.
 */

import { useTranslation } from 'react-i18next';
import { DatePicker, Form, Input, Modal, Select } from 'antd';
import type { Dayjs } from 'dayjs';

import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';

import { ONCELIKLER } from './durum';
import { useIsEmriOlustur, useKullaniciSecenekleri } from './hooks';

type Alanlar = {
  baslik: string;
  makine_id: number;
  oncelik: string;
  aciklama?: string;
  atanan_kullanici_id?: number;
  hedef_tarih?: Dayjs;
};

export function IsEmriFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<Alanlar>();
  const olustur = useIsEmriOlustur();
  const { data: makineler } = useMakineSecenekleri();
  const kullaniciOku = useAuthStore((s) => s.izinVar('kullanici:oku'));
  const { data: kullanicilar } = useKullaniciSecenekleri(kullaniciOku);

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      baslik: v.baslik.trim(),
      makine_id: v.makine_id,
      oncelik: v.oncelik,
      aciklama: v.aciklama?.trim() ?? '',
      atanan_kullanici_id: v.atanan_kullanici_id ?? null,
      hedef_tarih: v.hedef_tarih ? v.hedef_tarih.toISOString() : null,
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      width={560}
      title={t('isemri.is_emri_olustur')}
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
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        preserve={false}
        initialValues={{ oncelik: 'orta' }}
      >
        <Form.Item
          name="baslik"
          label={t('isemri.baslik')}
          rules={[{ required: true, message: t('isemri.baslik_gerekli') }, { max: 200 }]}
        >
          <Input placeholder={t('isemri.baslik_ipucu')} autoFocus />
        </Form.Item>

        <Form.Item
          name="makine_id"
          label={t('isemri.makine')}
          rules={[{ required: true, message: t('isemri.makine_gerekli') }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            placeholder={t('uretim.makine_sec')}
            options={(makineler ?? []).map((m) => ({ value: m.id, label: `${m.kod} · ${m.ad}` }))}
          />
        </Form.Item>

        <Form.Item name="oncelik" label={t('isemri.oncelik')}>
          <Select
            options={ONCELIKLER.map((o) => ({ value: o, label: t(`isemri.oncelik_${o}`) }))}
          />
        </Form.Item>

        <Form.Item
          name="hedef_tarih"
          label={t('isemri.hedef_tarih')}
          extra={t('isemri.hedef_ipucu')}
        >
          <DatePicker showTime={{ format: 'HH:mm' }} style={{ width: '100%' }} />
        </Form.Item>

        {kullaniciOku && (
          <Form.Item name="atanan_kullanici_id" label={t('isemri.atanan')}>
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder={t('isemri.atanmamis')}
              options={(kullanicilar ?? []).map((k) => ({
                value: k.id,
                label: k.ad_soyad || k.eposta,
              }))}
            />
          </Form.Item>
        )}

        <Form.Item name="aciklama" label={t('isemri.aciklama')}>
          <Input.TextArea rows={3} maxLength={1000} placeholder={t('isemri.aciklama_ipucu')} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
