/**
 * Refresh token kalıcılığı (localStorage). Access token bellektedir (bkz. store/authStore.ts);
 * refresh ise sayfa yenilemesinde sessiz girişi mümkün kılmak için saklanır.
 */

const REFRESH_ANAHTARI = 'fabrikaos.refresh';

export function refreshOku(): string | null {
  return localStorage.getItem(REFRESH_ANAHTARI);
}

export function refreshSakla(jeton: string): void {
  localStorage.setItem(REFRESH_ANAHTARI, jeton);
}

export function refreshTemizle(): void {
  localStorage.removeItem(REFRESH_ANAHTARI);
}
