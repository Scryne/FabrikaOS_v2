/**
 * Oturum durumu (Zustand) — access token BELLEKTE tutulur (kalıcı değil; XSS kalıcı
 * sızıntısını azaltır). Refresh token ayrıca localStorage'dadır (bkz. api/jeton.ts) ve
 * sayfa yenilemesinde sessiz giriş için kullanılır. Kullanıcı izinleri RBAC menü ve
 * korunan rotalar için ``Set`` olarak tutulur.
 */

import { create } from 'zustand';

import type { components } from '@/api/types.gen';

export type Kullanici = components['schemas']['BenCevapDTO'];

type AuthDurum = {
  access: string | null;
  kullanici: Kullanici | null;
  izinler: Set<string>;
  girisYapildi: boolean;
  /** Tam oturum kur: access + kullanıcı + izinler. */
  ayarlaOturum: (access: string, kullanici: Kullanici) => void;
  /** Yalnız access'i değiştir (sessiz token yenileme sonrası). */
  ayarlaAccess: (access: string) => void;
  /** Oturumu sıfırla (çıkış / yenileme başarısız). */
  temizle: () => void;
  /** Kullanıcının bu izne sahip olup olmadığı (RBAC). */
  izinVar: (kod: string) => boolean;
};

export const useAuthStore = create<AuthDurum>((set, get) => ({
  access: null,
  kullanici: null,
  izinler: new Set<string>(),
  girisYapildi: false,
  ayarlaOturum: (access, kullanici) =>
    set({
      access,
      kullanici,
      izinler: new Set(kullanici.izinler),
      girisYapildi: true,
    }),
  ayarlaAccess: (access) => set({ access }),
  temizle: () =>
    set({ access: null, kullanici: null, izinler: new Set<string>(), girisYapildi: false }),
  izinVar: (kod) => get().izinler.has(kod),
}));
