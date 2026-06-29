/**
 * Tenant çözümleme: önce subdomain (prod + *.localhost dev), sonra login fallback (saklı slug).
 *
 * Frontend ile API ayrı origin olduğundan tenant client tarafında çözülür ve her isteğe
 * ``X-Tenant`` başlığı olarak eklenir (bkz. api/client.ts).
 */

const TENANT_ANAHTARI = 'fabrikaos.tenant';

// Tenant olmayan, yok sayılacak alt etiketler.
const YOK_SAYILAN = new Set(['www', 'app']);

// IPv4 adresi (ör. 127.0.0.1) — ilk okteti tenant sanılmamalı.
const IPV4 = /^\d{1,3}(\.\d{1,3}){3}$/;

/**
 * Host adından tenant slug'ını yapısal olarak çıkarır.
 * - ``alfa.localhost`` → ``alfa`` (dev)
 * - ``alfa.fabrikaos.com`` → ``alfa`` (3+ etiket)
 * - ``localhost`` / ``fabrikaos.com`` (apex) / IP → ``null``
 */
export function subdomainSlug(hostname: string): string | null {
  const h = hostname.toLowerCase();
  if (IPV4.test(h)) return null;
  const parcalar = h.split('.');
  const ilk = parcalar[0];
  if (!ilk) return null;

  const yapisalSubdomain =
    (h.endsWith('.localhost') && parcalar.length >= 2) || parcalar.length >= 3;
  if (!yapisalSubdomain) return null;
  if (YOK_SAYILAN.has(ilk)) return null;
  return ilk;
}

export function tenantOku(): string | null {
  return localStorage.getItem(TENANT_ANAHTARI);
}

export function tenantSakla(slug: string): void {
  localStorage.setItem(TENANT_ANAHTARI, slug);
}

export function tenantTemizle(): void {
  localStorage.removeItem(TENANT_ANAHTARI);
}

/**
 * Aktif tenant slug'ı: subdomain öncelikli, yoksa saklı (login'de girilen firma kodu).
 */
export function cozumleTenant(hostname: string = window.location.hostname): string | null {
  return subdomainSlug(hostname) ?? tenantOku();
}
