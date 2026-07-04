/** Sözleşme rozetleri (durum) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const DURUM_RENK: Record<string, string> = {
  taslak: 'default',
  aktif: 'success',
  sonlandi: 'blue',
  feshedildi: 'error',
  iptal: 'default',
};

export function SozlesmeDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`sozlesme.durum_${durum}`)}
    </Tag>
  );
}
