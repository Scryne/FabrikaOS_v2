import { describe, expect, it } from 'vitest';

import { baslangicDegerleri, govdeKur, type GuvenlikAyarlari } from './guvenlikAyarBicim';

describe('guvenlikAyarBicim', () => {
  it('boş ayarlarda makul varsayılanlar üretir', () => {
    const d = baslangicDegerleri(null);
    expect(d.parola_acik).toBe(false);
    expect(d.sso_aktif).toBe(false);
    expect(d.min_uzunluk).toBe(12);
    expect(d.jit_provizyon).toBe(true); // SSO açılırsa JIT varsayılan olarak açık
    expect(d.claim_eposta).toBe('email');
  });

  it('kayıtlı ayarları forma yükler', () => {
    const ayarlar: GuvenlikAyarlari = {
      parola: { min_uzunluk: 16, buyuk_kucuk: true, rakam: false, ozel_karakter: true },
      iki_asama_zorunlu: true,
      ip_izin_listesi: ['10.0.0.0/8'],
      oidc: {
        aktif: true,
        issuer: 'https://idp.test',
        istemci_id: 'fos',
        istemci_sirri: '••••••••',
        donus_url: 'https://app.test/sso/donus',
        claim_eslemesi: { eposta: 'preferred_username', gruplar: 'realm_access.roles' },
      },
    };
    const d = baslangicDegerleri(ayarlar);
    expect(d.parola_acik).toBe(true);
    expect(d.min_uzunluk).toBe(16);
    expect(d.rakam).toBe(false);
    expect(d.iki_asama_zorunlu).toBe(true);
    expect(d.ip_izin_listesi).toEqual(['10.0.0.0/8']);
    expect(d.sso_aktif).toBe(true);
    expect(d.claim_eposta).toBe('preferred_username');
    expect(d.claim_gruplar).toBe('realm_access.roles');
  });

  it('kapalı bölümleri gövdeye hiç yazmaz (anahtar yokluğu = kural yok)', () => {
    const govde = govdeKur(baslangicDegerleri(null));
    expect(govde.parola).toBeUndefined();
    expect(govde.oidc).toBeUndefined();
    expect(govde.iki_asama_zorunlu).toBeUndefined();
    expect(govde.ip_izin_listesi).toBeUndefined();
  });

  it('açık bölümleri backend sözleşmesine uygun yazar', () => {
    const alanlar = {
      ...baslangicDegerleri(null),
      parola_acik: true,
      min_uzunluk: 14,
      iki_asama_zorunlu: true,
      ip_izin_listesi: ['192.168.1.0/24'],
      sso_aktif: true,
      issuer: '  https://idp.test  ',
      istemci_id: ' fos ',
      istemci_sirri: 'sir',
      donus_url: ' https://app.test/sso/donus ',
    };
    const govde = govdeKur(alanlar);
    expect(govde.parola?.min_uzunluk).toBe(14);
    expect(govde.iki_asama_zorunlu).toBe(true);
    expect(govde.ip_izin_listesi).toEqual(['192.168.1.0/24']);
    // Boşluklar kırpılır: issuer'daki fazladan boşluk discovery URL'ini bozardı.
    expect(govde.oidc?.issuer).toBe('https://idp.test');
    expect(govde.oidc?.istemci_id).toBe('fos');
    expect(govde.oidc?.donus_url).toBe('https://app.test/sso/donus');
  });

  it('maskeli sır gövdede aynen taşınır (sunucu mevcut sırrı korur)', () => {
    const alanlar = { ...baslangicDegerleri(null), sso_aktif: true, istemci_sirri: '••••••••' };
    expect(govdeKur(alanlar).oidc?.istemci_sirri).toBe('••••••••');
  });
});
