import { beforeEach, describe, expect, it } from 'vitest';

import type { Kullanici } from './authStore';
import { useAuthStore } from './authStore';

const KULLANICI: Kullanici = {
  id: 1,
  eposta: 'admin@alfa.test',
  ad_soyad: 'Yönetici',
  roller: ['admin'],
  izinler: ['uretim:oku', 'uretim:yaz', 'isemri:oku'],
  iki_asama_aktif: false,
};

describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.getState().temizle();
  });

  it('başlangıçta oturum yok', () => {
    const s = useAuthStore.getState();
    expect(s.access).toBeNull();
    expect(s.kullanici).toBeNull();
    expect(s.girisYapildi).toBe(false);
    expect(s.izinVar('uretim:oku')).toBe(false);
  });

  it('ayarlaOturum access + kullanıcı + izinleri kurar', () => {
    useAuthStore.getState().ayarlaOturum('access-jeton', KULLANICI);
    const s = useAuthStore.getState();
    expect(s.access).toBe('access-jeton');
    expect(s.kullanici?.eposta).toBe('admin@alfa.test');
    expect(s.girisYapildi).toBe(true);
  });

  it('izinVar yalnızca sahip olunan izinde true döner', () => {
    useAuthStore.getState().ayarlaOturum('a', KULLANICI);
    const s = useAuthStore.getState();
    expect(s.izinVar('uretim:yaz')).toBe(true);
    expect(s.izinVar('isemri:yaz')).toBe(false);
  });

  it('ayarlaAccess yalnız access’i günceller (sessiz yenileme)', () => {
    useAuthStore.getState().ayarlaOturum('eski', KULLANICI);
    useAuthStore.getState().ayarlaAccess('yeni');
    const s = useAuthStore.getState();
    expect(s.access).toBe('yeni');
    expect(s.girisYapildi).toBe(true);
  });

  it('temizle oturumu sıfırlar', () => {
    useAuthStore.getState().ayarlaOturum('a', KULLANICI);
    useAuthStore.getState().temizle();
    const s = useAuthStore.getState();
    expect(s.access).toBeNull();
    expect(s.kullanici).toBeNull();
    expect(s.girisYapildi).toBe(false);
  });
});
