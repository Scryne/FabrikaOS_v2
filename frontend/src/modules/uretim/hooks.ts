/**
 * Üretim modülü veri hook'ları (TanStack Query) — makineler, makine detayı/OEE, OEE özeti,
 * üretim verileri + yazma mutasyonları. Mutasyonlar başarıda ilgili sorguları geçersizleştirir
 * ve AntD ``message`` ile geri bildirim verir; hata zarfı mesajı kullanıcıya gösterilir.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Makine = components['schemas']['MakineCevapDTO'];
export type MakineOlustur = components['schemas']['MakineOlusturDTO'];
export type UretimVerisi = components['schemas']['UretimVerisiCevapDTO'];
export type UretimGiris = components['schemas']['UretimGirisDTO'];
export type Oee = components['schemas']['OeeCevapDTO'];
export type OeeOzetSatir = components['schemas']['OeeOzetSatirDTO'];
export type UretimOzet = components['schemas']['UretimOzetDTO'];

export const URETIM_ANAHTAR = {
  makineler: ['makineler'] as const,
  makine: (id: number) => ['makine', id] as const,
  makineOee: (id: number) => ['makine', id, 'oee'] as const,
  uretim: ['uretim-verileri'] as const,
  oeeOzet: ['oee-ozet'] as const,
  uretimOzet: ['uretim-ozet'] as const,
};

export function useMakineler(param: SayfaParam) {
  return useSayfaliSorgu<Makine>(URETIM_ANAHTAR.makineler, '/makineler', param);
}

/** Üretim modülü KPI özeti (OzetSerit + analiz donut). */
export function useUretimOzet() {
  return useQuery({
    queryKey: URETIM_ANAHTAR.uretimOzet,
    queryFn: () => istek<UretimOzet>('GET', `${PREFIX}/uretim/ozet`),
  });
}

/** Filtreler/seçim için hafif makine sözlüğü (id → makine); büyük sayfa, tek istek. */
export function useMakineSecenekleri() {
  return useQuery({
    queryKey: [...URETIM_ANAHTAR.makineler, 'secenek'],
    queryFn: () =>
      istek<Makine[]>('GET', `${PREFIX}/makineler?sayfa=1&adet=100&siralama=kod&yon=asc`),
  });
}

export function useMakine(id: number) {
  return useQuery({
    queryKey: URETIM_ANAHTAR.makine(id),
    queryFn: () => istek<Makine>('GET', `${PREFIX}/makineler/${id}`),
    enabled: id > 0,
  });
}

export function useMakineOee(id: number) {
  return useQuery({
    queryKey: URETIM_ANAHTAR.makineOee(id),
    queryFn: () => istek<Oee>('GET', `${PREFIX}/makineler/${id}/oee`),
    enabled: id > 0,
  });
}

/** Bu makinenin son ``adet`` üretim kaydı (trend grafiği + vardiya kırılımı + toplulaştırma için). */
export function useMakineUretimSerisi(id: number, adet = 24) {
  return useQuery({
    queryKey: [...URETIM_ANAHTAR.makine(id), 'seri', adet] as const,
    queryFn: () =>
      istek<UretimVerisi[]>(
        'GET',
        `${PREFIX}/uretim-verileri?makine_id=${id}&sayfa=1&adet=${adet}&siralama=zaman&yon=desc`,
      ),
    enabled: id > 0,
  });
}

export function useOeeOzet() {
  return useQuery({
    queryKey: URETIM_ANAHTAR.oeeOzet,
    queryFn: () => istek<OeeOzetSatir[]>('GET', `${PREFIX}/oee/ozet`),
  });
}

export function useUretimVerileri(param: SayfaParam) {
  return useSayfaliSorgu<UretimVerisi>(URETIM_ANAHTAR.uretim, '/uretim-verileri', param);
}

/** Mutasyon hatasını standart hata zarfı mesajıyla gösteren yardımcı. */
function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useMakineOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: MakineOlustur) => istek<Makine>('POST', `${PREFIX}/makineler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.makineler });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.oeeOzet });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.uretimOzet });
      message.success(t('uretim.makine_eklendi'));
    },
    onError: hataGoster,
  });
}

export function useMakineDurumGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, durum }: { id: number; durum: string }) =>
      istek<Makine>('PATCH', `${PREFIX}/makineler/${id}/durum`, { durum }),
    onSuccess: (_veri, { id }) => {
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.makine(id) });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.makineler });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.oeeOzet });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.uretimOzet });
      message.success(t('uretim.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useUretimGiris() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: UretimGiris) =>
      istek<UretimVerisi>('POST', `${PREFIX}/uretim-verileri`, govde),
    onSuccess: (_veri, govde) => {
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.uretim });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.oeeOzet });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.uretimOzet });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.makineOee(govde.makine_id) });
      message.success(t('uretim.uretim_kaydedildi'));
    },
    onError: hataGoster,
  });
}
