/**
 * Giriş ekranı — split: solda marka kimliği (kontrol odası), sağda form.
 * Subdomain yoksa "Firma kodu" alanı gösterilir (tenant fallback). Başarıda panoya gider.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, Form, Input } from 'antd';

import { girisYap } from '@/api/kimlik';
import { subdomainSlug } from '@/api/tenant';
import { Marka } from '@/components/Marka';

import './giris.css';

type Alanlar = { firmaKodu?: string; eposta: string; parola: string };

export function GirisSayfasi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(false);

  // Subdomain tenant'ı belirliyse firma kodu sorulmaz.
  const subdomainVar = subdomainSlug(window.location.hostname) !== null;

  async function gonder(degerler: Alanlar) {
    setHata(false);
    setYukleniyor(true);
    try {
      await girisYap(
        subdomainVar ? null : (degerler.firmaKodu ?? null),
        degerler.eposta,
        degerler.parola,
      );
      navigate('/', { replace: true });
    } catch {
      setHata(true);
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <div className="giris-sayfa">
      <aside className="giris-marka">
        <Marka boyut={34} />
        <div>
          <h1 className="giris-baslik-buyuk">{t('kimlik.giris_basligi')}</h1>
          <p style={{ color: 'var(--metin-soluk)', maxWidth: '34ch', margin: 0 }}>
            {t('kimlik.giris_aciklama')}
          </p>
        </div>
        <div className="giris-durum">
          <span className="canli-nokta" aria-hidden="true" />
          {t('ortak.sistem_cevrimici')}
        </div>
      </aside>

      <main className="giris-form-alan">
        <div className="giris-form icerik-acilis">
          <div className="giris-form-marka">
            <Marka boyut={26} />
          </div>

          {hata && (
            <Alert
              type="error"
              showIcon
              message={t('kimlik.hatali_giris')}
              style={{ marginBottom: 16 }}
            />
          )}

          <Form<Alanlar>
            layout="vertical"
            onFinish={gonder}
            requiredMark={false}
            disabled={yukleniyor}
          >
            {!subdomainVar && (
              <Form.Item
                name="firmaKodu"
                label={t('kimlik.firma_kodu')}
                extra={t('kimlik.firma_kodu_ipucu')}
                rules={[{ required: true, message: t('kimlik.firma_kodu_gerekli') }]}
              >
                <Input autoComplete="organization" placeholder="alfa" />
              </Form.Item>
            )}

            <Form.Item
              name="eposta"
              label={t('kimlik.eposta')}
              rules={[{ required: true, message: t('kimlik.eposta_gerekli') }]}
            >
              <Input type="email" autoComplete="username" />
            </Form.Item>

            <Form.Item
              name="parola"
              label={t('kimlik.parola')}
              rules={[{ required: true, message: t('kimlik.parola_gerekli') }]}
            >
              <Input.Password autoComplete="current-password" />
            </Form.Item>

            <Button type="primary" htmlType="submit" block size="large" loading={yukleniyor}>
              {t('kimlik.giris_yap')}
            </Button>
          </Form>
        </div>
      </main>
    </div>
  );
}
