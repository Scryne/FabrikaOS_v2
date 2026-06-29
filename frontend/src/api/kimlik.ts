/**
 * Kimlik (auth) servisi — giriş, sessiz başlatma (bootstrap), çıkış, parola değiştirme.
 *
 * Token akışı: ``/kimlik/token`` (form) → refresh localStorage'a, access belleğe; sonra
 * ``/kimlik/ben`` ile kullanıcı + izinler store'a. Sayfa yüklenince ``oturumBaslat`` saklı
 * refresh ile sessiz giriş dener.
 */

import { useAuthStore } from '@/store/authStore';
import type { Kullanici } from '@/store/authStore';

import { istek, oturumDusur, PREFIX } from './client';
import { refreshOku, refreshSakla } from './jeton';
import { tenantSakla } from './tenant';
import type { components } from './types.gen';

type Jeton = components['schemas']['TokenCevapDTO'];

async function kullaniciYukle(access: string): Promise<void> {
  useAuthStore.getState().ayarlaAccess(access);
  const kullanici = await istek<Kullanici>('GET', `${PREFIX}/kimlik/ben`);
  useAuthStore.getState().ayarlaOturum(access, kullanici);
}

/**
 * Giriş. ``firmaKodu`` verilirse (subdomain yokken fallback) tenant olarak saklanır.
 */
export async function girisYap(
  firmaKodu: string | null,
  eposta: string,
  parola: string,
): Promise<void> {
  if (firmaKodu) tenantSakla(firmaKodu.trim().toLowerCase());

  const form = new URLSearchParams({ username: eposta, password: parola });
  const jeton = await istek<Jeton>('POST', `${PREFIX}/kimlik/token`, form, false);
  refreshSakla(jeton.refresh_token);
  await kullaniciYukle(jeton.access_token);
}

/**
 * Sayfa yükünde sessiz giriş: saklı refresh varsa yeni access alıp kullanıcıyı yükler.
 * Başarısızsa oturumu temizler. İlk açılışta (refresh yok) hiç istek atmaz.
 */
export async function oturumBaslat(): Promise<boolean> {
  const refresh = refreshOku();
  if (!refresh) return false;
  try {
    const jeton = await istek<Jeton>(
      'POST',
      `${PREFIX}/kimlik/yenile`,
      { refresh_token: refresh },
      false,
    );
    refreshSakla(jeton.refresh_token);
    await kullaniciYukle(jeton.access_token);
    return true;
  } catch {
    oturumDusur();
    return false;
  }
}

/** Çıkış: refresh'i sunucuda iptal eder, ardından yerel oturumu temizler. */
export async function cikisYap(): Promise<void> {
  const refresh = refreshOku();
  try {
    if (refresh) await istek('POST', `${PREFIX}/kimlik/cikis`, { refresh_token: refresh });
  } catch {
    // Sunucu hatası olsa da yerel oturum yine de temizlenir.
  } finally {
    oturumDusur();
  }
}

export async function parolaDegistir(eskiParola: string, yeniParola: string): Promise<void> {
  await istek('POST', `${PREFIX}/kimlik/parola-degistir`, {
    eski_parola: eskiParola,
    yeni_parola: yeniParola,
  });
}
