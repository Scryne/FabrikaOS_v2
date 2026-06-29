/** İş emri öncelik + durum rozetleri (renk + i18n etiket). AntD Tag tabanlı. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const ONCELIK_RENK: Record<string, string> = {
  dusuk: 'default',
  orta: 'blue',
  yuksek: 'gold',
  kritik: 'red',
};

const DURUM_RENK: Record<string, string> = {
  acik: 'default',
  atandi: 'cyan',
  devam_ediyor: 'processing',
  kapandi: 'success',
  iptal: 'default',
};

export function OncelikRozet({ oncelik }: { oncelik: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={ONCELIK_RENK[oncelik] ?? 'default'} bordered={false}>
      {t(`isemri.oncelik_${oncelik}`)}
    </Tag>
  );
}

export function DurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`isemri.durum_${durum}`)}
    </Tag>
  );
}
