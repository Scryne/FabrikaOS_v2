/** Kalite rozetleri (durum/önem/sonuç) — AntD Tag + i18n. */

import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';

const DURUM_RENK: Record<string, string> = {
  acik: 'default',
  kok_neden: 'processing',
  aksiyon_plani: 'processing',
  uygulama: 'warning',
  dogrulama: 'cyan',
  kapandi: 'success',
  iptal: 'default',
};

const ONEM_RENK: Record<string, string> = {
  dusuk: 'default',
  orta: 'blue',
  yuksek: 'orange',
  kritik: 'error',
};

const SONUC_RENK: Record<string, string> = {
  gecti: 'success',
  kaldi: 'error',
  sartli: 'warning',
};

export function UygunsuzlukDurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={DURUM_RENK[durum] ?? 'default'} bordered={false}>
      {t(`kalite.durum_${durum}`)}
    </Tag>
  );
}

export function OnemEtiketi({ onem }: { onem: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={ONEM_RENK[onem] ?? 'default'} bordered={false}>
      {t(`kalite.onem_${onem}`)}
    </Tag>
  );
}

export function KontrolSonucEtiketi({ sonuc }: { sonuc: string }) {
  const { t } = useTranslation();
  return (
    <Tag color={SONUC_RENK[sonuc] ?? 'default'} bordered={false}>
      {t(`kalite.sonuc_${sonuc}`)}
    </Tag>
  );
}
