/** Modül ekranı yer tutucu — gerçek ekranlar sonraki sprintlerde gelir (S6+). */

import { useTranslation } from 'react-i18next';
import { Empty, Typography } from 'antd';

export function ModulYerTutucu({ baslikAnahtari }: { baslikAnahtari: string }) {
  const { t } = useTranslation();
  return (
    <div>
      <Typography.Title level={3} style={{ marginTop: 0, letterSpacing: '-0.02em' }}>
        {t(baslikAnahtari)}
      </Typography.Title>
      <div style={{ padding: '48px 0' }}>
        <Empty description={t('pano.yakinda_modul')} />
      </div>
    </div>
  );
}
