/**
 * Giriş ekranı — split: solda marka kimliği (kontrol odası: animasyonlu üretim hattı şeması),
 * sağda form. Subdomain yoksa "Firma kodu" alanı gösterilir (tenant fallback). Başarıda panoya gider.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { Alert, Button, Form, Input } from 'antd';

import { girisYap } from '@/api/kimlik';
import { subdomainSlug } from '@/api/tenant';
import { Marka } from '@/components/Marka';

import './giris.css';

type Alanlar = { firmaKodu?: string; eposta: string; parola: string };

/** Soyut üretim hattı şeması — düğümler (makineler) + akış hattı (animasyonlu sinyal). */
function HatSemasi() {
  return (
    <svg
      className="giris-hat"
      viewBox="0 0 380 130"
      fill="none"
      aria-hidden="true"
      role="presentation"
    >
      {/* akış hattı: sabit zemin çizgisi + üzerinde akan sinyal */}
      <path
        d="M14 96 H92 C104 96 110 90 110 78 V52 C110 40 116 34 128 34 H196 C208 34 214 40 214 52 V78 C214 90 220 96 232 96 H366"
        stroke="var(--kenarlik-parlak)"
        strokeWidth="1.5"
      />
      <path
        className="giris-hat-akis"
        d="M14 96 H92 C104 96 110 90 110 78 V52 C110 40 116 34 128 34 H196 C208 34 214 40 214 52 V78 C214 90 220 96 232 96 H366"
        stroke="var(--cyan)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      {/* makine düğümleri: durum noktalı istasyonlar */}
      <g>
        <rect
          x="34"
          y="78"
          width="36"
          height="36"
          rx="9"
          fill="var(--yuzey-ust)"
          stroke="var(--kenarlik-parlak)"
        />
        <circle cx="52" cy="96" r="4" fill="var(--basari)" />
      </g>
      <g>
        <rect
          x="144"
          y="16"
          width="36"
          height="36"
          rx="9"
          fill="var(--yuzey-ust)"
          stroke="var(--kenarlik-parlak)"
        />
        <circle cx="162" cy="34" r="4" fill="var(--basari)" />
      </g>
      <g>
        <rect
          x="252"
          y="78"
          width="36"
          height="36"
          rx="9"
          fill="var(--yuzey-ust)"
          stroke="var(--kenarlik-parlak)"
        />
        <circle cx="270" cy="96" r="4" fill="var(--uyari)" />
      </g>
      <g>
        <rect
          x="330"
          y="78"
          width="36"
          height="36"
          rx="9"
          fill="var(--yuzey-ust)"
          stroke="var(--kenarlik-parlak)"
        />
        <circle cx="348" cy="96" r="4" fill="var(--cyan)" />
      </g>
    </svg>
  );
}

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
      navigate('/pano', { replace: true });
    } catch {
      setHata(true);
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <div className="giris-sayfa">
      <aside className="giris-marka">
        <Link
          to="/"
          aria-label="FabrikaOS"
          style={{ display: 'inline-flex', width: 'fit-content' }}
        >
          <Marka boyut={34} />
        </Link>
        <div>
          <h1 className="giris-baslik-buyuk">{t('kimlik.giris_basligi')}</h1>
          <p style={{ color: 'var(--metin-soluk)', maxWidth: '38ch', margin: '0 0 36px' }}>
            {t('kimlik.giris_aciklama')}
          </p>
          <HatSemasi />
        </div>
        <div className="giris-durum">
          <span className="canli-nokta" aria-hidden="true" />
          {t('ortak.sistem_cevrimici')}
        </div>
      </aside>

      <main className="giris-form-alan">
        <div className="giris-form icerik-acilis">
          <div className="giris-form-marka">
            <Link to="/" aria-label="FabrikaOS" style={{ display: 'inline-flex' }}>
              <Marka boyut={26} />
            </Link>
          </div>

          <h2 className="giris-form-baslik">{t('kimlik.form_baslik')}</h2>

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
