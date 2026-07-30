/**
 * Kimlik (auth) servisi — giriş, sessiz başlatma (bootstrap), çıkış, parola değiştirme.
 *
 * Token akışı: ``/kimlik/token`` (form) → refresh localStorage'a, access belleğe; sonra
 * ``/kimlik/ben`` ile kullanıcı + izinler store'a. Sayfa yüklenince ``oturumBaslat`` saklı
 * refresh ile sessiz giriş dener.
 */

import { useAuthStore } from '@/store/authStore';
import type { Kullanici } from '@/store/authStore';

import { istek, istekJetonlu, oturumDusur, PREFIX } from './client';
import { refreshOku, refreshSakla } from './jeton';
import { tenantSakla } from './tenant';
import type { components } from './types.gen';

type Jeton = components['schemas']['TokenCevapDTO'];
/** Aktif oturum/cihaz satırı (güvenlik ekranı tablosu). */
export type OturumSatiri = components['schemas']['OturumCevapDTO'];

/**
 * Girişin üç olası sonucu (S23):
 * - ``tamam`` — oturum açıldı;
 * - ``2fa`` — ikinci adım gerekli (geçici token ile kod doğrulanacak);
 * - ``2fa-kurulum`` — tenant 2FA'yı zorunlu kılmış, kullanıcı henüz kurmamış.
 */
export type GirisSonucu =
  | { durum: 'tamam' }
  | { durum: '2fa'; geciciToken: string }
  | { durum: '2fa-kurulum'; geciciToken: string };

async function kullaniciYukle(access: string): Promise<void> {
  useAuthStore.getState().ayarlaAccess(access);
  const kullanici = await istek<Kullanici>('GET', `${PREFIX}/kimlik/ben`);
  useAuthStore.getState().ayarlaOturum(access, kullanici);
}

/** Token zarfını sonuca çevirir; tam çift geldiyse oturumu açar. */
async function jetonuIsle(jeton: Jeton): Promise<GirisSonucu> {
  if (jeton.iki_asama_gerekli) {
    return { durum: '2fa', geciciToken: jeton.gecici_token ?? '' };
  }
  if (jeton.iki_asama_kurulum_gerekli) {
    return { durum: '2fa-kurulum', geciciToken: jeton.gecici_token ?? '' };
  }
  refreshSakla(jeton.refresh_token ?? '');
  await kullaniciYukle(jeton.access_token ?? '');
  return { durum: 'tamam' };
}

/**
 * Giriş. ``firmaKodu`` verilirse (subdomain yokken fallback) tenant olarak saklanır.
 * 2FA açıksa oturum AÇILMAZ; çağıran ikinci adımı yürütür.
 */
export async function girisYap(
  firmaKodu: string | null,
  eposta: string,
  parola: string,
): Promise<GirisSonucu> {
  if (firmaKodu) tenantSakla(firmaKodu.trim().toLowerCase());

  const form = new URLSearchParams({ username: eposta, password: parola });
  const jeton = await istek<Jeton>('POST', `${PREFIX}/kimlik/token`, form, false);
  return jetonuIsle(jeton);
}

/** 2FA ikinci adımı: TOTP kodu veya kurtarma kodu → oturum. */
export async function ikiAsamaDogrula(geciciToken: string, kod: string): Promise<GirisSonucu> {
  const jeton = await istek<Jeton>(
    'POST',
    `${PREFIX}/kimlik/2fa-dogrula`,
    { gecici_token: geciciToken, kod },
    false,
  );
  return jetonuIsle(jeton);
}

type KurCevap = components['schemas']['IkiAsamaKurCevapDTO'];
type KurtarmaCevap = components['schemas']['IkiAsamaKurtarmaCevapDTO'];

/**
 * 2FA kurulumunu başlatır (sır + otpauth URI). ``geciciToken`` verilirse zorunlu-2FA
 * ilk girişindeki kurulum akışıdır (henüz tam oturum yok); verilmezse normal oturum.
 */
