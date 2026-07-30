/**
 * Tenant güvenlik ayarları ↔ form alanları dönüşümü (saf; S23 / ADR-0022).
 *
 * Bileşenden ayrı tutulur: hem test edilebilir hem de hızlı yenileme (fast refresh)
 * bileşen dosyasında yalnız bileşen kalsın diye. Backend sözleşmesi
 * ``public.tenant.guvenlik_ayarlari`` JSONB'sidir.
 */

/** Sunucudan gelen ham ayar ağacı (alanlar opsiyonel — kısmi yapılandırma normaldir). */
export type GuvenlikAyarlari = {
  parola?: {
    min_uzunluk?: number;
    buyuk_kucuk?: boolean;
    rakam?: boolean;
    ozel_karakter?: boolean;
  };
  iki_asama_zorunlu?: boolean;
  ip_izin_listesi?: string[];
  oidc?: {
    aktif?: boolean;
    issuer?: string;
    istemci_id?: string;
    istemci_sirri?: string;
    donus_url?: string;
    izinli_alan_adlari?: string[];
    jit_provizyon?: boolean;
    varsayilan_roller?: string[];
    claim_eslemesi?: { eposta?: string; konu?: string; ad?: string; gruplar?: string };
    debug_claim_log?: boolean;
  };
};

export type GuvenlikAlanlari = {
  parola_acik: boolean;
  min_uzunluk: number;
  buyuk_kucuk: boolean;
  rakam: boolean;
  ozel_karakter: boolean;
  iki_asama_zorunlu: boolean;
  ip_izin_listesi: string[];
  sso_aktif: boolean;
  issuer: string;
  istemci_id: string;
  istemci_sirri: string;
  donus_url: string;
  izinli_alan_adlari: string[];
  jit_provizyon: boolean;
  varsayilan_roller: string[];
  claim_eposta: string;
  claim_gruplar: string;
  debug_claim_log: boolean;
};

/** Ham ayarları form başlangıç değerlerine çevirir (eksik alanlar makul varsayılana düşer). */
export function baslangicDegerleri(ayarlar: GuvenlikAyarlari | null | undefined): GuvenlikAlanlari {
  const a = ayarlar ?? {};
  const parola = a.parola ?? {};
  const oidc = a.oidc ?? {};
  const esleme = oidc.claim_eslemesi ?? {};
  return {
    parola_acik: a.parola != null,
    min_uzunluk: parola.min_uzunluk ?? 12,
    buyuk_kucuk: parola.buyuk_kucuk ?? true,
    rakam: parola.rakam ?? true,
    ozel_karakter: parola.ozel_karakter ?? false,
    iki_asama_zorunlu: a.iki_asama_zorunlu ?? false,
    ip_izin_listesi: a.ip_izin_listesi ?? [],
    sso_aktif: oidc.aktif ?? false,
    issuer: oidc.issuer ?? '',
    istemci_id: oidc.istemci_id ?? '',
    istemci_sirri: oidc.istemci_sirri ?? '',
    donus_url: oidc.donus_url ?? '',
    izinli_alan_adlari: oidc.izinli_alan_adlari ?? [],
    jit_provizyon: oidc.jit_provizyon ?? true,
    varsayilan_roller: oidc.varsayilan_roller ?? [],
    claim_eposta: esleme.eposta ?? 'email',
    claim_gruplar: esleme.gruplar ?? 'groups',
    debug_claim_log: oidc.debug_claim_log ?? false,
  };
}

/**
 * Form alanlarını PUT gövdesine çevirir. Kapalı bölümler gövdeye hiç YAZILMAZ —
 * böylece "politika yok / SSO kapalı" durumu backend'de anahtar yokluğuyla ifade edilir
 * (ayar_coz ve parola_kurali_ihlalleri bunu bekliyor).
 */
export function govdeKur(d: GuvenlikAlanlari): GuvenlikAyarlari {
  const govde: GuvenlikAyarlari = {};
  if (d.parola_acik) {
    govde.parola = {
      min_uzunluk: d.min_uzunluk,
      buyuk_kucuk: d.buyuk_kucuk,
      rakam: d.rakam,
      ozel_karakter: d.ozel_karakter,
    };
  }
  if (d.iki_asama_zorunlu) govde.iki_asama_zorunlu = true;
  if (d.ip_izin_listesi.length > 0) govde.ip_izin_listesi = d.ip_izin_listesi;
  if (d.sso_aktif) {
    govde.oidc = {
      aktif: true,
      issuer: d.issuer.trim(),
      istemci_id: d.istemci_id.trim(),
      istemci_sirri: d.istemci_sirri,
      donus_url: d.donus_url.trim(),
      izinli_alan_adlari: d.izinli_alan_adlari,
      jit_provizyon: d.jit_provizyon,
      varsayilan_roller: d.varsayilan_roller,
      claim_eslemesi: { eposta: d.claim_eposta, gruplar: d.claim_gruplar },
      debug_claim_log: d.debug_claim_log,
    };
  }
  return govde;
}
