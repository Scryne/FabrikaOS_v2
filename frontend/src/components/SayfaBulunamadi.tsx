/**
 * 404 — tanımsız adres. Eskiden her bilinmeyen yol sessizce /pano'ya yönleniyordu: yanlış
 * yazılmış ya da kaldırılmış bir bağlantı "çalışıyor" gibi görünüp kullanıcıyı başka bir
 * ekrana atıyordu. Artık hangi adresin bulunamadığı söylenir ve iki çıkış verilir.
 * Kabuksuz çizilir (oturum gerekmez); kabuk menüsü oturum açıksa panodan zaten erişilir.
 */

import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Button } from 'antd';

import { LogoIsareti } from '@/components/Marka';

export function SayfaBulunamadi() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const onceki = document.title;
    document.title = `${t('bulunamadi.sekme')} · FabrikaOS`;
    return () => {
      document.title = onceki;
    };
  }, [t]);

  return (
    <main className="bulunamadi">
      <div className="bulunamadi-kart">
        <Link to="/" aria-label="FabrikaOS" className="bulunamadi-logo">
          <LogoIsareti boyut={32} />
        </Link>
        <p className="bulunamadi-kod sayisal" aria-hidden="true">
          404
        </p>
        <h1 className="bulunamadi-baslik">{t('bulunamadi.baslik')}</h1>
        <p className="bulunamadi-aciklama">{t('bulunamadi.aciklama')}</p>
        <code className="bulunamadi-yol sayisal">{pathname}</code>
        <div className="bulunamadi-aksiyon">
          <Button type="primary" onClick={() => navigate('/pano')}>
            {t('yetki.panoya_don')}
          </Button>
          <Button onClick={() => navigate('/')}>{t('bulunamadi.ana_sayfa')}</Button>
        </div>
      </div>
    </main>
  );
}
