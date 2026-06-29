import { beforeEach, describe, expect, it } from 'vitest';

import { cozumleTenant, subdomainSlug, tenantOku, tenantSakla, tenantTemizle } from './tenant';

describe('subdomainSlug', () => {
  it('*.localhost subdomain’ini çözer', () => {
    expect(subdomainSlug('alfa.localhost')).toBe('alfa');
  });

  it('gerçek alan adında 3+ etiketten subdomain çözer', () => {
    expect(subdomainSlug('alfa.fabrikaos.com')).toBe('alfa');
  });

  it('düz localhost’ta tenant yok', () => {
    expect(subdomainSlug('localhost')).toBeNull();
  });

  it('apex alan adında (2 etiket) tenant yok', () => {
    expect(subdomainSlug('fabrikaos.com')).toBeNull();
  });

  it('www/app gibi etiketleri yok sayar', () => {
    expect(subdomainSlug('www.fabrikaos.com')).toBeNull();
    expect(subdomainSlug('app.fabrikaos.com')).toBeNull();
  });

  it('IP adresinde tenant yok', () => {
    expect(subdomainSlug('127.0.0.1')).toBeNull();
  });

  it('büyük harfi küçültür', () => {
    expect(subdomainSlug('ALFA.localhost')).toBe('alfa');
  });
});

describe('cozumleTenant (subdomain → fallback)', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('subdomain varsa onu kullanır (saklıyı yok sayar)', () => {
    tenantSakla('beta');
    expect(cozumleTenant('alfa.localhost')).toBe('alfa');
  });

  it('subdomain yoksa saklı tenant’a (login fallback) düşer', () => {
    tenantSakla('beta');
    expect(cozumleTenant('localhost')).toBe('beta');
  });

  it('subdomain de saklı da yoksa null', () => {
    expect(cozumleTenant('localhost')).toBeNull();
  });

  it('tenantSakla/Oku/Temizle döngüsü', () => {
    expect(tenantOku()).toBeNull();
    tenantSakla('gamma');
    expect(tenantOku()).toBe('gamma');
    tenantTemizle();
    expect(tenantOku()).toBeNull();
  });
});
