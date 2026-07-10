/**
 * Kullanıcı oluşturma + düzenleme formu (modal). Roller tenant rol kataloğundan
 * (``GET /roller``) çoklu seçilir; parola en az 8 karakterdir (backend kuralıyla uyumlu).
 *
 * Düzenleme modunda e-posta salt-okunur, parola alanı yoktur; aktiflik anahtarı
 * ve rol seçimi KENDİ hesabında kilitlidir (backend 422 korumasının UI yansıması).
 * Firma alanı (S18 dış portal bağlantısı) yalnız `crm:oku` izni + `crm` modülü
 * açıkken görünür — dis-panel kullanıcısı artık UI'dan bağlanabilir.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Form, Input, Modal, Select, Switch } from 'antd';

import { useModulAcik } from '@/modules/abonelik/hooks';
import { useAuthStore } from '@/store/authStore';

import {
  type Kullanici,
  useFirmaSecenekleri,
  useKullaniciGuncelle,
  useKullaniciOlustur,
  useRoller,
} from './hooks';

type FormDegerleri = {
  eposta?: string;
  ad_soyad?: string;
  parola?: string;
  roller?: string[];
  aktif?: boolean;
  firma_id?: number | null;
};

export function KullaniciFormu({
  acik,
  kapat,
  duzenlenen,
}: {
  acik: boolean;
  kapat: () => void;
  /** Doluysa düzenleme modu; boşsa yeni kullanıcı oluşturma. */
  duzenlenen?: Kullanici | null;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm<FormDegerleri>();
  const ben = useAuthStore((s) => s.kullanici);
  const rolOkuyabilir = useAuthStore((s) => s.izinVar('rol:oku'));
  const firmaOkuyabilir = useAuthStore((s) => s.izinVar('crm:oku'));
  const modulAcik = useModulAcik();
  const firmaAlaniVar = firmaOkuyabilir && modulAcik('crm');

  const { data: roller } = useRoller(acik && rolOkuyabilir);
  const { data: firmalar } = useFirmaSecenekleri(acik && firmaAlaniVar);
  const olustur = useKullaniciOlustur();
  const guncelle = useKullaniciGuncelle();

  const duzenlemeModu = duzenlenen != null;
  const kendiHesabi = duzenlemeModu && duzenlenen.id === ben?.id;

  // Modal her açılışta seçili kullanıcının değerleriyle (ya da boş) başlar.
  useEffect(() => {
    if (!acik) return;
    if (duzenlenen) {
      form.setFieldsValue({
        eposta: duzenlenen.eposta,
        ad_soyad: duzenlenen.ad_soyad,
        roller: duzenlenen.roller,
        aktif: duzenlenen.aktif,
        firma_id: duzenlenen.firma_id ?? undefined,
      });
    } else {
      form.resetFields();
    }
  }, [acik, duzenlenen, form]);

  const gonder = async () => {
    const v = await form.validateFields();
    if (duzenlemeModu) {
      await guncelle.mutateAsync({
        id: duzenlenen.id,
        govde: {
          ad_soyad: v.ad_soyad ?? '',
          // Kendi hesabında aktif/roller gönderilmez (backend 422 koruması).
          ...(kendiHesabi ? {} : { aktif: v.aktif, roller: v.roller ?? [] }),
          ...(firmaAlaniVar ? { firma_id: v.firma_id ?? null } : {}),
        },
      });
    } else {
      await olustur.mutateAsync({
        eposta: v.eposta ?? '',
        parola: v.parola ?? '',
        ad_soyad: v.ad_soyad ?? '',
        roller: v.roller ?? [],
        ...(firmaAlaniVar && v.firma_id != null ? { firma_id: v.firma_id } : {}),
      });
    }
    form.resetFields();
    kapat();
  };

  // Kendi hesabında kilitli alanların açıklaması (backend 422 korumasının UI yansıması).
  const kilitAciklama = kendiHesabi ? t('kullanici.kendi_hesap_kilidi') : undefined;

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      onOk={() => void gonder()}
      title={duzenlemeModu ? t('kullanici.duzenle') : t('kullanici.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending || guncelle.isPending}
      destroyOnHidden
      maskClosable={false}
    >
      <Form form={form} layout="vertical" requiredMark="optional">
        <Form.Item
          name="eposta"
          label={t('kullanici.eposta')}
          rules={
            duzenlemeModu
              ? []
              : [{ required: true }, { type: 'email', message: t('kullanici.eposta_gecersiz') }]
          }
        >
          <Input maxLength={255} autoComplete="off" disabled={duzenlemeModu} />
        </Form.Item>
        <Form.Item name="ad_soyad" label={t('kullanici.ad_soyad')}>
          <Input maxLength={200} />
        </Form.Item>
        {!duzenlemeModu && (
          <Form.Item
            name="parola"
            label={t('kullanici.parola')}
            rules={[{ required: true }, { min: 8, message: t('kullanici.parola_kisa') }]}
          >
            <Input.Password maxLength={128} autoComplete="new-password" />
          </Form.Item>
        )}
        <Form.Item name="roller" label={t('kullanici.roller')} extra={kilitAciklama}>
          <Select
            mode="multiple"
            allowClear
            disabled={kendiHesabi}
            placeholder={t('kullanici.rol_sec')}
            options={(roller ?? []).map((r) => ({
              value: r.ad,
              label: r.ad,
              title: r.aciklama,
            }))}
          />
        </Form.Item>
        {firmaAlaniVar && (
          <Form.Item
            name="firma_id"
            label={t('kullanici.firma')}
            extra={t('kullanici.firma_aciklama')}
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder={t('kullanici.firma_sec')}
              options={(firmalar ?? []).map((f) => ({ value: f.id, label: f.ad }))}
            />
          </Form.Item>
        )}
        {duzenlemeModu && (
          <Form.Item
            name="aktif"
            label={t('kullanici.durum')}
            valuePropName="checked"
            extra={kilitAciklama}
          >
            <Switch
              disabled={kendiHesabi}
              checkedChildren={t('kullanici.aktif')}
              unCheckedChildren={t('kullanici.pasif')}
            />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}
