/**
 * Ürün & Reçete (BOM) veri hook'ları (S24). Reçete ürün başına tektir; kaydetme
 * **replace-all** PUT'tur (ikiz yerleşim deseni). Malzeme seçenekleri stok modülünün
 * hafif sözlük deseniyle çekilir (tek istek, geniş sayfa).
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';
import type { Malzeme } from '@/modules/stok/hooks';

export type Urun = components['schemas']['UrunCevapDTO'];
export type UrunOlustur = components['schemas']['UrunOlusturDTO'];
export type UrunGuncelle = components['schemas']['UrunGuncelleDTO'];
export type Recete = components['schemas']['ReceteCevapDTO'];
export type ReceteKaydet = components['schemas']['ReceteKaydetDTO'];
export type ReceteKalem = components['schemas']['ReceteKalemCevapDTO'];

export const URUN_ANAHTAR = {
  urunler: ['urunler'] as const,
  urun: (id: number) => ['urun', id] as const,
  recete: (urunId: number) => ['urun', urunId, 'recete'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useUrunler(param: SayfaParam) {
  return useSayfaliSorgu<Urun>(URUN_ANAHTAR.urunler, '/urunler', param);
}

/** İş emri formu / reçete için hafif ürün sözlüğü (tek istek, geniş sayfa). */
export function useUrunSecenekleri(etkin = true) {
  return useQuery({
    queryKey: [...URUN_ANAHTAR.urunler, 'secenek'],
    queryFn: () => istek<Urun[]>('GET', `${PREFIX}/urunler?sayfa=1&adet=100&aktif=true`),
    enabled: etkin,
  });
}

/** Reçete kalemleri / yedek parça için hafif malzeme sözlüğü (stok:oku gerektirir). */
export function useMalzemeSecenekleri(etkin = true) {
  return useQuery({
    queryKey: ['malzemeler', 'secenek'],
    queryFn: () => istek<Malzeme[]>('GET', `${PREFIX}/malzemeler?sayfa=1&adet=100`),
    enabled: etkin,
  });
}

export function useUrunOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: UrunOlustur) => istek<Urun>('POST', `${PREFIX}/urunler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: URUN_ANAHTAR.urunler });
      message.success(t('urun.olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useUrunGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: UrunGuncelle }) =>
      istek<Urun>('PATCH', `${PREFIX}/urunler/${id}`, govde),
    onSuccess: (_veri, { id }) => {
      void qc.invalidateQueries({ queryKey: URUN_ANAHTAR.urunler });
      void qc.invalidateQueries({ queryKey: URUN_ANAHTAR.urun(id) });
      message.success(t('urun.guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useRecete(urunId: number) {
  return useQuery({
    queryKey: URUN_ANAHTAR.recete(urunId),
    queryFn: () => istek<Recete>('GET', `${PREFIX}/urunler/${urunId}/recete`),
    enabled: urunId > 0,
  });
}

export function useReceteKaydet() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ urunId, govde }: { urunId: number; govde: ReceteKaydet }) =>
      istek<Recete>('PUT', `${PREFIX}/urunler/${urunId}/recete`, govde),
    onSuccess: (_veri, { urunId }) => {
      void qc.invalidateQueries({ queryKey: URUN_ANAHTAR.recete(urunId) });
      message.success(t('urun.recete_kaydedildi'));
    },
    onError: hataGoster,
  });
}
