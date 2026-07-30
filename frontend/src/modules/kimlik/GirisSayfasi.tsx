/**
 * Giriş ekranı — split: solda marka kimliği (kontrol odası: animasyonlu üretim hattı şeması),
 * sağda form. Subdomain yoksa "Firma kodu" alanı gösterilir (tenant fallback). Başarıda panoya gider.
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { Alert, Button, Divider, Form, Input, Space, Typography } from 'antd';

import { ApiHata } from '@/api/client';
import { girisYap, ikiAsamaDogrula, ssoAcikMi, ssoBaslat } from '@/api/kimlik';
import { subdomainSlug } from '@/api/tenant';
import { Marka } from '@/components/Marka';

import { IkiAsamaKurulum } from './IkiAsamaKurulum';

import './giris.css';

type Alanlar = { firmaKodu?: string; eposta: string; parola: string };

/** Giriş ekranının aşaması: parola → (2FA kodu | zorunlu 2FA kurulumu). */
type Asama =
  | { tur: 'parola' }
  | { tur: '2fa'; geciciToken: string }
  | { tur: '2fa-kurulum'; geciciToken: string };

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
  const [asama, setAsama] = useState<Asama>({ tur: 'parola' });
  const [kod, setKod] = useState('');
  const [kodHatasi, setKodHatasi] = useState<string | null>(null);
  const [firmaKodu, setFirmaKodu] = useState('');
  const [ssoVar, setSsoVar] = useState(false);
  const [ssoHatasi, setSsoHatasi] = useState<string | null>(null);

  // Subdomain tenant'ı belirliyse firma kodu sorulmaz.
  const subdomainVar = subdomainSlug(window.location.hostname) !== null;

  // Subdomain varsa tenant baştan bellidir → SSO düğmesi hemen sorgulanabilir. Firma kodu
  // ile giriliyorsa kullanıcı kodu yazana kadar beklenir (tenant çözülemeden sorulamaz).
  useEffect(() => {
    if (!subdomainVar && firmaKodu.trim().length < 2) {
      setSsoVar(false);
      return;
    }
    let iptal = false;
    void ssoAcikMi(subdomainVar ? null : firmaKodu).then((acik) => {
      if (!iptal) setSsoVar(acik);
    });
    return () => {
      iptal = true;
    };
  }, [subdomainVar, firmaKodu]);

  async function gonder(degerler: Alanlar) {
    setHata(false);
    setYukleniyor(true);
    try {
      const sonuc = await girisYap(
        subdomainVar ? null : (degerler.firmaKodu ?? null),
        degerler.eposta,
        degerler.parola,
      );
      if (sonuc.durum === 'tamam') {
        navigate('/pano', { replace: true });
      } else if (sonuc.durum === '2fa') {
        setAsama({ tur: '2fa', geciciToken: sonuc.geciciToken });
      } else {
        setAsama({ tur: '2fa-kurulum', geciciToken: sonuc.geciciToken });
      }
    } catch {
      setHata(true);
    } finally {
      setYukleniyor(false);
    }
  }

  async function koduDogrula() {
    if (asama.tur !== '2fa') return;
    setKodHatasi(null);
    setYukleniyor(true);
    try {
      const sonuc = await ikiAsamaDogrula(asama.geciciToken, kod.trim());
      if (sonuc.durum === 'tamam') navigate('/pano', { replace: true });
    } catch (e) {
      setKodHatasi(e instanceof ApiHata ? e.message : t('kimlik.kod_hatali'));
    } finally {
      setYukleniyor(false);
    }
  }

  async function ssoyaGit() {
    setSsoHatasi(null);
    setYukleniyor(true);
    try {
      const url = await ssoBaslat(subdomainVar ? null : firmaKodu);
      window.location.assign(url);
    } catch (e) {
      setSsoHatasi(e instanceof ApiHata ? e.message : t('kimlik.sso_hatasi'));
      setYukleniyor(false);
    }
  }

  /** Zorunlu-2FA kurulumu bitti: kullanıcı artık parolayla normal giriş yapabilir. */
  function kurulumTamamlandi() {
    setAsama({ tur: 'parola' });
    setKod('');
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

          <h2 className="giris-form-baslik">
            {asama.tur === 'parola' ? t('kimlik.form_baslik') : t('kimlik.iki_asama_baslik')}
          </h2>

          {asama.tur === 'parola' && (
            <>
              {hata && (
                <Alert
                  type="error"
                  showIcon
                  message={t('kimlik.hatali_giris')}
                  style={{ marginBottom: 16 }}
                />
              )}
              {ssoHatasi && (
                <Alert type="error" showIcon message={ssoHatasi} style={{ marginBottom: 16 }} />
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
                    <Input
                      autoComplete="organization"
                      placeholder="alfa"
                      onChange={(e) => setFirmaKodu(e.target.value)}
                    />
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

              {ssoVar && (
                <>
                  <Divider plain style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>
                    {t('kimlik.veya')}
                  </Divider>
                  <Button block size="large" loading={yukleniyor} onClick={() => void ssoyaGit()}>
                    {t('kimlik.sso_ile_giris')}
                  </Button>
                </>
              )}
            </>
          )}

          {asama.tur === '2fa' && (
            <Space direction="vertical" size={14} style={{ width: '100%' }}>
              <Typography.Paragraph style={{ marginBottom: 0, color: 'var(--metin-soluk)' }}>
                {t('kimlik.iki_asama_aciklama')}
              </Typography.Paragraph>
              {kodHatasi && <Alert type="error" showIcon message={kodHatasi} />}
              <Input
                value={kod}
                onChange={(e) => setKod(e.target.value)}
                onPressEnter={() => void koduDogrula()}
                placeholder="123456"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={12}
                size="large"
                autoFocus
                className="sayisal"
                aria-label={t('kimlik.dogrulama_kodu')}
              />
              <Button
                type="primary"
                block
                size="large"
                loading={yukleniyor}
                disabled={kod.trim().length < 6}
                onClick={() => void koduDogrula()}
              >
                {t('kimlik.dogrula')}
              </Button>
              <Button type="link" block onClick={() => setAsama({ tur: 'parola' })}>
                {t('ortak.geri')}
              </Button>
            </Space>
          )}

          {asama.tur === '2fa-kurulum' && (
            <Space direction="vertical" size={14} style={{ width: '100%' }}>
              <Alert
                type="info"
                showIcon
                message={t('kimlik.zorunlu_2fa_baslik')}
                description={t('kimlik.zorunlu_2fa_aciklama')}
              />
              <IkiAsamaKurulum
                geciciToken={asama.geciciToken}
                onTamamlandi={kurulumTamamlandi}
                onIptal={() => setAsama({ tur: 'parola' })}
              />
            </Space>
          )}
        </div>
      </main>
    </div>
  );
}
