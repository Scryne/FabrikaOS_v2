/** Satınalma talebi durum rozeti (renk + i18n etiket). AntD Tag tabanlı. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const DURUM_RENK: Record<string, string> = {
  taslak: 'default',
  onay_bekliyor: 'processing',
  onaylandi: 'success',
  reddedildi: 'error',
  iptal: 'default',
};

export function TalepDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`satinalma.durum_${durum}`)}
    </Tag>
  );
}
