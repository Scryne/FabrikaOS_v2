/** İK rozetleri (izin durumu/türü + zimmet durumu) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const IZIN_DURUM_RENK: Record<string, string> = {
  taslak: 'default',
  onay_bekliyor: 'processing',
  onaylandi: 'success',
  reddedildi: 'error',
  iptal: 'default',
};

const IZIN_TUR_RENK: Record<string, string> = {
  yillik: 'blue',
  mazeret: 'gold',
  hastalik: 'volcano',
  ucretsiz: 'default',
  dogum: 'magenta',
  babalik: 'geekblue',
};

const ZIMMET_DURUM_RENK: Record<string, string> = {
  zimmetli: 'processing',
  iade_edildi: 'success',
};

export function IzinDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={IZIN_DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`ik.durum_${durum}`)}
    </Tag>
  );
}

export function IzinTuruEtiketi({ tur }: { tur: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={IZIN_TUR_RENK[tur] ?? 'default'} bordered={false}>
      {t(`ik.izin_turu_${tur}`)}
    </Tag>
  );
}

export function ZimmetDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={ZIMMET_DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`ik.zimmet_durum_${durum}`)}
    </Tag>
  );
}
