# S16 — Abonelik, Entitlement & Feature Flag (Tasarım)

**Tarih:** 2026-07-09 · **Sprint:** Faz 4 / S16 · **ADR:** 0018

## 1. Amaç

Ürünü **modül modül satılabilir** hâle getirmek: tenant'ın planı hangi modülleri
kapsıyorsa yalnız onlar açılır; kapalı modüle erişim **backend'de 403** ile engellenir
ve **frontend menüsünde görünmez**. Koltuk (seat) limiti aşımı engellenir. Entitlement
değişimi **anında** etkili olur.

## 2. Kavramlar ve sözlük (turkce-identifier-standardi)

| Kavram | Identifier | Açıklama |
|---|---|---|
| Plan | `Plan` / `planlar` | Satış planı: modül seti + koltuk limiti + özellik seti |
| Entitlement (modül hakkı) | `ModulHakki` / `modul_haklari` | Tenant-başına modül aç/kapat **istisnası** (override) |
| Feature flag (özellik bayrağı) | `OzellikBayragi` / `ozellik_bayraklari` | Tenant-başına deneysel özellik aç/kapat istisnası |
| Modül | `modul_kodu` | İş modülü kimliği (`MODUL_KATALOGU` anahtarı) |
| Koltuk | `koltuk_limiti` / `koltuk` | Aktif kullanıcı üst sınırı (`None` = sınırsız) |

**Etkin entitlement** = override varsa override, yoksa "modül planın `moduller`
listesinde mi". Bilinmeyen modül kodu → **kapalı** (fail-closed).

## 3. Modül kataloğu (17 modül)

`uretim` (makineler+üretim verileri+OEE+ikiz+kiosk), `saha`, `isemri`, `bakim`,
`stok` (malzeme+hareket+satınalma), `kalite`, `enerji`, `isg`, `ik`, `crm`
(firma/ortak+ticari pano), `sozlesme`, `talep`, `dys`, `duyuru`, `ai`, `analitik`, `rapor`.

Çekirdek (her zaman açık, entitlement dışı): kimlik, kullanıcılar/roller, abonelik
uçları, WS, sağlık. **İkiz+kiosk `uretim`'e, ticari pano `crm`'e, satınalma `stok`'a
bağlıdır** (ayrı satılmaz — menü bölümleriyle hizalı).

## 4. Plan kataloğu (4 plan)

| Kod | Koltuk | Modüller | Özellikler |
|---|---|---|---|
| `deneme` | 5 | tümü | tümü |
| `temel` | 10 | uretim, isemri, bakim, stok | — |
| `profesyonel` | 50 | temel + saha, kalite, enerji, isg, ik, crm, sozlesme, talep, dys, duyuru | — |
| `kurumsal` | sınırsız | tümü | tümü |

Mevcut tüm tenant'lar `deneme` planında → davranış değişmez (geriye uyumlu).

## 5. Veri modeli (public / control-plane)

- `planlar`: `kod` uq, `ad`, `koltuk_limiti` int nullable, `moduller` JSONB list,
  `ozellikler` JSONB list, `aktif` bool. Kaynak gerçeği kod tarafında `PLAN_KATALOGU`;
  migration statik literallerle seed eder, provizyon her koşuda upsert ile eşitler.
- `modul_haklari`: `tenant_id` FK CASCADE, `modul_kodu`, `acik` bool,
  uq(`tenant_id`,`modul_kodu`).
- `ozellik_bayraklari`: `tenant_id` FK CASCADE, `kod`, `acik` bool, uq(`tenant_id`,`kod`).
- `abonelik.plan_kodu` → FK `planlar.kod` (migration'da seed'den SONRA eklenir).

## 6. Zorlama (enforcement)

- **`modul_gerekli(kod)`** dependency (core/deps.py): `tenant_cozumle` sonrası planı +
  override'ları **istek başına sorgular** (önbellek YOK → değişim anında etkili;
  Redis önbelleği bilinçli ertelendi, ADR-0018). Kapalıysa
  `403 YetkiHatasi(hata_kodu="MODUL_KAPALI")`. RBAC'den bağımsızdır: **admin bile
  kapalı modüle giremez** (bypass güvenlik testi).
- 19 modül router'ına `dependencies=[Depends(modul_gerekli(...))]` (router seviyesi).
- **Koltuk limiti**: `POST /kullanicilar`'da `public.tenant` satırı `FOR UPDATE`
  kilitlenir (eşzamanlı oluşturma yarışına karşı), aktif kullanıcı sayısı ≥ limit →
  `409 CakismaHatasi(hata_kodu="KOLTUK_LIMITI")`. Pasif kullanıcı sayılmaz.

## 7. Uçlar

- `GET /api/v1/moduller` — **oturum yeterli** (izin yok): menü süzgeci her kullanıcıya
  lazım; yalnız modül adı/açıklık sızar (menünün zaten gösterdiği bilgi). Yanıt:
  `{moduller: [{kod, ad, acik, kaynak: "plan"|"hak"}], ozellikler: [{kod, ad, acik, deneysel}]}`.
- `GET /api/v1/abonelik` — yeni izin **`abonelik:oku`** (admin + izleyici `:oku`
  kuralıyla alır): plan künyesi + dönem + `koltuk {limit, kullanilan}` + modüller +
  özellikler.
- Entitlement **yazma API'si S17'de** (platform admin paneli). S16'da değişiklik
  control-plane servis fonksiyonları + `backend/scripts/entitlement_ayarla.py` CLI ile.

## 8. Frontend

- `useModuller()` (TanStack, staleTime 60 sn): menü süzgeci + rota kapısı beslenir.
  Veri yüklenmemişken/uçtan hata gelirse **fail-open** (UI gizlemez; backend zaten
  zorlar — kilitlenme değil kozmetik süzgeç).
- `menu.ts`: `MenuOgesi.modul?` + `gorunurMenu(ogeler, izinVar, modulAcik)`.
- `routes/ModulKapisi.tsx`: modül kapalıysa **upsell boş durumu** (kilit ikonu +
  "Bu modül planınızda kapalı" + `abonelik:oku` varsa `/abonelik`'e CTA).
- `/abonelik` ekranı (Yönetim, slate; uiplani §11.1): plan kartı + koltuk progress
  (eşik renkli) + hat renkli modül matrisi + "deneysel" özellik rozetleri.

## 9. Kabul kriterleri (yol haritası S16)

1. Kapalı modüle erişim backend'de 403 `MODUL_KAPALI` + UI'da menüde yok, doğrudan
   URL'de upsell.
2. Koltuk limiti aşımı 409 `KOLTUK_LIMITI` ile engellenir.
3. Entitlement değişimi anında etkili (override yaz → bir sonraki istek 403/200).
4. Bypass güvenlik testi: tüm izinlere sahip admin, kapalı modülde yine 403.
5. Tenant izolasyonu: A'nın override'ı B'yi etkilemez.
6. Migration public ağacında up/down çalışır; eski tenant'lar `deneme` ile aynen çalışır.
