# FabrikaOS Saha — Mobil Uygulama Master Planı (v1)

> **Sürüm 1 · 2026-07-08.** Bu belge, web platformunun **tüm fazları (0–6) tamamlandıktan
> sonra** uygulanacak mobil uygulamanın master planıdır — yol haritasında **FAZ 7** olarak
> işaretlidir. Fabrika çalışanlarının kendi telefonlarına (veya saha tabletlerine)
> indireceği uygulamanın adı: **"FabrikaOS Saha"**. Görsel dil `DESIGN.md`'den, ekran
> desen sözlüğü `uiplani.md`'den türetilir; backend kuralları değişmez
> (`tenant-rbac-conventions` + `turkce-identifier-standardi` mobilde de bağlayıcıdır).

---

## 1. Vizyon & konumlandırma

**FabrikaOS Saha, web uygulamasının küçültülmüş kopyası DEĞİLDİR.** Web = masabaşı
"kontrol odası" (analiz, yönetim, konfigürasyon). Mobil = **cepte saha terminali**:
çalışanın *o an, o noktada, eldivenle* yapması gereken işi 3 dokunuşta bitirten,
bağlantı yokken bile çalışan görev-odaklı bir araç.

| | Web (kontrol odası) | Mobil (saha terminali) |
|---|---|---|
| Kullanım anı | Masada, uzun oturum | Hat başında, 10–60 saniyelik etkileşim |
| İçerik | Tüm modüller, analiz, konfigürasyon | Rol paketi: yalnız *benim işim* |
| Girdi | Klavye, filtre, form | Kamera (QR/foto), sayı pedi, tek dokunuş |
| Bağlantı | Sürekli | Kesintili — **offline-first zorunlu** |
| Bildirim | Uygulama içi zil | **Push** — iş çalışana gelir |

**Değer önerisi (tek cümle):** *"İş emrini panoda arama; makinenin QR'ını okut, işini
bitir, kaydı bağlantı gelince biz taşırız."*

---

## 2. Ürün ilkeleri (tasarım anayasası)

1. **3 dokunuş kuralı:** her çekirdek görev (üretim girişi, durum geçişi, ramak kala
   bildirimi) ana ekrandan en fazla 3 dokunuşta tamamlanır.
2. **Offline-first, sonra senkron:** her yazma önce cihazdaki kuyruğa; bağlantı gelince
   `Idempotency-Key` ile tek sefer işlenir (edge ajanının store-and-forward felsefesi —
   proje bu deseni zaten kanıtladı).
3. **Eldiven-dostu:** dokunma hedefleri ≥ 48dp; kritik aksiyonlar başparmak bölgesinde;
   kaydırmalı hassas kontroller yok (sayı pedi > slider).
4. **Rolün ne ise ekranın o:** operatör CRM görmez. Ana ekran ("Bugün") rol paketine göre
   derlenir; menü RBAC + entitlement (F4·S16) süzgeçli — web ile aynı izin sözlüğü.
5. **Sunucu otoritedir:** durum makineleri, OEE, bakiye — hesap hep sunucuda. Mobil
   çakışmada 409'u zarifçe gösterir, asla kendi kararını dayatmaz.
6. **Tek doğruluk kaynağı API:** mobil, web'in kullandığı **aynı** REST + WS uçlarını
   kullanır; mobile özel uç ancak gerçekten mobile özgü ihtiyaçta açılır (bkz. §8).

---

## 3. Personalar & rol paketleri

Her persona bir "paket"tir: Bugün ekranı bileşimi + görev listesi + Tara davranışı + push abonelikleri.

