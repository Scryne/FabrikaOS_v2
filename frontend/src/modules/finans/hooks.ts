/**
 * Finans veri hook'ları (S29, ADR-0048). Mutasyonlar fatura/cari/ödeme/özet sorgularını birlikte
 * geçersizleştirir: bir fatura kesimi ya da tahsilat dördünü de değiştirir.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, istekIndir, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Fatura = components['schemas']['FaturaCevapDTO'];
export type FaturaOlustur = components['schemas']['FaturaOlusturDTO'];
export type FaturaGuncelle = components['schemas']['FaturaGuncelleDTO'];
export type Odeme = components['schemas']['OdemeCevapDTO'];
export type OdemeOlustur = components['schemas']['OdemeOlusturDTO'];
export type CariHesap = components['schemas']['CariHesapCevapDTO'];
export type CariEkstre = components['schemas']['CariEkstreDTO'];
export type FinansOzet = components['schemas']['FinansOzetDTO'];
export type Yaslandirma = components['schemas']['YaslandirmaDTO'];
export type IsEmriMaliyeti = components['schemas']['IsEmriMaliyetiDTO'];

export const FINANS_ANAHTAR = {
  faturalar: ['faturalar'] as const,
  fatura: (id: number) => ['fatura', id] as const,
  odemeler: ['odemeler'] as const,
  cariler: ['cari-hesaplar'] as const,
  ekstre: (firmaId: number) => ['cari-ekstre', firmaId] as const,
  ozet: ['finans-ozet'] as const,
  yaslandirma: ['finans-yaslandirma'] as const,
  maliyet: (gun: number) => ['finans-maliyet', gun] as const,
};

/** Türkçe para biçimi: 1234567.5 → "1.234.567,50 ₺" (TRY dışı birimler kodla). */
export function paraBicim(deger: number, birim = 'TRY'): string {
  const metin = deger.toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return birim === 'TRY' ? `${metin} ₺` : `${metin} ${birim}`;
}

/**
 * KPI kartı için kısa tutar: kuruşsuz ("316.440 ₺"), milyon üstü "1,25 mn ₺". Tam tutar tablolarda.
 */
export function paraKisa(deger: number): string {
  if (Math.abs(deger) >= 1_000_000) {
    const mn = (deger / 1_000_000).toLocaleString('tr-TR', { maximumFractionDigits: 2 });
    return `${mn} mn ₺`;
  }
  return `${Math.round(deger).toLocaleString('tr-TR')} ₺`;
}

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
      FINANS_ANAHTAR.faturalar,
      FINANS_ANAHTAR.odemeler,
      FINANS_ANAHTAR.cariler,
      FINANS_ANAHTAR.ozet,
      FINANS_ANAHTAR.yaslandirma,
      ['fatura'],
      ['cari-ekstre'],
      ['onaylarim'],
    ]) {
      void qc.invalidateQueries({ queryKey: a });
    }
  };
}

export function useFinansOzet() {
  return useQuery({
    queryKey: FINANS_ANAHTAR.ozet,
    queryFn: () => istek<FinansOzet>('GET', `${PREFIX}/finans/ozet`),
  });
}

export function useYaslandirma() {
  return useQuery({
    queryKey: FINANS_ANAHTAR.yaslandirma,
    queryFn: () => istek<Yaslandirma>('GET', `${PREFIX}/finans/yaslandirma`),
  });
}

export function useMaliyet(gun: number) {
  return useQuery({
    queryKey: FINANS_ANAHTAR.maliyet(gun),
    queryFn: () => istek<IsEmriMaliyeti[]>('GET', `${PREFIX}/finans/maliyet?gun=${gun}`),
  });
}

export function useFaturalar(param: SayfaParam) {
  return useSayfaliSorgu<Fatura>(FINANS_ANAHTAR.faturalar, '/faturalar', param);
}

export function useFatura(id: number) {
  return useQuery({
    queryKey: FINANS_ANAHTAR.fatura(id),
    queryFn: () => istek<Fatura>('GET', `${PREFIX}/faturalar/${id}`),
    enabled: id > 0,
  });
}

export function useFaturaOlustur() {
  const hata = useHataGoster();
  const yenile = useGecersizlestir();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (govde: FaturaOlustur) => istek<Fatura>('POST', `${PREFIX}/faturalar`, govde),
    onSuccess: () => {
      yenile();
      void message.success(t('finans.taslak_kaydedildi'));
    },
    onError: hata,
  });
}

export function useFaturaGuncelle() {
  const hata = useHataGoster();
  const yenile = useGecersizlestir();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: FaturaGuncelle }) =>
      istek<Fatura>('PATCH', `${PREFIX}/faturalar/${id}`, govde),
    onSuccess: yenile,
    onError: hata,
  });
}

export type FaturaAksiyon = 'gonder' | 'kes' | 'iade' | 'iptal';

export function useFaturaAksiyon() {
  const hata = useHataGoster();
  const yenile = useGecersizlestir();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: ({ id, aksiyon, neden }: { id: number; aksiyon: FaturaAksiyon; neden?: string }) =>
      istek<Fatura>(
        'POST',
        `${PREFIX}/faturalar/${id}/${aksiyon}`,
        aksiyon === 'iade' || aksiyon === 'iptal' ? { neden: neden ?? '' } : undefined,
      ),
    onSuccess: (_v, d) => {
      yenile();
      void message.success(t(`finans.aksiyon_tamam_${d.aksiyon}`));
    },
    onError: hata,
  });
}

export function useOdemeler(param: SayfaParam) {
  return useSayfaliSorgu<Odeme>(FINANS_ANAHTAR.odemeler, '/odemeler', param);
}

export function useOdemeOlustur() {
  const hata = useHataGoster();
  const yenile = useGecersizlestir();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    // Idempotency-Key: çift tık ya da ağ kopmasında aynı ödeme ikinci kez yazılmaz.
    mutationFn: ({ govde, anahtar }: { govde: OdemeOlustur; anahtar: string }) =>
      istek<Odeme>('POST', `${PREFIX}/odemeler`, govde, true, { 'Idempotency-Key': anahtar }),
    onSuccess: () => {
      yenile();
      void message.success(t('finans.odeme_kaydedildi'));
    },
    onError: hata,
  });
}

export function useCariler(param: SayfaParam) {
  return useSayfaliSorgu<CariHesap>(FINANS_ANAHTAR.cariler, '/cari-hesaplar', param);
}

export function useEkstre(firmaId: number) {
  return useQuery({
    queryKey: FINANS_ANAHTAR.ekstre(firmaId),
    queryFn: () => istek<CariEkstre>('GET', `${PREFIX}/cari-hesaplar/${firmaId}/ekstre`),
    enabled: firmaId > 0,
  });
}

/** Fatura bilgi nüshasını (PDF) yeni sekmede açar; tarayıcı engellerse indirir. */
export async function faturaPdfAc(faturaId: number, kod: string): Promise<void> {
  const { blob } = await istekIndir(`${PREFIX}/faturalar/${faturaId}/pdf`);
  const url = URL.createObjectURL(blob);
  const pencere = window.open(url, '_blank', 'noopener');
  if (!pencere) {
    const a = document.createElement('a');
    a.href = url;
    a.download = `${kod}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
