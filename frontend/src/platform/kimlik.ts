/**
 * Platform kimlik servisi — giriş, sessiz başlatma (bootstrap), çıkış.
 * Tenant ``api/kimlik.ts``'inin control-plane aynası (rotasyon-dayanıklı dedupe dahil).
 */

import type { components } from '@/api/types.gen';

import {
  PLATFORM_PREFIX,
  platformIstek,
  platformOturumDusur,
  platformRefreshOku,
  platformRefreshSakla,
} from './api';
import { usePlatformAuthStore } from './store';
import type { PlatformYonetici } from './store';

type Jeton = components['schemas']['TokenCevapDTO'];

async function yoneticiYukle(access: string): Promise<void> {
  usePlatformAuthStore.getState().ayarlaAccess(access);
  const yonetici = await platformIstek<PlatformYonetici>('GET', `${PLATFORM_PREFIX}/kimlik/ben`);
  usePlatformAuthStore.getState().ayarlaOturum(access, yonetici);
}

export async function platformGirisYap(eposta: string, parola: string): Promise<void> {
  const form = new URLSearchParams({ username: eposta, password: parola });
  const jeton = await platformIstek<Jeton>('POST', `${PLATFORM_PREFIX}/kimlik/token`, form, false);
  platformRefreshSakla(jeton.refresh_token);
  await yoneticiYukle(jeton.access_token);
}

async function _oturumBaslat(): Promise<boolean> {
  const refresh = platformRefreshOku();
  if (!refresh) return false;
  try {
    const jeton = await platformIstek<Jeton>(
      'POST',
      `${PLATFORM_PREFIX}/kimlik/yenile`,
      { refresh_token: refresh },
      false,
    );
    platformRefreshSakla(jeton.refresh_token);
    await yoneticiYukle(jeton.access_token);
    return true;
  } catch {
    platformOturumDusur();
    return false;
  }
}

let baslatiliyor: Promise<boolean> | null = null;

/** Sessiz giriş — eşzamanlı çağrılar tekilleştirilir (rotasyonlu refresh yarışına karşı). */
export function platformOturumBaslat(): Promise<boolean> {
  baslatiliyor ??= _oturumBaslat().finally(() => {
    baslatiliyor = null;
  });
  return baslatiliyor;
}

export async function platformCikisYap(): Promise<void> {
  const refresh = platformRefreshOku();
  try {
    if (refresh) {
      await platformIstek('POST', `${PLATFORM_PREFIX}/kimlik/cikis`, { refresh_token: refresh });
    }
  } catch {
    // Sunucu hatası olsa da yerel oturum yine de temizlenir.
  } finally {
    platformOturumDusur();
  }
}
