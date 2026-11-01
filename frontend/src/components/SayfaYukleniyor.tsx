/** Rota parçası yüklenirken içerik alanında gösterilen sade yükleniyor durumu (S27-A). */

import { useTranslation } from 'react-i18next';
import { Spin } from 'antd';

export function SayfaYukleniyor() {
  const { t } = useTranslation();
  return (
    <div
      role="status"
      aria-live="polite"
      style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}
    >
      <Spin tip={t('ortak.yukleniyor')}>
        <div style={{ width: 120, height: 40 }} />
      </Spin>
    </div>
  );
}
