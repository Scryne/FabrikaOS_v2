/** İSG rozetleri (kaza türü/ağırlık + risk seviyesi/durum) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const TUR_RENK: Record<string, string> = {
  kaza: 'error',
  ramak_kala: 'warning',
  meslek_hastaligi: 'volcano',
};

const AGIRLIK_RENK: Record<string, string> = {
  hafif: 'default',
  orta: 'blue',
  agir: 'orange',
  olumcul: 'error',
};

const SEVIYE_RENK: Record<string, string> = {
  dusuk: 'success',
  orta: 'blue',
  yuksek: 'orange',
  cok_yuksek: 'error',
};

const RISK_DURUM_RENK: Record<string, string> = {
  acik: 'default',
  devam: 'processing',
  kapandi: 'success',
};

export function KazaTurEtiketi({ tur }: { tur: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={TUR_RENK[tur] ?? 'default'} bordered={false}>
      {t(`isg.tur_${tur}`)}
    </Tag>
  );
}

export function AgirlikEtiketi({ agirlik }: { agirlik: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={AGIRLIK_RENK[agirlik] ?? 'default'} bordered={false}>
      {t(`isg.agirlik_${agirlik}`)}
    </Tag>
  );
}

export function RiskSeviyeEtiketi({ seviye }: { seviye: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={SEVIYE_RENK[seviye] ?? 'default'} bordered={false}>
      {t(`isg.seviye_${seviye}`)}
    </Tag>
  );
}

export function RiskDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={RISK_DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`isg.risk_durum_${durum}`)}
    </Tag>
  );
}
