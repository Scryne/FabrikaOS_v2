/**
 * Kullanıcı oluşturma formu (modal). Roller tenant rol kataloğundan (``GET /roller``)
 * çoklu seçilir; parola en az 8 karakterdir (backend kuralıyla uyumlu).
 */

import { useTranslation } from 'react-i18next';
import { Form, Input, Modal, Select } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { useKullaniciOlustur, useRoller } from './hooks';

export function KullaniciFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const rolOkuyabilir = useAuthStore((s) => s.izinVar('rol:oku'));
  const { data: roller } = useRoller(acik && rolOkuyabilir);
  const olustur = useKullaniciOlustur();

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
      title={t('kullanici.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item
          name="eposta"
          label={t('kullanici.eposta')}
          rules={[{ required: true }, { type: 'email', message: t('kullanici.eposta_gecersiz') }]}
        >
          <Input maxLength={255} autoComplete="off" />
        </Form.Item>
        <Form.Item name="ad_soyad" label={t('kullanici.ad_soyad')}>
          <Input maxLength={200} />
        </Form.Item>
        <Form.Item
          name="parola"
          label={t('kullanici.parola')}
          rules={[{ required: true }, { min: 8, message: t('kullanici.parola_kisa') }]}
        >
          <Input.Password maxLength={128} autoComplete="new-password" />
        </Form.Item>
        <Form.Item name="roller" label={t('kullanici.roller')}>
          <Select
            mode="multiple"
            allowClear
            placeholder={t('kullanici.rol_sec')}
            options={(roller ?? []).map((r) => ({
              value: r.ad,
              label: r.ad,
              title: r.aciklama,
            }))}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
