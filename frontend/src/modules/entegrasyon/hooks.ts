/**
 * Entegrasyon (webhook + API anahtarı) veri hook'ları — S18 / ADR-0020.
 *
 * Gizli anahtar/anahtar YALNIZ oluşturma ve anahtar-yenile yanıtlarında tam döner;
 * mutation sonuçları çağırana aktarılır ki "bir kez göster" modalı açılabilsin.
 * ``useWebhookErisim`` webhook uçlarının kapısını (modül VEYA `webhook-onizleme`
 * bayrağı) UI tarafında yansıtır — fail-open, güvenlik backend'dedir.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useModuller } from '@/modules/abonelik/hooks';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Webhook = components['schemas']['WebhookCevapDTO'];
export type WebhookOlustur = components['schemas']['WebhookOlusturDTO'];
export type WebhookGuncelle = components['schemas']['WebhookGuncelleDTO'];
export type Teslimat = components['schemas']['TeslimatCevapDTO'];
export type OlayTuru = components['schemas']['OlayTuruCevapDTO'];
export type ApiAnahtari = components['schemas']['ApiAnahtariCevapDTO'];
export type ApiAnahtariOlustur = components['schemas']['ApiAnahtariOlusturDTO'];

export const ENTEGRASYON_ANAHTAR = {
  webhooklar: ['webhooklar'] as const,
  teslimatlar: ['webhook-teslimatlar'] as const,
  olayTurleri: ['webhook-olay-turleri'] as const,
  apiAnahtarlari: ['api-anahtarlari'] as const,
};

/** API anahtarına atanabilir kapsam beyaz-listesi (backend ile hizalı). */
export const API_KAPSAMLARI = ['uretim:oku', 'stok:oku', 'satinalma:oku'] as const;

/** Webhook yüzeyi erişimi: `entegrasyon` modülü AÇIK **veya** `webhook-onizleme`
 * bayrağı açık. Veri yokken fail-open (UI gizlemez; backend 403 zorlar). */
export function useWebhookErisim(): boolean {
  const { data } = useModuller();
  if (!data) return true;
  const modulAcik = data.moduller.find((m) => m.kod === 'entegrasyon')?.acik ?? true;
  const bayrakAcik = data.ozellikler.find((o) => o.kod === 'webhook-onizleme')?.acik ?? false;
  return modulAcik || bayrakAcik;
}

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- Webhook abonelikleri ---

export function useWebhooklar(param: SayfaParam) {
  return useSayfaliSorgu<Webhook>(ENTEGRASYON_ANAHTAR.webhooklar, '/webhooklar', param);
}

export function useOlayTurleri(etkin = true) {
  return useQuery({
    queryKey: ENTEGRASYON_ANAHTAR.olayTurleri,
    queryFn: () => istek<OlayTuru[]>('GET', `${PREFIX}/webhooklar/olay-turleri`),
    staleTime: 5 * 60_000,
    enabled: etkin,
  });
}

export function useWebhookOlustur() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: WebhookOlustur) => istek<Webhook>('POST', `${PREFIX}/webhooklar`, govde),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.webhooklar }),
    onError: hataGoster,
  });
}

export function useWebhookGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, ...govde }: WebhookGuncelle & { id: number }) =>
      istek<Webhook>('PATCH', `${PREFIX}/webhooklar/${id}`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.webhooklar });
      message.success(t('entegrasyon.guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useWebhookSil() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (id: number) => istek<null>('DELETE', `${PREFIX}/webhooklar/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.webhooklar });
      message.success(t('entegrasyon.silindi'));
    },
    onError: hataGoster,
  });
}

/** Yeni imza anahtarı üretir; TAM anahtar yalnız bu yanıtta döner (bir kez göster). */
export function useAnahtarYenile() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (id: number) => istek<Webhook>('POST', `${PREFIX}/webhooklar/${id}/anahtar-yenile`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.webhooklar }),
    onError: hataGoster,
  });
}

// --- Teslimat günlüğü ---

export function useTeslimatlar(param: SayfaParam) {
  return useSayfaliSorgu<Teslimat>(
    ENTEGRASYON_ANAHTAR.teslimatlar,
    '/webhooklar/teslimatlar',
    param,
  );
}

export function useYenidenDene() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (id: number) =>
      istek<Teslimat>('POST', `${PREFIX}/webhooklar/teslimatlar/${id}/yeniden-dene`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.teslimatlar });
      message.success(t('entegrasyon.yeniden_denendi'));
    },
    onError: hataGoster,
  });
}

// --- API anahtarları ---

export function useApiAnahtarlari(param: SayfaParam) {
  return useSayfaliSorgu<ApiAnahtari>(
    ENTEGRASYON_ANAHTAR.apiAnahtarlari,
    '/api-anahtarlari',
    param,
  );
}

export function useApiAnahtarOlustur() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: ApiAnahtariOlustur) =>
      istek<ApiAnahtari>('POST', `${PREFIX}/api-anahtarlari`, govde),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.apiAnahtarlari }),
    onError: hataGoster,
  });
}

export function useApiAnahtarGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, aktif }: { id: number; aktif: boolean }) =>
      istek<ApiAnahtari>('PATCH', `${PREFIX}/api-anahtarlari/${id}`, { aktif }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.apiAnahtarlari });
      message.success(t('entegrasyon.guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useApiAnahtarSil() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (id: number) => istek<null>('DELETE', `${PREFIX}/api-anahtarlari/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ENTEGRASYON_ANAHTAR.apiAnahtarlari });
      message.success(t('entegrasyon.anahtar_silindi'));
    },
    onError: hataGoster,
  });
}
