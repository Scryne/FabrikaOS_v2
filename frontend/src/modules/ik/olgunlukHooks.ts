/**
 * S26-B İK hook'ları (ADR-0044): yıllık izin bakiyesi, yönetici ataması + org şeması, işe giriş /
 * çıkış kontrol listeleri. Bakiye anahtarı ``['izin-bakiyesi', id]``; izin olayları (olayIsle.ts)
 * ve kontrol listesi tamamlanması bunu tazeler.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

import { IK_ANAHTAR, type Personel } from './hooks';

export type IzinBakiyesi = components['schemas']['IzinBakiyesiDTO'];
export type OrgDugum = components['schemas']['OrgDugumDTO'];
export type KontrolListesi = components['schemas']['KontrolListesiDTO'];

export const IK26_ANAHTAR = {
  bakiye: (id: number) => ['izin-bakiyesi', id] as const,
  org: (dep?: string) => ['org-semasi', dep ?? ''] as const,
  listeler: (id: number) => ['kontrol-listeleri', id] as const,
  secenekler: ['personeller', 'secenek'] as const,
};

function useHata() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

/** Seçiciler için aktif personel sözlüğü (tek istek, en çok 100). */
export function usePersonelSecenekleri(etkin = true) {
  return useQuery({
    queryKey: IK26_ANAHTAR.secenekler,
    queryFn: () =>
      istek<Personel[]>('GET', `${PREFIX}/personeller?sayfa=1&adet=100&siralama=ad&yon=asc`),
    enabled: etkin,
  });
}

export function useIzinBakiyesi(personelId: number | undefined) {
  return useQuery({
    queryKey: IK26_ANAHTAR.bakiye(personelId ?? 0),
    queryFn: () => istek<IzinBakiyesi>('GET', `${PREFIX}/personeller/${personelId}/izin-bakiyesi`),
    enabled: !!personelId && personelId > 0,
  });
}

export function useYoneticiAta(personelId: number) {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (yonetici_id: number | null) =>
      istek('PUT', `${PREFIX}/personeller/${personelId}/yonetici`, { yonetici_id }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.personel(personelId) });
      void qc.invalidateQueries({ queryKey: ['org-semasi'] });
    },
    onError: hata,
  });
}

export function useOrgSemasi(departman?: string) {
  return useQuery({
    queryKey: IK26_ANAHTAR.org(departman),
    queryFn: () =>
      istek<OrgDugum[]>(
        'GET',
        `${PREFIX}/ik/org-semasi${departman ? `?departman=${encodeURIComponent(departman)}` : ''}`,
      ),
  });
}

export function useKontrolListeleri(personelId: number) {
  return useQuery({
    queryKey: IK26_ANAHTAR.listeler(personelId),
    queryFn: () =>
      istek<KontrolListesi[]>('GET', `${PREFIX}/personeller/${personelId}/kontrol-listeleri`),
  });
}

export function useKontrolListesiAc(personelId: number) {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (tur: 'giris' | 'cikis') =>
      istek<KontrolListesi>('POST', `${PREFIX}/personeller/${personelId}/kontrol-listeleri`, {
        tur,
      }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: IK26_ANAHTAR.listeler(personelId) }),
    onError: hata,
  });
}

export function useMaddeIsaretle(personelId: number) {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (v: { listeId: number; anahtar: string; tamam: boolean }) =>
      istek<KontrolListesi>(
        'PUT',
        `${PREFIX}/kontrol-listeleri/${v.listeId}/maddeler/${v.anahtar}`,
        { tamam: v.tamam },
      ),
    onSuccess: (liste) => {
      void qc.invalidateQueries({ queryKey: IK26_ANAHTAR.listeler(personelId) });
      if (liste.durum === 'tamamlandi') {
        // Çıkış listesi personeli pasifleştirir.
        void qc.invalidateQueries({ queryKey: IK_ANAHTAR.personel(personelId) });
        void qc.invalidateQueries({ queryKey: IK_ANAHTAR.personeller });
      }
    },
    onError: hata,
  });
}
