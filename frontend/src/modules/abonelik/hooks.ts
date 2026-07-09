/**
 * Abonelik & entitlement hook'ları (S16 / ADR-0018).
 *
 * `useModuller` menü süzgeci + rota kapısını besler. Veri yüklenmemişken veya uçtan
 * hata geldiğinde süzgeç **fail-open** davranır (UI gizlemez) — güvenlik backend'dedir
 * (kapalı modül 403 MODUL_KAPALI), UI süzgeci kozmetiktir.
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type ModulDurum = components['schemas']['ModulDurumDTO'];
export type OzellikDurum = components['schemas']['OzellikDurumDTO'];
export type ModullerCevap = components['schemas']['ModullerCevapDTO'];
export type AbonelikCevap = components['schemas']['AbonelikCevapDTO'];

export function useModuller() {
  return useQuery({
    queryKey: ['moduller'],
    queryFn: () => istek<ModullerCevap>('GET', `${PREFIX}/moduller`),
    staleTime: 60_000,
  });
}

/** `kod -> açık?` sorgulayıcısı; veri yokken herkese açık sayar (fail-open). */
export function useModulAcik(): (kod?: string) => boolean {
  const { data } = useModuller();
  return useMemo(() => {
    if (!data) return () => true;
    const harita = new Map(data.moduller.map((m) => [m.kod, m.acik]));
    return (kod?: string) => (kod === undefined ? true : (harita.get(kod) ?? true));
  }, [data]);
}

export function useAbonelik() {
  return useQuery({
    queryKey: ['abonelik'],
    queryFn: () => istek<AbonelikCevap>('GET', `${PREFIX}/abonelik`),
  });
}
