/**
 * Duruş & Vardiya veri hook'ları (S24) — vardiya tanımları, duruş nedeni kataloğu,
 * duruş kayıtları (sayfalı) + pareto analizi. Duruş kaydı OEE kullanılabilirliğini
 * düşürdüğü için kayıt mutasyonu OEE sorgularını da geçersizleştirir.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';
import { URETIM_ANAHTAR } from '@/modules/uretim/hooks';

export type Vardiya = components['schemas']['VardiyaCevapDTO'];
export type VardiyaOlustur = components['schemas']['VardiyaOlusturDTO'];
export type VardiyaGuncelle = components['schemas']['VardiyaGuncelleDTO'];
export type DurusNedeni = components['schemas']['DurusNedeniCevapDTO'];
export type DurusNedeniOlustur = components['schemas']['DurusNedeniOlusturDTO'];
export type DurusNedeniGuncelle = components['schemas']['DurusNedeniGuncelleDTO'];
export type DurusKaydi = components['schemas']['DurusKaydiCevapDTO'];
export type DurusKaydiOlustur = components['schemas']['DurusKaydiOlusturDTO'];
export type ParetoSatir = components['schemas']['ParetoSatirDTO'];

/** Backend beyaz-listesiyle birebir (``DURUS_SINIFLARI``). */
export const DURUS_SINIFLARI = ['planli', 'plansiz'];

export const DURUS_ANAHTAR = {
  vardiyalar: ['vardiyalar'] as const,
  nedenler: ['durus-nedenleri'] as const,
  kayitlar: ['durus-kayitlari'] as const,
  pareto: (gun: number) => ['durus-pareto', gun] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- Vardiya ---
export function useVardiyalar() {
  return useQuery({
    queryKey: DURUS_ANAHTAR.vardiyalar,
    queryFn: () => istek<Vardiya[]>('GET', `${PREFIX}/vardiyalar`),
  });
}

export function useVardiyaOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: VardiyaOlustur) => istek<Vardiya>('POST', `${PREFIX}/vardiyalar`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DURUS_ANAHTAR.vardiyalar });
      message.success(t('durus.vardiya_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useVardiyaGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: VardiyaGuncelle }) =>
      istek<Vardiya>('PATCH', `${PREFIX}/vardiyalar/${id}`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DURUS_ANAHTAR.vardiyalar });
      message.success(t('durus.vardiya_guncellendi'));
    },
    onError: hataGoster,
  });
}

// --- Duruş nedeni kataloğu ---
export function useDurusNedenleri() {
  return useQuery({
    queryKey: DURUS_ANAHTAR.nedenler,
    queryFn: () => istek<DurusNedeni[]>('GET', `${PREFIX}/durus-nedenleri`),
  });
}

export function useDurusNedeniOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: DurusNedeniOlustur) =>
      istek<DurusNedeni>('POST', `${PREFIX}/durus-nedenleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DURUS_ANAHTAR.nedenler });
      message.success(t('durus.neden_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useDurusNedeniGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: DurusNedeniGuncelle }) =>
      istek<DurusNedeni>('PATCH', `${PREFIX}/durus-nedenleri/${id}`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DURUS_ANAHTAR.nedenler });
      message.success(t('durus.neden_guncellendi'));
    },
    onError: hataGoster,
  });
}

// --- Duruş kayıtları ---
export function useDurusKayitlari(param: SayfaParam) {
  return useSayfaliSorgu<DurusKaydi>(DURUS_ANAHTAR.kayitlar, '/durus-kayitlari', param);
}

export function useDurusKaydiOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: DurusKaydiOlustur) =>
      istek<DurusKaydi>('POST', `${PREFIX}/durus-kayitlari`, govde),
    onSuccess: (_veri, govde) => {
      void qc.invalidateQueries({ queryKey: DURUS_ANAHTAR.kayitlar });
      void qc.invalidateQueries({ queryKey: ['durus-pareto'] });
      // Kayıtlı duruş OEE kullanılabilirliğini düşürür (S24) — OEE görünümleri tazelenir.
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.oeeOzet });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.uretimOzet });
      void qc.invalidateQueries({ queryKey: URETIM_ANAHTAR.makineOee(govde.makine_id) });
      message.success(t('durus.kayit_olusturuldu'));
    },
    onError: hataGoster,
  });
}

// --- Pareto ---
export function useDurusPareto(gun: number) {
  return useQuery({
    queryKey: DURUS_ANAHTAR.pareto(gun),
    queryFn: () => istek<ParetoSatir[]>('GET', `${PREFIX}/durus/pareto?gun=${gun}`),
  });
}
