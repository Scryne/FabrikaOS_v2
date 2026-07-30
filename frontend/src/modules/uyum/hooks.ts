/**
 * Uyum veri hook'ları (S23 / ADR-0022) — denetim kaydı görünürlüğü + KVKK paketi + rıza.
 *
 * Denetim kayıtları **append-only**'dir: yalnız listeleme uçları vardır, düzenleme/silme
 * mutation'ı bilinçli olarak YOKTUR (DB tarafında da trigger korur).
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, istekIndir, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type DenetimKaydi = components['schemas']['DenetimKaydiDTO'];
export type KvkkIhrac = components['schemas']['KvkkIhracCevapDTO'];
export type ConsentKaydi = components['schemas']['ConsentCevapDTO'];

export const UYUM_ANAHTAR = {
  denetim: ['denetim-kayitlari'] as const,
  kaynaklar: ['denetim-kaynaklari'] as const,
  ihraclar: ['kvkk-ihraclar'] as const,
  consent: ['consent'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- Denetim kaydı ---
export function useDenetimKayitlari(param: SayfaParam) {
  return useSayfaliSorgu<DenetimKaydi>(UYUM_ANAHTAR.denetim, '/denetim-kayitlari', param);
}

/** Filtre açılırı için denetimde geçen kaynak adları. */
export function useDenetimKaynaklari() {
  return useQuery({
    queryKey: UYUM_ANAHTAR.kaynaklar,
    queryFn: () => istek<string[]>('GET', `${PREFIX}/denetim-kayitlari/kaynaklar`),
    staleTime: 5 * 60_000,
  });
}

// --- KVKK ihracı ---
export function useKvkkIhraclar(param: SayfaParam) {
  return useSayfaliSorgu<KvkkIhrac>(UYUM_ANAHTAR.ihraclar, '/kvkk/ihraclar', param);
}

export function useIhracBaslat() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (girdi: { kisi_turu: string; kisi_id: number }) =>
      istek<KvkkIhrac>('POST', `${PREFIX}/kvkk/ihrac`, girdi),
    onSuccess: () => void qc.invalidateQueries({ queryKey: UYUM_ANAHTAR.ihraclar }),
    onError: hataGoster,
  });
}

/** Hazır ihracı indirir (409 → henüz hazır değil). */
export async function ihracIndir(kayit: KvkkIhrac): Promise<void> {
  const { blob, dosyaAdi } = await istekIndir(`${PREFIX}/kvkk/ihraclar/${kayit.id}/indir`);
  const url = URL.createObjectURL(blob);
  const bag = document.createElement('a');
  bag.href = url;
  bag.download = dosyaAdi ?? kayit.dosya_adi ?? `${kayit.kod}.zip`;
  document.body.appendChild(bag);
  bag.click();
  document.body.removeChild(bag);
  URL.revokeObjectURL(url);
}

export function useAnonimlestir() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (girdi: { kisi_turu: string; kisi_id: number; onay: string }) =>
      istek<Record<string, unknown>>('POST', `${PREFIX}/kvkk/anonimlestir`, girdi),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: UYUM_ANAHTAR.denetim });
      void qc.invalidateQueries({ queryKey: UYUM_ANAHTAR.ihraclar });
    },
    onError: hataGoster,
  });
}

// --- Rıza / aydınlatma (kişisel yüzey) ---
export function useConsentKayitlari() {
  return useQuery({
    queryKey: UYUM_ANAHTAR.consent,
    queryFn: () => istek<ConsentKaydi[]>('GET', `${PREFIX}/consent`),
  });
}

export function useConsentEkle() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (girdi: { tur: string; metin_surumu: string; kabul: boolean }) =>
      istek<ConsentKaydi>('POST', `${PREFIX}/consent`, girdi),
    onSuccess: () => void qc.invalidateQueries({ queryKey: UYUM_ANAHTAR.consent }),
    onError: hataGoster,
  });
}
