/**
 * Merkezi API katmanı — tek noktadan tüm istekleri yönetir (tenant-rbac-conventions, istemci tarafı).
 *
 * Her isteğe ``X-Tenant`` (cozumleTenant) ve varsa ``Authorization: Bearer <access>`` enjekte eder.
 * **401** alındığında bir kez ``/kimlik/yenile`` (refresh rotasyonu) denenir, başarılıysa orijinal
 * istek yeni access ile tekrarlanır; refresh de düşerse oturum düşürülür. Eşzamanlı 401'ler için
 * yenileme tek-uçuşludur (single-flight), böylece tek bir refresh çağrısı yapılır.
 */

import { useAuthStore } from '@/store/authStore';

import { refreshOku, refreshSakla, refreshTemizle } from './jeton';
import { cozumleTenant, tenantTemizle } from './tenant';
import type { components } from './types.gen';

const API_TABANI = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const PREFIX = '/api/v1';

type Jeton = components['schemas']['TokenCevapDTO'];
type Zarf<T> = { success: boolean; message: string; data: T | null };

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
  } else if (govde !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(govde);
  }

  return fetch(`${API_TABANI}${yol}`, { method: yontem, headers, body });
}

async function zarfCoz<T>(cevap: Response): Promise<T> {
  let zarf: Zarf<T> | null = null;
  try {
    zarf = (await cevap.json()) as Zarf<T>;
  } catch {
    zarf = null;
  }
  if (!cevap.ok || !zarf || zarf.success === false) {
    const mesaj = zarf?.message ?? `İstek başarısız (${cevap.status})`;
    throw new ApiHata(cevap.status, mesaj);
  }
  return zarf.data as T;
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
      const jeton = await zarfCoz<Jeton>(cevap);
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
 * Tiplenmiş API isteği. ``yol`` ``/api/v1`` ile başlamalıdır. ``data`` zarfı çözülür.
 * 401 → refresh → tek tekrar; başarısızsa oturum düşürülür ve ``ApiHata`` fırlatılır.
 */
export async function istek<T>(
  yontem: Yontem,
  yol: string,
  govde?: unknown,
  kimlikli = true,
): Promise<T> {
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

  return zarfCoz<T>(cevap);
}

export { oturumDusur, PREFIX, tenantTemizle };
