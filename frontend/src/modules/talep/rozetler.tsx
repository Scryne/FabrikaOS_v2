/** Talep rozetleri (durum + öncelik) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const DURUM_RENK: Record<string, string> = {
  acik: 'blue',
  inceleniyor: 'processing',
  cozuldu: 'cyan',
  kapandi: 'success',
  iptal: 'default',
};

const ONCELIK_RENK: Record<string, string> = {
  dusuk: 'default',
  orta: 'blue',
  yuksek: 'orange',
};

export function TalepDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`talep.durum_${durum}`)}
    </Tag>
  );
}

export function TalepOncelikEtiketi({ oncelik }: { oncelik: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={ONCELIK_RENK[oncelik] ?? 'default'} bordered={false}>
      {t(`talep.oncelik_${oncelik}`)}
    </Tag>
  );
}