| Persona | Bugün ekranı | Çekirdek görevler | Tipik push |
|---|---|---|---|
| **Operatör** | Vardiyam, makinem (canlı durum + OEE), açık iş emirlerim, hızlı üretim girişi | Üretim/fire girişi · iş emri durum geçişi + yorum · duruş kaydı (F6·S24) | "Sana iş emri atandı" |
| **Bakım teknisyeni** | Bugünkü bakım görevleri, açık arızalar, makine geçmişi kısayolu | Bakım görevini kapat · arıza bildir (foto+not) · MTBF kartına bakış | "Yeni arıza kaydı" / "Bakım vadesi bugün" |
| **Depo görevlisi** | Bekleyen sayım oturumu, kritik stok, son hareketler | Barkodla stok sorgu · hızlı giriş/çıkış/transfer · mobil sayım (F6·S25) | "Kritik stok eşiği" |
| **Kalite kontrolcü** | Planlı kontroller, açık CAPA aksiyonlarım | Kontrol sonucu gir (geçti/kaldı) · uygunsuzluk aç (foto) · SPC ihlal görüntüle (F6·S26) | "SPC ihlali" / "CAPA aksiyonu sana atandı" |
| **İSG uzmanı** | "X gündür kazasız" sayacı, son ramak kalalar, açık riskler | Kaza/ramak kala kaydı · risk gözlemi · tatbikat yoklaması (F6·S26) | "Ramak kala bildirildi" |
| **Çalışan (self-servis)** — *herkese dahil* | Duyurular, izin bakiyem, sertifikalarım/zimmetlerim | İzin talebi · duyuru oku · tek-tuş ramak kala (**herkes** İSG gözüdür) | "İzin talebin onaylandı" / kritik duyuru |
| **Yönetici / süpervizör** | Mini OEE panosu, Onaylarım sayacı, canlı uyarılar | Onay/ret (satınalma·izin·sayım) · makine canlı izleme · kazasız gün | "Onay bekliyor" / "Anomali tespit" |

> Paketler roller üzerinden otomatik derlenir (`gorunurMenu` mantığının mobil karşılığı);
> kişi birden çok pakete sahipse Bugün ekranı bölümleri birleşir (öncelik sırası sabit).

---

## 4. Bilgi mimarisi & gezinme

**Navigasyon modeli:** 5'li alt sekme + merkez aksiyon.

```
┌────────────────────────────────────┐
│              (içerik)              │
├────────┬────────┬────┬───────┬────┤
│ Bugün  │Görevler│ ⊕  │Bildirim│Profil│
└────────┴────────┴─┬──┴───────┴────┘
                    └─ Tara (QR/NFC/barkod — merkez FAB)
```

- **Bugün:** rol-duyarlı ana ekran (persona bileşimi, §3) + son senkron çipi.
- **Görevlerim:** tek birleşik liste — iş emirlerim + bakım görevlerim + CAPA
  aksiyonlarım + planlı kontrollerim; durum pimli, kartlı; segment süzgeci.
- **Tara (merkez):** kamera açılır → QR/barkod türü otomatik ayırt edilir:
  makine QR → makine kartı · malzeme barkodu → stok kartı · personel rozeti →
  vardiya cihazı kullanıcı geçişi (§5.3). NFC etiketi aynı yönlendirme.
- **Bildirimler:** push geçmişi + okundu; tercihe derin bağlantı (F6·S27 altyapısı).
- **Profil:** kullanıcı/rol/tenant kartı, izin bakiyem, sertifikalarım, zimmetlerim,
  dil, biyometrik kilit, çevrimdışı kuyruk durumu, çıkış.

**Ekran haritası (evre etiketli):**

| Ekran | Persona | İzin | Offline | Evre |
|---|---|---|---|---|
| Giriş (tenant kodu + e-posta/parola + 2FA) | herkes | — | son oturum önbelleği | M0 |
| Bugün | herkes | rol-duyarlı | önbellek + bayat rozeti | M0→ |
| Görevlerim | operatör/bakım/kalite | ilgili `:oku` | önbellek | M1 |
| İş emri detay + durum geçişi + yorum | operatör | `isemri:*` | kuyruklu yazma | M1 |
| Hızlı üretim girişi (sayı pedi) | operatör | `uretim:yaz` | kuyruklu yazma | M1 |
| Makine kartı (Tara hedefi) | operatör/bakım | `uretim:oku` | önbellek | M1 |
| Duyurular | herkes | oturum | önbellek | M1 |
| Bakım görevi + tamamlama | bakım | `bakim:*` | kuyruklu yazma | M2 |
| Arıza bildir (foto+not) | bakım/operatör | `uretim:yaz` | kuyruklu + ek eşlik | M2 |
| Stok kartı + hızlı hareket | depo | `stok:*` | kuyruklu yazma | M2 |
| Mobil sayım modu | depo | `stok:*` (+`stok:duzeltme` onayı sunucuda) | **tam offline oturum** | M2 |
| Kalite kontrol girişi | kalite | `kalite:yaz` | kuyruklu yazma | M3 |
| Uygunsuzluk aç (foto) | kalite/operatör | `kalite:yaz` | kuyruklu + ek | M3 |
| **Tek-tuş Ramak Kala** | **herkes** | `isg:yaz` (dar kapsam) | kuyruklu yazma | M3 |
| İzin talebi + bakiyem | herkes | `ik` self-servis | kuyruklu yazma | M3 |
| Bildirim merkezi + tercihler | herkes | oturum | önbellek | M3 |
| Mini pano (OEE/kazasız gün/uyarılar) | yönetici | `analitik:oku` | önbellek + bayat rozeti | M4 |
| Onaylarım (satınalma·izin·sayım) | onaylayan roller | görev-ayrımı izinleri | **yalnız çevrimiçi** (onay offline verilmez) | M4 |
| Vardiya cihazı modu | paylaşımlı tablet | özel akış (§5.3) | kısıtlı | M4 |
| Ana ekran widget'ları (OEE · kazasız gün) | yönetici/İSG | ilgili `:oku` | son değer | M4 |

