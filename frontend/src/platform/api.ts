/**
 * Platform API istemcisi — tenant ``api/client.ts``'inin control-plane aynası.
 *
 * Farklar: **X-Tenant başlığı YOK** (control-plane tenant'tan bağımsız), token
 * deposu ayrı (``fabrikaos.platform.refresh``), 401'de yenileme ``/platform/
 * kimlik/yenile``'ye gider (single-flight). Tenant istemcisine dokunulmaz —
 * iki düzlem aynı sekmede yan yana yaşayabilir.
 */

import { ApiHata } from '@/api/client';
import type { components } from '@/api/types.gen';

import { usePlatformAuthStore } from './store';

const API_TABANI = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const PLATFORM_PREFIX = '/api/v1/platform';

const REFRESH_ANAHTARI = 'fabrikaos.platform.refresh';

type Jeton = components['schemas']['TokenCevapDTO'];
export type SayfaMeta = { sayfa: number; adet: number; toplam: number };
type Zarf<T> = {
  success: boolean;
  message: string;
  data: T | null;
  meta?: SayfaMeta | null;
  hata_kodu?: string;
};

type Yontem = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

export function platformRefreshOku(): string | null {
  return localStorage.getItem(REFRESH_ANAHTARI);
}

export function platformRefreshSakla(jeton: string): void {
  localStorage.setItem(REFRESH_ANAHTARI, jeton);
}

export function platformRefreshTemizle(): void {
  localStorage.removeItem(REFRESH_ANAHTARI);
}

export function platformOturumDusur(): void {
  usePlatformAuthStore.getState().temizle();
  platformRefreshTemizle();
}

let yenilemeIslemi: Promise<string> | null = null;

async function hamIstek(
  yontem: Yontem,
  yol: string,
  govde?: unknown,
  kimlikli = true,
): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' };

  if (kimlikli) {
    const access = usePlatformAuthStore.getState().access;
    if (access) headers['Authorization'] = `Bearer ${access}`;
  }

  let body: BodyInit | undefined;
  if (govde instanceof URLSearchParams) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = govde;
  } else if (govde !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(govde);
  }

  return fetch(`${API_TABANI}${yol}`, { method: yontem, headers, body });
}

async function zarfOku<T>(cevap: Response): Promise<Zarf<T>> {
  let zarf: Zarf<T> | null = null;
  try {
    zarf = (await cevap.json()) as Zarf<T>;
  } catch {
    zarf = null;
  }
  if (!cevap.ok || !zarf || zarf.success === false) {
    const mesaj = zarf?.message ?? `İstek başarısız (${cevap.status})`;
    throw new ApiHata(cevap.status, mesaj, zarf?.hata_kodu);
  }
  return zarf;
}

/** Tek-uçuşlu (single-flight) platform access yenileme; başarısızsa null. */
async function accessYenile(): Promise<string | null> {
  const refresh = platformRefreshOku();
  if (!refresh) return null;

  if (!yenilemeIslemi) {
    yenilemeIslemi = (async () => {
      const cevap = await hamIstek(
        'POST',
        `${PLATFORM_PREFIX}/kimlik/yenile`,
        { refresh_token: refresh },
        false,
      );
      const zarf = await zarfOku<Jeton>(cevap);
      const jeton = zarf.data as Jeton;
      usePlatformAuthStore.getState().ayarlaAccess(jeton.access_token);
      platformRefreshSakla(jeton.refresh_token);
      return jeton.access_token;
    })().finally(() => {
      yenilemeIslemi = null;
    });
  }

  try {
    return await yenilemeIslemi;
  } catch {
    return null;
  }
}

async function istekCevap(
  yontem: Yontem,
  yol: string,
  govde?: unknown,
  kimlikli = true,
): Promise<Response> {
  let cevap = await hamIstek(yontem, yol, govde, kimlikli);

  if (cevap.status === 401 && kimlikli) {
    const yeniAccess = await accessYenile();
    if (yeniAccess) {
      cevap = await hamIstek(yontem, yol, govde, kimlikli);
    } else {
      platformOturumDusur();
      throw new ApiHata(401, 'Oturum sona erdi, lütfen tekrar giriş yapın');
    }
  }

  return cevap;
}

/** Tiplenmiş platform isteği; yanıt zarfının ``data``sı çözülür. */
export async function platformIstek<T>(
  yontem: Yontem,
  yol: string,
  govde?: unknown,
  kimlikli = true,
): Promise<T> {
  const cevap = await istekCevap(yontem, yol, govde, kimlikli);
  const zarf = await zarfOku<T>(cevap);
  return zarf.data as T;
}

/** Sayfalı platform listesi — ``data`` + ``meta`` birlikte döner. */
export async function platformIstekSayfali<T>(
  yol: string,
): Promise<{ veri: T[]; meta: SayfaMeta }> {
  const cevap = await istekCevap('GET', yol);
  const zarf = await zarfOku<T[]>(cevap);
  return {
    veri: zarf.data ?? [],
    meta: zarf.meta ?? { sayfa: 1, adet: 0, toplam: 0 },
  };
}

/** İkili içerik indirir (KVKK ihraç ZIP'i). */
export async function platformIstekIndir(
  yol: string,
): Promise<{ blob: Blob; dosyaAdi: string | null }> {
  const cevap = await istekCevap('GET', yol);
  if (!cevap.ok) {
    throw new ApiHata(cevap.status, `İndirme başarısız (${cevap.status})`);
  }
  const disp = cevap.headers.get('Content-Disposition') ?? '';
  const eslesme = /filename\*=UTF-8''([^;]+)/i.exec(disp);
  const dosyaAdi = eslesme?.[1] ? decodeURIComponent(eslesme[1]) : null;
  return { blob: await cevap.blob(), dosyaAdi };
}
