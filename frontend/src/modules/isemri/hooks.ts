/**
 * İş emri modülü veri hook'ları (TanStack Query) — liste, kanban (gruplama için tek çekim),
 * detay (yorumlu), oluşturma, durum geçişi, yorum ekleme + atama için kullanıcı seçenekleri.
 *
 * Mutasyonlar liste/kanban/detay sorgularını geçersizleştirir. ``is-emirleri`` ön ekiyle
 * yapılan invalidate hem sayfalı listeyi hem kanban'ı yeniler.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type IsEmri = components['schemas']['IsEmriCevapDTO'];
export type IsEmriDetay = components['schemas']['IsEmriDetayDTO'];
export type IsEmriOlustur = components['schemas']['IsEmriOlusturDTO'];
export type DurumGuncelle = components['schemas']['DurumGuncelleDTO'];
export type Yorum = components['schemas']['IsEmriYorumCevapDTO'];
export type Kullanici = components['schemas']['KullaniciCevapDTO'];

export const ISEMRI_ANAHTAR = {
  liste: ['is-emirleri'] as const,
  pano: ['is-emirleri', 'pano'] as const,
  detay: (id: number) => ['is-emri', id] as const,
  kullanicilar: ['kullanicilar', 'secenek'] as const,
};

export function useIsEmirleri(param: SayfaParam) {
  return useSayfaliSorgu<IsEmri>(ISEMRI_ANAHTAR.liste, '/is-emirleri', param);
}

/** Kanban için (gruplama istemci tarafında): en güncel 100 iş emri tek çekimde. */
export function useIsEmriPano() {
  return useQuery({
    queryKey: ISEMRI_ANAHTAR.pano,
    queryFn: () =>
      istek<IsEmri[]>('GET', `${PREFIX}/is-emirleri?sayfa=1&adet=100&siralama=id&yon=desc`),
  });
}

export function useIsEmri(id: number) {
  return useQuery({
    queryKey: ISEMRI_ANAHTAR.detay(id),
    queryFn: () => istek<IsEmriDetay>('GET', `${PREFIX}/is-emirleri/${id}`),
    enabled: id > 0,
  });
}

/** Atama için kullanıcı seçenekleri — yalnız ``etkin`` (kullanici:oku) olduğunda çekilir. */
export function useKullaniciSecenekleri(etkin: boolean) {
  return useQuery({
    queryKey: ISEMRI_ANAHTAR.kullanicilar,
    queryFn: () => istek<Kullanici[]>('GET', `${PREFIX}/kullanicilar?sayfa=1&adet=100`),
    enabled: etkin,
  });
}

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useIsEmriOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: IsEmriOlustur) => istek<IsEmri>('POST', `${PREFIX}/is-emirleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ISEMRI_ANAHTAR.liste });
      message.success(t('isemri.olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useDurumGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: DurumGuncelle }) =>
      istek<IsEmri>('PATCH', `${PREFIX}/is-emirleri/${id}/durum`, govde),
    onSuccess: (_veri, { id }) => {
      void qc.invalidateQueries({ queryKey: ISEMRI_ANAHTAR.liste });
      void qc.invalidateQueries({ queryKey: ISEMRI_ANAHTAR.detay(id) });
      message.success(t('isemri.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useYorumEkle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, metin }: { id: number; metin: string }) =>
      istek<Yorum>('POST', `${PREFIX}/is-emirleri/${id}/yorum`, { metin }),
    onSuccess: (_veri, { id }) => {
      void qc.invalidateQueries({ queryKey: ISEMRI_ANAHTAR.detay(id) });
      message.success(t('isemri.yorum_eklendi'));
    },
    onError: hataGoster,
  });
}
