# Pilot fabrika devreye alma — kontrol listesi (S21)

Kararlar: [ADR-0042](../adr/0042-tohumlama-ice-aktarma.md). Bu liste bir pilot müşteriyle
yürütülür; durum: **müşteri bekleniyor** (yazılım tarafı hazır).

## 0. Ön koşullar (bir kez)
- [ ] Prod/staging yığını ayakta (`docker-compose.prod.yml`, `docs/operasyon/dr.md`), gözlem yığını
      açık (`--profile gozlem`), yedek servisleri çalışıyor, ilk tatbikat kaydı var.
- [ ] Sözleşme + KVKK veri işleme sözleşmesi imzalı (FabrikaOS veri işleyen, müşteri sorumlu).

## 1. Tenant (gün 1)
```bash
KURULUM_ADMIN_PAROLA='<geçici-güçlü-parola>' python backend/scripts/kurulum.py \
  --tenant <slug> --ad "<Fabrika A.Ş.>" --admin-eposta <bt-sorumlusu@musteri> --plan profesyonel
```
- [ ] Yönetici ilk girişte parolasını değiştirir, 2FA'yı açar (Güvenlik sayfası).
- [ ] Kullanıcılar ve roller (Kullanıcılar sayfası): üretim şefi, depo, satınalma onaylayan, İK.
- [ ] Gerekirse SSO (`docs/uyum/sso-kurulum.md`).

## 2. Ana veri (gün 1–2) — Yönetim › Veri içe aktarma
Sırayla, her biri önce önizlenir:
1. [ ] Firmalar (tedarikçi + müşteri; vergi no'lu)
2. [ ] Makineler (kod, ad, OEE hedefi, konum)
3. [ ] Malzemeler (kod, birim, kritik stok, tedarikçi vergi no)
4. [ ] Personel (sicil no; T.C. kimlik no isteğe bağlı, doğrulanır)
5. [ ] Depo/lokasyon tanımları (Depolar sayfası) → Açılış stoğu (malzeme kodu, miktar, lokasyon, lot)

Kontrol: Malzemeler listesindeki stok toplamı müşterinin son sayım tablosuyla tutuyor mu?

## 3. Saha verisi (gün 2–5)
- [ ] Saha cihazı (edge) her hat için tanımlı, MQTT ile ölçüm geliyor (Saha cihazları sayfası, son
      görülme < 5 dk). Edge yoksa: CSV ölçüm yükleme (`/saha/olcumler/csv`) geçiş yolu.
- [ ] Vardiya tanımları ve duruş nedenleri.
- [ ] İlk OEE değerleri müşterinin kendi hesabıyla karşılaştırıldı (aynı vardiya, aynı makine).

## 4. İlk iki hafta — izlenecekler
| Ne | Nerede | Eşik |
|---|---|---|
| Hata bütçesi | Grafana "FabrikaOS · SLI / SLO" | yanma alarmı yok |
| Ölçüm akışı | Saha cihazları | hat başına kesinti < 15 dk |
| Kullanım | Denetim kayıtları | her rol en az günde bir işlem |
| Destek talepleri | (müşteri kanalı) | haftalık gözden geçirme |

## 5. Pilot çıkışı → UAT (S22)
- [ ] Kabul senaryoları müşteriyle birlikte koşuldu (S22 UAT listesi).
- [ ] Geri bildirimler yol haritasına işlendi.
