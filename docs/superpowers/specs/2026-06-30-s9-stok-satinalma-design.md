# S9 — Stok & Satınalma · Tasarım (Spec)

> Faz 2 / Sprint S9. Onaylı yol haritası: `docs/yol-haritasi.md` ve `~/.claude/plans/…buzzing-cake.md` §4 (FAZ 2 / S9).
> Bağlayıcı skill'ler: `tenant-rbac-conventions`, `turkce-identifier-standardi`, `alembic-fan-out`.

## 1. Amaç ve Kabul Kriterleri

Stok (malzeme + hareket) ve satınalma talebi (çok-kalemli + onay akışı) modülünü çekirdeğin üzerine, **çok-kiracılı + RBAC + canlı** kurmak.

Kabul kriterleri (plandan):
1. **Stok hareketi bakiyeyi doğru günceller** (giriş artırır, çıkış azaltır; çıkışta negatif bakiye reddedilir).
2. **Kritik eşik tetikler** — bakiye kritik eşiğin altına düştüğünde `stok.kritik` olayı üretilir.
3. **`satinalma:onay` ayrı izin** — talebi onaylama, oluşturma izninden (`satinalma:yaz`) bağımsızdır.
4. Ek DoD: tenant izolasyon + RBAC + migration fan-out testleri; **ADR-0011** (Stok & Satınalma).

## 2. Kapsam Kararları (onaylı)

| Karar | Seçim | Gerekçe |
|---|---|---|
| Kapsam | **Backend + frontend** uçtan uca | S3–S8 ile tutarlı; modül demolanabilir. |
| Bakiye modeli | **`Malzeme.mevcut_miktar`'da tutulur + `FOR UPDATE`** | Hızlı okuma, kritik eşik kontrolü kolay; eşzamanlı hareketlerde satır kilidi çift-hesabı önler (iş emri durum-geçişi deseninin aynısı). |
| Bakiye doğruluğu | Çıkışta **negatif reddedilir** (422); her harekette `bakiye_sonrasi` snapshot | Hareket geçmişi denetlenebilir; bakiye yeniden türetilebilir (tutarlılık kanıtı). |
| Talep yapısı | **Çok-kalemli** (başlık + N kalem) | Gerçek ERP deseni; bir talepte çok malzeme. |
| Onay akışı | **Saf durum makinesi** (`talep_durum.py`) | İş emri deseni; geçiş kuralları DB'siz test edilir; `onaylandi`/`reddedildi` geçişi `satinalma:onay` ister. |
| `stok.kritik` semantiği | **Kenar tetikleme** (eşik üstünden altına ilk geçişte 1 kez) | Gürültüsüz; webhook/bildirim için doğru. Eşik altında kalan ardışık çıkışlar tekrar yayınlamaz. |
| Talep ↔ stok | **Ayrı** (onay otomatik stok hareketi üretmez) | S9 kabul kriterlerinde mal kabul yok; sipariş/teslimat akışı ileride (YAGNI). |

