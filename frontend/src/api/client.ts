/**
 * Merkezi API katmanı — tek noktadan tüm istekleri yönetir (tenant-rbac-conventions, istemci tarafı).
 *
 * Her isteğe ``X-Tenant`` (cozumleTenant) ve varsa ``Authorization: Bearer <access>`` enjekte eder.
 * **401** alındığında bir kez ``/kimlik/yenile`` (refresh rotasyonu) denenir, başarılıysa orijinal
 * istek yeni access ile tekrarlanır; refresh de düşerse oturum düşürülür. Eşzamanlı 401'ler için
 * yenileme tek-uçuşludur (single-flight), böylece tek bir refresh çağrısı yapılır.
 *
 * İki çözücü vardır: ``istek`` yalnız ``data``yı döndürür; ``istekSayfali`` ``data`` + ``meta``
 * (sunucu-taraflı sayfalama: sayfa/adet/toplam) döndürür.
 */

import { useAuthStore } from '@/store/authStore';

import { refreshOku, refreshSakla, refreshTemizle } from './jeton';
import { cozumleTenant, tenantTemizle } from './tenant';
import type { components } from './types.gen';

const API_TABANI = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const PREFIX = '/api/v1';

type Jeton = components['schemas']['TokenCevapDTO'];
export type SayfaMeta = { sayfa: number; adet: number; toplam: number };
type Zarf<T> = {
  success: boolean;
  message: string;
  data: T | null;
  meta?: SayfaMeta | null;
  hata_kodu?: string;
};

export type Yontem = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

/** Standart hata zarfından türeyen API hatası. */
export class ApiHata extends Error {
  constructor(
    readonly durum: number,
    mesaj: string,
    readonly hataKodu?: string,
  ) {
    super(mesaj);
    this.name = 'ApiHata';
  }
}

let yenilemeIslemi: Promise<string> | null = null;

function oturumDusur(): void {
  useAuthStore.getState().temizle();
  refreshTemizle();
}

async function hamIstek(
  yontem: Yontem,
  yol: string,
  govde?: unknown,
  kimlikli = true,
): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' };

  const tenant = cozumleTenant();
  if (tenant) headers['X-Tenant'] = tenant;

  if (kimlikli) {
    const access = useAuthStore.getState().access;
    if (access) headers['Authorization'] = `Bearer ${access}`;
  }

  let body: BodyInit | undefined;
  if (govde instanceof URLSearchParams) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = govde;
  } else if (govde instanceof FormData) {
    // Content-Type ayarlanmaz: tarayıcı multipart sınırını (boundary) kendi ekler.
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

/** Tek-uçuşlu (single-flight) access yenileme; yeni access döner, başarısızsa null. */
async function accessYenile(): Promise<string | null> {
  const refresh = refreshOku();
  if (!refresh) return null;

  if (!yenilemeIslemi) {
    yenilemeIslemi = (async () => {
      const cevap = await hamIstek(
        'POST',
        `${PREFIX}/kimlik/yenile`,
        { refresh_token: refresh },
        false,
      );
      const zarf = await zarfOku<Jeton>(cevap);
      const jeton = zarf.data as Jeton;
      useAuthStore.getState().ayarlaAccess(jeton.access_token);
      refreshSakla(jeton.refresh_token);
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

/**
 * İsteği gönderir; 401 + kimlikli ise bir kez refresh + tekrar dener. Refresh düşerse
 * oturumu düşürür ve ``ApiHata`` fırlatır. Zarf çözümü çağırana bırakılır.
 */
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
      oturumDusur();
      throw new ApiHata(401, 'Oturum sona erdi, lütfen tekrar giriş yapın');
    }
  }

  return cevap;
}

/**
 * Tiplenmiş API isteği. ``yol`` ``/api/v1`` ile başlamalıdır. Yanıt zarfının ``data``sı çözülür.
 */
export async function istek<T>(
  yontem: Yontem,
  yol: string,
  govde?: unknown,
  kimlikli = true,
): Promise<T> {
  const cevap = await istekCevap(yontem, yol, govde, kimlikli);
  const zarf = await zarfOku<T>(cevap);
  return zarf.data as T;
}

/** Sayfalı liste isteği — ``data`` (liste) + ``meta`` (sayfa/adet/toplam) birlikte döner. */
export async function istekSayfali<T>(
  yol: string,
  kimlikli = true,
): Promise<{ veri: T[]; meta: SayfaMeta }> {
  const cevap = await istekCevap('GET', yol, undefined, kimlikli);
  const zarf = await zarfOku<T[]>(cevap);
  return {
    veri: zarf.data ?? [],
    meta: zarf.meta ?? { sayfa: 1, adet: 0, toplam: 0 },
  };
}

/**
 * İkili içerik indirir (DYS belge sürümü). Yanıt standart zarf değil ham dosyadır; ``Blob``
 * ve (varsa) ``Content-Disposition``'dan çözülen dosya adı döner.
 */
export async function istekIndir(yol: string): Promise<{ blob: Blob; dosyaAdi: string | null }> {
  const cevap = await istekCevap('GET', yol);
  if (!cevap.ok) {
    throw new ApiHata(cevap.status, `İndirme başarısız (${cevap.status})`);
  }
  const disp = cevap.headers.get('Content-Disposition') ?? '';
  const eslesme = /filename\*=UTF-8''([^;]+)/i.exec(disp);
  const dosyaAdi = eslesme?.[1] ? decodeURIComponent(eslesme[1]) : null;
  return { blob: await cevap.blob(), dosyaAdi };
}

export { oturumDusur, PREFIX, tenantTemizle };
