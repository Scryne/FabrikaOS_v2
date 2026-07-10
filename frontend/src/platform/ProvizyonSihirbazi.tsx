/**
 * Provizyon sihirbazı — Steps: kimlik (slug+ad) → plan → yönetici → özet.
 * Provizyon senkron API'ye gider; başarıda tenant detayına yönlendirir
 * ("dakikalar içinde canlı" kabulü: yeni admin hemen giriş yapabilir).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { App as AntdApp, Button, Card, Descriptions, Form, Input, Radio, Steps } from 'antd';

import { useTenantProvizyon, usePlanlar } from './hooks';

type Alanlar = {
  slug: string;
  ad: string;
  plan_kodu: string;
  admin_eposta: string;
  admin_parola: string;
};

const ADIM_ALANLARI: (keyof Alanlar)[][] = [
  ['slug', 'ad'],
  ['plan_kodu'],
  ['admin_eposta', 'admin_parola'],
  [],
];

export function ProvizyonSihirbazi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [form] = Form.useForm<Alanlar>();
  const [adim, setAdim] = useState(0);
  const planlar = usePlanlar();
  const provizyon = useTenantProvizyon();

  const adimlar = [
    { title: t('platform.adim_kimlik') },
    { title: t('platform.adim_plan') },
    { title: t('platform.adim_admin') },
    { title: t('platform.adim_ozet') },
  ];

  async function ileri() {
    try {
      await form.validateFields(ADIM_ALANLARI[adim]);
      setAdim((a) => a + 1);
    } catch {
      // doğrulama mesajları form alanlarında gösterilir
    }
  }

  async function gonder() {
    const degerler = form.getFieldsValue(true) as Alanlar;
    try {
      const tenant = await provizyon.mutateAsync({
        ...degerler,
        slug: degerler.slug.trim().toLowerCase(),
      });
      message.success(t('platform.provizyon_basarili'));
      navigate(`/platform/tenantlar/${tenant.id}`, { replace: true });
    } catch (h) {
      message.error(h instanceof Error ? h.message : t('platform.islem_hatasi'));
    }
  }

  // Form bağlanmadan (ilk render) form metodu çağrılmaz — AntD useForm uyarısı.
  const degerler = adim === 3 ? (form.getFieldsValue(true) as Partial<Alanlar>) : {};

  return (
    <Card style={{ maxWidth: 640 }} title={t('platform.provizyon_baslik')}>
      <Steps size="small" current={adim} items={adimlar} style={{ marginBottom: 24 }} />

      <Form<Alanlar> form={form} layout="vertical" requiredMark={false}>
        {/* Alanlar DOM'da kalır (display:none) — adım değişince değer kaybolmaz. */}
        <div style={{ display: adim === 0 ? 'block' : 'none' }}>
          <Form.Item
            name="slug"
            label={t('platform.slug')}
            extra={t('platform.provizyon_aciklama')}
            rules={[
              { required: true, message: t('platform.slug_gerekli') },
              {
                pattern: /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/,
                message: t('platform.slug_gerekli'),
              },
            ]}
          >
            <Input placeholder="fabrika-a" className="sayisal" />
          </Form.Item>
          <Form.Item
            name="ad"
            label={t('platform.ad')}
            rules={[{ required: true, message: t('platform.ad_gerekli') }]}
          >
            <Input placeholder="Fabrika A.Ş." />
          </Form.Item>
        </div>

        <div style={{ display: adim === 1 ? 'block' : 'none' }}>
          <Form.Item
            name="plan_kodu"
            label={t('platform.plan')}
            rules={[{ required: true, message: t('platform.plan_gerekli') }]}
          >
            <Radio.Group style={{ display: 'grid', gap: 8 }}>
              {(planlar.data ?? []).map((p) => (
                <Radio key={p.kod} value={p.kod}>
                  <strong>{p.ad}</strong>{' '}
                  <span style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>
                    — {p.moduller.length} {t('abonelik.moduller').toLowerCase()} ·{' '}
                    {p.koltuk_limiti ?? t('platform.koltuk_sinirsiz')}{' '}
                    {t('platform.koltuk').toLowerCase()}
                  </span>
                </Radio>
              ))}
            </Radio.Group>
          </Form.Item>
        </div>

        <div style={{ display: adim === 2 ? 'block' : 'none' }}>
          <Form.Item
            name="admin_eposta"
            label={t('platform.admin_eposta')}
            rules={[{ required: true, message: t('platform.eposta_gerekli') }]}
          >
            <Input type="email" placeholder="admin@fabrika-a.test" />
          </Form.Item>
          <Form.Item
            name="admin_parola"
            label={t('platform.admin_parola')}
            rules={[{ required: true, min: 8, message: t('platform.parola_gerekli') }]}
          >
            <Input.Password />
          </Form.Item>
        </div>

        {adim === 3 && (
          <Descriptions
            column={1}
            size="small"
            bordered
            items={[
              {
                key: 'slug',
                label: t('platform.slug'),
                children: <span className="sayisal">{degerler.slug}</span>,
              },
              { key: 'ad', label: t('platform.ad'), children: degerler.ad },
              { key: 'plan', label: t('platform.plan'), children: degerler.plan_kodu },
              {
                key: 'eposta',
                label: t('platform.admin_eposta'),
                children: degerler.admin_eposta,
              },
            ]}
          />
        )}
      </Form>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
        <Button disabled={adim === 0 || provizyon.isPending} onClick={() => setAdim((a) => a - 1)}>
          {t('ortak.geri')}
        </Button>
        {adim < 3 ? (
          <Button type="primary" onClick={() => void ileri()}>
            {t('platform.ileri')}
          </Button>
        ) : (
          <Button type="primary" loading={provizyon.isPending} onClick={() => void gonder()}>
            {t('platform.provizyonla')}
          </Button>
        )}
      </div>
    </Card>
  );
}