export async function ikiAsamaKur(geciciToken?: string): Promise<KurCevap> {
  const yol = `${PREFIX}/kimlik/2fa-kur`;
  return geciciToken
    ? istekJetonlu<KurCevap>('POST', yol, undefined, geciciToken)
    : istek<KurCevap>('POST', yol);
}

/** 2FA'yı etkinleştirir; kurtarma kodlarını YALNIZ burada bir kez döner. */
export async function ikiAsamaEtkinlestir(kod: string, geciciToken?: string): Promise<string[]> {
  const yol = `${PREFIX}/kimlik/2fa-etkinlestir`;
  const cevap = geciciToken
    ? await istekJetonlu<KurtarmaCevap>('POST', yol, { kod }, geciciToken)
    : await istek<KurtarmaCevap>('POST', yol, { kod });
  return cevap.kurtarma_kodlari;
}

/** 2FA'yı kapatır — parola VE geçerli kod (ya da kurtarma kodu) ister. */
export async function ikiAsamaKapat(parola: string, kod: string): Promise<void> {
  await istek('POST', `${PREFIX}/kimlik/2fa-kapat`, { parola, kod });
}

/** Aktif oturumlar (cihaz listesi). */
export async function oturumlariGetir(): Promise<OturumSatiri[]> {
  return istek<OturumSatiri[]>('GET', `${PREFIX}/kimlik/oturumlar`);
}

/** Oturumu uzaktan sonlandırır. */
export async function oturumSonlandir(id: number): Promise<void> {
  await istek('DELETE', `${PREFIX}/kimlik/oturumlar/${id}`);
}

// --- Kurumsal SSO (OIDC; S23) ---
type SsoDurum = components['schemas']['SsoDurumCevapDTO'];
type SsoBaslat = components['schemas']['SsoBaslatCevapDTO'];

/** Tenant'ta SSO açık mı (giriş ekranı düğmesi). Tenant çözülemezse sessizce ``false``. */
export async function ssoAcikMi(firmaKodu: string | null): Promise<boolean> {
  if (firmaKodu) tenantSakla(firmaKodu.trim().toLowerCase());
  try {
    const cevap = await istek<SsoDurum>('GET', `${PREFIX}/kimlik/sso/durum`, undefined, false);
    return cevap.aktif;
  } catch {
    return false;
  }
}

/** SSO akışını başlatır ve IdP yetkilendirme URL'ini döner (tarayıcı oraya gider). */
export async function ssoBaslat(firmaKodu: string | null): Promise<string> {
  if (firmaKodu) tenantSakla(firmaKodu.trim().toLowerCase());
  const cevap = await istek<SsoBaslat>('POST', `${PREFIX}/kimlik/sso/baslat`, undefined, false);
  return cevap.yetkilendirme_url;
}

/** IdP dönüşünü tamamlar (kod + state) → oturum (veya 2FA ikinci adımı). */
export async function ssoTamamla(kod: string, state: string): Promise<GirisSonucu> {
  const jeton = await istek<Jeton>('POST', `${PREFIX}/kimlik/sso/tamamla`, { kod, state }, false);
  return jetonuIsle(jeton);
}

async function _oturumBaslat(): Promise<boolean> {
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

let baslatiliyor: Promise<boolean> | null = null;

/**
 * Sayfa yükünde sessiz giriş: saklı refresh varsa yeni access alıp kullanıcıyı yükler.
 * Başarısızsa oturumu temizler. İlk açılışta (refresh yok) hiç istek atmaz.
 *
 * Eşzamanlı çağrılar tekilleştirilir: refresh **rotasyonlu** olduğundan iki paralel
 * ``yenile`` isteğinin ikincisi 401 alır ve taze oturumu düşürürdü (ör. StrictMode'un
 * çift effect'i her tam sayfa yenilemede çıkışa yol açıyordu).
 */
export function oturumBaslat(): Promise<boolean> {
  baslatiliyor ??= _oturumBaslat().finally(() => {
    baslatiliyor = null;
  });
  return baslatiliyor;
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
