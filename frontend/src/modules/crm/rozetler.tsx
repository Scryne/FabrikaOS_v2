/** CRM rozetleri (firma tipi) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const TIP_RENK: Record<string, string> = {
  musteri: 'blue',
  tedarikci: 'gold',
  her_ikisi: 'geekblue',
};

export function FirmaTipEtiketi({ tip }: { tip: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={TIP_RENK[tip] ?? 'default'} bordered={false}>
      {t(`crm.tip_${tip}`)}
    </Tag>
  );
}