### 2.1 İyileştirmeler (bu tasarımda katılan)
- **A — `duzeltme` hareket türü:** giriş/çıkış dışında **envanter sayım düzeltmesi**; `miktar` = sayılan **yeni mutlak bakiye**, servis deltayı hesaplar (`bakiye_sonrasi = miktar`). Gerçek depo gereği; kenar-tetikli kritik mantığı düzeltme deltasında da çalışır.
- **B — Opsiyonel `Idempotency-Key` (`POST /stok-hareketleri`):** çift-tıkta/yeniden-denemede bakiyenin iki kez değişmesini önler. Nullable **unique** `idempotency_anahtari`; aynı anahtar tekrar gelirse **mevcut hareket döner, bakiye değişmez**. Yol haritası "POST için opsiyonel Idempotency-Key" standardının ilk uygulaması (seam: ileride genel middleware'e çıkarılabilir).
- **C — Maliyet görünürlüğü:** talep kaleminde `tahmini_birim_fiyat` (nullable), talepte `para_birimi` (vars. `TRY`); talep cevabında **türetilmiş `tahmini_toplam`** (Σ miktar×fiyat) — onaylayan maliyeti görerek karar verir. Tutar saklanmaz, cevapta türetilir (bayatlamaz).
- **D — Doğrulama sertliği:** `birim` **beyaz-liste** (`BIRIMLER`); `miktar > 0` (hareket+kalem); `kritik_stok ≥ 0`, `min_stok ≥ 0`, varsa `max_stok ≥ min_stok`; geçersiz → 422 standart hata.
- **F — `stok.kritik` gerçek-zaman yayını da** (outbox'a ek): UI'da **canlı kritik rozet/uyarı** (S7 hattı). Outbox = kalıcı/webhook (S18); realtime = anlık UI.
- **G — Hareket listesi filtreleri:** `malzeme_id` + `tur` + tarih aralığı (`baslangic`/`bitis`) + sayfalama/sıralama.
- **Append-only & soft-delete:** stok hareketleri **değiştirilemez/silinemez** (audit); malzeme sert silinmez (`aktif=false` ile pasifleştirilir, FK `RESTRICT` korur).

## 3. Bileşenler ve Topoloji

```
backend/app/modules/stok/         # YENİ — malzeme + stok hareketi + satınalma talebi (standart modül)
  ├─ models.py                     # Malzeme, StokHareketi, SatinalmaTalebi, SatinalmaTalebiKalemi
  ├─ talep_durum.py                # SAF durum makinesi (DB'siz, birim testli)
  ├─ birimler.py                   # BIRIMLER beyaz-liste + STOK_HAREKET_TURLERI sabitleri
  ├─ schemas.py                    # Pydantic DTO'lar (Decimal miktarlar)
  ├─ repository.py                 # sorgular (getir_kilitli = FOR UPDATE, listele = arama/sıralama/filtre)
  ├─ service.py                    # stok_hareketi_uygula, talep_durum_gecisi, oto kod
  └─ router.py                     # /malzemeler, /stok-hareketleri, /stok/kritik, /satinalma-talepleri
backend/migrations/tenant/…        # YENİ — 4 tablo (fan-out)
backend/app/kimlik/izinler.py      # 2 yeni varsayılan rol (izinler zaten katalogda)
frontend/src/modules/stok/         # YENİ — malzeme + stok + satınalma ekranları
```

### 3.1 Saf durum makinesi `talep_durum.py`
İş emri `durum.py` deseninin aynısı (GECISLER tablosu + `gecis_gecerli_mi` + `gecerli_hedefler`):

```
taslak ──> onay_bekliyor ──> onaylandi*
   │            │
   │            └──────────> reddedildi*
   └──> iptal*   onay_bekliyor ──> iptal*
```

- `GECISLER = { taslak: {onay_bekliyor, iptal}, onay_bekliyor: {onaylandi, reddedildi, iptal}, onaylandi: {}, reddedildi: {}, iptal: {} }`
- `ILK_DURUM = "taslak"`; `TERMINAL_DURUMLAR = {onaylandi, reddedildi, iptal}`.
- Geçiş **izni** durum tablosunda değil router/servis katmanında: `onaylandi`/`reddedildi` → `satinalma:onay`; `onay_bekliyor`/`iptal` → `satinalma:yaz`.

### 3.2 Servis `service.py`
- `stok_hareketi_uygula(db, malzeme, *, tur, miktar, aciklama, kaynak, kullanici, idempotency_anahtari=None) -> StokHareketi`
  1. (B) `idempotency_anahtari` verilmiş + mevcutsa → mevcut hareketi döner (no-op).
  2. Malzeme satırı `FOR UPDATE` ile kilitli okunur (router `getir_kilitli` geçirir).
  3. `eski = malzeme.mevcut_miktar`; yeni bakiye türe göre: `giris → eski+miktar`, `cikis → eski−miktar` (negatif → `DogrulamaHatasi` 422), `duzeltme → miktar` (mutlak).
  4. (Kenar tetik) `ustteydi = eski > kritik_stok`; `simdi_altinda = yeni <= kritik_stok ve kritik_stok > 0`; `ustteydi ∧ simdi_altinda` → `olay_yayinla("stok.kritik", …)` (outbox, **aynı transaction**) **ve** realtime `stok.kritik` (F).
  5. `malzeme.mevcut_miktar = yeni`; `StokHareketi(bakiye_sonrasi=yeni, …)` yaz; `flush`.
- `talep_durum_gecisi(db, talep, *, hedef, onaylayan, red_nedeni=None)`: saf makineyle doğrula (geçersiz hedef → 422, geçersiz geçiş → 409); `onaylandi`→`onaylayan_kullanici_id`+`onay_tarihi`; `reddedildi`→`red_nedeni` (zorunlu, 422 boşsa); `flush`. Talep `getir_kilitli` (FOR UPDATE) ile çift-onay önlenir.
- `gecici_kod()/kalici_kod(id)` → `ST-{yıl}-{id:06d}` (iş emri deseni).

### 3.3 Uçlar `router.py` (hepsi tenant-kapsamlı + RBAC + yazıda audit)

**Malzeme**
- `POST /malzemeler` → `stok:yaz` (kod tekil; birim/eşik doğrulama; +audit)
- `GET /malzemeler` → `stok:oku` (sayfalama/arama[kod,ad]/sıralama; `aktif`/`kategori` filtresi)
- `GET /malzemeler/{id}` → `stok:oku`
- `PATCH /malzemeler/{id}` → `stok:yaz` (ad/kategori/birim/eşikler/aktif; **`mevcut_miktar` doğrudan değiştirilemez** — yalnız hareketle)
- `GET /stok/kritik` → `stok:oku` (`mevcut_miktar <= kritik_stok ∧ kritik_stok > 0`, aktif malzemeler)

**Stok hareketi**
- `POST /stok-hareketleri` → `stok:yaz` (gövde: `malzeme_id, tur, miktar, aciklama, kaynak`; başlık: opsiyonel `Idempotency-Key`; bakiyeyi günceller; +audit; realtime `stok.hareket`)
- `GET /stok-hareketleri` → `stok:oku` ((G) `malzeme_id`/`tur`/`baslangic`/`bitis` + sayfalama/sıralama)

**Satınalma talebi**
- `POST /satinalma-talepleri` → `satinalma:yaz` (başlık + N kalem; durum `taslak`; her kalem `malzeme_id` tenant'ta var; +audit; realtime `satinalma.durum`)
- `GET /satinalma-talepleri` → `satinalma:oku` (sayfalama/arama[kod,başlık]/`durum` filtresi)
- `GET /satinalma-talepleri/{id}` → `satinalma:oku` (kalemler + `tahmini_toplam`)
- `PATCH /satinalma-talepleri/{id}` → `satinalma:yaz` (yalnız `taslak`'ta; başlık/açıklama/kalemler)
- `POST /satinalma-talepleri/{id}/gonder` → `satinalma:yaz` (`taslak → onay_bekliyor`)
- `POST /satinalma-talepleri/{id}/onayla` → **`satinalma:onay`** (`onay_bekliyor → onaylandi`)
- `POST /satinalma-talepleri/{id}/reddet` → **`satinalma:onay`** (gövde `red_nedeni`; `onay_bekliyor → reddedildi`)
- `POST /satinalma-talepleri/{id}/iptal` → `satinalma:yaz` (`taslak`/`onay_bekliyor → iptal`)

## 4. Veri Modeli ve Migration (alembic-fan-out)

Tenant ağacına yeni revizyon. `down_revision` = mevcut tenant head (uygulama anında `alembic heads` ile doğrulanır; bilinen son: `f3a9c1d72b84`). **Hypertable yok** (düşük hacim, ilişkisel). Miktarlar `Numeric(18, 3)` (Decimal aritmetik; float hatası yok); para `Numeric(18, 2)`.

- **`malzemeler`** (`Malzeme`, `KimlikMixin`+`ZamanDamgaliMixin`): `kod` (String50, **unique**, index), `ad` (String200), `birim` (String20), `kategori` (String100, default ""), `mevcut_miktar` (Numeric18.3, default 0), `min_stok` (default 0), `max_stok` (nullable), `kritik_stok` (default 0), `aktif` (bool, default True).
- **`stok_hareketleri`** (`StokHareketi`): `malzeme_id` (FK `malzemeler.id` **RESTRICT**, index), `tur` (String10: `giris|cikis|duzeltme`), `miktar` (Numeric18.3), `bakiye_sonrasi` (Numeric18.3), `aciklama` (String500, default ""), `kaynak` (String50, nullable), `olusturan_kullanici_id` (FK `kullanici.id` SET NULL, nullable), `idempotency_anahtari` (String64, **unique**, nullable). Append-only.
- **`satinalma_talepleri`** (`SatinalmaTalebi`): `kod` (String50, **unique**, index, `ST-{yıl}-{id:06d}`), `baslik` (String200), `aciklama` (String1000, default ""), `durum` (String20, default `taslak`, index), `para_birimi` (String3, default `TRY`), `talep_eden_kullanici_id` (FK SET NULL), `onaylayan_kullanici_id` (FK SET NULL, nullable), `onay_tarihi` (timestamptz, nullable), `red_nedeni` (String500, nullable). `kalemler` relationship (cascade all, delete-orphan).
- **`satinalma_talebi_kalemleri`** (`SatinalmaTalebiKalemi`): `talep_id` (FK `satinalma_talepleri.id` **CASCADE**, index), `malzeme_id` (FK `malzemeler.id` **RESTRICT**, index), `miktar` (Numeric18.3), `birim` (String20), `tahmini_birim_fiyat` (Numeric18.2, nullable), `aciklama` (String500, default "").

**Fan-out DoD:** `public` + ≥2 tenant şemasında up/down testli; downgrade 4 tabloyu (FK sırasına göre) düşürür.

**Seed (`kimlik/izinler.py`):** İzinler **zaten katalogda** (`stok:oku/yaz`, `satinalma:oku/yaz/onay`). Görev ayrımı (separation-of-duties) demosu için 2 yeni varsayılan rol:
- `VARSAYILAN_ROLLER["depo"] = {stok:oku, stok:yaz, satinalma:oku, satinalma:yaz}` (depo sorumlusu: stok + talep oluşturur, **onaylayamaz**).
- `VARSAYILAN_ROLLER["satinalma-onaylayan"] = {satinalma:oku, satinalma:onay}` (yalnız onay yetkisi).

(`admin` zaten hepsine; `izleyici` `:oku`'lara sahip.)

## 5. Olaylar

- **Outbox (transactional, S18 webhook):** `stok.kritik` → `{malzeme_id, kod, ad, mevcut_miktar, kritik_stok}` (kenar tetikli, `stok_hareketi_uygula` içinde aynı transaction).
- **Gerçek zaman (`core/gercekzaman.yayinla`, canlı UI):** `stok.hareket {malzeme_id}` (malzeme+hareket listesi invalidate), `satinalma.durum {id, durum}` (talep listesi/detay invalidate), `stok.kritik {malzeme_id, kod}` (canlı kritik rozet/uyarı).

## 6. Hata Yönetimi

- Çıkışta negatif bakiye → **422** (`DogrulamaHatasi`, bakiye/istenen miktar detayında).
- Geçersiz durum hedefi → **422**; durum makinesine aykırı geçiş → **409** (`CakismaHatasi`).
- `satinalma:onay` izni yok → **403** (`onayla`/`reddet`).
- Bilinmeyen malzeme/talep → **404**; tekrar `kod` → **409**; doğrulama (`birim`/`miktar`/eşik) → **422**.
- (B) Tekrar `Idempotency-Key` → **200/201** mevcut hareketle, **bakiye değişmez**.
- `taslak` dışı talepte `PATCH` → **409** (yalnız taslak düzenlenebilir).

## 7. Test Stratejisi (DoD + kritik aileler)

**Birim (saf, DB'siz):**
- `talep_durum`: tüm geçerli/geçersiz geçişler, terminal'den çıkış yok, `gecerli_hedefler`.
- `birimler`: `BIRIMLER`/`STOK_HAREKET_TURLERI` doğrulama yardımcıları.

**Entegrasyon (TestClient + test DB):**
- **Bakiye:** giriş artırır, çıkış azaltır, `duzeltme` mutlak set eder; `bakiye_sonrasi` snapshot doğru; **negatif çıkış → 422**.
- **Kenar tetik:** eşik üstünden altına ilk çıkış → `stok.kritik` outbox satırı (1 kez); eşik altında 2. çıkış → **yeni olay yok**; eşik üstündeki hareket → olay yok; `duzeltme` ile altına inme → olay.
- `/stok/kritik`: doğru malzemeleri döner (aktif + `<= kritik`).
- **(B) Idempotency:** aynı `Idempotency-Key` ile 2. POST → tek hareket, bakiye 1 kez değişti.
- **Talep akışı:** çok-kalemli oluştur → `gonder` → `onayla` (alanlar set) / `reddet` (red_nedeni); geçersiz geçiş → **409**; `tahmini_toplam` doğru.
- **RBAC ayrımı (kritik):** `satinalma:yaz` olan ama `satinalma:onay` **olmayan** kullanıcı `onayla` → **403**; `satinalma:onay` olan onaylar.
- **Tenant izolasyonu (kritik):** alfa malzemesine/talebine beta token'ı erişemez (404/403).
- **RBAC 403:** `stok:oku`/`satinalma:oku` olmayan rol listelerde 403.
- **Audit:** her yazma (`olustur`/`hareket`/`durum_guncelle`) `denetim_izi` üretir.
- **Sözleşme:** `openapi.json` regen + schemathesis kırmızı değil.
- **Migration fan-out:** `public` + 2 tenant şemasında up/down.

**Frontend (Vitest + RTL):**
- `talep_durum` aynası (backend ile birebir, testli); durum/öncelik rozetleri; izin-duyarlı aksiyon görünürlüğü; hook'lar (TanStack Query) mock fetch ile.

## 8. Frontend `frontend/src/modules/stok/`

Codegen regen (`npm run codegen`) sonrası tiplenmiş API. Bileşenler (S6 deseni: `SunucuTablo`, hook'lar, rozetler):
- **Malzeme:** `MalzemeListesi` (`SunucuTablo` + kritik rozet + bakiye/birim sütunları), `MalzemeDetay` (bakiye + eşikler + son hareketler + "stok hareketi ekle"), `MalzemeFormu` (oluştur/düzenle).
- **Stok hareketi:** `StokHareketGirisFormu` (giriş/çıkış/düzeltme; opsiyonel idempotency anahtarı UI'da otomatik üretilir), hareket listesi (filtreli).
- **Kritik stok:** `KritikStok` paneli (`/stok/kritik`) — canlı `stok.kritik` ile güncellenir.
- **Satınalma:** `SatinalmaTalepListesi` (durum rozetli), `SatinalmaTalepDetay` (Drawer: kalemler + `tahmini_toplam` + **izin-duyarlı** gönder/onayla/reddet/iptal aksiyonları; `satinalma:onay` yoksa onay/red gizli), `SatinalmaTalepFormu` (dinamik çok-kalem satırları).
- **Menü (RBAC-gated):** "Stok" (`stok:oku`) → malzemeler/kritik; "Satınalma" (`satinalma:oku`) → talepler. Rotalar + i18n **TR/EN tam**.
- **Canlı:** `olayIsle` → `stok.hareket`/`stok.kritik`/`satinalma.durum` olayları ilgili sorguları invalidate eder.

## 9. Bağımlılıklar ve Operasyon

- **Yeni bağımlılık yok** (mevcut stack: FastAPI/SQLAlchemy/Alembic/TanStack/AntD/ECharts).
- **ADR-0011:** `docs/adr/0011-stok-satinalma.md` — tutulan bakiye + `FOR UPDATE`, kenar-tetikli `stok.kritik`, çok-kalemli talep durum makinesi, `satinalma:onay` görev ayrımı, opsiyonel Idempotency-Key.
- **Veri sözlüğü / README / yol-haritası:** `malzemeler`/`stok_hareketleri`/`satinalma_talepleri`/`satinalma_talebi_kalemleri` + S9 ✅.

## 10. Definition of Done (S9)
- [ ] `ruff`+`mypy` temiz; FE `eslint`+`tsc --strict`+`prettier` temiz.
- [ ] Birim + entegrasyon testleri geçer; **bakiye doğruluğu** + **kenar-tetikli kritik** + **idempotency** + **tenant izolasyonu** + **`satinalma:onay` 403** testleri kalıcı.
- [ ] API standart zarf (`{success, message, data, meta}`) + doğru HTTP kodu; `openapi.json` + FE codegen güncel.
- [ ] Migration `public` + ≥2 tenant şemasında fan-out + downgrade.
- [ ] Yazma uçları audit üretir.
- [ ] ADR-0011 + veri sözlüğü + README/yol-haritası güncel.
- [ ] CI yeşil; Conventional Commit.
- [ ] **Uçtan uca doğrulama:** stok çıkışı kritik eşiği tetikler → canlı kritik rozet/uyarı; çok-kalemli talep `taslak→onay_bekliyor→onaylandi` akışı UI'da çalışır (gerçek tarayıcı).
