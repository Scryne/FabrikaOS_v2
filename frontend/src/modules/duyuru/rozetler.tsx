/** Duyuru rozetleri (önem) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const ONEM_RENK: Record<string, string> = {
  bilgi: 'blue',
  uyari: 'orange',
  kritik: 'error',
};

export function DuyuruOnemEtiketi({ onem }: { onem: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={ONEM_RENK[onem] ?? 'default'} bordered={false}>
      {t(`duyuru.onem_${onem}`)}
    </Tag>
  );
}
