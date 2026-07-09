/**
 * DYS veri hook'ları (TanStack Query) — belge + sürüm (yükle/indir). Yükleme multipart
 * (``FormData``), indirme ikili (``istekIndir`` → tarayıcı indirmesi).
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, istekIndir, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Belge = components['schemas']['BelgeCevapDTO'];
export type BelgeOlustur = components['schemas']['BelgeOlusturDTO'];
export type BelgeSurumu = components['schemas']['BelgeSurumuCevapDTO'];
export type DysOzet = components['schemas']['DysOzetDTO'];

export const DYS_ANAHTAR = {
  liste: ['belgeler'] as const,
  detay: (id: number) => ['belge', id] as const,
  surumler: (belgeId: number) => ['belge-surumleri', belgeId] as const,
  ozet: ['dys-ozet'] as const,
};

/** DYS (belge) KPI özeti (OzetSerit). */
export function useDysOzet() {
  return useQuery({
    queryKey: DYS_ANAHTAR.ozet,
    queryFn: () => istek<DysOzet>('GET', `${PREFIX}/dys/ozet`),
  });
}

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useBelgeler(param: SayfaParam) {
  return useSayfaliSorgu<Belge>(DYS_ANAHTAR.liste, '/belgeler', param);
}

export function useBelge(id: number) {
  return useQuery({
    queryKey: DYS_ANAHTAR.detay(id),
    queryFn: () => istek<Belge>('GET', `${PREFIX}/belgeler/${id}`),
    enabled: id > 0,
  });
}

export function useSurumler(belgeId: number) {
  return useQuery({
    queryKey: DYS_ANAHTAR.surumler(belgeId),
    queryFn: () => istek<BelgeSurumu[]>('GET', `${PREFIX}/belgeler/${belgeId}/surumler`),
    enabled: belgeId > 0,
  });
}

export function useBelgeOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: BelgeOlustur) => istek<Belge>('POST', `${PREFIX}/belgeler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DYS_ANAHTAR.liste });
      message.success(t('dys.belge_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useSurumYukle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({
      belgeId,
      dosya,
      aciklama,
    }: {
      belgeId: number;
      dosya: File;
      aciklama: string;
    }) => {
      const fd = new FormData();
      fd.append('dosya', dosya);
      fd.append('aciklama', aciklama);
      return istek<BelgeSurumu>('POST', `${PREFIX}/belgeler/${belgeId}/surumler`, fd);
    },
    onSuccess: (_v, { belgeId }) => {
      void qc.invalidateQueries({ queryKey: DYS_ANAHTAR.surumler(belgeId) });
      void qc.invalidateQueries({ queryKey: DYS_ANAHTAR.detay(belgeId) });
      void qc.invalidateQueries({ queryKey: DYS_ANAHTAR.liste });
      message.success(t('dys.surum_yuklendi'));
    },
    onError: hataGoster,
  });
}

/** Bir belge sürümünü indirir ve tarayıcıda kaydettirir. */
export async function surumuIndir(
  belgeId: number,
  surumNo: number,
  yedekAd: string,
): Promise<void> {
  const { blob, dosyaAdi } = await istekIndir(
    `${PREFIX}/belgeler/${belgeId}/surumler/${surumNo}/indir`,
  );
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = dosyaAdi ?? yedekAd;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
