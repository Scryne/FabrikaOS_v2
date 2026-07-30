/**
 * SSO dönüş (callback) ekranı — IdP kullanıcıyı ``?code=..&state=..`` ile buraya yollar.
 *
 * Bu rota IdP'de kayıtlı ``redirect_uri`` ile birebir aynı olmalıdır (tenant ayarındaki
 * ``donus_url``). Kod tek kullanımlıktır: React StrictMode'un çift effect'i ikinci kez
 * ``tamamla`` çağırırsa IdP ``invalid_grant`` döner → ref ile tek atış garanti edilir.
 */

import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Button, Space, Spin } from 'antd';

import { ApiHata } from '@/api/client';
import { ssoTamamla } from '@/api/kimlik';
import { LogoIsareti } from '@/components/Marka';

export function SsoDonusSayfasi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [parametreler] = useSearchParams();
  const [hata, setHata] = useState<string | null>(null);
  const calisti = useRef(false);

  useEffect(() => {
    if (calisti.current) return;
    calisti.current = true;

    const kod = parametreler.get('code');
    const state = parametreler.get('state');
    const idpHatasi = parametreler.get('error');

    if (idpHatasi) {
      setHata(parametreler.get('error_description') ?? idpHatasi);
      return;
    }
    if (!kod || !state) {
      setHata(t('kimlik.sso_eksik_parametre'));
      return;
    }

    void ssoTamamla(kod, state)
      .then((sonuc) => {
        // 2FA açıksa kullanıcı ikinci adımı giriş ekranında tamamlar.
        navigate(sonuc.durum === 'tamam' ? '/pano' : '/giris', { replace: true });
      })
      .catch((e: unknown) => {
        setHata(e instanceof ApiHata ? e.message : t('kimlik.sso_hatasi'));
      });
  }, [parametreler, navigate, t]);

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 18,
        padding: 24,
      }}
    >
      <LogoIsareti boyut={40} />
      {hata ? (
        <Space direction="vertical" align="center" size={16} style={{ maxWidth: 460 }}>
          <Alert type="error" showIcon message={t('kimlik.sso_basarisiz')} description={hata} />
          <Button type="primary" onClick={() => navigate('/giris', { replace: true })}>
            {t('kimlik.giris_ekranina_don')}
          </Button>
        </Space>
      ) : (
        <>
          <Spin />
          <span style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>
            {t('kimlik.sso_tamamlaniyor')}
          </span>
        </>
      )}
    </div>
  );
}
