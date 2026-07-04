/**
 * İK veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir aynıdır (canlı
 * invalidate). Personel + izin talebi (onay akışı) + fazla mesai/zimmet/sertifika alt-kayıtları.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Personel = components['schemas']['PersonelCevapDTO'];
export type PersonelOlustur = components['schemas']['PersonelOlusturDTO'];
export type PersonelGuncelle = components['schemas']['PersonelGuncelleDTO'];
export type IzinTalebi = components['schemas']['IzinTalebiCevapDTO'];
export type IzinTalebiOlustur = components['schemas']['IzinTalebiOlusturDTO'];
export type FazlaMesai = components['schemas']['FazlaMesaiCevapDTO'];
export type FazlaMesaiOlustur = components['schemas']['FazlaMesaiOlusturDTO'];
export type Zimmet = components['schemas']['ZimmetCevapDTO'];
export type ZimmetOlustur = components['schemas']['ZimmetOlusturDTO'];
export type Sertifika = components['schemas']['SertifikaCevapDTO'];
export type SertifikaOlustur = components['schemas']['SertifikaOlusturDTO'];

export const IK_ANAHTAR = {
  personeller: ['personeller'] as const,
  personel: (id: number) => ['personel', id] as const,
  izinler: ['izin-talepleri'] as const,
  izin: (id: number) => ['izin-talebi', id] as const,
  mesailer: (pid: number) => ['fazla-mesailer', pid] as const,
  zimmetler: (pid: number) => ['zimmetler', pid] as const,
  sertifikalar: (pid: number) => ['sertifikalar', pid] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- Personel ---
export function usePersoneller(param: SayfaParam) {
  return useSayfaliSorgu<Personel>(IK_ANAHTAR.personeller, '/personeller', param);
}

export function usePersonel(id: number) {
  return useQuery({
    queryKey: IK_ANAHTAR.personel(id),
    queryFn: () => istek<Personel>('GET', `${PREFIX}/personeller/${id}`),
    enabled: id > 0,
  });
}

export function usePersonelOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: PersonelOlustur) => istek<Personel>('POST', `${PREFIX}/personeller`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.personeller });
      message.success(t('ik.personel_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function usePersonelGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: PersonelGuncelle }) =>
      istek<Personel>('PATCH', `${PREFIX}/personeller/${id}`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.personeller });
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.personel(id) });
      message.success(t('ik.guncellendi'));
    },
    onError: hataGoster,
  });
}

// --- İzin talebi ---
export function useIzinler(param: SayfaParam) {
  return useSayfaliSorgu<IzinTalebi>(IK_ANAHTAR.izinler, '/izin-talepleri', param);
}

export function useIzin(id: number) {
  return useQuery({
    queryKey: IK_ANAHTAR.izin(id),
    queryFn: () => istek<IzinTalebi>('GET', `${PREFIX}/izin-talepleri/${id}`),
    enabled: id > 0,
  });
}

export function useIzinOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: IzinTalebiOlustur) =>
      istek<IzinTalebi>('POST', `${PREFIX}/izin-talepleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.izinler });
      message.success(t('ik.izin_olusturuldu'));
    },
    onError: hataGoster,
  });
}

/** İzin durum aksiyonu: gonder | onayla | reddet | iptal. */
export function useIzinDurumAksiyon() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({
      id,
      aksiyon,
      red_nedeni,
    }: {
      id: number;
      aksiyon: string;
      red_nedeni?: string;
    }) =>
      istek<IzinTalebi>(
        'POST',
        `${PREFIX}/izin-talepleri/${id}/${aksiyon}`,
        aksiyon === 'reddet' ? { red_nedeni: red_nedeni ?? '' } : undefined,
      ),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.izinler });
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.izin(id) });
      message.success(t('ik.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}

// --- Fazla mesai (personele bağlı alt-liste) ---
export function useMesailer(personelId: number) {
  return useQuery({
    queryKey: IK_ANAHTAR.mesailer(personelId),
    queryFn: () => istek<FazlaMesai[]>('GET', `${PREFIX}/fazla-mesailer?personel_id=${personelId}`),
    enabled: personelId > 0,
  });
}

export function useMesaiOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: FazlaMesaiOlustur) =>
      istek<FazlaMesai>('POST', `${PREFIX}/fazla-mesailer`, govde),
    onSuccess: (_v, govde) => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.mesailer(govde.personel_id) });
      message.success(t('ik.mesai_eklendi'));
    },
    onError: hataGoster,
  });
}

export function useMesaiOnayla() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id }: { id: number; personelId: number }) =>
      istek<FazlaMesai>('POST', `${PREFIX}/fazla-mesailer/${id}/onayla`),
    onSuccess: (_v, { personelId }) => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.mesailer(personelId) });
      message.success(t('ik.mesai_onaylandi'));
    },
    onError: hataGoster,
  });
}

// --- Zimmet (personele bağlı alt-liste) ---
export function useZimmetler(personelId: number) {
  return useQuery({
    queryKey: IK_ANAHTAR.zimmetler(personelId),
    queryFn: () => istek<Zimmet[]>('GET', `${PREFIX}/zimmetler?personel_id=${personelId}`),
    enabled: personelId > 0,
  });
}

export function useZimmetOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: ZimmetOlustur) => istek<Zimmet>('POST', `${PREFIX}/zimmetler`, govde),
    onSuccess: (_v, govde) => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.zimmetler(govde.personel_id) });
      message.success(t('ik.zimmet_eklendi'));
    },
    onError: hataGoster,
  });
}

export function useZimmetIade() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id }: { id: number; personelId: number }) =>
      istek<Zimmet>('POST', `${PREFIX}/zimmetler/${id}/iade`),
    onSuccess: (_v, { personelId }) => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.zimmetler(personelId) });
      message.success(t('ik.zimmet_iade_alindi'));
    },
    onError: hataGoster,
  });
}

// --- Sertifika (personele bağlı alt-liste) ---
export function useSertifikalar(personelId: number) {
  return useQuery({
    queryKey: IK_ANAHTAR.sertifikalar(personelId),
    queryFn: () => istek<Sertifika[]>('GET', `${PREFIX}/sertifikalar?personel_id=${personelId}`),
    enabled: personelId > 0,
  });
}

export function useSertifikaOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: SertifikaOlustur) =>
      istek<Sertifika>('POST', `${PREFIX}/sertifikalar`, govde),
    onSuccess: (_v, govde) => {
      void qc.invalidateQueries({ queryKey: IK_ANAHTAR.sertifikalar(govde.personel_id) });
      message.success(t('ik.sertifika_eklendi'));
    },
    onError: hataGoster,
  });
}
