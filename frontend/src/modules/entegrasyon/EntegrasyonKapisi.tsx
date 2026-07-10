/**
 * Webhook yüzeyi erişim kapısı: `entegrasyon` modülü VEYA `webhook-onizleme`
 * bayrağı açıksa içerik; ikisi de kapalıysa standart modül-kapalı upsell'i
 * (`ModulKapisi`). Backend'deki `modul_veya_ozellik_gerekli`nin UI yansıması.
 */

import type { ReactNode } from 'react';

import { ModulKapisi } from '@/routes/ModulKapisi';

import { useWebhookErisim } from './hooks';

export function EntegrasyonKapisi({ children }: { children: ReactNode }) {
  const erisim = useWebhookErisim();
  if (erisim) return <>{children}</>;
  // Erişim yok → modül kapalı upsell'i (bayrak da kapalı olduğundan mesaj doğru).
  return <ModulKapisi modul="entegrasyon">{children}</ModulKapisi>;
}
