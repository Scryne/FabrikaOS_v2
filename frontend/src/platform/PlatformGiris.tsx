/**
 * Platform giriş ekranı — tek kart, PLATFORM düzlem çipi. Tenant giriş ekranından
 * bilinçli olarak farklıdır (yanlış düzlemde oturum açma riskine karşı).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, Form, Input } from 'antd';

import { Marka } from '@/components/Marka';

import { platformGirisYap } from './kimlik';
import './platform.css';

type Alanlar = { eposta: string; parola: string };

export function PlatformGiris() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState(false);

  async function gonder(degerler: Alanlar) {
    setHata(false);
    setYukleniyor(true);
    try {
      await platformGirisYap(degerler.eposta, degerler.parola);
      navigate('/platform', { replace: true });
    } catch {
      setHata(true);
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <div className="platform-giris">
      <div className="platform-giris-kart icerik-acilis">
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 20,
          }}
        >
          <Marka boyut={26} />
          <span className="platform-cip">{t('platform.filigran')}</span>
        </div>

        <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>{t('platform.giris_baslik')}</h2>
        <p style={{ color: 'var(--metin-soluk)', fontSize: 13, margin: '0 0 20px' }}>
          {t('platform.giris_aciklama')}
        </p>

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
    </div>
  );
}
