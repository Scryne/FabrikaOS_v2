/** 403 — gerekli izne sahip olmayan kullanıcı için. */

import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Button, Result } from 'antd';

export function YetkisizSayfa() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <Result
      status="403"
      title={t('yetki.yetkisiz_baslik')}
      subTitle={t('yetki.yetkisiz_aciklama')}
      extra={
        <Button type="primary" onClick={() => navigate('/')}>
          {t('yetki.panoya_don')}
        </Button>
      }
    />
  );
}
