/**
 * Platform veri kancaları (TanStack Query) — tüm platform ekranları buradan beslenir.
 * Yazma mutasyonları ilgili sorguları invalidate eder; ihraç listesi arka plan işi
 * bitene dek kısa aralıkla yoklanır (WS platform düzleminde yok — bilinçli sadelik).
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { components } from '@/api/types.gen';

import { PLATFORM_PREFIX, platformIstek, platformIstekSayfali } from './api';
import { usePlatformAuthStore } from './store';

type S = components['schemas'];
export type TenantOzet = S['TenantOzetDTO'];
export type TenantDetay = S['TenantDetayDTO'];
export type TenantProvizyon = S['TenantProvizyonDTO'];
export type TenantGuncelle = S['TenantGuncelleDTO'];
export type PlatformSaglik = S['PlatformSaglikDTO'];
export type AbonelikSatir = S['AbonelikSatirDTO'];
export type PlanSatir = S['PlanSatirDTO'];
export type IhracCevap = S['IhracCevapDTO'];
export type ModulDurum = S['PlatformModulDurumDTO'];
export type OzellikDurum = S['PlatformOzellikDurumDTO'];

function girisliMi(): boolean {
  return usePlatformAuthStore.getState().girisYapildi;
}

export function useTenantlar(sayfa: number, adet: number, arama: string) {
  const p = new URLSearchParams({ sayfa: String(sayfa), adet: String(adet) });
  if (arama) p.set('arama', arama);
  return useQuery({
    queryKey: ['platform', 'tenantlar', sayfa, adet, arama],
    queryFn: () => platformIstekSayfali<TenantOzet>(`${PLATFORM_PREFIX}/tenantlar?${p}`),
    placeholderData: keepPreviousData,
    enabled: girisliMi(),
  });
}

export function useTenantDetay(id: number | null) {
  return useQuery({
    queryKey: ['platform', 'tenant', id],
    queryFn: () => platformIstek<TenantDetay>('GET', `${PLATFORM_PREFIX}/tenantlar/${id}`),
    enabled: id !== null && girisliMi(),
  });
}

export function usePlatformAbonelikler(sayfa: number, adet: number) {
  return useQuery({
    queryKey: ['platform', 'abonelikler', sayfa, adet],
    queryFn: () =>
      platformIstekSayfali<AbonelikSatir>(
        `${PLATFORM_PREFIX}/abonelikler?sayfa=${sayfa}&adet=${adet}`,
      ),
    placeholderData: keepPreviousData,
    enabled: girisliMi(),
  });
}

export function usePlanlar() {
  return useQuery({
    queryKey: ['platform', 'planlar'],
    queryFn: () => platformIstek<PlanSatir[]>('GET', `${PLATFORM_PREFIX}/planlar`),
    staleTime: 5 * 60_000, // katalog nadiren değişir
    enabled: girisliMi(),
  });
}

export function usePlatformSaglik() {
  return useQuery({
    queryKey: ['platform', 'saglik'],
    queryFn: () => platformIstek<PlatformSaglik>('GET', `${PLATFORM_PREFIX}/saglik`),
    refetchInterval: 30_000,
    enabled: girisliMi(),
  });
}

export function useIhraclar(tenantId: number | null) {
  return useQuery({
    queryKey: ['platform', 'ihraclar', tenantId],
    queryFn: () =>
      platformIstekSayfali<IhracCevap>(`${PLATFORM_PREFIX}/ihraclar?tenant_id=${tenantId}&adet=10`),
    enabled: tenantId !== null && girisliMi(),
    // Kuyruktaki/hazırlanan iş varken yokla; hepsi terminalse dur.
    refetchInterval: (q) =>
      q.state.data?.veri.some((k) => k.durum === 'kuyrukta' || k.durum === 'hazirlaniyor')
        ? 3_000
        : false,
  });
}

function useTenantInvalidate() {
  const qc = useQueryClient();
  return (id?: number) => {
    void qc.invalidateQueries({ queryKey: ['platform', 'tenantlar'] });
    void qc.invalidateQueries({ queryKey: ['platform', 'abonelikler'] });
    if (id !== undefined) void qc.invalidateQueries({ queryKey: ['platform', 'tenant', id] });
  };
}

export function useTenantProvizyon() {
  const invalidate = useTenantInvalidate();
  return useMutation({
    mutationFn: (govde: TenantProvizyon) =>
      platformIstek<TenantDetay>('POST', `${PLATFORM_PREFIX}/tenantlar`, govde),
    onSuccess: () => invalidate(),
  });
}

export function useTenantGuncelle(id: number) {
  const invalidate = useTenantInvalidate();
  return useMutation({
    mutationFn: (govde: TenantGuncelle) =>
      platformIstek<TenantDetay>('PATCH', `${PLATFORM_PREFIX}/tenantlar/${id}`, govde),
    onSuccess: () => invalidate(id),
  });
}

export function useTenantAktiflik(id: number) {
  const invalidate = useTenantInvalidate();
  return useMutation({
    mutationFn: (aktif: boolean) =>
      platformIstek<TenantDetay>(
        'POST',
        `${PLATFORM_PREFIX}/tenantlar/${id}/${aktif ? 'aktiflestir' : 'askiya-al'}`,
      ),
    onSuccess: () => invalidate(id),
  });
}

export function useTenantSil(id: number) {
  const invalidate = useTenantInvalidate();
  return useMutation({
    mutationFn: (onay: string) =>
      platformIstek<null>('DELETE', `${PLATFORM_PREFIX}/tenantlar/${id}`, { onay }),
    onSuccess: () => invalidate(id),
  });
}

export function useModulHakkiAyarla(id: number) {
  const invalidate = useTenantInvalidate();
  return useMutation({
    mutationFn: ({ modulKodu, acik }: { modulKodu: string; acik: boolean | null }) =>
      platformIstek<ModulDurum[]>(
        'PUT',
        `${PLATFORM_PREFIX}/tenantlar/${id}/modul-haklari/${modulKodu}`,
        { acik },
      ),
    onSuccess: () => invalidate(id),
  });
}

export function useOzellikBayragiAyarla(id: number) {
  const invalidate = useTenantInvalidate();
  return useMutation({
    mutationFn: ({ kod, acik }: { kod: string; acik: boolean | null }) =>
      platformIstek<OzellikDurum[]>(
        'PUT',
        `${PLATFORM_PREFIX}/tenantlar/${id}/ozellik-bayraklari/${kod}`,
        { acik },
      ),
    onSuccess: () => invalidate(id),
  });
}

export function useIhracBaslat(tenantId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      platformIstek<IhracCevap>('POST', `${PLATFORM_PREFIX}/tenantlar/${tenantId}/ihrac`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['platform', 'ihraclar', tenantId] }),
  });
}

/**
 * Tenant güvenlik ayarlarını yazar (S23): parola politikası, zorunlu 2FA, IP izin
 * listesi, OIDC/SSO. ``null`` gövde varsayılana döner (tüm kısıtlar kalkar).
 *
 * OIDC istemci sırrı sunucudan MASKELİ gelir; maske aynen geri gönderilirse sunucu
 * mevcut sırrı korur (bkz. backend platform/guvenlik_ayar.py).
 */
export function useGuvenlikAyarla(id: number) {
  const invalidate = useTenantInvalidate();
  return useMutation({
    mutationFn: (ayarlar: Record<string, unknown> | null) =>
      platformIstek<Record<string, unknown> | null>(
        'PUT',
        `${PLATFORM_PREFIX}/tenantlar/${id}/guvenlik-ayarlari`,
        { ayarlar },
      ),
    onSuccess: () => invalidate(id),
  });
}