---

## 5. İmza özellikler (ürünü eşsiz yapan katman)

### 5.1 "Makineye dokun" — QR/NFC bağlam geçişi
Her makinenin gövdesinde QR (ve istenirse NFC) etiketi (F6·S25 etiket üretimi yeniden
kullanılır). Okutunca **makine kartı** açılır: canlı durum LED'i + pencere OEE bar'ı +
son üretim + duruma göre aksiyonlar (üretim gir · arıza bildir · duruş kaydet · iş
emirlerini gör). *Fiziksel dünya ile dijital ikizin kesişme noktası* — ikizdeki LED dili
cepte aynen konuşur.

### 5.2 Tek-tuş "Ramak Kala"
İSG kültürünün altın kuralı: bildirim ne kadar kolaysa o kadar çok gelir. Bugün
ekranında kalıcı buton → foto (opsiyonel) + yer (makine QR ile otomatik) + tek cümle →
gönder. 3 dokunuş, 15 saniye. `isg.kaza` outbox zinciri aynen çalışır; İSG uzmanına push
düşer. **"X gündür kazasız" sayacı** hem Bugün'de hem widget'ta — sahiplenme yaratır.

### 5.3 Vardiya cihazı modu (paylaşımlı tablet)
Herkese telefon dağıtılamayan hatlarda: hat başındaki tablet **vardiya moduna** alınır
(cihaz tenant'a kayıtlı, kiosk-benzeri kilitli). Çalışan **rozetindeki QR'ı okutup + PIN**
ile 2 saniyede oturum değiştirir; her işlem *gerçek kişinin* kimliğiyle audit'e yazılır
(paylaşımlı hesap anti-deseni çözülür). Vardiya sonunda otomatik kilit.

### 5.4 Cep store-and-forward
Edge ajanının kanıtlanmış deseni kullanıcı katmanına taşınır: her yazma önce şifreli
yerel kuyruğa (SQLite) → bağlantıda sıralı, `Idempotency-Key`'li teslim → sunucu 409
derse kayıt "çakıştı" kutusuna düşer, kullanıcı kartı açıp tek dokunuşla günceller.
Kuyruk durumu Profil'de şeffaf: bekleyen N kayıt · son senkron · elle "şimdi gönder".

### 5.5 Cep nabzı (widget + canlı etkinlik)
Ana ekran widget'ları: **OEE** (yönetici) ve **kazasız gün** (herkes). iOS Live
Activity / Android bildirim güncellemesiyle kritik durum (anomali, kritik stok) kilit
ekranında yaşar. Fabrika, cebe bakınca "nabzını" gösterir.

---

## 6. Teknoloji & mimari (ADR-0032 adayı kararlar)

| Karar | Seçim | Gerekçe / reddedilenler |
|---|---|---|
| Çerçeve | **React Native + Expo (EAS)** | Ekip TS+React; **OpenAPI codegen tipleri ve TanStack Query zihinsel modeli aynen paylaşılır**; EAS ile build/dağıtım/OTA yönetilir. *Reddedilen:* Flutter (Dart — tip/ekip paylaşımı yok), PWA (kamera/NFC/push/offline ve mağaza dağıtımı zayıf; saha cihazlarında güvenilmez). |
| Konum | Monorepo `mobile/` paketi | `frontend/` ile kardeş; ortak `packages/api-tipleri` (openapi-typescript çıktısı) her iki istemciye. |
| Dil/kalite | TS strict + ESLint + Prettier | Web ile aynı DoD; CI'ya `mobile` job. |
| Durum | TanStack Query + Zustand | Web ile bire bir aynı desen (`useSayfaliSorgu` benzeri hook'lar taşınır). |
| Offline DB | SQLite (expo-sqlite) + **SQLCipher şifreleme**; kuyruk tablosu + sorgu önbellek persist | WatermelonDB'ye gerek yok — senkron modeli kuyruk-temelli, CRDT değil (sunucu otorite, ilke §2.5). |
| Gerçek zaman | Mevcut WS (`/api/v1/ws/olaylar`) ön planda; arka planda **push** | Pil dostu: WS yalnız uygulama açıkken. |
| Push | FCM (Android) + APNs (iOS), **Expo Notifications** üstünden | Sunucu tarafı F6·S27 `Bildirim` altyapısına kanal olarak eklenir (§8). |
| Kimlik | Aynı OAuth2/JWT + `X-Tenant`; refresh **SecureStore/Keychain**; biyometrik kilit (Face/Touch/parmak) yerel kapı | Web'deki rotasyon/single-flight istemci mantığı porta edilir. |
| Dosya/foto | Mevcut multipart uçları + `NesneDepo` (`tenant_<slug>/ek/...`) | Presigned URL gerekirse ADR'de değerlendirilir; ilk sürümde API üstünden. |
| Tarama | expo-camera + ML Kit barkod; NFC opsiyonel modül | QR/Code128 (F6·S25 etiketleriyle aynı format). |
| Telemetri | Sentry (mevcut hesap) + crash-free metriği | `tenant_id`+`request_id` bağlamı loglara — web ile aynı disiplin. |
| Sürüm zorlama | `GET /mobil/surum` (min sürüm + mağaza linki) | Eski istemcinin kırık sözleşmeyle yazmasını engeller. |

**Katman şeması:**

```
mobile/
 ├─ app/            (expo-router ekranları: sekmeler + modül akışları)
 ├─ ozellikler/     (persona paketleri: operator/, bakim/, depo/, kalite/, isg/, yonetici/)
 ├─ cekirdek/
 │   ├─ api/        (apiClient portu: X-Tenant + Bearer + 401 yenile single-flight)
 │   ├─ kuyruk/     (store-and-forward: sıra, Idempotency-Key, çakışma kutusu)
 │   ├─ kimlik/     (SecureStore, biyometrik kilit, vardiya modu oturumu)
 │   └─ tara/       (QR/barkod/NFC çözümleyici → yönlendirme)
 ├─ bilesenler/     (DurumPim, MiniBar, KpiKaro, GorevKarti, SayiPedi, TaramaCerceve)
 └─ tema/           (Kontrol Odası mobil lehçesi — DESIGN.md token'ları)
```

---

## 7. Tasarım dili — "Kontrol Odası, cep lehçesi"

`DESIGN.md` token'ları temel: nötr antrasit zemin, mavi yalnız vurgu, hat rengi kimliği
(modül ekranlarında ince üst şerit), JetBrains Mono sayısal, `DurumPim` LED dili ikiz ve
kiosk'la birebir aynı. Mobil eklemeleri:

- **Tipografi ölçeği büyür:** gövde 16, KPI 40–56 mono; atölye ışığında kolay okunur.
- **Yüksek kontrast modu:** parlak ortam için tek dokunuş erişilebilir kontrast artışı
  (tema koyu kalır; yüzey/metin kontrastı yükselir).
- **Başparmak bölgesi:** birincil aksiyonlar ekranın alt üçte birinde; tehlikeli
  aksiyonlar (iptal/sil) kaydırarak onay (swipe-to-confirm) deseniyle.
- **Haptik dil:** kuyruk teslimi = kısa tık; hata/çakışma = çift titreşim; ramak kala
  gönderimi = onay deseni. Ses yok (fabrika zaten gürültülü, titreşim konuşur).
- **Boş durumlar öğretir** (web ilkesi): ilk açılışta persona paketine göre 3 kartlık
  mini tur ("QR okut → makinen açılır").
- **Hareket:** 150–250 ms, `prefers-reduced-motion`/OS ayarına saygı — web ile aynı kural.

---

## 8. Backend ek işleri (küçük, eklemeli — mevcut kurallar aynen)

Hepsi `tenant-rbac-conventions` + `turkce-identifier-standardi` disiplinli; şemada
yalnız iki küçük tablo:

| İş | Detay |
|---|---|
| `cihaz_jetonlari` | Push token kaydı: `POST/DELETE /cihazlar/push-jetonu` (kullanıcıya bağlı, platform alanlı); F6·S27 `Bildirim` üreticisine **push kanalı** eklenir (tercih sistemine "mobil" kanalı). |
| `vardiya_cihazlari` | Paylaşımlı tablet kaydı + rozet-QR/PIN hızlı oturum uçları (`POST /kimlik/rozet-oturum`); her işlem gerçek kullanıcı kimliğiyle audit'e (S23 oturum yönetimiyle entegre — mobil oturumlar da `/oturumlar` ekranında görünür/sonlandırılır). |
| `GET /mobil/surum` | Min desteklenen sürüm + mağaza linki (public, tenant'sız). |
| Ek (foto) yükleme | Mevcut multipart + `NesneDepo` deseni; anahtar `tenant_<slug>/ek/<modul>/...` — DYS ile aynı izolasyon garantisi. |
| Idempotency genişletme | Kuyruklu yazma yapan tüm POST/PATCH uçlarında `Idempotency-Key` desteğinin eksiksizliği doğrulanır (S9'da temel var; kapsam taraması M1'de). |

Her yeni uç: RBAC 403 + tenant izolasyon + idempotency testli (global DoD).

---

## 9. Güvenlik & KVKK (mobil özel katman)

- **Token saklama:** refresh yalnız Keychain/Keystore (SecureStore); access bellekte.
  Biyometrik kilit uygulama açılış kapısı (yerel; sunucu oturumundan bağımsız).
- **Cihaz hijyeni:** root/jailbreak tespiti → uyarı + hassas modüller (İK) kapanır;
  ekran görüntüsü engeli İK/KVKK ekranlarında (`FLAG_SECURE`/iOS koruması).
- **Yerel veri:** SQLite **SQLCipher** ile şifreli; çıkışta ve tenant askıya alınınca
  (F4·S17) yerel veri silinir (**uzaktan temizleme**: oturum sonlandırma push'u).
- **KVKK:** cepte kişisel veri minimizasyonu — TC hiç inmez (maskeleme zaten sunucuda),
  personel modülü self-servis dışında mobilde yok; foto ekleri yalnız iş bağlamı;
  aydınlatma metni ilk açılışta.
- **Vardiya cihazı:** kiosk-kilitli, oturum süresi vardiyayla sınırlı, hareketsizlikte
  otomatik kilit; rozet-QR tek başına yetmez (PIN ikinci faktör).
- **MDM uyumu:** managed Play / Apple Business Manager ile kurumsal dağıtım; AppConfig
  üzerinden tenant kodu ön-tanımlanabilir (kullanıcı yalnız e-posta+parola girer).

---

## 10. Kilometre taşları (M0–M5) — kapsam + kabul kriterleri

> Sprint döngüsü ve Global DoD, yol haritasındaki çalışma modeliyle aynıdır (kırmızı →
> yeşil → refactor → doğrulama → DoD; lint/tip temiz, testler, izolasyon+RBAC, ADR).

#### ⬜ M0 — Temel: iskelet + kimlik + tema
`mobile/` Expo + TS strict + CI job; ortak `packages/api-tipleri` (codegen paylaşımı);
tema (cep lehçesi) + i18n TR/EN; kimlik akışı: tenant kodu → e-posta/parola → (S23) 2FA →
SecureStore + sessiz yenileme + biyometrik kilit; 5 sekme iskeleti + rol-duyarlı boş
Bugün; Sentry; `GET /mobil/surum` + zorlama ekranı.
**Kabul:** iki gerçek tenant ile giriş/çıkış/yenileme cihazda (iOS+Android) çalışır;
yanlış tenant token reddi görünür hatayla; biyometrik kilit açılışta; CI yeşil. ADR-0032.

#### ⬜ M1 — Operatör paketi + offline çekirdek
Görevlerim (iş emirleri) + detay + durum geçişi + yorum; hızlı üretim girişi (sayı pedi,
fire); **Tara v1** (makine QR → makine kartı: canlı durum + OEE bar + aksiyonlar);
duyurular; **kuyruk v1** (üretim girişi/yorum/durum geçişi offline; çakışma kutusu);
`Idempotency-Key` kapsam taraması (backend).
**Kabul:** uçuş modunda girilen üretim verisi bağlantıda **tek sefer** işlenir (çift
kayıt yok — cihaz testi + backend idempotency testi); QR→makine kartı < 2 sn; durum
geçişi web'dekiyle aynı 409 disiplininde; olaylar WS ile canlı düşer.

#### ⬜ M2 — Bakım & Depo paketleri
Bakım görevleri + tamamlama; **arıza bildir** (foto+not → `NesneDepo` ek deseni);
makine geçmişi; stok kartı (barkod) + hızlı giriş/çıkış/transfer; **mobil sayım modu**
(F6·S25 sayım oturumunun mobil istemcisi — tam offline sayılır, senkronda fark listesi
sunucuda oluşur, onay yine webde/`stok:duzeltme`).
**Kabul:** foto ekli arıza kaydı uçtan uca (MinIO'da tenant-izole anahtar); sayım
offline yapılır, senkronda fark doğru; barkod→stok kartı < 2 sn; tüm yazmalar kuyruklu.

#### ⬜ M3 — Kalite, İSG & self-servis
Kalite kontrol girişi; uygunsuzluk aç (foto); **tek-tuş Ramak Kala** (§5.2); risk
gözlemi; izin talebi + bakiye (F6·S26 hakediş); sertifikalarım/zimmetlerim; **bildirim
merkezi + tercihler** (push kanalı canlı — `cihaz_jetonlari`).
**Kabul:** ramak kala ≤3 dokunuş ve İSG uzmanına push düşer; izin akışı çift yönlü
(talep → onaylayana push → sonuç talep edene push); push tercihi kapatınca gelmez;
bildirimler tenant-izole (yanlış tenant'a push imkânsız — token↔tenant bağı testli).

#### ⬜ M4 — Yönetici cebi + vardiya cihazı + widget
Mini pano (dönem OEE, kazasız gün, kritik uyarılar — `analitik/kpi` yeniden kullanım);
**Onaylarım** (F6·S27 `/onaylarim` — yalnız çevrimiçi, görev ayrımı izinleri);
**vardiya cihazı modu** (§5.3 — rozet-QR + PIN, audit gerçek kişiyle); ana ekran
widget'ları (OEE, kazasız gün) + kritik durum canlı bildirimi.
**Kabul:** push→aç→onayla akışı < 10 sn; paylaşımlı cihazda kullanıcı geçişi < 3 sn ve
audit doğru kişiyi yazar; widget son değeri gösterir (bayat işaretli); onay ekranı
offline'da güvenli şekilde kilitli.

#### ⬜ M5 — Sertleştirme & mağaza yayını `saha-v1.0.0`
E2E (Maestro/Detox: kritik akışlar cihaz çiftliğinde); performans (soğuk açılış,
liste kaydırma) + pil profili; güvenlik pası (root/jailbreak, SQLCipher doğrulama,
ekran koruması, pentest bulguları); erişilebilirlik (dinamik yazı tipi, TalkBack/
VoiceOver, kontrast); mağaza varlıkları (ikon/ekran görüntüleri/açıklama TR-EN);
**kurumsal dağıtım** (managed Google Play + Apple Business Manager; MDM AppConfig) +
açık mağaza; OTA politikası (yalnız JS katmanı, native değişiklikte mağaza treni);
pilot fabrika saha testi (gerçek vardiya, gerçek eldiven).
**Kabul:** NFR tablosu (§12) karşılanır; crash-free ≥ %99.5 (pilot); mağaza onayları
alınmış; pilot geri bildirimi kapatılmış; `saha-v1.0.0` etiketli.

> **🚦 Mobil Kapısı:** Operatör+bakım+depo+kalite+İSG paketleri sahada; offline kuyruk
> kayıpsız; push izole; pilot vardiyası uygulamayı **kendiliğinden** kullanıyor.

---

## 11. Test stratejisi & DoD

- **Birim:** saf mantık (kuyruk sıralama/yeniden deneme, tarama çözümleyici, persona
  paket derleme) — Jest/Vitest; web'deki "saf fonksiyon + tablo testi" geleneği.
- **Bileşen:** RN Testing Library — **görünür Türkçe metin + erişilebilirlik rolü**
  (web testlerindeki aynı sınır: test-id değil).
- **E2E:** Maestro (tercih; YAML, CI-dostu) kritik akışlar: giriş → QR → üretim girişi
  → uçuş modu → senkron; ramak kala; onay akışı.
- **Backend:** yeni uçlar için pytest (izolasyon + RBAC + idempotency) — mevcut 7 kritik
  test ailesine **"push tenant-izolasyonu"** eklenir.
- **Cihaz matrisi:** iOS son 2 sürüm + Android API 26+; düşük-uç Android referans cihazı
  (saha gerçeği) her sprintte elle duman testi.
- **DoD ekleri:** her ekran offline davranışını beyan eder (önbellek/kuyruk/kilitli);
  her yazma akışının idempotency testi vardır; ekran görüntüleri mağaza diline uygun.

## 12. NFR hedefleri

| Metrik | Hedef |
|---|---|
| Soğuk açılış (orta segment Android) | ≤ 2.5 sn |
| QR/barkod → kart | ≤ 2 sn |
| Offline dayanıklılık | ≥ 72 saat / ≥ 1.000 kuyruk kaydı, kayıpsız |
| Crash-free oturum | ≥ %99.5 |
| Uygulama boyutu (Android indirme) | ≤ 40 MB |
| Pil (vardiya boyu, arka plan) | ≤ %3 |
| Erişilebilirlik | dokunma ≥ 48dp · dinamik yazı tipi · ekran okuyucu etiketleri tam |

## 13. Bağımlılıklar (neden "tüm fazlardan sonra")

| Bağımlılık | Mobilde kullanan |
|---|---|
| F4·S16 entitlement | menü/paket süzgeci (kapalı modül cepte de kapalı) |
| F6·S23 oturum/cihaz yönetimi + 2FA | mobil oturumlar `/oturumlar`'da; uzaktan sonlandırma; giriş 2FA adımı |
| F6·S24 duruş kayıtları | operatör duruş girişi |
| F6·S25 barkod/etiket + sayım oturumu | Tara + mobil sayım modu |
| F6·S26 hakediş bakiyesi | izin self-servis |
| F6·S27 bildirim altyapısı + `/onaylarim` | push kanalı + Onaylarım ekranı |

> Erken başlanmak istenirse asgari küme: **M0–M1 yalnız S23+S27'ye ihtiyaç duyar**
> (duruş/sayım/hakediş ekranları kendi sprintleri bitene dek paketten düşer) — karar
> sprint açılışında verilir.

## 14. Riskler & azaltım

| Risk | Azaltım |
|---|---|
| Offline çakışmaları kullanıcıyı yorar | Sunucu-otorite ilkesi + "çakıştı kutusu" tek dokunuş çözümü; durum geçişleri gibi çatışmaya açık yazmalar kuyruğun en önünde senkronlanır |
| Paylaşımlı cihazda kimlik bulanıklığı | Rozet-QR+PIN zorunlu ikili; hareketsizlik kilidi; audit gerçek kişi testi DoD'de |
| Push teslimat güvenilirliği | Push = tetikleyici, veri değil (açınca API'den taze çekilir); kritik akışlar WS+yoklama yedekli |
| Mağaza süreç gecikmeleri | OTA (JS katmanı) + kurumsal dağıtım kanalı paralel; native değişiklik pencereleri planlı |
| RN/Expo sürüm kırılmaları | Expo SDK LTS takibi; sürüm yükseltme ayrı, testli PR; E2E regresyon zorunlu |
| Kapsam şişmesi ("web'i cebe kopyala" baskısı) | §1 konumlandırma anayasadır; yeni ekran talebi persona-görev testinden geçmeden giremez (MoSCoW) |

## 15. Açık sorular (sprint açılışında karara bağlanır)

1. NFC ilk sürümde mi, yoksa QR yeterli mi? (donanım envanterine bağlı)
2. Vardiya cihazı modu M4'te mi kalmalı, pilot fabrika talebine göre M2'ye mi çekilmeli?
3. Açık mağaza + kurumsal dağıtım birlikte mi, önce yalnız kurumsal mı?
4. iOS azınlıksa (saha genelde Android) iOS M5'e mi ertelenir?
5. Uygulama içi tenant markalaması (logo/renk) v1'de mi? (F4 dış portal markalamasıyla ortak karar)
