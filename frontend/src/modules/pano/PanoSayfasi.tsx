/** Pano (yer tutucu) — gerçek üretim panosu ve modül ekranları S6'da gelecek. */

import { useTranslation } from 'react-i18next';
import { Typography } from 'antd';

import { useAuthStore } from '@/store/authStore';

export function PanoSayfasi() {
  const { t } = useTranslation();
  const kullanici = useAuthStore((s) => s.kullanici);

  return (
    <div style={{ maxWidth: 720 }}>
      <Typography.Title level={3} style={{ marginTop: 0, letterSpacing: '-0.02em' }}>
        {t('pano.hosgeldin', { ad: kullanici?.ad_soyad || kullanici?.eposta || '' })}
      </Typography.Title>
      <Typography.Paragraph style={{ color: 'var(--metin-soluk)', maxWidth: '60ch' }}>
        {t('pano.yakinda')}
      </Typography.Paragraph>
    </div>
  );
}
