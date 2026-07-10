/**
 * Platform (control-plane) oturum durumu — tenant ``authStore``'undan AYRIK düzlem.
 *
 * Access token bellekte, refresh ayrı localStorage anahtarında (bkz. platform/api.ts).
 * Tenant oturumu ile aynı anda var olabilirler; iki düzlem birbirine dokunmaz.
 */

import { create } from 'zustand';

import type { components } from '@/api/types.gen';

export type PlatformYonetici = components['schemas']['PlatformBenCevapDTO'];

type PlatformAuthDurum = {
  access: string | null;
  yonetici: PlatformYonetici | null;
  girisYapildi: boolean;
  ayarlaOturum: (access: string, yonetici: PlatformYonetici) => void;
  ayarlaAccess: (access: string) => void;
  temizle: () => void;
};

export const usePlatformAuthStore = create<PlatformAuthDurum>((set) => ({
  access: null,
  yonetici: null,
  girisYapildi: false,
  ayarlaOturum: (access, yonetici) => set({ access, yonetici, girisYapildi: true }),
  ayarlaAccess: (access) => set({ access }),
  temizle: () => set({ access: null, yonetici: null, girisYapildi: false }),
}));
