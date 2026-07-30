/**
 * Tenant güvenlik ayarları paneli (platform düzlemi; S23 / ADR-0022).
 *
 * Dört bölüm tek formda: parola politikası · zorunlu 2FA · IP izin listesi · kurumsal SSO.
 * Ayarların tamamı ``public.tenant.guvenlik_ayarlari`` JSONB'sine tek PUT ile yazılır.
 *
 * **Sır davranışı:** OIDC istemci sırrı sunucudan maskeli (``••••••••``) gelir. Kullanıcı
 * alana dokunmazsa maske aynen geri gider ve sunucu mevcut sırrı korur; yeni bir değer
 * yazılırsa o kullanılır. Böylece her düzenlemede sırrın yeniden girilmesi gerekmez.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  Checkbox,
  Divider,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Typography,
} from 'antd';

import {
  baslangicDegerleri,
  type GuvenlikAlanlari,
  type GuvenlikAyarlari,
  govdeKur,
} from './guvenlikAyarBicim';
import { useGuvenlikAyarla } from './hooks';

export function GuvenlikAyarPaneli({
  tenantId,
  ayarlar,
}: {
  tenantId: number;
  ayarlar: GuvenlikAyarlari | null | undefined;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [form] = Form.useForm<GuvenlikAlanlari>();
  const kaydet = useGuvenlikAyarla(tenantId);
  const [ssoAcik, setSsoAcik] = useState(ayarlar?.oidc?.aktif ?? false);
  const [parolaAcik, setParolaAcik] = useState(ayarlar?.parola != null);

  async function gonder(d: GuvenlikAlanlari) {
    try {
      await kaydet.mutateAsync(govdeKur(d));
      message.success(t('platform.guvenlik_kaydedildi'));
    } catch (e) {
      message.error(e instanceof Error ? e.message : t('platform.islem_basarisiz'));
    }
  }

  async function sifirla() {
    try {
      await kaydet.mutateAsync(null);
      form.setFieldsValue(baslangicDegerleri(null));
      setSsoAcik(false);
      setParolaAcik(false);
      message.success(t('platform.guvenlik_sifirlandi'));
    } catch (e) {
      message.error(e instanceof Error ? e.message : t('platform.islem_basarisiz'));
    }
  }

  return (
    <Card
      size="small"
      title={
        <span>
          <SafetyCertificateOutlined /> {t('platform.guvenlik_baslik')}
        </span>
      }
    >
      <Form<GuvenlikAlanlari>
        form={form}
        layout="vertical"
        initialValues={baslangicDegerleri(ayarlar)}
        onFinish={(d) => void gonder(d)}
        requiredMark={false}
      >
        <Form.Item name="parola_acik" valuePropName="checked" style={{ marginBottom: 8 }}>
          <Checkbox onChange={(e) => setParolaAcik(e.target.checked)}>
            {t('platform.parola_politikasi')}
          </Checkbox>
        </Form.Item>
        {parolaAcik && (
          <div style={{ paddingLeft: 24, marginBottom: 12 }}>
            <Form.Item name="min_uzunluk" label={t('platform.min_uzunluk')}>
              <InputNumber min={6} max={128} />
            </Form.Item>
            <Form.Item name="buyuk_kucuk" valuePropName="checked" style={{ marginBottom: 4 }}>
              <Checkbox>{t('platform.buyuk_kucuk')}</Checkbox>
            </Form.Item>
            <Form.Item name="rakam" valuePropName="checked" style={{ marginBottom: 4 }}>
              <Checkbox>{t('platform.rakam')}</Checkbox>
            </Form.Item>
            <Form.Item name="ozel_karakter" valuePropName="checked" style={{ marginBottom: 0 }}>
              <Checkbox>{t('platform.ozel_karakter')}</Checkbox>
            </Form.Item>
          </div>
        )}

        <Divider style={{ margin: '12px 0' }} />

        <Form.Item
          name="iki_asama_zorunlu"
          label={t('platform.iki_asama_zorunlu')}
          valuePropName="checked"
          extra={t('platform.iki_asama_zorunlu_ipucu')}
        >
          <Switch />
        </Form.Item>

        <Form.Item
          name="ip_izin_listesi"
          label={t('platform.ip_izin_listesi')}
          extra={t('platform.ip_izin_ipucu')}
        >
          <Select mode="tags" tokenSeparators={[',', ' ']} placeholder="10.0.0.0/8" />
        </Form.Item>

        <Divider style={{ margin: '12px 0' }} />

        <Form.Item name="sso_aktif" label={t('platform.sso_baslik')} valuePropName="checked">
          <Switch onChange={setSsoAcik} />
        </Form.Item>

        {ssoAcik && (
          <div style={{ paddingLeft: 12 }}>
            <Form.Item
              name="issuer"
              label={t('platform.issuer')}
              rules={[{ required: true, message: t('platform.issuer_gerekli') }]}
              extra={t('platform.issuer_ipucu')}
            >
              <Input placeholder="https://login.microsoftonline.com/<tenant-id>/v2.0" />
            </Form.Item>
            <Form.Item
              name="istemci_id"
              label={t('platform.istemci_id')}
              rules={[{ required: true, message: t('platform.istemci_id_gerekli') }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="istemci_sirri"
              label={t('platform.istemci_sirri')}
              extra={t('platform.istemci_sirri_ipucu')}
            >
              <Input.Password />
            </Form.Item>
            <Form.Item
              name="donus_url"
              label={t('platform.donus_url')}
              rules={[{ required: true, message: t('platform.donus_url_gerekli') }]}
              extra={t('platform.donus_url_ipucu')}
            >
              <Input placeholder="https://firma.fabrikaos.com/sso/donus" />
            </Form.Item>
            <Form.Item name="izinli_alan_adlari" label={t('platform.izinli_alan_adlari')}>
              <Select mode="tags" tokenSeparators={[',', ' ']} placeholder="firma.com" />
            </Form.Item>
            <Form.Item
              name="jit_provizyon"
              label={t('platform.jit_provizyon')}
              valuePropName="checked"
              extra={t('platform.jit_ipucu')}
            >
              <Switch />
            </Form.Item>
            <Form.Item name="varsayilan_roller" label={t('platform.varsayilan_roller')}>
              <Select mode="tags" tokenSeparators={[',', ' ']} placeholder="izleyici" />
            </Form.Item>
            <Form.Item
              name="claim_eposta"
              label={t('platform.claim_eposta')}
              extra={t('platform.claim_ipucu')}
            >
              <Input placeholder="email" />
            </Form.Item>
            <Form.Item name="claim_gruplar" label={t('platform.claim_gruplar')}>
              <Input placeholder="groups" />
            </Form.Item>
            <Form.Item
              name="debug_claim_log"
              label={t('platform.debug_claim_log')}
              valuePropName="checked"
              extra={t('platform.debug_ipucu')}
            >
              <Switch />
            </Form.Item>
          </div>
        )}

        <div style={{ display: 'flex', gap: 12 }}>
          <Button type="primary" htmlType="submit" loading={kaydet.isPending}>
            {t('platform.kaydet')}
          </Button>
          <Button danger onClick={() => void sifirla()} loading={kaydet.isPending}>
            {t('platform.varsayilana_don')}
          </Button>
        </div>
        <Typography.Paragraph
          type="secondary"
          style={{ marginTop: 12, marginBottom: 0, fontSize: 12 }}
        >
          {t('platform.guvenlik_not')}
        </Typography.Paragraph>
      </Form>
    </Card>
  );
}
