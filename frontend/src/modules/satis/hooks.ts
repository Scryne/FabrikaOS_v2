/**
 * Satış veri hook'ları (S31, ADR-0050). Onay iş emri ve satınalma talebi açtığı için o listeler
 * de geçersizleşir; Onaylarım (satınalma onayı) da yeni talebi göstermeli.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Siparis = components['schemas']['SatisSiparisCevapDTO'];
export type SiparisOlustur = components['schemas']['SatisSiparisOlusturDTO'];
export type SiparisGuncelle = components['schemas']['SatisSiparisGuncelleDTO'];
export type Mrp = components['schemas']['SatisMrpDTO'];
export type SatisOzet = components['schemas']['SatisOzetDTO'];

export const SATIS_ANAHTAR = {
  siparisler: ['satis-siparisleri'] as const,
  siparis: (id: number) => ['satis-siparisi', id] as const,
  mrp: (id: number) => ['satis-mrp', id] as const,
  ozet: ['satis-ozet'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

function useGecersizlestir() {
  const qc = useQueryClient();
  return () => {
    for (const a of [
      SATIS_ANAHTAR.siparisler,
      SATIS_ANAHTAR.ozet,
      ['satis-siparisi'],
      ['satis-mrp'],
      ['is-emirleri'],
      ['satinalma-talepleri'],
      ['onaylarim'],
      ['planlama-cizelge'],
    ]) {
      void qc.invalidateQueries({ queryKey: a });
    }
  };
}

export function useSiparisler(param: SayfaParam) {
  return useSayfaliSorgu<Siparis>(SATIS_ANAHTAR.siparisler, '/satis-siparisleri', param);
}

export function useSiparis(id: number | null) {
  return useQuery({
    queryKey: SATIS_ANAHTAR.siparis(id ?? 0),
    queryFn: () => istek<Siparis>('GET', `${PREFIX}/satis-siparisleri/${id}`),
    enabled: id != null,
  });
}

export function useMrp(id: number | null) {
  return useQuery({
    queryKey: SATIS_ANAHTAR.mrp(id ?? 0),
    queryFn: () => istek<Mrp>('GET', `${PREFIX}/satis-siparisleri/${id}/mrp`),
    enabled: id != null,
  });
}

export function useSatisOzet() {
  return useQuery({
    queryKey: SATIS_ANAHTAR.ozet,
    queryFn: () => istek<SatisOzet>('GET', `${PREFIX}/satis/ozet`),
  });
}

export function useSiparisOlustur() {
  const gecersiz = useGecersizlestir();
  const hata = useHataGoster();
  return useMutation({
    mutationFn: (govde: SiparisOlustur) =>
      istek<Siparis>('POST', `${PREFIX}/satis-siparisleri`, govde),
    onSuccess: gecersiz,
    onError: hata,
  });
}

export function useSiparisGuncelle() {
  const gecersiz = useGecersizlestir();
  const hata = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: SiparisGuncelle }) =>
      istek<Siparis>('PUT', `${PREFIX}/satis-siparisleri/${id}`, govde),
    onSuccess: gecersiz,
    onError: hata,
  });
}

export function useSiparisOnayla() {
  const gecersiz = useGecersizlestir();
  const hata = useHataGoster();
  return useMutation({
    mutationFn: ({ id, makineId }: { id: number; makineId?: number }) =>
      istek<Siparis>('POST', `${PREFIX}/satis-siparisleri/${id}/onayla`, {
        makine_id: makineId ?? null,
      }),
    onSuccess: gecersiz,
    onError: hata,
  });
}

export function useSiparisDurum() {
  const gecersiz = useGecersizlestir();
  const hata = useHataGoster();
  return useMutation({
    mutationFn: ({ id, durum }: { id: number; durum: string }) =>
      istek<Siparis>('POST', `${PREFIX}/satis-siparisleri/${id}/durum`, { durum }),
    onSuccess: gecersiz,
    onError: hata,
  });
}
